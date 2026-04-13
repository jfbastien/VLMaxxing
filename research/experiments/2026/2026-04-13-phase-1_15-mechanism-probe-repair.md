# Phase 1.15: Mechanism Probe Repair

## Preregistration

Hypothesis:

- after repairing the synthetic probe geometry and measuring cosine in
  float32/float64, the local mechanism results will move closer to the imported
  whitepaper shape: repeated-image identity will stay exact, the partial-change
  minimum will land on the target token or its immediate neighborhood, and
  boundary-safe within-block shifts through `14 px` will remain highly similar

Track:

- A-supporting measurement

Primary metrics:

- repeated-encode max absolute feature diff
- repeated-encode row-wise cosine
- minimum-distance token under a mild localized partial change
- target-token cosine and far-field mean cosine for `1`, `4`, `8`, and `14 px`
  shifts that stay inside one `28 px` merged block

Secondary metrics:

- natural-image localized-change distance summary
- right-neighbor cosine for the boundary-safe shift ladder

Unit of analysis:

- merged visual token

Model:

- `Qwen2.5-VL-3B-Instruct-4bit`

Inputs:

- one repaired synthetic probe image aligned to the merged-token grid
- one natural probe image from `xiph_akiyo_cif`

Acceptance band:

- repeated-image identity stays exact
- synthetic mild partial-change minimum lands on the target token or distance
  `1`, and far-field mean cosine reaches at least `0.99`
- synthetic boundary-safe `1`, `4`, `8`, and `14 px` shifts keep target-token
  cosine at or above `0.96` and far-field mean cosine at or above `0.99`

Rejection band:

- repeated-image identity breaks
- repaired probes still show broad non-local disruption without a distance-shaped
  effect

Inconclusive:

- alignment remains ambiguous enough that the repaired probe cannot be
  interpreted
- runtime instability prevents a clean run

Notes:

- this experiment preserves the earlier Phase `1.1` run as a historical baseline
- if the repaired probe still disagrees materially, the next follow-up is a
  precision/runtime comparison rather than more synthetic tweaking

## Execution

Run date:

- 2026-04-13

Artifact:

- [phase1_15.json](artifacts/phase1_15.json)

## Result

Inconclusive under the preregistered acceptance band; interpreted narratively as
an improved but still partial reproduction.

Summary:

- repeated-image identity stayed exact to the local repeated-encode tolerance:
  - `xiph_akiyo_cif_frame0` max abs diff `0.0`, mean row cosine `0.99999998`
  - `mechanism_base_image_v2` max abs diff `0.0`, mean row cosine
    `0.99999999`
- repaired synthetic partial change:
  - target-token cosine `0.915`
  - minimum-cosine token landed at Manhattan distance `2`, not on the target or
    immediate neighbor
- repaired synthetic within-block shifts:
  - `1 px`: target-token cosine `0.993`, far-field mean `0.997`
  - `4 px`: target-token cosine `0.969`, far-field mean `0.988`
  - `8 px`: target-token cosine `0.948`, far-field mean `0.981`
  - `14 px`: target-token cosine `0.949`, far-field mean `0.987`
- natural-image localized partial change remained strongly coupled:
  - target-token cosine `0.477`
  - minimum-cosine token landed at Manhattan distance `3`

## Interpretation

The repair matters, but it does not fully close the gap.

What got stronger:

- the earlier `8 px` and `14 px` shift collapse was largely a probe-geometry
  artifact
- after the repair, the shift ladder is smoother and remains qualitatively
  local rather than catastrophically non-monotonic
- repeated-image identity stays exact under the higher-precision cosine
  measurement

What still does not reproduce at imported strength:

- the repaired synthetic partial-change minimum still misses the target
  neighborhood
- the repaired `8 px` and `14 px` shifts still fall below the preregistered
  target and far-field cosine bands
- the natural-image probe shows broader spatial coupling than the simple
  synthetic story suggests

Most likely implication:

- the Phase `1.1` mismatch was partly probe design, but not only probe design
- the local MLX `4-bit` path still looks weaker than the imported PyTorch/MPS
  float32 whitepaper path on locality and shift-strength

Next follow-up:

- compare the same repaired probes on a higher-precision local runtime before
  treating this as a conceptual disagreement with the whitepaper

## Links

- [2026-04-13-phase-1_1-direct-mechanism-reproduction.md](2026-04-13-phase-1_1-direct-mechanism-reproduction.md)
- [docs/reproduction-status.md](../../../docs/reproduction-status.md)
