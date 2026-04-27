---
date: 2026-04-27
phase: 1.65
status: preregistered; not yet run
related:
  - research/experiments/2026/2026-04-27-adaptive-mechanism-queue-findings.md
---

# Phase 1.65 — Dense Logit-Margin Stability Predictor Scout

## Question

Can dense answer confidence predict which paired queries tolerate reuse, or are
the recent 0/n C-PERSIST drift results only descriptive?

This is an oracle-feature predictor scout. It re-scores existing paired
artifacts with the dense Qwen prompt and extracts the first-answer-letter
logprob margin. Because it requires a dense reference pass, it is not a
deployed guard. Its purpose is mechanistic: test whether paired stability has a
measurable confidence signal that can motivate future selective-verify or
recache policies.

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
  - 1.55F short adaptive PASS rows.
  - 1.55F medium adaptive PASS rows.
  - 1.55F long adaptive PASS rows.
  - 1.55F 32f adaptive PASS rows.
  - 1.55E adaptive negative rows.
  - 1.30AD cache-reuse negative rows.
  - 1.30AC cache-invalidated negative rows.
- Default sampling: deterministic balanced sample of up to 180 paired rows,
  preserving stable and drift examples. Set `PHASE1_65_MAX_ROWS=0` for full
  scoring.
- Memory guard: default `RSS_GUARD_MB=9000`.
- Runner: `scripts/run_phase1_65_logit_margin_probe.sh`.

## Gates

- **H_class_presence**: selected rows include at least one stable and one drift
  example. Otherwise no predictor can be adjudicated.
- **H_margin_signal**: AUC for high dense margin predicting paired stability
  >= 0.65.
- **H_safe_filter**: some threshold `dense_answer_margin >= tau` selects a
  predicted-stable subset with precision >= 0.95 and coverage >= 0.25.

## Interpretation

- H_margin_signal + H_safe_filter PASS: dense answer margin is a plausible
  stability predictor. The paper can say the 0/n drift cells are not merely
  descriptive; paired stability correlates with a measurable confidence signal.
- H_margin_signal PASS but H_safe_filter FAIL: margin carries signal, but not
  enough for a high-precision guard at this sample size.
- H_margin_signal FAIL: reuse stability is not explained by simple dense
  answer margin; future predictors need richer features such as cache distance,
  query type, or verifier logits.
- Any result is exploratory because the feature is dense-oracle and the sample
  is balanced rather than deployment-distribution calibrated.

## Runtime And Resources

Default local wall time is estimated at ~3-6 h for 180 sampled rows, depending
on the frame-count mix. Full scoring (`PHASE1_65_MAX_ROWS=0`) may take
substantially longer. The run is sequential and uses the Qwen 7B 4-bit
checkpoint under the same 9 GB RSS policy as prior queues.
