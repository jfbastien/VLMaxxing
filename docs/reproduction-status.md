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

## Status Table

| Whitepaper area | Current status | Local evidence | Next required step |
| --- | --- | --- | --- |
| Dense-path determinism and cache-path transparency | Reproduced locally | [2026-04-13-phase-0_5-feasibility.md](../research/experiments/2026/2026-04-13-phase-0_5-feasibility.md), [2026-04-13-phase-0_75-cache-identity.md](../research/experiments/2026/2026-04-13-phase-0_75-cache-identity.md) | Keep as Track A control for later runs |
| §2.1 exact ViT output identity on two re-encodes | Reproduced locally | [2026-04-13-phase-1_1-direct-mechanism-reproduction.md](../research/experiments/2026/2026-04-13-phase-1_1-direct-mechanism-reproduction.md) | keep as a direct mechanistic control |
| §2.2 partial-change attention locality | Partial only | [2026-04-13-phase-1_1-direct-mechanism-reproduction.md](../research/experiments/2026/2026-04-13-phase-1_1-direct-mechanism-reproduction.md) plus [2026-04-13-phase-1_15-mechanism-probe-repair.md](../research/experiments/2026/2026-04-13-phase-1_15-mechanism-probe-repair.md) show that the earlier mismatch was partly probe design, but the repaired local MLX `4-bit` probe still misses the target-neighborhood and far-field acceptance bands | compare the repaired probes on a higher-precision local runtime before treating the mismatch as conceptual disagreement |
| §2.3 localized motion preserves embeddings | Partial only | [2026-04-13-phase-1_1-direct-mechanism-reproduction.md](../research/experiments/2026/2026-04-13-phase-1_1-direct-mechanism-reproduction.md) plus [2026-04-13-phase-1_15-mechanism-probe-repair.md](../research/experiments/2026/2026-04-13-phase-1_15-mechanism-probe-repair.md) show that the catastrophic `8 px` collapse was mostly a boundary artifact, but the repaired `8 px` and `14 px` shifts still remain weaker than the imported whitepaper-strength local-shift story | run a precision/runtime comparison, then decide whether the remaining gap is stack-specific or method-specific |
| §2.4 scored real-video quality slice | Imported only | current scored pilot is synthetic-only | run a scored natural-video slice after repairing divergence-capable items |
| §2.5 TOMATO agreement on Qwen 7B | Imported only | imported predecessor TOMATO artifacts are present under `seed/original_repo/results/`, but no local TOMATO assets or benchmark-native run exists yet on this stack | build benchmark-native adapter and run a documented local reproduction slice |
| §2.6 MVBench agreement slice | Imported only | imported predecessor MVBench artifacts are present under `seed/original_repo/results/`, but no local MVBench assets or local benchmark run exists yet on this stack | build MVBench adapter after the TOMATO path exists |
| Talking-head redundancy regime | Partial only | [2026-04-13-phase-1_0-local-redundancy.md](../research/experiments/2026/2026-04-13-phase-1_0-local-redundancy.md) reproduces a very high-reuse talking-head proxy on `xiph_akiyo_cif` | add matched content-class proxies and the predecessor cross-check clips |
| Surveillance redundancy regime | Imported only | no local surveillance-class proxy measured yet | add a stable surveillance-like clip and rerun redundancy table |
| FPV / egomotion redundancy regime | Imported only | no local FPV-like or predecessor FPV cross-check measured yet | add a stable high-motion proxy and rerun redundancy table |
| Refresh-interval drift / 14-frame tolerance | Imported only | no local refresh sweep yet | run refresh-interval sweep on the hard natural buckets |
| Q-table spatial correlation | Imported only | Q-table helpers exist, but no local correlation note or artifact is checked in | run local pre-filter correlation study |
| Track A synthetic answer stability under same-position reuse | Reproduced locally, narrow | [2026-04-13-track-a-local-pilot.md](../research/experiments/2026/2026-04-13-track-a-local-pilot.md), [2026-04-13-track-a-local-pilot-v2.md](../research/experiments/2026/2026-04-13-track-a-local-pilot-v2.md), and [2026-04-13-phase-1_05-temporal-necessity-ablation.md](../research/experiments/2026/2026-04-13-phase-1_05-temporal-necessity-ablation.md) together show one real cached failure plus prompt-prior contamination in several v2 passes | use the discriminating subset, add natural-video scored items, then run threshold sweeps |
| Track B skipped-compute, wall-clock, or compression headlines | Not reproduced | current local work is intentionally Track A only | build the in-memory timing path and sparse-execution path before claiming speedup |

## Interpretation Rules

- `Reproduced locally` means the repo contains a local note plus local artifact
  supporting the claim on this machine and stack.
- `Partial only` means the repo reproduces a close corollary, proxy, or content
  class, but not the exact imported claim.
- `Imported only` means the repo still depends on seed material or predecessor
  evidence.
- `Not reproduced` means the repo intentionally has not attempted the claim yet,
  usually because it belongs to Track B rather than Track A.

## What To Do Next

If the goal is honest whitepaper reproduction rather than new method work, the
highest-leverage next steps are:

1. finish the temporal-necessity cleanup so the discriminating subset is explicit
2. repair the local mechanism probes before treating the weaker numbers as real disagreement
3. add scored natural-video items before broad threshold sweeps
4. add surveillance and FPV-like content-class proxies to the local corpus
5. run refresh-interval drift on the hardest natural buckets
6. build benchmark-native TOMATO and MVBench paths only after the local Track A
   foundation is complete
