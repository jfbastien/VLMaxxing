# Codec Score Runtime Denominators

Codec score sources can be measured under three different runtime policies.
Keep them separate in experiment summaries and paper text.

## `live_pyav`

The runner decodes video and extracts H.264 metadata through the current PyAV
helper inside each model arm. This is the conservative local wall-clock
denominator. It measures what this repo pays today, but it repeats extraction
for each score source unless a script explicitly shares sidecars.

Use this denominator for implementation honesty. Do not describe it as free.

## `sidecar`

A CPU prepass writes runner-ready score grids to `.npz` sidecars, and the model
arm loads those grids during inference. This separates one-time metadata
extraction from model-side sparse-vision timing.

Use this denominator for session or corpus serving analysis where a stable video
can be preprocessed once and queried many times. Report sidecar build time,
sidecar load time, and the first-query drift policy separately.

Claim-bearing sidecars must be bound to the current manifest item IDs, current
git commit, current score-projection version, geometry details, and score-grid
hash. A clean sidecar from an older commit is stale evidence unless the
preregistration explicitly permits historical reuse.

## `decoder_integrated`

The video decoder exposes macroblock metadata while producing pixels, avoiding
the current separate PyAV pass. This is a systems hypothesis until measured in a
decoder-integrated implementation.

Use this only as future-work or as a modeled ceiling. Do not report it as a
reproduced wall-clock result.

## Reporting Rule

For every codec-scored Track B or OV-8 row, report:

- `codec_score_runtime_source`: `live_pyav`, `sidecar`, or
  `decoder_integrated` hypothesis.
- model-side end-to-end time excluding score runtime.
- end-to-end time including the measured score runtime for the current path.
- sidecar build/load time or live extraction time, whichever applies.
- for sidecars: unique-item extraction total, projection/write total, total
  prepass wall time, and per-item load time. Do not sum per-source copies of the
  same unique-item H.264 extraction time.

Never multiply Track A active-refresh budget, Track B sparse-vision speed, and
C-PERSIST follow-up speed. They are different denominators.
