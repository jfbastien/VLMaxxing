---
date: 2026-04-27
status: staged; not yet run
---

# Paper Deep-Mechanism Queue Runbook

## Purpose

This queue is the post-review mechanism batch. It is not the broad deployment
baseline batch and it does not edit the paper. It runs three sequential
experiments:

1. **1.63E** — Track B Qwen frame-budget scaling at 16f/20f/32f.
2. **1.63G** — Gemma Track B sparse-ViT architecture check.
3. **1.65** — dense logit-margin predictor scout for paired stability.

The goal is to turn the paper's remaining mechanism claims from single-point
or descriptive evidence into cross-budget, cross-architecture, and predictive
evidence.

## Launch

Dry run:

```bash
./.venv/bin/python scripts/run_paper_deep_mechanism_queue.py --dry-run
```

Autonomous run with per-phase commits:

```bash
nohup ./.venv/bin/python scripts/run_paper_deep_mechanism_queue.py --auto-commit \
  > /tmp/claude/deep_mechanism_queue.log 2>&1 &
```

Optional overrides:

- `PHASE1_63E_FRAME_COUNTS="16 20 32"` controls Qwen frame-budget cells.
  If the 8f 1.63 summary is already present, it is included as a non-veto
  reference. If 8f has not run and should be part of this batch, set
  `PHASE1_63E_FRAME_COUNTS="8 16 20 32"` so it is computed as a normal cell.
- `PHASE1_65_MAX_ROWS=0` runs the full logit-margin source set instead of the
  default 180-row balanced scout.

## Expected Runtime

- 1.63E: ~6-8 h.
- 1.63G: ~2.5-3.5 h.
- 1.65: ~3-6 h at default `PHASE1_65_MAX_ROWS=180`; longer if full scoring.
- Total: ~11.5-17.5 h default, sequential, no parallel MLX work.

## Interpretation Checklist

- If 1.63E passes across all new frame counts, C-CEILING is predictive across
  frame budgets for Qwen Track B vision-only sparse execution.
- If 1.63G passes, Track B sparse-ViT evidence is not Qwen-only.
- If 1.65 passes, dense margin becomes a measurable stability signal; report it
  as an oracle-feature predictor scout, not a deployed guard.
- If any Track B cell skips vision work but lacks end-to-end positivity, keep
  the result as a systems boundary: real ViT work was skipped, but non-ViT
  stages dominated the local wall-clock.
