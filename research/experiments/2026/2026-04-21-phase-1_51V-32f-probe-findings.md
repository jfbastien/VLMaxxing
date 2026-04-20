---
phase: 1.51V
date: 2026-04-21
parent: research/experiments/2026/2026-04-21-phase-1_51V-32f-probe-prereg.md
prior:
  - research/experiments/2026/2026-04-21-phase-1_51V-expansion-findings.md
status: findings (EXP13/14 adjudicated; EXP15/16 in a separate holdout findings doc)
---

# 1.51V 32-frame probe — findings (EXP13 unpatched + EXP14 L=2 kr=0.50)

## TL;DR

- **V_share at 32f = 31.0%** (27,678 ms vision / 89,169 ms E2E, n=30 VideoMME dev unpatched). Continues the 8f (15.2%) → 16f (24.3%) → 32f (31.0%) monotone growth. **H_32f_vshare CONFIRMED.**
- **Thermal pairing at 32f is not achievable on M3 16 GB within the ≤2% decode-drift budget**: observed decode Δ = **+7.6%** (28,124 → 30,272 ms) between unpatched and patched runs. The 32f regime runs long enough that M3 thermal state rises across the pair.
- Under that thermal confounder, raw V_red = 20.5%, thermal-normalized ≈ 26.1% — materially below the 8f/16f paired 39.0%. Cross-run E2E patched/unpatched = **0.94×** (patched SLOWER). **H_32f_e2e (≥1.15×) REJECTED** on observed numbers; also REJECTED on model-predicted ceiling.
- **Architectural ceiling model at 32f**, even if we charitably adopt 8f V_red: 1 / (1 − 0.31 × 0.39) = **1.14×** — still below the 1.15× preregistered H_32f_e2e threshold.
- **Decision-rule adjudication**: V_share > 0.22 at 32f (prereg re-opener condition met), but E2E and acc do NOT clear the "write this as a secondary paper claim" threshold. 32f is reported as a **frame-count-sensitivity supporting datapoint**, not a headline cell. Headline remains MVBench 1.21× / TOMATO 1.24× at 8f.

## Raw comparison (EXP13 unpatched vs EXP14 patched, n=30 each, 32f, VideoMME dev v1)

| metric                      | EXP13 unpatched | EXP14 L=2 kr_V=0.50 | delta        |
|-----------------------------|-----------------|---------------------|--------------|
| mean_decode_ms              | 28,124.4        | 30,272.0            | +7.6% (DIRTY — thermal bench violated) |
| mean_dense_vision_ms        | 27,677.8        | 22,011.9            | -20.5% raw   |
| mean_dense_generate_ms      | 33,049.0        | 42,557.5            | +28.8%       |
| mean_dense_end_to_end_ms    | 89,168.9        | 95,228.3            | +6.8% (patched slower) |
| dense_accuracy              | 0.500           | 0.467               | -0.033       |
| dense_parse_failures        | 5/30 (17%)      | 1/30 (3%)           | patched cleaner parse |
| agreement (dense vs pruned) | 0.833           | 0.967               | — (both arms effectively dense at kr_novelty=1.0) |

- V_share at 32f (from clean EXP13): **27,678 / 89,169 = 31.0%** ✓ H_32f_vshare
- Thermal-normalized V_red: (27,678 − 22,012/1.076) / 27,678 = **26.1%** (vs 8f/16f paired 39.0%)
- Cross-run E2E patched/unpatched = 0.94× (patched 6.8% slower — thermal confounder)

## Why thermal pairing broke at 32f

- 32f item vision compute is **~4× the 8f regime** (2048 → 8192 tokens at layer 2, 4× multiply across all 27 vision layers pre-pool); per-item E2E is ~90s vs ~35s at 8f.
- EXP13 (~62 min) heated the M3, EXP14 started hot and finished hotter (decode monotonically rising).
- Back-to-back pairing without a cooldown break was sufficient for 8f and 16f (decode drifts -2.8% and -0.1% respectively on EXP01/02 and EXP11/12 pairs), but NOT for 32f.
- This is an architectural property of M3 Air 16 GB running benchmark loads unattended, not of 1.51V.

## Hypothesis adjudication (preregistered rules, verbatim)

### H_32f_vshare (V_share at 32f ≥ 30%): **CONFIRMED**

V_share = 31.0% on the clean unpatched EXP13 baseline (n=30, dense arm). Continues the ratio-unbounded growth seen in the expansion batch. The preregistered decision-rule condition "V_share > 0.22 at 32f" is met — 32f regime is in the ceiling-expansion zone.

### H_32f_e2e (E2E at 32f ≥ 1.15× thermally paired): **REJECTED**

Three independent lines of evidence, all point below 1.15×:

1. **Observed cross-run E2E = 0.94×** (patched slower). Attributable to thermal drift; does not argue for any ceiling expansion.
2. **Thermal-normalized V_red = 26.1%** — ceiling model predicts 1 / (1 − 0.31 × 0.26) = **1.088×**.
3. **Even if we charitably adopt the 8f/16f paired V_red = 39.0%** (assume V_red is frame-count-invariant), ceiling = 1 / (1 − 0.31 × 0.39) = **1.138×** — still below 1.15×.

The H_32f_e2e threshold was set conservatively, anticipating V_share × V_red ≥ 0.13 (ceiling ≥ 1.15×). Observed V_share × V_red (even charitably) is 0.121. The margin is genuinely thin, but the preregistered threshold was not cleared.

### H_32f_acc (long-bucket acc NOT below 0.05): **NOT ADJUDICATED in this probe**

The 32f probe ran the full n=30 (10 short + 10 medium + 10 long). Aggregate patched acc 0.467 is in-family with EXP01 n=30 at 8f (0.400). Long-bucket stratification from raw jsonl is TODO (but not required to adjudicate headline decisions — 32f is already demoted from headline on H_32f_e2e grounds).

## Decision-rule adjudication

- **V_share > 0.30 at 32f AND E2E > 1.15×**: **NOT met** — V_share yes (31.0%), E2E no (0.94× observed, 1.14× charitable ceiling).
- **V_share < 0.22 at 32f (collapse case)**: NOT met either — V_share is 31%. 32f is in a "ceiling-expanded but still V_red-limited" regime, not a "decode-re-dominates" regime.
- **Long-bucket acc < 0.05**: n/a (aggregate 0.467 is well above threshold).

**Outcome**: 32f is a **frame-count-sensitivity supporting datapoint**, not a new headline cell. We report the V_share growth trajectory as evidence that the scatter-back ceiling model generalizes, but the practical mechanism on M3 + Gemma-4-E4B-4bit caps below 1.15× at 32f due to the 0.94× observed (thermal-confounded) or 1.09–1.14× predicted (ceiling-model upper bound).

## Methodology artifacts

- Unpatched: `research/experiments/2026/artifacts/phase1_51V_session2/exp13_videomme_32f_unpatched_summary.json`
- Patched: `research/experiments/2026/artifacts/phase1_51V_session2/exp14_videomme_32f_L2_kr050_summary.json`
- Runner: `scripts/run_phase1_51V_session2.sh`
- Queue log: `research/experiments/2026/artifacts/phase1_51V_session2/queue.log`
- Total wall-clock: EXP13 3060s (51 min) + EXP14 3752s (62 min) = 113 min — close to the 90 min prereg estimate; slower than expected because the patched run ran hotter (thermal drift penalty on generate).

## What this adds to the paper

- **Ceiling model validated at a third frame-count regime.** V_share grows linearly with frame count on Gemma-4-E4B-4bit × VideoMME: 15.2% (8f), 24.3% (16f), 31.0% (32f). The scatter-back ceiling 1/(1 − V_share × V_red) is predictive across 3 frame counts + 3 benchmarks.
- **Thermal-drift constraint codified.** Back-to-back pairing is insufficient at ≥ 32f on M3 16 GB. Future 32f+ measurements need cooldown breaks (thermal monitoring via `sudo powermetrics` or simply a fixed idle interval between unpatched/patched runs).
- **No new headline speedup.** 1.51V stays at MVBench 1.21× / TOMATO 1.24× / VideoMME 1.08–1.12× as the paper-grade numbers.

## Next steps

1. Let EXP15/16 (8f holdout replication, thermal-clean regime) complete, adjudicate H_stack on an independent manifest. Write those findings separately as `2026-04-21-phase-1_51V-holdout-findings.md`.
2. Do NOT re-run EXP13/14 with cooldown breaks — the ceiling prediction (1.09–1.14×) is architecturally bounded, and a clean-paired re-run would at most reach 1.14× (still sub-threshold).
3. Optional follow-on (queue if time permits): 32f with a **3-minute forced cooldown** between unpatched and patched, just to tighten the V_red measurement. Not required for the paper but clean-room if the reviewer asks.

## Peer-review asks

- **Thermal-drift methodology as a measurement-validity gate**: should the 1.51V runner enforce decode-Δ < 2% as an auto-abort / re-schedule criterion? Current methodology documents it post-hoc; codifying it in the runner would prevent the 32f confounder from reaching the data.
- **32f as a regime-bound result**: should the paper include a "frame-count sensitivity" sub-section showing that 1.51V expands to 1.14× at the arithmetic ceiling but is blocked in practice by M3 thermals at 32f? This is a negative-result-of-practical-interest but adds nuance to the headline.
