# Phase 1.55A-7B-20f — Temperature probe (PREREG)

**Status:** preregistration, 2026-04-20. Last in-phase mechanism probe
for the three-dimensional decomposition story. Queued from 3B 32f
saturation-mapping decision rule ("temperature probe becomes the next
experiment in all three sub-outcomes").

**Parent:**
`2026-04-20-phase-1_55A-3b-32f-saturation-findings.md` (3B 32f:
Δacc = −0.190 numerically identical to 24f, architecture-specific
ceiling ≈ 2.3× shallower than 7B).

## Purpose

The 7B cross-arch curve saturates at Δacc ≈ −0.43 via a progressive
basin-collapse (clean → 4-basin → 2-basin → single-attractor
`addCriterion`). The 3B curve saturates at Δacc ≈ −0.19 via
*clean-letter drift* with no basin collapse across 20f/24f/32f
(28/28 follow-ups clean 2-token letters). This is the **failure-
geometry** dimension of the three-dimensional decomposition.

Two live mechanistic explanations for the 7B basin-collapse:

1. **Greedy-argmax-commit (H-temp.greedy-commit):** T=0 greedy decoding
   commits early to the highest-probability attractor. Under cache
   reuse, the distribution flattens enough that argmax happens to land
   on `addCriterion`, then stays there by autoregressive self-
   reinforcement. A *distribution* with any probability mass outside
   the basin would escape: raising temperature (or adding min-p floor)
   should disperse the basin toward clean-letter drift and reduce |Δacc|.
2. **Distribution-collapse (H-temp.distribution-collapse):** Under
   cache reuse, the 7B output distribution ITSELF has collapsed onto
   `addCriterion` — most of the probability mass lies inside the basin,
   not just the argmax. Sampling doesn't escape because there's
   nowhere else to go. Temperature+min-p have ~no effect on Δacc or on
   basin prevalence.

Resolving this distinguishes **"greedy-decoding artifact masquerading
as model failure"** from **"intrinsic logit geometry of cache-reused
autoregression"**.

## Protocol

Identical to 1.55A persistent-KV 20f run but with non-greedy sampling.
- `--model-path ~/models/Qwen2.5-VL-7B-Instruct-4bit`
- `--frame-count 20`
- Same 7 short-bucket VideoMME clips × 3 Qs = 21 queries per mode.
- `--temperature 0.7 --min-p 0.05` (both session and baseline).
- Seed fixed at 42 → deterministic sampling trace across the 21
  queries, so re-runs replicate.

### Why T=0.7 + min_p=0.05

- T=0.7 is the conventional "reasonable sampling" setting — it
  disperses probability mass without reducing to full noise.
- min_p=0.05 prunes tokens with probability < 5% of the argmax —
  prevents low-probability tokens from being rescued by temperature
  alone. This is the sampler that *most strongly* disperses a basin
  while still keeping coherent output. If the basin survives
  (T=0.7, min_p=0.05), it is not a greedy artifact.
- Rationale: we want the sampler that maximizes escape probability
  from a greedy-commit basin. If even this sampler cannot escape, the
  greedy-commit hypothesis is falsified.

## Hypotheses

### H1-temp — speedup preserved under T>0

Temperature changes the sampler, not the KV path. Follow-up speedup
should remain ≥ 80× and median follow-up ≤ 700 ms at 20f
(20f greedy was 91× / 578 ms median; sampler overhead is minimal).
Falsified if speedup < 40× (would indicate a driver bug, not a
mechanism finding).

### H2-temp — basin-dispersal outcome (two pre-registered alternatives)

Two measurements per sub-outcome:
- **Δacc** — session accuracy minus baseline accuracy at 20f.
- **Basin prevalence** — fraction of 14 follow-up queries whose text
  includes `"addCriterion"` as a substring (0 = no basin survivors).

Greedy 20f reference: Δacc = −0.429, basin prevalence = 9/14 = 0.643.

Sub-outcomes:

- **H2-temp.greedy-commit (Δacc ≥ −0.25 AND basin prevalence ≤ 0.20):**
  Basin dissolves; drift-toward-wrong-letter replaces it. 7B's failure
  geometry collapses to 3B's under non-greedy sampling. Implies the
  basin IS a greedy-argmax artifact, not an intrinsic distribution
  property. Unifies 7B/3B failure modes (both "distribution-wide drift"
  with different ceilings). Paper claim #14 adjusts: "capacity-modulated
  threshold × architecture-modulated ceiling; greedy-decoding amplifies
  7B's failure at large prefill".

- **H2-temp.distribution-collapse (Δacc ≤ −0.35 OR basin prevalence ≥
  0.50):** Basin survives. The cache-reused distribution is intrinsically
  collapsed onto `addCriterion`, not a greedy argmax artifact. Paper
  claim #14 strengthens: "7B's basin collapse is a property of the
  logit distribution under cache reuse, not of the sampler. Greedy or
  temperature, the pathology is the same."

- **H2-temp.mixed (intermediate):** e.g. Δacc ∈ (−0.35, −0.25], or
  basin prevalence ∈ (0.20, 0.50). Partial dispersal — implies the
  distribution has *some* mass outside the basin, but argmax still
  favors it. Reported as "partial commit" with acknowledgment that
  neither hypothesis is cleanly earned.

### H3-temp — prefix coverage preserved

Prefix coverage ≥ 0.99 (sampler change does not affect KV reuse).
Falsified at < 0.95 → driver regression.

### H4-temp — peak RSS

Expected ≤ 13 GB (20f greedy was 12.3 GB; sampler overhead ≈ 0).

## Runtime budget

Expected ~35-40 min (20f greedy was 36 min; sampler adds ~0%).

## Decision rule

Post-run interpretation:

- **greedy-commit** → basin dissolves. Paper upgrades to the unified-
  failure-mode framing: 7B and 3B share "distribution-wide drift toward
  wrong letters" as the capacity-invariant failure geometry; the 7B
  basin is a greedy-decoding amplifier that disappears under sampling.
  This would be the most surprising mechanistic finding: closes the
  three-dimensional decomposition by showing failure-geometry is NOT
  architecture-specific, just greedy-decoding-specific on 7B.
- **distribution-collapse** → basin survives. Paper claim #14 hardens:
  failure-geometry IS architecture-specific at the distribution level,
  not the sampler level. Three-dimensional decomposition stands as-is.
- **mixed** → partial support for both. Report as-is. No further 1.55A
  probes queued; mechanism-mapping phase ends with acknowledged
  ambiguity in the last dimension.

In all three cases, the 1.55A mechanism-mapping phase closes and we
move back to fidelity-recovery experiments (selective re-prefill of
last-K frames, or the Gemma 4 cross-family lane).

## Falsifiers for the experiment itself

- If H1-temp speedup < 40× — driver regression or sampler overhead
  unexpectedly large; run is compromised.
- If H3-temp prefix coverage < 0.95 — KV path corrupted by sampler;
  run is compromised.
- If H4-temp RSS > 14 GB — memory regression; investigate before
  interpreting Δacc.

## Artifacts

Will land to `research/experiments/2026/artifacts/phase1_55A_7b_20f_temperature/`.
