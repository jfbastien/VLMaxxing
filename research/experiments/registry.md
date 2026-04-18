# Experiment Registry (Machine-Readable)

Last updated: 2026-04-17

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
  status: proposed
  authoritative_note: research/experiments/2026/2026-04-16-phase-1_41-videomme-lane.md
  authoritative_artifacts:
    - scripts/build_videomme_manifest.py
  current_best_policy: n/a
  supersedes: []
  paper_relevance: primary (VideoMME breadth gate, claim #8)
  prereg_outcome: (pending; runs after 1.37 dev; VideoMME loader + manifest builder landed)
  notes: VideoMME videos are hosted on Hugging Face at `lmms-lab/Video-MME` as 20 chunked zip archives (~101 GB full corpus); paper protocol only needs 57 unique videoIDs (dev+holdout manifests, one overlap). Use `scripts/fetch_videomme_subset.py` to walk chunks one-at-a-time and extract only wanted videoIDs (peak disk ~5 GB staging + ~3-15 GB extracted subset). See `docs/videomme-download-handoff.md` for environment gotchas (HF xet backend must be disabled; SOCKS proxy env vars must be cleared).

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

- phase_id: 1.51
  status: running
  authoritative_note: research/experiments/2026/2026-04-17-phase-1_51-novelty-pruning-gemma-prereg.md
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
  current_best_policy: n/a (pilot null — end-to-end 1.01× vs 1.8× prereg gate; mechanism verified correct, claim #11 magnitude is arithmetically bounded by vision+decode share on E4B)
  supersedes: []
  paper_relevance: primary (claim #11 Gemma novelty-pruning; now trending toward publishable preregistered null with mechanistic explanation)
  prereg_outcome: (pilot n=1 NULL 2026-04-18: 1.01× e2e on videomme:long:669-1 at kr=0.5 arm=none; ceiling formula `(D+V+G)/(D+V+G/s)` predicts 1.18× max even at s=∞; Stage 1 n=30 scale-up running, Stages 2-3 queued)
  notes: phase is tracked as the "1.51R" fresh driver across other docs (R = Reproduction of Sam's novelty-pruning, fresh code path that does not consume `_mix_gemma_features`). Preregistered 5 literature-grounded anchor-preservation arms (FastV, FasterVLM/HiPrune, Nüwa pillar, VLM-Pruner max-min diversity, IVC-Prune-spirit Gemma-structural); keep-rate grid {0.3..0.7}; must run on Gemma (not Qwen) because Qwen's M-RoPE-V ties token index to 2D grid position and breaks under token drop. cls_attention_proxy arm is explicitly excluded from winner promotion (see PROMOTABLE_ARMS in novelty_pruning.py). Pilot reveals vision-tower pruning (NEW phase 1.51V, task #87) is the only mechanism that could reach Sam's ≥1.8× end-to-end on E4B; queued as follow-up.

- phase_id: 1.52
  status: proposed
  authoritative_note: research/experiments/2026/2026-04-17-phase-1_52-combined-temporal-spatial-prereg.md
  authoritative_artifacts: []
  current_best_policy: n/a
  supersedes: []
  paper_relevance: primary (multiplicative composition — temporal reuse AND novelty-pruning stacked — paper-table headline number)
  prereg_outcome: (pending; blocked on 1.42 and 1.51 passes)
  notes: three-way gate preregistered (multiplicative / additive / interference); PoRe (arxiv 2508.17807) reserved for phase 1.53 if 1.52 passes
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
