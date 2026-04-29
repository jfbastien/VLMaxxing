# Phase 1.51R Stage 6 — 32-frame regime-match pilot (n=10 long)

**Status:** pilot findings 2026-04-18.

## Purpose

Pre-registered test of the regime-gap hypothesis (task #110): does matching
the pre-release source's 32-frame regime on VideoMME long bucket deliver aggregate e2e ∈
[1.5×, 2.0×] with Δacc ∈ [-0.15, -0.05]?

Prereg: `2026-04-18-phase-1_51R-stage6-regime-match-prereg.md`.
Anchor: `none`, `keep_rate=0.10`, `frame_count=32`, `max_tokens=32`.

## Headline result

| metric                         | value          |
|--------------------------------|----------------|
| dense accuracy                 | 0.500          |
| pruned accuracy                | 0.400          |
| **Δaccuracy**                  | **-0.100**     |
| agreement                      | 0.800          |
| **aggregate e2e speedup**      | **1.234×**     |
| generate-only speedup          | 5.017×         |
| per-token generate speedup     | 6.788×         |
| mean dense end-to-end          | 129.4s         |
| mean pruned end-to-end         | 104.9s         |
| peak RSS (during pilot)        | 5.3 GB         |

Authoritative file:
`artifacts/phase1_51R_32frame_pilot/long_kr010_n10_32frame_summary.json`.

## Hypothesis verdicts

- **H1 (e2e ∈ [1.5×, 2.0×] on long)** — **NOT EARNED.** Observed 1.234×
  falls below the band lower edge.
- **H2 (Δacc ∈ [-0.15, -0.05] on long)** — **EARNED.** Observed -0.100
  sits in the middle of the band.
- **H3 (peak RSS < 12 GB)** — **EARNED.** 5.3 GB, well under budget.

H1 is the SOTA-advancement hypothesis; H2 is a necessary-but-not-sufficient
side condition. The pilot therefore **falsifies the strong form of the
regime-gap thesis** on long bucket at this model size + this video pipeline.

## Per-item table

| item_id       | dense_e2e (ms) | pruned_e2e (ms) | e2e×  | dense | pruned | agree |
|---------------|----------------|------------------|-------|-------|--------|-------|
| long:669-1    | 73883          | 51325            | 1.439 | T     | T      | T     |
| long:711-2    | 102166         | 76780            | 1.331 | F     | F      | T     |
| long:712-2    | 105700         | 87068            | 1.214 | T     | T      | T     |
| long:712-3    | 110969         | 91410            | 1.214 | F     | F      | T     |
| long:737-3    | 182567         | 157891           | 1.156 | F     | F      | T     |
| long:756-2    | 151612         | 117659           | 1.288 | F     | F      | F     |
| long:758-3    | 127380         | 105826           | 1.204 | T     | T      | T     |
| long:794-1    | 119337         | 96249            | 1.240 | T     | F      | F     |
| long:847-3    | 149913         | 116489           | 1.287 | T     | T      | T     |
| long:892-1    | 170793         | 147842           | 1.155 | F     | F      | T     |

The smoke item (669-1, e2e=1.439×) sits at the far-right tail of the
distribution. Items 2–10 are clustered in [1.155×, 1.331×] with median
1.214×. **The smoke item was an outlier in e2e speedup, not a representative
sample.** Had we picked a different seed, we likely would not have launched
the pilot under H1 (band [1.5, 2.0]).

## Why H1 failed: decode dominates the ceiling, not G

Aggregate stage decomposition (n=10):

- mean decode_ms:      73672 (**56.9 %** of dense e2e)
- mean processor_ms:     292 ( 0.2 %)
- mean vision_ms:      24688 (19.1 %)
- mean generate_ms:    30780 (23.8 %)
- total dense e2e:    129432 (100.0 %)

**Fixed fraction = (D + P + V) / dense_e2e = 0.762.**

Arithmetic ceiling at s = 6.788 (observed per-token generate speedup):

    ceiling = 1 / (0.762 + 0.238 / 6.788) = 1 / 0.797 = 1.254×

Observed aggregate: 1.234×. **Prediction error 1.6 %**, consistent with
the 0.1–2.8 % band seen at 8 frames (Stage 6 kr-sweep). The ceiling model
continues to hold at aggregate scale.

**Ceiling@s=∞ on long-32:** 1 / 0.762 = **1.312×**. This is the theoretical
upper bound of token-pruning speedup on this configuration regardless of
what s the pruner achieves — because vision+decode are irreducible by token
pruning. At the *mean* long-bucket item at 32 frames, there is no token-
pruning mechanism that can exceed 1.31× aggregate speedup.

## Reconciling smoke vs pilot: G fraction varies by item

Smoke (669-1) had fixed_frac = 0.599 → ceiling@∞ = 1.670×. Items 2–10 have
fixed_frac in roughly [0.696, 0.835]. The smoke item had an unusually low
video decode time — 23s, vs a pilot mean of 74s — because its underlying
video file must be shorter or in an easier-to-decode codec state.

This has two implications:

1. **Item-level ceilings span 1.20×–1.67×** at 32 frames. Any claim framed
   as "32 frames delivers X×" must be attached to a decode-time bucket, not
   just a duration bucket.
2. **The ceiling lives where decode lives.** Cutting decode time in half
   (Phase 1.54 — video-decode acceleration, already preregistered) would
   lift mean fixed_frac from 0.76 to roughly 0.63, which would lift the
   aggregate ceiling from 1.31× to roughly 1.59× at the current s. **Phase
   1.54 is now the load-bearing lane for SOTA aggregate speedup**, not
   further token-pruning work.

## What the pilot DID earn

1. **Quantitative ceiling model graduates to cross-regime predictor.** The
   ceiling formula predicts 8-frame Stage 6 to 0.1–2.8 % error, 32-frame
   smoke to 0.1 % error, and 32-frame n=10 aggregate to 1.6 % error. Three
   regimes, six independent validations. This can be framed as a
   **publishable arithmetic-ceiling claim** regardless of whether any
   single arm earns SOTA.

2. **H2 earned.** Pruning holds accuracy within the pre-registered band on
   long 32-frame items. The mechanism (1049 visual tokens / 8441 = 12.4 %
   of the prompt) does not catastrophically degrade answer quality on long
   content. Agreement 0.800 is consistent with Stage 6 short/medium (0.80–
   0.87).

3. **Regime shift in fixed_frac confirmed.** 8-frame long had fixed_frac =
   0.912. 32-frame long has fixed_frac = 0.762. The ≈0.15 shift is the
   "regime gap" — but the gap *does not* cross the 1.5× threshold because
   decode scales with frame count roughly as fast as prefill does.

## What the pilot FALSIFIES

- the pre-release source's 1.8× long-bucket claim is **not reproducible on our pipeline** at
  the model size we run (Gemma 4-E4B, 4bit), *if* we interpret "wall-clock"
  to include video decode. If the pre-release source's "speedup" excludes video decode (i.e.
  measures generate-only or vision+generate), our generate-only speedup of
  5.02× comfortably exceeds 1.8×; the discrepancy is a scope definition,
  not a mechanism failure.
- The specific pre-registered prediction (H1 long ∈ [1.5, 2.0] at 32
  frames) is falsified. **This is a win for the methodology** — the
  pre-registered band ruled out the speculative claim before we over-
  invested in 32-frame infrastructure.

## Decision

1. Do NOT extend to medium/short long tranches at 32 frames under the
   current prereg — H1 is the gate and H1 failed. A smaller follow-up
   tranche at 32-frame short (n=5) is **sensible as a cross-bucket
   ceiling-model validation, not an H1 retry**; queue as optional.
2. Promote Phase 1.54 (video-decode acceleration) to **P0** — it is now the
   only mechanism left that can move aggregate e2e on long items at fixed
   model size.
3. Keep 1.51V (vision-tower pruning, task #108) at P1 — it lifts the G
   component, but G is 24 % of long-32 e2e, so even a 2× vision reduction
   yields ~1.14× aggregate; it is NOT the SOTA lever on long.
4. **Re-frame claim-matrix**: Phase 1.51R's SOTA-advancing result remains
   kr=0.33 short-bucket Pareto-knee (Δacc=0, e2e=1.090×, per_tok=7.90×) at
   8 frames. 32-frame long is a falsification result that promotes Phase
   1.54.

## Cross-references

- `2026-04-18-phase-1_51R-stage6-regime-match-prereg.md` — prereg.
- `2026-04-18-phase-1_51R-stage6-32frame-smoke-findings.md` — smoke.
- `2026-04-18-arithmetic-ceiling-findings.md` — ceiling model.
- `2026-04-18-scaleout-regime-gap-note.md` — regime-gap thesis (now needs
  update: aggregate e2e does not fully close).
- `artifacts/phase1_51R_32frame_pilot/long_kr010_n10_32frame_summary.json`
  — authoritative numbers.
- `artifacts/phase1_51R_32frame_pilot/long_kr010_n10_32frame.jsonl` — per
  item records.
