---
date: 2026-04-30
phase: 1.55K-extended (sampler-seed cross-product)
status: closed-earned (9/9 cells PASS)
related:
  - 2026-04-27-phase-1_55K-adaptive-temperature-sweep-prereg.md
  - 2026-04-27-phase-1_55F-adaptive-cpersist-findings.md
---

# Phase 1.55K extended — sampler seed × temperature C-PERSIST sweep

## Question

Phase 1.55K-base (`seed=42 × {0.5, 1.0, 1.5}`) showed adaptive C-PERSIST
on the seven-clip short tranche survives non-greedy sampling. Reviewers
can still ask: did one sampler seed get lucky? The extended sweep stresses
sampler robustness across `(seed × temperature) ∈ {42, 99, 2026} × {0.5,
1.0, 1.5}` on the same tranche.

## Method

- driver: `scripts/run_phase1_55K_extended_seed_sweep.sh` (chain-runner step
  A7), wrapping `scripts/run_kv_selective_reprefill_v2.py` per cell.
- model: `qwen2.5-vl-7b-instruct-4bit` (MLX), 20 frames, max-tokens 32,
  `top_p=0.95`, `min_p=0.0`.
- adaptive arm: `reprefill_k=1`, `reprefill_k_q2=1`, `reprefill_k_q3=0`,
  `q3_cache_source=post_q2_repaired`.
- 7 short clips × (1 cold + 21 paired) per cell × 9 cells.
- gates per cell (`scripts/summarize_phase1_55k_extended_seed_sweep.py`,
  prereg from 2026-04-27): H1 fidelity, H2 format, H3 baseline quality.

## Results

All 9 cells pass. `extended_seed_sweep_summary.json:by_temperature`:

| Temperature | Cells | max \|Δacc\| | max paired choice diffs | max paired correctness diffs | min baseline accuracy |
|---|---|---|---|---|---|
| 0.5 | 3/3 PASS | 0.048 | 1/21 | 1/21 | 0.762 |
| 1.0 | 3/3 PASS | 0.000 | 1/21 | 1/21 | 0.714 |
| 1.5 | 3/3 PASS | 0.000 | 1/21 | 0/21 | 0.667 |

Per-cell `accuracy_delta_session_minus_baseline` summary (`extended_seed_sweep_summary.json:cells`):

| seed | T | session_acc | baseline_acc | Δacc | choice diffs | correctness diffs | speedup all-query cold/follow-up |
|---|---|---|---|---|---|---|---|
| 42 | 0.5 | 0.810 | 0.810 | 0.000 | 0 | 0 | 25.19× |
| 42 | 1.0 | 0.810 | 0.857 | -0.048 | 1 | 1 | 24.82× |
| 42 | 1.5 | 0.762 | 0.762 | 0.000 | 1 | 0 | 25.05× |
| 99 | 0.5 | 0.810 | 0.762 | +0.048 | 1 | 1 | (clean) |
| 99 | 1.0 | 0.762 | 0.762 | 0.000 | (clean) | (clean) | (clean) |
| 99 | 1.5 | 0.714 | 0.714 | 0.000 | (clean) | (clean) | (clean) |
| 2026 | 0.5 | 0.762 | 0.762 | 0.000 | (clean) | (clean) | (clean) |
| 2026 | 1.0 | 0.714 | 0.714 | 0.000 | (clean) | (clean) | (clean) |
| 2026 | 1.5 | 0.667 | 0.667 | 0.000 | (clean) | (clean) | (clean) |

Pathological-format hits across all 9 cells: `0/126` follow-up rows,
`0/63` Q3 rows. `mean_follow_up_prefix_coverage = 0.968` per cell.

## Interpretation

H1, H2, H3 hold across the cross-product:
- max \|Δacc\| over 9 cells = 0.048, well below the 2/21 ≈ 0.095 prereg
  fidelity bound.
- 0/189 pathological format hits, well below the 2/14 cell-level format
  bound.
- baseline accuracy floor 0.667 (rounded to 14/21), so no cell passed by
  collapsing to low-quality both-arm output.

Adaptive C-PERSIST on the seven-clip short tranche is therefore
**sampler-robust across three seeds and three temperatures**, not a
greedy-path artifact and not a single-seed coincidence. The cold-over-
follow-up speedup remains in the 24.8–25.2× band where measured.

## Falsified hypotheses

- "Adaptive C-PERSIST is greedy-only" — 9/9 cells PASS at non-greedy
  sampling.
- "1.55K base was a single-seed lucky draw" — two additional seeds
  reproduce the same fidelity behavior.

## Cross-references

- Phase 1.55F: greedy reference for the same seven-clip tranche.
- Phase 1.55L (A6): many-turn horizon stress on the same tranche.
- `paper/claim-matrix.md` row 14 (C-PERSIST after-ingest envelope).
- Artifacts: `research/experiments/2026/artifacts/phase1_55K_extended_seed_sweep/`.

## Caveats

- Same seven-clip short tranche; this is sampler robustness, not benchmark
  generalization. Long-bucket sampler robustness is not exercised here.
- 21 paired rows per cell. Confidence intervals on Δacc are wide; the
  prereg gate is a hard threshold, not an interval test.
