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

- 2026-04-13

Artifacts:

- Run A hosted smoke:
  [phase1_5_run_a_smoke.json](artifacts/phase1_5_run_a_smoke.json)
- Run B initial hosted subset:
  - pending

## Result

Run A: hosted smoke

Preregistration outcome:

- Accepted for the smoke objective

Observed outcome:

- all `18` requested hosted-slice items returned parseable dense and cached
  answers
- no item-level runtime crash occurred
- dense accuracy: `12/18 = 0.667`
- cached accuracy: `11/18 = 0.611`
- dense-versus-cached agreement: `17/18 = 0.944`
- cached parse failures: `0`
- mean reuse ratio: `0.6928`
- only one item disagreed:
  - `mvbench:object_interaction:0`
  - dense answer `C` (correct)
  - cached answer `B` (wrong)
  - reuse ratio mean `0.7232`

Run B: initial hosted subset

- pending

## Interpretation

This is the strongest benchmark-native result on the local stack so far.

What the smoke established:

- after adding `perception.zip` and fixing nested hosted-path resolution, the
  hosted predecessor-style MVBench slice is genuinely runnable locally
- MVBench on this stack behaves much closer to the imported whitepaper
  direction than TOMATO does
- the default same-position cached path preserved `17/18` dense answers on the
  first hosted item from each predecessor-style task

What the smoke still does not establish:

- a generalized reproduction of `WP-2.6`
- stability on a larger hosted subset where per-task variance is visible

Immediate next step:

- run the preregistered `54`-item hosted subset before strengthening the
  reproduction-status row for `WP-2.6` beyond "partial, smoke only"

## Links

- [docs/claim-register.md](../../../docs/claim-register.md)
- [docs/reproduction-status.md](../../../docs/reproduction-status.md)
- [docs/benchmark-setup.md](../../../docs/benchmark-setup.md)
