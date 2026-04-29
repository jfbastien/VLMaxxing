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

Sweep completed 2026-04-15 (30/30 policies). The `pareto_analysis.py`
analyzer reports 8 raw candidates by its own (dense-only) rule: a cached
point is a "candidate" iff no dense-N baseline strictly dominates it on
`(cached_accuracy, effective_fresh_frames)`. It does NOT compute
inter-cached Pareto. After dedupe of non-binding `age8 ≡ noage`
equivalents, 4 candidate labels remain.

Codex audit 2026-04-15 flagged that an earlier draft of this note said
the 4 candidates were "distinct Pareto operating points under strict
inter-cached Pareto" — that was an overclaim. In commit (this tranche),
`pareto_analysis.py` was extended to compute a real inter-cached
skyline. Re-running the analyzer produces:

- **2-axis skyline (cached_accuracy, effective_fresh_frames)**: 1 point —
  `max_abs(16,64) static+shifted noage` at 0.733 / 2.52. This point
  strictly dominates every other candidate on the repo's headline axes.
- **3-axis skyline (cached_accuracy, effective_fresh_frames,
  agreement)**: 3 raw points that collapse to 2 distinct ones
  post-dedupe:
  - `max_abs(16,64) static+shifted noage` at 0.733 / 2.52 / agreement=0.667
  - `max_abs(8,32) static+shifted noage` at 0.733 / 3.22 / agreement=0.867

The 3-axis skyline matters because dense-agreement encodes
content-level fidelity that the 2-axis headline metrics miss: (16,64)
and (8,32) have the same accuracy on this slice but (8,32) produces
item-identical outputs to dense-4 while (16,64) generates different
answers that happen to score the same on 15 items. The right story is
"at the top accuracy tier there are two distinct operating regimes —
aggressive (2.52 fresh frames, 67% dense-agreement) and conservative
(3.22 fresh frames, 87% dense-agreement, item-identical to dense-4)."
The remaining phase 1.11 candidates (`top_k_mean`, `cpf`) are in neither
skyline; they sit below the frontier on all three axes.

1. **`max_abs(16, 64) static+shifted noage`** — cached_acc=0.733,
   effective_fresh_frames=**2.52**, mean_active_reuse=0.783,
   agreement=**0.667**. Strict Pareto winner by budget at the top
   accuracy tier, but the drop in dense-agreement (from 0.867 at the
   (8,32) winner to 0.667) indicates cached is making *different*
   answer choices than dense-N and happens to match the same 11/15
   count. On 15 items this is indistinguishable from lucky noise; the
   holdout evaluation is the discriminator.
2. **`max_abs(16, 64) static+shifted age=4`** — cached_acc=0.733,
   fresh=3.21, reuse=0.685, agreement=0.667. Same thresholds as (1)
   with age-4 gating; budget roughly equal to the (8,32) winner's 3.22.
   Useful because age-bound variants generalize differently on holdout.
3. **`max_abs(8, 32) static+shifted noage`** — cached_acc=0.733,
   fresh=3.22, reuse=0.682, agreement=**0.867**. Per-group diff vs
   same-run dense-4 shows this policy is item-identical to dense-4 on
   all 15 items (`phase1_11_mvbench_cached_vs_dense4.json`, zero
   disagreements). Weaker strict-Pareto claim than (1) but stronger
   quality claim.
4. **`top_k_mean(k=64, 4, 12) static+shifted noage`** — cached_acc=0.667,
   fresh=3.77, reuse=0.604, agreement=0.867. A genuinely distinct
   statistic-family frontier point at the second accuracy tier,
   strictly dominating the CPF shoulder.

Additional candidates (all dominated by the four above under strict
inter-cached Pareto):

- `cpf(px8, 0.02/0.08) static+shifted noage` at 0.667/3.94 — original
  shoulder, now dominated by top_k_mean.

Caveat (calibration vs reported metric alignment): planner calibration in
`planner_grid_search.py` still estimates reuse from unmasked pairwise
classification before age gating, while the benchmark runner reports
pad-masked active reuse after age gating. Phase 1.19 (preregistered) will
fix this; the per-item-identity result for policy (3) is independent of
calibration accuracy and stands regardless.

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

- 5 holdout launch slots now filled (post-dedupe):
  1. `max_abs(16,64) noage` @ 2.52 dev fresh / 2.63 holdout-projected
     → matched dense-2 on holdout (accuracy 0.533)
  2. `max_abs(16,64) age=4` @ 3.21 dev / 2.63 holdout → matched dense-2
  3. `max_abs(8,32) noage` @ 3.22 dev / 3.26 holdout → matched dense-3 (0.600)
  4. `top_k_mean(k=64, 4, 12) noage` @ 3.77 dev / 3.55 holdout → dense-3
  5. `cpf(px8, 0.02, 0.08) noage` @ 3.94 dev / 3.65 holdout → dense-3
- Primary holdout claim to watch: can any cached point beat matched
  dense-N on holdout at at least one of the four distinct operating
  budgets?
- The item-identity-to-dense-4 property of (3) gives that point the
  highest prior for surviving holdout; (1) has the most aggressive
  budget but the agreement=0.667 risk profile.

## Links

- [phase 1.9 MVBench motion frame-budget](2026-04-14-phase-1_9-mvbench-motion-frame-budget-baselines.md)
- [phase 1.10 TOMATO motion dev grid](2026-04-14-phase-1_10-planner-grid-tomato-motion-dev.md)
- [experiment registry](../registry.md)
