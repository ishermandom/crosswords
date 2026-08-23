#!/usr/bin/env python3
# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Machine-wide exclusive lease coordinating local model workloads.

Multiple Claude sessions share this machine's unified memory, and two model
workloads at once oversubscribe it. Any session about to run a local model
workload (an ollama batch, an MLX train or eval) first acquires the lease;
anyone else waits their turn. The protocol:

- **Exclusive**: one model workload at a time, recorded in a lease file.
- **Measured, not trusted**: acquiring requires that the machine *measures* idle
  — ollama reports no loaded models, the kernel's memory-pressure level is
  normal, and no model-stack process (python / ollama / optiq / mlx) holds
  multi-GB residency — in addition to the lease being free. A stale lease (dead
  holder PID or past expiry) is broken only when the machine also measures idle;
  a dead holder whose memory is still wired blocks acquisition — surface that to
  the user rather than piling on.
- **FIFO**: a blocked session runs `wait` (typically as a background watcher),
  then retries `acquire`; the file-creation race between two waiters has a
  single winner. `wait` also leaves an advisory I'm-waiting note (shown by
  `status`) so the holder can see demand: between self-served runs, the holder
  checks `status` and, seeing a waiter, releases instead of starting the next
  run.
- **Release unloads**: releasing asks ollama to unload loaded models so the next
  holder starts from measured idle. MLX frees its memory on process exit by
  itself.

Running a job under the lease — the detached-driver + watcher pattern.
Session-scoped background processes get killed after roughly 15 minutes (cause
unidentified — observed in both the Desktop app and the standalone terminal
CLI), so any job that might outlive that must not run as a plain in-session
command:

1. Acquire the lease.
2. Launch the job detached under `caffeinate`, writing to a log file, e.g.
   `subprocess.Popen(['caffeinate', '-is', ...], stdout=log_file,
   stderr=subprocess.STDOUT, start_new_session=True)` — its own process group
   sits out of the group-kill's reach, and caffeinate keeps the machine from
   sleeping. Without it, an unattended Mac drops into maintenance sleep with
   ~45-second dark-wakes every ~17 minutes, and a 27-minute batch takes 141 wall
   minutes (measured 2026-07-03; verify with `pmset -g log`).
3. Attach an expendable background watcher — `until ! kill -0 <pid>; do sleep
   30; done`, then `release` — to wake the session and free the lease on
   completion. A reaped watcher is harmless: the job continues, a fresh watcher
   can re-attach, and expiry plus the measured-idle rule backstop a lost
   release.

Usage:

```
cluegen/local/compute_lease.py status
cluegen/local/compute_lease.py acquire --holder ceiling \\
    --task 'agreement eval' --minutes 20 [--pid 74146]
cluegen/local/compute_lease.py wait --holder finetune \\
    [--task 'stage-1 eval'] [--timeout-minutes 240]
cluegen/local/compute_lease.py release --holder ceiling
```

Pass `--pid` when the workload runs as a known detached process; the lease then
frees early if that process dies. Without it, staleness rests on the expiry
alone (the estimate times a grace factor).

Exit codes: 0 success; 1 lease held by a live holder (wait, then retry); 2
machine busy — wired memory without a live lease, e.g. a keep-alive leftover or
a run outside the protocol (investigate); 3 wait timed out.
"""

import argparse
import dataclasses
import datetime
import enum
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

_LEASE_PATH = pathlib.Path('/Users/Shared/models/.compute-lease.json')
_WAITERS_PATH = pathlib.Path('/Users/Shared/models/.compute-waiters.json')
_OLLAMA_PS_URL = 'http://localhost:11434/api/ps'
_OLLAMA_BINARY = shutil.which('ollama') or '/opt/homebrew/bin/ollama'

# `sysctl kern.memorystatus_vm_pressure_level`: 1 normal, 2 warn, 4 critical.
_PRESSURE_NORMAL = 1

# Grace factor on the holder's own duration estimate before the lease counts as
# expired.
_EXPIRY_GRACE = 1.5

_POLL_SECONDS = 15

# Any process this large running one of the local model stacks is treated as a
# model workload, whether or not a lease records it. MLX jobs are invisible to
# the other two idle signals — they never appear in ollama, and ~10 GB on a 32
# GB machine leaves the kernel pressure level at normal — so the process table
# is the load-bearing check for them (incident: 2026-07-03 lease overlap).
_WORKLOAD_COMMAND_PATTERN = re.compile(
  r'python|ollama|optiq|mlx', re.IGNORECASE
)
_WORKLOAD_RSS_THRESHOLD_KIB = 2 * 1024 * 1024


class ExitCode(enum.IntEnum):
  """Process exit codes; see the module docstring."""

  OK = 0
  LEASE_HELD = 1
  MACHINE_BUSY = 2
  WAIT_TIMEOUT = 3


@dataclasses.dataclass(frozen=True)
class Lease:
  """One session's recorded claim on the machine's model-compute capacity.

  `pid` is the workload's process when known, or 0 when liveness isn't tracked
  and staleness rests on `expires_at` alone.
  """

  holder: str
  pid: int
  task: str
  acquired_at: float
  expires_at: float

  def describe(self) -> str:
    """One line naming the holder, task, and lease window."""
    acquired = datetime.datetime.fromtimestamp(self.acquired_at)
    expires = datetime.datetime.fromtimestamp(self.expires_at)
    return (
      f'{self.holder} (pid {self.pid or "untracked"}): {self.task} '
      f'[acquired {acquired:%H:%M:%S}, expires {expires:%H:%M:%S}]'
    )


@dataclasses.dataclass(frozen=True)
class Waiter:
  """One session's advisory note that it wants the machine next.

  Purely informational — it never blocks anyone. It lets the lease holder see
  demand between self-served runs and yield instead of starting another batch.
  """

  holder: str
  task: str
  since: float

  def describe(self) -> str:
    """One line naming the waiter, its task, and when it started waiting."""
    since = datetime.datetime.fromtimestamp(self.since)
    return f'{self.holder}: {self.task} [waiting since {since:%H:%M:%S}]'


def _read_waiters() -> list[Waiter]:
  """All registered I'm-waiting notes; [] when nobody is waiting.

  Raises ValueError on a malformed waiters file — like the lease file, that
  means a protocol bug worth a look rather than a silent default.
  """
  try:
    text = _WAITERS_PATH.read_text()
  except FileNotFoundError:
    return []
  entries: object = json.loads(text)
  if not isinstance(entries, list):
    raise ValueError(f'malformed waiters file {_WAITERS_PATH}: {text!r}')
  waiters: list[Waiter] = []
  for entry in entries:
    if not isinstance(entry, dict):
      raise ValueError(f'malformed waiters file {_WAITERS_PATH}: {text!r}')
    try:
      waiters.append(
        Waiter(
          holder=str(entry['holder']),
          task=str(entry['task']),
          since=float(entry['since']),
        )
      )
    except (KeyError, TypeError, ValueError) as error:
      raise ValueError(
        f'malformed waiters file {_WAITERS_PATH}: {text!r}'
      ) from error
  return waiters


def _write_waiters(waiters: list[Waiter]) -> None:
  """Persist the waiter notes; an empty list removes the file."""
  if waiters:
    _WAITERS_PATH.write_text(
      json.dumps([dataclasses.asdict(waiter) for waiter in waiters])
    )
  else:
    _WAITERS_PATH.unlink(missing_ok=True)


def _set_waiting_note(holder: str, task: str) -> None:
  """Register `holder`'s I'm-waiting note, replacing any prior one."""
  others = [waiter for waiter in _read_waiters() if waiter.holder != holder]
  _write_waiters([*others, Waiter(holder=holder, task=task, since=time.time())])


def _clear_waiting_note(holder: str) -> None:
  """Drop `holder`'s I'm-waiting note, if present."""
  _write_waiters(
    [waiter for waiter in _read_waiters() if waiter.holder != holder]
  )


def _loaded_models() -> list[str]:
  """Names of the models ollama holds in memory; [] when ollama is down."""
  try:
    with urllib.request.urlopen(_OLLAMA_PS_URL, timeout=5) as response:
      payload: object = json.load(response)
  except (urllib.error.URLError, TimeoutError):
    return []
  if not isinstance(payload, dict):
    return []
  models = payload.get('models')
  if not isinstance(models, list):
    return []
  names: list[str] = []
  for model in models:
    if isinstance(model, dict) and isinstance(model.get('name'), str):
      names.append(model['name'])
  return names


def _memory_pressure_level() -> int:
  """The kernel's memory-pressure level: 1 normal, 2 warn, 4 critical."""
  result = subprocess.run(
    ['sysctl', '-n', 'kern.memorystatus_vm_pressure_level'],
    capture_output=True,
    text=True,
    check=True,
  )
  return int(result.stdout.strip())


def model_workload_processes(ps_output: str) -> list[str]:
  """Descriptions of processes that look like running model workloads.

  `ps_output` is `ps axo pid=,rss=,command=` text: pid, resident set size in
  KiB, then the full command line. A process counts as a model workload when its
  command matches one of the local model stacks and its resident set exceeds the
  threshold.
  """
  workloads: list[str] = []
  for line in ps_output.splitlines():
    fields = line.split(None, 2)
    if len(fields) < 3:
      continue
    pid, rss_kib, command = fields
    if not rss_kib.isdigit():
      continue
    if int(rss_kib) < _WORKLOAD_RSS_THRESHOLD_KIB:
      continue
    if not _WORKLOAD_COMMAND_PATTERN.search(command):
      continue
    rss_gib = int(rss_kib) / (1024 * 1024)
    workloads.append(f'pid {pid} rss {rss_gib:.1f} GiB: {command[:80]}')
  return workloads


def _ps_output() -> str:
  """`ps axo pid=,rss=,command=` output for every process on the machine."""
  result = subprocess.run(
    ['ps', 'axo', 'pid=,rss=,command='],
    capture_output=True,
    text=True,
    check=True,
  )
  return result.stdout


def _busy_reason() -> str | None:
  """Why the machine is not measurably idle, or None when it is."""
  models = _loaded_models()
  if models:
    return f'ollama has loaded: {", ".join(models)}'
  pressure = _memory_pressure_level()
  if pressure != _PRESSURE_NORMAL:
    return f'kernel memory-pressure level is {pressure} (normal is 1)'
  workloads = model_workload_processes(_ps_output())
  if workloads:
    return f'model workload running: {"; ".join(workloads)}'
  return None


def _read_lease() -> Lease | None:
  """The current lease, or None when the machine is unleased.

  Raises ValueError on a malformed lease file — that means a protocol bug, not
  contention, and deserves a look rather than a silent default.
  """
  try:
    text = _LEASE_PATH.read_text()
  except FileNotFoundError:
    return None
  fields: object = json.loads(text)
  if not isinstance(fields, dict):
    raise ValueError(f'malformed lease file {_LEASE_PATH}: {text!r}')
  try:
    return Lease(
      holder=str(fields['holder']),
      pid=int(fields['pid']),
      task=str(fields['task']),
      acquired_at=float(fields['acquired_at']),
      expires_at=float(fields['expires_at']),
    )
  except (KeyError, TypeError, ValueError) as error:
    raise ValueError(f'malformed lease file {_LEASE_PATH}: {text!r}') from error


def _is_pid_alive(pid: int) -> bool:
  """Whether `pid` names a live process."""
  try:
    os.kill(pid, 0)
  except ProcessLookupError:
    return False
  except PermissionError:
    # The process exists but belongs to another user.
    return True
  return True


def _is_stale(lease: Lease) -> bool:
  """Whether the lease's holder can no longer be assumed to be running."""
  if time.time() > lease.expires_at:
    return True
  return lease.pid != 0 and not _is_pid_alive(lease.pid)


def _blocking_reason() -> str | None:
  """What blocks an acquire right now, or None when one should succeed."""
  lease = _read_lease()
  if lease is not None and not _is_stale(lease):
    return f'lease held by {lease.describe()}'
  return _busy_reason()


def _acquire(holder: str, task: str, minutes: float, pid: int) -> ExitCode:
  """Take the lease if the file is free and the machine measures idle."""
  lease = _read_lease()
  if lease is not None:
    if not _is_stale(lease):
      print(f'lease held by {lease.describe()}')
      return ExitCode.LEASE_HELD
    busy = _busy_reason()
    if busy is not None:
      print(
        f'stale lease ({lease.describe()}) but the machine is not idle: '
        f'{busy} — NOT breaking it; investigate or surface to the user'
      )
      return ExitCode.MACHINE_BUSY
    print(f'breaking stale lease: {lease.describe()}')
    _LEASE_PATH.unlink()

  busy = _busy_reason()
  if busy is not None:
    print(
      f'no lease, but the machine is not idle: {busy} — likely a '
      'keep-alive leftover or a run outside the protocol'
    )
    return ExitCode.MACHINE_BUSY

  now = time.time()
  new_lease = Lease(
    holder=holder,
    pid=pid,
    task=task,
    acquired_at=now,
    expires_at=now + minutes * 60 * _EXPIRY_GRACE,
  )
  try:
    # 'x' makes creation atomic: of two racing acquirers, one wins.
    with _LEASE_PATH.open('x') as file:
      json.dump(dataclasses.asdict(new_lease), file)
  except FileExistsError:
    print('lost an acquire race; wait and retry')
    return ExitCode.LEASE_HELD
  _clear_waiting_note(holder)
  print(f'acquired: {new_lease.describe()}')
  for waiter in _read_waiters():
    print(f'note — also waiting: {waiter.describe()}')
  return ExitCode.OK


def _wait(holder: str, task: str, timeout_minutes: float) -> ExitCode:
  """Block until an acquire should succeed; report each change of blocker.

  Leaves `holder`'s advisory I'm-waiting note registered for the duration so the
  lease holder can see the demand and yield between runs.
  """
  _set_waiting_note(holder, task)
  try:
    deadline = time.time() + timeout_minutes * 60
    last_reason = ''
    while time.time() < deadline:
      reason = _blocking_reason()
      if reason is None:
        print('machine is free')
        return ExitCode.OK
      if reason != last_reason:
        print(f'waiting: {reason}', flush=True)
        last_reason = reason
      time.sleep(_POLL_SECONDS)
    print(f'still blocked after {timeout_minutes:g} minutes: {last_reason}')
    return ExitCode.WAIT_TIMEOUT
  finally:
    _clear_waiting_note(holder)


def _release(holder: str) -> ExitCode:
  """Unload ollama models and free the lease held by `holder`."""
  lease = _read_lease()
  if lease is not None and lease.holder != holder:
    print(f'lease belongs to {lease.describe()}, not {holder!r} — refusing')
    return ExitCode.LEASE_HELD
  for model in _loaded_models():
    subprocess.run(
      [_OLLAMA_BINARY, 'stop', model], capture_output=True, check=True
    )
    print(f'unloaded {model}')
  if lease is None:
    print('no lease to release')
  else:
    _LEASE_PATH.unlink()
    print('released')
  return ExitCode.OK


def _status() -> ExitCode:
  """Print the lease and the measured machine state."""
  lease = _read_lease()
  if lease is None:
    print('lease: free')
  else:
    staleness = ' [STALE]' if _is_stale(lease) else ''
    print(f'lease: {lease.describe()}{staleness}')
  busy = _busy_reason()
  print(f'machine: {busy if busy else "measures idle"}')
  for waiter in _read_waiters():
    print(f'waiting: {waiter.describe()}')
  return ExitCode.OK


def main() -> int:
  """Dispatch the subcommand; returns the process exit code."""
  parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  subcommands = parser.add_subparsers(dest='subcommand', required=True)

  subcommands.add_parser('status')
  acquire = subcommands.add_parser('acquire')
  acquire.add_argument('--holder', required=True)
  acquire.add_argument('--task', required=True)
  acquire.add_argument('--minutes', type=float, required=True)
  acquire.add_argument('--pid', type=int, default=0)
  wait = subcommands.add_parser('wait')
  wait.add_argument('--holder', required=True)
  wait.add_argument('--task', default='unspecified')
  wait.add_argument('--timeout-minutes', type=float, default=240)
  release = subcommands.add_parser('release')
  release.add_argument('--holder', required=True)

  args = parser.parse_args()
  if args.subcommand == 'status':
    return _status()
  if args.subcommand == 'acquire':
    return _acquire(args.holder, args.task, args.minutes, args.pid)
  if args.subcommand == 'wait':
    return _wait(args.holder, args.task, args.timeout_minutes)
  return _release(args.holder)


if __name__ == '__main__':
  sys.exit(main())
