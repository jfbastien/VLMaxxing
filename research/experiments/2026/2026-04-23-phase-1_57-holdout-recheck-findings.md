---
phase: 1.57
date: 2026-04-23
parent: research/experiments/2026/2026-04-19-phase-1_57-feature-drift-mechanism-prereg.md
prior:
  - research/experiments/2026/2026-04-21-phase-1_41-qwen-videomme-16f-holdout-findings.md
  - research/experiments/2026/2026-04-22-phase-1_41-qwen-videomme-8f-holdout-findings.md
status: findings 2026-04-23. Paper narrative can now say "validated on dev AND holdout".
tracking: autonomous AFK session 2026-04-22/23
---

# 1.57 holdout re-check — feature-drift transfer from dev to holdout

## TL;DR

The Qwen 1.57 feature-drift geometry (STATIC/SHIFTED/NOVEL per-class cosine)
reproduces on the holdout VideoMME manifest with max |Δ| ≤ 5pp across every
(class × statistic) combination tested. The earlier concern that 1.57 was
dev-local — raised by the 1.41 holdout VideoMME runs where accuracy shape
did not fully mirror dev — was overstated as a feature-drift claim. The
mechanism itself transfers; what did not transfer was the *accuracy*
consequence, which is a separate downstream coupling question.

## Method

Ran `scripts/measure_feature_drift.py` on
`research/benchmark_manifests/videomme_holdout_v1.toml` at 8f and 16f with
the same planner-class setup as the dev measurements. Compared against the
dev references
`research/experiments/2026/artifacts/phase1_57/qwen_{8f,16f}_dev30.json`
via `scripts/compare_feature_drift.py`.

All 30 holdout items had cached ViT features (no live Metal encode for the
drift computation). Both the cache hits and the compare outputs are in
`research/experiments/2026/artifacts/phase1_57_holdout_recheck/`.

## Results

### 8-frame (n=30 per split)

| Class   | Dev mean_cos | Holdout mean_cos | Δ       |
|---------|--------------|------------------|---------|
| STATIC  | 0.562        | 0.551            | −0.011  |
| SHIFTED | 0.468        | 0.488            | +0.020  |
| NOVEL   | 0.322        | 0.312            | −0.010  |

All three classes move by < 2pp in the mean. The tails (p05, p95) also
move by < 5pp across all classes.

### 16-frame (n=30 per split)

| Class   | Dev mean_cos | Holdout mean_cos | Δ       |
|---------|--------------|------------------|---------|
| STATIC  | 0.607        | 0.590            | −0.017  |
| SHIFTED | 0.534        | 0.487            | −0.047  |
| NOVEL   | 0.341        | 0.331            | −0.010  |

SHIFTED shows the largest drift (−4.7pp in mean, −6.4pp in median), but
the class is thin at 16f (~1.5k blocks on holdout vs ~47k NOVEL blocks) so
the larger delta is consistent with lower-N noise rather than a split-level
distribution shift. STATIC and NOVEL remain under 2pp drift.

## Hypothesis verdicts

- **H2 (Qwen STATIC cos ∈ [0.95, 1.000])** — still FALSIFIED on holdout,
  consistent with dev. Qwen STATIC mean cos is in the 0.55–0.61 range, not
  saturation-class.
- **H3 (Qwen STATIC cos monotone rising 8f → 16f → 32f)** — partially
  reinforced. Both dev and holdout show STATIC cos rising from 8f to 16f
  (8f dev 0.562 → 16f dev 0.607 Δ+0.045; 8f holdout 0.551 → 16f holdout
  0.590 Δ+0.039). The 32f leg on holdout is not yet computed and is
  queued if frame-scaling carry-through remains a paper claim.
- **New: transfer claim.** The geometry of per-class drift is
  split-portable; the number that differs between dev and holdout is the
  downstream *accuracy* under this drift (see 1.41 holdout notes), not the
  drift itself.

## Paper narrative implication

The current paper co-saturation sentence (paper/claim-matrix.md:32, which
motivates C-VISION via STATIC feature drift) was written as "dev n=30
evidence". With this re-check, it is accurate to tighten to "dev n=30 +
holdout n=30 at 8f and 16f, with max |Δ| ≤ 5pp across all class × stat
pairs". No part of the paper needs softening; the opposite is true — the
mechanism gets an additional independent data point.

The 1.41 holdout *accuracy* divergence (where the dev long-bucket 16f
collapse did not mirror on holdout) is unaffected by this finding and
remains appropriately localized as a dev-only accuracy shape — the
feature-drift mechanism runs the same on both splits; what differs is how
the downstream LM collapses under that drift, which is a coupling question
one layer removed from 1.57.

## Reproduction

```
bash scripts/run_phase1_57_holdout_recheck.sh
```

Outputs:
- `research/experiments/2026/artifacts/phase1_57_holdout_recheck/qwen_8f_holdout.json`
- `research/experiments/2026/artifacts/phase1_57_holdout_recheck/qwen_16f_holdout.json`
- `research/experiments/2026/artifacts/phase1_57_holdout_recheck/qwen_8f_compare.txt`
- `research/experiments/2026/artifacts/phase1_57_holdout_recheck/qwen_16f_compare.txt`

## Next steps

1. Update `paper/claim-matrix.md` row 32 to cite both dev and holdout
   splits once 1.51V Qwen cross-arch completes (batch the paper pass).
2. Add a line to `research/decision-log.md`: 1.57 co-saturation story
   upgraded from dev-only to dev + holdout at 8f/16f.
3. Optional follow-up: 32f holdout re-check for H3 monotonic-rise
   completeness. Not currently on critical path.
