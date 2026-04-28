---
phase: 1.63H
date: 2026-04-29
parent: research/experiments/2026/2026-04-27-phase-1_63E-16f-catastrophic-findings.md
related:
  - research/experiments/2026/2026-04-27-phase-1_63E-track-b-frame-scaling-prereg.md
  - research/experiments/2026/2026-04-27-phase-1_63E-8f-findings.md
status: 1.63H 16f kr-sweep complete; kr=0.85 passes fidelity + format + ceiling gates with Δacc=-0.050 (CI95 touches 0). Safe Qwen Track B operating point at 16f bracketed.
---

# Phase 1.63H — Qwen 16f Track B keep-rate sweep (FINDINGS)

**Verdict.** The catastrophic 1.63E 16f result at L=2, kr=0.50 (Δacc=-0.42, 22 parse failures) is configuration-fragile, not architecture-fundamental. A kr-sweep at the same frame budget recovers fidelity monotonically: kr=0.65 → 0.75 → 0.85 produces Δacc=-0.28 → -0.10 → -0.05, parse failures 11 → 0 → 0, choice agreement 47% → 75% → 82%. **kr=0.85 is the safe Qwen 16f Track B operating point** — fidelity, format, and ceiling gates all pass. The cost is small: the conservative kr trades the 46% vision reduction at kr=0.50 for 14% reduction at kr=0.85, and the E2E speedup drops from 1.13× (catastrophic-fidelity) to 1.03× (clean-fidelity).

## Headline numbers, n=60 paired against the 1.63E dense_16f reference

| kr | Δaccuracy | CI95 | Choice agreement | Sparse parse failures | Vision reduction | E2E speedup | Predicted ceiling | Gap | Gates passed |
|---|---|---|---|---|---|---|---|---|---|
| 0.50 (1.63E) | -0.417 | [-0.55, -0.28] | 36.7% | **22** | 46.4% | 1.132× | 1.074× | +0.058 | **3/6** |
| 0.65 | -0.283 | [-0.42, -0.15] | 46.7% | 11 | 36.1% | 1.093× | 1.057× | +0.036 | 4/6 |
| 0.75 | -0.100 | [-0.22, +0.02] | 75.0% | **0** | 27.0% | 1.065× | 1.042× | +0.023 | 5/6 |
| **0.85** | **-0.050** | **[-0.15, +0.05]** | **81.7%** | **0** | **13.6%** | **1.032×** | **1.021×** | **+0.011** | **5/6** |
| 1.00 (dense) | 0.000 | n/a | 100.0% | 0 | 0% | 1.000× | n/a | n/a | n/a |

By bucket at kr=0.85:

| Bucket | Δacc | Vision share | Vision red | E2E actual | Predicted | Gap |
|---|---|---|---|---|---|---|
| short (n=20) | -0.050 | 26.2% | 8.8% | 1.038× | 1.024× | +0.014 |
| medium (n=20) | -0.100 | 20.3% | 0.7% | 0.977× | 1.001× | -0.024 |
| long (n=20) | **0.000** | 8.5% | 32.3% | 1.055× | 1.028× | +0.027 |

The medium-bucket vision_red 0.7% is the conservative path's near-degenerate point — at kr=0.85 the sparse Qwen path is barely doing different work than dense. Long bucket holds vision reduction (32%) because longer sequences benefit more from drop-back proportionally; long-bucket fidelity is perfect (Δ 0.000).

## Why this matters for the paper

The 1.63E 16f catastrophic point made it look like Track B is frame-budget-fragile on Qwen at any setting. The kr-sweep replaces that one-point conclusion with a clean monotonic curve: there is a continuous safe-operating envelope, and the boundary on Qwen 16f is between kr=0.75 and kr=0.85 (at kr=0.75 fidelity narrowly misses by 5pp; at kr=0.85 it lands within tolerance).

This converts the C-VISION story from a binary "works at 8f, breaks at 16f" claim to a configuration-conditional one: **"Qwen Track B works across frame budgets when kr is set conservatively; the safe kr depends on frame count."** That is exactly the kind of nuance reviewers want.

Cross-arch contrast remains:
- **Gemma**: robust at L=2 kr=0.50 across 8f/16f/32f (0/60 paired drift in all three)
- **Qwen 8f**: works at kr=0.50 with bounded fidelity loss (Δ -0.067)
- **Qwen 16f**: requires kr ≥ 0.85 for fidelity preservation
- **Qwen 16f kr=0.50**: instruction-following collapse (boundary result, useful for paper)

The paper can frame this as: "C-VISION works as a configuration envelope; the safe operating envelope depends on architecture, frame budget, and pruning aggressiveness."

## Mechanism interpretation

The trajectory of parse failures (22 → 11 → 0 → 0) and choice agreement (37% → 47% → 75% → 82%) correlates monotonically with kr. At kr=0.50, dropping half of merged-token groups removes too much answer-relevant information for the LM to follow the multiple-choice format. Higher kr preserves more of the visual evidence; the LM stays on its prompt-format manifold; the C-CEILING arithmetic model holds tighter (gap +0.058 → +0.036 → +0.023 → +0.011).

This is consistent with the 1.55E Q3 catastrophe pattern (instruction-following collapse under aggressive cache disturbance) and with Codex's earlier guidance: kr=0.50 is too aggressive for any 16f+ Qwen setting on this manifest.

## Paper integration

1. **Update C-VISION envelope language** in abstract and intro: not "works at all configurations", but "works within a measured envelope (architecture × frame budget × kr)".
2. **Add 1.63H sweep table** to the C-VISION results section as the configuration-fragility evidence.
3. **Replace the 1.63E 16f catastrophic point as the "Track B fails" sentence** with the more useful "Track B at kr=0.85 16f is fidelity-safe with 1.032× E2E gain", and use 1.63E 16f kr=0.50 as a frontier-of-aggressiveness sentence.
4. **Cite the kr-sweep recovery curve** as the cleanest evidence the failure mode is configuration-fragile, not implementation-broken.

## Limits and follow-ups

- This sweep is Qwen-only at 16f. Gemma's safe-operating envelope across kr is not measured (Gemma was zero-drift at kr=0.50 across all frame budgets, so kr-sweep is less informative on Gemma).
- 20f and 32f Qwen kr-sweep would be the natural extension. The 16f kr=0.85 point predicts a kr-sweep at 20f/32f would shift the safe boundary further toward higher kr, with smaller absolute E2E gains. Worth doing if a reviewer asks; not needed for the current paper version.
- The 1.66 memory-cap implementation (`mx.set_memory_limit(12 * 1024**3)`) successfully kept the entire ~17h restart run kernel-panic-free; CVE-2026-28834 mitigation worked.
