---
phase: 1.51V
date: 2026-04-20
parent: research/experiments/2026/2026-04-18-phase-1_51V-vision-tower-pruning-prereg.md
prior:
  - research/experiments/2026/2026-04-20-phase-1_51V-dev-tranche-findings.md
  - research/experiments/2026/2026-04-20-phase-1_51V-n30-findings.md
status: running (autonomous batch 2026-04-20)
---

# 1.51V expansion — Pareto completion, cross-benchmark transfer, frame-scaling, stack re-runs

## Motivation

1.51V at L=2 kr=0.50 closed with H1 EARNED (V_red=42.2% thermally normalized) and H3 VIOLATED (architectural cap 1.16×). Three open questions remain before the paper narrative is complete:

1. **Is the 42% V-reduction stable under matched thermal conditions?** The closing measurement relied on a composition-run dense arm as thermal proxy. A back-to-back unpatched-vs-patched pair removes that indirection.
2. **Does 1.51V transfer to other benchmarks or other frame counts?** VideoMME dev is our only data point. MVBench motion dev + TOMATO motion dev are paper-grade, and 16f frame scaling probes whether V_share is ratio-bounded in a decode-dominant regime.
3. **Does a different novelty anchor earn on V-patched features?** 1.51R was null with `anchor=none` on VideoMME. V-patched features are geometrically different (top-k retained post-L=2) and may change the novelty statistic's behavior, particularly under `gemma_structural` or aggressive kr.

## Queue (priority-ordered, executed back-to-back by single process)

Each run uses `gemma-4-e4b-it-4bit`, `max-tokens=32`, `rss-guard-mb=10000`. Artifacts land in `research/experiments/2026/artifacts/phase1_51V_expansion/`.

### Tier 0 — Thermally-paired VideoMME 8f at L=2 (confirmation)

- **EXP01 `videomme_8f_unpatched`**: VideoMME dev v1 n=30, 8f, anchor=none, kr_novelty=1.0, unpatched. (~35 min). **Serves as thermal anchor for EXP02–EXP04, EXP09–EXP10.**
- **EXP02 `videomme_8f_L2_kr050`**: same but L=2 kr_V=0.50. (~35 min)

**H_confirm**: V_red in back-to-back pair EXP01/EXP02 clears 35% threshold (H1 stable); decode_ms delta < 2% (thermal pairing clean).

### Tier 1 — L=2 Pareto completion on VideoMME 8f

- **EXP03 `videomme_8f_L2_kr025`**: L=2 kr_V=0.25 (aggressive). (~35 min)
- **EXP04 `videomme_8f_L2_kr075`**: L=2 kr_V=0.75 (conservative). (~35 min)

**H_pareto**: at kr_V=0.25, V_red > 55% and acc drops below control − 0.10; at kr_V=0.75, V_red ∈ [15%, 25%] with acc preserved within CI.

### Tier 2 — Cross-benchmark transfer

- **EXP05 `mvbench_8f_unpatched`**: MVBench motion dev v2 n=30, 8f, unpatched. (~25 min)
- **EXP06 `mvbench_8f_L2_kr050`**: same but L=2 kr_V=0.50. (~25 min)
- **EXP07 `tomato_8f_unpatched`**: TOMATO motion dev v2 n=30, 8f, unpatched. (~25 min)
- **EXP08 `tomato_8f_L2_kr050`**: same but L=2 kr_V=0.50. (~25 min)

**H_transfer**: V_red (EXP05→EXP06) ≥ 30% and (EXP07→EXP08) ≥ 30%. Accuracy preserved within n=30 CI on both.

### Tier 3 — 1.51R anchor re-run on V-patched features

- **EXP09 `videomme_8f_L2_kr050_novelty050_structural`**: L=2 kr_V=0.50 + novelty kr=0.5 anchor=gemma_structural. (~40 min)
- **EXP10 `videomme_8f_L2_kr050_novelty030_none`**: L=2 kr_V=0.50 + novelty kr=0.3 anchor=none. (~40 min)

**H_stack**: neither composition lifts E2E speedup above the 1.51V-alone observation (1.07×) — novelty adds no marginal value on V-patched features (confirm prior null) OR does show a signal (new positive result).

### Tier 4 — Frame-scaling probe

- **EXP11 `videomme_16f_unpatched`**: VideoMME dev v1 n=30, 16f, unpatched. (~70 min)
- **EXP12 `videomme_16f_L2_kr050`**: same but L=2 kr_V=0.50. (~70 min)

**H_fsscale**: V_share at 16f is within 5pp of V_share at 8f (ratio-bounded). 1.51V E2E ceiling at 16f ≤ 1.20×.

## Estimated total benchmark runtime

- Tier 0: 70 min
- Tier 1: 70 min
- Tier 2: 100 min
- Tier 3: 80 min
- Tier 4: 140 min

**Total: ~460 min = 7.7 hours**, plus ~10-20 min total model-load overhead. Target budget: 8 h.

## Methodology

- **Thermal pairing**: each patched run is immediately preceded by its unpatched control. Decode_ms should be within 2% across the pair; wider drift invalidates the V_red measurement for that pair.
- **Sandbox**: single-process execution via `scripts/run_phase1_51V_expansion.sh` launched once with Metal/sandbox-disabled approval. No per-run user intervention needed.
- **Idempotent resume**: each experiment touches `<out>/<name>.done` on success; re-invocation skips completed experiments.
- **Validation at each step**: artifacts include `<name>.jsonl` (per-item), `<name>_summary.json` (aggregate), `<name>.log` (stdout/stderr).

## Decision rules

- If EXP01/EXP02 thermal pairing shows V_red within [35%, 50%], H1 is **confirmed** (not just earned under indirection).
- If any Tier 2 benchmark shows V_red < 20% or acc drop > 15pp, 1.51V does NOT transfer cleanly to that benchmark — demote to VideoMME-only in paper.
- If Tier 3 shows any E2E speedup > 1.15× on composition, the 1.51R null lane **re-opens** conditional on V-patched features.
- If Tier 4 shows V_share > 0.22 at 16f, 1.51V ceiling re-opens for longer-horizon regimes.

## Follow-ons (not in this batch, queued pending results)

- 32f regime smoke at L=2 kr=0.50 (only if Tier 4 shows V_share growth).
- 1.51V on VideoMME holdout (only if Tier 0 confirms H1 under thermal pairing).
- Post-pool token merging prototype (H3 re-opener; requires new code).
- Different vision-tower layers (L=3, L=4) at kr=0.25 to widen the Pareto.

## Artifacts

- Runner: `scripts/run_phase1_51V_expansion.sh`
- Output root: `research/experiments/2026/artifacts/phase1_51V_expansion/`
- Findings doc (on completion): `research/experiments/2026/2026-04-21-phase-1_51V-expansion-findings.md`
