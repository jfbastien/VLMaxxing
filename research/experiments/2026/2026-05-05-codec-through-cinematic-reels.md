# 2026-05-05 Codec-Through Cinematic Reels

## Preregistration

Goal: produce review-only video reels that communicate the Qwen routing-budget
visualization and paper-level anti-recomputation claims without changing the
paper build path.

Acceptance criteria:

- Orange block overlays appear only on real clip frames and mean Qwen routing
  fresh visual evidence.
- First frames are treated as unscored reference frames.
- C-PERSIST numbers are labeled as paper-level results, not per-clip timing.
- Rewind and slowdown reuse rendered/display frames; they do not imply new
  planner decisions.
- The primary teaser uses a stable video stage and evidence console rather than
  teleporting between slide-like scenes.

## Execution

Added `scripts/render_codec_through_cinematic_reels.py` to render exploratory
MP4 variants from the same three checked windows used by the paper appendix:

- TOMATO 0298-00, high-reuse routing example.
- VideoMME 380, visual anchor.
- VideoMME 267, lower-reuse boundary.

The current primary artifact is:

```text
research/experiments/2026/artifacts/codec_through_cinematic_reels_exploratory/anchored_lure_cut.mp4
```

The scored audio experiment is:

```text
research/experiments/2026/artifacts/codec_through_cinematic_reels_exploratory/anchored_lure_cut_scored.mp4
```

The latest pass splits the work into separate communication products:

- `anchored_lure_cut`: simplified fixed-stage teaser with title first, three
  real windows, freeze/rewind/replay for each, exact routing overlays, a real
  dense full-frame baseline budget before each replay, frame-by-frame
  reused/fresh routing charts, an early speedup result after the first clip,
  and a generated moving-title closing probe with the same budget chart.
- `minimal_teaser_cut`: older short teaser with an additional landscape beat;
  retained for comparison.
- `title_motion_probe`: explicit synthetic probe where a generated moving
  wordmark is passed through the same planner path. It is a communication joke,
  not benchmark evidence.

The pipeline is deliberately staged:

1. **Algorithm plate generation.** Real clips are decoded/scored through the
   existing Qwen routing planner path at the audited cadence. This produces
   frame crops, transition masks, reused/fresh ratios, and stale-by-age counts.
2. **Display plate generation.** Raw viewing frames may be decoded at 24 fps
   for smoother playback, but planner decisions are still taken from the
   audited scored frames.
3. **Compositing.** The teaser renderer places raw plates, exact overlay
   plates, a real dense full-frame baseline budget, a frame-by-frame
   reused/fresh routing chart, and the speedup result into a stable stage.
   Rewind/VHS effects are presentation-only and are applied after the
   scientific plates are generated.
4. **Audio mux.** Optional synthetic audio is event-timed to title/freeze/
   rewind/replay/result beats and has no scientific meaning.

The renderer now also accepts custom windows without editing the source:

```text
uv run python scripts/render_codec_through_cinematic_reels.py \
  --variant anchored-lure \
  --video-path path/to/video.mp4 \
  --start-s 0 --end-s 2 \
  --result-mode none
```

For multiple windows, pass `--clip-manifest` with a JSON list, or an object
containing a `clips` list, where each record has `video_path`, `start_s`, and
`end_s` plus optional metadata fields. The default remains the three selected
appendix windows. Use `--result-mode paper` only when the paper-level
C-PERSIST speedup is intended to appear; use `--result-mode none` for pure
routing visualizations on arbitrary training-set windows.

## Result

The simplified anchored teaser is 1920x1080, 24 fps, about 30.5 s. The scored
variant adds review-only AAC mono audio with no scientific meaning. The older
minimal and paper-explainer cuts remain available as comparison drafts.

Representative frames were inspected for title, rewind, replay, result,
third real-window, and generated title-motion beats. The inspected frames show:

- no orange grid blocks on static title cards;
- exact orange fresh-block overlays only on real clips;
- all three real example windows included;
- dense baseline budget bars before each routing replay, with one bar per
  actual scored frame for that clip;
- frame-by-frame reused/fresh routing budget bars in the evidence console,
  with a live cursor, top/bottom fresh/reused labels, and no numeric budget
  labels;
- no paired-drift or first-query caveats in the teaser UI;
- the speedup number isolated as the result beat immediately after the first
  clip replay;
- closing title motion passed through the same planner path, clearly separate
  from benchmark evidence, with the same right-side budget visualization;
- readable rewind as a reverse-scrub visual inside the same video box.
- the title probe initially jumped too far between sparse generated frames; it
  now scores adjacent generated title frames at the same 12 fps planner
  cadence, moves more slowly, uses one moving wordmark, and ends on a clean
  title hold. The on-screen label is the viewer-facing `title motion`; the
  generated-frame caveat lives in the manifest and this note.

## Verification

```text
uv run ruff check scripts/render_codec_through_cinematic_reels.py scripts/render_codec_through_video_overlays.py
uv run python -m py_compile scripts/render_codec_through_cinematic_reels.py scripts/render_codec_through_video_overlays.py
ffprobe anchored_lure_cut_scored.mp4
uv run python scripts/render_codec_through_cinematic_reels.py --variant anchored-lure \
  --video-path data/benchmarks/tomato/videos/object/0298-00.mp4 \
  --start-s 0 --end-s 0.5 --result-mode none \
  --out-dir /tmp/codec-through-custom-video-smoke
zip -T codec_through_cinematic_reels_code_review.zip
```

## Interpretation

The simplified anchored version is a better communication artifact than the
previous text-heavy cuts because the viewer can track one stable visual
experiment: see dense full-frame input, rewind, replay with exact routing
evidence, then read one result. It remains review-only until pacing and optional
audio are approved.

The title motion probe is accurate as a generated-frame planner visualization,
but it is not benchmark evidence. It should be reviewed as a communication gag,
not as part of the empirical corpus.

## Links

- Renderer: `scripts/render_codec_through_cinematic_reels.py`
- Shared overlay helpers: `scripts/render_codec_through_video_overlays.py`
- Local render directory, intentionally ignored by git:
  `research/experiments/2026/artifacts/codec_through_cinematic_reels_exploratory/`
- Local code-review bundle for external feedback, intentionally ignored by git:
  `research/experiments/2026/artifacts/codec_through_cinematic_reels_code_review.zip`
