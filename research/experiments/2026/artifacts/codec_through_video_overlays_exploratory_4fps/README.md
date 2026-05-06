# Video Overlay Artifacts

This directory contains generated 4 fps review/demo videos and thumbnails from
`scripts/render_codec_through_video_overlays.py`. The lower planner cadence is
for inspection; the experiment note distinguishes it from the primary 12 fps
render.

The rendered videos include short benchmark-derived visual windows:

- TOMATO `tomato:rotation:0298-00`, `0.00-2.00s`, from
  `data/benchmarks/tomato/videos/object/0298-00.mp4`
- VideoMME `videomme:medium:380-3`, `206.39-207.89s`, from
  `data/benchmarks/videomme/videos/2Bns2m5Bg4M.mp4`
- VideoMME `videomme:short:267-2`, `0.00-1.00s`, from
  `data/benchmarks/videomme/videos/Atf_Af1q_5w.mp4`

`video_overlay_manifest.json` records the source paths, source JSONL artifacts,
time windows, rendered outputs, and per-frame planner statistics.

The overlay graphics, captions, planner statistics, and thumbnails are
repo-generated. The underlying visual frames come from the benchmark sources
listed above.

Regenerate this directory with:

```bash
uv run python scripts/render_codec_through_video_overlays.py \
  --fps 4 \
  --out-dir research/experiments/2026/artifacts/codec_through_video_overlays_exploratory_4fps
```

Regeneration context is recorded in
`research/experiments/2026/2026-05-04-codec-through-video-overlays.md`.
Benchmark acquisition and local asset handling are documented in
`docs/benchmark-setup.md` and `docs/videomme-download-handoff.md`.
