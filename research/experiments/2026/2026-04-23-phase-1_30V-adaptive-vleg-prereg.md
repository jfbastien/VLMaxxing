---
phase: 1.30V
date: 2026-04-23
parent:
  - research/experiments/2026/2026-04-23-phase-1_30-rootcause-findings.md
status: preregistered
scope: Q0-only adaptive V-leg diagnostic on the same ten short-scout items used by Phase 1.30 root-cause
---

# Phase 1.30V — adaptive V-leg diagnostic

## Motivation

Phase 1.30 root-cause localized the Sam-style Qwen 7B 8f composition loss
primarily to the V-only Q0 pruning leg at `L=2`, `kr_V=0.50`. The immediate
scientific question is whether that is an unavoidable C-VISION/Qwen failure on
these items or simply an over-aggressive operating point.

This diagnostic is intentionally Q0-only and same-item. It is not a new
deployment claim. It asks whether a more conservative V leg can recover enough
Q0 accuracy to justify a later full session rerun.

## Dataset

Use the Phase 1.30 root-cause Q0 manifest generated from:

- `research/experiments/2026/artifacts/phase1_30_rootcause_short_codex_20260423/cold_pruned.jsonl`

Manifest:

- `/tmp/phase1_30_q0_codex_manifest.toml`

Items: the ten short-bucket Q0 items from Phase A.

## Arms

Existing anchors:

- dense reference: `q0_151V_dense`
- failed V leg: `q0_151V_pruned`, `L=2`, `kr_V=0.50`

New arms:

- `q0_151V_L2_kr067`
- `q0_151V_L2_kr075`

All arms use Qwen 2.5-VL-7B-Instruct-4bit, 8 frames, max_tokens 32, and the
same `run_phase1_51V.py` path used for Phase B.

## Hypotheses and gates

**H_recover.** A more conservative keep-rate recovers the Q0 accuracy cliff.

Pass if either `kr_V=0.67` or `kr_V=0.75` reaches:

- Q0 accuracy >= 0.80 on the ten-item Q0 set, and
- choice agreement with dense >= 0.80.

This is still a scout gate; n=10 cannot promote a paper claim.

**H_budget.** The recovered arm still removes enough vision work to matter.

Pass if the recovered arm has `mean_effective_keep_rate <= 0.75`.

This is deliberately weak because the goal is to find a candidate admission
policy, not to maximize speed in the scout.

**Decision rule.**

- If H_recover and H_budget both pass, queue a full 1.30 session rerun with the
  recovered V leg as the next composition experiment.
- If H_recover fails at both keep-rates, deprioritize naive fixed-kr composition
  on Qwen and move to adaptive admission: no-prune on high-risk Q0 items, or
  content/confidence-gated V pruning.
- If accuracy recovers only at kr=0.75 but budget is marginal, treat it as a
  boundary point and do not claim deployment composition without a session run.

## Expected runtime

Each Q0 arm is about 5-8 minutes on the local M3 Air. Total run time for both
new arms is expected to be 10-20 minutes.
