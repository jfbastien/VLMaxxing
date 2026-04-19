# Phase 1.55A-18f — Persistent-KV ramp-onset bisection (PREREG)

**Status:** preregistration, 2026-04-19. Midpoint between 16f (clean,
Δacc=0) and 20f (ramp-with-mixed-basins, Δacc=−0.381) to localize the
onset of the soft-threshold transition.

**Parents:**
- 16f findings: `2026-04-19-phase-1_55A-16f-frame-scaling-findings.md`
- 20f findings: `2026-04-19-phase-1_55A-20f-frame-scaling-findings.md`
- 24f findings: `2026-04-19-phase-1_55A-24f-frame-scaling-findings.md`
- 32f findings: `2026-04-19-phase-1_55A-32f-frame-scaling-findings.md`

## Purpose

20f established that the 16f→24f transition is a NARROW SOFT THRESHOLD
with a ramp-and-saturation shape, not a pure cliff. We have three
interior data points to place on that curve:

| Frames | Prefill | Δacc |
|---|---|---|
| 16 | ~6500 | 0.000 (clean) |
| 20 | ~8100 | −0.381 (ramp, mixed-basin) |
| 24 | ~9700 | −0.429 (saturated) |

The 16f→20f gap spans ~1.6k prefill tokens. 18f (~7.3k) is the
midpoint. Outcome sub-scenarios below discriminate threshold location
and shape.

## Hypotheses

**Protocol:** identical driver; 7 clips × 3 questions; only change is
`--frame-count 18`. Expected prefill: ~7 300 tokens.

### H1'''''  — speedup continues linear scaling

Follow-up speedup in band [**65×, 110×**]. Interpolation between 91×
(16f) and 94× (20f) gives ~92×. Prereg widened to accommodate
follow-up-median inflation if garbage generations appear (longer
gen_tokens raise median; already observed at 20f vs 16f).

### H2''''' — fidelity verdict (four alternatives)

- **H2'''''.clean (Δacc ∈ [−0.05, 0.05]):** soft threshold onset sits
  past 18f. Narrows ramp onset to [7.3k, 8.1k]. Next: 19f bisection.
- **H2'''''.early-ramp (Δacc ∈ (−0.05, −0.20]):** ramp starts before
  18f. Narrows onset to [6.5k, 7.3k]. Next: 17f bisection.
- **H2'''''.mid-ramp (Δacc ∈ (−0.20, −0.35]):** consistent with
  monotonic-smooth ramp on a 4-point curve (16/18/20/24f).
  Strengthens ramp-with-saturation interpretation.
- **H2'''''.cliff-proximal (Δacc ≤ −0.35, ≥12/14 addCriterion):**
  18f already saturated. Pushes cliff location below 7.3k; weakens
  the 20f mixed-basin interpretation (would force "20f was a
  statistical fluke") — requires re-run of 20f.

### H3''''' — prefix coverage preserved

`mean_follow_up_prefix_coverage ≥ 0.99`. Same as prior frame counts;
no reason for find_prefix_length to change.

### H4''''' — RSS stays under budget

Peak RSS ≤ 5 GB. 18f prefill is below 20f observed 3.51 GB peak.

### Failure-mode distribution (diagnostic, not H-gated)

Record per-follow-up: (a) short-`addCriterion` (saturated attractor),
(b) long-garbage (>8 gen tokens), (c) empty / malformed, (d) clean-
but-wrong-choice (2 gen tokens, non-gold answer), (e) clean-correct.
Distribution across these five basins is the mechanism signal; Δacc
alone undercounts it.

## Runtime budget

Expected wall-clock ~38 min based on 18f first-query ≈ 78 s × 21
queries × 50% overlap ≈ 2300 s.

## Decision rule

Post-run update: choose between clean / early-ramp / mid-ramp / cliff-
proximal by the H2''''' outcome. Queue next experiment on the winner:

- clean → 19f to narrow onset further, OR move to mechanism tests
- early-ramp → 17f to narrow onset further
- mid-ramp → **launch bf16 KV control at 20f** as cleanest falsifier
  of the 4-bit-KV-quantization mechanism hypothesis
- cliff-proximal → re-run 20f for reproducibility

**Strong default: if 18f mid-ramp, the frame-count sweep has done its
job. Switch to mechanism-discriminating experiments.**
