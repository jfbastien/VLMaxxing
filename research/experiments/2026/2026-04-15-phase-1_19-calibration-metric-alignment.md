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

Pending. Low priority in queue; runs whenever no GPU-heavy phase is
active.

## Result

Pending.

## Interpretation

Pending.

## Links

- [phase 1.10 TOMATO motion dev](2026-04-14-phase-1_10-planner-grid-tomato-motion-dev.md)
- [phase 1.11 MVBench motion dev](2026-04-14-phase-1_11-planner-grid-mvbench-motion-dev.md)
- [decision-log 2026-04-14 calibration mismatch](../../../research/decision-log.md)
- [execution plan round 7](../../../docs/execution-plan-round-7.md)
