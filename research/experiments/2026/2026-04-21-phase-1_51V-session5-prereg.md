---
phase: 1.51V
date: 2026-04-21
parent: scripts/run_phase1_51V_session5.sh
prior:
  - research/experiments/2026/2026-04-21-phase-1_51V-session4-findings.md
  - research/experiments/2026/2026-04-21-phase-1_51V-session4-prereg.md
status: prereg (session 5 — TOMATO holdout V-only rerun after thermal confound)
---

# 1.51V session 5 prereg — TOMATO holdout V-only rerun (EXP23/24)

## Motivation

Session 4 EXP21/22 TOMATO 8f holdout pair was adjudicated THERMALLY
CONFOUNDED: paired sum-ratio E2E 1.330× (outlier-contaminated by 4
EXP21 dense-arm runtime outliers), V_red 0.2867 (below [0.38, 0.48]
band), decode Δ 6.52% (206 ms abs on 3164 ms window — genuine drift,
exceeds both the 2% relative and the proposed 100 ms absolute floor).

VideoMME holdout (session 3) and MVBench holdout (session 4) both
CLOSED. TOMATO is the one remaining C-VISION holdout cell with a
"dev-only n=30" footnote; session 5 is the minimal experiment to
lift that.

Changes from session 4:
- Extended cool-down (≥30 min since last Metal process) before launch.
- Same runner pattern (idempotent, unpatched → patched back-to-back).
- Thermal gate applies the revised absolute-floor rule:
  `|decode_ms Δ| < max(0.02 × decode_ms(EXP23), 100 ms)`.

## Hypotheses (preregistered)

Four hypotheses on the TOMATO 8f holdout pair.

**H_to5_vonly_e2e (primary)**: paired sum-ratio E2E speedup (sum of
EXP23 dense_e2e / sum of EXP24 pruned_e2e across the 30 items) ≥
**1.15×**. Same gate as session 4 for consistency; dev reference 1.24×.
Report median and trimmed-mean alongside the mean to control for
runtime outliers.

**H_to5_vred (primary)**: V_red ∈ [0.38, 0.48]. Dev measured 42.7%;
session-4 confounded run measured 0.287 (well below band), which is
what flagged the pair as thermally compromised. A clean V_red should
match the dev band because `keep_rate = 0.50` is an architectural
property independent of thermal state.

**H_to5_thermal (process)**:
`|decode_ms(EXP24) − decode_ms(EXP23)| < max(0.02 × decode_ms(EXP23), 100 ms)`.
At the TOMATO decode scale of ~3100 ms, the 2% relative gate = 62 ms
dominates the 100 ms floor — so the effective gate is 100 ms absolute.
If EXP24 − EXP23 ∈ [−100, +100] ms, the pair is thermally clean under
the revised calibration.

**H_to5_accuracy (secondary)**: acc Δ ∈ [−0.050, +0.050]. Session 4
measured −0.067 (below band); dev +0.033. A clean accuracy result
should sit closer to dev, since V-patching alters vision features but
not per-item generation targets.

## Non-hypotheses (explicit non-goals)

- No EXP21 rerun (the unpatched arm also ran with 4 dense-arm runtime
  outliers). The session 5 EXP23 unpatched rerun will fold into the
  new paired adjudication; if dense-arm outliers re-emerge, that
  becomes its own follow-up finding rather than blocking the pair.
- No 16f cell; no cross-benchmark Pareto sweep.
- No H_stack. That lives in task #152 (EXP10 n=60).

## Configuration

```
model-path        /Users/jfb/models/gemma-4-e4b-it-4bit
frame-count       8
n                 30 per arm
max-tokens        32
rss-guard-mb      10000
anchor-arm        none
keep-rate         1.0 (novelty disabled on both arms)

EXP23 (TOMATO unpatched):  manifest=tomato_motion_holdout_v2, no VT flags
EXP24 (TOMATO V-patched):  manifest=tomato_motion_holdout_v2,
                           --vision-tower-layer 2 --vision-tower-keep-rate 0.50
```

Same driver (`scripts/run_novelty_pruning_gemma.py`) and same
idempotent queue pattern as sessions 3 and 4.

## Runtime

Session 4 measured EXP21 862 s (14.4 min) + EXP22 772 s (12.9 min) =
1634 s (~27 min total). Expect ~30 min wall-clock for session 5.

## Adjudication rules

- **H_to5_vonly_e2e**: CONFIRMED if ≥ 1.15× AND thermal gate passes
  under revised rule. EARNED-advisory if ≥ 1.15× and thermal fails by
  <200 ms abs (second advisory pass). NULL if below 1.15× with thermal
  passing. CONFOUNDED if below 1.15× AND thermal fails.
- **H_to5_vred**: CONFIRMED if in [0.38, 0.48]; NOTED if outside and
  thermal fails; violated otherwise.
- **H_to5_thermal**: PASS/FAIL the revised absolute-floor gate.
- **H_to5_accuracy**: CONFIRMED if in band; NOTED if outside.

**Paper promotion rule**: if H_to5_vonly_e2e + H_to5_vred both
CONFIRMED under clean thermal, the TOMATO 8f V-only cell drops its
dev-only caveat, completing the three-benchmark C-VISION holdout
trifecta. If thermal fails a second time, treat TOMATO 8f as
"thermally-pairing-intractable on M3 16 GB" and report the dev number
with a methodology footnote rather than a holdout.

## Dependencies (gating)

None. Session 4 driver is unchanged. Pre-flight: `ps aux | grep -i
metal` empty; load average < 3.0; ≥30 min since last GPU-using process
exited.

## Artifacts expected

- `research/experiments/2026/artifacts/phase1_51V_session5/exp23_tomato_holdout_8f_unpatched.{jsonl,log,done}` + summary
- `research/experiments/2026/artifacts/phase1_51V_session5/exp24_tomato_holdout_8f_L2_kr050.{jsonl,log,done}` + summary
- `research/experiments/2026/artifacts/phase1_51V_session5/queue.{log,done}`
- Runner: `scripts/run_phase1_51V_session5.sh`
- Findings doc: `research/experiments/2026/2026-04-??-phase-1_51V-session5-findings.md`
