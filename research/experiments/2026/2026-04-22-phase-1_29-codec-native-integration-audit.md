---
phase: 1.29
date: 2026-04-22
parent: research/experiments/2026/2026-04-19-phase-1_29-codec-native-integration-design.md
prior:
  - research/experiments/2026/artifacts/phase1_57/qwen_8f_dev30.json
status: BLOCKED — semantic-gap and pilot-cost both unfavorable. Full harness integration (Stages A/B/C per design note) remains ~3-5h; **pre-integration pilot to validate that codec labels are usable as a drop-in for pixel-diff did not complete within the autonomous-session budget** because native-rate H.264 metadata extraction on long VideoMME clips is dominated by frame-count + full-span decoding. The open question "does codec-native OR-aggregated across sparse-sampling span agree with pixel-diff to ±10pp per class?" is unanswered. Defer full integration pending a scoped replacement pilot (see "Unblock paths").
tracking: autonomous session 2026-04-21/22 dynamic-loop
---

# 1.29 Codec-native BlockStatistic integration — pre-integration audit (BLOCKED)

## Headline

The 1.29 prereg (task #98 2026-04-20) and the integration design note (2026-04-19) set up a 3-stage code path to land `BlockStatistic.CODEC_NATIVE` alongside the four existing pixel-domain statistics. The design note estimates ~5h total for Stages A (data path) + B (planner dispatch) + C (CLI wiring) + harness regression coverage.

Before spending the implementation budget, this audit attempted a **pre-integration pilot** to verify that codec-native labels — OR-aggregated across the native-rate span between sparse-sampled frames — agree with the pixel-diff classification from Phase 1.57 to within ±10pp per class on VideoMME. A 5-item stratified pilot was run against the `artifacts/phase1_57/qwen_8f_dev30.json` reference distribution:

```
8f VideoMME dev30 pixel-diff class shares (summed n_pairs across 30 items):
  STATIC  = 0.436
  SHIFTED = 0.026
  NOVEL   = 0.538
```

The pilot stopped before completion: for long-bucket VideoMME items, `_count_frames` over the full clip + per-frame H.264 metadata extraction takes long enough that 5 items × 3 buckets × full native-rate decode ran past the session's foreground budget. No per-item codec-vs-pixel comparison numbers are produced here.

## Why pilot-cost matters

The design note (stage A) calls for a **per-sample codec precompute** during `_prepare_sample`: extract H.264 metadata once per video, classify, cache, reuse across arms. For the benchmark harness this is "one-time" cost per item — but "one-time" means decoding the entire video (all native frames, not just the 8 sampled), extracting MV/CBF, and OR-aggregating across span-between-sampled-indices to produce the 7 inter-frame-pair labels the sparse-sampling regime needs.

On VideoMME long-bucket clips (600-1800 s, 30 fps → 18k–54k native frames per clip), the extract cost is the dominant term regardless of Stage-B/C design. The pilot's timeout on 5 items is the **direct evidence** that the full harness run across Qwen 8f VideoMME n=30 (task #175) would spend most of its compute inside `H264MetadataExtractor.iter_frames()`, not inside the VLM. A runtime that the prereg estimates at ~1-2 h may in practice extend to multi-hour territory driven by video-decode of long clips at native rate.

## Semantic-gap concern (motivated, unverified)

Codec H.264 metadata is classified per-MB on **native-rate inter-frame relations** (here `classify_blocks_h264`: skip → STATIC, intra|cbf → NOVEL, else SHIFTED). At 30 fps, same-scene inter-frames between a camera that barely moves are dominated by skip-MBs — a typical codec-STATIC share on a static-dominant clip is much higher than the 0.436 STATIC we see at sparse 8f pixel-diff.

When we sparse-sample 8 frames from a 600-s clip, adjacent sampled frames are ~75 s apart; **OR-aggregating ~2250 native-rate labels** to produce one "sparse-pair" label is a conservative operation that should lift the label toward NOVEL (max over span, NOVEL=2 > SHIFTED=1 > STATIC=0). The question is whether the result is distributionally close to pixel-diff's 0.436 / 0.026 / 0.538 — or whether the codec OR-aggregate lands in a different regime (e.g., 0.05 / 0.02 / 0.93) because any single scene cut within the ~75-second span locks NOVEL.

Without the pilot numbers we cannot discriminate. The **a-priori expectation** (inferred from the pre-release source Table 1 and native-rate codec-STATIC rates reported there) is that the distributions diverge by >10pp per class on long-bucket items, i.e. the gap is real. But this is a prior, not a measurement.

## Recommendation

Mark 1.29 **deferred, not abandoned**. Full Stages A/B/C harness integration is premature until we have at least one of:

- **Unblock path A** — **cheap pilot** on a small short-bucket-only subset (e.g., 5 items, all short-bucket, all < 60 s). Native-rate extract on short clips is minutes not hours; a completing pilot produces the codec-vs-pixel per-class Δ numbers needed to gate full integration. ~30-60 min compute + ~15 min script work. **This is the action.**
- **Unblock path B** — skip the OR-aggregation question entirely by running the scale-out-like **native-rate streaming protocol** (priority.md should-do #4) instead of retrofitting codec labels into a sparse-sampled pixel-domain planner. Aligns the codec signal with the protocol it was designed for, but requires its own prereg + ~90-min run.
- **Unblock path C** — hand-verify a single pathological long clip (e.g., `videomme:long:669-1`, our highest pixel-diff shifted_fraction at 0.108 from the 1.60 scroll/pan audit): count codec STATIC/SHIFTED/NOVEL at native rate, then after OR-aggregation to 7 sparse pairs, compare to 1.57's `class_counts` for that item. One completed datapoint tells us whether the gap is 5pp, 20pp, or 50pp.

The `paper/priority.md` should-do #8 ("1.29 local codec-native benchmark slice") remains the right north star; this audit reports that **the slice is one cheap short-bucket pilot away from the implementation-go/no-go decision**, not one harness-integration-sprint away.

## What this audit does NOT claim

- We do **not** claim the pixel-diff vs codec-native signals will diverge. We claim the measurement to answer that was not completed.
- We do **not** claim `H264MetadataExtractor` is broken. It works; it's just slow on long-bucket inputs and that cost compounds through the harness.
- We do **not** recommend abandoning codec-native. the pre-release source uses it to justify the 5-300× ViT headline; any claim we make about local evidence must eventually land on a codec-native run, either via Stage A/B/C harness wiring OR via a streaming-protocol reproduction.

## Claim-matrix / priority edits required

- `paper/priority.md` should-do #8 status line: update from "blocker is harness wire-up" to "blocker is pilot validation; 2026-04-22 full-bucket pilot exceeded session budget, short-bucket pilot is the cheap unblock".
- Registry / experiments 1.29 row: add line "pre-integration audit 2026-04-22 — harness-cost on long-bucket VideoMME exceeds autonomous-session budget; semantic gap between native-rate codec and sparse-8f pixel-diff unverified; short-bucket pilot queued".

## Non-goals

- **No Stage A/B/C implementation.** Gate on pilot first.
- **No long-bucket retry.** The extract cost is architectural; re-running produces the same outcome.
- **No redesign of the codec path.** The design note's 3-stage split is sound; only the pre-integration go/no-go is unresolved.

## What a short-bucket pilot would look like

```python
# 5 short-bucket items (< 60 s each), native-rate extract should be ~30-60 s per item.
# For each: compute per-item codec OR-aggregated STATIC/SHIFTED/NOVEL fractions on 7 pairs,
# compare to artifacts/phase1_57/qwen_8f_dev30.json `class_counts` ratios.
# Gate: any-class |Δ| < 10pp on mean → proceed with Stage A/B/C.
#       any-class |Δ| ≥ 10pp → redesign (e.g. change aggregation rule or
#       signal definition from STATIC/SHIFTED/NOVEL labels to a continuous
#       codec-score that gets re-thresholded — per design-note §Stage B alt).
```

Cost: ~15 min scripting, ~30 min extract, ~5 min comparison; well under a session's budget.
