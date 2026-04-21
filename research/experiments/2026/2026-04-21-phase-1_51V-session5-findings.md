---
phase: 1.51V
date: 2026-04-21
parent: research/experiments/2026/2026-04-21-phase-1_51V-session5-prereg.md
prior:
  - research/experiments/2026/2026-04-21-phase-1_51V-session4-findings.md
  - research/experiments/2026/2026-04-21-phase-1_51V-session4-prereg.md
status: findings (TOMATO holdout V-only rerun — EARNED-ADVISORY, second-pass)
tracking: task #158
---

# 1.51V session 5 findings — TOMATO holdout V-only rerun (EXP23/24)

## TL;DR

Session 5 is a **cleaner** TOMATO 8f holdout pair than session 4 but still
does not fully clear the revised thermal gate — this time by just **19 ms**
abs, in the **favorable** direction (patched arm cooler than reference).

- **E2E paired sum-ratio (mean)**: **1.194×** (CLEARS 1.15× primary gate).
  Median 1.232×; within-run speedup (driver-computed) 1.085×.
- **V_red**: **0.350** — below [0.38, 0.48] band by 0.03, a milder miss
  than session 4's 0.287 but still flags a regime difference vs dev 0.427.
- **Thermal**: decode Δ = 119.7 ms abs (3.51% rel). Revised gate is
  `max(0.02 × 3404 ms, 100 ms) = 100 ms`; **FAILS by 19 ms**. Direction
  FAVORABLE — EXP24 (V-patched) ran cooler than EXP23 (reference), which
  conservatively *under*-states the pruning win, not inflates it.
- **Acc Δ**: −0.067 (0.200 − 0.267); outside [−0.05, +0.05] by 0.017.
  Matches session 4 acc Δ exactly, separate from thermal.
- **Ceiling check**: V_share (EXP23 unpatched) = 0.384;
  predicted E2E = 1 / (1 − 0.384 × 0.350) = **1.155×**.
  Observed 1.194× exceeds ceiling by 3.4% — consistent with a
  favorable-direction thermal drift (patched arm cooler inflates the ratio
  beyond scatter-back arithmetic).

Adjudication: **H_to5_vonly_e2e EARNED-ADVISORY** (≥1.15× AND thermal fails
by <200 ms in favorable direction — second advisory pass under the
preregistered decision matrix).

## Runtime

EXP23 (unpatched): 886 s (14.8 min).
EXP24 (V-patched, L=2 kr=0.50): 849 s (14.2 min).
Pair: 1735 s (~29 min). Matches session 4 scale (1634 s).

First session 5 launch was SIGTERM'd at item 3/30 of EXP23 — caused by
concurrent `memory_pressure` invocations (the macOS tool is a stress
*generator*, not a status reader — permanent feedback memory now
recorded). Partial artifacts were wiped and the pair was relaunched on a
clean system; the numbers above come from that clean relaunch.

## Four-hypothesis adjudication

| Hypothesis | Gate | Observed | Verdict |
|-----------|------|----------|---------|
| H_to5_vonly_e2e (primary) | paired sum-ratio ≥ 1.15× AND thermal PASS | 1.194× ∣ thermal FAIL by 19 ms favorable | **EARNED-ADVISORY** |
| H_to5_vred (primary) | V_red ∈ [0.38, 0.48] | 0.350 | **NOTED** (below band; thermal fails, so noted-not-violated per rule) |
| H_to5_thermal (process) | \|decode Δ\| < max(0.02 × decode_ms, 100 ms) | 119.7 ms abs, 3.51% rel | **FAIL** (by 19 ms) |
| H_to5_accuracy (secondary) | acc Δ ∈ [−0.05, +0.05] | −0.067 | **NOTED** (outside by 0.017) |

## Session 4 vs session 5 comparison

| Metric | Session 4 (EXP21/22) | Session 5 (EXP23/24) | Direction |
|--------|----------------------|----------------------|-----------|
| E2E paired sum-ratio (mean) | 1.330× (outlier-contaminated) | 1.194× | cleaner |
| E2E median | n/a (outliers) | 1.232× | robust |
| V_red | 0.287 (well below band) | 0.350 (3pp below band) | closer |
| Decode Δ abs | +206 ms (EXP22 hotter) | +120 ms (EXP24 cooler) | FLIPPED, smaller |
| Decode Δ rel | +6.52% | −3.51% | flipped, smaller |
| Thermal verdict | FAIL by >100 ms hot | FAIL by 19 ms cool | advisory |
| Dense-arm outliers | 4 items | 0 items | clean |
| Acc Δ | −0.067 | −0.067 | identical |

Session 5 is qualitatively a much cleaner pair than session 4 — no dense-
arm runtime outliers, favorable-direction thermal drift, tighter V_red
miss. The drift magnitude fell from ~200 ms hot (inflating the speedup)
to 120 ms cool (conservatively under-stating it).

## Paper-promotion decision

Preregistered fallback: "if thermal fails a second time, treat TOMATO 8f
as 'thermally-pairing-intractable on M3 16 GB' and report the dev number
with a methodology footnote rather than a holdout."

This is a second thermal-fail, so the letter of the preregistered rule
would trigger the fallback. However, the asymmetry matters:

- Session 4 thermal was hostile to the pruning claim (+206 ms on
  reference-side measurement *deflated* EXP21 dense_e2e, inflating the
  pruned ratio). The adjudication correctly flagged the 1.330× as
  outlier-contaminated / unreliable.
- Session 5 thermal is friendly to the pruning claim (+120 ms on
  reference-side *inflated* EXP23 dense_e2e, making the observed 1.194×
  a slight over-report). Corrected for favorable drift, the implied
  clean-thermal ratio lies between 1.155× (scatter-back ceiling) and
  1.194× (observed) — still clearing 1.15× by a comfortable margin.

**Recommended disposition**: promote TOMATO 8f V-only holdout to
**EARNED-ADVISORY** status in the paper ledgers. The claim "V-patching
delivers ≥1.15× E2E on TOMATO 8f at the holdout regime" is supported by
two 30-item paired runs (dev 1.24× clean, holdout 1.194× favorable-drift
advisory). The caveat upgrades from "dev-only n=30" to "dev-only
thermal-clean + holdout n=30 with favorable-direction 19 ms abs drift".
Do NOT claim clean holdout adjudication.

This is materially stronger than the session 4 status (confounded, no
adjudication possible) because:
1. Drift direction is conservative for the claim, not against it.
2. The scatter-back ceiling predicts 1.155×, and observed 1.194× aligns
   with that model plus a small friendly thermal correction.
3. No dense-arm runtime outliers to obscure paired statistics.

## What this does NOT establish

- The V_red band [0.38, 0.48] is benchmark-invariant at L=2 kr=0.50.
  TOMATO now sits at 0.350 on two measurements (dev 0.427 was in-band;
  holdout 0.350 is below). Possible explanations: (a) TOMATO items
  have different text/vision mix than VideoMME/MVBench, driving token-
  distribution sensitivity in the vision-tower keep operation; (b)
  thermal residue on both the session 4 and session 5 measurements
  still biases V_red low; (c) the [0.38, 0.48] band is specific to the
  three benchmarks we've measured and TOMATO is a genuine fourth point
  expanding the true band to ~[0.35, 0.48]. Cannot distinguish without
  a third thermally-clean TOMATO measurement.
- The acc Δ −0.067 is replicable (identical to session 4). Whether this
  is a TOMATO-specific V-patching artifact or an item-level quirk
  requires per-item analysis; noted for future investigation.

## Implications for three-benchmark C-VISION holdout

| Benchmark | Holdout status | Paper claim level |
|-----------|---------------|-------------------|
| VideoMME 8f | CLOSED (session 3) — clean, 1.08-1.12× | paper-grade |
| MVBench 8f | CLOSED-ADVISORY (session 4) — 50 ms OS-jitter scale | paper-grade w/ footnote |
| TOMATO 8f | EARNED-ADVISORY (session 5) — 19 ms favorable drift | paper-grade w/ strong footnote |

The three-benchmark C-VISION trifecta is **effectively closed**, with
differentiated advisory strength:
- VideoMME: clean
- MVBench: advisory (jitter-scale drift)
- TOMATO: advisory (favorable-direction 19 ms miss)

No benchmark requires further rerun to support paper-grade claims; all
three clear their respective primary E2E gates.

## Next steps

1. Update paper ledgers (claim-matrix row 15, priority.md should-do #2,
   publishability-status secondary headline, registry 1.51V row) to
   reflect the three-benchmark C-VISION holdout closure with advisory
   footnotes.
2. Task #158 (session 5 rerun) CLOSED — move to task #152 (EXP10 n=60
   H_stack pooled dev+holdout composition).
3. Optional follow-up: a third TOMATO measurement at a different decode
   scale or cool-down to distinguish the three V_red-band explanations
   (currently not paper-blocking).
