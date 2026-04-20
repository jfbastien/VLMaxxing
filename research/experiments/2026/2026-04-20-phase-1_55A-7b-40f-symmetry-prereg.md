# Phase 1.55A — 7B 40f basin-symmetry probe (PREREG)

**Date:** 2026-04-20. **Status:** preregistration.
**Parent:** `2026-04-20-phase-1_55A-3b-40f-deeper-plateau-findings.md`
and the 7B frame-scaling ramp (8f→32f on Qwen 2.5-VL-7B-Instruct-4bit).

## Problem statement

The 3B 40f probe (2026-04-20) invalidated the prior "saturation
ceiling" interpretation of Claim #14 and revised the 3-D
decomposition to **shifted-onset same-basin**: 3B and 7B share a
basin structure, and onset depth scales ~1.6× with parameter count
(7B basin at ~8k tokens / 20f; 3B basin at ~16k tokens / 40f).

This probe tests the revision **symmetrically** on 7B. If 7B
already saturated by 24f (Δacc=−0.429 across 24f/32f), does
pushing 7B to 40f (~16.1k prefill, double the 20f onset) expose a
**novel attractor class** beyond the established
`addCriterion` / `自动生成` set — or does the 7B basin stay
closed on the same attractor identity?

Two outcomes are paper-relevant:

1. **Symmetric (no novel attractor at 40f):** 7B at 40f reproduces
   Δacc ≈ −0.43 with follow-ups landing in the SAME basin set
   (`addCriterion` dominant, plus light Java-code / `自动生成`
   variants). Strengthens the shifted-onset claim — the basin, once
   entered, is depth-invariant.

2. **Asymmetric (novel attractor at 40f):** 7B Δacc worse than
   −0.50 OR ≥4/14 follow-ups landing in a qualitatively-new
   attractor class (empty-response, non-addCriterion non-Chinese
   tokens, or a new degeneracy pattern). Opens a **dimension 4**
   for the mechanism: within-basin structure is depth-dependent.

## Parameters

- **Model:** Qwen 2.5-VL-7B-Instruct-4bit.
- **Frame count:** 40.
- **Clips:** 7 short-bucket VideoMME clips (037, 100, 116, 120,
  158, 160, 210) × 3 Qs = 21 queries.
- **Decoding:** greedy (T=0.0), max_tokens=64 (same as prior 7B
  runs, to allow full attractor emergence — shorter would mask
  long-garbage patterns).
- **Driver:** `scripts/run_kv_cache_session.py` (unchanged).
- **Output dir:**
  `research/experiments/2026/artifacts/phase1_55A_7b_40f_symmetry/`.

## Hypotheses

**H1-7B-40f.symmetric (primary):** Δacc ∈ [−0.55, −0.35] AND
≥10/14 session follow-ups land in the established 7B basin set
{`addCriterion`, `addCriterion(…)` Java-code, `自动生成` Chinese,
long-garbage repetition}. **Earns** the "basin-closed-under-depth"
interpretation; strengthens Claim #14's shifted-onset revision.

**H1-7B-40f.novel (primary, competing):** Δacc worse than −0.55 OR
≥4/14 follow-ups land in a qualitatively-NEW attractor (empty-
response, non-letter non-addCriterion non-Chinese tokens, new
repetition class). **Earns** the "within-basin structure is depth-
dependent" interpretation; requires a 4-D decomposition.

**H2-7B-40f (secondary, speedup):** Speedup ≥ 140× (monotonic
extrapolation from 32f=150×). Follow-up median ≤ 1200 ms.
**Falsification:** speedup < 100× → 7B prefill-dominance model
breaks at this depth, scientifically interesting.

**H3-7B-40f (tertiary, RSS):** Peak RSS ≤ 8 GB. **Falsification:**
RSS > 12 GB → caveat footnote only.

## Attractor identity tally (to populate post-run)

| Attractor class                                | Count |
|------------------------------------------------|-------|
| Plain `addCriterion` (short)                   | TBD   |
| `addCriterion(…)` Java-code method-chain       | TBD   |
| `自动生成` Chinese auto-generate               | TBD   |
| Long-garbage repetition (> 16 gen tokens)      | TBD   |
| Empty-response (`generation_tokens=1`)          | TBD   |
| Clean 2-token letter (any)                     | TBD   |
| Novel non-letter class (describe)              | TBD   |

## Runtime estimate

Based on 7B 32f (~163s first-query × 14 = ~38min; speedup 150×
→ follow-up ~1s × 14 = ~15s; processor overhead ~5-10min;
total ~50 min).

40f extrapolation (~20% deeper than 32f):
- First-query ~200s × 14 = ~47 min
- Follow-ups ~1.3s × 14 = ~18s
- Processor + overhead ~5-10 min
- **Total: ~60-70 min.**

## Falsification decision tree

- **H1-symmetric + H2 earn:** claim #14 shifted-onset
  interpretation strengthened with 40f symmetry datapoint;
  proceed to 36f/48f interpolation probes if time permits.
- **H1-novel earns:** write findings doc; revise Claim #14 to
  four-dimensional (threshold × onset-depth × basin-identity ×
  within-basin-depth-structure). Preregister a follow-up 48f
  probe to map the within-basin evolution.
- **H2 alone fails:** note "deep-prefill 7B speedup anomaly";
  does not change basin-identity claim.
- **H3 alone fails:** footnote.

## What this probe does NOT test

- 3B 36f onset-depth interpolation (separate prereg pending,
  task #141).
- 3B 40f temperature probe (separate prereg pending, reopen
  condition h).
- Gemma cross-family (blocked on 1.55C infra).
- Selective re-prefill at 40f (blocked on 1.55D infra).

## Artifact paths (to be populated)

- Findings doc (post-run):
  `...-7b-40f-symmetry-findings.md`.
- Session/baseline JSONL + summary.json:
  `research/experiments/2026/artifacts/phase1_55A_7b_40f_symmetry/`.
- Run log: same dir, `run.log`.
