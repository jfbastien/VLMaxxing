# Phase 1.5: MVBench Benchmark-Native Reproduction Slice

## Preregistration

Objective:

- establish the first benchmark-native MVBench reproduction path on this local
  MLX Qwen `7B` stack using the same-position cached-feature method family

Claim register targets:

- `WP-2.6`
- `WP-3.1`

Reproduction mode:

- generalized reproduction

Track:

- A

Hypotheses:

- the hosted predecessor-style MVBench slice will run cleanly on this machine
  after fixing the local asset profile and nested-path resolver
- on an initial hosted slice, cached answers will stay close to dense answers
  under default same-position reuse and thresholds `(3, 8)`

Stack caveats stated up front:

- local model path is `Qwen2.5-VL-7B-Instruct-4bit` under MLX, not the imported
  PyTorch float16 path
- chunked subprocess execution is part of the declared semantic harness
  contract on this machine
- the initial local slice uses only the hosted predecessor-style tasks and does
  not claim NTU-manual completion

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
- per-task accuracy deltas
- per-item generation metadata

Run A: hosted smoke

- `1` item per hosted predecessor-style task, `18` items total

Run A acceptance band:

- all items return parseable dense and cached outputs
- no item-level runtime crash

Run A rejection band:

- model load, file resolution, or item execution fails materially enough that
  the hosted MVBench path cannot run end to end

Run B: initial hosted subset

- `3` items per hosted predecessor-style task, `54` items total

Run B acceptance band:

- cached accuracy stays within `2` answers of dense
- agreement stays at or above `0.85`
- cached parse failures stay at or below `2`

Run B rejection band:

- cached accuracy drops by more than `5` answers relative to dense
- agreement falls below `0.70`
- parse failures exceed `4`

Inconclusive:

- harness instability forces uncontrolled reruns
- hosted-only coverage proves too unrepresentative to interpret against the
  imported `18`-task slice

Notes:

- this note is about bringing the MVBench benchmark-native reproduction lane
  online on the hosted portion of the predecessor-style task slice
- if Run A succeeds, Run B should happen before any stronger `WP-2.6` language
  lands in the reproduction ledger

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
