# Phase 1.1: Direct Mechanism Reproduction

## Preregistration

Hypothesis:

- the local Qwen 3B vision path reproduces the whitepaper's mechanistic shape:
  exact repeated-image identity, strong locality under a single aligned token
  change, and high far-field similarity under localized motion

Track:

- A-supporting measurement

Primary metrics:

- repeated-encode max absolute feature diff
- repeated-encode mean row-wise cosine similarity
- token-wise cosine by Manhattan distance from a changed token
- target-token and far-field cosine under localized shifts

Unit of analysis:

- merged visual token

Model:

- `Qwen2.5-VL-3B-Instruct-4bit`

Inputs:

- one natural probe image from `xiph_akiyo_cif`
- one controlled synthetic mechanism probe image aligned to Qwen's `28 px`
  merged-token grid

Preprocessing:

- decode backend: `pyav` for the natural probe
- colorspace: RGB
- no padding
- Qwen-aligned image size `336x252`

Acceptance band:

- repeated encodes of the same image have max abs diff `0.0` and mean
  row-wise cosine `1.0`
- for the aligned single-token partial change, the lowest-cosine token lands on
  the target token or its immediate neighborhood and far-field mean cosine
  stays above `0.99`
- for localized shifts of `1 px` and `4 px`, target-token cosine stays above
  `0.95` while far-field mean cosine stays above `0.99`

Rejection band:

- repeated-encode identity is not exact
- the locality probe shows broad feature disruption instead of a distance-shaped
  effect

Inconclusive:

- runtime instability prevents the direct feature probes from completing
- target-token alignment is ambiguous enough that the locality result cannot be
  interpreted

## Execution

Run date:

- 2026-04-13

Artifact:

- [phase1_1.json](artifacts/phase1_1.json)

## Result

Inconclusive under the preregistered acceptance band; interpreted narratively as
partial reproduction.

Repeated-image identity:

- `xiph_akiyo_cif` natural probe:
  - feature shape `9x11x2048`
  - max abs diff `0.0`
  - mean row-wise cosine `1.0`
- controlled synthetic mechanism probe:
  - feature shape `9x12x2048`
  - max abs diff `0.0`
  - mean row-wise cosine `1.0`

Aligned partial change:

- target token: `(row=4, col=5)`
- target-token cosine: `0.736`
- mean cosine rises with distance from the changed token:
  - distance `0`: `0.736`
  - distance `1`: `0.798`
  - distance `2`: `0.864`
  - distance `5`: `0.942`
  - distance `9`: `0.984`
- the minimum-cosine token landed at `(row=6, col=6)`, not exactly on the
  target token

Localized shift:

- `1 px` shift:
  - target-token cosine `0.990`
  - far-field mean cosine `0.993`
- `4 px` shift:
  - target-token cosine `0.975`
  - far-field mean cosine `0.989`
- `8 px` shift:
  - target-token cosine `0.565`
  - far-field mean cosine `0.935`
- `14 px` shift:
  - target-token cosine `0.937`
  - far-field mean cosine `0.985`

## Interpretation

What reproduced cleanly:

- exact repeated-image feature identity on the local Qwen 3B MLX path

What reproduced only qualitatively:

- the partial-change probe does show a locality-shaped effect: mean cosine
  generally rises with distance from the changed token
- small localized shifts of `1 px` and `4 px` keep the target token highly
  similar and the far field near `0.99`

What did not reproduce at imported whitepaper strength:

- the far field under the aligned partial-change probe stayed below the
  preregistered `>0.99` target
- larger shifts degraded more sharply than the imported whitepaper story would
  suggest
- the partial-change probe's minimum-cosine token did not land exactly on the
  target token, so alignment or broader-context effects remain an open question

Net:

- the local repo now directly reproduces the strongest low-level identity claim
- the locality and shift claims remain only partially reproduced and should stay
  out of any stronger prose until we run the follow-up alignment and natural
  image probes

## Links

- [PLAN.md](../../../PLAN.md)
- [docs/reproduction-status.md](../../../docs/reproduction-status.md)
- [research/decision-log.md](../../decision-log.md)
