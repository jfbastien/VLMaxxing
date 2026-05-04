# 2026-05-04 Codec-Through Video Overlay Exploratory Reel

## Preregistration

Goal: create review/demo videos that visualize the same routing-budget policy
used by the real-clip appendix, while keeping C-PERSIST, C-VISION, and C-STREAM
visually separated from the per-frame orange routing overlay.

Acceptance checks:

- reuse/fresh blocks come from the existing Qwen routing-budget policy;
- stale-by-age blocks are rendered as fresh, not reused;
- the first frame is labeled as an unscored reference frame;
- C-PERSIST, C-VISION, and C-STREAM labels state whether they are reproduced
  here or hypotheses;
- clean and overlay phases keep the same video geometry.

## Execution

Implemented `scripts/render_codec_through_video_overlays.py`.

Rendered three checked benchmark windows:

- TOMATO `0298-00`, `0.00-2.00s`;
- VideoMME `380`, `206.39-207.89s`;
- VideoMME `267`, `0.00-1.00s`.

Outputs are written under:

- `research/experiments/2026/artifacts/codec_through_video_overlays_exploratory/`;
- `research/experiments/2026/artifacts/codec_through_video_overlays_exploratory_4fps/`.

The main review artifact is `all_clips_cinematic_reel.mp4`: a title card,
then the three clips back-to-back, with each clip shown clean first and then
slowed with the routing overlay and separated mechanism lanes.

## Result

The renderer now uses age-filtered `static_reused_boxes` and
`shifted_reused_boxes`; raw static/shifted blocks that age out are counted in
the fresh budget. First frames show "no prior frame" rather than a fabricated
0/100 budget. C-STREAM is shown as a stable candidate/hypothesis lane instead
of being driven by the current routing ratio.

The 12 fps reel is the primary artifact. The 4 fps render is explicitly labeled
as resampled planner cadence for inspection.

## Interpretation

This is a communication artifact, not a new paper claim. The orange video
overlay is reproduced-here routing-budget evidence. C-PERSIST and C-VISION
lanes summarize reproduced-here paper results with separate denominators.
C-STREAM is shown as a candidate bridge/hypothesis.

