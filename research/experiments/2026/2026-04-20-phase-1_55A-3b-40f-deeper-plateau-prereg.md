# Phase 1.55A — 3B 40f deeper-plateau probe (PREREG)

**Date:** 2026-04-20. **Status:** preregistration.
**Parent:** `2026-04-19-phase-1_55A-persistent-kv-findings.md` and the
3B saturation-mapping finding at 32f (Δacc=−0.19, plateau confirmed
across 24f and 32f).

## Problem statement

Phase 1.55A established that Qwen 2.5-VL-3B-Instruct-4bit hits a
saturation plateau at Δacc ≈ −0.19 from 24f onward (2.3× shallower
ceiling than 7B's Δacc=−0.43). The 32f datapoint (~12.9k prefill
tokens) was numerically identical to the 24f datapoint (10/21
session, 14/21 baseline). The temperature probe at 20f further
established that the 3B distribution is genuinely clean-letter-
dominant and sampler-invariant.

**Reopen condition (f) in registry:** "deeper-prefill 3B runs (40f+,
~16k tokens) expose a latent basin that 20/24/32f does not."

This probe tests the plateau claim at a third depth: 40f ≈ 16.4k
prefill tokens (~27% deeper than 32f). Either outcome is paper-
valuable:

1. **Plateau holds (Δacc ≈ −0.19, 14/14 clean-letter):** 3B's
   saturation ceiling is now empirically confirmed across 10k, 13k,
   and 16k prefill tokens — strengthens the architectural-ceiling
   interpretation in Claim #14. The 3-D decomposition's dimension-2
   (saturation ceiling = architecture-specific) becomes a
   3-data-point claim on 3B.

2. **Basin emerges (Δacc worse than −0.25 OR ≥2/14 non-letter
   follow-ups):** 3B has a latent second threshold that 20/24/32f
   did not expose. Invalidates the "saturation plateau" claim and
   forces a rewrite of 3B's mechanism as "delayed onset, same
   basin-structure as 7B but shifted rightward." Weaker than the
   current paper claim but still scientifically valid (and more
   interesting).

## Parameters

- **Model:** Qwen 2.5-VL-3B-Instruct-4bit.
- **Frame count:** 40.
- **Clips:** 7 short-bucket VideoMME clips (same as prior 1.55A runs:
  037, 100, 116, 120, 158, 160, 210) × 3 Qs = 21 queries.
- **Decoding:** greedy (T=0.0), max_tokens=2 (same as greedy 3B 20f/
  24f/32f runs).
- **Driver:** `scripts/run_kv_cache_session.py` (unchanged from prior
  3B runs).
- **Output dir:**
  `research/experiments/2026/artifacts/phase1_55A_3b_40f_deeper_plateau/`.

## Hypotheses (2 primary, 1 secondary)

**H1-3B-40f.plateau (primary):** At 40f, Δacc ∈ [−0.25, −0.10] AND
≥12/14 clean 2-token letter follow-ups. **Earns** the plateau
extension claim.

**H1-3B-40f.latent-basin (primary, competing):** At 40f, Δacc worse
than −0.25 OR ≥3/14 non-letter follow-ups (any attractor emergence).
**Earns** the "shifted basin onset" revision and falsifies the
plateau claim.

**H2-3B-40f (secondary, speedup):** Speedup ≥ 150× (monotonic
extrapolation from 32f=213×; 40f should give ≥220× given prefill-
dominance). Follow-up median ≤ 700 ms. **Falsification:** speedup
< 100× → prefill-dominance model breaks at this depth on 3B, which
would itself be a novel finding.

**H3-3B-40f (tertiary, RSS):** Peak RSS ≤ 8 GB. **Falsification:**
RSS > 12 GB → experiment is not fully repeatable on the 16 GB
machine class; flag as caveat.

## Runtime estimate

Based on 3B 32f (50 min wall time, 100s per first-query, 213×
speedup):
- First-query at 40f: ~135s × 14 (7 session + 7 baseline) = ~31 min
- Follow-ups: 14 queries × 0.5 s = 7 s
- Processor + overhead: ~5-10 min
- **Total: ~40-50 min.**

## Falsification decision tree

- H1-plateau earns AND H2-speedup earns → plateau claim extended to
  3rd depth, speedup scaling confirmed; paper Claim #14 strengthened.
- H1-latent-basin earns → write findings doc; revise Claim #14 to
  acknowledge a second threshold on 3B; preregister further probes at
  48f, 56f to map the onset.
- H2-speedup alone fails → note as "deep-prefill 3B speedup
  anomaly"; does not affect the fidelity claim.
- H3-RSS alone fails → footnote but keep the fidelity claim.

## What this probe does NOT test

- Gemma cross-family (blocked on 1.55C infra fork).
- Selective re-prefill recovery (blocked on 1.55D infra fork).
- Novel 7B attractor emergence (would need 7B 40f; ~2h runtime; can
  be queued after this probe if time permits).
- Temperature invariance at 40f (would need a temp variant; defer).

## Artifact paths (to be populated)

- Findings doc (post-run): `...-3b-40f-deeper-plateau-findings.md`.
- Session/baseline JSONL + summary.json:
  `research/experiments/2026/artifacts/phase1_55A_3b_40f_deeper_plateau/`.
- Run log: same dir, `run.log`.
