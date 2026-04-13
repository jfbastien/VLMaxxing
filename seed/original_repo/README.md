# Original Repo Reference Material

These files were imported selectively from `~/s/codec-through-sam/` on 2026-04-13.

Purpose:

- preserve the strongest predecessor scripts and result artifacts
- make future audits and agent reviews possible without reopening the old repo
- keep provenance visible while the working code in `src/` stays clean

Non-purpose:

- serve as the repo's primary implementation
- bypass audit or review

## Trust Level

Treat these files as:

- useful reference material
- important provenance
- not the active source of truth

The active source of truth for new work is:

- code under `src/`
- tests under `tests/`
- audit notes under `docs/`

## Imported Material

Reference experiments:

- `experiments/run_tomato_mlx.py`
- `experiments/codec_pipeline.py`
- `experiments/exp_wall_clock_speedup.py`
- `experiments/exp_vit_attention_baseline.py`
- `experiments/exp_per_block_mv_lookup.py`
- `experiments/qtable_prefilter.py`

Reference result artifacts:

- `results/tomato_7b_ALL_1000.json`
- `results/mvbench_7b_10.json`
- `results/codec_native_results.json`
- `results/mv_relocation_results.json`
- `results/vit_attention_results.json`
- `results/h264_spatial_signals_results.json`

## Exclusions

These were intentionally not imported:

- scripts containing secrets
- mission files
- the fleet knowledge database
- generated agent result dumps as if they were source code

See [docs/original-repo-audit.md](../../docs/original-repo-audit.md) for the reasoning.
