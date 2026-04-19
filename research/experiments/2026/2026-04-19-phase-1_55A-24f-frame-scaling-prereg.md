# Phase 1.55A-24f — Persistent-KV safe-regime boundary bisection (PREREG)

**Status:** preregistration, 2026-04-19. Bisects the safe-regime
boundary uncovered by the 8f/16f/32f scaling series.

**Parents:**
- 8f findings: `2026-04-19-phase-1_55A-persistent-kv-findings.md`
- 16f findings: `2026-04-19-phase-1_55A-16f-frame-scaling-findings.md`
- 32f findings: `2026-04-19-phase-1_55A-32f-frame-scaling-findings.md`

## Purpose

At 16f (~6.5k prefill tokens) all four H' earn cleanly with Δacc = 0.
At 32f (~13k prefill tokens) the cache-reuse path degenerates into a
literal-token artifact (`addCriterion`), rejecting H2'' by Δ = −0.429
while H1''/H3''/H4'' continue to earn. **Somewhere between 6.5k and
13k prefill tokens, cache-reuse fidelity transitions from clean to
broken on Qwen 2.5-VL-7B-Instruct-4bit.**

24f (~9.7k prefill tokens) is the geometric bisection point. The
answer is most informative to:

- **Paper scope:** can the "safe prefill budget" claim be sharpened
  from "≤16f" to something tighter like "≤9.7k tokens"?
- **Mechanism:** a sharp cliff at 24f favours a threshold-like
  mechanism (fixed quantization budget, position-encoding range); a
  graceful slope favours accumulating drift.

## Hypotheses

**Protocol:** identical to 1.55A 8f/16f/32f (driver, manifest, 7
clips × 3 questions, session + baseline). Only change: `--frame-count 24`.

Expected prefill at 24f: ~9 700 tokens (linearly interpolated from
the 6 500 / 12 920 token measurements at 16f / 32f).

### H1''' — speedup continues linear scaling

**Prediction.** Follow-up speedup in band [**95×, 180×**]. Midpoint
~125× ≈ geometric mean of 16f and 32f values. Lower bound allows for
the 32f sub-linearity to persist (16→32 ratio was 1.65× vs 1.91×
prefill-time ratio). Upper bound reflects the super-linear first-
query scaling observed at 32f.

**Falsifies mechanism if:** speedup < 95× — would indicate a non-
prefill cost floor saturating.

### H2''' — accuracy bisection

Three mutually exclusive sub-hypotheses (we pick the closest match):

- **H2'''.sharp** — Δacc ∈ [−0.05, 0.05]. Boundary sits past 24f
  (closer to 32f). Safe budget is approximately 9.7k tokens.
- **H2'''.cliff** — Δacc ≤ −0.30 and ≥80% of follow-ups emit a
  repeating literal token. Boundary is before 24f (closer to 16f).
  Safe budget is below 9.7k tokens; suggests a hard threshold.
- **H2'''.gradient** — Δacc ∈ (−0.30, −0.05). Partial degeneracy:
  some cache-path follow-ups still emit letters, others fall into
  artifacts. Suggests a soft boundary consistent with drift
  accumulation rather than a hard threshold.

### H3''' — prefix coverage stays ≥ 0.90

**Prediction.** Mean prefix coverage ≥ 0.90 (mechanism unchanged).

### H4''' — peak RSS stays under 12 GB

**Prediction.** Peak RSS ≤ **12 GB**. 16f hit 1.5 GB, 32f hit 2.5 GB;
24f should land near 2.0 GB with no allocator pressure.

## Falsification-sensitive observables

- Literal token distribution in cache-path follow-ups. If ≥80% emit
  the same out-of-distribution token, the boundary is at-or-before
  24f (H2'''.cliff supported).
- Cold-Q1 accuracy. Should stay 7/7 (matches baseline) regardless of
  bisection outcome — Q1 has no cache state to corrupt.
- Per-clip response distribution. If the artifact is specific to
  certain videos (e.g. those with higher effective prefix length due
  to token-count variance), that's a new sub-hypothesis.

## Scoring

All four H''' earn requires: speedup in band, Δacc ∈ [−0.05, 0.05],
prefix ≥ 0.90, peak RSS ≤ 12 GB.

The sharp/cliff/gradient sub-verdict on H2''' is independent of
"earn/reject" — it documents where the boundary sits.

## Runtime budget

Expected: ~55 min wall-clock (between the 35 min of 16f and 76 min
of 32f). If actual exceeds 90 min, abort and investigate.

## Pre-registered decisions

| Outcome | Decision |
|---------|----------|
| H2'''.sharp earns | Safe budget claim sharpens from "≤16f" to "≤24f (~9.7k tokens)"; boundary is past 24f; queue 28f next |
| H2'''.cliff | Boundary is before 24f; queue 20f next; consider 4-bit quantization as prime suspect (budget-like behaviour) |
| H2'''.gradient | Soft boundary; consistent with drift mechanism; investigate via longer-suffix decode and RoPE probe |
| H1''' rejects low | Speedup saturates earlier than the prefill-dominance model predicts |
| H4''' rejects | Memory-pressure evidence at 24f; paper caveats memory budget at 9.7k tokens |

## What this does NOT test

- Medium/long bucket (bucket-independence is a separate probe)
- Gemma path (deferred per 1.55A scope)
- 1.55B decode-accel composition (separate prereg)
- bf16 KV mechanism test (separate prereg required once boundary is
  localized)
