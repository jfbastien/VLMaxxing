# Phase 1.55A-20f — Persistent-KV cliff-midpoint bisection (PREREG)

**Status:** preregistration, 2026-04-19. Midpoint between 16f (clean)
and 24f (broken-saturated) to test whether the fidelity boundary is
a step-cliff or a narrow ramp.

**Parents:**
- 8f findings: `2026-04-19-phase-1_55A-persistent-kv-findings.md`
- 16f findings: `2026-04-19-phase-1_55A-16f-frame-scaling-findings.md`
- 24f findings: `2026-04-19-phase-1_55A-24f-frame-scaling-findings.md`
- 32f findings: `2026-04-19-phase-1_55A-32f-frame-scaling-findings.md`

## Purpose

24f localized the fidelity boundary to between 6.5k (16f, Δacc=0) and
9.7k (24f, Δacc=−0.429), with 24f and 32f failing identically. The
saturation signal is consistent with a threshold mechanism, but the
16f→24f transition still contains ~3.2k tokens where the failure
could be a sharp cliff, a narrow ramp, or a gradual slope. 20f
(~8.1k prefill tokens) is the geometric midpoint.

## Hypotheses

**Protocol:** identical driver; 7 clips × 3 questions; only change is
`--frame-count 20`. Expected prefill: ~8 100 tokens.

### H1'''' — speedup continues linear scaling

Follow-up speedup in band [**75×, 140×**]. Midpoint ~105×. Prereg
wide because prefill-token interpolation between 91× (16f) and 122×
(24f) gives ~105×.

### H2'''' — fidelity verdict (three alternatives)

- **H2''''.clean (Δacc ∈ [−0.05, 0.05]):** boundary between 8.1k and
  9.7k. Narrows failure onset to a narrow 1.6k-token band.
- **H2''''.cliff (Δacc ≤ −0.30, ≥12/14 addCriterion):** boundary
  between 6.5k and 8.1k. The failure saturates fast.
- **H2''''.gradient (Δacc ∈ (−0.30, −0.05), mixed failure modes):**
  partial degeneracy — the transition is a ramp, not a cliff.
  Weakens the threshold-mechanism hypothesis.

### H3'''' — prefix coverage preserved

`mean_follow_up_prefix_coverage ≥ 0.99`. Trivial; no reason for the
find_prefix_length path to change across frame counts.

### H4'''' — RSS stays under budget

Peak RSS ≤ 5 GB. 20f prefill is below the 24f/32f observed peaks.

## Runtime budget

Expected wall-clock ~42 min based on 20f first-query ≈ 85 s × 21
queries × 50% overlap ≈ 2500 s.

## Decision rule

Post-run update: choose between clean / cliff / gradient by the H2''''
outcome. Queue next experiment on the winner:

- clean → 22f (~8.9k) to narrow further
- cliff → 18f (~7.3k) to narrow further
- gradient → 18f (if partial degeneracy is also observed there) or
  mechanism tests (bf16 KV, RoPE probe)
