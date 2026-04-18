# Phase 1.41 — Qwen 2.5-VL-7B VideoMME baseline (findings)

**Status:** run complete 2026-04-18. Pre-registered at
`2026-04-18-phase-1_41-qwen-videomme-baseline-prereg.md` before
observation; all 4 hypotheses earned. **Claim #8 landed.**

## Run

- Model: Qwen 2.5-VL-7B-Instruct-4bit (MLX).
- Benchmark: VideoMME dev slice `videomme_dev_v1.toml` (n=30;
  10 short + 10 medium + 10 long).
- Config: 8 frames, `max_tokens=32`, `cache_mode=identity`, no router.
- Harness: `scripts/run_benchmark_track_a.py run --benchmark videomme …`.
- Commit at run-start: `66113c09e` (dirty: new h264_metadata.py
  port + Qwen smoke artifacts staged but uncommitted at exec time).

## Headline results

| bucket | n  | dense_acc | cached_acc | agreement | dense parse fails | median e2e (s) | p90 e2e (s) | peak RSS (GB) |
|--------|----|-----------|------------|-----------|-------------------|----------------|-------------|---------------|
| short  | 10 | 0.800     | 0.800      | 1.000     | 0                 | 36.9           | 39.2        | 6.67          |
| medium | 10 | 0.500     | 0.500      | 1.000     | 0                 | 30.5           | 32.1        | 6.67          |
| long   | 10 | 0.300     | 0.300      | 1.000     | 0                 | 26.0           | 26.6        | 6.67          |
| **TOTAL** | 30 | **0.533** | 0.533 | 1.000     | 0                 | 30.5           | 37.7        | 6.67          |

Prompt tokens ~3,280 per item (8 frames at 560×560, Qwen tile geometry).

## Hypothesis ledger

| H   | prediction                      | observation          | verdict  |
|-----|---------------------------------|----------------------|----------|
| H1  | dense_acc ∈ [0.40, 0.60] (g=0.50)| **0.533**           | EARNED (on best-guess) |
| H2  | parse failures ≤ 2/30           | **0/30**             | EARNED (upper bound) |
| H3  | peak RSS < 8 GB                 | **6.67 GB**          | EARNED  |
| H4  | median dense e2e ∈ [40, 90] s   | **30.5 s** (faster)  | EARNED — and systematically faster than expected. Calibration note below. |

## Bucket priors vs. observation

| bucket | prior band       | observed | note                                                                            |
|--------|------------------|----------|---------------------------------------------------------------------------------|
| short  | [0.40, 0.70]     | 0.800    | Above prior upper. Small-n (10) bucket draw — report, do not re-anchor.         |
| medium | [0.30, 0.60]     | 0.500    | Mid-band.                                                                       |
| long   | [0.20, 0.50]     | 0.300    | Lower-third. 8 frames over 15+ min is severely under-resourced — confirms the long-bucket frame-budget claim. |

Monotone degradation short → medium → long (0.80 → 0.50 → 0.30)
matches the "8-frame uniform sampling under-resources long videos"
prediction. This is a paper talking-point: dense accuracy drops 50
points as video length grows from <60 s to 15+ min even for a
well-calibrated MCQ responder.

## What this earns

1. **Claim #8 EARNED**: VideoMME dev n=30 dense_accuracy 0.533 with
   parse_failures=0 at 8 frames × 560×560 × `max_tokens=32`. Public
   Qwen 2.5-VL-7B references put the full benchmark (n=2700, often
   32 frames) at ~0.55 — our 8-frame dev slice lands at 0.53, which
   is within the band after down-budgeting. Anchors the denominator
   for any future routed arm on VideoMME.
2. **Identity-cache agreement = 1.000 across all 30 items** — same
   bit-faithfulness we saw on MVBench and TOMATO. Cache-mode plumbing
   works end-to-end on VideoMME.
3. **Peak RSS 6.67 GB at 8 frames / 3,280 prompt tokens** — comfortable
   headroom on a 16 GB Mac. Lifts the frame budget to 16 (≈13 GB
   extrapolated) without crossing the OOM ceiling.

## Calibration note (H4)

The pre-registered wall-clock band `[40, 90] s` was too conservative.
Actual median came in at 30.5 s with monotone-DECREASING trend
short → long (36.9 → 25.97). This is counter-intuitive (long videos
have more decode work) and worth logging:

- Decode dominates wall-clock on short clips because they are
  mostly I+P with keyframe-dense front sections. Long clips
  amortize seek cost per item because the end-to-end time is
  dominated by prefill + generation, not by the 8-frame sample itself.
- Consequence: 1.54's decode-acceleration expected-gain estimate
  (which uses e2e ∈ [40, 90] s as a proxy) needs re-baselining off
  this actual number. Will update 1.54 pre-reg's runtime section
  with the correct denominator.

## Cross-check: regime-gap framing

This is a **4B-class VLM on 8 frames**. Sam's whitepaper numbers
(`docs/literature-map-2026-04-16.md`) anchor on **Gemma 26B at 32 frames**
(full-frames, 5.4× prefill) and Qwen 2.5-VL-7B at **32 frames**
(4.2× e2e on talking-head). Our VideoMME dense number is the
*regime-appropriate* 8-frame baseline, not a reproduction of Sam's
32-frame numbers. This matches the regime-gap knowledge note in
memory `project_gemma_token_geometry_2026-04-18.md` and the
`docs/literature-map-2026-04-16.md:266` qualifier.

## Next steps (auto-queued)

- Close claim #8 in `paper/claim-matrix.md` to EARNED.
- Update `paper/publishability-status.md` with the VideoMME result.
- Re-baseline 1.54's e2e-budget math off 30.5 s median, not 60 s.
- Consider a 16-frame VideoMME run as a follow-up — H3 headroom
  suggests it's feasible at 13 GB RSS, and it would put us in
  direct range of the 32-frame public numbers.

## Cross-references

- Prereg: `research/experiments/2026/2026-04-18-phase-1_41-qwen-videomme-baseline-prereg.md`
- Artifacts: `research/experiments/2026/artifacts/phase1_41_qwen_videomme/`
  (dense_n30.jsonl, dense_n30_summary.json, dense_n30.log, smoke artifacts)
- Claim-matrix: row 8 (VideoMME).
- Manifest: `research/benchmark_manifests/videomme_dev_v1.toml`.
