---
phase: 1.30V
date: 2026-04-23
parent: research/experiments/2026/2026-04-23-phase-1_30V-adaptive-vleg-prereg.md
artifacts:
  - research/experiments/2026/artifacts/phase1_30V_adaptive_vleg_q0_20260423/
status: CLOSED-NEGATIVE. Conservative fixed keep-rates did not recover the Q0 accuracy gate.
---

# Phase 1.30V adaptive V-leg diagnostic findings

## Result

The same ten Q0 items from the Phase 1.30 root-cause scout were rerun through
the 1.51V Qwen path at more conservative keep-rates:

| arm | Q0 accuracy | dense-choice agreement | effective keep-rate |
|---|---:|---:|---:|
| dense reference | 0.900 | 1.000 | 1.000 |
| L2 kr=0.50 | 0.500 | 0.400 | 0.500 |
| L2 kr=0.67 | 0.700 | 0.600 | 0.688 |
| L2 kr=0.75 | 0.700 | 0.800 | 0.750 |

Preregistered H_recover required both:

- Q0 accuracy >= 0.80
- dense-choice agreement >= 0.80

Neither new arm passes. `kr=0.75` reaches the agreement threshold but still
misses accuracy by one item.

H_budget passes mechanically for both tested arms (`mean_effective_keep_rate`
<= 0.75), but the accuracy gate is binding.

## Interpretation

The Phase 1.30 root-cause conclusion survives the rescue attempt: this is not
just `kr=0.50` being too aggressive by a small margin. On this Q0 slice, even
keeping 75% of vision tokens remains below the preregistered recovery threshold.

The practical implication is that a naive fixed-kr V leg is the wrong
composition policy for Qwen 7B session streaming. The next credible path is
adaptive admission:

- do not prune Q0 when the item is high-risk
- use a dense Q0 fallback when a cheap confidence or content heuristic flags
  sensitivity
- only apply V pruning on clips/prompts where the first-query answer is robust

This keeps C-VISION intact as a first-pass efficiency mechanism while narrowing
what can be claimed for deployment composition.

## Decision

Do not launch a full 1.30 session rerun with fixed `kr_V=0.67` or `kr_V=0.75`.
The scout failed the recovery gate. Future 1.30 composition work should be
adaptive, not another blind fixed-rate sweep.

Immediate research priority shifts back to the codec-native 1.29 replication
queue, because that has a better chance of creating a new paper-relevant bridge
without first solving adaptive V admission.
