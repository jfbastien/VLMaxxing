# Phase 1.55F-stage-timing — Adaptive-vs-Fixed Timing Attribution (PREREG)

## Question

Why does adaptive C-PERSIST beat fixed K=1 on speed while preserving the same
paired answer identity on the short tranche?

## Hypothesis

Adaptive Q2=K1/Q3=K0 with `q3_cache_source=post_q2_repaired` avoids the Q3
re-prefill work that fixed K=1 still pays. The measurable signature is a much
smaller Q3 tail prompt and lower Q3 elapsed time in the existing 1.55F artifacts.

## Inputs

- Adaptive: `phase1_55F_q3_post_q2_state/session_k1_n7.jsonl`
- Fixed K=1: `phase1_55D_selective_reprefill_v2/session_k1_n7.jsonl`

No MLX generation is run. This is analysis-only.

## Gates

- H1-mechanism: fixed-K1 Q3 median elapsed / adaptive Q3 median elapsed >= 5x.
- H2-tail-work: adaptive Q3 median tail prompt tokens are lower than fixed K=1.

## Interpretation

If both gates hold, the paper can attribute adaptive's extra speedup to Q3
re-prefill avoidance rather than to a vague implementation artifact. This does
not create a new fidelity claim; it explains an already-landed fidelity result.
