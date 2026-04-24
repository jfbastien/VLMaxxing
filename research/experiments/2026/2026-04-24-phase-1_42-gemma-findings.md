# Phase 1.42 — Gemma 4 architecture-topology lane (FINDINGS)

**Date:** 2026-04-24.
**Status:** complete on the preregistered holdout pair.

## Summary

Gemma 4-E4B-IT-4bit now has the full second-architecture holdout readout
for claim #7 under the transferred Planner 2.0 base policy
(`MAX_ABS`, static+shifted, `age=4`) and the corrected cached-feature
geometry (`133` pooled cached tokens/frame on the live 560×560 path).

The result is **split, not binary**:

- **TOMATO motion holdout N=30:** PASS on the preregistered fidelity
  gate. Dense and cached accuracy both finish at `0.2667` (`8/30`),
  strict agreement is `0.9333` (`28/30`), and parse failures are `0`.
- **MVBench motion holdout N=30:** FAIL on the preregistered fidelity
  gate. Dense and cached accuracy both finish at `0.2000` (`6/30`), but
  strict agreement is only `0.7333` (`22/30`), below the `0.85` gate.

So Gemma does **not** support the strongest version of
"all-global attention gives high-fidelity approximate reuse" across both
benchmarks. What it does support is a more precise claim:

> Reuse fidelity is architecture-conditioned **and benchmark-conditioned**.
> On Gemma, cached reuse can preserve aggregate accuracy exactly while
> answer identity drifts materially more than on Qwen.

This is scientifically useful because it converts claim #7 from a
mechanism-only hypothesis into a measured second-architecture boundary.

## Artifacts

- TOMATO:
  `research/experiments/2026/artifacts/phase1_42_gemma_tomato_motion_holdout_v2_mc_cached/`
- MVBench:
  `research/experiments/2026/artifacts/phase1_42_gemma_mvbench_motion_holdout_v2_mc_cached/`
- Prereg + execution notes:
  `research/experiments/2026/2026-04-17-phase-1_42-gemma-architecture-topology-prereg.md`

## Protocol note — why MC scoring is the right path here

Gemma's free-form generation path is not a valid one-letter evaluator on
the local benchmark prompt format. On the smoke item, dense and cached
prefill logits matched exactly while free-form text still diverged into
parse-hostile generations. That is an evaluation-path problem, not a
reuse-fidelity problem.

Therefore the holdout pair was run with explicit multiple-choice scoring
(`--answer-mode option_logprobs`). This preserves the scientific target:
compare dense versus cached answer preference under the same options,
without conflating reuse fidelity with output-format obedience.

## TOMATO N=30

Headline:

- `dense_accuracy = 0.2667`
- `cached_accuracy = 0.2667`
- `agreement = 0.9333`
- `reuse_ratio_mean_active = 0.6616`
- parse failures `= 0`

The two answer mismatches were:

- `tomato:direction:0224-05`
- `tomato:direction:0227-04`

Both mismatches occur inside the `direction` subgroup. Rotation and
shape-trend items stayed aligned under this policy. This is the
cleanest evidence that Gemma can support transferred reuse on at least
one motion benchmark without any aggregate accuracy penalty.

## MVBench N=30

Headline:

- `dense_accuracy = 0.2000`
- `cached_accuracy = 0.2000`
- `agreement = 0.7333`
- `reuse_ratio_mean_active = 0.5844`
- parse failures `= 0`

There are `8` mismatches total, spread across four groups rather than
localized to one pathology:

- `action_localization`: 2
- `fine_grained_action`: 2
- `object_interaction`: 2
- `moving_direction`: 2

Mismatch IDs:

- `mvbench:action_localization:4`
- `mvbench:action_localization:7`
- `mvbench:fine_grained_action:33`
- `mvbench:fine_grained_action:7`
- `mvbench:object_interaction:96`
- `mvbench:object_interaction:6`
- `mvbench:moving_direction:32`
- `mvbench:moving_direction:125`

That distribution matters. This is **not** one brittle subgroup
breaking the whole benchmark. The answer drift is broad enough that the
high-fidelity interpretation fails on MVBench even though aggregate
accuracy remains tied.

## Interpretation

The architecture-spectrum story now has three local pieces:

1. **Qwen** already shows very high answer stability under reuse on the
   main Planner 2.0 cells.
2. **Gemma 1.57** showed higher adjacent-frame feature cosine than Qwen
   on VideoMME long dev (`0.769 / 0.794 / 0.807` vs
   `0.545 / 0.582 / 0.592`), proving the vision features themselves are
   not "less stable" in a simple cosine sense.
3. **Gemma 1.42** now shows that higher local feature similarity does
   **not** imply Qwen-like answer-level stability. TOMATO stays in the
   high-fidelity regime; MVBench does not.

The likely lesson is that answer-level reuse fidelity depends on more
than adjacent-frame feature similarity. The downstream prompt/answer
manifold and the benchmark's motion-query structure matter. That is
precisely why claim #7 should be phrased as a spectrum with benchmark-
specific bounds rather than a single architecture-level label.

## Decision

- Claim #7 is **strengthened** from mechanism-only to
  second-architecture holdout evidence.
- Claim #7 is **not fully earned** as a universal "all-global =
  high-fidelity approximate" rule.
- The paper should say:
  - Qwen-family reuse can be exact or near-exact on the tested cells.
  - Gemma-family reuse is **benchmark-conditional**:
    - TOMATO: high-fidelity approximate.
    - MVBench: accuracy-preserving but not high-fidelity by strict
      agreement.

## Consequence for follow-on work

Phase C Track B dense-baseline timing for Gemma was preregistered only
if Phase B passed. Because the holdout pair is split, Gemma Track B
should be treated as **exploratory systems characterization**, not as
claim-bearing follow-through for 1.42.

The higher-value next experiments remain:

1. `1.55D v2 selective re-prefill` — fidelity recovery on the Qwen
   persistent-KV basin.
2. `1.58 bf16 KV control` — quantization-vs-attention mechanism split.
3. A broader or third-architecture claim-7 check only if it changes the
   paper materially; 1.42 already disproves the simplistic binary story.
