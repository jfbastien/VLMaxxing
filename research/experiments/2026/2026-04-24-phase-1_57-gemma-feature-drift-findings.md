# Phase 1.57 — Gemma feature-drift findings

Date: 2026-04-24
Status: findings
Parent prereg: `2026-04-19-phase-1_57-feature-drift-mechanism-prereg.md`
Cross-reference: `2026-04-19-phase-1_57-feature-drift-findings.md` (Qwen)

## Why this note exists

The original 1.57 findings note landed the adjacent-frame feature-drift ladder
for Qwen and explicitly left Gemma deferred. That gap is now closed for the
Gemma cached-feature path used by local Track A work.

This run also corrected a real implementation mistake that matters for future
Gemma experiments: the live `encode_image(...)` cached-feature path in the
current `mlx-vlm` Gemma4 stack does **not** emit the earlier assumed
`256`-token square layout per 560×560 frame. On this path the vision pooler
reduces the 35×35 patch grid to **133 pooled cached tokens per frame**. The
measurement below uses that live pooled-token geometry, not the stale square
assumption.

## Methodology correction

For Gemma, adjacent-frame cosine is measured on the **cached-feature sequence
actually returned by `model.encode_image(...)`**:

- input frames: 560×560 square-padded benchmark frames
- live patch grid: 35×35 at `patch_size=16`
- live pool rule: `pooling_kernel_size=3`, `default_output_length=280`
- live cached-feature output: **133 pooled tokens per frame**

Planner labels are assigned by:

1. computing the planner statistic on the 35×35 patch grid
2. grouping those patch scores with the same pooled-token assignment rule the
   Gemma pooler uses
3. thresholding the grouped scores into STATIC / SHIFTED / NOVEL

This preserves the prereg's intended question, but with the correct local
Gemma geometry rather than the stale `16×16 / 256` assumption.

## Commands

```bash
uv run python scripts/measure_feature_drift.py \
  --model gemma \
  --model-path ~/models/gemma-4-e4b-it-4bit \
  --manifest research/benchmark_manifests/videomme_dev_v1.toml \
  --group long \
  --frame-count 8 \
  --output research/experiments/2026/artifacts/phase1_57_gemma/gemma_8f_long.json

uv run python scripts/measure_feature_drift.py \
  --model gemma \
  --model-path ~/models/gemma-4-e4b-it-4bit \
  --manifest research/benchmark_manifests/videomme_dev_v1.toml \
  --group long \
  --frame-count 16 \
  --output research/experiments/2026/artifacts/phase1_57_gemma/gemma_16f_long.json

uv run python scripts/measure_feature_drift.py \
  --model gemma \
  --model-path ~/models/gemma-4-e4b-it-4bit \
  --manifest research/benchmark_manifests/videomme_dev_v1.toml \
  --group long \
  --frame-count 32 \
  --output research/experiments/2026/artifacts/phase1_57_gemma/gemma_32f_long.json
```

## Artifacts

- `research/experiments/2026/artifacts/phase1_57_gemma/gemma_8f_long.json`
- `research/experiments/2026/artifacts/phase1_57_gemma/gemma_16f_long.json`
- `research/experiments/2026/artifacts/phase1_57_gemma/gemma_32f_long.json`

## Results

All three runs landed on the VideoMME dev **long** bucket (`n=10` items):

| frames | items_ok | n_samples | STATIC mean | STATIC p05 | STATIC p95 | SHIFTED mean | NOVEL mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| 8f  | 10 |  9,310 | 0.7689 | 0.2513 | 0.9809 | 0.5640 | 0.2968 |
| 16f | 10 | 19,950 | 0.7940 | 0.2806 | 0.9830 | 0.6388 | 0.3002 |
| 32f | 10 | 41,230 | 0.8074 | 0.3065 | 0.9827 | 0.6490 | 0.3130 |

Ordering is preserved at every frame count:

- `STATIC > SHIFTED > NOVEL`

STATIC rises monotonically with frame density:

- `0.7689 < 0.7940 < 0.8074`

## Hypothesis verdicts

| hypothesis | prereg band | observed | verdict |
|---|---|---|---|
| H1 Gemma STATIC in `[0.60, 0.85]` | `[0.60, 0.85]` | 0.7689 / 0.7940 / 0.8074 | **EARNED** at 8f, 16f, and 32f |
| H3 Gemma STATIC decreases monotonically across `8f → 16f → 32f` | monotonic ↓ | 0.7689 / 0.7940 / 0.8074 | **FALSIFIED in the opposite direction** |

## Interpretation

### 1. Gemma does not support a "drift gets worse with more frames" story

The preregistered monotonic-decrease story is not what happened. On the long
bucket, adjacent-frame STATIC cosine **increases** with denser sampling. That
puts Gemma in the same qualitative direction as the Qwen adjacent-frame result,
not in an opposite-direction failure mode.

### 2. Gemma's cached-feature path is substantially more stable than Qwen's

Qwen long-bucket STATIC cosine from the earlier 1.57 note was:

- `8f: 0.5445`
- `16f: 0.5819`
- `32f: 0.5920`

Gemma long-bucket STATIC cosine is materially higher at every matched frame
count:

- `8f: 0.7689`
- `16f: 0.7940`
- `32f: 0.8074`

This is the clearest local evidence so far that reuse fidelity is
**architecture-conditioned in magnitude, not just in sign**. Both models show
the same directional response to denser temporal sampling, but Gemma's pooled
cached features are much closer adjacent-frame under the same bucket and frame
budgets.

### 3. This weakens "drift-compounds" as the dominant explanation for the Qwen long-bucket pathology

If Gemma's all-global cached-feature path had shown a monotonic collapse with
frame count, it would have strengthened a universal "global-attention drift
compounds with longer contexts" story. It did not. Instead, Gemma remains in a
high-cosine regime and improves with denser sampling.

That does **not** prove Gemma cache-substitute reuse is safe; this remains an
adjacent-frame fresh-vs-fresh lower-bound proxy, not a true cache-substitute
measurement. But it does say the mechanism is more architecture-specific than a
single universal drift-collapse story would imply.

### 4. The next experiment is now cleaner, not riskier

Phase 1.42 is still the fidelity benchmark that matters for claim #7. But this
1.57 result de-risks it substantially:

- the Gemma cached-feature path is wired and measurable
- the cached-feature geometry is now corrected
- the local mechanism evidence points in the *favorable* direction for Gemma

So 1.42 should now be interpreted as a benchmarking question, not as a blind
integration gamble.
