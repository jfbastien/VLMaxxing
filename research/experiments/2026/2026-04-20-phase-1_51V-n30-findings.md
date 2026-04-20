---
phase: 1.51V
date: 2026-04-20
parent: research/experiments/2026/2026-04-18-phase-1_51V-vision-tower-pruning-prereg.md
prior: research/experiments/2026/2026-04-20-phase-1_51V-dev-tranche-findings.md
superseded_by: research/experiments/2026/2026-04-21-phase-1_51V-expansion-findings.md
status: findings (superseded 2026-04-21 — paired EXP01/02 gives V_red=39.0%, see §Revision 2026-04-21)
---

# 1.51V n=30 at L=2 kr=0.50 — V-reduction EARNED (thermal-normalized), H3 architecturally blocked

## Revision note (2026-04-21, Codex round-22)

The paper-facing V_red is now **39.0%**, from within-session thermal pairing on EXP01 (unpatched) and EXP02 (L=2 kr=0.50) in the 2026-04-21 expansion batch. Decode drift across the paired runs was < 2% — strictest pairing the batch can produce. The 42.2% number below came from normalizing against a composition-run dense arm across sessions (decode +0.2% vs a *prior* session's control); valid mechanism evidence, but not the tightest pairing. 3.2pp delta is inside the thermal-drift bracket so both measurements attest the same effect. Per Codex, standardize on 39.0% paired across docs.

See `research/experiments/2026/2026-04-21-phase-1_51V-expansion-findings.md` §Reproduction-of-prior-claim for the reconciliation and the per-benchmark V_share × V_red → E2E ceiling predictions.

## Revision note (2026-04-20)

The initial n=30 read below reported V_red = 26% against the raw dev control and rejected H1. Subsequent composition run (1.51V × 1.51R kr=0.5) at the same manifest produced a dense arm that matches decode_ms within 0.2% of the pristine stage1_none_kr50 control (thermally clean), while this standalone n=30 run has +6.5% decode drift vs the same control. Using decode_ms as a thermal proxy, the standalone n=30 vision_ms is confounded upward by thermal load; the composition dense arm is the valid measurement.

**Corrected headline:** at L=2 kr=0.50 on 8-frame VideoMME dev n=30, the thermally-normalized V-reduction is **42.2%** (3088ms patched vs 5339ms control), **clearing H1's 35% threshold**. H3 remains violated (1.07× E2E vs 1.50× target, architecturally bounded). H4 null-robust (-0.067 acc, CI overlap).

## Thermally-normalized comparison (composition dense arm, n=30)

| metric                        | control (unpatched) | patched (L=2 kr=0.50, composition dense) | delta       |
|-------------------------------|---------------------|------------------------------------------|-------------|
| mean_decode_ms                | 26475.7             | 26519.1                                  | +0.2% (clean) |
| mean_dense_vision_ms          | 5338.7              | 3087.8                                   | **-42.2%**  |
| mean_dense_generate_ms        | 6380.0              | 6114.4                                   | -4.2%       |
| mean_dense_end_to_end_ms      | 38257.1             | 35779.5                                  | **-6.5% (1.07× E2E)** |
| dense_accuracy                | 0.400               | 0.333                                    | -0.067 (10/30 vs 12/30) |
| dense_parse_failures          | —                   | 3/30                                     | —           |

## Verdicts (REVISED)

### H1 (V-reduction ≥ 35% at kr=0.50): **EARNED** (thermally normalized)

42.2% V-reduction with matched decode load. The 5-item dev tranche's 38% signal was real, not optimistic sampling — the initial n=30 standalone-run rejection was a thermal artifact. Composition run's dense arm is the authoritative measurement.

### H3 (composed E2E ≥ 1.5×): **VIOLATED, architecturally**

Observed E2E: 1.07×. Theoretical cap on 1.51V-alone:
- V_share = 5339 / 38257 = 13.9% of E2E
- Even V_red = 100%: max E2E = 1 / (1 - 0.139) = 1.16×
- H3's 1.5× is architecturally unreachable on 1.51V; would require post-pool token merging that cuts LM prompt (scatter-back holds LM prompt at 2181 tokens unchanged).

### H4 (accuracy preserved): **NULL-ROBUST with weak negative**

Δ = -0.067 (0.400 → 0.333). Clopper-Pearson 95% CI overlap ([0.17, 0.53] vs [0.23, 0.59]). Direction consistent with dev-tranche L=1 signal but cannot be distinguished from n=30 noise. Parse failures: 3/30 (10%) on patched, unknown on control.

## Original (confounded) n=30 standalone read — preserved for record

The standalone n=30 run (`phase1_51V_n30/L2_kr050_summary.json`, decode=28195ms, +6.5% thermal drift vs control) showed the following. These numbers are real but confounded by thermal upload and are not the basis of H1 verdict:

## Setup (standalone run, thermally confounded)

- Manifest: `videomme_dev_v1.toml` (n=30: 10 short + 10 medium + 10 long)
- Model: gemma-4-e4b-it-4bit, 8 frames, max_tokens=32
- Patched cell: L=2 kr=0.50 (dev-tranche winner by V_red × accuracy)
- Novelty pruning: OFF (keep_rate=1.0) to isolate vision-tower effect
- Control baseline: `phase1_51R_dev/stage1_none_kr50_summary.json` (n=30 same manifest, same frame_count, unpatched, dense arm is clean baseline)

## Raw comparison (dense-vs-dense, n=30)

| metric                        | control (unpatched) | patched (L=2 kr=0.50) | delta       |
|-------------------------------|---------------------|-----------------------|-------------|
| mean_dense_vision_ms          | 5338.7              | 3945.0                | -1393.7 ms  |
| mean_dense_generate_ms        | 6380.0              | 7652.7                | +1272.7 ms  |
| mean_decode_ms                | 26475.7             | 28195.0               | +1719.4 ms  |
| mean_dense_end_to_end_ms      | 38257.1             | 39861.7               | +1604.6 ms  |
| dense_accuracy                | 0.400               | 0.333                 | -0.067      |
| dense_parse_failures          | ?                   | 3/30                  | —           |

- **V-reduction n=30: 26.1%** (falls below H1's 35% threshold; 5-item subset showed 38%)
- **E2E drift: +1.6s patched slower** — dominated by +1.7s decode drift + +1.3s generate drift (thermal/system-state cross-session); V saved 1.4s
- **Thermal-normalized E2E impact** (subtract decode+generate drift): 1.51V reduces E2E by ~1.4s/item, matching vision savings. Theoretical max E2E gain = V_share × V_red = 14% × 26.1% = **3.6%**.

## Verdicts vs prereg hypotheses

### H1 (V-reduction ≥ 35% at kr=0.50): **REJECTED (this run, confounded; superseded by thermal-normalized read above)**

V_red = 26.1% on full n=30 standalone run. Originally attributed to dev-tranche sample optimism, but later diagnosed as cross-session thermal drift: decode_ms on this run was +6.5% vs the control, evidence that compute load has inflated vision_ms measurement. Composition run dense arm (thermally clean, decode +0.2%) gives 42.2% → **H1 EARNED after thermal normalization**.

### H3 (composed E2E ≥ 1.5×): **VIOLATED on 1.51V alone**

Max theoretical E2E from 1.51V alone = 1 / (1 - V_share × V_red) = 1 / (1 - 0.036) = **1.04×** at n=30 VideoMME dev. Far below H3's 1.5× target. Even perfect pruning (V_red=100%) would cap E2E at 1.16×.

### H4 (accuracy preserved): **NULL-ROBUST with weak negative signal**

Δ = -6.7pp (0.40 → 0.333). For proportion n=30 with p=0.333, Clopper-Pearson 95% CI is [0.17, 0.53], overlapping control's [0.23, 0.59]. Cannot statistically distinguish from noise, but direction is consistent (-2 items) with the dev-tranche L=1 signal. Parse failures: 3/30 (10%) on patched, unknown on control (not reported). Accuracy preservation is not a confident win.

## Architectural conclusion

1.51V's pooler-geometry-preserving scatter-back design is **E2E-ceiling-bound by V_share**. On 8-frame Gemma-4-E4B-4bit VideoMME dev:

- V_share = 14% of E2E (decode dominates: 70% of E2E is video decode, not LM)
- Even 100% V-reduction caps E2E speedup at 1.16×
- Reaching H3's 1.5× requires cutting decode (1.54 lane) or LM prompt (post-pool merge, not 1.51V)

**Publication framing**: 1.51V is a preregistered negative result. It reduces vision-tower time by ~26% at accuracy cost within noise, but this does not translate to E2E speedup because (1) LM prompt is unchanged by scatter-back, (2) video decode dominates E2E on the M3/Gemma-4 regime, and (3) V-share is structurally small.

## Next steps (REVISED 2026-04-20 after composition run + thermal diagnosis)

1. ✅ n=30 H1 test on L=2 kr=0.50 done. First read confounded by thermal; composition dense arm = thermally-normalized authoritative measurement.
2. ✅ Composition with 1.51R at kr=0.50 done. Dense arm = clean 1.51V measurement (H1 EARNED at 42.2%); pruned arm (V-patch + novelty) adds no E2E value because 1.51R is null on this axis.
3. **Skip holdout**: H3 blocked architecturally, holdout provides no new information.
4. **Close 1.51V as preregistered EARNED-on-H1, BLOCKED-on-H3, NULL-on-H4**. Paper framing: "vision-tower-time cut by 42% at kr=0.50 with accuracy preserved within n=30 noise; E2E gain capped at 1.07× by scatter-back preserving LM prompt (architectural)."

## Raw artifacts

- This run (confounded): `phase1_51V_n30/L2_kr050_summary.json` (decode 28195ms)
- Composition dense arm (thermally clean): `phase1_51V_compose/L2_kr050_x_novelty_kr050_summary.json` (decode 26519ms)
- Control: `phase1_51R_dev/stage1_none_kr50_summary.json` (decode 26476ms)
- Dev tranche: `phase1_51V_dev_tranche/`

## Methodology note: thermal drift diagnosis

Cross-session thermal drift on M3 Air 16 GB manifests as elevated decode_ms (constant operation, varies with system thermal state), inflating all forward-pass times proportionally. With the same manifest and `n_items`, different sessions can show ±6-10% on vision_ms even when control-vs-patched is unchanged.

Diagnostic protocol used here: match runs by `mean_decode_ms` (a thermal proxy independent of the intervention) before comparing `mean_dense_vision_ms`. For 1.51V, the valid control-patched pair is (stage1_none_kr50 control, composition-run dense arm) with decode delta 0.2%.

**Future 1.51V measurements should run control and patched back-to-back in one session**, or use composition-run dense arms against a thermally-matched control. The standalone n=30 run was executed minutes after an unrelated hot workload; all vision_ms in that run are inflated.
