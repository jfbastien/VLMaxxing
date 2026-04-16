# Phase 1.19: Align Calibration Metric with Runner's Pad-Masked Active Reuse

## Preregistration

Objective:

- fix the known calibration mismatch documented in the decision-log row of
  2026-04-14: `planner_grid_search.py::_calibrate` estimates reuse from
  unmasked pairwise classification before age gating, while
  `run_benchmark_track_a.py` reports pad-masked active reuse after age
  gating. Phase 1.10 mean absolute calibration error was 0.245 vs
  active, 0.087 vs raw.
- once aligned, calibration-bin narratives in phase 1.10/1.11 become
  measurement-compatible evidence rather than caveated documentation.

Claim register targets:

- methodology fix; supports any future paper claim that reports
  "calibration-bin occupancy" as evidence for grid coverage.

Reproduction mode:

- no benchmark runs; purely a calibration code change + re-calibration
  on MVBench motion dev for sanity check.

Track:

- A (methodology).

Gating:

- **PROMOTED** 2026-04-16 by codex audit. The MVBench holdout + TOMATO
  holdout winner selection used the calibration-projected
  effective_fresh_frames to match each cached policy to a holdout
  dense-N reference point. Observed projection error on TOMATO holdout
  `max_abs(8,32) age=4`: projected 1.94 fresh frames, ACTUAL 3.39 — an
  error of ~1.45 frames, enough to flip which dense-N baseline is the
  matched reference.
- Phase 1.19 is now **top priority** among code-change phases because
  the mismatch is affecting experiment *interpretation*, not just
  caveat language.
- Runs ahead of 1.20/1.21/1.22 unless a GPU-bound survivor claim needs
  immediate backfill (phase 1.24).

Hypotheses:

- H1 (code-level fix): applying the same active-region mask and
  max-age gate inside calibration brings MAE vs runner active-reuse to
  below 0.02 on MVBench motion dev.
- H2 (bin reshuffle): some policies move bin after the fix (expected);
  the phase 1.11 winner does not because it has `max_age=None` on an
  8-frame clip (age gating is a no-op) and its pad mask impact is
  small for short MVBench clips.

Acceptance band:

- calibration code refactored to apply active-region masking and
  max-age gating in `_calibrate`; new calibration artifact for MVBench
  motion dev emitted; MAE vs phase-1.11 runner-reported active reuse
  drops below 0.02 on at least 20 of the 22 completed policies.

Rejection band:

- fix does not reduce MAE by a factor of 10+ → deeper investigation
  needed, not a quick alignment change.

Inconclusive:

- cannot replicate runner's mask semantics from the pair-classification
  API without additional runner-side refactor.

Planned code change:

1. Extract the pad-mask + age-gate logic from
   `run_benchmark_track_a.py::_compute_reuse_ratio` into a shared
   helper in `src/codec_through/temporal/` (or a new script-local
   helper if a shared home is contentious).
2. Call that helper in `planner_grid_search.py::_calibrate` on the
   per-pair classification output.
3. Re-calibrate MVBench motion dev (single command, CPU-only pass,
   ~5 min).
4. Diff new calibration's `mean_active_reuse` against the phase-1.11
   runner-reported value per policy; write a small verification note
   in the artifact.

Runtime: ~1 hr code change + ~15 min CPU re-calibration.

## Execution

Completed 2026-04-16. Code change: `_calibrate` in
`scripts/planner_grid_search.py` now mirrors the runner's pad-masked,
age-gated `_compute_reuse_ratio` semantics. Verified in commit
`a59e37c` via ruff + mypy.

Re-calibrated all 4 manifests (`phase1_19_*_calibration_v2.json`).

## Result

Preregistration outcome: **Accepted**.

MVBench motion dev, 30 policies that actually ran in phase 1.11:

| calibration version | MAE vs runner `reuse_ratio_mean_active` |
|---|---|
| v1 (pre-fix, unmasked + pre-age-gate) | 0.2023 |
| v2 (pad-masked + age-gated) | **0.0017** (max 0.0041, median 0.0018) |

120× improvement in MAE. Calibration is now essentially a drop-in
estimator for runner-reported active reuse.

H1 acceptance band (MAE < 0.02 on ≥20 of 22 completed policies):
**PASSED** for 30/30 policies.

## Interpretation

- H1 confirmed cleanly. The pre-fix mismatch (0.20 MAE) was large
  enough to flip holdout-target dense-N assignments; the v2 error
  (0.002 MAE) is below sampling noise.
- All future sweeps should reference v2 calibrations.
- Existing v1 calibrations left on disk for provenance; do not use
  them for new analysis.
- `select_holdout_winners.py` and `pareto_analysis.py` already
  reference the calibration file path by argument, so switching is
  a per-invocation choice.

## Links

- [phase 1.10 TOMATO motion dev](2026-04-14-phase-1_10-planner-grid-tomato-motion-dev.md)
- [phase 1.11 MVBench motion dev](2026-04-14-phase-1_11-planner-grid-mvbench-motion-dev.md)
- [decision-log 2026-04-14 calibration mismatch](../../../research/decision-log.md)
- [execution plan round 7](../../../docs/execution-plan-round-7.md)
