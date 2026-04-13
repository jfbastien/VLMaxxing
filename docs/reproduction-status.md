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
| §2.1 exact ViT output identity on two re-encodes | Partial only | end-to-end bit-identical dense outputs imply a strong corollary, but the direct feature-space measurement is not yet checked in | run direct feature comparison on repeated image encodes |
| §2.2 partial-change attention locality | Imported only | no local per-token locality measurement yet | run localized perturbation study and measure token-wise cosine by distance |
| §2.3 localized motion preserves embeddings | Imported only | no local shift-versus-similarity study yet | run local shift sweep on Qwen 3B features |
| §2.4 scored real-video quality slice | Imported only | current scored pilot is synthetic-only | run a scored natural-video slice after repairing divergence-capable items |
| §2.5 TOMATO agreement on Qwen 7B | Imported only | no TOMATO assets or local benchmark run yet | build benchmark-native adapter and run a labeled local reproduction slice |
| §2.6 MVBench agreement slice | Imported only | no MVBench assets or local benchmark run yet | build MVBench adapter after TOMATO path exists |
| Talking-head redundancy regime | Partial only | [2026-04-13-phase-1_0-local-redundancy.md](../research/experiments/2026/2026-04-13-phase-1_0-local-redundancy.md) reproduces a very high-reuse talking-head proxy on `xiph_akiyo_cif` | add matched content-class proxies and the predecessor cross-check clips |
| Surveillance redundancy regime | Imported only | no local surveillance-class proxy measured yet | add a stable surveillance-like clip and rerun redundancy table |
| FPV / egomotion redundancy regime | Imported only | no local FPV-like or predecessor FPV cross-check measured yet | add a stable high-motion proxy and rerun redundancy table |
| Refresh-interval drift / 14-frame tolerance | Imported only | no local refresh sweep yet | run refresh-interval sweep on the hard natural buckets |
| Q-table spatial correlation | Imported only | Q-table helpers exist, but no local correlation note or artifact is checked in | run local pre-filter correlation study |
| Track A synthetic answer stability under same-position reuse | Reproduced locally, narrow | [2026-04-13-track-a-local-pilot.md](../research/experiments/2026/2026-04-13-track-a-local-pilot.md), [2026-04-13-track-a-local-pilot-v2.md](../research/experiments/2026/2026-04-13-track-a-local-pilot-v2.md) | keep the stronger v2 suite, then add natural-video scored items and threshold sweeps |
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

1. repair the local scored suite so at least one item is divergence-capable
2. reproduce the direct mechanism claims in feature space on Qwen 3B
3. add surveillance and FPV-like content-class proxies to the local corpus
4. run refresh-interval drift on the hardest natural buckets
5. build benchmark-native TOMATO and MVBench paths only after the local Track A
   foundation is complete
