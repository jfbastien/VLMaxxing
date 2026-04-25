# Phase 1.55D v2 — Selective re-prefill K=2 (FINDINGS)

**Date:** 2026-04-24.
**Parent:** `2026-04-20-phase-1_55D-selective-reprefill-prereg.md`.
**Verdict:** **frontier point improved; no observed paired drift on n=21,
speed still below the prereg deployment floor.**

## Why this run mattered

K=4 already established that repo-local v2 can recover the 20f Qwen 7B
short-bucket tranche to baseline accuracy. The next scientific question
was whether a lighter tail could preserve that recovery while moving the
latency materially closer to the preregistered deployment gate.

K=2 is the first informative frontier point for that question.

## Setup

- Model: `Qwen2.5-VL-7B-Instruct-4bit`
- Regime: 20-frame persistent-KV short-bucket VideoMME session
- Clips: `037,100,116,120,158,160,210`
- Queries: 3 per clip, session path vs matched cold baseline
- Output dir:
  `research/experiments/2026/artifacts/phase1_55D_selective_reprefill_v2/`

## Headline results

From `summary_k2_n7.json` plus the paired row analysis:

- `session_accuracy = 17/21 = 0.8095`
- `baseline_accuracy = 17/21 = 0.8095`
- `accuracy_delta_session_minus_baseline = 0.0`
- `session_follow_up_accuracy = 11/14 = 0.7857`
- `session_follow_up_median = 16.006 s`
- paired follow-up median `= 15.272 s`
- cold baseline median `= 102.627 s`
- median speedup vs cold baseline `= 6.72×`
- mean follow-up prefix coverage `= 0.8938`
- `peak_rss_gb = 3.305`

Most importantly:

- **per-item correctness diffs = 0/21**
- **paired answer-choice diffs = 0/21**
- **pathological attractor count on follow-ups = 0/14**

So K=2 keeps the same no-observed-drift result as K=4 on this `n=21`
paired tranche while cutting the follow-up latency roughly in half and
reducing RSS by ~1.7 GB.

## Preregistered verdicts

### H1-1.55D.K=2 (fidelity recovery)

**EARNED strongly.**

Observed `Δacc = 0.0` relative to the cold baseline, with zero paired
choice or correctness diffs on all 21 query pairs. Scope this as **no
observed paired drift on n=21**, not as an unqualified exact-fidelity
law.

### H2-1.55D (speedup floor)

**FALSIFIED narrowly but materially improved.**

The preregistered target was follow-up median `<= 15 s` and speedup
`>= 10×`.

Observed:

- paired follow-up median `= 15.272 s`
- speedup `= 6.72×`

So K=2 misses the median gate by only ~0.27 s, but still falls well
short of the `10×` multiplier gate.

### H3-1.55D (basin dispersal)

**EARNED strongly.**

Observed pathological-attractor prevalence on session follow-ups:

- `0/14`

### H4-1.55D (peak RSS)

**EARNED.**

Observed:

- `peak_rss_gb = 3.305`

This is comfortably inside the preregistered `<= 5 GB` cap.

## Interpretation

K=2 is now the best local operating point for 1.55D.

The scientific picture after K=2 is:

- selective re-prefill is **not** an infrastructure-only open question;
  it is a working fidelity-recovery method,
- the recovery is not fragile on this tranche; even the lighter tail
  preserves exact paired choices and correctness,
- the current limitation is no longer "can it work?" but
  "can it reach a deployment-grade speed regime?"

K=2 therefore upgrades 1.55D from a single rescue point to a real
**speed/fidelity frontier**:

- K=4: no observed paired drift on n=21, `3.66×`, RSS miss
- K=2: no observed paired drift on n=21, `6.72×`, RSS pass

That still does not earn the preregistered deployment claim, but it is
substantially stronger paper evidence than K=4 alone.

## Consequence for next work

The next informative follow-up is **not K=8**.

K=8 would mostly spend more latency to re-prove a fidelity result that
already holds at K=2 and K=4. The meaningful remaining questions are:

1. whether a still-lighter recovery point (for example K=1 or an
   adaptive trigger) can cross the `<= 15 s` / `>= 10×` line without
   giving back fidelity, or
2. whether the better paper move is now to keep K=2 as the frontier
   point and shift effort to the other open contribution lanes.
