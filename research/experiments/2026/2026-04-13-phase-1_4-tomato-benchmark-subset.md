# Phase 1.4: TOMATO Benchmark-Native Reproduction Slice

## Preregistration

Objective:

- establish the first benchmark-native TOMATO reproduction path on this local
  MLX Qwen `7B` stack using the same-position cached-feature method family

Claim register targets:

- `WP-2.5`
- `WP-3.1`

Reproduction mode:

- generalized reproduction

Track:

- A

Hypotheses:

- the benchmark-native TOMATO path will run cleanly on this machine with
  chunked subprocess execution
- on a stratified TOMATO subset, cached answers will remain close to dense
  answers under default same-position reuse and default thresholds `(3, 8)`

Stack caveats stated up front:

- local model path is `Qwen2.5-VL-7B-Instruct-4bit` under MLX, not the imported
  PyTorch float16 path
- chunked subprocess execution is part of the declared semantic harness
  contract on this machine
- the initial reproduction slice uses a subset, not the full `1,484`-question
  benchmark

Sampling and preprocessing:

- `uniform_global` sampling
- `8` frames per video
- resize and black-pad every decoded frame to `560 x 560` to match the imported
  benchmark-style path

Conditions:

- `dense`: dense-direct generation
- `cached_default`: same-position cached-feature substitution with reuse of
  `STATIC` and `SHIFTED` blocks under thresholds `(3, 8)`

Primary metrics:

- dense accuracy
- cached accuracy
- dense-versus-cached agreement
- cached parse-failure count

Secondary metrics:

- mean reuse ratio
- per-split accuracy deltas
- per-item generation metadata

Run A: smoke

- `1` item per TOMATO split, `6` items total

Run A acceptance band:

- all items return parseable dense and cached outputs
- no item-level runtime crash

Run A rejection band:

- model load or item execution fails materially enough that the benchmark path
  cannot run end to end

Run B: initial subset

- `5` items per TOMATO split, `30` items total

Run B acceptance band:

- cached accuracy stays within `1` answer of dense
- agreement stays at or above `0.90`
- cached parse failures stay at or below `1`

Run B rejection band:

- cached accuracy drops by more than `3` answers relative to dense
- agreement falls below `0.75`
- parse failures exceed `3`

Inconclusive:

- harness instability forces uncontrolled reruns
- local memory/runtime constraints require changing frame count or model before
  Run B completes

Notes:

- this note is about bringing the benchmark-native reproduction lane online
- even a successful Run B is still a generalized reproduction, not a strict
  replication of the imported full-benchmark story

## Execution

Run date:

- pending

Artifacts:

- pending

## Result

Pending.

## Interpretation

Pending.

## Links

- [docs/claim-register.md](../../../docs/claim-register.md)
- [docs/reproduction-status.md](../../../docs/reproduction-status.md)
- [docs/benchmark-setup.md](../../../docs/benchmark-setup.md)
