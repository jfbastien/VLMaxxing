# Phase 1.55C — Gemma 4-E4B-4bit cross-family probe (PREREG)

**Date:** 2026-04-20. **Status:** preregistration, deferred pending
driver Gemma path.

## Provenance

Phase 1.55A closed 2026-04-20 with a three-dimensional mechanism
decomposition of persistent-KV cache-reuse failure:
1. Threshold onset — capacity-modulated (7B-4bit ~7.3k; 3B-4bit ~9.7k).
2. Saturation ceiling — architecture-specific (Qwen 7B-4bit −0.43;
   Qwen 3B-4bit −0.19; plateau confirmed across 9.7k and 12.9k).
3. Failure geometry — architecture-specific at distribution level
   (Qwen 7B-4bit: pathological-attractor SET {addCriterion,
   addCriterion(…)Java, 自动生成}, sampler-invariant per 7B/20f
   temperature probe; Qwen 3B-4bit: clean 2-token letter drift, 28/28
   follow-ups across 20f/24f/32f).

All three dimensions are currently parametrized across **one
architecture family** (Qwen 2.5-VL, 4-bit MLX weights). Every
cross-arch datapoint we have is a capacity ablation within Qwen. A
cross-family probe is the final axis needed to test whether the 3-D
decomposition is a property of Qwen's specific architecture (M-RoPE-V,
interleaved-attention, Qwen tokenizer decoder) or a generic property
of 4-bit-quantized VLMs under cache reuse.

Gemma 4 is the cleanest cross-family: our stack already uses
Gemma 4-E4B-4bit for the Phase 1.51R novelty-pruning lane; Sam's
whitepaper §2.13.3 persistent-KV result was measured on Gemma 4 26B.

## Hypotheses

Gemma 4-E4B is an order smaller than Sam's 26B — we cannot replicate
Sam's exact numbers. What we CAN test:

**H1-Gemma (speedup scales).** Median follow-up latency < 1.5 s at
20f; speedup vs first-query ≥ 50×. Calibrates our expectation that
persistent-KV yields large latency wins on Gemma's attention topology
(different from Qwen's M-RoPE). **Falsification:** speedup < 20×.

**H2-Gemma (fidelity surface).** Three exclusive sub-outcomes at 20f:
- **H2-Gemma.3B-match** (architecture geometry generalizes across
  families at equivalent capacity): Δacc ∈ [−0.25, −0.10], follow-ups
  emit clean letter answers, NO pathological-attractor basin. Earns if
  both (a) Δacc in band AND (b) ≥12/14 follow-ups clean-letter.
- **H2-Gemma.7B-match** (failure geometry tracks scale/capacity, not
  architecture family): Δacc ∈ [−0.50, −0.30] with ≥8/14 follow-ups
  showing basin collapse (any pathological attractor repeated ≥3
  times). Earns if both.
- **H2-Gemma.novel-geometry** (failure geometry is Qwen-specific):
  Δacc pattern does not match either Qwen-3B or Qwen-7B envelopes
  OR follow-ups exhibit a NEW failure mode (not clean-letter, not
  addCriterion-family). Mutually exclusive with the other two.

**H3-Gemma.** Prefix coverage ≥ 0.99. Sanity that cache-reuse
mechanics work on Gemma's attention. **Falsification:** < 0.98.

**H4-Gemma.** Peak RSS ≤ 8 GB at 20f. E4B is ~4B params, 4-bit ≈ 2GB
weights + KV cache + activations. **Falsification:** > 10 GB.

## Decision rules

- **H2-Gemma.3B-match earns** → 3-D decomposition generalizes across
  architecture families; shallower Δacc ceiling at Gemma's smaller
  capacity; sampler-invariance extends (testable via follow-up
  Gemma temperature probe, deferred).
- **H2-Gemma.7B-match earns** → basin collapse is capacity-dependent
  and/or attractor-set is shared across Qwen and Gemma (implying
  4-bit-quantization-noise is the dominant mechanism, not
  architecture-specific decoder distribution). High-impact finding.
- **H2-Gemma.novel-geometry earns** → 3-D decomposition is under-
  parametrized; a fourth dimension (attention topology or tokenizer
  family) gates the failure mode. Publishable as an open question.

## Gating / deferral

Requires:
1. Gemma loader in `scripts/run_kv_cache_session.py` (currently
   hard-codes Qwen VideoMME preprocessing pipeline — `_load_videomme_rows`
   and `_questions_for_video_id` are benchmark-generic, but the
   prompt-template and image-token placement are Qwen-specific).
2. Verification that mlx-vlm's `PromptCacheState` + `find_prefix_length`
   work correctly with Gemma's attention (Gemma 4 uses multimodal
   attention interleaving; the prefix-matching invariant may not hold
   across image tokens without custom handling).
3. VideoMME compatible prompt for Gemma (Sam's whitepaper prompt is
   Gemma-native; we should mirror §2.13.3's exact prompt).

Runtime estimate: ~30 min implementation + ~30-60 min run at 20f
(Gemma 4B is smaller than Qwen 7B but the prefill cost dominates).

## Non-goals

- NOT a frame-scaling sweep. Single point at 20f to place Gemma on
  the same prefill axis as Qwen 7B/3B 20f.
- NOT a temperature probe on Gemma (follow-up if clean-letter
  geometry is observed; deferred).
- NOT targeting Sam's 26B numbers — we are at E4B (4B), cross-family
  generalization of the 3-D decomposition is the scientific goal.
