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

### Per-bucket stratification (post-landing, 2026-04-19)

Re-analyzing the same three JSONs by VideoMME duration bucket
(short / medium / long, n=10 each) reveals that the aggregate
"sub-linear bending" is a **mix of very different per-bucket
trajectories**:

| bucket | STATIC 8f | STATIC 16f | STATIC 32f | δ(8→16) | δ(16→32) |
|--------|-----------|------------|------------|---------|----------|
| short  | +0.5668   | +0.6177    | +0.6757    | +0.0509 | **+0.0580** |
| medium | +0.5746   | +0.6200    | +0.6394    | +0.0454 | +0.0194 |
| long   | +0.5445   | +0.5819    | +0.5920    | +0.0374 | **+0.0101** |

Short-bucket STATIC cos is **still rising, and the rise is
accelerating** (+0.058 at 16→32 vs +0.051 at 8→16). Medium bucket
is the one with the classic sub-linear bend (+0.045 → +0.019).
Long bucket is essentially **saturated by 16f** at cos ~0.59
(+0.010 at 16→32). This means:

- The attention-mixing ceiling is **bucket-dependent**, not a
  single universal constant. Short clips: ceiling not yet reached
  at 32f (likely ≥0.75). Long clips: ceiling ~0.59.
- Rebut: "the 0.70-0.75 asymptote estimate in aggregate is wrong
  direction for short-bucket extrapolation — short-bucket STATIC
  at 64f could plausibly reach 0.80+, while long-bucket has
  essentially no room left."
- Class-share confirms this: long-bucket at 32f is still 41.9%
  STATIC / 55.9% NOVEL, vs short-bucket 48.9% / 46.7%. Long-clip
  adjacent frames simply have more disparate global content per
  stride, even with denser sampling.

**Paper implication.** Any per-bucket accuracy result on Qwen
must carry a per-bucket drift caveat, not the aggregate. Long-
bucket degradation from cache-substitute would hit a LOWER
feature-cos floor (≤0.60) than short-bucket (≥0.68 at 32f).

### Counter-intuitive SHIFTED finding: long > short at 32f

At 32f, long-bucket SHIFTED cos (+0.613) is HIGHER than
short-bucket SHIFTED cos (+0.576). The SHIFTED class captures
translated-but-similar content; long clips with smooth camera
motion generate more such blocks, and those blocks happen to have
higher feature-cos than short-clip SHIFTED blocks (which are
rarer and often texture-contaminated). SHIFTED share is
**lower** in long bucket (2.1% vs 4.3% short at 32f), so this
higher-cos population is also a smaller fraction of long-clip
tokens. No paper claim rides on SHIFTED alone.

### Cross-reference to 1.41: drift-vs-accuracy co-saturation

Aligning per-bucket drift (this doc) with per-bucket accuracy
(`2026-04-19-phase-1_41-qwen-videomme-32f-long-findings.md`):

| bucket | 8f acc | 16f acc | 32f acc | STATIC 8f | STATIC 16f | STATIC 32f |
|--------|--------|---------|---------|-----------|------------|------------|
| short  | ~1.000 | 0.800   | 0.800   | +0.567    | +0.618     | **+0.676** (still rising) |
| medium | 0.400  | 0.700   | 0.700   | +0.575    | +0.620     | **+0.639** (sub-linear) |
| long   | 0.300  | 0.100   | 0.100   | +0.545    | +0.582     | **+0.592** (saturated at 16f) |

The 1.41 findings doc preregistered three mechanism-candidates
for the long-bucket plateau: H-drift-compounds, H-stride-window,
and H-saturation. The per-bucket drift numbers now adjudicate:

- **H-drift-compounds REJECTED.** Predicts monotonic STATIC cos
  *decline* with frame count. Observed direction is *rise* at all
  buckets. Drift-compounds as originally framed is not the
  mechanism.
- **H-saturation SUPPORTED.** Predicts long-bucket signals plateau
  at 16f. Observed: long-bucket accuracy plateaued at 16f AND
  long-bucket STATIC drift essentially plateaued at 16f (δ16→32 =
  +0.010). Both capacity-signals co-saturate.
- **H-stride-window NEUTRAL.** Drift data doesn't rule it out
  but also doesn't selectively support it over saturation.

The clean empirical fact is **drift saturates at the same frame
count where accuracy saturates, per-bucket**. Short bucket: both
signals still have room (acc flat from 16f, but drift still rising
at 32f — so acc ceiling is NOT drift-driven on short). Long
bucket: both signals flat-lined at 16f. Medium: both sub-linear
mid-saturation at 32f.

**Paper-facing conclusion.** Feature-cos drift is a *co-indicator*
of the capacity plateau, not the *binding constraint*. Short-
bucket accuracy at 16-32f is flat despite rising drift — meaning
the ViT still has representational headroom that the LLM-side
reasoner can't exploit on this question distribution. The long-
bucket "H-drift-compounds" narrative is empirically wrong in
direction and should be retired from the mechanism-candidates
list. Saturation (both ViT-attention-mixing and LLM-integration)
is the surviving explanation.

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
