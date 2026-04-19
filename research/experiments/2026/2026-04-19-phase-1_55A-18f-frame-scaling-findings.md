# Phase 1.55A-18f — Ramp-onset bisection (FINDINGS)

**Status:** resolved 2026-04-19. **H2''''' = mid-ramp** (Δacc=−0.238).
4-point ramp curve now complete; **switching to mechanism tests.**

**Prereg:** [`2026-04-19-phase-1_55A-18f-frame-scaling-prereg.md`](2026-04-19-phase-1_55A-18f-frame-scaling-prereg.md)
**Artifacts:** `research/experiments/2026/artifacts/phase1_55A_18f_frame_scaling/`

## Headline

**18f lands squarely on the interior ramp — Δacc=−0.238 at ~7.3k
prefill tokens.** The soft-threshold curve now has three interior
points (18f/20f/24f) plus clean (16f) and saturated (24f/32f)
endpoints. The ramp is monotonic-saturating (differences decay:
−0.238, −0.143, −0.048, 0). Failure-mode distribution is the richest
yet — four distinct basins coexist.

## Verdict table

| Hypothesis | Outcome | Evidence |
|---|---|---|
| H1''''' — speedup [65×, 110×] | **earn** | 70.28× (first 77 462 ms, follow-up median 1 102 ms) |
| H2''''' — fidelity | **mid-ramp** | Δacc = −0.238 (12/21 session vs 17/21 baseline) |
| H3''''' — prefix coverage ≥ 0.99 | **earn** | 0.9920 |
| H4''''' — peak RSS ≤ 5 GB | **earn** | 4.19 GB |

**Note on H1''''':** speedup is BELOW both 16f (91×) and 20f (94×),
despite 18f prefill (~7.3k) being intermediate. This is because
median follow-up time is inflated by long-garbage generations (3 of
14 follow-ups produce 14-64 gen tokens, pulling the median up to
1102 ms vs 807-905 ms at 16f/20f). **Speedup is coupled to failure-
mode distribution, not just cache-reuse.** This is a useful
diagnostic, not a broken measurement.

## Scaling surface (5-point curve, updated with 18f)

| Frames | Prefill | First-Q (s) | Follow-up median (ms) | Speedup | Δacc | Basin |
|---|---|---|---|---|---|---|
| 8 | ~3270 | 38.5 | 815 | 47.23× | −0.048 | clean |
| 16 | ~6500 | 73.5 | 807 | 91.06× | 0.000 | clean |
| **18** | **~7300** | **77.5** | **1102** | **70.28×** | **−0.238** | **early-mid ramp** |
| 20 | ~8100 | 83.8 | 905 | 94.42× | −0.381 | mid-ramp |
| 24 | ~9700 | 108.9 | 864 | 121.58× | −0.429 | saturated |
| 32 | ~12920 | 163.2 | 1008 | 149.88× | −0.429 | saturated |

Δacc series (vs baseline): 0 (16f) → −0.238 (18f) → −0.381 (20f) →
−0.429 (24f) → −0.429 (32f). **Monotonic-saturating approach to
limiting Δacc ≈ −0.43.** Pairwise increments decay: −0.238, −0.143,
−0.048, 0.

## Failure-mode decomposition (14 follow-ups at 18f)

**Correct: 5** (0.357)
- 4 clean answers: 037-Q2 "D", 116-Q1 "D", 116-Q2 "B", 160-Q1 "D"
- 1 coincident-saturated: 210-Q2 `addCriterion` → "A" (gold "A")

**Incorrect: 9**, distributed across FOUR distinct basins:

| Basin | Count | Example |
|---|---|---|
| **Clean-but-wrong-choice** (2 tok, non-gold letter) | **3** | 158-Q1 picks "A" gold "D"; 158-Q2 picks "C" gold "D"; 160-Q2 picks "D" gold "A" |
| **Long-garbage** (>8 gen tokens, Java/MyBatis hallucinations) | **3** | 037-Q1 14 tok `addCriterion("index").like("%500%")`; 100-Q2 64 tok; 120-Q1 16 tok |
| **Empty / malformed** (1-2 tok, no option letter parsed) | **2** | 100-Q1 empty; 120-Q2 2 tok no parse |
| **Short-`addCriterion` saturated attractor** (2 tok, parsed as "A") | **2** | 210-Q1, 210-Q2 both `addCriterion` → "A" |

This is qualitatively different from 20f (9 short-addCriterion + 4
long-garbage + 1 clean-correct; no empty, no clean-wrong) and from
24f/32f (14 short-addCriterion, single attractor).

## Ramp mechanism: basin-structure evolution

Failure-mode distribution BY PATTERN (not correctness) across frame
counts reveals the transition is not just an accuracy drop — it's an
**attractor-basin shift**. n=14 follow-ups per row:

| Frames | Clean-correct | Clean-wrong | Long-garbage | Empty | Sat-addCriterion | Δacc-measured |
|---|---|---|---|---|---|---|
| 16 | 14 | 0 | 0 | 0 | 0 | 0.000 |
| **18** | **4** | **3** | **3** | **2** | **2** | −0.238 |
| 20 | 1 | 0 | 4 | 0 | 9 | −0.381 |
| 24 | 0 | 0 | 0 | 0 | 14 | −0.429 |
| 32 | 0 | 0 | 0 | 0 | 14 | −0.429 |

(At 20f and 18f, 2 addCriterion follow-ups coincidentally scored when
gold answer was "A"; those count in the saturated-attractor basin but
are tallied as correct in Δacc.)

**18f has the richest basin diversity.** As prefill grows past
the soft threshold, the decoder progressively collapses into the
most dominant saturated attractor; at 18f, four basins still have
mass; by 20f, the saturated attractor dominates; by 24f, basin
collapse is complete.

## Mechanism interpretation (updated)

Previous verdict (post-20f): soft threshold with ramp favours
quantization-noise / M-RoPE-OOD over pure cliff and pure gradient.

**Updated (post-18f):**
1. **Strongly supported:** 4-bit KV quantization noise accumulates
   with prefill length. At 16f noise is below signal threshold
   (clean); between 16f-18f it crosses into a zone where it
   contaminates the decoder distribution (multiple basins emerge);
   between 20f-24f it dominates, collapsing to the single most
   accessible attractor in the corrupted distribution space.
2. **Strongly supported:** M-RoPE trained-support boundary.
   Approach-to-OOD mixes trained-support and off-manifold behaviour;
   full OOD collapses.
3. **Weakened:** pure gradient — would predict smooth Δacc past 24f;
   we see saturation by 24f, confirmed by 32f.
4. **Falsified:** pure single-step cliff — would predict no ramp; we
   have a 3-point ramp (18/20/24) with decaying increments.

## Next experiment (queued)

Frame-count sweep has mapped the fidelity curve to the resolution
we need. **Switching to mechanism-discriminating experiments.**

**Queued #135: bf16 KV-cache control at 20f.** Cleanest falsifier of
the 4-bit-KV-quantization hypothesis:
- If Δacc collapses to ~0 with bf16 KV at 20f → quantization-noise
  hypothesis EARN, M-RoPE-OOD hypothesis weakened (but not
  falsified — bf16 may also extend trained-support via higher
  precision preservation of positional signal).
- If Δacc stays ~−0.38 with bf16 KV at 20f → quantization-noise
  hypothesis FALSIFIED, M-RoPE-OOD hypothesis strongly supported.

**Follow-up after bf16:** M-RoPE probe — truncated visual prefix at
matched frame count (same 20 frames but fewer video tokens via
shorter per-frame encoding) to isolate position from count.

## Paper implication

Claim #14 safe-budget language now:

> cache-reuse preserves accuracy below a narrow soft threshold near
> ~6.5k prefill tokens on Qwen 7B-4bit; between ~7.3k and ~9.7k
> tokens the decoder progressively collapses through a 4-basin
> mixed-attractor ramp into a single saturated attractor (Δacc
> series 0 → −0.238 → −0.381 → −0.429; 14-sample per point).
> Speedup is prefill-dominated (47× at 3.3k → 150× at 12.9k) and
> remains high even past the fidelity threshold.

This is a sharper claim than "cliff" and a richer one than
"gradient."
