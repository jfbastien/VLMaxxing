---
phase: 1.51V
date: 2026-04-21
parent: research/experiments/2026/2026-04-20-phase-1_51V-expansion-prereg.md
prior:
  - research/experiments/2026/2026-04-21-phase-1_51V-expansion-findings.md
status: proposed (awaiting sandbox approval)
runtime_estimate: ~90 min (n=30 VideoMME 32f unpatched + L=2 kr_V=0.50 pair, thermally paired)
---

# 1.51V 32-frame follow-on probe — V_share growth and ceiling re-test

## Motivation

The 1.51V expansion batch (2026-04-21) showed **H_fsscale favorable violation** at 16f: V_share grew 15.2% → 24.3% (+9.1pp), exceeding the preregistered ratio-bounded 5pp tolerance. E2E at 16f matched the ceiling-model prediction (1.12× obs vs 1.105× pred). The preregistered decision rule triggered: "If Tier 4 shows V_share > 0.22 at 16f, 1.51V ceiling re-opens for longer-horizon regimes."

A 32f probe tests whether V_share continues to grow and how much headline E2E the 1.51V mechanism can reach before decode begins to dominate again.

## Hypotheses

### H_32f_vshare
V_share at 32f ≥ 30% (continuing the 15.2% → 24.3% trajectory). If V_share plateaus below 30%, the ceiling model says headline E2E stays below ~1.15×.

### H_32f_e2e
At V_red ≈ 40% (kr_V=0.50 benchmark-invariant from expansion batch), observed E2E at 32f ≥ 1.15× on thermally-paired unpatched-vs-patched pair.

### H_32f_acc
Long-bucket accuracy at 32f does NOT collapse below 0.05 (prior memory: 32f long-bucket accuracy was 0.10 for dense; 1.51V pruning may degrade further).

## Decision rules

- **V_share > 0.30 at 32f AND E2E > 1.15×**: H3 architectural re-opener CONFIRMED. Write this as a secondary paper claim (frame-count-dependent ceiling).
- **V_share < 0.22 at 32f**: ceiling collapses back (decode dominates again at 32f). Close the 32f regime as a dead-end and promote 16f as the ceiling-max cell.
- **Long-bucket acc < 0.05**: demote 32f from headline, report as frame-count-fragile.

## Queue

All runs: `gemma-4-e4b-it-4bit`, `max-tokens=32`, `rss-guard-mb=10000`, n=30 on VideoMME dev v1.

- **EXP13 `videomme_32f_unpatched`**: 32f, anchor=none, kr_novelty=1.0, unpatched. Thermal anchor for EXP14. (~45 min)
- **EXP14 `videomme_32f_L2_kr050`**: same but L=2 kr_V=0.50. (~45 min)

Thermal pairing: decode_ms Δ < 2% across the pair; wider drift flags the pair for re-run.

## What this does NOT do

- Does not probe 32f on MVBench or TOMATO (those are already paper-grade at 8f with the highest V_shares; 32f adds nothing to their story).
- Does not probe 32f on 1.51R composition (Stage 6 already covered that).
- Does not re-run 8f or 16f cells (H1/H_pareto/H_fsscale already CONFIRMED).

## Estimated total runtime

~90 min wall-clock, n=30 × 2 experiments, single sandbox approval for the pair.

## Runner

Proposed extension of `scripts/run_phase1_51V_expansion.sh` — add EXP13/EXP14 to the queue tail with `.done` sentinels. Idempotent resume semantics preserved.

## Artifacts (target)

- `research/experiments/2026/artifacts/phase1_51V_32f_probe/exp13_videomme_32f_unpatched_summary.json`
- `research/experiments/2026/artifacts/phase1_51V_32f_probe/exp14_videomme_32f_L2_kr050_summary.json`
- Findings doc on completion: `research/experiments/2026/2026-04-21-phase-1_51V-32f-probe-findings.md`
