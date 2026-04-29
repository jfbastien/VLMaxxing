# Phase 1.55D — Selective re-prefill of last-K frames (PREREG)

**Date:** 2026-04-20. **Status:** preregistration.
**Parent phase:** 1.55A closed with distribution-level basin collapse
on 7B at 20f+. 1.55D is the first fidelity-recovery lever.

## Problem statement

Phase 1.55A established that Qwen 2.5-VL-7B-4bit suffers a
monotonic-saturating Δacc ramp at 20f+ persistent-KV cache reuse,
saturating at Δacc ≈ −0.43 from 24f onward. The 2026-04-20
temperature probe ruled out greedy-argmax-commit as the mechanism:
**the cache-reused logit distribution has collapsed onto a
pathological-attractor set** {addCriterion, addCriterion(…)Java,
自动生成} and temperature + min-p cannot escape the set because
clean-letter mass is too thin to sample.

Corollary: sampler-side recovery is not possible. The pathology must
be fixed UPSTREAM of decoding.

## Proposed mechanism

**Selective re-prefill of the last-K frames per follow-up query.**

Concretely: for each follow-up query on a cache-warm session, truncate
the KV cache AFTER the system prompt + (first N−K frames) + text
template, then re-prefill (last K frames + question). The first N−K
frames' cache is reused across follow-ups (the global-context saving);
the last K frames are freshly prefilled each query.

Intuition: the basin collapse appears to correlate with prefill depth
(16f clean → 18f 4-basin → 20f 2-basin → 24f saturated). Re-prefilling
the tail of the visual context under fresh attention on each query
preserves the question-conditioned "recency" of those frame tokens
and may restore the logit-distribution mass lost to 4-bit KV
quantization accumulation across the long tail.

This is the pre-release source §2.13.3 with a targeted carve-out: we trade
a fraction of the follow-up speedup for a fidelity recovery that
the temperature probe proved sampler-side interventions cannot
deliver.

## Parameters to sweep

- **K = 4 frames** (primary candidate). At 20f, re-prefilling 4
  frames ≈ 1600 tokens added to each follow-up. Extrapolating the
  prefill rate (~140 tok/s at 8k; slower at larger prefills), ~12s
  additional latency per follow-up → 13-14s follow-up median vs
  greedy 905ms at 20f greedy → ~14× speedup retained (vs 94× without
  re-prefill).
- **K = 2 frames** (speedup-preserving variant). ~800 tokens added,
  ~6s added → ~30× speedup retained.
- **K = 8 frames** (fidelity-maximizing variant). Halfway between
  baseline and 20f cache reuse.

**Anchor:** 20f total frames. 16f greedy reference (Δacc=0.000,
94× speedup) sets the fidelity target; the 1.55D proposal is to
approach that envelope while retaining ≥30× speedup.

## Hypotheses

**H1-1.55D (fidelity recovery).** At K=4 on 7B-20f, Δacc ≤ −0.15
(primary target) — equivalent to the pre-release source's reported regime. At K=2,
Δacc ≤ −0.25 (partial recovery). At K=8, Δacc ≤ −0.10.
**Falsification:** K=4 yields Δacc worse than −0.25 → selective
re-prefill does not escape the basin; mechanism is deeper than
tail-frame cache corruption.

**H2-1.55D (speedup floor).** At K=4, follow-up median latency
≤ 15 s and speedup ≥ 10×. **Falsification:** speedup < 5× →
re-prefill cost dominates; mechanism-only intervention without
speedup benefit; not paper-publishable as deployment lever.

**H3-1.55D (basin dispersal).** Fraction of follow-ups emitting
any pathological-attractor-set member (addCriterion, Java-code,
自动生成) drops from 13/14 greedy baseline to ≤ 4/14 at K=4.
**Falsification:** basin prevalence unchanged → re-prefill does
not perturb the logit distribution enough to escape collapse
(distinguishes "tail-frame corruption" mechanism from "global
prefix-pollution" mechanism; if the former, re-prefill recovers; if
the latter, re-prefill does not).

**H4-1.55D (peak RSS).** ≤ 5 GB. K=4 re-prefill at 20f should not
materially exceed the baseline 20f cold-path (RSS ~3.5 GB). More
fundamental: does maintaining a truncatable cache incur structural
memory overhead that would block deployment?

## Decision rules

- **H1-1.55D.K=4 earns** → paper-grade result: selective re-prefill
  is the deployment lever that restores fidelity under cache reuse.
  Claim #14 extends with a prescriptive recovery recipe. the pre-release source's 1.8×
  regime becomes reachable on 7B-4bit with K=4.
- **H1-1.55D.K=4 misses but H1-1.55D.K=8 earns** → fidelity is
  recoverable at reduced speedup (~7× instead of ~30×). Report as
  a trade-off curve; frame as "recovery-speedup Pareto frontier."
- **H1-1.55D.K=4 misses, H1-1.55D.K=8 also misses** → mechanism
  is NOT tail-frame-corruption-dominated; the pathology extends
  deeper into the cache. Opens search for mechanism earlier in the
  pipeline (cross-frame KV quantization reset, attention-score
  eviction, different quantization scheme).

## Required driver work

`scripts/run_kv_cache_session.py` currently calls
`generate(model, processor, prompt_cache_state=state, ...)` with
`state` accumulated across queries. To support selective re-prefill:

1. After first-query prefill completes, record a **truncation index**
   `trunc_idx` = token offset corresponding to the boundary between
   (system + first N−K frames + text template) and (last K frames).
   This requires knowing the token count of the first N−K frames
   after vision-encoder tokenization, which is model-specific.
2. On each follow-up: **clone or rewind** the `PromptCacheState` to
   `trunc_idx`, then prefill the remaining (last K frames + new
   question) fresh.
3. Verify mlx-vlm's `PromptCacheState` supports rewind/clone without
   corrupting the underlying attention KV tensors. If not, we must
   either reconstruct the state from scratch (defeats the point) or
   patch mlx-vlm.

Estimated driver work: 1-3 hours depending on mlx-vlm API
flexibility. The truncation-index computation is the tricky part;
vision-tokens per frame in Qwen 2.5-VL is image-grid-dependent and
must be recovered from the prepared inputs.

## Gating

- 1.55A CLOSED (done 2026-04-20).
- No external gates; this is the natural next-phase experiment in
  the persistent-KV track.

## Runtime estimate

- K=4 pilot at 20f n=7 clips = ~50-70 min (3× follow-up latency
  vs 20f greedy's 42 min; but only one K value + one N value).
- Full K sweep (K ∈ {2, 4, 8}) = ~3-4 hours.

## Paper implication

If H1-1.55D.K=4 earns, claim #14 reads:
"Qwen 2.5-VL-7B-4bit persistent-KV cache reuse preserves accuracy
at prefills ≤ 16f (Δacc=0.000 at 91× speedup). At 20f+ the cache-
reused logit distribution collapses onto a pathological-attractor
set that is not recoverable at the sampler; selective re-prefill
of the last-4 frames per follow-up restores accuracy to within
Δacc ≤ −0.15 while retaining ≥ 15× speedup."

This is the first fidelity-recovery lever that complements the
mechanism decomposition and closes the gap to the pre-release source's 26B/Gemma 1.8×
claim on a smaller model with a different architecture family.

## Non-goals

- Not a sweep across N (frame count). 20f is the anchor — cleanest
  mid-ramp condition; K=4 recovery extrapolates to 24f/32f if K
  scales linearly.
- Not a Gemma run (see 1.55C). If 1.55C earns H2-Gemma.7B-match,
  selective re-prefill generalizes to Gemma; if H2-Gemma.3B-match,
  Gemma does not need recovery because its ceiling is shallower.
- Not composed with decode acceleration (that is 1.55B with 1.54).
