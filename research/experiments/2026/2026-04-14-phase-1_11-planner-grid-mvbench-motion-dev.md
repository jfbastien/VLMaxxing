# Phase 1.11: MVBench Motion Dev Planner Grid Sweep

## Preregistration

Objective:

- mirror phase 1.10 on MVBench motion dev: search the
  (statistic × thresholds × reuse_classes × max_age) space using the same
  calibration + sweep pipeline so cached policies on MVBench motion can be
  Pareto-checked against the phase 1.9 MVBench motion dev dense
  frame-budget curve

Claim register targets:

- `WP-2.6`
- `WP-3.1`
- `WP-3.3`

Reproduction mode:

- generalized benchmark search; method development on MVBench motion content

Track:

- A (quality at matched fresh-token-equivalent budget)

Hypotheses:

- H1 (transfer): Pareto-dominating policies on TOMATO motion dev (phase 1.10
  if any survive holdout) generalize to MVBench motion dev
- H2 (content-conditioned): MVBench motion dev's flatter dense-frame-budget
  curve (peak at 4 frames, plateaus rather than monotonically rising) means
  Pareto-dominance is HARDER to find on this slice — the dense baseline is
  already efficient at low frame counts
- H3 (calibration shape): MVBench motion dev calibration shows different bin
  occupancy than TOMATO (32/100/12 vs 4/80/60), so the same per-bin=1
  selection produces a different shape of grid coverage and may surface
  policies that TOMATO never examined

Acceptance band:

- calibration + sweep complete without runtime errors
- at least 15 distinct policies evaluated with valid metrics
- Pareto analysis produces at least one "candidate" policy

Rejection band:

- all searched policies dominated by some MVBench motion dense-N point;
  cached method does not beat dense frame subsampling on this slice at any
  operating point

Inconclusive:

- harness instability mid-sweep
- zero policies survive Pareto check on either dev or (later) holdout

Notes:

- DEV-only sweep, holdout gated to a separate commit
- no `--log-option-logprobs` initially (saves ~50% per-policy time); will
  be added in phase 1.13 stratification on selected winners only
- chunk_size=1 due to existing Metal-timeout operational constraint

## Execution

Run date: pending (awaits TOMATO motion dev sweep / phase 1.10 to free GPU)

Planned commands:

```
uv run python scripts/planner_grid_search.py sweep \
  --calibration research/experiments/2026/artifacts/phase1_10_mvbench_motion_dev_calibration.json \
  --frame-count 8 \
  --per-bin 1 \
  --max-policies 30 \
  --output-dir research/experiments/2026/artifacts/phase1_11_mvbench_motion_dev_grid \
  --out research/experiments/2026/artifacts/phase1_11_mvbench_motion_dev_grid_summary.json \
  --allow-dirty
```

Planned analysis:

```
uv run python scripts/pareto_analysis.py analyze \
  --cached research/experiments/2026/artifacts/phase1_11_mvbench_motion_dev_grid_summary.json \
  --dense research/experiments/2026/artifacts/phase1_9_mvbench_motion_frame_budget_dev.json \
  --total-frames 8 \
  --out research/experiments/2026/artifacts/phase1_11_mvbench_motion_dev_pareto.json
```

Calibration summary:

- `144` candidate policies calibrated
- bin counts: `0.50-0.70`: 32, `0.70-0.85`: 100, `0.85-0.95`: 12
- compared with TOMATO dev (4 / 80 / 60) the MVBench dev candidate space
  skews lower-reuse — most candidates land in the 0.50-0.85 range,
  reflecting that MVBench motion dev has more aggressive per-clip motion

## Result

In-flight as of 2026-04-15 (21/30 policies fully complete; one policy at 4/15
items). The three entries in
`phase1_11_mvbench_motion_dev_pareto_partial.json` are **two distinct
operating points**, not three — `max_abs(8,32) static+shifted age=8` and
`max_abs(8,32) static+shifted noage` collapse to the same bit-identical
behavior. Reason: with frame_count=8 there are only 7 reuse decisions, so
`max_age=8` is never a binding gate. This fact was flagged by codex audit on
2026-04-15. `select_holdout_winners.py` now de-duplicates across such
non-binding-age equivalents before emitting phase 1.12 launch rows.

Distinct Pareto-candidate operating points on dev (partial, 21 policies):

- `max_abs(8,32) static+shifted noage` — cached_acc=0.733,
  effective_fresh_frames=3.22, mean_active_reuse=0.682, agreement=0.867.
  Per-group diff vs same-run dense-8 + vs dense-4 shows this policy is
  item-identical to dense-4 on all 15 MVBench motion dev items
  (`phase1_11_mvbench_cached_vs_dense4.json`, 0 disagreements). It is
  therefore not an accuracy breakthrough; it is an **efficiency-at-identity**
  result: the 8-frame cached policy produces the same answers as the
  4-frame dense run on every item, at an effective proxy budget of 3.22
  fresh-token-equivalent frames.
- `changed_pixel_fraction(px8, 0.02/0.08) static+shifted noage` —
  cached_acc=0.667, effective_fresh_frames=3.94, mean_active_reuse=0.580,
  agreement=0.800. A valid lower-accuracy shoulder on the frontier, not a
  top-quality win. Per-group diff vs dense-3 gains 3 items; vs dense-4 loses
  1 action_localization item.

Caveat (calibration vs reported metric alignment): planner calibration in
`planner_grid_search.py` still estimates reuse from unmasked pairwise
classification before age gating, while the benchmark runner reports
pad-masked active reuse after age gating. The MVBench winner's dev reuse
(0.682) and calibration bin are not measurement-aligned. This is a
documentation-only caveat for now; it does not invalidate the dense-4
per-item identity.

## Interpretation

- **H1 (transfer from TOMATO)**: NOT supported. TOMATO motion dev's winning
  policy (`max_abs(8,32) static+shifted age=4`) also appears on the MVBench
  frontier as the `noage` variant, but the MVBench result is qualitatively
  different — per-item identity to dense-4 at lower budget rather than a
  near-equal-accuracy substitute. So the *policy label* transfers, the
  *operating behavior* does not.
- **H2 (MVBench is harder)**: partially supported. On the first 15
  dominated policies, every Pareto candidate was absent. The frontier only
  became non-empty after the sweep reached `max_abs(8,32) static+shifted`
  + `cpf static+shifted`. These are exactly the statistic families that
  codex audits and phase 1.46 control work suggested were strongest.
- **H3 (calibration shape)**: supported on the question of bin coverage
  but not on the question of Pareto outcome prediction.

Immediate implications for phase 1.12:

- Holdout launch slots are two (post-dedupe), not three. `max_abs(8,32)
  static+shifted noage` is the primary candidate; `cpf static+shifted
  noage` is the shoulder.
- Per `select_holdout_winners.py` output: MVBench holdout calibrated reuse
  projects winner to 3.26 fresh-frame-equivalent vs dense-3 holdout
  accuracy 0.600 — enough headroom to pass holdout if the 0.733 dev
  accuracy is stable.

## Links

- [phase 1.9 MVBench motion frame-budget](2026-04-14-phase-1_9-mvbench-motion-frame-budget-baselines.md)
- [phase 1.10 TOMATO motion dev grid](2026-04-14-phase-1_10-planner-grid-tomato-motion-dev.md)
- [execution plan round 7](../../../docs/execution-plan-round-7.md)
