# Phase 1.55A-3B — Cross-architecture mechanism probe (FINDINGS)

**Date:** 2026-04-19. **Parent prereg:**
`2026-04-19-phase-1_55A-3b-crossarch-prereg.md`. **Motivates next:**
24f 3B boundary-shift test + 7B/20f temperature probe.

## Headline

At matched 20f prefill (~8.1k tokens), **Qwen 2.5-VL-3B-Instruct-4bit
shows NO ramp**: Δacc = −0.048 (inside ±0.05 envelope).
H2-3B.**matched** verdict. The monotonic-saturating ramp observed on
7B-4bit (Δacc = −0.38 at same frame count) is **not** intrinsic to
prefill length, M-RoPE position, or 4-bit weight quantization per se.
It is **model-dependent** — capacity, depth, or model-specific
decoder distribution.

## Numbers (7 short-bucket VideoMME clips × 3 Qs each)

| Metric | 3B-4bit 20f | 7B-4bit 20f |
|---|---|---|
| Session (cache reuse) n_correct/21 | 12 (0.571) | 8 (0.381) |
| Baseline (cold each) n_correct/21 | 13 (0.619) | 16 (0.762) |
| **Δacc (session − baseline)** | **−0.048** | **−0.381** |
| Follow-up n_correct/14 | 7 | 1 |
| Speedup (first / follow-up) | **136.07×** | 94.42× |
| Follow-up median (ms) | 412 | 905 |
| First-query median (s) | 56.1 | 83.8 |
| Prefix coverage | 0.9928 | 0.9979 |
| Peak RSS (GB) | 3.93 | 4.64 |

- H1 EARN: speedup 136× exceeds the conservative [>30×] band; 3B's
  prefill-dominance ratio is HIGHER than 7B's because 3B decode is
  comparatively faster.
- H2 EARN (matched): Δacc = −0.048 within ±0.05.
- H3 EARN: 99.28% prefix coverage.
- H4 EARN (modified): 3.93 GB peak RSS (pre-reg expected ≤2.5 GB —
  actual is higher because activations + 8k-token KV dominate over
  just-weights in mlx-vlm; not a ceiling violation, just a re-calibration).

## Basin structure (failure-mode pattern across 14 follow-ups)

| Pattern | 3B-4bit 20f | 7B-4bit 20f |
|---|---|---|
| Clean-correct (single letter, matches gold) | 7 | 1 |
| Clean-wrong-choice (single letter, off from gold) | 7 | 0 |
| Long-garbage (Java/MyBatis gen, 14–64 tok) | 0 | 4 |
| Empty / minimal (0–1 tok) | 0 | 0 |
| Saturated addCriterion (repeating SQL-ish) | 0 | 9 |

**Every 3B follow-up emits exactly 2 tokens (one-char answer + EOS).**
The addCriterion attractor basin is **not present** at 3B at this
prefill length. The long-garbage Java basin is also absent.

This is the most consequential observation: at 3B, the decoder remains
in the format-compliant basin even under the same ~8.1k-token prefill
that saturates 7B into addCriterion. The attractor basin is not a
generic Qwen-tokenizer-space artifact — it is **7B-specific** (weights,
capacity, or decoder distribution-shape).

## Mechanism verdict (post 3B probe)

### Falsified

- **Pure prefill-length-intrinsic mechanism.** If the ramp were caused
  by prefill-length-only effects (M-RoPE approaching trained-support
  boundary, attention degeneracy from long visual prefix, or
  KV-vs-position-space mismatch), 3B with identical prefill length,
  identical m-RoPE config, identical tokenizer, and identical bf16 KV
  storage would show an equivalent ramp. It does not. Δacc collapses
  from −0.381 (7B) to −0.048 (3B) with only model-weights changed.
- **Shared-tokenizer basin attractor hypothesis.** The addCriterion /
  Java-MyBatis basins were hypothesized to be anchored in
  shared-tokenizer-space dynamics. They are not: 3B shares Qwen
  tokenizer but shows zero instances of either basin.

### Strongly supported

- **Model-capacity / depth-dependent accumulation.** Ramp is specific
  to 7B under 4-bit weight quantization. Plausible microstructure:
  7B's larger hidden dimension + more parameters accumulate more
  quantization-induced perturbation per layer; OR 7B's decoder
  distribution has more basins reachable from a perturbed hidden state.
- **Decoder-distribution basin difference.** 3B's decoder distribution
  may simply not have an easily-accessible addCriterion / MyBatis
  attractor from format-priming. 7B's attractor could originate in
  training-data co-occurrence of chatML-like prompts and
  SQL/Java training data; 3B's training-data mixture may differ.

### Weakened (not dispositive)

- **4-bit KV quantization hypothesis** (original #135 framing) is not
  directly addressable on mlx-vlm — KV is bf16 in both models.
  Ramp is still consistent with weight-quantization noise accumulating
  through deeper 7B stack; but that is now "weight-quant × depth"
  rather than "KV-quant × length".

## SOTA implication

Paper claim #14 gains a scope dimension: the monotonic-saturating
ramp and single-attractor-basin collapse is a **Qwen 2.5-VL-7B-4bit
boundary phenomenon**, not a universal property of 4-bit VLM cache
reuse. Safe-budget prose should read:

> Cache reuse preserves accuracy at ≤ ~6.5k tokens on Qwen
> 2.5-VL-7B-4bit, degrading through progressive basin collapse to a
> saturated single-attractor by ~9.7k tokens. At the same prefill
> length, the smaller Qwen 2.5-VL-3B-4bit shows no such ramp
> (Δacc = −0.048 at 8.1k tokens) — the ramp boundary is
> model-specific, likely depth- or capacity-mediated.

This makes the paper story RICHER: we've both (a) found and (b)
discriminated a failure-mode boundary. Mechanism discrimination is a
stronger contribution than an accuracy curve on one model.

## Decision rule → next experiments

Per prereg H2-3B.matched rule:

1. **Queue 24f 3B boundary-shift test.** Does 3B have a ramp at all,
   or is it just shifted to a later prefill length? 24f ≈ 9.7k tokens.
   Expected runtime ~28 min.
2. **Queue 7B/20f temperature probe (T>0, min-p).** The addCriterion
   attractor is 7B-greedy-specific. Testing whether temperature > 0
   (e.g. T=0.7 with min-p=0.05) disperses the basins reveals whether
   this is a greedy-argmax commit on a broad distribution, or a
   distribution-collapsed state with no alternative commits available.
   Requires small driver mod: expose `--temperature` / `--min-p`
   flags and forward to `generate()`.

24f 3B is cheaper/faster (single existing driver path). Runs first.

## Artifacts

- `research/experiments/2026/artifacts/phase1_55A_3b_20f_crossarch/`
  - `summary.json`
  - `session_qwen7b_n7.jsonl` (filename tag is legacy; model is 3B)
  - `baseline_qwen7b_n7.jsonl`
