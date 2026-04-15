# Phase 1.33: FastVID Baseline Comparison

## Preregistration

Objective:

- run FastVID (arXiv 2503.11187) on the same Qwen 2.5-VL TOMATO and
  MVBench motion slices to establish a video-specific within-frame
  token-reduction baseline for our paper's comparison table.
- FastVID is the nearest direct competitor in the "attention-score
  token pruning on Qwen 2.5-VL" space; any paper claim we make must
  contextualize our Pareto against it.

Claim register targets:

- Paper-framing requirement: competitive baseline comparison at
  matched operating points.

Reproduction mode:

- baseline evaluation of an external method.

Track: A (baseline comparison).

Gating: FastVID is torch-only per phase 1.23 research; requires
running on a separate torch install (not MLX). Run this as an
out-of-band comparison, NOT as part of our MLX pipeline.

Hypotheses:

- **H1 (FastVID performs well on TOMATO/MVBench)**: cached_accuracy
  via FastVID at our matched operating points (e.g., 90% token
  reduction) is within 2 items of our dense-8 baseline on both
  slices.
- **H2 (our method beats FastVID at motion-heavy subsets)**:
  FastVID's density-based pruning is less targeted for brief
  semantically-critical motion events than our sticky-dynamic-aware
  planner. At the TOMATO direction group specifically, our method
  outperforms FastVID.
- **H3 (composition potential)**: FastVID-chosen tokens have low
  overlap with our cached reused blocks, suggesting a composition
  experiment would be additive.

Acceptance band:

- FastVID runs on at least 10/15 items per slice without harness
  crashes
- comparable numbers can be cited in the paper's baseline table

Rejection band:

- FastVID cannot be ported / runs in a torch stack we can't
  trivially run side-by-side with our MLX results

Inconclusive:

- FastVID published numbers on TOMATO/MVBench are unavailable (per
  phase 1.23 research); we'd need to run it ourselves, which adds
  harness complexity

## Execution plan

Out of MLX scope. Option A: stand up a separate pytorch conda env
with Qwen 2.5-VL from HF + FastVID patches. Option B: cite published
FastVID results (VideoMME, EgoSchema) and note TOMATO/MVBench
numbers are unavailable — flag as a limitation.

## Result

Pending.

## Interpretation

Pending.

## Links

- FastVID paper: https://arxiv.org/abs/2503.11187
- FastVID repo: https://github.com/LunarShen/FastVID
- [phase 1.23 within-frame survey](2026-04-15-phase-1_23-fastv-composition-scouting.md)
- [docs/literature-map-2026-04-16.md](../../../docs/literature-map-2026-04-16.md)
