# Experiment Registry (Machine-Readable)

Last updated: 2026-04-21

This is the primary source of per-phase experiment state. Other docs
(PLAN.md, research-strategy-post-codecsight.md, literature-map,
paper/framing.md) narrate and contextualize; if they contradict this
registry on a phase's status or current_best_policy, fix them.

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
  current_best_policy: "base: max_abs(8,32) static+shifted age=4 — cached=0.600@4.06 (clean tree, Pareto win vs dense-6); sticky4 refinement: cached=0.633@4.49 (dirty tree, Pareto tie vs dense-8)"
  supersedes: [1.12.B (strengthened at N=30)]
  paper_relevance: primary (MVBench N=30 holdout — claim #6 MVBench half PASSED)
  prereg_outcome: Accepted (holdout v2 cells; dev v2 deferred as protocol note)

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
  paper_relevance: superseded (BLOCK_SIZE=28 is already projector-input granularity on Qwen 2.5-VL; sam's Gemma hard-spatial-pruning WP-2.11 is the better spatial follow-on if needed)
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
  status: proposed (planner-accuracy probe wired; pending run)
  authoritative_note: research/experiments/2026/2026-04-16-phase-1_29-mv-only-signal-path.md
  authoritative_artifacts: []
  current_best_policy: n/a
  supersedes: []
  paper_relevance: primary (deployability)
  prereg_outcome: MAX-over-span sparse retrofit falsified; continuous-score redesign partial-pass at aggregate level; downstream planner-accuracy still pending
  notes: 2026-04-22 infrastructure status — short-bucket continuous-score pilot landed (`scripts/pilot_1_29_continuous_codec_score.py`) and the standalone planner-accuracy probe is now wired in `src/codec_through/codec/continuous_score.py`, `scripts/run_phase1_29_planner_accuracy_probe.py`, and `scripts/run_phase1_29_planner_accuracy_probe.sh`. The live question is no longer "can we wire codec-native into the harness?" but "does the reframed planner retain downstream accuracy on a benchmark slice?"

- phase_id: 1.30
  status: proposed (session harness landed; reproduction prereg pending)
  authoritative_note: research/experiments/2026/2026-04-16-phase-1_30-streaming-window-harness.md
  authoritative_artifacts: []
  current_best_policy: n/a
  supersedes: []
  paper_relevance: historical / infra (deferred behind Track B)
  prereg_outcome: (not yet)
  notes: 2026-04-22 implementation status — the local session / streaming harness now exists in `scripts/run_phase1_30_sam_streaming.py`, `scripts/analyze_phase1_30_sam_streaming_pair.py`, and `scripts/run_phase1_30_sam_streaming.sh`. Remaining work is protocol-specific prereg + run selection, not harness wire-up.

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
    - results/novelty_ranked_dense/tomato_holdout_n4.json
    - results/novelty_ranked_dense/tomato_holdout_n6.json
    - results/novelty_ranked_dense/tomato_holdout_n8.json
    - results/novelty_ranked_dense/mvbench_holdout_n4.json
    - results/novelty_ranked_dense/mvbench_holdout_n6.json
    - results/novelty_ranked_dense/mvbench_holdout_n8.json
  current_best_policy: n/a (stronger baseline, not a new policy)
  supersedes: []
  paper_relevance: primary (stronger matched-budget comparator, claim #9)
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
    - results/feature_change_oracle/tomato_n30.json
    - results/feature_change_oracle/tomato_n30.parquet
    - results/feature_change_oracle/mvbench_n30.json
    - results/feature_change_oracle/mvbench_n30.parquet
  current_best_policy: n/a (oracle/diagnostic, not a routing policy)
  supersedes: []
  paper_relevance: primary (claim #2 lower-bound on pixel->feature fidelity)
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
  notes: originally filed as "phase 1.37 Planner 2.1"; renamed 2026-04-17 after Sam flagged that "child-veto" was the name of a distinct mechanism (within-block subtoken guard) and should not be reused for the neighbor-halo variant. Closed 2026-04-17 as preregistered null: TOMATO control rank-1 at cached_accuracy 0.233 with all cells within 1/30 MRU; MVBench control sole rank-1 at 0.800 with 7/8 halo cells losing 0.067-0.100. Halo moves only the agreement knob on TOMATO while draining fresh-frame budget, and actively hurts accuracy on MVBench.

- phase_id: 1.41
  status: EARNED 2026-04-18 (8f); strengthened 2026-04-19 (16f, 32f); **holdout 16f EARNED 2026-04-21** — Qwen 2.5-VL-7B-Instruct-4bit dense on `videomme_dev_v1.toml` n=30 AND `videomme_holdout_v1.toml` n=30 at 16f, parse_failures=0, agreement=1.000 at all frame counts on both splits. Holdout 16f aggregate 0.700 (21/30); per-bucket short 0.600 / medium 0.600 / **long 0.900**. Claim 8 (VideoMME breadth gate) satisfied dev+holdout. **Non-monotone long-bucket regression at 16f is DEV-ONLY and did NOT replicate on holdout** (dev 8f long 0.300 → dev 16f long 0.100; holdout 16f long 0.900 — per-bucket item-draw effect exceeds frame-scaling signal). Paper claim "16f long-bucket regresses" must soften to dev-only. Phase 1.57 feature-drift mechanism (dev-measured) stays intact; its 16f co-saturation framing remains local to dev. 32f adds prompt-length 2× and latency 2× for zero aggregate acc lift over 16f — NOT Pareto-efficient at this model/benchmark.
  authoritative_note: research/experiments/2026/2026-04-16-phase-1_41-videomme-lane.md + research/experiments/2026/2026-04-19-phase-1_41-qwen-videomme-16f-prereg.md + research/experiments/2026/2026-04-19-phase-1_41-qwen-videomme-32f-long-prereg.md + research/experiments/2026/2026-04-19-phase-1_57-feature-drift-mechanism-prereg.md
  authoritative_artifacts:
    - scripts/build_videomme_manifest.py
    - scripts/fetch_videomme_subset.py
    - research/benchmark_manifests/videomme_dev_v1.toml
    - research/benchmark_manifests/videomme_holdout_v1.toml
    - research/experiments/2026/artifacts/phase1_41_qwen_videomme_8f/ (dense baseline)
    - research/experiments/2026/artifacts/phase1_41_qwen_videomme_16f/ (16f follow-up)
    - research/experiments/2026/artifacts/phase1_41_qwen_videomme_32f_long/ (32f long-bucket third data point)
    - research/experiments/2026/artifacts/phase1_41_qwen_videomme_16f_holdout/ (holdout 16f, 2026-04-21)
    - research/experiments/2026/artifacts/phase1_57_feature_drift/ (STATIC-class drift mechanism; adjacent-frame ViT cos)
    - research/experiments/2026/2026-04-19-phase-1_41-qwen-videomme-16f-findings.md
    - research/experiments/2026/2026-04-19-phase-1_41-qwen-videomme-32f-long-findings.md
    - research/experiments/2026/2026-04-21-phase-1_41-qwen-videomme-16f-holdout-findings.md
    - research/experiments/2026/2026-04-19-phase-1_57-feature-drift-findings.md
  current_best_policy: Qwen 2.5-VL-7B-4bit dense at 16f is the paper-reporting default on VideoMME dev (best per-bucket accuracy at Pareto-efficient frame count: short 0.800 / medium 0.700 / long 0.100, agg 0.567). 32f is NOT recommended for paper reporting (flat aggregate, 2× latency).
  supersedes: []
  paper_relevance: primary (claim #8 VideoMME breadth gate; also feeds claim #15 C-VISION frame-count sweep denominator via V_share measurements at 8f/16f/32f)
  prereg_outcome: EARNED at 8f (2026-04-18); STRENGTHENED at 16f+32f (2026-04-19); **holdout 16f CLOSED 2026-04-21** — H1 pass (agg 0.700, at upper edge of [0.50, 0.70]), H2 FALSIFIES (long-bucket regression dev-only; holdout 16f long 0.90 vs dev 16f long 0.10 / dev 8f long 0.30), H3/H4/H5 pass. Three-frame-count × two-split per-bucket surface mapped. Mechanism (1.57 feature-drift as lower-bound proxy, dev-measured): drift rises sub-linearly 8f→32f, co-saturates with accuracy at 16f on long bucket — drift is a co-indicator of dev-split capacity plateau, not the binding cross-split constraint.
  notes: VideoMME videos hosted on HF `lmms-lab/Video-MME` as 20 chunked zip archives (~101 GB full corpus); paper protocol uses 57 unique videoIDs (dev+holdout manifests, one overlap). `scripts/fetch_videomme_subset.py` walks chunks one-at-a-time (peak disk ~5 GB staging + ~3-15 GB extracted subset). See `docs/videomme-download-handoff.md` for env gotchas (HF xet backend must be disabled; SOCKS proxy env vars must be cleared). Phase 1.58 (bf16 quantization ablation) is the remaining open mechanism question for 32f plateau — deferred pending 1.51V primary axis.

- phase_id: 1.42
  status: proposed
  authoritative_note: research/experiments/2026/2026-04-17-phase-1_42-gemma-architecture-topology-prereg.md
  authoritative_artifacts: []
  current_best_policy: n/a (second-architecture fidelity test, not a policy)
  supersedes: []
  paper_relevance: primary (claim #7 architecture-conditioned reuse fidelity — takes evidence from N=1 to N=2 architectures)
  prereg_outcome: (pending; blocked on _mix_gemma_features harness integration)
  notes: Gemma 4-E4B-IT-4bit verified to load on M3 Air 16 GB; all-global vision encoder + learned 2D positional + standard RoPE LLM is architecturally distinct from Qwen's windowed-global + M-RoPE-V

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
    - results/track_b/tomato_mc_n10.json
    - results/track_b/tomato_mc_n30.json
    - results/track_b/mvbench_mc_n30.json
    - scripts/run_track_b.py
  current_best_policy: n/a (wall-clock baseline, not a policy)
  supersedes: []
  paper_relevance: primary (claim #5 dense reference; sparse-execution half still blocked)
  prereg_outcome: Accepted with caveat (dense baseline paper-grade on TOMATO N=30 + MVBench N=30 holdout; cross-benchmark vision-cache ceiling 20-23% end-to-end; sparse-execution delta still not measured)

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
  current_best_policy: n/a — own-axis null confirmed at n=30 across 3 anchor arms at kr=0.50 on VideoMME dev (Stage 5 2026-04-18); ceiling binds anchor-invariantly. Composition with 1.51V at EXP10 cell (anchor=none kr=0.3) pending n=60 promotion gate.
  supersedes: []
  paper_relevance: secondary (demoted from primary per codex round-25 and paper/priority.md must-do #5: 1.51V is the primary local Gemma story, not 1.51R; 1.51R contributes (i) the EXP10 n=60 H_stack composition gate on VideoMME holdout and (ii) the Stage 5 gemma_structural anchor default as secondary methodology content; publishable preregistered null with mechanistic explanation; composition with 1.51V pending EXP10 n=60 outcome)
  prereg_outcome: NULL on own axis (Stage 5 n=30 cross-arm synthesis 2026-04-18 + post-1.51V composition closure 2026-04-21); EXP10 cell n=60 follow-up IN FLIGHT 2026-04-21 (task #152)
  notes: phase is tracked as the "1.51R" fresh driver across other docs (R = Reproduction of Sam's novelty-pruning, fresh code path that does not consume `_mix_gemma_features`). Preregistered 5 literature-grounded anchor-preservation arms (FastV, FasterVLM/HiPrune, Nüwa pillar, VLM-Pruner max-min diversity, IVC-Prune-spirit Gemma-structural); keep-rate grid {0.3..0.7}; must run on Gemma (not Qwen) because Qwen's M-RoPE-V ties token index to 2D grid position and breaks under token drop. cls_attention_proxy arm is explicitly excluded from winner promotion (see PROMOTABLE_ARMS in novelty_pruning.py). Pilot reveals vision-tower pruning (NEW phase 1.51V, task #87) is the only mechanism that could reach Sam's ≥1.8× end-to-end on E4B; queued as follow-up.

- phase_id: 1.51V
  status: CLOSED 2026-04-21 — expansion 12/12 DONE + session 2 (32f probe EXP13/14 + holdout EXP15/16) 4/4 DONE. H1 CONFIRMED (V_red=39.0% thermally-paired EXP01/02, decode Δ=-2.8%); H_pareto EARNED (kr=0.25 Pareto-dominates kr=0.50 on VideoMME: +23pp V_red at identical E2E and accuracy); H_transfer EARNED on MVBench (1.21× E2E at V_red=40%) and TOMATO (1.24× E2E at V_red=42.7%, +3.3pp accuracy); H_fsscale CONFIRMED at 16f (V_red benchmark-invariant, E2E 1.12× matches ceiling prediction 1.105× within 1pp); H_32f_vshare CONFIRMED (V_share climbs to 31.0% at 32f per ceiling model) but H_32f_e2e REJECTED (M3 16GB hits thermal cap at 32f: decode Δ +7.6% violates <2% pairing gate, cross-session headline inflated); H_stack PARTIAL CONFIRMATION on holdout (EXP15/16 VideoMME v1 n=30 disjoint: within-run 1.064× ceiling-matched via LLM-side analog 1/(1 − generate_share × generate_reduction), agreement 0.667 mirroring dev, acc Δ -0.033; below 1.10× headline-reopener threshold so stays secondary-claim). V-only holdout unpatched-vs-patched pair status (three-benchmark C-VISION trifecta effectively closed 2026-04-21 with differentiated advisory strength): **VideoMME 8f CLOSED 2026-04-21** session 3 EXP17/18 (E2E 1.113×, V_red 0.413, decode Δ 1.53%, acc Δ 0.000; holdout V_share=15.45%); **MVBench 8f CLOSED 2026-04-21 with advisory pass** session 4 EXP19/20 (E2E 1.407× far exceeding dev 1.21×, V_red 0.471, acc Δ −0.033; thermal gate 11.66% formally fails but 50 ms absolute is OS-jitter scale on MVBench's 432 ms decode window — calibration revision proposed); **TOMATO 8f EARNED-ADVISORY 2026-04-21** session 5 EXP23/24 (rerun after session 4 confound: E2E sum-ratio mean 1.194×, median 1.232×, clears 1.15× primary gate; V_red 0.350 below [0.38, 0.48] band by 0.03; decode Δ 119.7 ms = 3.51% rel in FAVORABLE direction — patched arm cooler than reference, observed speedup conservatively under-stated; scatter-back ceiling predicts 1.155×, consistent with ceiling + friendly thermal correction; acc Δ −0.067). Architectural ceiling 1/(1 − V_share × V_red) validated quantitatively on 5 (benchmark, frame-count, axis) cells including LLM-decode axis.
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
  prereg_outcome: H1 CONFIRMED, H_pareto EARNED, H_transfer EARNED, H_fsscale CONFIRMED, H_stack PARTIAL REOPENER on dev → PARTIAL CONFIRMATION on holdout (2026-04-21 session 2), H_32f_vshare CONFIRMED, H_32f_e2e REJECTED (thermal cap on M3 16GB)
  notes: Critical implementation bugs found and fixed 2026-04-20 — (1) Python `__call__` is looked up on the type, not the instance, so `encoder.__call__ = new_call` is silently a no-op. Fixed with `_PrunedEncoderWrapper` class-level `__call__`. (2) Helpers assumed B=1 but Gemma-4 vision tower batches frames in leading dim (B=N_frames). Generalized to per-frame pruning via `mx.take_along_axis` and batched one-hot matmul. (3) Cross-session thermal drift on M3 Air inflated standalone n=30 vision_ms by ~27% (decode_ms proxy: +6.5% drift vs control). **Authoritative V_red = 39.0% (paired EXP01/EXP02, thermally-paired within-session, decode drift < 2% — the strictest pairing the expansion batch can produce).** A cross-session composition-dense-arm normalization gave 42.2% on the earlier 2026-04-20 tranche (decode +0.2% vs a prior session's control); the 3.2pp delta sits inside the thermal-drift bracket and both readings attest the same mechanism, but per Codex round-22 the paired 39.0% is the paper-facing number. See `research/experiments/2026/2026-04-21-phase-1_51V-expansion-findings.md` §Reproduction-of-prior-claim for the reconciliation. **Architectural ceiling** (scatter-back preserves pooler geometry): pruned tokens scattered back to original length, so LM prompt token count is unchanged (2181 tokens), LM prefill + generate get zero speedup from 1.51V. E2E upper bound = `1 / (1 - V_share × V_red)` = 1.16× at V_red=100% on 8-frame VideoMME dev, cutting to 1.06× at V_red=39.0% × V_share=15.2% (8f). Reaching H3's 1.5× requires either (a) post-pool token merging that cuts LM prompt, (b) bypass scatter-back with a new pooler, or (c) composition with persistent-KV (CLOSED on 1.55 lane) or 1.51R (null on novelty axis).

- phase_id: 1.52R
  status: proposed
  authoritative_note: research/experiments/2026/2026-04-17-phase-1_52-combined-temporal-spatial-prereg.md
  authoritative_artifacts: []
  current_best_policy: n/a
  supersedes: []
  paper_relevance: primary (multiplicative composition — temporal reuse AND novelty-pruning stacked — paper-table headline number)
  prereg_outcome: (pending; blocked on 1.42 and 1.51R passes)
  runtime_estimate: ~2-3h at 8f n=30 per arm (dense+pruned); ~6-8h at 32f
  notes: three-way gate preregistered (multiplicative / additive / interference); PoRe (arxiv 2508.17807) reserved as a composable axis under phase 1.52R holdout (see 1.51 prereg §Composable Arm) — NOT phase 1.53 (1.53 is now the object-state delta sidecar, preregistered 2026-04-18).

- phase_id: 1.55
  status: superseded
  authoritative_note: research/experiments/2026/2026-04-19-phase-1_55-persistent-kv-prereg.md
  authoritative_artifacts: []
  current_best_policy: n/a
  supersedes: []
  paper_relevance: historical (split into 1.55A reproduction + 1.55B composition per Codex round-22; original provenance+gating were wrong)
  prereg_outcome: Superseded
  runtime_estimate: n/a (see 1.55A, 1.55B)
  notes: Original prereg mistakenly attributed Sam's MEASURED 2.13.3 persistent-KV result as a Codex hypothesis, and gated on an mlx-vlm fork that turned out to already be upstream (PromptCacheState + find_prefix_length). Split 2026-04-19 into 1.55A (reproduction of Sam 2.13.3 on Qwen 7B/M3 Air) and 1.55B (composition with 1.54 decode accel — deferred).

- phase_id: 1.55A
  status: completed/CLOSED (8f + 16f + 18f + 20f + 24f + 32f frame-scaling on 7B + 3B 20f matched + 3B 24f shifted-ramp + 3B 32f plateau-candidate + 3B 36f PRE-BASIN PLATEAU EXTENDED + 3B 40f LATENT BASIN EARNED + **7B 40f BASIN-SYMMETRY EARNED** + 7B/20f temperature probe EARNED H-distribution-collapse + 3B/20f temperature probe EARNED H2-3B-temp.null-robust + **3B/40f temperature probe HYBRID (basin partially dispersed, sampler-invariance is architecture-conditional)**; three-dimensional mechanism decomposition REVISED 2026-04-20 from saturation-ceiling to shifted-onset-same-basin AND **SYMMETRICALLY CONFIRMED** 2026-04-20 on 7B at 2× basin-onset depth: threshold onset capacity-modulated, **basin-onset depth architecture-dependent** (7B ~8k tokens; 3B ~16k tokens, ~1.6× scaling), **basin geometry architecture-conditional under sampling** — 7B basin sampler-invariant at both 20f and 40f; 3B basin at 40f is sampler-dispersible (4/14 → 1/14 novel) but dispersed mass returns only to the pre-basin plateau, not to baseline; phase closes; reopen conditions (f) RETIRED and (h) CLOSED with HYBRID outcome)
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
  current_best_policy: "persistent-KV session (PromptCacheState one-per-clip) — 7B-4bit: 8f 47.2×/815ms/Δ=−0.048; 16f 91.1×/807ms/Δ=0.000; 18f 70.3×/1102ms/Δ=−0.238 (4-basin); 20f 94.4×/905ms/Δ=−0.381 (2-basin); 24f 121.6×/864ms/Δ=−0.429 (single attractor); 32f 149.9×/1008ms/Δ=−0.429 (saturated). **7B/20f temperature probe (T=0.7, top_p=1.0, min_p=0.05, seed=42): 117.0×/907ms/Δ=−0.429 — Δacc temperature-invariant within 1/21 noise floor (greedy −0.381, temp −0.429; diff 0.048); basin prevalence 13/14→8/14 but clean-drift share stayed 1/14 (dispersed mass landed in novel `自动生成` Chinese attractor, NOT in clean letters); H-distribution-collapse EARNED on both prereg conditions (Δacc≤−0.35 AND basin≥0.50). 7B basin is distribution-level, not sampler-level.** **3B-4bit cross-arch 3-point: 20f 136.1×/412ms/Δ=−0.048 (MATCHED); 24f 154.2×/423ms/Δ=−0.190 (SHIFTED-RAMP); 32f 213.0×/484ms/Δ=−0.190 (PLATEAUED — identical Δacc to 24f, 3B saturated at a ~2.3× shallower ceiling than 7B). 28/28 3B follow-ups emit clean 2-token letter answers — no basin collapse at any 3B prefill.** **3B/20f temperature probe (T=0.7, top_p=1.0, min_p=0.05, seed=42): 130.8×/385ms/Δ=−0.095 — H2-3B-temp.null-robust EARNED (Δacc inside envelope [−0.15, +0.05] AND 14/14 clean-letter follow-ups); Δacc shifts by exactly 1/21 vs greedy 3B/20f (−0.048 → −0.095), identical noise-floor signature to 7B temperature probe (−0.381 → −0.429, 1/21 shift). Sampler-invariance verified at BOTH ceilings.** 7B: monotonic-saturating ramp 16f→24f through progressive basin collapse, Δacc ceiling −0.43 (distribution-level). 3B: ramp shifted ~2-3k tokens later, Δacc ceiling −0.19 (architecture-specific), failure geometry is clean-letter drift (architecture-specific)."
  supersedes: ["1.55"]
  paper_relevance: primary (reproduces Sam whitepaper §2.13.3 on Qwen 7B-4bit / M3 Air; prefill-dominance mechanism confirmed on 6-point scaling curve; 18f+20f bisections reveal the 7B fidelity transition is a monotonic-saturating ramp through progressive basin collapse — clean → 4-basin → 2-basin → single-attractor; 3B cross-arch 3-point (20f matched, 24f shifted-ramp, 32f plateaued) decomposes the mechanism into **three orthogonal architectural dimensions: threshold onset (capacity-modulated), saturation ceiling (architecture-specific −0.43 vs −0.19), failure geometry (architecture-specific basin collapse vs clean-letter drift)**)
  prereg_outcome: H1/H1'/H1''/H1'''/H1''''/H1''''' all earn (speedup 47×→91×→70×→94×→122×→150×; 18f dip is median-inflation from long-garbage gen tokens, not cache-reuse failure). H3/H3'/H3''/H3'''/H3''''/H3''''' all earn (prefix ≥0.99). H4/H4'/H4''/H4'''/H4''''/H4''''' all earn (peak RSS ≤ 4.2 GB). H2/H2' earn at 8f/16f; **H2''/H2'''/H2''''/H2''''' REJECT at 32f/24f/20f/18f on 7B**. 18f is mid-ramp with 4-basin diversity (Δ = −0.238). 20f is mid-ramp with 2-basin dominance (Δ = −0.381). 24f/32f saturate to 14/14 `addCriterion` (Δ = −0.429). **3B cross-arch 20f: H2-3B.matched (Δ = −0.048); 3B cross-arch 24f: H2-3B-24.shifted-ramp (Δ = −0.190, inside (−0.30, −0.05)); 3B cross-arch 32f: H2-3B-32.plateaued (Δ = −0.190, inside (−0.25, −0.10] — most-surprising pre-registered sub-outcome; Δacc numerically identical to 24f, 3B saturated ~2.3× shallower than 7B). All three 3B runs: 28/28 follow-ups emit clean 2-token letter answers — no addCriterion, no long-garbage, ever. **7B/20f temperature probe: H1-temp 117×, H2-temp.distribution-collapse EARNED (Δacc=−0.429 ✓, basin=0.571 ✓; H2-temp.greedy-commit FALSIFIED on both conditions). H3-temp prefix 0.993, H4-temp RSS 1.61 GB. Temperature + min-p redistribute basin mass WITHIN the pathological-attractor set (plain `addCriterion` 9→4; Java-code `addCriterion(…)` 4→4 rigid; novel `自动生成` 0→5; clean letter 1→1 unchanged) — 7B basin is distribution-level, not sampler-level.** **3B/20f temperature probe: H1-3B-temp 130.8×, H2-3B-temp.null-robust EARNED on both preregistered conditions (Δacc=−0.095 ∈ [−0.15, +0.05] ✓ AND 14/14 clean-letter follow-ups ≥ 12/14 ✓); H2-3B-temp.hidden-basin FALSIFIED (0/14 non-letter follow-ups); H2-3B-temp.sampler-dispersion NOT TRIGGERED (inside envelope). H3-3B-temp prefix 0.993, H4-3B-temp RSS 2.36 GB. Δacc temperature-shift is exactly 1/21 (−0.048 → −0.095) — identical noise-floor signature to 7B probe. 3B clean-letter distribution is sampler-invariant; temperature shuffles argmax on a few queries but NEVER exposes non-letter content.** Three-dimensional mechanism decomposition FINALIZED AND TEMPERATURE-VERIFIED AT BOTH CEILINGS: threshold onset (capacity-modulated), saturation ceiling (architecture-specific), failure geometry (architecture-specific AT DISTRIBUTION LEVEL on both 7B and 3B — distribution-level sampler-invariance is cross-architecture).**
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
    Sam's 0.8 s (Gemma 4 26B / M5 Max) to 15 ms at 8f/16f.
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
    conditions); novel Chinese `自动生成` 0→5; clean letter 1→1
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
    addCriterion(…)Java, 自动生成} plus a thin clean tail; they do not
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
    7B share the same basin geometry; onset depth scales ~1.6×
    with parameter count (7B ~8k at 20f; 3B ~16k at 40f). The
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
  runtime_estimate: 0h executed; ~2-4h fork + smoke test to unblock (Option A in findings doc); ~30-60min run once driver is correctness-preserving
  notes: Discovered during pre-run driver verification 2026-04-20. The prereg's assumption of drop-in mlx-vlm compatibility was wrong — Gemma 4's sliding-window attention architecture is fundamentally incompatible with linear-cache prefix truncation. Three options documented (A: cache-type-aware fork with RotatingKVCache.is_trimmable() guard, B: partial-layer cache reuse losing most speedup, C: prefix ≤ 512 tokens = non-starter for video). Recommended disposition: DO NOT run with current driver (would produce plausible-looking garbage on silent-wrong-answer path); defer behind 1.55D (Qwen-only, known-compatible); revisit after 1.55D or rescope to Gemma 2 (non-sliding) as cross-family target. Paper Claim #14 (3-D decomposition) remains Qwen-family-only this draft; cross-family generalization declared an open question with explicit mlx-vlm sliding-window caveat.

- phase_id: 1.55D
  status: infrastructure-falsified (v1 driver; prereg retained for re-run after fork or rescope)
  authoritative_note: research/experiments/2026/2026-04-20-phase-1_55D-selective-reprefill-v1-driver-findings.md
  authoritative_artifacts: []
  current_best_policy: n/a
  supersedes: []
  paper_relevance: deferred (fidelity-recovery lever remains open; claim matrix declares as open infrastructure question)
  prereg_outcome: v1 driver (`scripts/run_kv_selective_reprefill.py`) runs Q1 cold-start correctly (68.5s prefill on 8094 tokens, correct=True on clip 037) but crashes deterministically on Q2 in `mlx_vlm/models/qwen2_5_vl/language.py:296` with `ValueError: [broadcast_shapes] Shapes (8119) and (1672) cannot be broadcast`. Root cause: mlx-vlm's generate path does not co-slice `pixel_values`/`image_grid_thw`/`attention_mask` when `PromptCacheState.find_prefix_length` trims `input_ids` to a tail that still contains image tokens (partial image-block reuse). 1.55A avoided this because its shared prefix always included the full image block (triggering `pixel_values = None`). H1/H2/H3/H4 UNTESTED.
  runtime_estimate: 0h experimentally meaningful executed; ~3-5h Option A fork (mlx-vlm multimodal auxiliary co-slicing + smoke test); ~30min Option C rescope (text-only selective re-prefill prereg variant); ~1h run once driver correctness-preserving
  notes: Discovered 2026-04-20 on K=4 pilot. Parallel infrastructure finding to 1.55C: both 1.55C and 1.55D surface distinct limitations of mlx-vlm's multimodal prefix-cache reuse path (1.55C: RotatingKVCache type-blindness; 1.55D: auxiliary-tensor co-slicing gap). Three paths to actionability documented: Option A (faithful fork, ~3-5h), Option B (manual cache injection, untested may still hit broadcast), Option C (text-only selective re-prefill as scientifically weaker variant). Recommended disposition: defer behind 1.51V vision-tower pruning and 1.51R focused dev sweep (independent code paths, not blocked by mlx-vlm prefix-reuse contract); 1.55D returns via Option A fork or Option C rescope. Paper impact: fidelity-recovery lever declared as open infrastructure question with explicit mlx-vlm multimodal prefix-reuse caveat alongside 1.55C's sliding-window caveat.

- phase_id: 1.55B
  status: proposed (deferred)
  authoritative_note: research/experiments/2026/2026-04-19-phase-1_55B-persistent-kv-decode-composition-prereg.md
  authoritative_artifacts: []
  current_best_policy: n/a
  supersedes: []
  paper_relevance: secondary (composition of persistent-KV with 1.54 decode-accel toward Sam's 1.8× long-clip aggregate)
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
  notes: Codex-round-21 hypothesis extending Sam's system. Three H: signal beats pixel-MEAN at matched compute, random-ablation rules out correlate-of-activity, signal needs lower refresh rate at matched accuracy. Paper language constrained to "VLM-signaled" until Phase 1.44 lands; no "confidence-conditioned" framing until earned.

- phase_id: 1.57
  status: findings-landed (Qwen complete; Gemma path deferred)
  authoritative_note: research/experiments/2026/2026-04-19-phase-1_57-feature-drift-findings.md
  authoritative_artifacts:
    - research/experiments/2026/artifacts/phase1_57/qwen_8f_dev30.json
    - research/experiments/2026/artifacts/phase1_57/qwen_16f_dev30.json
    - research/experiments/2026/artifacts/phase1_57/qwen_32f_dev30.json
  current_best_policy: n/a
  supersedes: []
  paper_relevance: primary (feature-drift mechanism; three-frame sweep landed on Qwen 7B-4bit; adjudicates the 16f→32f long-bucket plateau via drift-accuracy co-saturation)
  prereg_outcome: Qwen 8f/16f/32f landed on videomme_dev_v1 n=30. H2 FALSIFIED (STATIC cos 0.562/0.607/0.638, all below [0.95, 1.00] prereg band). H3 EARNED under adjacent-frame measurement (monotonic rise). Per-bucket stratification reveals attention-mixing ceiling is bucket-dependent. Cross-ref to 1.41 rejects H-drift-compounds (long-bucket), supports H-saturation. Gemma path deferred (needs inline ViT encode wiring). H1/H4 NOT TESTED.
  runtime_estimate: ~45-60min total (Gemma + Qwen, 8/16/32 frames × N items, feature-tap extraction only — no generation)
  notes: Qwen side landed 2026-04-19. Measurement methodology is adjacent-frame fresh-vs-fresh (not Sam's cache-substitute); findings doc documents the reason and the lower-bound interpretation. Per-bucket drift co-saturates with per-bucket accuracy at 16f on long bucket — empirical support for H-saturation over H-drift-compounds for the long-bucket plateau. Short-bucket drift still accelerating at 32f while short-bucket acc is flat — drift is co-indicator, not binding constraint. Gemma deferred, 1.58 (bf16) still open.

- phase_id: 1.58
  status: proposed (deferred)
  authoritative_note: research/experiments/2026/2026-04-19-phase-1_58-bf16-quantization-ablation-prereg.md
  authoritative_artifacts: []
  current_best_policy: n/a
  supersedes: []
  paper_relevance: secondary (quantization × long-context — one of three candidate mechanisms for the 16f long-bucket regression)
  prereg_outcome: (deferred; gated on bf16 Qwen 2.5-VL-7B checkpoint download ~15 GB + feasibility check on 16 GB Mac)
  runtime_estimate: ~50-60min bf16 8f n=30 + ~2.5-3h bf16 16f n=30 + matched 4bit re-runs if needed; total ~3.5-4h once bf16 checkpoint is local
  notes: Tests H-C (4bit × long-context) from the 2026-04-19 16f findings. Four pre-registered H: H1 long-bucket quantization gap ≥ +0.20, H2 no short-bucket gap, H3 RSS < 14 GB, H4 prefill ~4× ratio. Discriminator for the 16f non-monotonic finding; complementary to Phase 1.57 (feature-drift). Wrapper + analyzer landed 2026-04-22 in `scripts/run_phase1_58_bf16_control.sh` and `scripts/analyze_phase1_58_bf16_control.py`; remaining blockers are checkpoint availability and RSS feasibility.

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
  status: proposed (preregistered 2026-04-21; queued after EXP10 n=60 + cross-arch Qwen C-VISION probe)
  authoritative_note: research/experiments/2026/2026-04-21-phase-1_60-scroll-pan-subset-prereg.md
  authoritative_artifacts: []
  current_best_policy: n/a (regime-boundary probe, not a policy selection)
  supersedes: []
  paper_relevance: secondary (closes the codex round-24/25 "where does C-VISION break" gap; graceful-degradation branch is paper-body-bound; broken-deployment branch gates scroll-detection bail-out policy 1.60c)
  prereg_outcome: (pending; four hypotheses — H_vision_scroll_breaks, H_vision_scroll_v_red_drops, H_vision_scroll_acc_holds, H_vision_scroll_ceiling_holds — with three promotion branches: CLEAN FAILURE CLAIM / BROKEN DEPLOYMENT CLAIM / SHIFTED-DOES-NOT-BREAK)
  runtime_estimate: ~70 min point (~90 min upper bound): 20 items × 8 f × 2 arms, Gemma 4-E4B-4bit, medium-duration content to avoid long-bucket blowout
  notes: Subset construction: 20 items stratified 7 light / 7 medium / 6 heavy scroll intensity, drawn from VideoMME (existing pixel-diff statistic), augmented with synthesized constant-velocity-crop clips if natural items are insufficient. Reuses scripts/run_novelty_pruning_gemma.py with $VT_FLAGS (L=2, kr_V=0.50); no driver changes. Thermal gate same as sessions 3–5: |decode Δ| < max(0.02 × decode_ms, 100 ms). 2026-04-22 curation tooling landed in `scripts/run_phase1_60_curation_audit.sh` and `scripts/build_phase1_60_scroll_pan_candidates.py`; remaining blocker is choosing the actual subset, not writing the ranking path. Future follow-ups: 1.60b (egomotion/FPV subset), 1.60c (scroll-detection bail-out policy if BROKEN DEPLOYMENT branch earns), 1.60d (cross-architecture scroll/pan on Qwen).
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

## Forward-queue runtime budget (benchmark wall-clock only)

Only counts dense-generate + pruned-generate passes; excludes
implementation, debugging, analysis, and CI time. Estimates are at
8-frame regime unless noted; scale ~4× for 32-frame.

| phase | status | runtime at 8f | runtime at 32f | blocked on |
|-------|--------|---------------|----------------|------------|
| 1.57  | proposed — P1 **first** | ~45-60min (all frame counts, feature-tap only, no generation) | (same run covers 8/16/32) | scripts/measure_feature_drift.py (scaffold planned; no fork needed) |
| 1.55A | proposed — P1 **second** | ~17min (7 items × 3 queries, 4bit Qwen) | n/a (short-bucket only) | scripts/run_kv_cache_session.py (uses existing mlx-vlm PromptCacheState) |
| 1.56  | deferred-design — P2 **third** | ~45min | ~2h | Phase 1.44 margin logging + RefreshPolicy API |
| 1.52R | pending | ~2-3h | ~6-8h | 1.42 + 1.51R sweep completion |
| 1.55B | deferred | ~65min (composition + controls) | ~2.5h | 1.54 landing + 1.55A earning |
| 1.58  | deferred | ~1h bf16 8f | ~3h bf16 16f (no 32f) | bf16 Qwen checkpoint download (~15 GB), RSS feasibility |
| 1.59  | research_note | n/a on M3 Air | n/a on M3 Air | external hardware |
| 1.30  | P2 | ~2h (3 clips × 3 policies) | n/a | 1.26 + 1.27 + 1.29 infra; P2 now |
| 1.55  | superseded | — | — | — (replaced by 1.55A/1.55B) |

**Bottom-line forward benchmark time**: ~7-9h at 8f, ~15-18h at
32f, to clear the Codex round-21 + 16f-follow-up forward queue
end-to-end (assuming all gating implementation and checkpoint
downloads land first; that work is NOT included here — user
asked for runtime only).
