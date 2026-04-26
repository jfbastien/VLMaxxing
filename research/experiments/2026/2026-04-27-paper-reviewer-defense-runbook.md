---
date: 2026-04-27
status: staged; not yet run
related:
  - research/experiments/2026/2026-04-27-adaptive-mechanism-queue-findings.md
  - research/experiments/2026/2026-04-27-phase-1_62D-lowfps-dense-baseline-prereg.md
  - research/experiments/2026/2026-04-27-phase-1_55F-16f-adaptive-prereg.md
  - research/experiments/2026/2026-04-27-phase-1_57G-gemma-matched-duration-drift-prereg.md
---

# Reviewer-Defense Queue

## Purpose

The adaptive-mechanism queue made C-PERSIST strong enough for the paper
headline and closed the current 1.30 admission lane. The next queue should not
keep sweeping the already-closed 1.30 family. It should answer the highest
value reviewer objections that remain cheap and scientifically clean:

1. Is a simple low-FPS dense baseline enough?
2. Does C-VISION skip real vision-tower work, not only preserve answers?
3. Does adaptive C-PERSIST have a 16f interpolation point?
4. Does Gemma show matched duration-wise feature-drift geometry?

## Queue

Run:

```bash
./.venv/bin/python scripts/run_paper_reviewer_defense_queue.py --auto-commit
```

Dry-run:

```bash
./.venv/bin/python scripts/run_paper_reviewer_defense_queue.py --dry-run
```

The queue uses the same operational pattern as the closeout queues:

- CPU-only preflight first
- per-step timeout
- continue-on-failure unless `--strict` is set
- auto-commit only the step artifact directory plus queue status / preflight
- one MLX approval at launch is enough for the whole queue

## Step 1 — 1.63 Track B Compact Qwen ViT Execution

Runtime estimate: `~2.8-3.2 h`.

What it answers: whether the landed C-VISION Qwen policy actually skips
vision-tower wall time when run through the compact post-layer execution path.
This is a Track B measurement, not a Track A substitution result.

Interpretation:

- fidelity PASS + vision reduction PASS + E2E positive + ceiling explained:
  C-VISION gets a measured skipped-work result at the local vision-only
  arithmetic ceiling.
- fidelity PASS + vision reduction PASS but no E2E win: real sparse vision
  execution exists, but overhead / decode / prefill dominance absorbs the win.
- fidelity FAIL: the earlier semantic-safe cell did not reproduce in this
  fresh Track B pair.

## Step 2 — 1.62D Low-FPS Dense Baseline

Runtime estimate: `~3.5-5.5 h`.

What it answers: whether dense 4f or 2f inference over the exact 1.30W
session protocol is competitive with the 8f cold reference.

Interpretation:

- 4f delta ≥ -0.05: low-FPS dense is a serious baseline; the paper needs a
  caveat.
- 4f delta ≤ -0.10: low-FPS dense is rejected as a replacement for the 8f
  reference on this session protocol.
- otherwise: ambiguous; report CI and duration slices.

## Step 3 — 1.55F-16f Adaptive Interpolation

Runtime estimate: `~35-60 min`.

What it answers: whether the adaptive post-Q2-state C-PERSIST policy is stable
at 16f, between the landed 20f and 32f short cells.

Interpretation:

- 0/21 exact-match pass: the adaptive curve has another clean point.
- bounded drift but not exact: still a fidelity PASS but not an exact-frontier
  extension.
- fidelity/pathology fail: non-monotone frame-budget boundary; this is a real
  mechanism result and should be reported, not hidden.

## Step 4 — 1.57G Gemma Matched-Duration Drift

Runtime estimate: `~2-6 h`.

What it answers: whether Gemma's visual-feature drift geometry across
short/medium/long VideoMME buckets matches the Qwen geometry enough to support
a two-architecture mechanism explanation.

Interpretation:

- matched geometry: strengthens C-VISION as a cross-architecture mechanism
  story.
- high Gemma STATIC cosine but answer drift: feature cosine alone is not
  sufficient; the explanation should shift toward architecture-conditioned
  readout / attention topology.

## Deferred

These are real science gaps but should not be smuggled into this queue:

- failure predictor / logit-margin model: high explanatory value; needs a
  separate logprob-rerun plan or a careful inventory of existing logprob
  artifacts.
- temporal placement ablations and event-window oracle: require explicit
  frame-index selection support.
- screenshot polling and SimpleStream-like recency baselines: useful for a
  systems submission, but VideoMME lacks query timestamps, so the fairness
  protocol must be reviewed before coding.
- 1.58 bf16 control: larger-memory machine only.
