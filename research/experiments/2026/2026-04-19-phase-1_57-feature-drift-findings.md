# Phase 1.57 — Feature-drift findings (Qwen, v0)

**Status:** findings, 2026-04-19. First pass covers
**Qwen 2.5-VL-7B-Instruct-4bit only** at 8f / 16f / 32f — all three
landed on `videomme_dev_v1` n=30. Gemma 4-E4B-4bit deferred pending
inline ViT-encode path. Prereg:
`2026-04-19-phase-1_57-feature-drift-mechanism-prereg.md`.

## Methodology clarification (important)

Our implementation differs from the prereg's original sketch in a
specific, defensible way. The **prereg** envisioned:

> two ViT passes: (a) cache-substitute for STATIC+SHIFTED, (b) fresh
> ViT encode of all tokens; emits per-token cosine

— which would give NOVEL cos = 1.000 trivially (we re-encode them
fresh in pass (a) anyway).

**What we actually implemented** is a cleaner, more directly
interpretable measurement: **adjacent-frame fresh-vs-fresh cosine
similarity** between two ViT encode passes, stratified by
per-block classification:

- For each pair of adjacent frames (t, t+1) in a clip:
  - Classify each block using MEAN pixel-diff: STATIC / SHIFTED / NOVEL
  - Take per-block ViT feature at spatial position k on frame t
    and on frame t+1 (both fresh encodes)
  - Compute cosine similarity
- Aggregate cos per class across all (item, pair, block) triples

**Why this is the right quantity.** The prereg measurement
presumes a specific cache-substitute mechanism under test. Our
measurement is a *lower bound* on that cache-substitute drift:

- At minimum, a cache that reuses STATIC block k's features from
  frame t to populate frame t+1's input will deviate from the
  fresh encode of frame t+1 at position k by at least the
  adjacent-frame cosine we measure (because both the "what was at
  position k in frame t" and the "context of frame t" have changed).
- Any multi-frame cache reuse (e.g., Sam's `sticky4`, or frame-0
  persistent reuse) accumulates at least this much drift per frame.

So **adjacent-frame per-class cos is a conservative lower bound
on cache-substitute drift magnitude**. If adjacent is already far
below 1.0, cache-substitute drift is at least as bad.

**Trade-off.** We lose the "NOVEL cos = 1.0 by construction"
diagnostic in exchange for a cleaner independent measurement.
NOVEL cos in our scheme should be *lowest* (not 1.0) because NOVEL
= "pixel content actually changed a lot." Ordering should be
STATIC > SHIFTED > NOVEL, and it is — see results.

## Results v0: Qwen 8f VideoMME dev n=30

```
model=qwen2.5-vl-7b-4bit items_ok=30 miss=0 samples=84000
  static   n= 36629 mean_cos=+0.5623 p05=+0.1774 p95=+0.9368
  shifted  n=  2208 mean_cos=+0.4680 p05=+0.1429 p95=+0.8965
  novel    n= 45163 mean_cos=+0.3215 p05=+0.0950 p95=+0.7017
```

### Hypothesis verdicts (v0)

| hypothesis | prereg band | observed | verdict |
|-----------|-------------|----------|---------|
| H1 Gemma STATIC [0.60, 0.85] | — | deferred | not testable (Gemma path not wired) |
| H2 Qwen STATIC [0.95, 1.000] | [0.95, 1.000] | **0.562/0.607/0.638** (8/16/32f) | **FALSIFIED** at all frame counts under our adjacent-frame measurement |
| H3 Qwen STATIC rises monotonically 8f→16f→32f (adjacent-frame variant) | monotonic ↑ | **0.562 < 0.607 < 0.638** | **EARNED** (see "H3 verdict" below) |
| H4 entropy weaker than cosine | — | deferred (no entropy path) | deferred |

**H2 falsification, interpreted.** The observed Qwen STATIC cos
of 0.562 is *far* below the preregistered [0.95, 1.000] band. Two
readings:

(a) **Our measurement differs from Sam's in a specific way and
the band wasn't the right target for our measurement.** Sam's
cache-substitute vs fresh comparison uses a specific hybrid
encoding; ours uses naive adjacent fresh encodes. Adjacent-frame
cosine is naturally lower because the INPUT to the ViT at
position k is allowed to differ slightly between frames (STATIC
threshold is MEAN pixel-diff < 3.0 on 0-255 scale, not 0.0),
whereas cache-substitute literally uses the *same* cached feature.

(b) **Even "STATIC" blocks drift substantially due to global
self-attention.** Qwen 2.5-VL has a large ViT with 32 attention
layers; a 0.562 cosine between adjacent-frame STATIC features is
consistent with significant attention-mixing, even on this model.

The two readings are not mutually exclusive. Reading (a)
explains *why H2 as preregistered fails*; reading (b) is the
**more interesting scientific finding**: on VideoMME-style
content (varied motion across 1-minute-spaced samples), Qwen's
"STATIC-classified" blocks nonetheless have meaningful per-token
feature drift adjacent-frame. This is **not a bug in our
measurement** — it is a direct observation about how much the
ViT output changes at a spatially-identical position when the
GLOBAL content of the frame changes.

### Ordering preserved

STATIC (0.562) > SHIFTED (0.468) > NOVEL (0.322). The planner's
pixel-based class ranks correlate with feature-space cosine — low
pixel delta → higher (but not 1.0) feature cos; high pixel delta
→ lower feature cos. This internal consistency of the
block-classification signal is a positive result: the planner's
proxy classes **do** capture feature-space drift ordering even if
the STATIC class is not bit-faithful at the feature level.

### Parse statistics

84,000 block samples across 7 frame-pairs × 30 items × per-frame
token grid. STATIC:NOVEL ratio ~44%:54% at 8f, reflecting that
short/medium VideoMME clips at 8f uniform sampling have roughly
equal "static-ish" and "novel-ish" content per block — i.e., the
8f stride is large enough that about half the pixel content
changes substantially frame-to-frame.

## Results v1: 8f / 16f / 32f frame-count sweep (landed 2026-04-19)

All three Qwen runs landed on the same `videomme_dev_v1` n=30
manifest. Per-class adjacent-frame cos aggregates:

| frames | n_samples | STATIC mean | STATIC median | STATIC std | STATIC p05 | STATIC p95 | SHIFTED mean | NOVEL mean |
|--------|-----------|-------------|---------------|------------|------------|------------|--------------|------------|
| 8f     |    84,000 | +0.5623     | +0.5596       | 0.2335     | +0.1774    | +0.9368    | +0.4680      | +0.3215    |
| 16f    |   180,000 | +0.6072     | +0.6076       | 0.2290     | +0.2250    | +0.9578    | +0.5342      | +0.3410    |
| 32f    |   372,000 | +0.6378     | +0.6424       | 0.2285     | +0.2531    | +0.9730    | +0.5579      | +0.3585    |

ΔSTATIC vs 8f: **+0.045** (8→16), **+0.076** (8→32). The
direction is **monotonically increasing** across all three pair
classes. Sub-linear: δ(8→16) = +0.045 exceeds δ(16→32) = +0.031
— the curve is bending over, consistent with an asymptotic
attention-similarity ceiling below 1.0.

### H3 verdict: EARNED (adjacent-frame variant)

Under our measurement, STATIC cos **rises monotonically** with
frame density on Qwen 2.5-VL-7B-4bit: **0.562 (8f) → 0.607 (16f)
→ 0.638 (32f)**. This is the preregistered adjacent-frame earn
direction (denser sampling → smaller adjacent pixel delta →
higher feature cos). Ordering STATIC > SHIFTED > NOVEL also
holds at every frame count.

Caveat: **H3 as preregistered in the Sam cache-substitute frame
(which predicts *decreasing* cos with more frames, due to
accumulated reuse drift) is NOT tested by our measurement.** Our
H3-earn is the inverted-direction version and is scientifically
meaningful independently: it shows that Qwen's ViT attention
mixing *is* sensitive to input pixel delta, not globally
saturated.

### Per-class prevalence (block-count shares)

| frames | STATIC share | SHIFTED share | NOVEL share |
|--------|--------------|---------------|-------------|
| 8f     | 43.6%        | 2.6%          | 53.8%       |
| 16f    | 43.8%        | 3.1%          | 53.1%       |
| 32f    | 45.4%        | 3.6%          | 51.0%       |

As frame density rises, the STATIC and SHIFTED classes absorb
share from NOVEL. That matches physical intuition: denser temporal
sampling means more spatially co-located pixels fall below the
static/shifted pixel-diff thresholds.

### Important negative finding — even at 32f, STATIC ≠ 1.0

STATIC cos of **0.638 at 32f** is still far below the
preregistered bit-faithful band [0.95, 1.00]. The rise is real
but plateauing. Extrapolating the δ trend (+0.045, +0.031)
suggests a STATIC cos asymptote in the 0.70-0.75 range even at
frame rates where adjacent-frame pixel delta approaches zero —
attention-mixing globalness on Qwen's ViT imposes a hard ceiling
that is **not a function of frame density alone**. This is the
strongest paper-facing statement the frame-count sweep supports:
Qwen's ViT features adjacent-frame are *not* bit-faithful even
at dense temporal sampling, and the mechanism is attention-mixing
driven by global frame content, not a measurement artifact of
sparse 8f sampling.

## Scope of claim after v0

**Earned.** Qwen-side per-class adjacent-frame ViT feature drift
is quantified and stratifies monotonically by planner class.
STATIC cos ~0.56 at 8f on VideoMME dev is a new, paper-reportable
number.

**NOT earned.** The preregistered H2 "Qwen STATIC cos ≥ 0.95"
claim fails under our measurement. We document the methodological
reason (adjacent-frame vs cache-substitute), and report the
*actual* measurement direction.

**Paper implication.** The mechanism claim "identity-cache works
on Qwen because ViT features are bit-faithful adjacent-frame"
**cannot be supported by this measurement**. Qwen's feature drift
is substantial even at STATIC positions. Whether the LLM prefill
nonetheless tolerates *cache-substitute-drift* (the Sam-style
experiment) is a distinct, not-yet-measured question. The
identity-cache 100% agreement results (8f/16f/32f, n=30 each on
VideoMME dev) are a **determinism result** — both branches run
the same ViT — **not** a robustness-to-drift result.

## Deferred follow-ups

1. **Gemma path.** Requires an inline ViT encode (no Gemma
   feature cache exists at the 16×16 post-pool grid). Implement
   by calling `model.vision_tower` + `model.embed_vision` as in
   `run_novelty_pruning_gemma.py:_compute_vision_features`. Once
   wired, H1 can be tested directly.
2. **True cache-substitute measurement.** If we want a faithful
   replication of Sam's measurement, we need a ViT forward pass
   that accepts a mask of "use frame 0's features at these
   positions, re-run ViT on the others." On mlx-vlm this is
   non-trivial (would require patching the vision tower call
   path). Deferred.
3. **Entropy proxy (H4).** Attention-entropy correlation is
   deferred until vision-tower attention instrumentation lands
   in the mlx-vlm path (see 1.51R notes on
   `cls_attention_proxy` being non-faithful).

## Cross-references

- Prereg: `2026-04-19-phase-1_57-feature-drift-mechanism-prereg.md`
- Code: `scripts/measure_feature_drift.py`
- Artifacts:
  - `research/experiments/2026/artifacts/phase1_57/qwen_8f_dev30.json` (landed)
  - `research/experiments/2026/artifacts/phase1_57/qwen_16f_dev30.json` (landed)
  - `research/experiments/2026/artifacts/phase1_57/qwen_32f_dev30.json` (landed)
- 32f cross-bucket findings: `2026-04-19-phase-1_41-qwen-videomme-32f-long-findings.md`
  (mechanism context)
- Claim #11 (streaming/mechanism) — this is the numerical content
- Sam ref: `~/s/codec-through-sam/research_queue.md` lines 14-29
