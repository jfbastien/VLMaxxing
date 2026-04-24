---
phase: 1.55E
date: 2026-04-24
parent: research/experiments/2026/2026-04-24-phase-1_55D-selective-reprefill-v2-k1-findings.md
artifacts:
  - research/experiments/2026/artifacts/phase1_55E_adaptive_reprefill_q2_k1_q3_k0/
status: preregistered 2026-04-24. Position-conditioned adaptive selective re-prefill.
---

# 1.55E — Adaptive selective re-prefill (`Q2=K1`, `Q3=K0`) preregistration

## Objective

Test the smallest adaptive extension beyond the mapped fixed-K frontier:

- `Q1`: cold start, as before
- `Q2`: selective re-prefill with `K=1`
- `Q3`: no selective re-prefill (`K=0`), reusing the retained full-Q1
  cache path

The scientific question is whether the repo-local `1.55D` recovery
frontier can clear the deployment-speed crossover once we stop paying
the `K=1` tax on every follow-up.

## Why this is the right next step

The landed `1.55D K=1` point already tells us two important facts on the
full 7-clip 20f tranche:

1. `Q2` is the high-value rescue point:
   `7/7` correct at a median `12.6 s`.
2. `Q3` already matches the cold baseline in correctness:
   `4/7` vs cold `4/7`, but still costs a median `6.65 s`.

So the clean next hypothesis is not another blind fixed-K sweep. It is:

**Q2 needs the tail refresh; Q3 may not.**

## Protocol

- Model: `Qwen2.5-VL-7B-Instruct-4bit`
- Regime: 20-frame persistent-KV short-bucket VideoMME session
- Clips: `037,100,116,120,158,160,210`
- Queries: 3 per clip, matched cold baseline
- Session policy:
  - `Q1`: cold (`K=0`)
  - `Q2`: `K=1` selective re-prefill
  - `Q3`: `K=0` full-cache reuse

## Hypotheses

### H1 — exact paired fidelity survives

Session correctness and answer choices remain exactly paired to the
matched cold baseline on the full 7-clip tranche.

**Acceptance:** `Δacc = 0.0` and paired answer-choice diffs `= 0/21`.

**Failure:** any paired correctness or answer-choice regressions.

### H2 — deployment-speed crossover lands

Removing the `K=1` tax from `Q3` is enough to cross the paper-grade
speed line.

**Acceptance:** paired follow-up median speedup `>= 10×`.

**Failure:** speedup `< 10×`.

### H3 — basin control survives

The adaptive policy preserves the `K=1` attractor control.

**Acceptance:** pathological follow-up attractors `= 0/14`.

### H4 — memory stays in budget

**Acceptance:** `peak_rss_gb <= 5.0`.

## Interpretation rules

- If H1/H3/H4 pass and H2 passes:
  adaptive selective re-prefill becomes the new best local
  deployment-grade point.
- If H1/H3/H4 pass but H2 fails narrowly:
  the adaptive direction is still right, but a stronger condition on Q3
  is required.
- If H1 fails:
  Q3 is not dispensable, and the next adaptive policy must reintroduce
  some targeted Q3 refresh rather than chase more speed.

## Code path

- Runner:
  `scripts/run_kv_selective_reprefill_v2.py`
- New policy resolver:
  `src/codec_through/selective_reprefill_policy.py`

## Execution

Pending.

## Result

Pending.

## Interpretation

Pending.
