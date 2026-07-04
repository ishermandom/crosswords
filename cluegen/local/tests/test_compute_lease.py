# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Tests for the model-workload process scan in compute_lease."""

from cluegen.local.compute_lease import model_workload_processes


def _ps_line(pid: int, rss_kib: int, command: str) -> str:
  """One `ps axo pid=,rss=,command=` output line."""
  return f'{pid:>5} {rss_kib:>8} {command}'


# --- detection ---


def test_large_python_process_is_reported_with_pid_and_size() -> None:
  output = _ps_line(
      68811, 10 * 1024 * 1024,
      '/Users/claude-sandbox/.venvs/default/bin/python '
      '/Users/claude-sandbox/.venvs/default/bin/optiq lora train')

  workloads = model_workload_processes(output)

  assert len(workloads) == 1
  assert 'pid 68811' in workloads[0]
  assert '10.0 GiB' in workloads[0]


def test_ollama_runner_is_reported() -> None:
  output = _ps_line(3568, 18 * 1024 * 1024,
                    '/opt/homebrew/bin/ollama runner --model gemma4')

  workloads = model_workload_processes(output)

  assert len(workloads) == 1
  assert 'pid 3568' in workloads[0]


# --- exclusions ---


def test_small_python_process_is_ignored() -> None:
  # An idle interpreter well under the threshold is everyday background noise,
  # not a model workload.
  output = _ps_line(400, 120 * 1024, '/usr/bin/python3 some_script.py')

  assert model_workload_processes(output) == []


def test_large_non_workload_process_is_ignored() -> None:
  # Browsers routinely exceed the size threshold; only the model stacks count.
  output = _ps_line(
      500, 3 * 1024 * 1024,
      '/Applications/Chrome.app/Contents/Frameworks/Chrome Helper (Renderer)')

  assert model_workload_processes(output) == []


def test_malformed_lines_are_ignored() -> None:
  output = '\n'.join([
      '',
      'not a ps line',
      _ps_line(68811, 10 * 1024 * 1024, '/usr/bin/python3 train.py'),
  ])

  workloads = model_workload_processes(output)

  assert len(workloads) == 1
