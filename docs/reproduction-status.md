# Whitepaper Reproduction Status

This file tracks which imported whitepaper claims are reproduced locally on this
repo and machine, which are only partially supported, and which remain
imported-only.

Canonical imported target:

- use [seed/whitepaper/whitepaper.md](../seed/whitepaper/whitepaper.md) as the
  repo's corrected internal reference for the imported whitepaper
- do not treat the original historical PDF wording as the source of truth

Current bottom line:

- reproduced locally: the Track A substrate, a narrow synthetic
  answer-stability slice, a narrow real-video slice, and supportive hosted
  MVBench benchmark evidence
- not reproduced locally yet: the whitepaper's mechanism section at imported
  strength, TOMATO on this stack, refresh drift, and any Track B speedup or
  compression headline
- mechanism interpretation currently compares a local `MLX 4-bit` path against
  an imported `PyTorch/MPS float32` whitepaper path; treat remaining gaps as
  stack-specific until a higher-precision local follow-up lands
- benchmark interpretation is different: the imported benchmark path is also
  Qwen `7B` via `mlx-vlm`, so local benchmark caveats are subset policy,
  quantization, package revision, and preprocessing rather than a generic
  runtime-family mismatch

## Status Table

| Whitepaper area | Current status | Prereg outcome | Local evidence | Next required step |
| --- | --- | --- | --- | --- |
| Dense-path determinism and cache-path transparency | Reproduced locally | Accepted | [2026-04-13-phase-0_5-feasibility.md](../research/experiments/2026/2026-04-13-phase-0_5-feasibility.md), [2026-04-13-phase-0_75-cache-identity.md](../research/experiments/2026/2026-04-13-phase-0_75-cache-identity.md), and [2026-04-14-phase-1_46-benchmark-path-controls.md](../research/experiments/2026/2026-04-14-phase-1_46-benchmark-path-controls.md) now cover both the local bring-up path and a direct Qwen `7B` benchmark-runner identity smoke | Keep as Track A control for later runs |
| §2.1 exact ViT output identity on two re-encodes | Reproduced locally | Inconclusive in `1.1`, strengthened by `1.15` | [2026-04-13-phase-1_1-direct-mechanism-reproduction.md](../research/experiments/2026/2026-04-13-phase-1_1-direct-mechanism-reproduction.md) plus [2026-04-13-phase-1_15-mechanism-probe-repair.md](../research/experiments/2026/2026-04-13-phase-1_15-mechanism-probe-repair.md) both keep repeated-image identity exact | keep as a direct mechanistic control |
| §2.2 partial-change attention locality | Partial only | Inconclusive | [2026-04-13-phase-1_1-direct-mechanism-reproduction.md](../research/experiments/2026/2026-04-13-phase-1_1-direct-mechanism-reproduction.md) plus [2026-04-13-phase-1_15-mechanism-probe-repair.md](../research/experiments/2026/2026-04-13-phase-1_15-mechanism-probe-repair.md) show that the earlier mismatch was partly probe design, but the repaired local MLX `4-bit` probe still misses the target-neighborhood and far-field acceptance bands from the imported PyTorch/MPS `float32` story | compare the repaired probes on a higher-precision local runtime before treating the mismatch as conceptual disagreement |
| §2.3 localized motion preserves embeddings | Partial only | Inconclusive | [2026-04-13-phase-1_1-direct-mechanism-reproduction.md](../research/experiments/2026/2026-04-13-phase-1_1-direct-mechanism-reproduction.md) plus [2026-04-13-phase-1_15-mechanism-probe-repair.md](../research/experiments/2026/2026-04-13-phase-1_15-mechanism-probe-repair.md) show that the catastrophic `8 px` collapse was mostly a boundary artifact, but the repaired `8 px` and `14 px` shifts still remain weaker than the imported whitepaper-strength local-shift story on the local MLX `4-bit` path | run a precision/runtime comparison, then decide whether the remaining gap is stack-specific or method-specific |
| §2.4 scored real-video quality slice | Reproduced locally, narrow | Accepted with caveat | [2026-04-13-phase-1_3-crosscheck-real-video-slice.md](../research/experiments/2026/2026-04-13-phase-1_3-crosscheck-real-video-slice.md) contains a `6`-item endpoint-oriented real-video slice on the predecessor cross-check clips with `6/6` dense and `6/6` cached accuracy on Qwen `3B`; this is a generalized slice, not the imported real-video suite shape | expand beyond endpoint scene facts, then connect the result to TOMATO and MVBench |
| §2.5 TOMATO agreement on Qwen 7B | Partial only | Inconclusive on the `30`-item subset | [2026-04-13-phase-1_4-tomato-benchmark-subset.md](../research/experiments/2026/2026-04-13-phase-1_4-tomato-benchmark-subset.md), [2026-04-14-phase-1_45-benchmark-diagnostics.md](../research/experiments/2026/2026-04-14-phase-1_45-benchmark-diagnostics.md), [2026-04-14-phase-1_46-benchmark-path-controls.md](../research/experiments/2026/2026-04-14-phase-1_46-benchmark-path-controls.md), and [2026-04-14-phase-1_47-benchmark-first-frame-ablation.md](../research/experiments/2026/2026-04-14-phase-1_47-benchmark-first-frame-ablation.md) show that the local benchmark-native TOMATO path is online, parser-stable, and cache-path-transparent on the MLX `7B` stack, but the first `30`-item subset reached only `0.833` agreement and the first-frame ablation collapsed from `0.300` to `0.067`, which points toward real temporal dependence rather than prompt-prior collapse | keep TOMATO as the primary diagnosis lane: targeted planner and refresh sweeps on the disagreement items, then revisit larger reruns only if those controls materially change the result |
| §2.6 MVBench agreement slice | Reproduced locally, weaker than imported | Accepted on the `54`-item hosted subset | [2026-04-13-phase-1_5-mvbench-benchmark-subset.md](../research/experiments/2026/2026-04-13-phase-1_5-mvbench-benchmark-subset.md), [2026-04-14-phase-1_45-benchmark-diagnostics.md](../research/experiments/2026/2026-04-14-phase-1_45-benchmark-diagnostics.md), [2026-04-14-phase-1_46-benchmark-path-controls.md](../research/experiments/2026/2026-04-14-phase-1_46-benchmark-path-controls.md), and [2026-04-14-phase-1_47-benchmark-first-frame-ablation.md](../research/experiments/2026/2026-04-14-phase-1_47-benchmark-first-frame-ablation.md) show that the hosted predecessor-style MVBench slice is runnable locally and that the first `54` hosted items reach `0.870` agreement with zero parse failures; dense and cached are statistically indistinguishable on this slice (`3` improvements, `2` regressions, exact paired `p = 1.0`), while the first-frame ablation stays relatively high at `0.519`, which supports a content-conditioned contrast rather than a parser-driven one | keep the hosted-slice caveat explicit, then use MVBench as the broader-content comparator while TOMATO remains the harder diagnosis target |
| Talking-head redundancy regime | Reproduced locally, generalized | Accepted | [2026-04-13-phase-1_0b-matched-content-redundancy.md](../research/experiments/2026/2026-04-13-phase-1_0b-matched-content-redundancy.md) measures the predecessor talking-head cross-check clip locally and keeps it in the high-reuse regime | add scored real-video items on talking-head content, then benchmark-native runs |
| Surveillance redundancy regime | Reproduced locally, generalized | Accepted | [2026-04-13-phase-1_0b-matched-content-redundancy.md](../research/experiments/2026/2026-04-13-phase-1_0b-matched-content-redundancy.md) measures the predecessor surveillance cross-check clip locally, with `xiph_hall_monitor_cif` added as a stable surveillance-like anchor | add scored real-video items and keep the stable proxy separate from the predecessor clip |
| FPV / egomotion redundancy regime | Reproduced locally, generalized | Accepted | [2026-04-13-phase-1_0b-matched-content-redundancy.md](../research/experiments/2026/2026-04-13-phase-1_0b-matched-content-redundancy.md) measures the predecessor FPV cross-check clip locally and reproduces the low-reuse ordering qualitatively | add scored real-video items, then refresh-drift and benchmark-native runs |
| Refresh-interval drift / 14-frame tolerance | Partial only | Accepted on the targeted `direction` subset | [2026-04-14-phase-1_49-tomato-direction-refresh-sweep.md](../research/experiments/2026/2026-04-14-phase-1_49-tomato-direction-refresh-sweep.md) shows that the current TOMATO `direction` failures are refresh-sensitive on the local `7B` stack: no-refresh cached accuracy is `0.2`, while refresh intervals `1`, `2`, and `4` all recover to exact dense agreement on the five-item subset | run a broader refresh sweep beyond the `direction` slice before treating the imported `14`-frame tolerance claim as reproduced |
| Q-table spatial correlation | Imported only | N/A | Q-table helpers exist, but no local correlation note or artifact is checked in | run local pre-filter correlation study |
| Track A synthetic answer stability under same-position reuse | Reproduced locally, narrow | Accepted in `v1`, Accepted in `1.05`, Re-interpreted after ablation | [2026-04-13-track-a-local-pilot.md](../research/experiments/2026/2026-04-13-track-a-local-pilot.md), [2026-04-13-track-a-local-pilot-v2.md](../research/experiments/2026/2026-04-13-track-a-local-pilot-v2.md), and [2026-04-13-phase-1_05-temporal-necessity-ablation.md](../research/experiments/2026/2026-04-13-phase-1_05-temporal-necessity-ablation.md) together show one canonical cached failure plus prompt-prior contamination in several apparent v2 passes | use the discriminating subset, add natural-video middle-event items, then run threshold sweeps |
| Track B skipped-compute, wall-clock, or compression headlines | Not reproduced | N/A | current local work is intentionally Track A only | build the in-memory timing path and sparse-execution path before claiming speedup |

## Interpretation Rules

- `Reproduced locally` means the repo contains a local note plus local artifact
  supporting the claim on this machine and stack.
- `Partial only` means the repo reproduces a close corollary, proxy, or content
  class, but not the exact imported claim.
- `Imported only` means the repo still depends on seed material or predecessor
  evidence.
- `Not reproduced` means the repo intentionally has not attempted the claim yet,
  usually because it belongs to Track B rather than Track A.
- `Prereg outcome` records what the local experiment contract actually said.
  Narrative terms such as `partial reproduction` do not override an
  `Inconclusive` preregistration outcome.

## What To Do Next

If the goal is honest whitepaper reproduction rather than new method work, the
highest-leverage next steps are:

1. add benchmark-path identity on the Qwen `7B` TOMATO and MVBench runner
2. extend the real-video slice beyond endpoint scene facts so natural middle-event items are explicit
3. compare the repaired mechanism probes on a higher-precision runtime before treating the weaker numbers as real disagreement
4. rerun broader refresh sweeps beyond the five-item TOMATO `direction` slice before claiming a stable drift story
