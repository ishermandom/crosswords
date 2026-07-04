# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Training launcher: optiq's LoRA trainer plus learning-rate schedules and
resume.

`optiq lora train` is constant-LR only and cannot resume a checkpoint — both are
needed for the multi-night scaling rungs (15k, 50k). This launcher reuses
optiq's `train_lora` (OptiQ quant handling, best-adapter snapshots, flash
attention) and adds:

- Schedule: linear warmup 0 -> peak, hold at peak, cosine decay to a floor over
  the final stretch. MLX optimizers accept a step->lr callable, and `train_lora`
  passes `config.learning_rate` straight into AdamW, so the schedule rides
  through untouched.
- Resume: `--resume-adapter-file` loads existing adapter weights right after
  optiq applies its LoRA layers (a wrapper around
  `apply_sensitivity_aware_lora`; the trainer re-imports it at call time, so the
  wrapper takes effect).

LoRA shape matches the stage-1 probe runs: rank 8, alpha 8, constant rank
scaling.

Usage: python launch_train.py MODEL --data DIR --output DIR --iters N
           --peak-lr LR [--batch-size N] [--resume-adapter-file FILE]
"""

import argparse

from optiq.mlx_lm_patches._register import register


def build_lr_schedule(peak: float, iters: int, warmup_fraction: float,
                      decay_fraction: float, floor_fraction: float):
  """Step->lr callable: warmup to `peak`, hold, cosine decay to the floor."""
  import mlx.optimizers as optim

  warmup_steps = max(1, round(iters * warmup_fraction))
  decay_steps = max(1, round(iters * decay_fraction))
  warmup = optim.schedulers.linear_schedule(0.0, peak, warmup_steps)
  cosine = optim.schedulers.cosine_decay(peak, decay_steps,
                                         peak * floor_fraction)

  def hold(_step) -> float:
    return peak

  return optim.schedulers.join_schedules(
      [warmup, hold, cosine], [warmup_steps, iters - decay_steps])


def install_resume(resume_file: str) -> None:
  """Load `resume_file` into the model right after LoRA layers are applied."""
  from optiq.lora import apply as apply_module

  original_apply = apply_module.apply_sensitivity_aware_lora

  def apply_and_load(model, model_dir, config):
    applied_ranks = original_apply(model, model_dir, config)
    print(f'[launcher] resuming adapter weights from {resume_file}')
    model.load_weights(resume_file, strict=False)
    return applied_ranks

  apply_module.apply_sensitivity_aware_lora = apply_and_load


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('model')
  parser.add_argument('--data', required=True)
  parser.add_argument('--output', required=True)
  parser.add_argument('--iters', type=int, required=True)
  parser.add_argument('--peak-lr', type=float, required=True)
  parser.add_argument('--batch-size', type=int, default=1)
  parser.add_argument('--warmup-fraction', type=float, default=0.04)
  parser.add_argument('--decay-fraction', type=float, default=0.25)
  parser.add_argument('--floor-fraction', type=float, default=0.10,
                      help='final lr as a fraction of peak')
  parser.add_argument('--constant-lr', action='store_true',
                      help='skip the schedule (matches optiq CLI behavior; '
                           'for apples-to-apples short probes)')
  parser.add_argument('--resume-adapter-file', default=None)
  args = parser.parse_args()

  register()
  from optiq.lora.config import OptiqLoraConfig
  from optiq.lora.trainer import train_lora

  learning_rate = (args.peak_lr if args.constant_lr else build_lr_schedule(
      args.peak_lr, args.iters, args.warmup_fraction, args.decay_fraction,
      args.floor_fraction))
  if args.resume_adapter_file:
    install_resume(args.resume_adapter_file)

  config = OptiqLoraConfig(
      rank=8, scale=1.0, rank_scaling='constant',
      batch_size=args.batch_size, iters=args.iters,
      learning_rate=learning_rate, adapter_path=args.output)
  result = train_lora(args.model, args.data, config)
  print(f'[launcher] done: {result}')


if __name__ == '__main__':
  main()
