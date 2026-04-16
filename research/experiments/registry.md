# Experiment Registry (Machine-Readable)

Last updated: 2026-04-16

This is the single source of truth for per-phase state. Other docs
(PLAN.md, research-strategy-post-codecsight.md, literature-map, paper/
framing.md) narrate and contextualize, but if any of them contradicts
this registry, fix them — not this file.

## Fields

Each entry is a YAML-style block with these fields:

- `phase_id`: e.g. `1.26`, `1.12.B`
- `status`: `proposed` / `running` / `completed` / `superseded` /
  `deferred`
- `authoritative_note`: path to the phase note
- `authoritative_artifacts`: paths to primary result artifacts
- `current_best_policy`: the winning policy (if any) — verbatim label
- `supersedes`: phase IDs whose claims are narrowed or replaced
- `paper_relevance`: `primary`, `diagnostic`, `methodology`, `historical`
- `prereg_outcome`: per research/README.md — `Accepted`,
  `Accepted with caveat`, `Rejected`, `Inconclusive`, or empty if
  still running

Entries are ordered by phase_id (chronological within each 1.x range).

## Registry

### Foundation (phases 1.0–1.9)

Registry entries for the foundation phases (cache-path identity,
mechanism reproduction, TOMATO/MVBench subset smokes, benchmark
path controls, matched dense frame-budget baselines) are kept
authoritative in the per-phase notes under
`research/experiments/2026/`. This registry is summary; see
`docs/reproduction-status.md` for the whitepaper claim status table.

### Active experimental phases (1.10–1.35)

```yaml
- phase_id: 1.10
  status: completed
  authoritative_note: research/experiments/2026/2026-04-14-phase-1_10-planner-grid-tomato-motion-dev.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_10_tomato_motion_dev_grid/
    - research/experiments/2026/artifacts/phase1_10_tomato_motion_dev_grid_summary.json
    - research/experiments/2026/artifacts/phase1_10_tomato_motion_dev_pareto.json
  current_best_policy: "max_abs(8,32) static+shifted age=4 — cached=0.400 @ fresh=3.99 on TOMATO motion dev"
  supersedes: []
  paper_relevance: primary (dev evidence)
  prereg_outcome: Accepted with caveat

- phase_id: 1.11
  status: completed
  authoritative_note: research/experiments/2026/2026-04-14-phase-1_11-planner-grid-mvbench-motion-dev.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_11_mvbench_motion_dev_grid/
    - research/experiments/2026/artifacts/phase1_11_mvbench_motion_dev_grid_summary.json
    - research/experiments/2026/artifacts/phase1_11_mvbench_motion_dev_pareto.json
  current_best_policy: "max_abs(16,64) static+shifted noage — cached=0.733 @ fresh=2.52 (2D skyline winner); but rejected on phase 1.12 holdout. See 1.12.B for the real winner."
  supersedes: []
  paper_relevance: methodology
  prereg_outcome: Accepted (dev-only); winners later rejected on holdout

- phase_id: 1.12
  status: completed
  authoritative_note: research/experiments/2026/2026-04-14-phase-1_12-grid-winners-holdout.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_12_mvbench_motion_holdout_pareto.json
    - research/experiments/2026/artifacts/phase1_12_tomato_motion_holdout_pareto.json
  current_best_policy: "MVBench holdout: 0/5 survivors (narrow null). TOMATO holdout: 5/5 tie dense-6 at cached=0.267 @ fresh=3.39–4.24."
  supersedes: []
  paper_relevance: primary (holdout gate for phase 1.11)
  prereg_outcome: Rejected on MVBench; Accepted with caveat on TOMATO

- phase_id: 1.12.B
  status: completed
  authoritative_note: research/experiments/2026/2026-04-16-phase-1_12b-crossbench-winner-mvbench-holdout.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_12b_crossbench_winner_mvbench_holdout_summary.json
    - research/experiments/2026/artifacts/phase1_12b_crossbench_winner_mvbench_holdout_pareto.json
    - research/experiments/2026/artifacts/phase1_12b_cached_vs_dense6_holdout.json
  current_best_policy: "max_abs(8,32) static+shifted age=4 — cached=0.667 @ fresh=4.59 @ agreement=0.933 on MVBench motion holdout (N=15, transfer-discovered follow-up)"
  supersedes: [1.12 (narrowed), 1.11 (winner gap filled)]
  paper_relevance: primary (SOTA-direction signal)
  prereg_outcome: Accepted with caveat

- phase_id: 1.16
  status: completed
  authoritative_note: research/experiments/2026/2026-04-15-phase-1_16-cross-benchmark-winner-transfer.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_16_mvbench_winner_on_tomato_summary.json
    - research/experiments/2026/artifacts/phase1_16_tomato_winner_on_mvbench_summary.json
  current_best_policy: "Cell A loses 1 item on TOMATO dev (cached=0.333). Cell B finds MVBench dev winner: cached=0.800 @ fresh=3.78 with max_abs(8,32) age=4 (discovery fed 1.12.B)."
  supersedes: []
  paper_relevance: diagnostic (asymmetric transfer finding)
  prereg_outcome: Accepted with caveat

- phase_id: 1.19
  status: completed
  authoritative_note: research/experiments/2026/2026-04-15-phase-1_19-calibration-metric-alignment.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_19_mvbench_motion_dev_calibration_v2.json
    - research/experiments/2026/artifacts/phase1_19_mvbench_motion_holdout_calibration_v2.json
    - research/experiments/2026/artifacts/phase1_19_tomato_motion_dev_calibration_v2.json
    - research/experiments/2026/artifacts/phase1_19_tomato_motion_holdout_calibration_v2.json
  current_best_policy: n/a (methodology phase)
  supersedes: [1.10 v1 calibrations (still valid historically); any phase citing pre-fix calibration bins]
  paper_relevance: methodology
  prereg_outcome: Accepted

- phase_id: 1.20
  status: proposed
  authoritative_note: research/experiments/2026/2026-04-15-phase-1_20-tomato-motion-slice-enlargement.md
  authoritative_artifacts: []
  current_best_policy: n/a
  supersedes: []
  paper_relevance: primary (TOMATO hardening)
  prereg_outcome: (pending run)

- phase_id: 1.21
  status: proposed
  authoritative_note: research/experiments/2026/2026-04-15-phase-1_21-mvbench-motion-slice-enlargement.md
  authoritative_artifacts: []
  current_best_policy: "primary cell = max_abs(8,32) static+shifted age=4 sticky_window=4 (phase 1.26.B survivor); diagnostic comparators listed in prereg"
  supersedes: []
  paper_relevance: primary (MVBench hardening — top priority after phase 1.26.C)
  prereg_outcome: (pending run)

- phase_id: 1.23
  status: completed
  authoritative_note: research/experiments/2026/2026-04-15-phase-1_23-fastv-composition-scouting.md
  authoritative_artifacts:
    - docs/fastv-composition-plan.md
  current_best_policy: n/a (scouting)
  supersedes: []
  paper_relevance: historical (infrastructure scouting)
  prereg_outcome: Accepted with caveat

- phase_id: 1.24
  status: completed
  authoritative_note: research/experiments/2026/2026-04-16-phase-1_24-tomato-holdout-dense-backfill.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_24_tomato_motion_holdout_dense/
    - research/experiments/2026/artifacts/phase1_24_tomato_motion_holdout_dense_summary.json
    - research/experiments/2026/artifacts/phase1_24_tomato_motion_holdout_dense_full.json
  current_best_policy: n/a (baseline)
  supersedes: []
  paper_relevance: methodology (dense curve for 1.12 TOMATO)
  prereg_outcome: Accepted with caveat

- phase_id: 1.25
  status: proposed
  authoritative_note: research/experiments/2026/2026-04-16-phase-1_25-tempcompass-ingest.md
  authoritative_artifacts: []
  current_best_policy: n/a
  supersedes: []
  paper_relevance: primary (third benchmark, deferred)
  prereg_outcome: (pending)

- phase_id: 1.26
  status: completed (TOMATO dev cells 1+2)
  authoritative_note: research/experiments/2026/2026-04-16-phase-1_26-sticky-dynamic-planner.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_26_sticky_dynamic_tomato_dev/
  current_best_policy: "sticky_window ∈ {4, 8} HURT on TOMATO dev; see 1.26.B for MVBench result."
  supersedes: []
  paper_relevance: diagnostic
  prereg_outcome: Rejected (for TOMATO-dev H1)

- phase_id: 1.26.B
  status: completed
  authoritative_note: research/experiments/2026/2026-04-16-phase-1_26-sticky-dynamic-planner.md (see "Phase 1.26.B" section)
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_26b_sticky_on_mvbench_holdout/
    - research/experiments/2026/artifacts/phase1_26b_sticky_on_mvbench_holdout_summary.json
    - research/experiments/2026/artifacts/phase1_26b_sticky_on_mvbench_holdout_pareto.json
    - research/experiments/2026/artifacts/phase1_26b_sticky4_vs_dense8_holdout.json
  current_best_policy: "max_abs(8,32) static+shifted age=4 sticky_window=4 — cached=0.733 @ fresh=5.10 @ agreement=1.000 on MVBench motion holdout (N=15, single-shot, transfer-discovered)"
  supersedes: [1.12.B (strengthened with +1 item, item-identity to dense-8)]
  paper_relevance: primary (strongest current MVBench Pareto signal)
  prereg_outcome: Accepted with caveat (overturns original H2 framing)

- phase_id: 1.26.C
  status: running
  authoritative_note: research/experiments/2026/2026-04-16-phase-1_26-sticky-dynamic-planner.md (to be extended)
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_26c_sticky_on_mvbench_dev/
  current_best_policy: "testing sticky_window ∈ {4, 8} on MVBench motion DEV to validate mechanism reproducibility beyond holdout"
  supersedes: []
  paper_relevance: diagnostic
  prereg_outcome: (pending completion)

- phase_id: 1.27
  status: proposed (needs rescoping)
  authoritative_note: research/experiments/2026/2026-04-16-phase-1_27-projector-group-completion.md
  authoritative_artifacts: []
  current_best_policy: n/a
  supersedes: []
  paper_relevance: diagnostic (scoping note: on our Qwen 2.5-VL stack, `BLOCK_SIZE=28` is already at projector-input granularity, so the mechanism as preregistered may be a no-op; needs reinterpretation as 2×2 block coarsening)
  prereg_outcome: (pending; needs pre-run reinterpretation)

- phase_id: 1.28
  status: completed (off-budget probe, NOT iso-budget)
  authoritative_note: research/experiments/2026/2026-04-16-phase-1_28-iso-token-budget-coverage.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_28_tomato_dev_cached_16frames/
    - research/experiments/2026/artifacts/phase1_28_mvbench_holdout_cached_16frames/
  current_best_policy: "TOMATO 16f: 0.467 @ fresh=6.90 (off-budget). MVBench hold 16f: 0.667 @ fresh=8.58 (off-budget, Pareto-dominated by dense-8). The iso-budget test (fresh ≈ 4 via tighter thresholds at 16 frames) was NOT run."
  supersedes: []
  paper_relevance: diagnostic (rejected "more frames helps" at this policy, but iso-budget question still open)
  prereg_outcome: Inconclusive (protocol deviation)

- phase_id: 1.29
  status: proposed
  authoritative_note: research/experiments/2026/2026-04-16-phase-1_29-mv-only-signal-path.md
  authoritative_artifacts: []
  current_best_policy: n/a
  supersedes: []
  paper_relevance: primary (deployability)
  prereg_outcome: (pending)

- phase_id: 1.30
  status: deferred
  authoritative_note: research/experiments/2026/2026-04-16-phase-1_30-streaming-window-harness.md
  authoritative_artifacts: []
  current_best_policy: n/a
  supersedes: []
  paper_relevance: historical / infra (deferred behind Track B)
  prereg_outcome: (not yet)

- phase_id: 1.31
  status: proposed
  authoritative_note: research/experiments/2026/2026-04-16-phase-1_31-failure-predictor.md
  authoritative_artifacts: []
  current_best_policy: n/a (CPU analysis, not a policy run)
  supersedes: []
  paper_relevance: methodology
  prereg_outcome: (pending)

- phase_id: 1.32
  status: deferred (mlx-vlm fork prerequisite)
  authoritative_note: research/experiments/2026/2026-04-16-phase-1_32-fastv-composition-pilot.md
  authoritative_artifacts: []
  current_best_policy: n/a
  supersedes: []
  paper_relevance: historical / stretch
  prereg_outcome: (not yet)

- phase_id: 1.33
  status: deferred (out of MLX scope)
  authoritative_note: research/experiments/2026/2026-04-16-phase-1_33-fastvid-baseline.md
  authoritative_artifacts: []
  current_best_policy: n/a
  supersedes: []
  paper_relevance: diagnostic (baseline for paper table)
  prereg_outcome: (not yet)

- phase_id: 1.34
  status: proposed
  authoritative_note: research/experiments/2026/2026-04-16-phase-1_34-novelty-ranked-dense-baseline.md
  authoritative_artifacts: []
  current_best_policy: n/a (stronger baseline, not a new policy)
  supersedes: []
  paper_relevance: primary (stronger matched-budget comparator)
  prereg_outcome: (pending)

- phase_id: 1.35
  status: proposed
  authoritative_note: research/experiments/2026/2026-04-16-phase-1_35-event-window-oracle.md
  authoritative_artifacts: []
  current_best_policy: n/a (oracle ceiling, not a policy)
  supersedes: []
  paper_relevance: primary (method headroom)
  prereg_outcome: (pending)
```

## Maintenance rules

- When a phase status changes (runs → completed, completed →
  superseded), update the registry row in the same commit as the
  corresponding phase note + decision-log entry.
- When `current_best_policy` changes, update `supersedes` and
  `paper/framing.md` + `literature-map-2026-04-16.md` citations.
- When a new phase is preregistered, add its registry row alongside
  the prereg note.
- When an old roadmap document (PLAN.md, execution-plan-round-7.md)
  is updated, re-verify that its claims agree with this registry.
  If they disagree, fix the prose and cite back to this registry.
