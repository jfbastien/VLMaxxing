# Whitepaper Reproduction Status

This file tracks which imported whitepaper claims are reproduced locally on this
repo and machine, which are only partially supported, and which remain
imported-only.

Canonical imported target:

- use [seed/whitepaper/whitepaper.md](../seed/whitepaper/whitepaper.md) as the
  repo's corrected internal reference for the imported whitepaper
- do not treat the original historical PDF wording as the source of truth

Current bottom line:

- reproduced locally: the Track A substrate and a narrow synthetic
  answer-stability slice
- not reproduced locally yet: the whitepaper's mechanism section in direct
  feature space, the scored natural-video suite, TOMATO, MVBench, refresh
  drift, and any Track B speedup or compression headline
- mechanism interpretation currently compares a local `MLX 4-bit` path against
  an imported `PyTorch/MPS float32` whitepaper path; treat remaining gaps as
  stack-specific until a higher-precision local follow-up lands

## Status Table

| Whitepaper area | Current status | Prereg outcome | Local evidence | Next required step |
| --- | --- | --- | --- | --- |
| Dense-path determinism and cache-path transparency | Reproduced locally | Accepted | [2026-04-13-phase-0_5-feasibility.md](../research/experiments/2026/2026-04-13-phase-0_5-feasibility.md), [2026-04-13-phase-0_75-cache-identity.md](../research/experiments/2026/2026-04-13-phase-0_75-cache-identity.md) | Keep as Track A control for later runs |
| §2.1 exact ViT output identity on two re-encodes | Reproduced locally | Inconclusive in `1.1`, strengthened by `1.15` | [2026-04-13-phase-1_1-direct-mechanism-reproduction.md](../research/experiments/2026/2026-04-13-phase-1_1-direct-mechanism-reproduction.md) plus [2026-04-13-phase-1_15-mechanism-probe-repair.md](../research/experiments/2026/2026-04-13-phase-1_15-mechanism-probe-repair.md) both keep repeated-image identity exact | keep as a direct mechanistic control |
| §2.2 partial-change attention locality | Partial only | Inconclusive | [2026-04-13-phase-1_1-direct-mechanism-reproduction.md](../research/experiments/2026/2026-04-13-phase-1_1-direct-mechanism-reproduction.md) plus [2026-04-13-phase-1_15-mechanism-probe-repair.md](../research/experiments/2026/2026-04-13-phase-1_15-mechanism-probe-repair.md) show that the earlier mismatch was partly probe design, but the repaired local MLX `4-bit` probe still misses the target-neighborhood and far-field acceptance bands from the imported PyTorch/MPS `float32` story | compare the repaired probes on a higher-precision local runtime before treating the mismatch as conceptual disagreement |
| §2.3 localized motion preserves embeddings | Partial only | Inconclusive | [2026-04-13-phase-1_1-direct-mechanism-reproduction.md](../research/experiments/2026/2026-04-13-phase-1_1-direct-mechanism-reproduction.md) plus [2026-04-13-phase-1_15-mechanism-probe-repair.md](../research/experiments/2026/2026-04-13-phase-1_15-mechanism-probe-repair.md) show that the catastrophic `8 px` collapse was mostly a boundary artifact, but the repaired `8 px` and `14 px` shifts still remain weaker than the imported whitepaper-strength local-shift story on the local MLX `4-bit` path | run a precision/runtime comparison, then decide whether the remaining gap is stack-specific or method-specific |
| §2.4 scored real-video quality slice | Reproduced locally, narrow | Accepted with caveat | [2026-04-13-phase-1_3-crosscheck-real-video-slice.md](../research/experiments/2026/2026-04-13-phase-1_3-crosscheck-real-video-slice.md) contains a `6`-item endpoint-oriented real-video slice on the predecessor cross-check clips with `6/6` dense and `6/6` cached accuracy on Qwen `3B`; this is a generalized slice, not the imported real-video suite shape | expand beyond endpoint scene facts, then connect the result to TOMATO and MVBench |
| §2.5 TOMATO agreement on Qwen 7B | Imported only | N/A | imported predecessor TOMATO artifacts are present under `seed/original_repo/results/`, but no local TOMATO assets or benchmark-native run exists yet on this stack | build benchmark-native adapter and run a documented generalized local reproduction slice |
| §2.6 MVBench agreement slice | Imported only | N/A | imported predecessor MVBench artifacts are present under `seed/original_repo/results/`, but no local MVBench assets or local benchmark run exists yet on this stack | build MVBench adapter after the TOMATO path exists |
| Talking-head redundancy regime | Reproduced locally, generalized | Accepted | [2026-04-13-phase-1_0b-matched-content-redundancy.md](../research/experiments/2026/2026-04-13-phase-1_0b-matched-content-redundancy.md) measures the predecessor talking-head cross-check clip locally and keeps it in the high-reuse regime | add scored real-video items on talking-head content, then benchmark-native runs |
| Surveillance redundancy regime | Reproduced locally, generalized | Accepted | [2026-04-13-phase-1_0b-matched-content-redundancy.md](../research/experiments/2026/2026-04-13-phase-1_0b-matched-content-redundancy.md) measures the predecessor surveillance cross-check clip locally, with `xiph_hall_monitor_cif` added as a stable surveillance-like anchor | add scored real-video items and keep the stable proxy separate from the predecessor clip |
| FPV / egomotion redundancy regime | Reproduced locally, generalized | Accepted | [2026-04-13-phase-1_0b-matched-content-redundancy.md](../research/experiments/2026/2026-04-13-phase-1_0b-matched-content-redundancy.md) measures the predecessor FPV cross-check clip locally and reproduces the low-reuse ordering qualitatively | add scored real-video items, then refresh-drift and benchmark-native runs |
| Refresh-interval drift / 14-frame tolerance | Imported only | N/A | no local refresh sweep yet | run refresh-interval sweep on the hard natural buckets |
| Q-table spatial correlation | Imported only | N/A | Q-table helpers exist, but no local correlation note or artifact is checked in | run local pre-filter correlation study |
| Track A synthetic answer stability under same-position reuse | Reproduced locally, narrow | Accepted in `v1`, Accepted in `1.05`, Re-interpreted after ablation | [2026-04-13-track-a-local-pilot.md](../research/experiments/2026/2026-04-13-track-a-local-pilot.md), [2026-04-13-track-a-local-pilot-v2.md](../research/experiments/2026/2026-04-13-track-a-local-pilot-v2.md), and [2026-04-13-phase-1_05-temporal-necessity-ablation.md](../research/experiments/2026/2026-04-13-phase-1_05-temporal-necessity-ablation.md) together show one canonical cached failure plus prompt-prior contamination in several apparent v2 passes | use the discriminating subset, add natural-video scored items, then run threshold sweeps |
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

1. extend the real-video slice beyond endpoint scene facts so natural middle-event items are explicit
2. compare the repaired mechanism probes on a higher-precision runtime before treating the weaker numbers as real disagreement
3. run threshold sweeps on the discrimination-safe synthetic subset plus the real-video slice
4. run refresh-interval drift on the hardest natural buckets
5. build TOMATO and MVBench adapters with the local hardware caveats stated up front
