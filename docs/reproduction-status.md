# Pre-release source Reproduction Status

This file tracks which pre-release source claims are reproduced locally on this
repo and machine, which are only partially supported, and which remain
imported-only.

Ledger scope:

- `docs/claim-register.md` defines imported pre-release targets.
- This file records reproduction/import status for those targets.
- `research/experiments/registry.md` records per-phase execution state.
- `paper/claim-matrix.md` is the paper-facing claim ledger.

Canonical imported targets:

- **Original pre-release source**: the frozen target for WP-2.1 through WP-5.
- **Revised pre-release source (2026-04-16)**: adds VideoMME (WP-2.7),
  strict-parse audit (WP-2.8), cross-arch (WP-2.9), thinking amplification
  (WP-2.10), wall-clock (WP-4.1), and composition (WP-5.1). See
  [claim-register.md](claim-register.md) for the full table.
- Do not treat either document as the source of truth for what we
  claim locally; use this status table and the claim register.
- Raw seed files are not kept in the release tree. Git history preserves them;
  this file records their current reproduction status.

Current bottom line:

- reproduced locally: the Track A substrate, a narrow synthetic
  answer-stability slice, a narrow real-video slice, supportive hosted MVBench
  benchmark evidence, a generalized Qwen VideoMME lane, and bounded measured
  sparse-vision evidence on the local hardware stack
- not reproduced locally yet: the pre-release source's mechanism section at imported
  strength, full TOMATO at imported cardinality, refresh drift, imported Gemma
  26B scale-out, and the imported compression/throughput headline. A local
  measured sparse-execution envelope now exists, but it is hardware- and
  model-conditioned boundary evidence rather than a reproduction of the M5
  stackup.
- mechanism interpretation currently compares a local `MLX 4-bit` path against
  an imported `PyTorch/MPS float32` pre-release source path; treat remaining gaps as
  stack-specific until a higher-precision local follow-up lands
- benchmark interpretation is different: the imported benchmark path is also
  Qwen `7B` via `mlx-vlm`, so local benchmark caveats are subset policy,
  quantization, package revision, and preprocessing rather than a generic
  runtime-family mismatch

## Status Table

| Pre-release source area | Current status | Prereg outcome | Local evidence | Next required step |
| --- | --- | --- | --- | --- |
| Dense-path determinism and cache-path transparency | Reproduced locally | Accepted | [2026-04-13-phase-0_5-feasibility.md](../research/experiments/2026/2026-04-13-phase-0_5-feasibility.md), [2026-04-13-phase-0_75-cache-identity.md](../research/experiments/2026/2026-04-13-phase-0_75-cache-identity.md), and [2026-04-14-phase-1_46-benchmark-path-controls.md](../research/experiments/2026/2026-04-14-phase-1_46-benchmark-path-controls.md) now cover both the local bring-up path and a direct Qwen `7B` benchmark-runner identity smoke | Keep as Track A control for later runs |
| §2.1 exact ViT output identity on two re-encodes | Reproduced locally | Inconclusive in `1.1`, strengthened by `1.15` | [2026-04-13-phase-1_1-direct-mechanism-reproduction.md](../research/experiments/2026/2026-04-13-phase-1_1-direct-mechanism-reproduction.md) plus [2026-04-13-phase-1_15-mechanism-probe-repair.md](../research/experiments/2026/2026-04-13-phase-1_15-mechanism-probe-repair.md) both keep repeated-image identity exact | keep as a direct mechanistic control |
| §2.2 partial-change attention locality | Partial only | Inconclusive | [2026-04-13-phase-1_1-direct-mechanism-reproduction.md](../research/experiments/2026/2026-04-13-phase-1_1-direct-mechanism-reproduction.md) plus [2026-04-13-phase-1_15-mechanism-probe-repair.md](../research/experiments/2026/2026-04-13-phase-1_15-mechanism-probe-repair.md) show that the earlier mismatch was partly probe design, but the repaired local MLX `4-bit` probe still misses the target-neighborhood and far-field acceptance bands from the imported PyTorch/MPS `float32` story | compare the repaired probes on a higher-precision local runtime before treating the mismatch as conceptual disagreement |
| §2.3 localized motion preserves embeddings | Partial only | Inconclusive | [2026-04-13-phase-1_1-direct-mechanism-reproduction.md](../research/experiments/2026/2026-04-13-phase-1_1-direct-mechanism-reproduction.md) plus [2026-04-13-phase-1_15-mechanism-probe-repair.md](../research/experiments/2026/2026-04-13-phase-1_15-mechanism-probe-repair.md) show that the catastrophic `8 px` collapse was mostly a boundary artifact, but the repaired `8 px` and `14 px` shifts still remain weaker than the pre-release source-strength local-shift story on the local MLX `4-bit` path | run a precision/runtime comparison, then decide whether the remaining gap is stack-specific or method-specific |
| §2.4 scored real-video quality slice | Reproduced locally, narrow | Accepted with caveat | [2026-04-13-phase-1_3-crosscheck-real-video-slice.md](../research/experiments/2026/2026-04-13-phase-1_3-crosscheck-real-video-slice.md) contains a `6`-item endpoint-oriented real-video slice on the predecessor cross-check clips with `6/6` dense and `6/6` cached accuracy on Qwen `3B`; this is a generalized slice, not the imported real-video suite shape | expand beyond endpoint scene facts, then connect the result to TOMATO and MVBench |
| §2.5 TOMATO agreement on Qwen 7B | Partial only | Inconclusive on the `30`-item subset | [2026-04-13-phase-1_4-tomato-benchmark-subset.md](../research/experiments/2026/2026-04-13-phase-1_4-tomato-benchmark-subset.md), [2026-04-14-phase-1_45-benchmark-diagnostics.md](../research/experiments/2026/2026-04-14-phase-1_45-benchmark-diagnostics.md), [2026-04-14-phase-1_46-benchmark-path-controls.md](../research/experiments/2026/2026-04-14-phase-1_46-benchmark-path-controls.md), [2026-04-14-phase-1_47-benchmark-first-frame-ablation.md](../research/experiments/2026/2026-04-14-phase-1_47-benchmark-first-frame-ablation.md), and [2026-04-14-phase-1_8-motion-frame-budget-baselines.md](../research/experiments/2026/2026-04-14-phase-1_8-motion-frame-budget-baselines.md) show that the local benchmark-native TOMATO path is online, that strict and loose rescoring matched on the saved `30`-item slice with `0` parse failures, and that cache-path transparency controls exist on the MLX `7B` stack; the first-frame ablation collapsed from `0.300` to `0.067`, and matched motion-slice frame-budget baselines show a real dev budget win for `mean + max_age = 4` that does not yet survive cleanly on holdout | keep TOMATO as the primary diagnosis lane: targeted planner and refresh sweeps on the disagreement items, then revisit larger reruns only if those controls materially change the result |
| §2.6 MVBench agreement slice | Reproduced locally, weaker than imported | Accepted on the `54`-item hosted subset | [2026-04-13-phase-1_5-mvbench-benchmark-subset.md](../research/experiments/2026/2026-04-13-phase-1_5-mvbench-benchmark-subset.md), [2026-04-14-phase-1_45-benchmark-diagnostics.md](../research/experiments/2026/2026-04-14-phase-1_45-benchmark-diagnostics.md), [2026-04-14-phase-1_46-benchmark-path-controls.md](../research/experiments/2026/2026-04-14-phase-1_46-benchmark-path-controls.md), [2026-04-14-phase-1_47-benchmark-first-frame-ablation.md](../research/experiments/2026/2026-04-14-phase-1_47-benchmark-first-frame-ablation.md), and [2026-04-14-phase-1_9-mvbench-motion-frame-budget-baselines.md](../research/experiments/2026/2026-04-14-phase-1_9-mvbench-motion-frame-budget-baselines.md) show that the hosted predecessor-style MVBench slice is runnable locally, that the first `54` hosted items reach `0.870` agreement with zero parse failures, and that the MVBench motion dense frame-budget curve peaks at `4` frames (`0.733`) and is non-monotonic in frame count (`8` frames drops to `0.600`); dense and cached are statistically indistinguishable on the original `54`-item slice (`3` improvements, `2` regressions, exact paired `p = 1.0`), while the first-frame ablation stays relatively high at `0.519`, which supports a content-conditioned contrast rather than a parser-driven one | keep the hosted-slice caveat explicit, then use MVBench as the broader-content comparator while TOMATO remains the harder diagnosis target |
| Revised §2.7 VideoMME evaluation | Generalized local reproduction, not strict imported scale-out | Accepted with caveat | [2026-04-18-phase-1_41-qwen-videomme-baseline-findings.md](../research/experiments/2026/2026-04-18-phase-1_41-qwen-videomme-baseline-findings.md), [2026-04-19-phase-1_41-qwen-videomme-16f-findings.md](../research/experiments/2026/2026-04-19-phase-1_41-qwen-videomme-16f-findings.md), [2026-04-19-phase-1_41-qwen-videomme-32f-long-findings.md](../research/experiments/2026/2026-04-19-phase-1_41-qwen-videomme-32f-long-findings.md), and [2026-04-21-phase-1_41-qwen-videomme-16f-holdout-findings.md](../research/experiments/2026/2026-04-21-phase-1_41-qwen-videomme-16f-holdout-findings.md) reproduce a local Qwen VideoMME lane across 8f/16f/32f dev plus 16f holdout; 32f is not Pareto-efficient and the long-bucket dev regression does not replicate on holdout | do not present as the imported 300-question or Gemma 26B result; use claim-matrix row 8 for paper-facing status |
| Revised §2.9 cross-architecture generalization | Generalized locally, split | Accepted with caveat | [2026-04-24-phase-1_42-gemma-findings.md](../research/experiments/2026/2026-04-24-phase-1_42-gemma-findings.md) shows Gemma 4 E4B TOMATO motion N=30 passes strict agreement while MVBench N=30 preserves aggregate accuracy but fails strict agreement; [2026-04-24-phase-1_57-gemma-feature-drift-findings.md](../research/experiments/2026/2026-04-24-phase-1_57-gemma-feature-drift-findings.md) shows corrected Gemma cached-feature geometry and higher long-bucket adjacent-frame cosine than Qwen | frame as an architecture- and benchmark-conditioned spectrum, not a strict imported 26B reproduction |
| Talking-head redundancy regime | Reproduced locally, generalized | Accepted | [2026-04-13-phase-1_0b-matched-content-redundancy.md](../research/experiments/2026/2026-04-13-phase-1_0b-matched-content-redundancy.md) measures the predecessor talking-head cross-check clip locally and keeps it in the high-reuse regime | add scored real-video items on talking-head content, then benchmark-native runs |
| Surveillance redundancy regime | Reproduced locally, generalized | Accepted | [2026-04-13-phase-1_0b-matched-content-redundancy.md](../research/experiments/2026/2026-04-13-phase-1_0b-matched-content-redundancy.md) measures the predecessor surveillance cross-check clip locally, with `xiph_hall_monitor_cif` added as a stable surveillance-like anchor | add scored real-video items and keep the stable proxy separate from the predecessor clip |
| FPV / egomotion redundancy regime | Reproduced locally, generalized | Accepted | [2026-04-13-phase-1_0b-matched-content-redundancy.md](../research/experiments/2026/2026-04-13-phase-1_0b-matched-content-redundancy.md) measures the predecessor FPV cross-check clip locally and reproduces the low-reuse ordering qualitatively | add scored real-video items, then refresh-drift and benchmark-native runs |
| Refresh-interval drift / 14-frame tolerance | Partial only | Accepted on the targeted `direction` subset | [2026-04-14-phase-1_49-tomato-direction-refresh-sweep.md](../research/experiments/2026/2026-04-14-phase-1_49-tomato-direction-refresh-sweep.md) shows that the current TOMATO `direction` failures were refresh-sensitive on the local `7B` stack and this five-item subset: no-refresh cached accuracy is `0.2`, while refresh intervals `1`, `2`, and `4` all recover to exact dense agreement there | run a broader refresh sweep beyond the `direction` slice before treating the imported `14`-frame tolerance claim as reproduced |
| Q-table spatial correlation | Imported only | N/A | Q-table helpers exist, but no local correlation note or artifact is checked in | run local pre-filter correlation study |
| Track A synthetic answer stability under same-position reuse | Reproduced locally, narrow | Accepted in `v1`, Accepted in `1.05`, Re-interpreted after ablation | [2026-04-13-track-a-local-pilot.md](../research/experiments/2026/2026-04-13-track-a-local-pilot.md), [2026-04-13-track-a-local-pilot-v2.md](../research/experiments/2026/2026-04-13-track-a-local-pilot-v2.md), and [2026-04-13-phase-1_05-temporal-necessity-ablation.md](../research/experiments/2026/2026-04-13-phase-1_05-temporal-necessity-ablation.md) together show one canonical cached failure plus prompt-prior contamination in several apparent v2 passes | use the discriminating subset, add natural-video middle-event items, then run threshold sweeps |
| Measured sparse-execution wall-clock boundary | Partially reproduced locally | Mixed / bounded | local measured sparse-vision runs now skip timed vision-tower work: Gemma 1.63G has a clean 32f-short operating point at 1.316x with no paired drift in that cell, while Qwen 1.63E/H exposes a keep-rate/fidelity boundary and a conservative 16f kr=0.85 point at 1.032x | broaden to a fidelity-preserving sparse-backend curve before claiming a general compression/speed headline |

## Interpretation Rules

- `Reproduced locally` means the repo contains a local note plus local artifact
  supporting the claim on this machine and stack.
- `Partial only` means the repo reproduces a close corollary, proxy, or content
  class, but not the exact imported claim.
- `Imported only` means the repo still depends on external imported evidence
  recorded in the claim register rather than local artifacts.
- `Not reproduced` means the repo intentionally has not attempted the claim yet
  or has only landed a bounded proxy rather than the imported claim.
- `Prereg outcome` records what the local experiment contract actually said.
  Narrative terms such as `partial reproduction` do not override an
  `Inconclusive` preregistration outcome.

## What To Do Next

If the goal is honest pre-release source reproduction rather than new method work, the
highest-leverage next steps are:

1. ✅ ~~add benchmark-path identity on the Qwen `7B` TOMATO and MVBench runner~~
   — done in phase 1.46 ([2026-04-14-phase-1_46-benchmark-path-controls.md](../research/experiments/2026/2026-04-14-phase-1_46-benchmark-path-controls.md))
2. extend the real-video slice beyond endpoint scene facts so natural middle-event items are explicit
3. compare the repaired mechanism probes on a higher-precision runtime before treating the weaker numbers as real disagreement
4. rerun broader refresh sweeps beyond the five-item TOMATO `direction` slice before claiming a stable drift story

### 2026-04-16 update

The project has moved from "reproduction with diagnosis" into "early
method discovery." The current paper-facing paths (not repro paths)
are:

- Phase 1.20 TOMATO N=30 enlargement — **COMPLETED 2026-04-17**
  (base policy 0.333 @ 3.55 effective fresh frames; ties uniform
  dense-8 at 44 % of fresh-frame budget on clean tree)
- Phase 1.21 MVBench N=30 enlargement — **COMPLETED 2026-04-17**
  (base policy 0.600 @ 4.06; strict Pareto win vs dense-6 on clean
  tree; the older sticky4 refinement is retained as historical supplementary
  evidence only and is not part of the current paper-facing evidence set)
- Phase 1.26 sticky-dynamic planner — **COMPLETED 2026-04-16**
  (helps MVBench holdout; hurts TOMATO motion dev; explanatory
  variable = placement, not quantity)
- Phase 1.27 projector-group mask completion — **COMPLETED 2026-04-14**
- Phase 1.50 dense timing baseline — **LOCAL HISTORICAL DIAGNOSTIC**
  (n=10 dev + N=30 holdout on both benchmarks; raw timing outputs lived under
  ignored `results/track_b/`). Use checked phase 1.63E/G/H artifacts for current
  paper-facing measured sparse-vision claims.
- Phase 1.34 novelty-ranked dense baseline — **LOCAL DIAGNOSTIC COMPLETED 2026-04-17**
  (2×3 grid N=30 recorded in the phase note; raw outputs lived under ignored
  `results/`, so regenerate or materialize them before treating the comparison
  as paper-body evidence).
- Phase 1.36 feature-change oracle — **LOCAL DIAGNOSTIC COMPLETED 2026-04-17**
  (best pixel stat Pearson r=0.233 to r=0.504; content-conditional). Raw outputs
  lived under ignored `results/feature_change_oracle/`, so regenerate or
  materialize them before treating the exact values as paper-body evidence.
- Phase 1.37B neighbor-halo veto — **RETIRED 2026-04-17** as a
  preregistered null. Both dev benchmarks NO-LIFT under the frozen
  promotion rule (full 9/9 cells × 2 benchmarks). On TOMATO motion
  dev_v2 N=30, control cached_accuracy 0.233 is rank-1 and within
  0.034 of every cell — halo-veto moves only agreement (0.833 →
  0.867–0.933) at the cost of fresh-frame budget (3.77 → 4.20–6.58)
  with MRU 1/30 = 0.033, so all nine cells sit inside one item of
  noise on the primary metric. On MVBench halo HURTS accuracy:
  control is rank-1 (0.800) and 7/8 halo cells lose 0.067–0.100 —
  the highest-agreement cells drain most fresh frames. No holdout
  run. Code (`NeighborHaloVetoConfig`, `apply_neighbor_halo_veto`)
  stays in the harness behind the config gate but is no longer a
  candidate for winner promotion. See
  `research/experiments/2026/2026-04-17-phase-1_37B-neighbor-halo-veto-prereg.md`
  and artifact `halo_analysis.json`.
- Phase 1.41 VideoMME lane — **EARNED LOCALLY / GENERALIZED 2026-04-21**:
  Qwen2.5-VL-7B-Instruct-4bit local VideoMME dev at 8f/16f/32f plus 16f holdout. The dev
  long-bucket regression is split-specific and did not replicate on holdout;
  32f is not Pareto-efficient.
- Phase 1.42 Gemma architecture-topology lane — **COMPLETED SPLIT 2026-04-24**:
  Gemma E4B TOMATO motion holdout passes strict agreement, MVBench preserves
  aggregate accuracy but fails strict agreement. Use as a spectrum/boundary
  result, not a universal Gemma pass.
- Phase 1.51V first-pass vision pruning — **COMPLETED 2026-04-21**:
  bounded Gemma first-pass evidence on VideoMME/MVBench/TOMATO with
  share-limited speedups and benchmark-specific clean/advisory labels.
- Phase 1.57 Gemma feature-drift — **COMPLETED 2026-04-24**:
  corrected Gemma pooled cached-feature geometry (`133` tokens/frame) and
  higher long-bucket adjacent-frame cosine than Qwen; still a lower-bound
  adjacent-frame proxy, not true cache-substitute measurement.
- Phase 1.63E/G/H measured sparse-vision execution — **COMPLETED / BOUNDED
  2026-04-29**: real skipped vision-tower work exists. Gemma supplies the
  cleanest positive cell; Qwen supplies the aggressive-keep-rate failure and
  conservative aggregate/format boundary. Broad sparse backend and sparse LM
  prefill remain open.

The original §2.5 TOMATO and §2.6 MVBench reproduction rows remain "partial" /
"weaker than imported." Later generalized evidence above changes the local
paper surface, especially VideoMME and measured sparse-vision, but it does not
retroactively make the original imported TOMATO/MVBench claims strict
reproductions.
