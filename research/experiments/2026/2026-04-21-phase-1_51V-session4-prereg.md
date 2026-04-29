---
phase: 1.51V
date: 2026-04-21
parent: scripts/run_phase1_51V_session4.sh
prior:
  - research/experiments/2026/2026-04-21-phase-1_51V-session3-findings.md
  - research/experiments/2026/2026-04-21-phase-1_51V-expansion-findings.md
status: prereg (session 4 — V-only MVBench + TOMATO holdout pairs)
---

# 1.51V session 4 prereg — V-only MVBench + TOMATO holdout pairs (EXP19–22)

## Motivation

Session 3 (EXP17/18) closed the VideoMME 8f V-only holdout gap — all four
preregistered hypotheses passed with a clean thermal pair. The MVBench and
TOMATO V-only cells (1.21× and 1.24× dev-n=30) remain dev-only per
`paper/priority.md` should-do #2.

Session 4 replicates the session-3 pattern on the other two benchmarks:
back-to-back unpatched→patched pairs, same driver, same L=2 kr_V=0.50, same
novelty=1.0, same RSS guard. If all four hypotheses pass on both pairs, the
three C-VISION paper-table cells (VideoMME 8f, MVBench 8f, TOMATO 8f) all
drop the "dev-only n=30" footnote simultaneously — covering all three
benchmarks the paper reports on.

## Hypotheses (preregistered)

Four hypotheses per pair, eight total.

### MVBench pair (EXP19 unpatched → EXP20 V-patched, holdout v2 n=30 8f)

**H_mv_holdout_vonly_e2e (primary)**: paired E2E speedup (EXP19 dense /
EXP20 pruned) ≥ **1.10×**. Dev reference: 1.21×. MVBench is vision-
dominated (dev V_share 47.8%), so the holdout ceiling should be in the
1.15–1.25× band. A lower threshold of 1.10× accommodates holdout-specific
V_share variance while rejecting "no transfer".

**H_mv_holdout_vred (primary)**: V_red ∈ [0.35, 0.45]. Dev measured 40.0%;
benchmark-invariance at kr=0.50 predicts this cell stays in band.

**H_mv_holdout_thermal (process)**: cross-arm |decode_ms Δ| / decode_ms(EXP19)
< 2%. Fails the pair if violated.

**H_mv_holdout_accuracy (secondary)**: acc Δ ∈ [−0.100, +0.100]. Dev Δ =
−0.100 (accuracy drifted on dev); the band is wider than the VideoMME session-3
band because MVBench motion is a harder benchmark where V-patching may
marginally hurt.

### TOMATO pair (EXP21 unpatched → EXP22 V-patched, holdout v2 n=30 8f)

**H_to_holdout_vonly_e2e (primary)**: paired E2E speedup (EXP21 dense /
EXP22 pruned) ≥ **1.15×**. Dev reference: 1.24×. TOMATO motion is the most
vision-dominated of our three benchmarks (dev V_share 40.7%, V_red 42.7%).

**H_to_holdout_vred (primary)**: V_red ∈ [0.38, 0.48]. Dev measured 42.7%;
slightly wider than MVBench/VideoMME bands to allow for TOMATO's larger
V_red observed on dev.

**H_to_holdout_thermal (process)**: cross-arm |decode_ms Δ| / decode_ms(EXP21)
< 2%.

**H_to_holdout_accuracy (secondary)**: acc Δ ∈ [−0.050, +0.050]. Dev Δ =
+0.033; accuracy was neutral-to-favorable on dev.

## Non-hypotheses (explicit non-goals)

- No Pareto sweep (kr=0.25 / kr=0.75). That was already mapped on VideoMME
  dev; cross-benchmark Pareto is deferred to a future session if a reviewer
  asks.
- No 16f cross-frame scaling on the holdouts. The dev 16f cell is only
  measured on VideoMME; extending the scaling story to MVBench-16f /
  TOMATO-16f is a post-submission lift.
- No novelty × V-patching stacking (H_stack). H_stack is tested separately
  at EXP10 n=60 (should-do #1 in `paper/priority.md`).

## Configuration

```
model-path        $GEMMA_MODEL_PATH
frame-count       8
n                 30 per arm
max-tokens        32
rss-guard-mb      10000
anchor-arm        none
keep-rate         1.0 (novelty disabled on both arms)

EXP19 (MVBench unpatched):   manifest=mvbench_motion_holdout_v2, no VT flags
EXP20 (MVBench V-patched):   manifest=mvbench_motion_holdout_v2,
                             --vision-tower-layer 2 --vision-tower-keep-rate 0.50
EXP21 (TOMATO unpatched):    manifest=tomato_motion_holdout_v2, no VT flags
EXP22 (TOMATO V-patched):    manifest=tomato_motion_holdout_v2,
                             --vision-tower-layer 2 --vision-tower-keep-rate 0.50
```

## Runtime

Session 3 VideoMME 8f holdout: EXP17 1770 s (29.5 min), EXP18 1628 s (27.1
min). MVBench and TOMATO item lengths are comparable. Estimate ~25–30 min
per arm, ~2 h total for session 4. Well within single-autonomous-session
budget.

## Adjudication rules

Per pair:
- **H_*_vonly_e2e**: CONFIRMED if ≥ gate AND thermal gate passes. EARNED if
  ≥ gate but thermal fails (diagnostic). NULL if below gate with thermal
  gate passing.
- **H_*_vred**: CONFIRMED / violated based on band membership.
- **H_*_thermal**: PASS/FAIL gate; invalidates other verdicts if FAIL.
- **H_*_accuracy**: CONFIRMED if Δ in band; NOTED if outside (not a hard gate).

**Paper promotion rule**: if H_mv_holdout_vonly_e2e + H_mv_holdout_vred
both pass, the MVBench 8f V-only cell drops its dev-only caveat. Analogous
for TOMATO. If all three benchmarks pass (VideoMME session 3 + MVBench +
TOMATO here), the C-VISION three-benchmark paper-table headline is fully
holdout-earned — the strongest possible framing.

## Dependencies (gating)

None. Session 3 runner + driver pattern is identical; manifests exist.
Session 3 clean thermal pair (1.53% decode Δ) shows the pairing-pattern works
when the unpatched arm runs first back-to-back.

## Artifacts expected

- `research/experiments/2026/artifacts/phase1_51V_session4/exp19_mvbench_holdout_8f_unpatched.{jsonl,log,done}` + summary
- `research/experiments/2026/artifacts/phase1_51V_session4/exp20_mvbench_holdout_8f_L2_kr050.{jsonl,log,done}` + summary
- `research/experiments/2026/artifacts/phase1_51V_session4/exp21_tomato_holdout_8f_unpatched.{jsonl,log,done}` + summary
- `research/experiments/2026/artifacts/phase1_51V_session4/exp22_tomato_holdout_8f_L2_kr050.{jsonl,log,done}` + summary
- `research/experiments/2026/artifacts/phase1_51V_session4/queue.log`
- Runner: `scripts/run_phase1_51V_session4.sh`
- Findings doc: `research/experiments/2026/2026-04-21-phase-1_51V-session4-findings.md`
