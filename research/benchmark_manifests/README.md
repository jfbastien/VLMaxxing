# Benchmark Manifests

These manifests freeze benchmark item selections so planner and refresh search
can happen on a development slice without silently tuning on the reported
evaluation slice.

Current policy:

- `*_dev_v1.toml` preserves the first local benchmark slices already used in the
  checked-in reproduction notes
- `*_holdout_v1.toml` is a disjoint fixed-seed holdout for later evaluation
- holdouts are deterministic:
  - TOMATO: stratified `5` per split from the remaining items with
    `random.Random(42)`
  - MVBench hosted predecessor-style slice: stratified `3` per task from the
    remaining hosted items with `random.Random(42)` and local video existence
    checks

Runner support:

- pass `--manifest research/benchmark_manifests/<name>.toml` to
  `scripts/run_benchmark_track_a.py`
- benchmark runs fail on dirty trees by default; use `--allow-dirty` only for
  debugging, never for paper-grade artifacts
