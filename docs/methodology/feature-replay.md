# Feature Replay

Feature replay is a Track A acceleration layer for benchmark policy sweeps.

It caches the dense vision features for a `(model, prepared frame sequence)`
pair so later planner or refresh variants can reuse the same dense features
without re-encoding pixels.

## What It Is For

Use replay when the experiment changes only:

- planner statistic
- planner thresholds
- reuse classes
- bounded token age
- refresh interval

Replay is appropriate because those changes happen **after** dense vision
features already exist.

## What It Is Not

Feature replay is **not** Track B evidence.

It accelerates local Track A experimentation by avoiding redundant dense vision
encodes across repeated policy runs. It does **not** prove skipped model work in
the deployed method, and it must not be relabeled as:

- speedup
- compression
- FLOP reduction
- measured runtime win for the cached method

## Cache Identity Contract

A replay hit is valid only when all of the following match:

- model identifier
- benchmark item id
- full preprocessed frame sequence hash
- frame count
- preprocessed frame size
- preprocessing contract hash

The preprocessing contract currently covers:

- decode backend
- frame sampling mode
- maximum image size

Changing any of those inputs should produce a cache miss.

## Storage

Default cache location:

```text
research/cache/dense_features/
```

This directory is ignored by git.

Each cache entry stores:

- dense feature tensor
- `image_grid_thw`
- JSON metadata for provenance

## Runner Flags

The benchmark runner now exposes:

- `--feature-cache-dir <path>` to override the replay cache location
- `--no-feature-replay` to force dense recomputation even when a cache entry
  exists

Per-item outputs now record:

- `feature_cache_hit`

Run summaries now record:

- `feature_replay_enabled`
- `feature_cache_dir`
- `feature_cache_hits`
- `feature_cache_misses`

## Operational Guidance

- Warm the replay cache before broad planner grids if the same manifest will be
  evaluated many times.
- Keep benchmark execution single-worker during semantic measurements on this
  machine.
- Do not compare replay-on versus replay-off wall clock and call that a method
  win; the only supported conclusion is reduced experiment iteration cost.

## Minimal Validation

The replay path should be treated as working only after both conditions hold:

1. first pass on a fixed item records `feature_cache_hit = false`
2. second pass on the exact same item and cache dir records
   `feature_cache_hit = true` with unchanged dense and cached outputs
