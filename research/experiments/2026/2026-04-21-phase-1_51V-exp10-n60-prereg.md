---
phase: 1.51V
date: 2026-04-21
parent: scripts/run_phase1_51V_exp10_n60.sh
prior:
  - research/experiments/2026/2026-04-21-phase-1_51V-expansion-findings.md
  - research/experiments/2026/2026-04-21-phase-1_51V-holdout-findings.md
status: prereg (EXP10 n=60 H_stack composition re-check — pooled dev+holdout)
tracking: task #152
---

# 1.51V EXP10 n=60 prereg — H_stack composition re-check (pooled dev+holdout)

## Motivation

H_stack (V-patching × novelty-pruning composition) has two n=30 landings
that straddle the 1.10× paper-reopener threshold:

| Source | Config | n | E2E (within-run, clean) | Agreement | Acc Δ | V_share |
|--------|--------|---|-------------------------|-----------|-------|---------|
| EXP10 dev (VideoMME dev v1) | V L=2 kr_V=0.50 + novelty kr=0.3 anchor=none | 30 | 1.11× | 0.63 | −0.067 | 15.2% |
| EXP16 holdout (VideoMME holdout v1) | same config | 30 | 1.064× | 0.667 | −0.033 | 8.6% |

The holdout within-run is below 1.10×; the dev within-run is above.
The V_share spread (15.2% dev / 8.6% holdout) means the two cells are
architecturally different regimes — the holdout is LLM-decode-dominated,
the dev is closer to balanced. Pooling on a combined 60-item manifest
gives a weighted-average answer that is **what the paper actually
claims** when it says "H_stack on VideoMME": performance across a
realistic item mix, not a single hand-picked split.

EXP10 n=60 is the minimal experiment that resolves the partial-reopener
ambiguity: a single paired run on the combined 60-item manifest, with
the revised thermal gate and the updated driver (post-metadata fast-path
fix, commit 4174f82).

## Hypotheses (preregistered)

Four hypotheses on the pooled 60-item pair.

**H_exp10n60_e2e (primary)**: paired sum-ratio E2E speedup ≥ **1.10×**.
Weighted-mean prediction from the two n=30 landings:
`(30 × 1.11 + 30 × 1.064) / 60 = 1.087×`. So 1.10× is a headline-
reopener threshold a touch above the naive weighted mean, intentionally
requiring that the pooled run either a) clears dev behavior AND
holdout behavior doesn't drag it down enough, or b) reveals that
concurrent thermally-clean measurement of both pools gives a better
(less outlier-contaminated) number than the n=30 halves did separately.
Report median and trimmed-mean alongside.

**H_exp10n60_thermal (process)**: under the revised calibration,
`|decode Δ| < max(0.02 × decode_ms(reference), 100 ms)`. VideoMME
decode scale is ~12000 ms (dev mix), so the 2% relative gate = 240 ms
dominates the 100 ms floor.

**H_exp10n60_agreement (secondary)**: agreement between dense and
pruned arm ≥ 0.65. Dev 0.63, holdout 0.667; a clean n=60 should land
in [0.63, 0.67].

**H_exp10n60_accuracy (secondary)**: acc Δ ∈ [−0.10, +0.05].
Weighted mean of n=30 cells: (−0.067 × 30 + −0.033 × 30) / 60 = −0.050.

## Decision matrix

| e2e | thermal | agreement | interpretation |
|-----|---------|-----------|----------------|
| ≥ 1.10× | PASS | ≥ 0.65 | H_stack **CONFIRMED** — lifts to paper-grade H_stack claim; H1 reopener earned |
| ≥ 1.10× | FAIL | ≥ 0.65 | **ADVISORY** — earned pending thermal retry; not paper-grade yet |
| [1.08×, 1.10×) | PASS | ≥ 0.65 | H_stack **PARTIAL-CONFIRMED** — ceiling-bound at ~V_share-weighted-mean; secondary paper claim as framed today |
| < 1.08× | PASS | any | H_stack **NULL** at pooled regime — close the reopener; remove from should-do list |

## Configuration

```
model-path         $GEMMA_MODEL_PATH
frame-count        8
n                  60 per arm (pooled dev + holdout)
max-tokens         32
rss-guard-mb       10000

EXP_a (reference, V-only):
  --manifest research/benchmark_manifests/videomme_combined_v1_n60.toml
  --vision-tower-layer 2 --vision-tower-keep-rate 0.50
  --anchor-arm none --keep-rate 1.0

EXP_b (H_stack V+novelty):
  --manifest research/benchmark_manifests/videomme_combined_v1_n60.toml
  --vision-tower-layer 2 --vision-tower-keep-rate 0.50
  --anchor-arm none --keep-rate 0.30
```

Reference arm runs first back-to-back (per session-3 thermal lesson:
pair immediately, reference arm cold-to-lukewarm).

Prerequisite: create `videomme_combined_v1_n60.toml` by concatenating
the 30 dev + 30 holdout item-IDs (both already exist). Deterministic
order matters for fair pairing — use dev items then holdout items in
filename-sorted order.

## Runtime

EXP15 VideoMME holdout n=30 V-patched: 1425 s (24 min).
Scaling to n=60: ~2850 s (~48 min) per arm, ~95 min total.
Single autonomous-session bucket; well under the 2-hour attention budget.

## Non-hypotheses (explicit non-goals)

- No novelty kr sweep (0.3 is the preregistered sweet spot from EXP10 dev).
- No cross-frame-scaling (only 8f).
- No 3-benchmark extension (VideoMME-only per should-do #1).
- No cross-session pairing (within-run only; cross-session thermal
  contamination has been the single biggest noise source in 1.51V).

## Dependencies (gating)

- Combined manifest creation (scripts/make_videomme_combined_v1_n60.py
  or hand-edit; trivial).
- Session 5 TOMATO rerun completion (resource-sharing: both use Metal).
  Sequential not parallel.

## Artifacts expected

- `research/benchmark_manifests/videomme_combined_v1_n60.toml` (new)
- `research/experiments/2026/artifacts/phase1_51V_exp10_n60/exp10n60_a_vonly_ref.{jsonl,log,done,_summary.json}`
- `research/experiments/2026/artifacts/phase1_51V_exp10_n60/exp10n60_b_vplus_novelty030.{jsonl,log,done,_summary.json}`
- `research/experiments/2026/artifacts/phase1_51V_exp10_n60/queue.{log,done}`
- Runner: `scripts/run_phase1_51V_exp10_n60.sh`
- Findings doc: `research/experiments/2026/2026-04-21-phase-1_51V-exp10-n60-findings.md`
