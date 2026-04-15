# Phase 1.31: Failure Predictor (Mechanistic Modeling)

## Preregistration

Objective:

- fit a small, interpretable model predicting cached-vs-dense
  disagreement at the item level, from features already recorded in
  the benchmark summaries.
- produce a paper figure: "here's when cached fails, and here's the
  feature that predicts it best."

Claim register targets:

- Paper claim 2: "naive mean-diff is too blunt" — a predictor shows
  which failure mechanism dominates.
- Paper claim 3: "repair-mechanism targeting" — the predictor motivates
  which aspect to attack next (sticky-dynamic, projector-group, etc.)

Reproduction mode:

- mechanistic analysis; CPU-only; no new benchmark runs.

Track: A methodology.

Gating: runs any time; CPU-only; does not contend with GPU-bound
phases.

Hypotheses:

- **H1 (critical-span reuse predicts disagreement)**: if a cached
  policy reuses blocks in the active-region intersection on the
  "critical" frames (e.g., the frames where dense dwells on the
  answer cue), disagreement is ≥ 3× more likely than on items where
  critical-span reuse is low.
- **H2 (max-age binding predicts failure)**: items where the
  cached policy hits `max_age` on any active-region block are more
  likely to disagree than items where max_age is never reached.
- **H3 (dense answer margin predicts failure)**: items where dense's
  top-2 logprob gap is small (≤ 0.1) are more likely to flip under
  cached than items with large margin (≥ 0.3).

Acceptance band:

- H1: contingency-table odds ratio ≥ 3 (p < 0.05 McNemar style on
  all pooled items across TOMATO + MVBench dev/holdout runs).
- H2: odds ratio ≥ 2.
- H3: odds ratio ≥ 2.

Rejection band:

- odds ratio ≤ 1.5 for all three; the features don't carry signal
  and we need better instrumentation (e.g., per-frame attention
  traces).

Inconclusive:

- too few disagreeing items (< 10 pooled) for meaningful contingency
  test.

Features to compute per item (all from existing summaries + jsonls):

1. `reuse_active_mean` — the policy's average active reuse
2. `max_age_hit_flag` — did any block hit max_age?
3. `dense_top2_gap` — from phase 1.13 option logprobs (if present;
   else skip this feature until 1.13 lands)
4. `active_area_fraction` — fraction of pixels in active region
5. `first_frame_gap` — does the answer evidence appear in frame 1?
   (for TOMATO direction items, first frame is critical)
6. `pair_reuse_std` — variance of per-pair reuse across the clip
   (high variance = mixed-motion clip)

## Code change

New script `scripts/failure_predictor.py`:

- Loads phase 1.10, 1.11, 1.12 jsonls.
- Joins cached vs dense per item, computes the 6 features.
- Fits logistic regression `disagree ~ features` (statsmodels /
  scipy).
- Reports odds ratios + 95% CIs per feature.
- Writes `phase1_31_failure_predictor.json`.

## Execution

Pending.

## Result

Pending.

## Interpretation

Pending.

## Links

- [phase 1.10 TOMATO motion dev](2026-04-14-phase-1_10-planner-grid-tomato-motion-dev.md)
- [phase 1.11 MVBench motion dev](2026-04-14-phase-1_11-planner-grid-mvbench-motion-dev.md)
- [phase 1.12 holdout eval](2026-04-14-phase-1_12-grid-winners-holdout.md)
- [phase 1.13 logprob stratification](2026-04-14-phase-1_13-logprob-stratification.md)
