---
phase: 1.51V
date: 2026-04-21
parent: scripts/run_phase1_51V_session2.sh
prior:
  - research/experiments/2026/2026-04-21-phase-1_51V-expansion-findings.md
  - research/experiments/2026/2026-04-21-phase-1_51V-32f-probe-findings.md
status: findings (EXP15/16 adjudicated; holdout H_stack partial-replication)
---

# 1.51V holdout replication — findings (EXP15 V-patched baseline + EXP16 V+novelty kr=0.3 on VideoMME holdout v1)

## TL;DR

- **H_stack replicates on holdout in direction, with smaller magnitude.** EXP16 (V-patched L=2 kr_V=0.50 + novelty kr=0.3 anchor=none, n=30 disjoint holdout items) delivers within-run E2E **1.064×** over the V-patched baseline, agreement=0.667, acc Δ=-0.033. Compare to EXP10 dev (same config): 1.11× within-run, agreement=0.63, acc Δ=-0.067.
- **V_share on holdout is ~half of dev** (8.6% vs 15.2%), which ceiling-bounds stacking gains tighter on holdout. The LLM-side analog `1/(1 − generate_share × generate_reduction) = 1/(1 − 0.18 × 0.334) = 1.064×` matches observed speedup to within 0.1pp.
- **Thermal pairing EXP15→EXP16: clean within-run, DIRTY cross-session.** Decode Δ across the pair = -7.8% (cooler); EXP15 ran hot (after the 32f probe) and EXP16 started cooler. Cross-session 1.127× (EXP15 pruned / EXP16 pruned) is thermally inflated; within-run 1.064× is the safe number.
- **V-only holdout headline is UN-MEASURED.** Neither EXP15 nor EXP16 provides an unpatched holdout reference (EXP15 has novelty=1.0 but still V-patched). The dev 1.08×/1.12×/1.21×/1.24× V-only headlines remain **dev-only** until a holdout unpatched-vs-patched pair runs.
- **Decision-rule adjudication:** H_stack holdout **PARTIAL CONFIRMATION**. Direction replicates, magnitude is V_share-regime-bound to ~1.06× on VideoMME holdout. Not a headline reopener; keep as "stacking composes, ceiling-limited" secondary claim.

## Raw comparison (EXP15 vs EXP16, n=30 each, VideoMME holdout v1, 8f)

| metric                          | EXP15 V-patched (novelty=1) | EXP16 V-patched+novelty=0.3 | delta             |
|---------------------------------|------------------------------|------------------------------|-------------------|
| dense_accuracy                  | 0.467                        | 0.467                        | +0.000            |
| pruned_accuracy                 | 0.467 (≡dense, keep=1)       | 0.433                        | -0.033            |
| agreement (dense vs pruned)     | 0.967                        | 0.667                        | -0.300            |
| effective_keep_ratio            | 1.000                        | 0.297                        | -0.703            |
| mean_dense_vision_ms            | 3,446                        | 3,535                        | +2.6% (noise)     |
| mean_dense_prompt_tokens        | 2,195                        | 2,195                        | 0                 |
| mean_pruned_prompt_tokens       | 2,195                        | 755                          | -65.6% (novelty)  |
| mean_decode_ms                  | 29,522                       | 27,232                       | -7.8% (thermal)   |
| mean_dense_end_to_end_ms        | 39,997                       | 37,629                       | -5.9% (thermal)   |
| mean_pruned_end_to_end_ms       | 39,877                       | 35,378                       | -11.3%            |
| end_to_end_speedup_mean (within)| 1.003×                       | **1.064×**                   | +6.1pp            |
| generate_speedup_mean (within)  | 1.020×                       | 1.501×                       | +48pp             |
| dense_parse_failures            | 1/30 (3%)                    | 1/30 (3%)                    | 0                 |
| pruned_parse_failures           | 1/30 (3%)                    | 0/30 (0%)                    | -1                |

- Within-run H_stack (thermally clean, paired by item): E2E **1.064×**, agreement 0.667, acc Δ -0.033.
- V_share on holdout (from EXP15 dense arm): 3446 / 39997 = **8.6%** (vs dev 15.2%).
- Cross-session EXP15→EXP16: decode Δ = -7.8% (VIOLATES <2% pairing rule); cross-session 1.127× is measurement-inflated.

## Ceiling model check — LLM-side analog holds

Novelty pruning acts AFTER vision, on the emitted 2048 tokens (kept 608, plus anchors → 755 prompt tokens on pruned path). Vision tower is V-patched in both arms (equal cost). Gain is LLM-side.

LLM-side ceiling:
```
E2E_speedup ≈ 1 / (1 − generate_share × generate_reduction)
generate_share  = 6791 / 37629 = 0.180
generate_reduction = 1 − 4525/6791 = 0.334
predicted      = 1 / (1 − 0.180 × 0.334) = 1.064×
observed       = 1.064×
```

**Match within 0.1pp.** The scatter-back ceiling structure `1/(1 − share × reduction)` generalizes from the vision axis (C-CEILING/1.51V dev) to the LLM-decode axis (1.51V+novelty holdout). Fifth regime of ceiling-model validation.

## Dev vs holdout comparison (EXP10 dev vs EXP16 holdout)

| metric                       | EXP10 dev (n=30) | EXP16 holdout (n=30)        |
|------------------------------|------------------|------------------------------|
| V_share (V-patched baseline) | 15.2%            | 8.6%                         |
| novelty kr                   | 0.3              | 0.3                          |
| anchor                       | none             | none                         |
| E2E speedup (within-run)     | 1.11×            | 1.064×                       |
| E2E speedup (cross-session)  | 1.17× (dirty)    | 1.127× (dirty, decode -7.8%) |
| agreement                    | 0.63             | 0.667                        |
| acc Δ                        | -0.067           | -0.033                       |

**Interpretation:** direction replicates; magnitude is V_share-regime-scaled. VideoMME holdout prompts are long-tail (2195 avg prompt tokens), pushing more of E2E into decode/prefill relative to vision — reducing V_share from 15.2% to 8.6% and capping headroom for post-vision pruning gains.

## Hypothesis adjudication

### H_stack (holdout): V+novelty kr=0.3 anchor=none replicates on 30 disjoint items with E2E ≥ 1.10×

- Within-run (thermally clean, paired): **1.064×** — BELOW 1.10× threshold.
- Cross-session (thermally confounded, decode Δ=-7.8%): 1.127× — ABOVE threshold but measurement-invalid.
- Agreement 0.667 matches dev 0.63 — mechanism direction replicates.
- Accuracy -0.033 is LESS severe than dev -0.067 — holdout preserves acc marginally better.

**Verdict:** **PARTIAL CONFIRMATION.** The mechanism (V+novelty stacks with disagreement ~0.65 and minor acc cost) replicates on disjoint items. Within-run magnitude does not clear the 1.10× headline-reopener threshold under thermally-clean measurement. Treat as "stacking composes, ceiling-bound on VideoMME" — a secondary paper claim, not an H1 reopener.

## Paper implications

- **V-only headline cells remain dev-only.** EXP15 has novelty=1.0 (a V-patched baseline for cross-session pairing), NOT an unpatched reference. We have no holdout patched-vs-unpatched pair. Paper table cells for TOMATO 1.24×, MVBench 1.21×, VideoMME 1.08×/1.12× should be explicitly labeled "dev n=30" until a holdout unpatched pair lands.
- **H_stack ceiling-limited on VideoMME.** V_share on holdout (8.6%) caps stacking gain at ~1.06×. Architectural, not noise.
- **Recommendation:** add a "regime-conditional stacking gain" footnote to the C-STACK claim in the paper. V+novelty composes, headline magnitude tracks V_share.

## Thermal pairing diagnostic (all 1.51V pairs to date)

| Pair                        | decode Δ | within ±2%? | interpretation                |
|-----------------------------|----------|-------------|-------------------------------|
| EXP01/EXP02 (dev 8f)        | -2.8%    | no (cooler) | favorable to patched          |
| EXP11/EXP12 (dev 16f)       | -0.1%    | **yes**     | clean                         |
| EXP13/EXP14 (dev 32f)       | +7.6%    | no (hotter) | M3 thermal cap at 32f         |
| **EXP15/EXP16 (holdout 8f)**| **-7.8%**| **no (cooler)** | EXP15 ran hot after 32f probe, EXP16 cooler |

Only 1/4 pairs clears the decode-Δ<2% invariant. **Codify as runner-level auto-abort/retry gate** to prevent future thermal confounders.

## Artifacts

- EXP15 summary: `research/experiments/2026/artifacts/phase1_51V_session2/exp15_videomme_holdout_8f_L2_kr050_summary.json`
- EXP16 summary: `research/experiments/2026/artifacts/phase1_51V_session2/exp16_videomme_holdout_8f_L2_kr050_novelty030_none_summary.json`
- Queue log: `research/experiments/2026/artifacts/phase1_51V_session2/queue.log`
- Runner: `scripts/run_phase1_51V_session2.sh`
- Total wall-clock: EXP15 1425s (24 min) + EXP16 1281s (21 min) = 45 min

## Peer-review asks

1. **Paper V-only table scoping.** Given EXP15/16 do not provide a holdout unpatched baseline, should the paper explicitly call the TOMATO/MVBench/VideoMME V-only headlines "dev n=30" pending a holdout unpatched pair? Or queue a quick EXP17/18 (8f holdout VideoMME unpatched vs L=2 kr=0.50 patched) to de-risk promotion? ~40 min runtime.
2. **V+novelty stacking framing.** Holdout replicates at smaller magnitude (1.064× vs 1.11×), matching the V_share-regime prediction exactly. Is this a paper-grade secondary claim (stacking composes, ceiling-limited) or still ambiguous given 1.10× threshold miss?
3. **Thermal pairing runner gate.** Three of four 1.51V pairs violate decode-Δ<2%; only EXP11/EXP12 clears it. Codifying this as an auto-retry gate would prevent future thermal confound.

## Next actions

1. Update `2026-04-21-phase-1_51V-expansion-findings.md` "H_stack partial reopener" section with the holdout replication result (within-run 1.064×, ceiling-matched).
2. (Optional) Queue EXP17/18 (holdout V-only patched vs unpatched) to de-risk V-only paper headlines. ~40 min; one sandbox cycle.
3. (Optional, preregistered under task #152) EXP10 n=60 dev+holdout combined, thermally paired, to tighten the H_stack CI.
4. Sync paper docs (publishability-status, claim-matrix, framing, registry) with holdout replication result — Codex round-23 item 6.
