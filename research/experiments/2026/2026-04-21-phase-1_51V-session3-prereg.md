---
phase: 1.51V
date: 2026-04-21
parent: scripts/run_phase1_51V_session3.sh
prior:
  - research/experiments/2026/2026-04-21-phase-1_51V-holdout-findings.md
  - research/experiments/2026/2026-04-21-phase-1_51V-expansion-findings.md
status: prereg (session 3 — V-only holdout unpatched/patched pair)
---

# 1.51V session 3 prereg — V-only holdout unpatched vs V-patched (EXP17/18)

## Motivation

Session 2 (EXP15/16) delivered H_stack partial confirmation on the VideoMME
holdout v1 set but did **not** measure V-only on holdout. EXP15 is a V-patched
reference (L=2, kr_V=0.50, novelty=1.0), not an unpatched baseline. The paper's
V-only headline cells (TOMATO 1.24×, MVBench 1.21×, VideoMME 8f 1.08×, 16f 1.12×)
are therefore still **dev-only** per registry and claim-matrix C-VISION row.

Session 3 closes this gap on the VideoMME-8f cell by running a thermally-paired
unpatched/patched pair on the holdout v1 set:

- **EXP17**: VideoMME holdout v1, 8f, unpatched (no vision-tower slice), novelty=1.0.
- **EXP18**: VideoMME holdout v1, 8f, V-patched L=2 kr_V=0.50, novelty=1.0
  (identical config to EXP15, re-run paired with EXP17 in the same session).

Running EXP18 fresh rather than pairing EXP17 against EXP15 cross-session avoids
the thermal-pairing violation that cost session 2 (EXP15/EXP16 decode Δ = −7.8%).

## Hypotheses (preregistered)

### H_holdout_vonly_e2e (primary)

**Paired within-run E2E speedup (EXP17 dense vs EXP18 pruned) ≥ 1.05×.**

The dev V-only headline on VideoMME 8f is 1.08× (V_share 15.2% × V_red 39%).
Holdout V_share is ~8.6% (per EXP15 dense arm), so the ceiling-model prediction is
`1/(1 − 0.086 × 0.39) = 1.034×`. We preregister 1.05× as the "surprise-lift"
threshold; ≥1.05× would indicate the holdout is actually closer to dev in V_share
than the EXP15 measurement suggested (or there's per-item variance we should
investigate). Between 1.00× and 1.05× is the expected "ceiling-confirmed, V_share-
bound" outcome and the primary finding we expect.

**Failure condition:** paired speedup < 1.00× (patched is slower than unpatched on
matched items) — would falsify the scatter-back mechanism on holdout items.

### H_holdout_vred (primary)

**Vision-tower time reduction (EXP17 mean_dense_vision_ms vs EXP18 mean_pruned_vision_ms)
∈ [0.35, 0.45].**

Preregistered from the benchmark-invariant V_red ~40% at kr=0.50 observation
(5-regime ceiling-model validation, claim-matrix C-VISION). Holdout should not
be an architectural outlier; a V_red outside [0.35, 0.45] would be notable.

### H_holdout_thermal (process)

**Decode Δ across EXP17/EXP18 pair: |decode_ms(pruned) − decode_ms(dense)| / decode_ms(dense) < 2%.**

Three of four 1.51V pairs have violated this gate. Session 3 will explicitly check
the gate and treat the pair as measurement-invalid if it fails. If violated, flag
for auto-retry under a codified runner-level gate (deferred to future work).

### H_holdout_accuracy (secondary)

**Paired accuracy Δ (EXP18 − EXP17) ∈ [−0.050, +0.050]** (scatter-back preserves
pooler geometry; accuracy should be neutral).

## Non-hypotheses (explicit non-goals)

- No stacking with novelty pruning (that's H_stack, partial-confirmed session 2).
- No accuracy-lift chase; scatter-back is neutral-by-design.
- No MVBench or TOMATO holdout (can be queued later if VideoMME holdout reopens
  paper-table promotion).

## Configuration

```
model-path        $GEMMA_MODEL_PATH
manifest          research/benchmark_manifests/videomme_holdout_v1.toml
frame-count       8
n                 30 (full holdout v1)
max-tokens        32
rss-guard-mb      10000
anchor-arm        none
keep-rate         1.0 (novelty disabled on both arms)

EXP17 (unpatched):   no --vision-tower-layer, no --vision-tower-keep-rate
EXP18 (V-patched):   --vision-tower-layer 2 --vision-tower-keep-rate 0.50
```

## Runtime

Estimated ~22 min per experiment from session 2 observations (EXP15 = 1425 s,
EXP16 = 1281 s). Total ~45 min wall-clock.

## Adjudication rules

- **H_holdout_vonly_e2e**: CONFIRMED if paired E2E ≥ 1.05× AND thermal gate passes.
  EARNED if ≥ 1.05× with thermal gate failing (diagnostic). NULL if < 1.05× with
  thermal gate passing.
- **H_holdout_vred**: CONFIRMED if V_red ∈ [0.35, 0.45]. EARNED/violated if outside.
- **H_holdout_thermal**: PASS/FAIL gate; determines measurement validity of above.
- **Paper promotion rule**: if H_holdout_vonly_e2e passes AND H_holdout_vred passes,
  the VideoMME 8f V-only cell in the paper table can drop the "dev-only" caveat.
  If H_holdout_vonly_e2e fails but H_holdout_vred passes, update C-VISION narrative
  to "V_red mechanism generalizes to holdout; E2E magnitude bounded by low holdout
  V_share" (still paper-grade, just regime-conditional framing).

## Artifacts expected

- `research/experiments/2026/artifacts/phase1_51V_session3/exp17_videomme_holdout_8f_unpatched_summary.json`
- `research/experiments/2026/artifacts/phase1_51V_session3/exp18_videomme_holdout_8f_L2_kr050_summary.json`
- `research/experiments/2026/artifacts/phase1_51V_session3/queue.log`
- Runner: `scripts/run_phase1_51V_session3.sh`
- Findings doc: `research/experiments/2026/2026-04-21-phase-1_51V-session3-findings.md`
