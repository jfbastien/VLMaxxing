---
phase: 1.29B
date: 2026-04-23
parent: research/experiments/2026/2026-04-23-phase-1_29-planner-accuracy-probe-findings.md
status: preregistered
tracking: codex AFK continuation 2026-04-23
---

# Phase 1.29B — codec-native planner replication and breadth prereg

## Motivation

Phase 1.29 reopened the codec-native planner path after the continuous-score
redesign matched dense answers on VideoMME short-dev n=10:

- codec-dense agreement: 1.00
- codec accuracy = dense accuracy = 0.80
- codec-minus-pixel accuracy: +0.10
- codec active-reuse ratio within 1pp of pixel

That is a first point, not paper-grade evidence. The earlier queue described
"n=30 short", but the repository's fixed VideoMME manifests contain only
10 short items in `videomme_dev_v1.toml` and 10 disjoint short items in
`videomme_holdout_v1.toml`. This prereg corrects that scope before any new run:

1. **Replication slice:** disjoint short holdout n=10.
2. **Short evidence bundle:** dev+holdout short n=20, analyzed from the two
   short runs.
3. **Duration-breadth slice:** all-duration dev n=30, run only if short
   replication is not clearly falsifying.

## Hypotheses

### H_short_replicates

On `videomme_holdout_v1_short_only.toml` at Qwen 2.5-VL-7B-Instruct-4bit,
8 frames, per-item live-pixel calibration:

- codec-dense choice agreement >= 0.90
- codec accuracy loss relative to dense >= -0.05
- codec-pixel choice agreement >= 0.80
- absolute active-reuse-ratio gap between codec and pixel <= 0.05
- parse failures = 0 for dense, pixel, and codec arms

This is a strict n=10 replication gate. If it fails by one item only on
accuracy but passes choice-agreement and parse gates, interpret as MIXED and
use the combined n=20 short bundle rather than promoting or killing the claim.

### H_short_bundle

Pooling the existing dev-short n=10 with the holdout-short n=10:

- codec-dense choice agreement >= 0.90
- codec accuracy loss relative to dense >= -0.05
- codec-pixel choice agreement >= 0.80
- absolute active-reuse-ratio gap between codec and pixel <= 0.05

This is the minimum evidence needed to keep C-CODEC in the paper-body
candidate list. It is still short-bucket-only and must be labeled as such.

### H_duration_breadth

On `videomme_dev_v1.toml` all durations n=30:

- codec-dense choice agreement >= 0.85
- codec accuracy loss relative to dense >= -0.10
- codec-pixel choice agreement >= 0.75
- absolute active-reuse-ratio gap between codec and pixel <= 0.10

The breadth gate is intentionally looser because long clips make native-rate
H.264 extraction expensive and because the n=10 result is short-only. Passing
this gate would upgrade C-CODEC from short-only first point to a broader local
codec-native benchmark slice. Failing it localizes C-CODEC to short/static-ish
clips and keeps it out of the main headline.

## Method

Use the existing runner without code changes:

```bash
PHASE1_29_MANIFEST=research/benchmark_manifests/videomme_holdout_v1_short_only.toml \
PHASE1_29_OUT_DIR=research/experiments/2026/artifacts/phase1_29B_short_holdout_20260423 \
bash scripts/run_phase1_29_planner_accuracy_probe.sh
```

If H_short_replicates is not clearly falsified, run duration breadth:

```bash
PHASE1_29_MANIFEST=research/benchmark_manifests/videomme_dev_v1.toml \
PHASE1_29_OUT_DIR=research/experiments/2026/artifacts/phase1_29B_dev30_duration_20260423 \
bash scripts/run_phase1_29_planner_accuracy_probe.sh
```

Do not overwrite the existing first-point artifacts under
`phase1_29_planner_accuracy_probe/`.

## Interpretation rules

- Treat codec-native as a **planner-substitution** claim, not a latency claim.
  This runner pays native-rate H.264 extraction cost that a streaming decoder
  would already have; measured wall-clock here is a diagnostic, not a systems
  speedup.
- Do not promote C-CODEC to a headline on short-only evidence.
- If short holdout fails, root-cause before running long-duration breadth:
  inspect per-item dense correctness, parse failures, reuse-ratio drift, and
  codec-vs-pixel selection Jaccard.
- If duration breadth fails while short passes, frame C-CODEC as a boundary:
  codec-native planner substitution works on short clips but does not yet
  survive long-span sparse-sampling without a better native-rate aggregation or
  calibration policy.

## Artifacts

Planned:

- `research/benchmark_manifests/videomme_holdout_v1_short_only.toml`
- `research/benchmark_manifests/videomme_short_dev_holdout_v1_n20.toml`
- `research/experiments/2026/artifacts/phase1_29B_short_holdout_20260423/results.jsonl`
- `research/experiments/2026/artifacts/phase1_29B_short_holdout_20260423/summary.json`
- `research/experiments/2026/artifacts/phase1_29B_dev30_duration_20260423/results.jsonl`
- `research/experiments/2026/artifacts/phase1_29B_dev30_duration_20260423/summary.json`
