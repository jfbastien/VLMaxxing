# Phase 1.55D v2 — Selective re-prefill K=1 (FINDINGS)

**Date:** 2026-04-24.
**Parent:** `2026-04-24-phase-1_55D-selective-reprefill-v2-k1-prereg.md`.
**Verdict:** **best fixed frontier point; no observed paired drift on n=21,
deployment speed still narrowly misses.**

## Why this run mattered

After K=2 landed with exact paired recovery but only `6.72×` speedup,
the live question was whether one more step down the tail could push
1.55D across the deployment-speed line without giving back fidelity.

K=1 was the highest-information fixed-tail extension.

## Setup

- Model: `Qwen2.5-VL-7B-Instruct-4bit`
- Regime: 20-frame persistent-KV short-bucket VideoMME session
- Clips: `037,100,116,120,158,160,210`
- Queries: 3 per clip, session path vs matched cold baseline
- Output dir:
  `research/experiments/2026/artifacts/phase1_55D_selective_reprefill_v2/`

## Headline results

From `summary_k1_n7.json` plus the paired row analysis:

- `session_accuracy = 17/21 = 0.8095`
- `baseline_accuracy = 17/21 = 0.8095`
- `accuracy_delta_session_minus_baseline = 0.0`
- `session_follow_up_accuracy = 11/14 = 0.7857`
- `session_follow_up_median (= paired session-follow-up median) = 10.136 s`
- paired cold-follow-up median `= 96.095 s`
- paired all-query cold median `= 98.433 s`
- paired cold-follow-up median over session-follow-up median
  `= 9.48× = 96.095 / 10.136`
- paired all-query cold median over session-follow-up median
  `= 9.71× = 98.433 / 10.136`
- mean follow-up prefix coverage `= 0.9434`
- `peak_rss_gb = 4.886`

Most importantly:

- **per-item correctness diffs = 0/21**
- **paired answer-choice diffs = 0/21**
- **pathological attractor count on follow-ups = 0/14**

The two apparently "wrong" session rows on clip `120-Q3` and
`210-Q1/Q3` were not frontier failures; the matched cold baseline misses
the same keyed items with the same answer choices. K=1 therefore shows
**no observed paired correctness or choice drift on this full paired
tranche**. With `n=21`, that is strong evidence, but it is still an
observation-level claim rather than an unqualified exact law.

## Preregistered verdicts

### H1-K1 (partial fidelity recovery)

**EARNED strongly.**

Observed `Δacc = 0.0` with zero paired answer-choice or correctness
diffs on all 21 query pairs. This is much stronger than the
preregistered partial-recovery target, but it should still be written as
**no observed paired drift on n=21**.

### H2-K1 (deployment-speed crossover)

**Narrow miss; not formally falsified.**

Observed:

- paired follow-up median `= 10.136 s`
- paired cold-follow-up / session-follow-up speedup `= 9.48×`
- paired all-query cold / session-follow-up speedup `= 9.71×`

So K=1 misses the intended deployment crossover by a narrow but real
margin. It earns the latency side (`10.136 s <= 10.5 s`) but misses the
headline multiplier (`9.71× < 10×` on the all-query denominator; `9.48×`
on the same-class follow-up denominator). The result is close enough to
matter scientifically, but it does not earn the `>= 10×` paper-grade
fixed-policy claim.

### H3-K1 (basin control)

**EARNED strongly.**

Observed pathological-attractor prevalence on session follow-ups:

- `0/14`

### H4-K1 (memory)

**EARNED.**

Observed:

- `peak_rss_gb = 4.886`

## Interpretation

K=1 is now the **best fixed policy** in the 1.55D lane:

- K=4: no observed paired drift on n=21, `3.74×` all-query / `3.33×`
  same-class follow-up, RSS narrow fail
- K=2: no observed paired drift on n=21, `6.72×`, RSS pass
- K=1: no observed paired drift on n=21, `9.71×` all-query / `9.48×`
  same-class follow-up, RSS pass

That gives a clean scientific conclusion:

- selective re-prefill works,
- the fidelity recovery is robust across the fixed-tail points we ran,
- the fixed-K frontier improves smoothly as the tail gets lighter,
- but the local Qwen 7B setup still falls just short of a clean
  deployment-grade `>= 10×` crossover.

So 1.55D is no longer an infrastructure question and no longer just a
single rescue point. It is a mapped fixed-policy frontier with one clear
remaining gap.

## Consequence for next work

Another blind fixed-K sweep is now low information.

The next useful follow-up is an **adaptive** recovery policy: refresh
only when the query or clip geometry is risky enough to need it, rather
than paying a fixed one-frame tax on every follow-up.

That points naturally toward:

1. an adaptive 1.55D refresh trigger, or
2. the closely related 1.30 admission/no-prune policy lane, which is now
   the higher-leverage composition problem in the repo.
