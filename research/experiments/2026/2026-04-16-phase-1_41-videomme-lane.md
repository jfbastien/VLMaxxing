# Phase 1.41: VideoMME Lane (Breadth Gate)

## Preregistration

Objective:

- stand up a local VideoMME evaluation lane on Qwen 2.5-VL-7B MLX
  at 32 frames per video, duration-stratified (short/medium/long),
  using the same benchmark runner infrastructure as TOMATO/MVBench.
- run both dense-only baselines and the current cached winner
  (`max_abs(8,32) static+shifted age=4`) on a dev + holdout split.
- this is claim #8 in `paper/claim-matrix.md` — required for paper
  venue readiness per the revised whitepaper and codex reviews. Per
  round-17 one-paper reframe, VideoMME is also the benchmark that
  Lane B (Gemma big-numbers, phase 1.51/1.52) targets for its
  headline result.

Claim register targets:

- `WP-2.7` (VideoMME evaluation)

Reproduction mode:

- generalized benchmark; first local VideoMME results on our stack.

Track: A

Gating: runs after phase 1.20 TOMATO N=30 completes. VideoMME is
breadth validation, not mechanism diagnosis — it gates the paper but
doesn't inform the planner design.

Hypotheses:

- **H1 (cached = dense on Qwen)**: sam reports 100% byte-identical
  agreement on 300 VideoMME questions at 32 frames on Qwen 2.5-VL-7B.
  On our stack with the same default thresholds (STATIC < 3,
  SHIFTED < 8), cached accuracy should match dense accuracy within
  0.5pp on the local evaluation.
- **H2 (reuse ratio varies by content)**: sam reports 52% average
  token reuse on VideoMME (lower than TOMATO's 83% because content
  is more dynamic). Local reuse should be in a similar range.
- **H3 (our planner policy adds no regression)**: `max_abs(8,32)
  age=4` should NOT degrade VideoMME accuracy vs the default
  threshold policy, because VideoMME is mostly short-clip multiple-
  choice and our policy only changes the change-detection threshold,
  not the semantic caching mechanism.

Acceptance band:

- H1: cached accuracy matches dense within 1pp on a 100-item eval
- H2: mean token reuse between 40% and 70%
- H3: planner policy accuracy ≥ default policy accuracy − 1pp

Rejection band:

- H1: cached accuracy < dense − 3pp → something is broken on our
  VideoMME integration (parse failures, video loading, etc.)

Inconclusive:

- VideoMME videos fail to download or decode on M3 Air.

## Operational plan (from sam's infrastructure)

Sam's operational path for VideoMME:

1. Duration-stratified evaluation: 100 items per duration bucket
   (short < 2 min, medium 4–15 min, long 30–60 min) = 300 total.
   For our initial lane, use a smaller stratified sample (e.g., 20
   per bucket = 60 items) for dev, 60 for holdout.
2. Frame extraction at 32 frames using uniform sampling (same as our
   existing `np.linspace` approach).
3. VideoMME parquet loading: sam uses a custom loader; we need to
   adapt our `run_benchmark_track_a.py` with a VideoMME loader
   parallel to the TOMATO/MVBench loaders.

## Code changes needed

1. Add `videomme` as a benchmark option in `run_benchmark_track_a.py`
2. Write `_load_videomme_items()` and `_load_videomme_items_by_id()`
3. Write dev/holdout manifests
4. Write a frame-budget-baseline pass at {8, 16, 32} frames

## Execution

**2026-04-17: loader + manifests landed.** VideoMME integration is in
place as part of the Gemma lane (phase 1.51R) build-out:
`research/benchmark_manifests/videomme_dev_v1.toml` (30 items,
10/bucket balanced short/medium/long), plus subset and single-item
manifests. Dev corpus is exercised daily by 1.51R Stage 1–5 runs on
Gemma 4-E4B. **Qwen 7B VideoMME N=30 still pending** — the Track A
path is the remaining runtime-only gap for claim #8.

Deferred reasons: (1) Gemma big-numbers lane is the SOTA-facing
content per the one-paper reframe; Qwen VideoMME breadth is claim-8
evidence but not headline. (2) Prioritized 1.51R Stage 5 anchor
ablation and Phase 1.51V (vision-tower pruning) because they unlock
the big-number claim (#11) that 1.41 VideoMME Qwen cannot unlock on
its own.

## Result

Partial: manifest infrastructure + Gemma 1.51R Stage 1–5 evidence
(Gemma dense accuracy ~0.40 on dev n=30, matches Sam's relative band
on 4B-class model). Qwen Track A result pending.

## Interpretation

Pending.

## Links

- [paper/claim-matrix.md](../../../paper/claim-matrix.md) claim #8
- [docs/benchmark-taxonomy.md](../../../docs/benchmark-taxonomy.md) VideoMME entry
- [seed/whitepaper/whitepaper-revised-2026-04-16.md](../../../seed/whitepaper/whitepaper-revised-2026-04-16.md) §2.7
