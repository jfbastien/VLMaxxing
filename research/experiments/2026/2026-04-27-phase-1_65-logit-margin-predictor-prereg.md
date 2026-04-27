---
date: 2026-04-27
phase: 1.65
status: preregistered; not yet run
related:
  - research/experiments/2026/2026-04-27-adaptive-mechanism-queue-findings.md
---

# Phase 1.65 — Dense Logit-Margin Stability Predictor Scout

## Question

Within the closed 1.30 cache-boundary lane, does dense answer confidence
predict which paired queries drift?

This is an oracle-feature predictor scout. It re-scores existing paired
artifacts with the dense Qwen prompt and extracts the first-answer-letter
logprob margin. Because it requires a dense reference pass, it is not a
deployed guard. Its purpose is mechanistic: test whether the 1.30 drift rows
concentrate on items where the dense model is already intrinsically uncertain.

## Protocol

- Model: `Qwen2.5-VL-7B-Instruct-4bit`.
- Scorer: dense prompt, first generated-token answer-letter logprobs.
- Feature: `dense_answer_margin = top_candidate_logprob -
  second_candidate_logprob` over answer letters only.
- Letter scoring uses the maximum first-token logprob over the single-token
  encodings of `A` and ` A` (and analogously for each option letter), because
  chat-template boundaries may put the first answer letter at either
  whitespace convention.
- Sources:
  - 1.30AD cache-reuse negative rows.
  - 1.30AC cache-invalidated negative rows.
- Row scope: follow-up rows only (`q_index > 0`). Q0 rows are excluded because
  they measure admission/vision behavior, not post-Q0 cache/reuse stability.
- Excluded sources: all 1.55F/adaptive rows. Mixing 1.55F's 0/n adaptive cells
  with 1.30's drift rows would confound source/policy identity with stability.
- Validity filter: rows where the dense first-token logit argmax does not match
  the recorded dense/cold artifact choice are rejected before analysis. Their
  count is reported. This prevents the margin feature from being interpreted as
  confidence in a decision it did not actually rank first.
- Default sampling: `PHASE1_65_MAX_ROWS=0` scores all selected 1.30 rows.
  Nonzero values request a deterministic balanced subsample for debugging only.
- Split: grouped 80/20 train/test by `item_id`, class-stratified by whether the
  item has any drift row. Rows from the same item never cross the split.
- Thresholding: choose the high-margin safe-filter threshold on the train split;
  report precision/coverage on the held-out test split.
- Uncertainty: paired bootstrap by held-out `item_id` with 2000 resamples for
  the held-out AUC CI.
- Calibration: report held-out margin bins with stable/drift fractions plus a
  binary Brier score for the train-selected threshold.
- Memory guard: default `RSS_GUARD_MB=9000`.
- Runner: `scripts/run_phase1_65_logit_margin_probe.sh`.

## Gates

- **H_class_presence**: train and test splits each include at least one stable
  and one drift example. Otherwise no predictor can be adjudicated.
- **H_margin_signal**: lower 95% CI bound for held-out AUC of high dense margin
  predicting paired stability >= 0.60.
- **H_safe_filter**: the train-selected threshold `dense_answer_margin >= tau`
  has held-out precision >= 0.90 and held-out coverage >= 0.15.

## Interpretation

- H_margin_signal + H_safe_filter PASS: dense answer margin is a plausible
  within-1.30 drift predictor. The paper can say the 1.30 boundary failures
  concentrate on intrinsically uncertain items, with held-out evidence.
- H_margin_signal PASS but H_safe_filter FAIL: margin carries signal, but not
  enough for a high-precision guard at this sample size.
- H_margin_signal FAIL: reuse stability is not explained by simple dense
  answer margin; future predictors need richer features such as cache distance,
  query type, or verifier logits.
- Any result is exploratory because the feature is dense-oracle and is not a
  runtime guard. It should not be used to explain the 1.55F adaptive 0/n cells.

## Runtime And Resources

Default local wall time is estimated at ~5-8 h for full 1.30 scoring
(`PHASE1_65_MAX_ROWS=0`). The run is sequential and uses the Qwen 7B 4-bit
checkpoint under the same 9 GB RSS policy as prior queues.
