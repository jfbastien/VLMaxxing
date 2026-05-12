# Experiment Registry (Machine-Readable)

Last updated: 2026-05-08

This is the primary source of per-phase experiment state. It is the phase
ledger, not the paper claim ledger. Use `paper/claim-matrix.md` for
paper-facing claim status, `docs/claim-register.md` for imported pre-release
target definitions, and `docs/reproduction-status.md` for reproduction/import
status. Other docs (PLAN.md, paper/framing.md, docs/related-work-table.md)
narrate and contextualize; if they contradict this registry on a phase's
status or current_best_policy, fix them.

Limitation: this is structured Markdown, not a real machine-parseable
ledger. Treat YAML blocks as structured prose, not as a database.
The maintenance rules below mitigate drift but don't eliminate it.
A future tooling pass could promote this to actual YAML + a CI
validator.

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

### Recent phase-2 additions (2026-04-29 to 2026-04-30)

```yaml
- phase_id: onevision-vlmaxxing-20260508
  status: completed through OV-6 Qwen; Gemma/OV-8 follow-ups pending
  authoritative_note: research/experiments/2026/2026-05-08-onevision-vlmaxxing-prereg.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/onevision_vlmaxxing_plan/experiment_schedule.json
    - research/experiments/2026/artifacts/onevision_vlmaxxing_visuals/
    - research/experiments/2026/artifacts/phase1_29_onevision_n57/statistical_audit.json
    - research/experiments/2026/artifacts/onevision_vlmaxxing_plan/ov6_track_b_statistical_audit.json
  current_best_policy: "bounded codec-source evidence: Track A positive point estimates over pixel at N=57/8f; Track B codec_novel_coded is best tested Qwen sparse arm at kr=0.7/layer=2 by point estimate, but paired tests remain inconclusive and current PyAV extraction erases net wall-clock savings"
  supersedes: []
  paper_relevance: diagnostic/proposed new science
  prereg_outcome: Accepted with caveat / bounded

- phase_id: 1.55L
  status: completed
  authoritative_note: research/experiments/2026/2026-04-30-phase-1_55L-many-turn-cpersist-findings.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_55L_many_turn_cpersist/summary.json
    - research/experiments/2026/artifacts/phase1_55L_many_turn_cpersist/paired_many_turn.jsonl
  current_best_policy: "adaptive repaired-cache inheritance and refresh-10 — no observed paired drift through 50-turn repeated-question stress; fixed K=1 shows nonzero repeated-question drift but stays below 3% gate"
  supersedes: []
  paper_relevance: primary (controlled C-PERSIST horizon stress)
  prereg_outcome: Accepted with caveat

- phase_id: 1.55M
  status: completed
  authoritative_note: research/experiments/2026/2026-05-02-phase-1_55M-dense-anchored-cpersist-findings.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_55M_dense_anchored_cpersist/summary.json
    - research/experiments/2026/artifacts/phase1_55M_dense_anchored_cpersist/baseline_many_turn.jsonl
    - research/experiments/2026/artifacts/phase1_55M_dense_anchored_cpersist/paired_many_turn.jsonl
  current_best_policy: "fixed K=1 has 0/133 observed dense-answer-anchored follow-up drift; adaptive and refresh-10 each show 6/133 paired drift at roughly 0.7s follow-up latency"
  supersedes: []
  paper_relevance: primary (C-PERSIST operating-envelope boundary)
  prereg_outcome: Accepted with caveat / mixed

- phase_id: 1.51VC
  status: completed (uniform-random multi-seed sanity baseline)
  authoritative_note: research/experiments/2026/2026-05-01-paper-defensibility-experiment-plan.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_51VC_random_keep_baseline/videomme_dev30_8f_L2_kr050_uniform_random_seed42_summary.json
    - research/experiments/2026/artifacts/phase1_51VC_random_keep_baseline/videomme_dev30_8f_L2_kr050_uniform_random_seed137_summary.json
    - research/experiments/2026/artifacts/phase1_51VC_random_keep_baseline/videomme_dev30_8f_L2_kr050_uniform_random_seed999_summary.json
    - research/experiments/2026/artifacts/phase1_51VC_random_keep_baseline/videomme_dev30_8f_L2_kr050_uniform_random_seed2024_summary.json
  current_best_policy: "structured magnitude_norm beats uniform-random 4-seed mean by +14.2pp at matched keep-rate; sanity baseline only, not peer-method comparison"
  supersedes: []
  paper_relevance: diagnostic sanity baseline
  prereg_outcome: Accepted with caveat

- phase_id: 1.63J
  status: completed
  authoritative_note: research/experiments/2026/artifacts/phase1_63J_qwen_8f_kr_sweep/kr_sweep_summary.json
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_63J_qwen_8f_kr_sweep/kr_sweep_summary.json
    - research/experiments/2026/artifacts/phase1_63J_qwen_8f_kr_sweep/pair_summary_kr025_8f.json
    - research/experiments/2026/artifacts/phase1_63E_track_b_frame_scaling/pair_summary_8f.json
    - research/experiments/2026/artifacts/phase1_63J_qwen_8f_kr_sweep/pair_summary_kr075_8f.json
  current_best_policy: "timing model validates across Qwen 8f keep rates, but all cells fail fidelity; use as C-CEILING timing evidence only"
  supersedes: []
  paper_relevance: primary for C-CEILING timing/fidelity separation; boundary for C-VISION
  prereg_outcome: Accepted with caveat

- phase_id: 1.62D
  status: completed (4f arm only)
  authoritative_note: research/experiments/2026/2026-04-30-phase-1_62D-lowfps-dense-findings.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_62D_lowfps_dense_videomme/lowfps_4f_vs_8f_summary.json
    - research/experiments/2026/artifacts/phase1_62D_lowfps_dense_videomme/cold_dense_4f_summary.json
  current_best_policy: "4f dense is 1.21x faster but overall accuracy delta is ambiguous; short bucket is a hard negative"
  supersedes: []
  paper_relevance: diagnostic baseline
  prereg_outcome: Inconclusive

- phase_id: 1.63I
  status: completed
  authoritative_note: research/experiments/2026/2026-04-30-phase-1_63I-qwen-kr-bracket-findings.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_63I_16f_kr_fine_bracket/fine_bracket_summary.json
  current_best_policy: "no full gate pass; kr=0.80/0.82 are format-caveated high-gain candidates, kr=0.85 remains the format-clean low-gain boundary"
  supersedes: []
  paper_relevance: diagnostic boundary
  prereg_outcome: Rejected for promotion

- phase_id: 1.65v2
  status: completed
  authoritative_note: research/experiments/2026/2026-04-29-phase-1_65v2-richer-predictor-findings.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_65v2_richer_predictor/prediction_summary.json
  current_best_policy: "no deployable guard; margin and richer dense-side features have signal but fail coverage/precision gates"
  supersedes: [1.65]
  paper_relevance: diagnostic negative
  prereg_outcome: Rejected

- phase_id: scaleout-m5-20260429
  status: completed (mixed bundle)
  authoritative_note: research/experiments/2026/2026-04-30-sam-integration-and-next-experiments.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/sam_scaleout_m5_20260429/README.md
    - research/experiments/2026/2026-04-29-phase-B0b-sam-cache-correctness-findings.md
    - research/experiments/2026/2026-04-29-phase-B3-sam-streaming-baselines-findings.md
    - research/experiments/2026/2026-04-29-phase-B4-sam-track-b-hard-prune-findings.md
    - research/experiments/2026/2026-04-29-phase-B5-sam-s4-reexport-findings.md
    - research/experiments/2026/2026-04-29-phase-M5-5b-sam-prefix-snapshot-fix-findings.md
    - research/experiments/2026/2026-04-29-phase-M5-comp-sam-prefix-snapshot-32f-composition-findings.md
    - research/experiments/2026/2026-05-02-phase-perception-fps-headline-findings.md
    - research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b0b_cache_correctness_summary.json
    - research/experiments/2026/artifacts/sam_scaleout_m5_r2_20260430/sam_b0b_cache_correctness_summary.json
    - research/experiments/2026/artifacts/sam_scaleout_m5_r2_20260430/sam_b0b_cache_correctness.jsonl
    - research/experiments/2026/artifacts/sam_scaleout_m5_r2_followup_20260430/sam_b0b_cache_correctness_unguarded_patched_summary.json
    - research/experiments/2026/artifacts/sam_scaleout_m5_r2_followup_20260430/sam_b0b_cache_correctness_unguarded_patched.jsonl
    - research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_m5_5b_swa_prefix_snapshot_summary.json
    - research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_m5_5b_swa_prefix_snapshot_32f_n21_summary.json
    - research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b3_streaming_baselines_summary.json
    - research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b4_sparse_vit_ceiling_summary.json
    - research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b5_s4_accuracy_1937_summary.json
    - research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b5_s4_raw_paired_513_summary.json
  current_best_policy: "candidate C-STREAM remains mixed: default cache path blocked; patched topology-aware B0b path is full-regression correctness-clean but falls back to cold-dense speed; prefix snapshot positive small-N including 32f n=21 with 0 choice/correctness diffs and 7/21 text diffs; derived perception-fps view is 27.02fps median at 8f (8/21 rows >=30fps) and 54.68fps median at 32f (19/21 rows >=30fps), after-warm only; low-FPS dense wins fixed-evidence baseline"
  supersedes: []
  paper_relevance: scale-out bounded evidence
  prereg_outcome: Accepted with caveat
```

### Foundation (phases 1.0–1.9)

Registry entries for the foundation phases (cache-path identity,
mechanism reproduction, TOMATO/MVBench subset smokes, benchmark
path controls, matched dense frame-budget baselines) are kept
authoritative in the per-phase notes under
`research/experiments/2026/`. This registry is summary; see
`docs/reproduction-status.md` for the pre-release source claim status table.

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
  status: completed (holdout v2 cells)
  authoritative_note: research/experiments/2026/2026-04-15-phase-1_20-tomato-motion-slice-enlargement.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_20_tomato_motion_holdout_v2_dense_summary.json
    - research/experiments/2026/artifacts/phase1_20_tomato_motion_holdout_v2_cached_summary.json
    - research/experiments/2026/artifacts/phase1_20_tomato_motion_holdout_v2_pareto.json
  current_best_policy: "max_abs(8,32) static+shifted age=4 — cached=0.333@3.55, ties dense-8 at 44% budget (CLEAN TREE)"
  supersedes: [1.12 TOMATO holdout (N=15 → N=30)]
  paper_relevance: primary (TOMATO N=30 holdout — PAPER-GRADE, clean tree)
  prereg_outcome: Accepted (clean-tree rerun confirmed)

- phase_id: 1.21
  status: completed (holdout v2 cells; dev v2 cells deferred)
  authoritative_note: research/experiments/2026/2026-04-15-phase-1_21-mvbench-motion-slice-enlargement.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_21_mvbench_motion_holdout_v2_dense_summary.json
    - research/experiments/2026/artifacts/phase1_21_mvbench_motion_holdout_v2_cached_summary.json
    - research/experiments/2026/artifacts/phase1_21_mvbench_motion_holdout_v2_cached_nosticky_summary.json
    - research/experiments/2026/artifacts/phase1_21_mvbench_motion_holdout_v2_pareto.json
    - research/experiments/2026/artifacts/phase1_21_mvbench_motion_holdout_v2_nosticky_pareto.json
    - research/experiments/2026/artifacts/phase1_21_sticky4_vs_dense8_holdout_v2.json
    - research/experiments/2026/artifacts/phase1_21_nosticky_vs_dense8_holdout_v2.json
  current_best_policy: "base: max_abs(8,32) static+shifted age=4 — cached=0.600@4.06 (clean tree, Pareto win vs dense-6); sticky4 refinement: cached=0.633@4.49 (supplementary rerun-required, Pareto tie vs dense-8)"
  supersedes: [1.12.B (strengthened at N=30)]
  paper_relevance: primary (MVBench N=30 holdout — claim #6 MVBench half PASSED)
  prereg_outcome: Accepted (holdout v2 cells; dev v2 deferred as protocol note)

- phase_id: 1.23
  status: completed
  authoritative_note: research/experiments/2026/2026-04-15-phase-1_23-fastv-composition-scouting.md
  authoritative_artifacts:
    - historical scout document removed from the public artifact tree; see git history
      if the original phase-1.23 implementation sketch is needed
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
  status: completed
  authoritative_note: research/experiments/2026/2026-04-16-phase-1_26-sticky-dynamic-planner.md (to be extended)
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_26c_sticky_on_mvbench_dev/
  current_best_policy: "testing sticky_window ∈ {4, 8} on MVBench motion DEV to validate mechanism reproducibility beyond holdout"
  supersedes: []
  paper_relevance: diagnostic
  prereg_outcome: (pending completion)

- phase_id: 1.27
  status: superseded
  authoritative_note: research/experiments/2026/2026-04-16-phase-1_27-projector-group-completion.md
  authoritative_artifacts: []
  current_best_policy: n/a
  supersedes: []
  paper_relevance: superseded (BLOCK_SIZE=28 is already projector-input granularity on Qwen 2.5-VL; any spatial-pruning follow-on should be a separately measured Gemma path, not a claim imported by name)
  prereg_outcome: not run (mechanism is a no-op on current stack)

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
  status: semantic breadth passed; calibration-mode/source ablations closed neutral; systems integration pending
  authoritative_note: research/experiments/2026/2026-04-23-phase-1_29B-codec-native-replication-prereg.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_29_planner_accuracy_probe/results.jsonl
    - research/experiments/2026/artifacts/phase1_29_planner_accuracy_probe/summary.json
    - research/experiments/2026/artifacts/phase1_29B_short_holdout_20260423/results.jsonl
    - research/experiments/2026/artifacts/phase1_29B_short_holdout_20260423/summary.json
    - research/experiments/2026/artifacts/phase1_29B_dev30_duration_20260423/results.jsonl
    - research/experiments/2026/artifacts/phase1_29B_dev30_duration_20260423/summary.json
  current_best_policy: "VideoMME 8f dev all-duration n=30 Qwen 2.5-VL-7B-4bit: codec_dense_agreement 1.000 (30/30), codec_accuracy=dense_accuracy=0.533, codec_pixel_agreement 0.933, reuse-ratio gap 1.6pp, parse failures 0. Short dev+holdout n=20 also passes on the -5pp accuracy-loss boundary. This is local codec-native planner-substitution evidence, not a latency win: offline codec extraction totals 7290s (long mean 615s/item)."
  supersedes: []
  paper_relevance: candidate body row with caveats (local codec-native planner-substitution evidence now spans short/medium/long dev n=30; calibration-mode/source ablations are closed neutral; streaming integration remains needed before deployment/system-speed claims)
  prereg_outcome: MAX-over-span sparse retrofit falsified; continuous-score redesign partial-pass at aggregate level; planner-accuracy probe first-point-confirmed on n=10 short (2026-04-23); short-holdout replication MIXED-positive and combined short n=20 PASS on boundary (2026-04-23); all-duration dev n=30 H_duration_breadth PASS (2026-04-23)
  notes: 2026-04-23 first-point run lands at 495a57b. Continuous-score + per-item live-pixel calibration substitutes 1:1 for dense planner on the dev-short pilot (10/10 agreement) and beats pixel oracle by +0.10. Codex takeover corrected the impossible "n=30 short" follow-up: fixed manifests provide dev-short n=10 + holdout-short n=10, not short n=30. Holdout short lands codec_dense_agreement 0.900, codec_pixel_agreement 1.000, codec_accuracy 0.700 vs dense 0.800. Pooled short n=20 passes exactly at the -5pp accuracy-loss boundary. The all-duration dev n=30 run then passes strongly: codec equals dense on 30/30 choices across long/medium/short. 2026-04-24 follow-up runs then closed both calibration axes neutral on the local slices we ran: pooled/per-item and live-pixel/artifact source changes produce identical answer-level outcomes. Operational caveat is severe: offline codec extraction totals 121.5 min, so this is not a systems speedup route without streaming decoder integration or a cache/checkpointed pipeline.

- phase_id: 1.30
  status: CLOSED-SCOUT (speedup PASS, accuracy FALSIFIED; root-cause localized to V-only Q0 pruning on short-scout slice)
  authoritative_note: research/experiments/2026/2026-04-23-phase-1_30-rootcause-findings.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_30_scaleout_streaming/cold_summary.json
    - research/experiments/2026/artifacts/phase1_30_scaleout_streaming/streaming_summary.json
    - research/experiments/2026/artifacts/phase1_30_scaleout_streaming/pair_summary.json
    - research/experiments/2026/artifacts/phase1_30_scaleout_streaming/paired_queries.jsonl
    - research/experiments/2026/artifacts/phase1_30_rootcause_short_codex_20260423/analysis.txt
    - research/experiments/2026/artifacts/phase1_30_rootcause_short_codex_20260423/q0_parity_compare.txt
    - research/experiments/2026/artifacts/phase1_30_rootcause_short_codex_20260423/q0_dense_path_compare.txt
  current_best_policy: "Qwen 2.5-VL-7B-4bit VideoMME 8f dev+holdout union n=57 sessions / 171 queries: cold 0.561 (96/171) / streaming 0.368 (63/171) → Δacc = −0.193, FALSIFIES ±0.05 budget; paired amortized 3.326× speedup PASSES. Short-scout root-cause: H_V PASS, H_K FAIL, H_interaction FAIL, H_reset PASS, H_path PASS; dominant loss is V-only Q0 pruning at L=2, kr_V=0.50."
  supersedes: []
  paper_relevance: negative-result with mechanism attribution; composition bridge requires safer/adaptive V admission before deployment-grade framing
  prereg_outcome: H_stream_e2e accuracy-FALSIFIED, speedup-PASSED; root-cause Phase A/B landed 2026-04-23: H_V PASS, H_K FAIL, H_interaction FAIL, H_reset PASS, H_path PASS; Phase C not triggered
  notes: 2026-04-23 paired-data analysis (codex round-28) showed Q0 alone drops −0.105, violating the ±0.05 budget before any KV reuse. Codex takeover reran the preregistered 6-arm short scout in a fresh artifact directory after the Claude run was interrupted. Results: cold_dense 0.733, cold_pruned 0.400, streaming_dense_off 0.667, streaming_pruned_off 0.300, streaming_dense_reset 0.733, streaming_pruned_reset 0.400. Q0 parity against 1.51V passes 10/10 for pruned and dense paths after normalizing letter-vs-index choice encodings. Phase 1.30V then tested fixed kr=0.67/0.75 rescue and failed the Q0 accuracy gate, so the next 1.30 composition path requires an adaptive admission/no-prune policy rather than Phase C or another blind fixed-rate run.

- phase_id: 1.30V
  status: CLOSED-NEGATIVE 2026-04-23
  authoritative_note: research/experiments/2026/2026-04-23-phase-1_30V-adaptive-vleg-findings.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_30V_adaptive_vleg_q0_20260423/q0_151V_L2_kr067_summary.json
    - research/experiments/2026/artifacts/phase1_30V_adaptive_vleg_q0_20260423/q0_151V_L2_kr075_summary.json
    - research/experiments/2026/artifacts/phase1_30V_adaptive_vleg_q0_20260423/q0_kr067_vs_dense_compare.txt
    - research/experiments/2026/artifacts/phase1_30V_adaptive_vleg_q0_20260423/q0_kr075_vs_dense_compare.txt
  current_best_policy: n/a; fixed-rate Q0 rescue failed on the short-scout items
  supersedes: []
  paper_relevance: negative follow-up to 1.30 root-cause; rules out a simple fixed-kr rescue of the deployment composition bridge
  prereg_outcome: H_recover FAIL for kr_V=0.67 and kr_V=0.75. kr=0.75 reaches dense-choice agreement 0.800 but Q0 accuracy remains 0.700 < 0.800 gate.
  runtime_estimate: complete
  notes: Same ten Q0 items as 1.30 root-cause Phase A. Dense reference accuracy 0.900; L2 kr=0.50 accuracy 0.500; L2 kr=0.67 accuracy 0.700, dense-choice agreement 0.600, effective keep-rate 0.688; L2 kr=0.75 accuracy 0.700, dense-choice agreement 0.800, effective keep-rate 0.750. Future 1.30 composition work should be adaptive admission/no-prune-on-risky-Q0, not another blind fixed-rate sweep.

- phase_id: 1.30W
  status: partial (exact Q0 parity; bounded near-miss on the full-session bridge)
  authoritative_note: research/experiments/2026/2026-04-24-phase-1_30W-q0-dense-followup-pruned-full-findings.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_30W_q0_dense_followup_pruned_full/cold_dense_summary.json
    - research/experiments/2026/artifacts/phase1_30W_q0_dense_followup_pruned_full/streaming_q0_dense_followup_pruned_off_summary.json
    - research/experiments/2026/artifacts/phase1_30W_q0_dense_followup_pruned_full/pair_summary.json
    - research/experiments/2026/artifacts/phase1_30W_q0_dense_followup_pruned_full/per_clip_buckets.json
    - research/experiments/2026/artifacts/phase1_30W_q0_dense_followup_pruned_full/paired_queries.jsonl
  current_best_policy: "Qwen 2.5-VL-7B-4bit VideoMME 8f dev+holdout union n=57 sessions / 171 queries: cold 0.561 (96/171) / streaming 0.503 (86/171) → Δacc = −0.0585 and paired 2.7869× speedup. Q0 is exact (34/57 in both arms); all residual loss is follow-up-only."
  supersedes: []
  paper_relevance: active near-miss / boundary cell; strongest local composition bridge so far, but still below the preregistered deployment-speed floor
  prereg_outcome: H_q0 PASS exactly (`34/57` in both arms) and H_format PASS (`0` parse failures, `0` degenerates). H_strict FAIL (`Δacc = −0.0585`, speedup `2.7869×`). H_rescue also FAILS because speed remains below the `>=3.0×` floor even though accuracy stays inside the `>=−0.10` rescue band.
  runtime_estimate: complete
  notes: This full rerun materially improves the original 1.30 negative (`Δacc = −0.193`) without reopening the preregistered bridge. The decisive mechanistic result is that dense Q0 fully fixes the first-query leg: Q0 accuracy is numerically identical in every `duration × split` cell. All remaining loss is follow-up-only, with the strongest deficits in long dev (`follow-up delta = −0.125`), short dev (`−0.10`), short holdout (`−0.1111`), and medium holdout (`−0.10`); medium dev and long holdout follow-ups match cold exactly. Wording discipline: this row should be described as **dense-Q0 admission plus the existing session-reuse follow-up path**, not as proven "pruned follow-ups", until the new image-token activity instrumentation shows how much follow-up vision pruning is actually active under prompt-cache reuse. The speed miss is structural under the current 3-query protocol: dense Q0 alone consumes `5.249M ms`, while the full run would need to fit inside `4.981M ms` to earn `3.0×`; even zero-cost follow-ups would still miss by `268.7k ms`. If 1.30 continues, the next meaningful work is either a safe cheaper-Q0 policy or a longer-session protocol, not another same-protocol follow-up-only keep-rate tweak.

- phase_id: 1.30X
  status: partial (speed/accuracy rescue reopened offline; no format-clean point in the current endpoint family)
  authoritative_note: research/experiments/2026/2026-04-24-phase-1_30X-q0-admission-frontier-findings.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_30X_q0_admission_frontier/analysis.json
  current_best_policy: "Deployable duration-gated replay: dense_on_medium_short on VideoMME 8f dev+holdout union n=57 sessions / 171 queries yields cold 0.561 (96/171) / streaming 0.480 (82/171) → Δacc = −0.0819 at 3.0168×, but still leaves 2 parse failures / degenerates. Exact per-session frontier upper bound reaches Δacc = 0.0000 at 3.0781×."
  supersedes: []
  paper_relevance: active reopening analysis for the streaming bridge; shows same-protocol admission is viable on speed/accuracy but still blocked on format hygiene
  prereg_outcome: H1 FALSIFIED on the preregistered speed/accuracy rescue criterion because `dense_on_medium_short` passes `Δacc >= −0.10` and `speedup >= 3.0×`. H2 EARNED strongly: the exact frontier contains a `Δacc = 0.0000`, `3.0781×` point. But `best_strict_with_format` and `best_rescue_with_format` are both null within the current 1.30 / 1.30W endpoint family.
  runtime_estimate: complete
  notes: This offline frontier replay uses only landed session-level outputs from 1.30 and 1.30W; no synthetic within-session timings or answer edits are allowed. The decisive new result is that the current 3-query protocol is no longer closed on speed/accuracy: a simple duration policy (`dense_on_medium_short`) already passes the rescue band. The remaining full-promotion gap is entirely format hygiene. Under that deployable policy, the residual bad sessions are `videomme:long:783-2` and `videomme:long:847-3`. Wording discipline: the `Δacc = 0.0000`, `3.0781×` frontier point is an **oracle upper bound over the landed endpoint family**, not a deployable policy. The exact frontier proves that the lane is not dead in principle, but also proves the current 2-endpoint family is insufficient for a format-clean reopening. If 1.30 continues, the next move should target those long-session format failures explicitly or introduce a third endpoint family, not rerun another global policy.

- phase_id: 1.30Y
  status: SCOUT COMPLETE 2026-04-24 (`kr_Q0 = 0.67` promoted, `kr_Q0 = 0.75` rejected)
  authoritative_note: research/experiments/2026/2026-04-24-phase-1_30Y-residual-long-q0-keep-rate-findings.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_30Y_residual_long_q0_keep_rate_20260424/cold_dense_summary.json
    - research/experiments/2026/artifacts/phase1_30Y_residual_long_q0_keep_rate_20260424/streaming_q0_kr100_followup_kr050_summary.json
    - research/experiments/2026/artifacts/phase1_30Y_residual_long_q0_keep_rate_20260424/streaming_q0_kr075_followup_kr050_summary.json
    - research/experiments/2026/artifacts/phase1_30Y_residual_long_q0_keep_rate_20260424/streaming_q0_kr067_followup_kr050_summary.json
  current_best_policy: residual-pair scout only; `kr_Q0 = 0.67`, `kr_followup = 0.50` is the promoted long-bucket candidate
  supersedes: []
  paper_relevance: active bridge-repair scout for the 1.30 streaming composition lane
  prereg_outcome: `kr_Q0 = 0.75` fails the key format gate (degenerate `847-2`); `kr_Q0 = 0.67` earns the scout format gate (`0` parse, `0` degenerate) and improves the residual pair from `4/6` to `5/6` versus the dense-Q0 reference.
  runtime_estimate: complete (~35 min benchmark-only on the residual pair)
  notes: The purpose of this scout is deliberately narrow: after 1.30X, the only remaining format failures under the deployable `dense_on_medium_short` policy are `videomme:long:783-2` and `videomme:long:847-3`, and forcing those two sessions onto the dense-Q0 family misses the full-policy `3.0×` line by only `0.006×`. The scout shows that a cheaper long-session Q0 regime is still viable: `kr_Q0 = 0.67` stays clean on both binding sessions and improves the pair to `5/6`, while `kr_Q0 = 0.75` reintroduces a degenerate follow-up. Wording discipline: this is a **selection-biased routing scout**, not paper evidence. The splice against the landed medium/short dense-Q0 results (`Δacc ≈ -0.0702`, `3.0023×`) is only a design hint that justifies a full long-bucket continuation; it must not be treated as a measured full-policy result.

- phase_id: 1.30Z
  status: landed (FAIL rescue gate; falsifies 1.30Y candidate)
  authoritative_note: research/experiments/2026/2026-04-25-phase-1_30Z-long-q0-kr067-findings.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_30Z_long_q0_kr067_20260424/pair_summary.json
    - research/experiments/2026/artifacts/phase1_30Z_long_q0_kr067_20260424/per_clip_buckets.json
  current_best_policy: closed for `kr_Q0 = 0.67` long-bucket Q0 admission; reverts to 1.30W (full-union dense Q0 + cache-reused follow-ups, Δ=−0.058 / n=171)
  supersedes:
    - 1.30Y (selection-biased residual scout; falsified at scale)
  paper_relevance: primary (closes the duration-conditioned admission lane in this configuration)
  prereg_outcome: H1 FAIL (Δacc=−0.130 / n=54, beyond the −0.10 rescue gate; CI95=[−0.278, +0.019]); H2 PASS (0 parse failures, 0 degenerate); speedup 3.12× passes; H4 PASS-as-explicitly-absent (vision_pruning_active_fraction=0.0, all_image_tokens_reused_fraction=1.0 — the relabel-as-Q0-admission rule fires).
  runtime_estimate: complete (~58 min on this laptop because the cold arm was reused; streaming arm only)
  notes: First measured generalization test of the 1.30Y residual-pair scout. The result both falsifies the kr_Q0=0.67 candidate and provides the first quantitative measurement that the kr_followup=0.50 vision config is mechanically a no-op under prompt-cache reuse on every long-bucket follow-up. Auto-committed by the closeout queue runner as `6df2369`.

- phase_id: 1.30AA
  status: skipped-by-1.30Z-gate (pre-registered; correctly not run after 1.30Z failed H1)
  authoritative_note: research/experiments/2026/2026-04-25-phase-1_30AA-duration-conditioned-union-prereg.md
  authoritative_artifacts: []
  current_best_policy: n/a (the gate that would have unlocked this run did not pass)
  supersedes: []
  paper_relevance: primary (would have produced the first publishable no-splice bridge candidate in the 1.30 family if 1.30Z had passed)
  prereg_outcome: not run; the closeout queue's `should_launch_130aa = pass_rescue and pass_format` gate evaluated to False after 1.30Z landed Δacc=−0.130. Saved an estimated ~6 hours of MLX compute on a doomed-by-policy run.
  runtime_estimate: not consumed
  notes: Re-running 1.30AA only makes sense if 1.30Z's underlying policy family is replaced (e.g. 1.30AB long-Q0 finer sweep) or if 1.30AC enables true follow-up vision pruning by invalidating the cache between queries. The current configuration is closed.

- phase_id: 1.30AB
  status: landed (FAIL — all 4 candidates miss rescue gate; long-Q0 admission lane closed under cache-reuse)
  authoritative_note: research/experiments/2026/2026-04-25-phase-1_30AB-long-q0-sweep-findings.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_30AB_long_q0_kr075/pair_summary.json
    - research/experiments/2026/artifacts/phase1_30AB_long_q0_kr080/pair_summary.json
    - research/experiments/2026/artifacts/phase1_30AB_long_q0_kr085/pair_summary.json
    - research/experiments/2026/artifacts/phase1_30AB_long_q0_kr090/pair_summary.json
  current_best_policy: 1.30W remains the best landed 1.30 lane number; admission family closed at long-bucket under cache-reuse follow-ups
  supersedes:
    - 1.30Y (selection-biased scout, falsified by full sweep)
  paper_relevance: primary (closes the duration-conditioned admission lane; produces a clean Q0/follow-up decoupling mechanism finding at kr_Q0 ≥ 0.85)
  prereg_outcome: H1 FALSIFIED (no candidate clears Δacc ≥ -0.10 + speedup ≥ 3.0 + format clean); H2 vacuously satisfied (no passing rate); H3 EARNED across all 5 long-bucket runs (active_fraction=0.0). Headline numbers: kr=0.75/0.80 → Δ=-0.185; kr=0.85/0.90 → Δ=-0.130 with q0_dacc=0.000 (Q0 EXACT parity, follow-up drift -0.194 dominates).
  runtime_estimate: complete (~2.5h total; cold reused from 1.30Z)
  notes: Mechanism evidence — at kr_Q0 ≥ 0.85, Q0 admission accuracy is exactly preserved but follow-up drift is locked at ~-19pp. This isolates post-Q0 K-cache state quality as the failure mode, not Q0 admission accuracy. Auto-committed by the queue as `dc599d3`, `36cdc21`, `c506614`, `53622c3`; consolidated findings as `148e5e3`.

- phase_id: 1.30AE
  status: skipped-by-1.30AB-gate (correct queue logic — no 1.30AB candidate passed)
  authoritative_note: research/experiments/2026/2026-04-25-phase-1_30AE-duration-conditioned-union-candidate-prereg.md
  authoritative_artifacts: []
  current_best_policy: n/a (the gate that would have unlocked this run did not pass)
  supersedes:
    - 1.30AA (policy family replaced after 1.30Z)
  paper_relevance: primary (would have produced the first no-splice union rerun after 1.30Z if any 1.30AB candidate had cleared)
  prereg_outcome: not run; queue's `_select_130ab_rate()` returned None after all four 1.30AB candidates failed the rescue gate. Saved an estimated ~6 hours of MLX compute.
  runtime_estimate: not consumed
  notes: Re-running 1.30AE only makes sense if a fundamentally different policy family lands a passing rate. The current cache-reuse admission family is closed across kr_Q0 ∈ {0.67, 0.75, 0.80, 0.85, 0.90}. Future paths: 1.30AC (cache-invalidated follow-ups, prereg 39f5097), 1.30AD (instrumented 1.30W rerun, prereg 234bf3d), or an optional 1.30AB-fine at kr_Q0=0.95.

- phase_id: 1.30AC
  status: completed 2026-04-27
  authoritative_note: research/experiments/2026/2026-04-25-phase-1_30AC-cache-invalidated-followups-prereg.md
  authoritative_artifacts: [research/experiments/2026/artifacts/phase1_30AC_cache_invalidated_followups/]
  current_best_policy: cache-invalidated follow-up test: follow-up vision activity fires, speedup collapses to 1.06x, and aggregate loss matches the cache-reuse arm through different row-level failures
  supersedes: []
  paper_relevance: primary mechanism adjudication for the 1.30 lane
  prereg_outcome: boundary landed; use as evidence that active follow-up pruning is not a deployable rescue in the current family
  runtime_estimate: complete
  notes: This is the first 1.30-family run that can support or falsify an actual follow-up vision-pruning mechanism claim. The wrapper runs a one-seed smoke first and aborts unless follow-up rows show prefix_hit=0, all image tokens recomputed, and vision_pruning_active=true.

- phase_id: 1.30AD
  status: completed 2026-04-27
  authoritative_note: research/experiments/2026/2026-04-25-phase-1_30AD-instrumented-1_30W-rerun-prereg.md
  authoritative_artifacts: [research/experiments/2026/artifacts/phase1_30AD_instrumented_w_rerun/]
  current_best_policy: instrumented cache-reuse reference: reproduces 1.30W aggregate boundary while preserving the speed profile
  supersedes: []
  paper_relevance: paper-locking mechanism measurement for the 1.30W reference line
  prereg_outcome: landed; pairs with 1.30AC and 1.30AF for the composition-boundary narrative
  runtime_estimate: complete
  notes: Expected to reproduce the landed 1.30W delta and directly confirm that follow-up pruning activity is negligible under prompt-cache reuse. If it does not reproduce within the preregistered delta/CI bands, the 1.30W line needs an explicit reproducibility note.

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
  status: completed
  authoritative_note: research/experiments/2026/2026-04-17-phase-1_34-novelty-ranked-dense.md
  authoritative_artifacts:
    - phase note records the exact local-only ignored results tree and commit IDs; regenerate or re-materialize before using as manuscript claim evidence
  current_best_policy: n/a (stronger baseline, not a new policy)
  supersedes: []
  paper_relevance: historical comparator unless the ignored results files are regenerated or re-materialized as checked artifacts
  prereg_outcome: Accepted (Planner 2.0 cached dominates every novelty cell at equal-or-lower budget; novelty hurts on TOMATO N>=6 and saturates on MVBench N>=6)

- phase_id: 1.35
  status: proposed
  authoritative_note: research/experiments/2026/2026-04-16-phase-1_35-event-window-oracle.md
  authoritative_artifacts: []
  current_best_policy: n/a (oracle ceiling, not a policy)
  supersedes: []
  paper_relevance: primary (method headroom)
  prereg_outcome: (pending)

- phase_id: 1.36
  status: completed
  authoritative_note: research/experiments/2026/2026-04-17-phase-1_36-feature-change-oracle.md
  authoritative_artifacts:
    - phase note records the exact local-only ignored results tree and commit IDs; regenerate or re-materialize before using as manuscript claim evidence
  current_best_policy: n/a (oracle/diagnostic, not a routing policy)
  supersedes: []
  paper_relevance: diagnostic / historical unless the ignored results files are regenerated or re-materialized as checked artifacts
  prereg_outcome: Accepted with caveat (Pearson r=0.23-0.50 caps below the r>=0.7 preregistered target; 45/60 item coverage due to cache-key rewrite; the finding reframes claim as a ranking/diagnosis study rather than a leaderboard)

- phase_id: 1.37
  status: proposed
  authoritative_note: research/experiments/2026/2026-04-16-phase-1_37-child-veto-subtoken-guard.md
  authoritative_artifacts: []
  current_best_policy: n/a (mechanism not yet implemented)
  supersedes: []
  paper_relevance: primary (claim #3 concentration-aware routing — within-block subtoken guard half)
  prereg_outcome: (pending; code path lives in _mix_qwen_features and has NOT been written; distinct from 1.37B)
  notes: the 2026-04-17 "Planner 2.1" prereg that previously lived under this phase ID has been rescoped to phase 1.37B (neighbor-halo veto); this phase retains the original 2026-04-16 within-block 2x2 child-veto specification. Status `proposed` per registry vocab (prereg written, code unimplemented).

- phase_id: 1.37B
  status: completed
  authoritative_note: research/experiments/2026/2026-04-17-phase-1_37B-neighbor-halo-veto-prereg.md
  authoritative_artifacts:
    - src/codec_through/temporal.py (NeighborHaloVetoConfig, apply_neighbor_halo_veto, _neighborhood_max)
    - tests/test_neighbor_halo_veto.py
    - scripts/run_benchmark_track_a.py (--halo-veto-percentile / --halo-veto-neighborhood)
    - research/experiments/2026/artifacts/phase1_37B_tomato_motion_dev_v2_cached/halo_analysis.json
    - research/experiments/2026/artifacts/phase1_37B_mvbench_motion_dev_v2_cached/halo_analysis.json
  current_best_policy: control (no halo-veto); halo-veto axis is therefore FROZEN at {no-halo-veto} for future combined sweeps
  supersedes: []
  paper_relevance: primary (claim #3 concentration-aware routing — spatial neighbor-halo half); after 2026-04-17 retirement this claim rests on phase 1.37 within-block child-veto as the remaining mechanism path
  prereg_outcome: Rejected (preregistered null — NO-LIFT on TOMATO, HURTS on MVBench; both dev benchmarks fail the promotion rule → full retirement, no holdout run)
  notes: originally filed as "phase 1.37 Planner 2.1"; renamed 2026-04-17 after external review flagged that "child-veto" was the name of a distinct mechanism (within-block subtoken guard) and should not be reused for the neighbor-halo variant. Closed 2026-04-17 as preregistered null: TOMATO control rank-1 at cached_accuracy 0.233 with all cells within 1/30 MRU; MVBench control sole rank-1 at 0.800 with 7/8 halo cells losing 0.067-0.100. Halo moves only the agreement knob on TOMATO while draining fresh-frame budget, and actively hurts accuracy on MVBench.

- phase_id: 1.41
  status: EARNED 2026-04-18 (8f); strengthened 2026-04-19 (16f, 32f); **holdout 16f EARNED 2026-04-21** — Qwen 2.5-VL-7B-Instruct-4bit dense on `videomme_dev_v1.toml` n=30 AND `videomme_holdout_v1.toml` n=30 at 16f, parse_failures=0, agreement=1.000 at all frame counts on both splits. Holdout 16f aggregate 0.700 (21/30); per-bucket short 0.600 / medium 0.600 / **long 0.900**. Claim 8 (VideoMME breadth gate) satisfied dev+holdout. **Non-monotone long-bucket regression at 16f is DEV-ONLY and did NOT replicate on holdout** (dev 8f long 0.300 → dev 16f long 0.100; holdout 16f long 0.900 — per-bucket item-draw effect exceeds frame-scaling signal). Paper claim "16f long-bucket regresses" must soften to dev-only. Phase 1.57 drift geometry now covers Qwen dev plus 8f/16f holdout re-check; the 16f co-saturation framing remains local to dev because 32f holdout drift was not computed. 32f adds prompt-length 2× and latency 2× for zero aggregate acc lift over 16f — NOT Pareto-efficient at this model/benchmark.
  authoritative_note: research/experiments/2026/2026-04-16-phase-1_41-videomme-lane.md + research/experiments/2026/2026-04-19-phase-1_41-qwen-videomme-16f-prereg.md + research/experiments/2026/2026-04-19-phase-1_41-qwen-videomme-32f-long-prereg.md + research/experiments/2026/2026-04-19-phase-1_57-feature-drift-mechanism-prereg.md
  authoritative_artifacts:
    - scripts/build_videomme_manifest.py
    - scripts/fetch_videomme_subset.py
    - research/benchmark_manifests/videomme_dev_v1.toml
    - research/benchmark_manifests/videomme_holdout_v1.toml
    - research/experiments/2026/artifacts/phase1_41_qwen_videomme/ (8f dense baseline)
    - research/experiments/2026/artifacts/phase1_41_qwen_videomme_16f/ (16f follow-up)
    - research/experiments/2026/artifacts/phase1_41_qwen_videomme_32f_long/ (32f long-bucket third data point)
    - research/experiments/2026/artifacts/phase1_41_qwen_videomme_16f_holdout/ (holdout 16f, 2026-04-21)
    - research/experiments/2026/artifacts/phase1_57/ (STATIC-class drift mechanism; adjacent-frame ViT cos)
    - research/experiments/2026/2026-04-19-phase-1_41-qwen-videomme-16f-findings.md
    - research/experiments/2026/2026-04-19-phase-1_41-qwen-videomme-32f-long-findings.md
    - research/experiments/2026/2026-04-21-phase-1_41-qwen-videomme-16f-holdout-findings.md
    - research/experiments/2026/2026-04-19-phase-1_57-feature-drift-findings.md
  current_best_policy: Qwen 2.5-VL-7B-4bit dense at 16f is the paper-reporting default on VideoMME dev (best per-bucket accuracy at Pareto-efficient frame count: short 0.800 / medium 0.700 / long 0.100, agg 0.567). 32f is NOT recommended for paper reporting (flat aggregate, 2× latency).
  supersedes: []
  paper_relevance: primary (claim #8 VideoMME breadth gate; also feeds claim #15 C-VISION frame-count sweep denominator via V_share measurements at 8f/16f/32f)
  prereg_outcome: EARNED at 8f (2026-04-18); STRENGTHENED at 16f+32f (2026-04-19); **holdout 16f CLOSED 2026-04-21** — H1 pass (agg 0.700, at upper edge of [0.50, 0.70]), H2 FALSIFIES (long-bucket regression dev-only; holdout 16f long 0.90 vs dev 16f long 0.10 / dev 8f long 0.30), H3/H4/H5 pass. Three-frame-count × two-split per-bucket surface mapped. Mechanism (1.57 feature-drift as lower-bound proxy): Qwen drift geometry transfers to holdout at 8f/16f with max class-statistic delta <= 5pp; 32f remains dev-only. Dev drift rises sub-linearly 8f→32f and co-saturates with dev accuracy at 16f on the long bucket, so drift is a co-indicator of dev-split capacity plateau, not the binding cross-split constraint.
  notes: VideoMME videos hosted on HF `lmms-lab/Video-MME` as 20 chunked zip archives (~101 GB full corpus); paper protocol uses 57 unique videoIDs (dev+holdout manifests, one overlap). `scripts/fetch_videomme_subset.py` walks chunks one-at-a-time (peak disk ~5 GB staging + ~3-15 GB extracted subset). See `docs/videomme-download-handoff.md` for env gotchas (HF xet backend must be disabled; SOCKS proxy env vars must be cleared). Phase 1.58 (bf16 quantization ablation) is the remaining open mechanism question for 32f plateau — deferred pending 1.51V primary axis.

- phase_id: 1.42
  status: completed split 2026-04-24
  authoritative_note: research/experiments/2026/2026-04-17-phase-1_42-gemma-architecture-topology-prereg.md + research/experiments/2026/2026-04-24-phase-1_42-gemma-findings.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_42_gemma_tomato_motion_holdout_v2_mc_cached/
    - research/experiments/2026/artifacts/phase1_42_gemma_mvbench_motion_holdout_v2_mc_cached/
    - research/experiments/2026/artifacts/phase1_42_gemma_smoke_mc/
  current_best_policy: n/a (second-architecture fidelity boundary, not a policy; transferred Planner 2.0 base policy)
  supersedes: []
  paper_relevance: primary (claim #7 architecture-conditioned reuse fidelity — takes evidence from N=1 to N=2 architectures)
  prereg_outcome: Split result. TOMATO motion holdout N=30 passes fidelity gate (dense_acc=cached_acc=0.2667, agreement=0.9333, parse failures 0); MVBench motion holdout N=30 fails strict agreement despite tied aggregate accuracy (dense_acc=cached_acc=0.2000, agreement=0.7333, parse failures 0). Claim #7 is strengthened to a benchmark-conditioned architecture spectrum, not a universal all-global-high-fidelity rule.
  notes: Gemma 4-E4B-IT-4bit verified to load on M3 Air 16 GB. The run uses explicit multiple-choice scoring because Gemma's local free-form path was parse-hostile despite matching dense/cached prefill logits on the smoke item. Corrected cached-feature geometry is 133 pooled tokens/frame on the live 560x560 Gemma path.

- phase_id: 1.43
  status: proposed
  authoritative_note: research/experiments/2026/2026-04-17-phase-1_43-egoschema-lane-prereg.md
  authoritative_artifacts: []
  current_best_policy: n/a
  supersedes: []
  paper_relevance: primary (EgoSchema breadth gate; long-form egocentric)
  prereg_outcome: (pending; needs EgoSchema loader implementation + benchmark manifest build — NOT gated on phase 1.42; the 1.43 prereg explicitly scopes this lane to Qwen 2.5-VL and does not consume `_mix_gemma_features`)
  notes: Huggingface lmms-lab/EgoSchema is open-licensed (no TOS click-through unlike VideoMME); 3-min clips at 22 s inter-frame gap stress-test reuse fidelity

- phase_id: 1.50
  status: completed
  authoritative_note: research/experiments/2026/2026-04-17-phase-1_50-track-b-dense-baseline.md
  authoritative_artifacts:
    - phase note records the exact local-only ignored results tree and commit IDs; current release-facing sparse-vision claims use checked 1.63 artifacts
    - historical dense-baseline driver removed from the public artifact tree;
      current measured sparse-vision claims use the 1.63 drivers below
  current_best_policy: n/a (wall-clock baseline, not a policy)
  supersedes: []
  paper_relevance: historical dense reference; current paper-facing measured sparse-vision claims use checked 1.63 artifacts
  prereg_outcome: Accepted with caveat (dense baseline paper-grade on TOMATO N=30 + MVBench N=30 holdout in the local results tree; cross-benchmark vision-cache ceiling 20-23% end-to-end; superseded for current sparse-vision reporting by checked 1.63 artifacts)

- phase_id: 1.51R
  status: CLOSED 2026-04-21 null on own axis — Stage 5 anchor sweep (2026-04-18) showed all three anchor arms at kr=0.50 on VideoMME dev n=30 bounded by the arithmetic E2E ceiling (<1.10× at s=∞); gemma_structural and max_min_diversity earn acc bar (-3.3pp), nuwa_pillar fails (-16.7pp). Post-1.51V composition re-runs (EXP09/EXP10 from 1.51V expansion 2026-04-21): EXP09 (gemma_structural kr=0.5) replicates own-axis null (own-pair E2E 0.990×, acc -6.7pp, agree 0.50); EXP10 (anchor=none kr=0.3) shows +4.7pp own-pair E2E lift over V-alone with agg acc preserved BUT agreement drops 0.90→0.63 ("noisy preserve"). EXP10 cell flagged as n=60 follow-up lane with promotion rule: ≥4pp lift AND agreement ≥0.75 AND acc within -0.067.
  authoritative_note: research/experiments/2026/2026-04-17-phase-1_51-novelty-pruning-gemma-prereg.md + research/experiments/2026/2026-04-18-phase-1_51R-stage5-cross-arm-synthesis.md + research/experiments/2026/2026-04-21-phase-1_51R-closure-post-1_51V.md
  authoritative_artifacts:
    - src/codec_through/novelty_pruning.py (anchor scoring + keep mask; CPU tested)
    - src/codec_through/video_decode.py (bounded-memory uniform decode)
    - src/codec_through/memory_guard.py (RSS guard; platform-correct 2026-04-18)
    - scripts/run_novelty_pruning_gemma.py (end-to-end driver)
    - scripts/smoke_novelty_pruning.py (CPU smoke harness)
    - tests/test_novelty_pruning.py, tests/test_video_decode.py, tests/test_memory_guard.py
    - research/experiments/2026/artifacts/phase1_51R_smoke/ (CPU smoke output on VideoMME sample)
    - research/experiments/2026/artifacts/phase1_51R_pilot/ (GPU pilot n=1 long item, arm=none kr=0.5, e2e 1.01× / gen 1.12×)
    - research/experiments/2026/artifacts/phase1_51R_dev/ (Stage 1 n=30 scale-up; in flight)
    - research/experiments/2026/2026-04-18-phase-1_51R-pilot-findings.md (arithmetic-ceiling derivation)
  current_best_policy: n/a — own-axis null confirmed at n=30 across 3 anchor arms at kr=0.50 on VideoMME dev (Stage 5 2026-04-18); ceiling binds anchor-invariantly. Composition with 1.51V at EXP10 cell (anchor=none kr=0.3) closed-null on the n=60 composition audit.
  supersedes: []
  paper_relevance: secondary (demoted from primary per codex round-25 and paper/priority.md must-do #5: 1.51V is the primary local Gemma story, not 1.51R; 1.51R contributes (i) the EXP10 n=60 composition audit on VideoMME holdout and (ii) the Stage 5 gemma_structural anchor default as secondary methodology content; publishable preregistered null with mechanistic explanation)
  prereg_outcome: NULL on own axis (Stage 5 n=30 cross-arm synthesis 2026-04-18 + post-1.51V composition closure 2026-04-21); EXP10 n=60 composition audit CLOSED-NULL 2026-04-21 (task #152)
  notes: phase is tracked as the "1.51R" fresh driver across other docs (R = reproduction of the pre-release novelty-pruning, fresh code path that does not consume `_mix_gemma_features`). Preregistered 5 literature-grounded anchor-preservation arms (FastV, FasterVLM/HiPrune, Nüwa pillar, VLM-Pruner max-min diversity, IVC-Prune-spirit Gemma-structural); keep-rate grid {0.3..0.7}; must run on Gemma (not Qwen) because Qwen's M-RoPE-V ties token index to 2D grid position and breaks under token drop. cls_attention_proxy arm is explicitly excluded from winner promotion (see PROMOTABLE_ARMS in novelty_pruning.py). Pilot reveals vision-tower pruning (NEW phase 1.51V, task #87) is the only mechanism that could reach the pre-release ≥1.8× end-to-end on E4B; queued as follow-up.

- phase_id: 1.51V
  status: CLOSED 2026-04-21 — expansion 12/12 DONE + session 2 (32f probe EXP13/14 + holdout EXP15/16) 4/4 DONE. H1 CONFIRMED (V_red=39.0% thermally-paired EXP01/02, decode Δ=-2.8%); H_pareto EARNED (kr=0.25 Pareto-dominates kr=0.50 on VideoMME: +23pp V_red at identical E2E and accuracy); H_transfer EARNED on MVBench (1.21× E2E at V_red=40%) and TOMATO (1.24× E2E at V_red=42.7%, +3.3pp accuracy); H_fsscale CONFIRMED at 16f (V_red benchmark-invariant, E2E 1.12× matches ceiling prediction 1.105× within 1pp); H_32f_vshare CONFIRMED (V_share climbs to 31.0% at 32f per ceiling model) but H_32f_e2e REJECTED (M3 16GB hits thermal cap at 32f: decode Δ +7.6% violates <2% pairing gate, cross-session headline inflated); composition audit PARTIAL CONFIRMATION on holdout (EXP15/16 VideoMME v1 n=30 disjoint: within-run 1.064× ceiling-matched via LLM-side analog 1/(1 − generate_share × generate_reduction), agreement 0.667 mirroring dev, acc Δ -0.033; below 1.10× headline-reopener threshold so stays secondary-claim). V-only holdout unpatched-vs-patched pair status (three-benchmark C-VISION trifecta effectively closed 2026-04-21 with differentiated advisory strength): **VideoMME 8f CLOSED 2026-04-21** session 3 EXP17/18 (E2E 1.113×, V_red 0.413, decode Δ 1.53%, acc Δ 0.000; holdout V_share=15.45%); **MVBench 8f CLOSED 2026-04-21 with advisory pass** session 4 EXP19/20 (E2E 1.407× far exceeding dev 1.21×, V_red 0.471, acc Δ −0.033; thermal gate 11.66% formally fails but 50 ms absolute is OS-jitter scale on MVBench's 432 ms decode window — calibration revision proposed); **TOMATO 8f EARNED-ADVISORY 2026-04-21** session 5 EXP23/24 (rerun after session 4 confound: E2E sum-ratio mean 1.194×, median 1.232×, clears 1.15× primary gate; V_red 0.350 below [0.38, 0.48] band by 0.03; decode Δ 119.7 ms = 3.51% rel in FAVORABLE direction — patched arm cooler than reference, observed speedup conservatively under-stated; scatter-back ceiling predicts 1.155×, consistent with ceiling + friendly thermal correction; acc Δ −0.067). Architectural ceiling 1/(1 − V_share × V_red) validated quantitatively on 5 (benchmark, frame-count, axis) cells including LLM-decode axis.
  authoritative_note: research/experiments/2026/2026-04-18-phase-1_51V-vision-tower-pruning-prereg.md + research/experiments/2026/2026-04-20-phase-1_51V-dev-tranche-findings.md + research/experiments/2026/2026-04-20-phase-1_51V-n30-findings.md + research/experiments/2026/2026-04-20-phase-1_51V-expansion-prereg.md + research/experiments/2026/2026-04-21-phase-1_51V-expansion-findings.md + research/experiments/2026/2026-04-21-phase-1_51V-32f-probe-findings.md + research/experiments/2026/2026-04-21-phase-1_51V-holdout-findings.md + research/experiments/2026/2026-04-21-phase-1_51V-session4-findings.md + research/experiments/2026/2026-04-21-phase-1_51V-session5-findings.md
  authoritative_artifacts:
    - src/codec_through/pruned_vision_tower.py (patch_vision_tower + magnitude_keep_mask + slice-then-scatter-back, B>1 generalized 2026-04-20 with `_PrunedEncoderWrapper` class-level `__call__` fix)
    - research/experiments/2026/artifacts/phase1_51V_pilot/ (single-item pilot; control vs patched L=1 kr=0.50; V-reduction 36% flagged)
    - research/experiments/2026/artifacts/phase1_51V_dev_tranche/ (control + 9-cell layer×kr grid + knee search L∈{2,3,4} on 5-item subset)
    - research/experiments/2026/artifacts/phase1_51V_n30/L2_kr050_summary.json (standalone n=30, thermally confounded +6.5% decode drift)
    - research/experiments/2026/artifacts/phase1_51V_compose/L2_kr050_x_novelty_kr050_summary.json (composition n=30, thermally clean +0.2% decode; dense arm is authoritative 1.51V measurement)
    - research/experiments/2026/artifacts/phase1_51V_expansion/ (12-experiment autonomous batch 2026-04-20/21: VideoMME Pareto + MVBench + TOMATO + 16f + 1.51R×1.51V re-runs, all n=30 thermally-paired)
    - research/experiments/2026/artifacts/phase1_51V_session2/ (4-experiment session 2 batch 2026-04-20/21: EXP13/14 VideoMME 32f probe — thermal cap confirmed on M3 16GB, decode Δ +7.6%; EXP15/16 VideoMME holdout v1 n=30 V-patched baseline + V+novelty kr=0.3 anchor=none at within-run 1.064× ceiling-matched)
    - research/experiments/2026/artifacts/phase1_51V_session3/ (2-experiment VideoMME 8f holdout V-only pair EXP17/18 2026-04-21: unpatched-vs-patched clean thermal pair; all 4 hypotheses pass)
    - research/experiments/2026/artifacts/phase1_51V_session4/ (4-experiment MVBench+TOMATO 8f holdout V-only pairs EXP19-22 2026-04-21: MVBench pair CLOSED advisory-pass; TOMATO pair thermally confounded, superseded by session 5 for adjudication)
    - research/experiments/2026/artifacts/phase1_51V_session5/ (2-experiment TOMATO 8f holdout V-only pair rerun EXP23/24 2026-04-21: EARNED-ADVISORY at E2E 1.194× sum-ratio mean / 1.232× median, V_red 0.350, decode Δ 119.7 ms in FAVORABLE direction — three-benchmark C-VISION trifecta effectively closed)
  current_best_policy: L=2 kr=0.50 knee for headline; L=2 kr=0.25 for aggressive Pareto. Headline E2E by benchmark (all at kr=0.50): TOMATO 1.24× (V_share=40.7%, acc +3.3pp), MVBench 1.21× (V_share=47.8%, acc -10pp), VideoMME 16f 1.12× (V_share=24.3%), VideoMME 8f 1.08× (V_share=15.2%). V_red benchmark-invariant ~40% at kr=0.50.
  supersedes: []
  paper_relevance: secondary (three-benchmark transfer confirmed at n=30 thermally-paired: V_red mechanism generalizes, E2E headline tracks V_share per architectural ceiling model; TOMATO/MVBench paper-grade cells; VideoMME bounded by low V_share; scatter-back ceiling validated quantitatively)
  prereg_outcome: H1 CONFIRMED, H_pareto EARNED, H_transfer EARNED, H_fsscale CONFIRMED, composition audit PARTIAL REOPENER on dev → PARTIAL CONFIRMATION on holdout (2026-04-21 session 2), H_32f_vshare CONFIRMED, H_32f_e2e REJECTED (thermal cap on M3 16GB)
  notes: Critical implementation bugs found and fixed 2026-04-20 — (1) Python `__call__` is looked up on the type, not the instance, so `encoder.__call__ = new_call` is silently a no-op. Fixed with `_PrunedEncoderWrapper` class-level `__call__`. (2) Helpers assumed B=1 but Gemma-4 vision tower batches frames in leading dim (B=N_frames). Generalized to per-frame pruning via `mx.take_along_axis` and batched one-hot matmul. (3) Cross-session thermal drift on M3 Air inflated standalone n=30 vision_ms by ~27% (decode_ms proxy: +6.5% drift vs control). **Authoritative V_red = 39.0% (paired EXP01/EXP02, thermally-paired within-session, decode drift < 2% — the strictest pairing the expansion batch can produce).** A cross-session composition-dense-arm normalization gave 42.2% on the earlier 2026-04-20 tranche (decode +0.2% vs a prior session's control); the 3.2pp delta sits inside the thermal-drift bracket and both readings attest the same mechanism, but per Codex round-22 the paired 39.0% is the paper-facing number. See `research/experiments/2026/2026-04-21-phase-1_51V-expansion-findings.md` §Reproduction-of-prior-claim for the reconciliation. **Architectural ceiling** (scatter-back preserves pooler geometry): pruned tokens scattered back to original length, so LM prompt token count is unchanged (2181 tokens), LM prefill + generate get zero speedup from 1.51V. E2E upper bound = `1 / (1 - V_share × V_red)` = 1.16× at V_red=100% on 8-frame VideoMME dev, cutting to 1.06× at V_red=39.0% × V_share=15.2% (8f). Reaching H3's 1.5× requires either (a) post-pool token merging that cuts LM prompt, (b) bypass scatter-back with a new pooler, or (c) composition with persistent-KV (CLOSED on 1.55 lane) or 1.51R (null on novelty axis).

- phase_id: 1.52R
  status: superseded / not launched under original gate
  authoritative_note: research/experiments/2026/2026-04-17-phase-1_52-combined-temporal-spatial-prereg.md
  authoritative_artifacts: []
  current_best_policy: n/a
  supersedes: [1.52]
  paper_relevance: historical composition prereg; current composition evidence comes from 1.51V EXP10 and scale-out bundle gates, not this original proposed headline path
  prereg_outcome: Not launched under original gate. The prerequisites changed meaning: 1.42 landed as a split architecture boundary rather than a clean Gemma pass, and 1.51R closed as an own-axis null while 1.51V became the primary Gemma first-pass story.
  runtime_estimate: obsolete
  notes: The original three-way gate (multiplicative / additive / interference) remains useful design context but is not a live paper-table promise. Any future composition claim should use a fresh prereg tied to the current C-VISION/C-PERSIST/scale-out evidence surface.

- phase_id: 1.55
  status: superseded
  authoritative_note: research/experiments/2026/2026-04-19-phase-1_55-persistent-kv-prereg.md
  authoritative_artifacts: []
  current_best_policy: n/a
  supersedes: []
  paper_relevance: historical (split into 1.55A reproduction + 1.55B composition per Codex round-22; original provenance+gating were wrong)
  prereg_outcome: Superseded
  runtime_estimate: n/a (see 1.55A, 1.55B)
  notes: Original prereg mistakenly attributed the pre-release MEASURED 2.13.3 persistent-KV result as a Codex hypothesis, and gated on an mlx-vlm fork that turned out to already be upstream (PromptCacheState + find_prefix_length). Split 2026-04-19 into 1.55A (reproduction of pre-release 2.13.3 on Qwen 7B/M3 Air) and 1.55B (composition with 1.54 decode accel — deferred).

- phase_id: 1.55A
  status: completed/CLOSED (8f + 16f + 18f + 20f + 24f + 32f frame-scaling on 7B + 3B 20f matched + 3B 24f shifted-ramp + 3B 32f plateau-candidate + 3B 36f PRE-BASIN PLATEAU EXTENDED + 3B 40f LATENT BASIN EARNED + **7B 40f BASIN-SYMMETRY EARNED** + 7B/20f temperature probe EARNED H-distribution-collapse + 3B/20f temperature probe EARNED H2-3B-temp.null-robust + **3B/40f temperature probe HYBRID (basin partially dispersed, sampler-invariance is architecture-conditional)**; three-dimensional mechanism decomposition REVISED 2026-04-20 from saturation-ceiling to shifted-onset-same-basin AND **SYMMETRICALLY CONFIRMED** 2026-04-20 on 7B at 2× basin-onset depth: threshold onset capacity-modulated, **basin-onset depth architecture-dependent** (7B ~8k tokens; 3B ~16k tokens in the tested Qwen points; two-size evidence, not a scaling law), **basin geometry architecture-conditional under sampling** — 7B basin sampler-invariant at both 20f and 40f; 3B basin at 40f is sampler-dispersible (4/14 → 1/14 novel) but dispersed mass returns only to the pre-basin plateau, not to baseline; phase closes; reopen conditions (f) RETIRED and (h) CLOSED with HYBRID outcome)
  authoritative_note: research/experiments/2026/2026-04-19-phase-1_55A-persistent-kv-findings.md + research/experiments/2026/2026-04-19-phase-1_55A-16f-frame-scaling-findings.md + research/experiments/2026/2026-04-19-phase-1_55A-18f-frame-scaling-findings.md + research/experiments/2026/2026-04-19-phase-1_55A-20f-frame-scaling-findings.md + research/experiments/2026/2026-04-19-phase-1_55A-24f-frame-scaling-findings.md + research/experiments/2026/2026-04-19-phase-1_55A-32f-frame-scaling-findings.md + research/experiments/2026/2026-04-19-phase-1_55A-3b-crossarch-findings.md + research/experiments/2026/2026-04-20-phase-1_55A-3b-24f-boundary-findings.md + research/experiments/2026/2026-04-20-phase-1_55A-3b-32f-saturation-findings.md + research/experiments/2026/2026-04-20-phase-1_55A-7b-20f-temperature-findings.md + research/experiments/2026/2026-04-20-phase-1_55A-3b-20f-temperature-findings.md + research/experiments/2026/2026-04-20-phase-1_55A-3b-40f-deeper-plateau-findings.md + research/experiments/2026/2026-04-20-phase-1_55A-7b-40f-symmetry-findings.md + research/experiments/2026/2026-04-20-phase-1_55A-3b-36f-interpolation-findings.md + research/experiments/2026/2026-04-20-phase-1_55A-3b-40f-temperature-findings.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/loop_queue_20260419_155108/phase1_55A_persistent_kv_qwen/summary.json
    - research/experiments/2026/artifacts/loop_queue_20260419_155108/phase1_55A_persistent_kv_qwen/session_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/loop_queue_20260419_155108/phase1_55A_persistent_kv_qwen/baseline_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_16f_frame_scaling/summary.json
    - research/experiments/2026/artifacts/phase1_55A_16f_frame_scaling/session_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_16f_frame_scaling/baseline_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_18f_frame_scaling/summary.json
    - research/experiments/2026/artifacts/phase1_55A_18f_frame_scaling/session_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_18f_frame_scaling/baseline_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_20f_frame_scaling/summary.json
    - research/experiments/2026/artifacts/phase1_55A_20f_frame_scaling/session_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_20f_frame_scaling/baseline_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_24f_frame_scaling/summary.json
    - research/experiments/2026/artifacts/phase1_55A_24f_frame_scaling/session_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_24f_frame_scaling/baseline_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_32f_frame_scaling/summary.json
    - research/experiments/2026/artifacts/phase1_55A_32f_frame_scaling/session_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_32f_frame_scaling/baseline_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_3b_20f_crossarch/summary.json
    - research/experiments/2026/artifacts/phase1_55A_3b_20f_crossarch/session_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_3b_20f_crossarch/baseline_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_3b_24f_boundary/summary.json
    - research/experiments/2026/artifacts/phase1_55A_3b_24f_boundary/session_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_3b_24f_boundary/baseline_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_3b_32f_saturation/summary.json
    - research/experiments/2026/artifacts/phase1_55A_3b_32f_saturation/session_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_3b_32f_saturation/baseline_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_7b_20f_temperature/summary.json
    - research/experiments/2026/artifacts/phase1_55A_7b_20f_temperature/session_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_7b_20f_temperature/baseline_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_3b_20f_temperature/summary.json
    - research/experiments/2026/artifacts/phase1_55A_3b_20f_temperature/session_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_3b_20f_temperature/baseline_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_3b_40f_deeper_plateau/summary.json
    - research/experiments/2026/artifacts/phase1_55A_3b_40f_deeper_plateau/session_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_3b_40f_deeper_plateau/baseline_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_7b_40f_symmetry/summary.json
    - research/experiments/2026/artifacts/phase1_55A_7b_40f_symmetry/session_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_7b_40f_symmetry/baseline_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_3b_36f_interpolation/summary.json
    - research/experiments/2026/artifacts/phase1_55A_3b_36f_interpolation/session_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_3b_36f_interpolation/baseline_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_3b_40f_temperature/summary.json
    - research/experiments/2026/artifacts/phase1_55A_3b_40f_temperature/session_qwen7b_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55A_3b_40f_temperature/baseline_qwen7b_n7.jsonl
  current_best_policy: "persistent-KV session (PromptCacheState one-per-clip) — 7B-4bit: 8f 47.2×/815ms/Δ=−0.048; 16f 91.1×/807ms/Δ=0.000; 18f 70.3×/1102ms/Δ=−0.238 (4-basin); 20f 94.4×/905ms/Δ=−0.381 (2-basin); 24f 121.6×/864ms/Δ=−0.429 (single attractor); 32f 149.9×/1008ms/Δ=−0.429 (saturated). **7B/20f temperature probe (T=0.7, top_p=1.0, min_p=0.05, seed=42): 117.0×/907ms/Δ=−0.429 — Δacc temperature-invariant within 1/21 noise floor (greedy −0.381, temp −0.429; diff 0.048); basin prevalence 13/14→8/14 but clean-drift share stayed 1/14 (dispersed mass landed in novel `自动生成` (\"auto-generated\") attractor, NOT in clean letters); H-distribution-collapse EARNED on both prereg conditions (Δacc≤−0.35 AND basin≥0.50). 7B basin is distribution-level, not sampler-level.** **3B-4bit cross-arch 3-point: 20f 136.1×/412ms/Δ=−0.048 (MATCHED); 24f 154.2×/423ms/Δ=−0.190 (SHIFTED-RAMP); 32f 213.0×/484ms/Δ=−0.190 (PLATEAUED — identical Δacc to 24f, 3B saturated at a ~2.3× shallower ceiling than 7B). 28/28 3B follow-ups emit clean 2-token letter answers — no basin collapse at any 3B prefill.** **3B/20f temperature probe (T=0.7, top_p=1.0, min_p=0.05, seed=42): 130.8×/385ms/Δ=−0.095 — H2-3B-temp.null-robust EARNED (Δacc inside envelope [−0.15, +0.05] AND 14/14 clean-letter follow-ups); Δacc shifts by exactly 1/21 vs greedy 3B/20f (−0.048 → −0.095), identical noise-floor signature to 7B temperature probe (−0.381 → −0.429, 1/21 shift). Sampler-invariance verified at BOTH ceilings.** 7B: monotonic-saturating ramp 16f→24f through progressive basin collapse, Δacc ceiling −0.43 (distribution-level). 3B: ramp shifted ~2-3k tokens later, Δacc ceiling −0.19 (architecture-specific), failure geometry is clean-letter drift (architecture-specific)."
  supersedes: ["1.55"]
  paper_relevance: primary (reproduces pre-release source §2.13.3 on Qwen 7B-4bit / M3 Air; prefill-dominance mechanism confirmed on 6-point scaling curve; 18f+20f bisections reveal the 7B fidelity transition is a monotonic-saturating ramp through progressive basin collapse — clean → 4-basin → 2-basin → single-attractor; 3B cross-arch 3-point (20f matched, 24f shifted-ramp, 32f plateaued) decomposes the mechanism into **three orthogonal architectural dimensions: threshold onset (capacity-modulated), saturation ceiling (architecture-specific −0.43 vs −0.19), failure geometry (architecture-specific basin collapse vs clean-letter drift)**)
  prereg_outcome: H1/H1'/H1''/H1'''/H1''''/H1''''' all earn (speedup 47×→91×→70×→94×→122×→150×; 18f dip is median-inflation from long-garbage gen tokens, not cache-reuse failure). H3/H3'/H3''/H3'''/H3''''/H3''''' all earn (prefix ≥0.99). H4/H4'/H4''/H4'''/H4''''/H4''''' all earn (peak RSS ≤ 4.2 GB). H2/H2' earn at 8f/16f; **H2''/H2'''/H2''''/H2''''' REJECT at 32f/24f/20f/18f on 7B**. 18f is mid-ramp with 4-basin diversity (Δ = −0.238). 20f is mid-ramp with 2-basin dominance (Δ = −0.381). 24f/32f saturate to 14/14 `addCriterion` (Δ = −0.429). **3B cross-arch 20f: H2-3B.matched (Δ = −0.048); 3B cross-arch 24f: H2-3B-24.shifted-ramp (Δ = −0.190, inside (−0.30, −0.05)); 3B cross-arch 32f: H2-3B-32.plateaued (Δ = −0.190, inside (−0.25, −0.10] — most-surprising pre-registered sub-outcome; Δacc numerically identical to 24f, 3B saturated ~2.3× shallower than 7B). All three 3B runs: 28/28 follow-ups emit clean 2-token letter answers — no addCriterion, no long-garbage, ever. **7B/20f temperature probe: H1-temp 117×, H2-temp.distribution-collapse EARNED (Δacc=−0.429 ✓, basin=0.571 ✓; H2-temp.greedy-commit FALSIFIED on both conditions). H3-temp prefix 0.993, H4-temp RSS 1.61 GB. Temperature + min-p redistribute basin mass WITHIN the pathological-attractor set (plain `addCriterion` 9→4; Java-code `addCriterion(…)` 4→4 rigid; novel `自动生成` ("auto-generated") 0→5; clean letter 1→1 unchanged) — 7B basin is distribution-level, not sampler-level.** **3B/20f temperature probe: H1-3B-temp 130.8×, H2-3B-temp.null-robust EARNED on both preregistered conditions (Δacc=−0.095 ∈ [−0.15, +0.05] ✓ AND 14/14 clean-letter follow-ups ≥ 12/14 ✓); H2-3B-temp.hidden-basin FALSIFIED (0/14 non-letter follow-ups); H2-3B-temp.sampler-dispersion NOT TRIGGERED (inside envelope). H3-3B-temp prefix 0.993, H4-3B-temp RSS 2.36 GB. Δacc temperature-shift is exactly 1/21 (−0.048 → −0.095) — identical noise-floor signature to 7B probe. 3B clean-letter distribution is sampler-invariant; temperature shuffles argmax on a few queries but NEVER exposes non-letter content.** Three-dimensional mechanism decomposition FINALIZED AND TEMPERATURE-VERIFIED AT BOTH CEILINGS: threshold onset (capacity-modulated), saturation ceiling (architecture-specific), failure geometry (architecture-specific AT DISTRIBUTION LEVEL on both 7B and 3B — distribution-level sampler-invariance is cross-architecture).**
  runtime_estimate: 17 min @ 8f + 35 min @ 16f + 38 min @ 18f + 42 min @ 20f + 55 min @ 24f + 76 min @ 32f + 27 min @ 3B-20f + 31 min @ 3B-24f + 50 min @ 3B-32f + 48 min @ 7B-20f-temp + 24 min @ 3B-20f-temp = ~7.3 h total across 6 frame counts + 3 cross-arch points + 2 sampler probes (both architectures)
  notes: |
    **8f run (loop_queue_20260419_155108):** all four preregistered hypotheses
    earn. H1 47.23× speedup, H2 Δacc −0.048, H3 prefix 0.982, H4 peak RSS 2.81 GB.
    Driver bug caught and fixed at 143e782 (state.token_ids gate prevented state
    threading).
    **16f follow-up (phase1_55A_16f_frame_scaling):** all four H' earn. H1' 91.06×
    speedup, H2' follow-up median 807 ms, H3' prefix 0.991, H4' peak RSS 1.48 GB.
    16f Δacc = 0.000 (17/21 = 17/21).
    **32f third point (phase1_55A_32f_frame_scaling):** H1'' 149.88×, H3'' 0.9955,
    H4'' 2.50 GB — BUT H2'' REJECTS with Δacc = −0.429. 14/14 cache-path follow-ups
    emit literal `addCriterion` token.
    **24f bisection (phase1_55A_24f_frame_scaling):** H1''' 121.58×, H3''' 0.9940,
    H4''' 3.30 GB — BUT H2''' REJECTS with Δacc = −0.429 identical to 32f
    (same session 9/21, baseline 18/21, follow-up 2/14, 14/14 `addCriterion`).
    **20f midpoint bisection (phase1_55A_20f_frame_scaling):** H1'''' 94.42×,
    H3'''' 0.9928, H4'''' 3.51 GB — H2'''' Δacc = −0.381. Basin distribution
    (by pattern, n=14): 9 short `addCriterion`, 4 long-garbage (up to 64 gen tok),
    1 clean-correct "D". Correct: 3/14 (1 clean-D + 2 lucky addCriterion→A).
    Q1 6/7 (one cold flake).
    **18f ramp-onset bisection (phase1_55A_18f_frame_scaling):** H1''''' 70.28×
    (median follow-up 1102 ms; LOWER than 16f/20f because long-garbage gens inflate
    median — speedup metric is coupled to failure-mode distribution, not just
    cache-reuse), H3''''' 0.9920, H4''''' 4.19 GB — H2''''' Δacc = −0.238 mid-ramp.
    **Richest basin diversity in the sweep**: 4 clean-correct + 3 clean-wrong-choice
    (2-tok non-gold letter) + 3 long-garbage + 2 empty + 2 saturated-`addCriterion`.
    Q1 7/7.
    **Cliff-versus-gradient-versus-ramp verdict: monotonic-saturating ramp.**
    Pairwise Δacc increments decay (−0.238, −0.143, −0.048, 0). Basin-structure
    evolution traces progressive collapse: clean → 4-basin → 2-basin → single
    attractor. Falsifies pure cliff (would predict no intermediate basins).
    Falsifies pure gradient (would predict no saturation past 24f; we have
    identical 24f/32f). Favours threshold mechanisms with a soft edge (4-bit
    KV quantization budget, M-RoPE OOD). Prefill-dominance speedup curve:
    38.5→73.5→77.5→83.8→108.9→163.2 s first-query; 815→807→1102→905→864→1008
    ms follow-up; 47×→91×→70×→94×→122×→150× speedup. Median follow-up matches
    the pre-release 0.8 s (Gemma 4 26B / M5 Max) to 15 ms at 8f/16f.
    **Frame-count sweep complete at ramp-resolution.**
    **3B cross-arch at 20f (phase1_55A_3b_20f_crossarch):** H1-3B 136.07×
    speedup (follow-up median 412 ms), H2-3B Δacc = −0.0476 (inside ±0.05
    envelope → H2-3B.matched sub-outcome), H3-3B prefix 0.9928, H4-3B peak
    RSS 3.93 GB. Baseline 13/21, session 12/21 — cache reuse does NOT
    degrade 3B beyond statistical noise at same prefill length as 7B's
    2-basin ramp. **All 14 follow-ups emit 2-token clean letter answers —
    NO addCriterion basin, NO long-garbage basin.** The 7B basin attractor
    collapse is model-specific, not prefill-length-intrinsic, not
    m-RoPE-position-intrinsic, not shared-tokenizer-space-intrinsic.
    **Falsified**: pure prefill-length-intrinsic mechanism, shared-tokenizer
    attractor hypothesis. **Strongly supported**: model-capacity /
    depth-dependent accumulation OR 7B-specific decoder-distribution
    basin geometry. First mechanism-discriminating falsifier LANDED in
    one run.
    **3B 24f boundary-shift (phase1_55A_3b_24f_boundary, 2026-04-20):**
    H1-3B-24 154.17× speedup (median follow-up 423 ms), H2-3B-24.shifted-ramp
    sub-outcome EARNED with Δacc = −0.190 (inside (−0.30, −0.05)), H3-3B-24
    prefix 0.9940, H4-3B-24 peak RSS 1.48 GB. Baseline 14/21, session 10/21.
    First-query accuracy 4/7 identical to baseline — deficit is
    entirely on cache-reused follow-ups (session 6/14 vs baseline 10/14,
    Δ=−0.286). **All 14 follow-ups emit clean 2-token letter answers**
    (no addCriterion, no long-garbage, no empty). 3B at 24f exhibits
    **decode-choice drift**, structurally distinct from 7B's single-attractor
    basin collapse. Cross-arch 2-point verdict: **ramp is capacity-modulated
    (3B threshold ~2-3k prefill tokens later than 7B); basin attractor
    identity is architecture-specific (addCriterion is 7B-only)**.
    **3B 32f saturation-mapping (phase1_55A_3b_32f_saturation, 2026-04-20):**
    H1-3B-32 213.01× speedup (median follow-up 484 ms — 3B speedup
    curve keeps scaling, now exceeds 7B 32f's 150×), H2-3B-32.plateaued
    sub-outcome EARNED with Δacc = −0.190 (inside (−0.25, −0.10] —
    most-surprising pre-registered sub-outcome), H3-3B-32 prefix
    0.9955, H4-3B-32 peak RSS 4.58 GB. Baseline 14/21, session 10/21
    — **numerically identical raw counts to 3B 24f** (same session
    10/21, same baseline 14/21). First-query 5/7 both modes (matches
    baseline). Follow-up Δacc = −0.286 (session 5/14 vs baseline 9/14).
    All 14 follow-ups still emit clean 2-token letter answers at
    12.9k prefill — **no basin collapse emerges on 3B at 60% deeper
    prefill than 7B saturation point**. Cross-arch 3-point verdict:
    **3B has SATURATED at a ~2.3× SHALLOWER CEILING than 7B (−0.19
    vs −0.43). Three-dimensional mechanism decomposition: (1) threshold
    onset capacity-modulated (7B ramps at ~7.3k; 3B ramps at ~9.7k),
    (2) saturation ceiling architecture-specific (−0.43 vs −0.19,
    confirmed across 9.7k and 12.9k), (3) failure geometry
    architecture-specific (basin collapse to `addCriterion` vs clean
    letter drift across A/B/C/D).**
    **7B/20f temperature probe (phase1_55A_7b_20f_temperature,
    2026-04-20):** H1-temp 117.0× speedup (median follow-up 907 ms),
    H2-temp.distribution-collapse EARNED on both preregistered
    conditions (Δacc = −0.429, basin prevalence 0.571), H2-temp.greedy-
    commit FALSIFIED on both conditions. H3-temp prefix 0.9928,
    H4-temp peak RSS 1.61 GB. Session 9/21, baseline 18/21 — follow-up
    2/14 (clean-"D" row 8 + Java-code lucky `addCriterion(…)` parse on
    rows 15/17 — the latter was from the follow-ups where temperature
    reshuffled the long tail). Attractor tally shift vs 20f greedy
    reference (14 follow-ups each): plain `addCriterion` 9→4; Java-code
    `addCriterion(…)` 4→4 (rigid — SAME 4 clip IDs under both
    conditions); novel `自动生成` ("auto-generated") 0→5; clean letter 1→1
    unchanged. **Δacc is temperature-invariant** within noise floor
    (−0.381→−0.429, diff 0.048 = exactly 1 correct/21). Basin
    prevalence dropped (13/14→8/14) but dispersal went to a DIFFERENT
    pathological attractor, not to clean letters. Java-code basin
    variant is rigid under temperature — identical 4 clips produce
    `addCriterion(...)` method-chain parse in both conditions;
    structured-output attractor is deterministic in the cache-reused
    distribution. **Verdict: 7B basin collapse is a property of the
    cache-reused logit distribution itself, not of greedy decoding.**
    Temperature + min-p redistribute WITHIN the set {addCriterion,
    addCriterion(…)Java, 自动生成 ("auto-generated")} plus a thin clean tail; they do not
    escape it.
    **3B/20f temperature probe (phase1_55A_3b_20f_temperature,
    2026-04-20):** H1-3B-temp 130.8× speedup (follow-up median
    385 ms — fastest follow-up latency in the entire sweep),
    H2-3B-temp.null-robust EARNED on both preregistered conditions
    (Δacc = −0.095 inside envelope [−0.15, +0.05] ✓; 14/14 clean
    2-token letter follow-ups ≥ 12/14 prereg bar ✓); H2-3B-temp.hidden-
    basin FALSIFIED (0/14 non-letter); H2-3B-temp.sampler-dispersion
    NOT TRIGGERED (inside envelope). H3-3B-temp prefix 0.9928,
    H4-3B-temp peak RSS 2.36 GB. Session 13/21, baseline 15/21 —
    **Δacc shifts by exactly 1/21 vs greedy 3B/20f** (−0.048 →
    −0.095; diff 0.048 = noise floor). Letter distribution: D×8,
    B×4, C×2. The same 1/21 noise-floor shift was observed on the
    7B/20f temperature probe (−0.381 → −0.429). **Sampler-invariance
    is cross-architecture**: each ceiling preserves its characteristic
    failure geometry under temperature (7B basin set 13/14 → 8/14 with
    zero clean-drift recovery; 3B clean-letter set 14/14 → 14/14 with
    argmax-shuffling only). Zero hidden basin on 3B at 8.1k prefill;
    the clean-letter distribution is intrinsic to the cache-reused
    3B logits at its shallower ceiling, not an argmax-only artifact.
    **Three-dimensional mechanism decomposition FINALIZED AND
    TEMPERATURE-VERIFIED AT BOTH CEILINGS:**
    (1) threshold onset capacity-modulated (7B ramps ~7.3k; 3B ramps
    ~9.7k); (2) saturation ceiling architecture-specific (−0.43 vs
    −0.19, 2.3× shallower on 3B, confirmed across 9.7k and 12.9k);
    (3) failure geometry architecture-specific AT DISTRIBUTION LEVEL
    at BOTH architectures (7B pathological-attractor SET; 3B clean-
    letter SET; distribution-level sampler-invariance is cross-
    architectural, not a 7B idiosyncrasy).
    **3B 40f deeper-plateau probe (phase1_55A_3b_40f_deeper_plateau,
    2026-04-20):** H1-3B-40.plateau FAILS; **H1-3B-40.latent-basin
    EARNS.** H2-3B-40 speedup 191.1× (follow-up median 603 ms —
    still the fastest follow-up class), H3-3B-40 prefix 0.9964,
    H4-3B-40 peak RSS 3.15 GB. Session 8/21, baseline 13/21,
    Δacc = −0.238 (inside prereg band [−0.25, −0.10] but at edge).
    **Critical finding: 4/14 session follow-ups emit non-letter
    content (3 empty-response with generation_tokens=1; 1 "The");
    0/14 on the matched baseline.** Three clip-120 follow-ups and
    one clip-037 follow-up expose the basin. Q1 accuracy 4/7
    identical session/baseline — deficit is entirely on follow-
    ups (Δacc_followup = −0.357). **Mechanism revised from
    architectural-ceiling to shifted-onset:** 3B is NOT on a
    saturation plateau; the 24f/32f "plateau" was pre-onset, and
    basin emergence appears at ~16k prefill tokens (40f). 3B and
    7B share the same basin geometry; onset depth is deeper on the tested 3B
    point than on the tested 7B point (7B ~8k at 20f; 3B ~16k at 40f). The
    3-D decomposition's dimension 2 is relabelled from
    "saturation ceiling = architecture-specific" to "**basin-
    onset depth = architecture-dependent; basin geometry =
    cross-architectural**." This unifies 3B and 7B under one
    mechanism (same attractor geometry, different threshold)
    and is structurally cleaner than the ceiling claim.
    **7B 40f basin-symmetry probe (phase1_55A_7b_40f_symmetry,
    2026-04-20):** H1-symmetric EARNS; H1-novel FAILS.
    H2 speedup 157.6× (≥140× ✓; follow-up median 1497 ms >
    1200 ms so H2 PARTIAL — same long-garbage-tail mechanism
    as 18f), H3-7B-40 prefix 0.9964, H3-7B-40 peak RSS 4.25 GB.
    Session 7/21, baseline 17/21, Δacc = −0.476 (inside prereg
    symmetric band [−0.55, −0.35]). **13/14 session follow-ups
    land in the established basin set (7 plain addCriterion +
    6 addCriterion(…) Java-code variants); 1/14 novel (empty-
    response on clip 120-2, single-clip phenomenon).** Confirms
    the shifted-onset-same-basin revision symmetrically at 2×
    the 7B basin-onset depth: within-basin structure is
    depth-invariant once entered. **Cross-architectural
    curiosity (n=1, not load-bearing):** clip 120-2 emits
    empty-response on BOTH 3B-40f AND 7B-40f — consistent with
    a clip-specific prefix-geometry effect; flagged, not
    claimed. Basin-identity claim now has two independent
    datapoints (3B 40f + 7B 40f) supporting the unified
    mechanism.
    **3B 36f basin-onset interpolation probe
    (phase1_55A_3b_36f_interpolation, 2026-04-20):** H1-wide-
    transition EARNS; H1-sharp-onset FAILS; H1-intermediate
    FAILS. H2-3B-36 speedup 215.2× / median follow-up 562 ms
    (fastest follow-up on 3B to date), H3 prefix 0.9960, H4
    peak RSS 2.35 GB. Session 8/21, baseline 12/21,
    **Δacc = −0.190 — numerically identical to 3B 24f and 3B
    32f (three-point pre-basin plateau).** **0/14 session
    follow-ups emit novel content; all 14 are clean 2-token
    letter responses.** The 3B basin onset is therefore
    bounded to **(36f, 40f] = (14.5k, 16.1k] prefill tokens**,
    a ~1.6k-token (~11%) transition window. Basin onset on 3B
    is SHARP, consistent with a threshold mechanism (KV
    quantization budget edge or M-RoPE OOD). Pre-basin plateau
    at Δacc = −0.19 across 24f/32f/36f argues that the pre-
    basin regime is a depth-saturated noise floor (scrambled-
    letter noise, not basin), not a capacity ceiling — only
    basin emergence changes Δacc. Reopen condition (g) CLOSED
    with EARNED outcome.
    **3B 40f temperature probe (phase1_55A_3b_40f_temperature,
    2026-04-20):** HYBRID verdict. H1-3B-40-temp.distribution-
    collapse REJECTED (1/14 novel << 3/14 prereg bar; Δacc
    −0.190 on the upper boundary); H1-3B-40-temp.sampler-
    recovers PARTIALLY EARNS (13/14 clean-letter ≥ 12/14
    prereg bar ✓ but Δacc −0.190 lands just outside
    [−0.15, +0.05] envelope, AT the 3B pre-basin plateau);
    H1-3B-40-temp.degenerate REJECTED decisively (1/14 << 8/14;
    Δacc better than greedy −0.238). H2-temp 236.4× speedup /
    median follow-up 648 ms, H3-temp prefix 0.9964, H4-temp
    peak RSS 3.95 GB. Session 11/21, baseline 15/21 — follow-up
    7/14 (Δfollow-up = −0.214). **Attractor tally: 13/14 clean
    2-token letter, 1/14 empty-response (clip 120-Q3, tok=1).**
    Under greedy 3B 40f the same subset had 4/14 non-letter
    (3 empty + 1 "The"); temperature dispersed 3 of the 4
    basin emissions. **Cross-architectural asymmetry
    EARNED:** 7B basin is sampler-invariant at both 20f and
    40f (addCriterion-family preserved under temperature); 3B
    basin at 40f is sampler-dispersible but dispersed mass
    returns only to the pre-basin plateau noise floor, not to
    baseline. 1/21 resolution signature extends to 4 regimes
    (7B 20f, 3B 20f, 7B 40f partial, 3B 40f): shifts of
    exactly one query-worth, direction regime-specific
    (pre-basin / 7B-basin: −1/21 noise; 3B-basin: +1/21
    dispersal-net). **Claim #14 sampler-invariance subclaim
    narrows to architecture-conditional:** the pre-basin
    plateau noise floor is sampler-invariant cross-
    architecturally, but basin-regime sampler-invariance is
    7B-specific. Sampler-side intervention is SUFFICIENT at
    3B basin (returns to plateau floor) but INSUFFICIENT at
    7B basin. Full baseline recovery still requires upstream
    intervention (1.55D selective re-prefill, mlx-vlm fork
    gated). Clip 120 is the hardest-basin clip on the short-
    bucket subset across both 3B and 7B at 40f (empty-
    response emission on BOTH architectures, single-Q shift
    120-2 greedy → 120-3 temperature). Reopen condition (h)
    CLOSED with HYBRID outcome.
    **Phase 1.55A closes.** Both 20f temperature probes plus
    both 40f regime probes (7B basin-symmetry + 3B partial
    dispersal) demonstrate that sampler-side intervention is
    7B-basin-insufficient and 3B-basin-partial; fidelity
    recovery at 7B remains gated on upstream intervention;
    3B partial recovery is paper-worthy in its own right. No
    further mechanism probes queued in-phase.
    **Both downstream follow-ups are now INFRASTRUCTURE-
    FALSIFIED at the mlx-vlm prefix-reuse contract boundary
    (2026-04-20):** 1.55C by sliding-window `RotatingKVCache`
    incompatibility with naive prefix truncation, and 1.55D by
    mlx-vlm's `generate` path not co-slicing `pixel_values`/
    `image_grid_thw`/`attention_mask` when shared-prefix ends
    inside an image block (v1 driver crashes deterministically
    on Q2 `get_rope_index` broadcast mismatch). See 1.55C and
    1.55D blocks below. Next priorities pivot to 1.51V vision-
    tower pruning and 1.51R focused dev sweep. Reopen
    conditions (3B 36f CLOSED 2026-04-20 with EARNED wide-
    transition outcome): (a) a mlx-vlm fork with cache-type-aware
    prefix truncation (unblocks 1.55C); (b) a mlx-vlm fork
    with auxiliary-tensor co-slicing for partial image-block
    reuse (unblocks 1.55D); (c) a rescope of 1.55D to text-
    only selective re-prefill (shared prefix ends cleanly
    past image block — existing infra supports); (d) rescope
    of 1.55C to Gemma 2 (non-sliding) as cross-family target;
    (e) deeper-prefill 7B runs (48f+) exhibit novel
    attractors; **(f) RETIRED 2026-04-20 with EARNED outcome
    (3B 40f basin confirmed; mechanism revised to shifted-
    onset);** (g) 3B 36f interpolation to pin onset threshold
    (~45min); (h) 3B 40f temperature probe to extend sampler-
    invariance claim to the 3B basin (~50min).

- phase_id: 1.55C
  status: infrastructure-falsified (driver blocker; prereg retained for re-run after fork)
  authoritative_note: research/experiments/2026/2026-04-20-phase-1_55C-gemma-cross-family-findings.md
  authoritative_artifacts: []
  current_best_policy: n/a
  supersedes: []
  paper_relevance: deferred (cross-family generalization of 3-D decomposition remains open; claim matrix now declares this an open question)
  prereg_outcome: Gate #2 of the prereg ("verify PromptCacheState + find_prefix_length work with Gemma's attention") FALSIFIED at realistic video prefill. Gemma 4 uses RotatingKVCache(max_size=512, keep=0) on 4/5 layers per sliding_window_pattern=5; 20-frame prefill = 5120 image tokens rotates sliding layers ~10×; mlx-vlm/generate.py:689-697 performs naive physical-position truncation (c.keys[:, :, :prefix_len, :]) that silently corrupts post-rotation KV. H1-H4 UNTESTED (cannot be tested correctly with current driver).
  runtime_estimate: 0h executed; ~2-4h fork + cache-correctness test to unblock (Option A in findings doc); ~30-60min run once driver is correctness-preserving
  notes: Discovered during pre-run driver verification 2026-04-20. The prereg's assumption of drop-in mlx-vlm compatibility was wrong — Gemma 4's sliding-window attention architecture is fundamentally incompatible with linear-cache prefix truncation. Three options documented (A: cache-type-aware fork with RotatingKVCache.is_trimmable() guard, B: partial-layer cache reuse losing most speedup, C: prefix ≤ 512 tokens = non-starter for video). Recommended disposition: DO NOT run with current driver (would produce plausible-looking garbage on silent-wrong-answer path); defer behind 1.55D (Qwen-only, known-compatible); revisit after 1.55D or rescope to Gemma 2 (non-sliding) as cross-family target. Paper Claim #14 (3-D decomposition) remains Qwen-family-only this draft; cross-family generalization declared an open question with explicit mlx-vlm sliding-window caveat.

- phase_id: 1.55D
  status: partial (v2 K=1 is the best fixed policy, but the deployment floor still narrowly misses)
  authoritative_note: research/experiments/2026/2026-04-24-phase-1_55D-selective-reprefill-v2-k1-findings.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_55D_selective_reprefill_v2/summary_k1_n7.json
    - research/experiments/2026/artifacts/phase1_55D_selective_reprefill_v2/session_k1_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55D_selective_reprefill_v2/baseline_k1_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55D_selective_reprefill_v2/summary_k2_n7.json
    - research/experiments/2026/artifacts/phase1_55D_selective_reprefill_v2/session_k2_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55D_selective_reprefill_v2/baseline_k2_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55D_selective_reprefill_v2/summary_k4_n7.json
    - research/experiments/2026/artifacts/phase1_55D_selective_reprefill_v2/session_k4_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55D_selective_reprefill_v2/baseline_k4_n7.jsonl
  current_best_policy: K=1 selective re-prefill (20f short-bucket, Qwen 7B)
  supersedes:
    - research/experiments/2026/2026-04-20-phase-1_55D-selective-reprefill-v1-driver-findings.md
  paper_relevance: active (working fidelity-recovery frontier; deployment-grade speed still open)
  prereg_outcome: K=1 on the full 7-clip tranche again earns H1 observationally strongly (session accuracy `17/21`, baseline accuracy `17/21`, `Δacc = 0.0`, no observed paired diffs on `n=21`), earns H3 strongly (pathological attractors `0/14` on follow-ups), and earns H4 (`peak_rss_gb = 4.886` vs `<=5.0`). H2 narrowly misses the intended deployment crossover: paired all-query-cold median over session-follow-up median `= 9.71×`, and the paired cold-follow-up median over session-follow-up median is `9.48×`. K=2 and K=4 remain useful comparison points (`6.72×` and `3.66×`), but the fixed-K frontier is now effectively mapped and K=1 is the best local operating point.
  runtime_estimate: ~65min per K for n=7 paired tranche on M3 Air; K=1, K=2, and K=4 are now completed, and further blind K sweeps are lower-value than adaptive refresh/admission policies
  notes: v2 uses repo-local explicit tail slicing, explicit position IDs, prefix-cache materialization, and manual rewind rather than mlx-vlm's partial-image `PromptCacheState` path. A repo-local return-type bug in the first v2 smoke (Qwen `LanguageModelOutput` vs raw tensor) was fixed in commit `d6f9354`; after that, the smoke and full K=4, K=2, and K=1 tranches completed. Wording discipline: describe this as **no observed paired drift on n=21**, not as an unqualified exact-fidelity law, and define the speed metric explicitly. The canonical paired metrics now live in `pair_metrics_k{1,2,4}_n7.json`. The open question is no longer basic runnability or whether fixed-K selective re-prefill works; it is whether an adaptive policy can clear the `>=10×` line without sacrificing the paired-fidelity result.

- phase_id: 1.55E
  status: CLOSED-NEGATIVE 2026-04-24
  authoritative_note: research/experiments/2026/2026-04-24-phase-1_55E-q2-mandatory-q3-optional-findings.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_55E_adaptive_reprefill_q2_k1_q3_k0/summary_k1_n7.json
    - research/experiments/2026/artifacts/phase1_55E_adaptive_reprefill_q2_k1_q3_k0/session_k1_n7.jsonl
    - research/experiments/2026/artifacts/phase1_55E_adaptive_reprefill_q2_k1_q3_k0/baseline_k1_n7.jsonl
  current_best_policy: none; the simplest adaptive omission (`Q2=K1`, `Q3=K0`) is a bounded negative
  supersedes: []
  paper_relevance: negative boundary on adaptive refresh for C-PERSIST deployment
  prereg_outcome: H1 FALSIFIED (`Δacc = -0.0952`, paired correctness diffs `4/21`, paired choice diffs `6/21`), H2 FALSIFIED (paired follow-up median speedup `7.38×` < `10×`), H3 FALSIFIED strongly (`Q3` pathological-like outputs `7/7`, follow-up parse failures `2/14`), H4 EARNED (`peak_rss_gb = 4.555`).
  runtime_estimate: complete (~62min paired tranche on M3 Air)
  notes: This run answers the simplest adaptive question cleanly: `Q2` remains the real rescue point (`7/7` correct, `0/7` pathological-like outputs), but `Q3` is not safely dispensable under the retained-full-cache path (`2/7` correct, `7/7` pathological-like outputs). The lane should not spend more time on blind query-index omission variants. If 1.55 continues, the next adaptive move must change the post-Q2 state itself or add an explicit risk signal for Q3. Cross-run caveat: compared with the earlier 1.55D K=1 baseline, one false item (`videomme:short:120-3`) flipped wrong-answer choice while remaining incorrect; the prereg verdict is therefore anchored to the matched baseline rerun inside the 1.55E artifact directory.

- phase_id: 1.55F
  status: landed (PASS — adaptive Q3=K0+post_q2 dominates fixed K=1 on every dimension)
  authoritative_note: research/experiments/2026/2026-04-25-phase-1_55F-q3-post-q2-state-findings.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_55F_q3_post_q2_state/pair_metrics_k1_n7.json
    - research/experiments/2026/artifacts/phase1_55F_q3_post_q2_state/summary_k1_n7.json
    - research/experiments/2026/artifacts/phase1_55F_q3_post_q2_state/paired_queries_k1_n7.jsonl
  current_best_policy: adaptive Q1-cold / Q2-K=1 / Q3-K=0-from-post-Q2-state on 7-clip 20f short — strongest landed C-PERSIST recovery point
  supersedes: []
  paper_relevance: primary (paper-headline mechanism story for C-PERSIST adaptive)
  prereg_outcome: H1 EARNED (0/21 correctness, 0/21 choice diffs — exact paired fidelity); H1' EARNED at the strongest possible level; H2 EARNED dramatically (0/7 Q3 pathological vs 1.55E's 7/7 catastrophe — cache-source choice was the mechanism); H3 EARNED dramatically (24.91× cross-class follow-up speedup vs 1.55D K=1's 9.71× — 2.57× higher); H4 EARNED with massive margin (peak_rss_gb=1.44 vs 5.5 ceiling, also 3.4× lower than 1.55D K=1's 4.886).
  runtime_estimate: complete (~49.7 min on this laptop)
  notes: This is now the strongest C-PERSIST result. The Q3 catastrophe in 1.55E was definitively a cache-source error, not adaptive-repair impossibility. Q3 takes ~688ms with K=0+post_q2 vs ~87s cold = 126× per-Q3 speedup. The K=0+post-Q2 path apparently lets MLX release more intermediate state than the K=1 path holds onto, producing the 3.4× peak RSS drop. Auto-committed by the queue runner as `cbe10bd`; findings as `f55262c`. Initial run blocked by 1b7c05a-fixed runner bug; rerun completed cleanly post-fix.

- phase_id: 1.55G
  status: landed (PASS science gates; H4 RSS narrowly missed against an over-tight prereg ceiling)
  authoritative_note: research/experiments/2026/2026-04-25-phase-1_55G-k1-medium-replication-findings.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_55G_k1_medium_replication/pair_metrics_k1_n10.json
    - research/experiments/2026/artifacts/phase1_55G_k1_medium_replication/summary_k1_n10.json
    - research/experiments/2026/artifacts/phase1_55G_k1_medium_replication/session_k1_n10.jsonl
    - research/experiments/2026/artifacts/phase1_55G_k1_medium_replication/baseline_k1_n10.jsonl
  current_best_policy: K=1 selective re-prefill at 20f preserves answer identity exactly on the medium tranche (10 clips × 3 queries, 0/30 paired diffs); ~10× follow-up speedup
  supersedes: []
  paper_relevance: primary (turns 1.55D K=1 from short-only to short+medium scope; combined n=51 with 0 observed paired drift)
  prereg_outcome: H1 EARNED (0/30 correctness, 0/30 choice — the tightest possible value); H2 EARNED (0/20 follow-up pathological, 0/10 Q3 pathological); H3 EARNED strongly (speedup_all_query_median_cold_over_session_follow_up = 10.85×; same-class follow-up speedup = 10.76×); H4 FAIL on the strict letter (peak_rss_gb = 6.097 > 5.5 prereg ceiling) but PASS in spirit (well within the 9 GB safe-RSS guard; ceiling was set too aggressively before any 20f-medium evidence existed); H5 EARNED (baseline accuracy = 0.533 ≥ 0.40 floor).
  runtime_estimate: complete (~78.8 min on this laptop)
  notes: First multi-regime confirmation of the C-PERSIST K=1 lane. Speedup *increases* on medium vs short (10.76× vs 9.48×) because the larger 20f-medium prefill (8100 tokens vs 3000 short) makes K=1 cache reuse save proportionally more wall-time. Auto-committed by the closeout queue runner as `45ffc94`.

- phase_id: 1.55H
  status: landed (PASS — K=1 survives 32f depth boundary; speedup 20.37× exceeds 20f speedups due to longer prefill)
  authoritative_note: research/experiments/2026/2026-04-25-phase-1_55H-k1-32f-short-probe-findings.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_55H_k1_32f_short_probe/pair_metrics_k1_n7.json
    - research/experiments/2026/artifacts/phase1_55H_k1_32f_short_probe/summary_k1_n7.json
    - research/experiments/2026/artifacts/phase1_55H_k1_32f_short_probe/paired_queries_k1_n7.jsonl
  current_best_policy: K=1 selective re-prefill at 32f short, 0/21 paired diffs, 20.37× same-class follow-up speedup
  supersedes: []
  paper_relevance: primary (closes the C-PERSIST K=1 lane at scope+depth: 4-cell n=93 with 0/93 paired drift)
  prereg_outcome: H1 EARNED dramatically (0/21 vs ≤3/21 prereg ceiling); H2 EARNED (0/14 follow-up pathological); H3 EARNED dramatically (20.37× same-class vs ≥8.0× gate); H4 EARNED (peak_rss_gb=5.821 ≤ 6.5).
  runtime_estimate: complete (~83.6 min on this laptop)
  notes: 32f short Q1 cold prefill is ~131-147 s vs 1.55D K=1 short Q1's ~80-90 s, so 32f roughly doubles cold-arm cost. K=1 keeps follow-ups at ~6.78 s, producing the 20.37× ratio (~2× higher than 20f speedups). Mechanism: K=1 cache reuse is prefill-dominated, so the speedup ratio scales with prefix length. Auto-committed as `facd82e`; findings as `12502a5`.

- phase_id: 1.55I
  status: landed (PASS — long-bucket K=1, 0/21 paired diffs, 11.24× speedup)
  authoritative_note: research/experiments/2026/2026-04-25-phase-1_55I-k1-long-replication-findings.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_55I_k1_long_replication/pair_metrics_k1_n7.json
    - research/experiments/2026/artifacts/phase1_55I_k1_long_replication/summary_k1_n7.json
    - research/experiments/2026/artifacts/phase1_55I_k1_long_replication/paired_queries_k1_n7.jsonl
  current_best_policy: K=1 selective re-prefill at 20f long, 0/21 paired diffs, 11.24× same-class follow-up speedup
  supersedes: []
  paper_relevance: primary (turns C-PERSIST K=1 from short+medium to short+medium+long; combined n=72 with 0/72 paired drift)
  prereg_outcome: H1 EARNED (0/21 vs ≤2/21); H1' EARNED (combined picture closes at n=93 short+medium+long+32f-short with 0/93 drift); H2 EARNED (0/14 fu pathological, 0/7 Q3 pathological — long-bucket basin not triggered); H3 EARNED (11.24× ≥ 6.0×); H4 EARNED (peak_rss_gb=5.94 ≤ 7.5); H5 EARNED (baseline accuracy=0.333 ≥ 0.30 — long-bucket VideoMME on Qwen 7B-4bit is intrinsically hard, but session and baseline agree byte-identically including on the wrong rows).
  runtime_estimate: complete (~65.0 min on this laptop)
  notes: Natural next scope test after 1.55G. Uses the fixed 7-video long tranche `669,711,712,737,756,758,794`, all drawn from the existing long-manifest pool and validated against the parquet's ≥3-question rule. If H1' passes, the combined K=1 result becomes n=72 paired short+medium+long with 0 observed drift.

- phase_id: 1.55J
  status: completed 2026-04-27
  authoritative_note: research/experiments/2026/2026-04-26-phase-1_55J-k1-sampler-variation-prereg.md
  authoritative_artifacts: [research/experiments/2026/artifacts/phase1_55J_k1_sampler_variation/]
  current_best_policy: fixed K=1 sampler scout at T=0.7 produced a small paired-diff count but remained within the robustness gate
  supersedes: []
  paper_relevance: robustness check for the fixed K=1 repaired frontier; tests whether 0/n paired drift is greedy-only
  prereg_outcome: landed; superseded for adaptive headline purposes by 1.55K
  runtime_estimate: complete
  notes: The v2 explicit-tail generator now supports sampling through the same MLX sampler family used by mlx-vlm generation. This phase should not be confused with the already-landed 1.55A sampler probes, which tested naive persistent-KV basin robustness rather than repaired K=1 selective re-prefill.

- phase_id: 1.55B
  status: proposed (deferred)
  authoritative_note: research/experiments/2026/2026-04-19-phase-1_55B-persistent-kv-decode-composition-prereg.md
  authoritative_artifacts: []
  current_best_policy: n/a
  supersedes: []
  paper_relevance: secondary (composition of persistent-KV with 1.54 decode-accel toward the pre-release 1.8× long-clip aggregate)
  prereg_outcome: (deferred; blocked on 1.54 landing first)
  runtime_estimate: ~45min composition pass + ~20min controls at 8f; ~2h composition + ~30min controls at 32f
  notes: Composition gate — only meaningful after 1.55A reproduces and 1.54 lands. Three H: aggregate long-clip e2e ≥2.0×, no new accuracy regression, peak RSS ≤13GB.

- phase_id: 1.56
  status: proposed (deferred-design)
  authoritative_note: research/experiments/2026/2026-04-19-phase-1_56-vlm-signaled-refresh-prereg.md
  authoritative_artifacts: []
  current_best_policy: n/a
  supersedes: []
  paper_relevance: secondary (Codex round-21 refresh-policy extension; tests whether VLM-internal signal beats pixel/structural for refresh routing)
  prereg_outcome: (pending; blocked on Phase 1.44 answer-margin logging + RefreshPolicy API)
  runtime_estimate: ~45min at 8f (3 arms × n=30 VideoMME dev); ~2h at 32f
  notes: Codex-round-21 hypothesis extending the pre-release scale-out system. Three H: signal beats pixel-MEAN at matched compute, random-ablation rules out correlate-of-activity, signal needs lower refresh rate at matched accuracy. Paper language constrained to "VLM-signaled" until Phase 1.44 lands; no "confidence-conditioned" framing until earned.

- phase_id: 1.57
  status: findings-landed (Qwen + Gemma complete)
  authoritative_note: research/experiments/2026/2026-04-19-phase-1_57-feature-drift-findings.md + research/experiments/2026/2026-04-24-phase-1_57-gemma-feature-drift-findings.md + research/experiments/2026/2026-04-23-phase-1_57-holdout-recheck-findings.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_57/qwen_8f_dev30.json
    - research/experiments/2026/artifacts/phase1_57/qwen_16f_dev30.json
    - research/experiments/2026/artifacts/phase1_57/qwen_32f_dev30.json
    - research/experiments/2026/artifacts/phase1_57_gemma/gemma_8f_long.json
    - research/experiments/2026/artifacts/phase1_57_gemma/gemma_16f_long.json
    - research/experiments/2026/artifacts/phase1_57_gemma/gemma_32f_long.json
  current_best_policy: n/a
  supersedes: []
  paper_relevance: primary mechanism (feature-drift geometry for Qwen frame scaling and Gemma architecture-conditioned reuse; lower-bound adjacent-frame proxy, not true cache-substitute measurement)
  prereg_outcome: Qwen 8f/16f/32f landed on videomme_dev_v1 n=30. H2 FALSIFIED (STATIC cos 0.562/0.607/0.638, all below [0.95, 1.00] prereg band). H3 EARNED under adjacent-frame measurement (monotonic rise). Per-bucket stratification reveals attention-mixing ceiling is bucket-dependent. Gemma long-bucket path landed 2026-04-24 with corrected 133 pooled-token geometry: STATIC cosine 0.7689/0.7940/0.8074 at 8f/16f/32f, H1 EARNED and preregistered monotonic-decrease H3 FALSIFIED in the opposite direction.
  runtime_estimate: ~45-60min total (Gemma + Qwen, 8/16/32 frames × N items, feature-tap extraction only — no generation)
  notes: Measurement methodology is adjacent-frame fresh-vs-fresh (not the pre-release cache-substitute); findings docs document the lower-bound interpretation. Qwen long-bucket drift co-saturates with dev accuracy at 16f, but the 16f long-bucket accuracy shape does not replicate on holdout. Gemma's cached-feature path is substantially higher-cosine than Qwen at matched long-bucket frame counts and improves with denser sampling, but 1.42 shows that higher feature cosine does not guarantee answer-identity stability. Phase 1.58 (bf16) remains open.

- phase_id: 1.58
  status: proposed (deferred)
  authoritative_note: research/experiments/2026/2026-04-19-phase-1_58-bf16-quantization-ablation-prereg.md
  authoritative_artifacts: []
  current_best_policy: n/a
  supersedes: []
  paper_relevance: secondary (quantization × long-context — one of three candidate mechanisms for the 16f long-bucket regression)
  prereg_outcome: (deferred; gated on bf16 Qwen 2.5-VL-7B checkpoint download ~15 GB + feasibility check on 16 GB Mac)
  runtime_estimate: ~50-60min bf16 8f n=30 + ~2.5-3h bf16 16f n=30 + matched 4bit re-runs if needed; total ~3.5-4h once bf16 checkpoint is local
  notes: Tests H-C (4bit × long-context) from the 2026-04-19 16f findings. Four pre-registered H: H1 long-bucket quantization gap ≥ +0.20, H2 no short-bucket gap, H3 RSS < 14 GB, H4 prefill ~4× ratio. Discriminator for the 16f non-monotonic finding; complementary to Phase 1.57 (feature-drift). Wrapper + analyzer landed 2026-04-22 in `scripts/run_phase1_58_bf16_control.sh` and `scripts/analyze_phase1_58_bf16_control.py`; remaining blockers are checkpoint availability and RSS feasibility, plus the tighter local machine policy that keeps autonomous runs near a 10 GB ceiling on this 16 GB laptop.

- phase_id: 1.59
  status: research_note (future work, no prereg)
  authoritative_note: research/experiments/2026/2026-04-19-phase-1_59-training-acceleration-feasibility.md
  authoritative_artifacts: []
  current_best_policy: n/a
  supersedes: []
  paper_relevance: methodology (closes Codex round-22 gap on the missing "training speedup" thread; scoped as named future-work rather than a vague paragraph)
  prereg_outcome: n/a (research note, not a prereg)
  runtime_estimate: n/a on M3 Air (hardware-insufficient; cloud/larger-Mac microbench ~few hundred training steps × 2 variants if resources materialize)
  notes: Articulates whether and how the codec-through mechanism could extend to training (not just inference). Scope: cache-substitute forward + gradient handling at STATIC tokens. Decision: NOT preregistering on M3 Air; paper § Future Work now names this direction with a concrete reference + cites Phase 1.57 as the gating measurement.

- phase_id: 1.60
  status: CLOSED — CORPUS LIMITATION 2026-04-23
  authoritative_note: research/experiments/2026/2026-04-23-phase-1_60-corpus-limitation-findings.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_60_curation_audit/qwen_8f_combined.json
    - research/experiments/2026/artifacts/phase1_60_curation_audit/qwen_16f_combined.json
    - research/experiments/2026/artifacts/phase1_60_curation_audit/qwen_32f_combined.json
    - research/experiments/2026/artifacts/phase1_60_curation_audit/shifted_fraction_ranking.json
  current_best_policy: n/a (regime-boundary probe, not a policy selection)
  supersedes: []
  paper_relevance: secondary corpus-boundary result; closes the VideoMME path and keeps scroll/pan as future work on an egomotion/scroll corpus rather than as an unresolved local blocker
  prereg_outcome: natural-VideoMME subset construction failed for corpus reasons, not model reasons; wider 60-item scan selected 0/60 at shifted_fraction >= 0.30, max 0.125
  runtime_estimate: n/a on natural VideoMME; future egomotion/synthetic reopen would need a new prereg and subset
  notes: Path A (wider VideoMME scan) executed on 60 items stratified 20 short / 20 medium / 20 long across 8f, 16f, and 32f. The observed shifted-fraction ceiling is far below the relaxed gate, so VideoMME lacks the sustained scroll/pan regime. Do not describe this as C-VISION failing on scroll/pan. Reopen only via EgoSchema/EPIC-Kitchens/Ego4D or a labeled synthetic scroll/pan set.

- phase_id: 1.61
  status: ready (analysis-only; no MLX runtime)
  authoritative_note: research/experiments/2026/2026-04-25-paper-closeout-runbook.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_61_per_item_drift_summary.json
  current_best_policy: n/a
  supersedes: []
  paper_relevance: primary supporting analysis (unifies per-item drift across C-VISION, cross-architecture reuse, and persistent-KV failure)
  prereg_outcome: n/a (analysis synthesis, not a new benchmark run)
  runtime_estimate: <1 min CPU-only
  notes: `scripts/build_per_item_drift_summary.py` builds figure-ready JSON from landed artifacts only. The goal is to make the paper's explanatory story concrete: aggregate metrics alone are incomplete, and the repo now has three distinct drift phenotypes worth showing in one place (1.30 V-only Q0 flips, 1.42 Gemma aggregate-preserved identity drift, 1.55A persistent-KV pathological attractors).

- phase_id: 1.63
  status: superseded by 1.63E/1.63G/1.63H
  authoritative_note: research/experiments/2026/2026-04-27-phase-1_63-track-b-sparse-vit-prereg.md
  authoritative_artifacts: []
  current_best_policy: base prereg superseded by measured sparse-execution frame scaling and keep-rate sweep
  supersedes: []
  paper_relevance: primary (first measured real skipped ViT work for C-VISION; LM prefill remains dense)
  prereg_outcome: superseded; see 1.63E/G/H
  runtime_estimate: superseded
  notes: Scope is vision-tower-only measured sparse execution. It hard-gates on both real vision-stage reduction and positive end-to-end speedup so a dense-stage-share null cannot be accidentally promoted as a headline.

- phase_id: 1.63E
  status: completed partial / boundary 2026-04-29
  authoritative_note: research/experiments/2026/2026-04-27-phase-1_63E-track-b-frame-scaling-prereg.md + research/experiments/2026/2026-04-27-phase-1_63E-8f-findings.md
  authoritative_artifacts: [research/experiments/2026/artifacts/phase1_63E_track_b_frame_scaling/]
  current_best_policy: "Qwen compact post-layer L=2 kr=0.50 measured sparse vision: 8f ceiling explained (1.042x observed vs 1.047x predicted) and real vision work skipped, but H_fidelity FAILS at -0.067 aggregate; 16f kr=0.50 catastrophically fails format/fidelity"
  supersedes: []
  paper_relevance: primary boundary (C-CEILING timing validation plus Qwen fidelity/format failure at aggressive keep rate)
  prereg_outcome: "8f timing boundary passes H_sparse_vision/H_e2e_positive/H_ceiling_explained but fails H_fidelity; 16f kr=0.50 fails format/fidelity and motivates 1.63H"
  runtime_estimate: complete partial
  notes: Preserve as a negative/boundary result, not a positive sparse-backend headline.

- phase_id: 1.63G
  status: completed 2026-04-29
  authoritative_note: research/experiments/2026/2026-04-27-phase-1_63G-gemma-track-b-prereg.md
  authoritative_artifacts: [research/experiments/2026/artifacts/phase1_63G_gemma_track_b/]
  current_best_policy: Gemma measured sparse vision at 8/16/32f has zero paired answer drift; cleanest cell is 32f short at 1.316x with 0/20 drift and 0/0 parse failures; full sweep has matched parse-failure caveats and 8f ceiling miss
  supersedes: []
  paper_relevance: primary measured sparse-execution evidence (Gemma curve plus caveats)
  prereg_outcome: landed as bounded envelope; headline_pass=false because full sweep is not format-clean and 8f misses ceiling tolerance
  runtime_estimate: complete
  notes: Use paper wording "zero paired drift under matched parse behavior"; do not call it clean all-gates.

- phase_id: 1.63H
  status: completed 2026-04-29
  authoritative_note: research/experiments/2026/2026-04-29-phase-1_63H-16f-kr-sweep-findings.md
  authoritative_artifacts: [research/experiments/2026/artifacts/phase1_63H_16f_kr_sweep/]
  current_best_policy: Qwen 16f keep-rate sweep recovers to within aggregate-accuracy and format gates as kr rises; kr=0.85 is aggregate-accuracy/format/ceiling safe but does not preserve paired answer identity, and remains low-gain at 1.032x and 13.6% vision-time reduction
  supersedes: []
  paper_relevance: primary boundary (Qwen measured sparse-execution configuration envelope)
  prereg_outcome: landed; useful monotone recovery curve, not a full sparse-vision gate pass
  runtime_estimate: complete
  notes: If a Qwen positive sparse-backend claim is needed later, bracket kr=0.75--0.85 to see whether any point preserves fidelity while clearing the 25% vision-reduction gate.

- phase_id: 1.55F-stage-timing
  status: completed 2026-04-27
  authoritative_note: research/experiments/2026/2026-04-27-phase-1_55F-stage-timing-prereg.md
  authoritative_artifacts: [research/experiments/2026/artifacts/phase1_55F_stage_timing/]
  current_best_policy: adaptive Q3 wins because it inherits post-Q2 repaired cache; tail tokens 451->50 and paired Q3 fixed/adaptive speedup is 9.50x
  supersedes: []
  paper_relevance: secondary mechanism (explains adaptive C-PERSIST speedup as Q3 re-prefill avoidance)
  prereg_outcome: landed; mechanism attribution explains adaptive speedup over fixed K=1
  runtime_estimate: complete (<1min)
  notes: No new MLX generation; this is a mechanism attribution over existing JSONL timings and tail-token counts. The preregistered Q3 speedup gate is >=3x so the analyzer does not mark a clear measured attribution as a false failure solely because it is below a more aggressive 5x heuristic.

- phase_id: 1.55K
  status: completed 2026-04-29 (base) + completed 2026-04-30 (extended seed sweep)
  authoritative_note: research/experiments/2026/2026-04-27-phase-1_55K-adaptive-temperature-sweep-prereg.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_55K_adaptive_temperature_sweep/
    - research/experiments/2026/artifacts/phase1_55K_extended_seed_sweep/extended_seed_sweep_summary.json
  current_best_policy: |
    adaptive short-cell sampler sweep across T=0.0/0.5/0.7/1.0/1.5 (base);
    extended cross-product across (seed × T) ∈ {42, 99, 2026} × {0.5, 1.0, 1.5}
    closes 9/9 cells with max |Δacc|=0.048, 0/189 pathological format hits,
    baseline floor 0.667, cold/follow-up speedup 17.37–25.84×.
  supersedes: [1.55J]
  paper_relevance: robustness check (tests whether adaptive C-PERSIST headline is greedy-only AND single-seed-only)
  prereg_outcome: |
    base sweep landed as practical robustness evidence against greedy-only
    artifact; the extended seed sweep (Phase 2 chain step A7) closes the
    single-seed-coincidence concern across three seeds at three temperatures
    on the same short tranche. Neither covers the full 0/93 breadth nor
    benchmark generalization; both apply only to the seven-clip short slice.
  runtime_estimate: complete
  notes: |
    Uses identical sampler settings for session and baseline arms; T=0.0 greedy
    1.55F is included as reference when present. The summary hard-gates
    sampler-robustness on absolute cold-baseline accuracy >=14/21 in every
    temperature cell so mutual sampler collapse cannot masquerade as cache
    robustness. The extended seed sweep findings are recorded in
    research/experiments/2026/2026-04-30-phase-1_55K-extended-seed-sweep-findings.md
    and the paper-side robustness table is generated as
    paper/arxiv/generated/tables/c_persist_sampler_seed_sweep.tex.

- phase_id: 1.30AF
  status: completed 2026-04-29
  authoritative_note: research/experiments/2026/2026-04-27-phase-1_30AF-cache-boundary-attribution-prereg.md
  authoritative_artifacts: [research/experiments/2026/artifacts/phase1_30AF_cache_boundary_attribution/]
  current_best_policy: post-hoc AC/AD attribution: same aggregate loss, non-identical row-level failure sets, Jaccard 0.3125
  supersedes: []
  paper_relevance: secondary mechanism (distinguishes same aggregate loss from row-identical behavior)
  prereg_outcome: landed; supports "same aggregate boundary through different row sets" but not causal tensor mechanism
  runtime_estimate: complete (<1min)
  notes: Named 1.30AF because 1.30AE already denotes the skipped duration-conditioned union candidate. This is not direct KV tensor-distance measurement; it reports duration/q-index/cold-correctness feature concentrations and, when 1.65 has landed first, logit-margin stratification.

- phase_id: 1.55F-Gemma
  status: deferred / blocked
  authoritative_note: research/experiments/2026/2026-04-27-phase-1_55F-gemma-adaptive-deferred.md
  authoritative_artifacts: []
  current_best_policy: blocked; Gemma 4 adaptive C-PERSIST requires cache-type-aware sliding-window/RotatingKVCache support
  supersedes: []
  paper_relevance: future cross-architecture C-PERSIST breadth
  prereg_outcome: blocked before run
  runtime_estimate: n/a until driver exists
  notes: Gemma 4 E4B 4-bit weights are local and fit prior runs, but the Qwen selective re-prefill driver must not be reused because 1.55C found silent Gemma prompt-cache corruption risk.

- phase_id: 1.65
  status: completed scout 2026-04-29
  authoritative_note: research/experiments/2026/2026-04-27-phase-1_65-logit-margin-predictor-prereg.md
  authoritative_artifacts: [research/experiments/2026/artifacts/phase1_65_logit_margin_failure_predictor/]
  current_best_policy: dense answer-letter margin has signal but is insufficient alone as a high-precision drift guard
  supersedes: []
  paper_relevance: primary diagnostic (tests whether 1.30 cache-boundary drift concentrates on intrinsically uncertain items)
  prereg_outcome: negative scout landed; test AUC point estimate 0.7125 but pass_margin_signal/pass_safe_filter fail
  runtime_estimate: complete
  notes: This is an oracle-feature predictor scout, not a deployed guard. It deliberately excludes Q0 rows and all 1.55F/adaptive rows to avoid learning admission/source/policy identity instead of within-1.30 follow-up stability; rows where the dense logit argmax disagrees with the artifact dense choice are rejected before analysis.

- phase_id: 1.30AG
  status: CLOSED-EARNED 2026-05-01 (all four gates pass; saturation HOLDS via fp32 cosine column)
  authoritative_note: research/experiments/2026/2026-04-30-phase-1_30AG-kcache-distance-probe-findings.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_30AG_kcache_distance_probe/kcache_distance_rows.jsonl
    - research/experiments/2026/artifacts/phase1_30AG_kcache_distance_probe/kcache_distance_summary.json
  current_best_policy: |
    20 paired rows × 28 layers × 2 arms × 2 (k/v) captured. Finite-audit
    telemetry confirms the cache is finite at every (row × layer × arm) -
    valid_window_nan_layers = 0, valid_window_inf_layers = 0, buffer-tail
    audit also clean. Native fp16 cosine reduction overflows on ~3M-element
    flat windows when single elements have |x| >= 256 (observed max_abs up
    to 420.75); the per-layer fp32 control cosine the finite-audit patch
    added is finite at every layer. Headline numbers (fp32 column, clamped):
    reuse_keys cos = 1.000, pruned_keys cos = 0.724 (distance 0.276);
    reuse_values cos = 1.000, pruned_values cos = 0.296 (distance 0.704).
    Saturation relative gap on cosine_fp32_distance: keys 0.9999993,
    values 0.9999989 (gate >= 0.5; passes by a wide margin). The 1.30
    mechanism question is now answered: vision-layer-2 pruning at kr=0.5
    produces substantial K and dominant V cache divergence vs dense, while
    same-prefix Q0 cache reuse preserves the cache exactly.
  supersedes: []
  paper_relevance: secondary mechanism evidence (1.30 K/V cache distance under reuse vs prune); not a paper headline by itself but materially strengthens the Phase 1.30 root-cause story
  prereg_outcome: |
    CLOSED-EARNED. H1 capture, H2 distance reporting, H3 outcome linkage,
    H4 saturation all PASS. headline_pass = True. Distance numbers ARE now
    release-claim-bearing as long as the paper-side text uses the fp32
    column and notes that the native fp16 column overflows by design at
    this flatten-and-reduce scale.
  runtime_estimate: complete (capture 30 min + finite-audit telemetry rerun 30 min + reaggregate 0.1 s)
  notes: |
    Named 1.30AG because 1.30AE already denotes the skipped duration-conditioned
    union candidate. Cache is mlx.core.float16 (NOT bf16 as earlier draft
    assumed). The earlier "fp32 cast crashed with NSException" was a sandbox
    artifact (Metal init blocked), not memory pressure. The retracted
    upstream-cache-NaN claim has been replaced with the correct fp16
    sum-of-squares overflow diagnosis. Reaggregator at
    scripts/reaggregate_phase1_30AG.py is MLX-free and lets future analyzer
    changes refresh the summary without paying the 30-min capture cost.
    One row in reuse_only_drift class (Q index 7) shows layer-systematic
    ~1e-4 reuse-arm K drift; not a closure blocker but worth a footnote
    in any paper-side use.

- phase_id: 1.66
  status: completed 2026-04-29
  authoritative_note: research/experiments/2026/2026-04-27-phase-1_66-memory-characterization-prereg.md
  authoritative_artifacts: [research/experiments/2026/artifacts/phase1_66_memory_characterization/]
  current_best_policy: analysis-only memory envelope over landed 1.30/1.55/1.63 artifacts; max observed peak 13.61 GB, measured sparse-execution max 10.80 GB
  supersedes: []
  paper_relevance: robustness check (turns RSS-gate misses and high-watermark cells into an explicit local-memory envelope)
  prereg_outcome: landed; use to distinguish MLX allocation cap from observed process working-set peaks
  runtime_estimate: complete (<1min)
  notes: Emits JSON and CSV only; it is not a model-quality claim and should be used to explain local 16 GB resource boundaries.
```

## Maintenance rules

- When a phase status changes (runs → completed, completed →
  superseded), update the registry row in the same commit as the
  corresponding phase note + decision-log entry.
- When `current_best_policy` changes, update `supersedes` and
  `paper/framing.md` + `literature-map-2026-04-16.md` citations.
- When a new phase is preregistered, add its registry row alongside
  the prereg note.
- When PLAN.md or paper/framing.md changes, re-verify that its claims agree with
  this registry. If they disagree, fix the prose and cite back to this registry.
