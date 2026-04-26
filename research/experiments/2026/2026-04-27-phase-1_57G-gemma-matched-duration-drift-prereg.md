---
date: 2026-04-27
phase: 1.57G
status: preregistered; not yet run
related:
  - research/experiments/2026/2026-04-20-phase-1_57-holdout-recheck-findings.md
  - research/experiments/2026/2026-04-21-phase-1_42-gemma-temporal-reuse-findings.md
---

# Phase 1.57G — Gemma Matched-Duration Feature-Drift Grid

## Question

Do Gemma's feature-drift geometry and Qwen's feature-drift geometry tell the
same story across short, medium, and long VideoMME buckets?

The current cross-architecture C-VISION story has answer-level Gemma evidence,
but the matched drift-geometry evidence is thinner. This phase measures Gemma's
STATIC / SHIFTED / NOVEL adjacent-frame cosine distributions over the same
duration buckets used in the Qwen drift discussion.

## Protocol

- Model: `gemma-4-e4b-it-4bit`.
- Manifest: `research/benchmark_manifests/videomme_dev_v1.toml`.
- Groups: `short`, `medium`, `long`.
- Frame counts: 8, 16, 32.
- Runner: `scripts/measure_feature_drift.py --model gemma`.
- Summary: `scripts/summarize_feature_drift_grid.py` writes a 3×3 grid summary
  with STATIC / SHIFTED / NOVEL means and medians.
- Reference: Qwen phase 1.57 dev-grid artifacts under
  `research/experiments/2026/artifacts/phase1_57/`.

## Gates

- **H_complete**: all 9 cells finish and the summary marks `complete=true`.
- **H_static_monotone_or_boundary**: STATIC mean cosine is either stable /
  increasing with frame count within each duration bucket, or any non-monotone
  bucket is explicitly reported as a Gemma-specific boundary. This is a
  mechanism readout, not a pass/fail claim.
- **H_cross_arch_matched_geometry**: compare Gemma and Qwen STATIC mean cosine
  in each matched `(duration, frame_count)` cell. If all absolute differences
  are ≤ 0.05, report "matched drift geometry." Otherwise report
  "architecture-conditioned drift geometry" and list the cells exceeding the
  threshold.
- **H_cross_arch_explanation**: if Gemma STATIC means remain high while answer
  identity can still drift (from 1.42), the paper should state that feature
  cosine alone is insufficient to predict answer stability across
  architectures. If Gemma STATIC means fall in the same cells where answer
  drift appears, the paper can use drift geometry as the likely explanation.

## Interpretation

The point is to make the cross-architecture story less hand-wavy:

- If Gemma and Qwen drift geometry match, C-VISION can claim a stronger
  two-architecture mechanism proxy.
- If Gemma has high STATIC cosine but answer drift remains, the paper should
  emphasize architecture-conditioned readout / attention topology rather than
  raw visual-feature drift.

## Runtime

Expected wall time: ~2-6 h for all 9 cells on the local 16 GB laptop. The
queue timeout is intentionally sized for the pessimistic end because the prior
Gemma 1.57 evidence only timed the long-bucket cells. Peak RSS should stay near
the existing Gemma 1.57 / 1.42 runs.
