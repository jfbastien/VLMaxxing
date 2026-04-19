# Phase 1.55A-3B — Cross-architecture mechanism probe (PREREG)

**Status:** preregistration, 2026-04-19. First mechanism-discriminating
experiment after the 6-point frame-count sweep. Tests whether the
monotonic-saturating ramp generalizes to a smaller model in the same
architecture family (Qwen 2.5-VL-3B-Instruct-4bit).

**Parents:** the six frame-count points on Qwen 7B-4bit
(`...-phase-1_55A-{persistent-kv,16f,18f,20f,24f,32f}-frame-scaling-findings.md`).

## Purpose

The frame-count sweep established a monotonic-saturating ramp on Qwen
2.5-VL-7B-Instruct-4bit between 16f (6.5k tokens, clean) and 24f
(9.7k tokens, saturated). Candidate mechanisms: (a) 4-bit WEIGHT
quantization noise, (b) M-RoPE positional OOD, (c) attention
degeneracy at long visual prefix, (d) basin-attractor dynamics of
the specific tokenizer/decoder distribution.

**Cross-architecture 3B probe discriminates:**
- If 3B also shows a ramp at **similar prefill-token counts**: ramp
  is intrinsic to prefill length, independent of model size. Weakens
  weight-quantization hypothesis (3B has fewer layers so less noise
  accumulation), supports position-OOD.
- If 3B shows a ramp at **different prefill-token counts** (shifted
  earlier or later): ramp depends on model capacity / depth.
  Supports accumulation mechanisms.
- If 3B shows **no ramp** at matched frame count: ramp is 7B-specific.
  Implicates a model-size-dependent mechanism (deeper accumulation or
  capacity saturation).

## Protocol

Identical to 1.55A 20f but with `--model-path ~/models/Qwen2.5-VL-3B-Instruct-4bit`.
Same 7 short-bucket VideoMME clips × 3 Qs = 21 queries per mode.
Same `--frame-count 20`. Temperature 0 (greedy).

## Hypotheses

### H1-3B — speedup follows prefill-dominance

Follow-up speedup > 30× (weaker band than 7B because 3B has lower
absolute first-query time, so speedup ratio is smaller in
prefill-dominated regime). Median follow-up < 1500 ms.

### H2-3B — fidelity outcome (three alternatives)

Δacc measured against 3B cold-start baseline. 3B is a weaker model,
so baseline accuracy may itself be lower — compare DELTA, not
absolute.

- **H2-3B.matched (Δacc ∈ [−0.05, 0.05]):** 3B ramp does NOT appear
  at 20f matched prefill → ramp is 7B-specific OR requires more
  depth/capacity. Queue 24f 3B to see if it appears later (saturated
  boundary shifted).
- **H2-3B.ramp (Δacc ∈ (−0.30, −0.05)):** 3B shows matching ramp
  behaviour at matched prefill → architectural generality confirmed.
  Strongly supports prefill-length-intrinsic mechanism (M-RoPE OOD or
  attention degeneracy).
- **H2-3B.worse (Δacc ≤ −0.30):** 3B collapses harder/earlier. 3B
  baseline may already be compromised; de-interpret with baseline
  check.

### H3-3B — prefix coverage ≥ 0.99

Trivial; same driver, same `find_prefix_length`.

### H4-3B — peak RSS

Expected ≤ 2.5 GB (3B weights ~1.8 GB in 4-bit).

### Failure-mode distribution (diagnostic)

Record whether the `addCriterion` basin also appears at 3B. If it
does not, the specific basin attractor is weight-dependent
(tokenizer is same, but decoder distribution differs after
quantization). If it does, the attractor is anchored in shared
token-space dynamics.

## Runtime budget

Expected ~12 min (3B runs ~50% of 7B wall time). First-query ~40 s,
21 queries × ~50% overlap ≈ 700 s.

## Decision rule

Post-run interpretation:
- H2-3B.matched → queue 24f 3B (boundary-shift test) AND temperature
  probe at 7B/20f (greedy-commit hypothesis)
- H2-3B.ramp → architectural generality confirmed. Queue mechanism
  falsifier: temperature probe at 7B/20f AND truncated-video probe
  (10-frame-2x-res matched-token-count)
- H2-3B.worse → queue bf16-weight 3B (if available) to disentangle
  baseline from cache-reuse

## Artifacts

Will land to `research/experiments/2026/artifacts/phase1_55A_3b_20f_crossarch/`.
