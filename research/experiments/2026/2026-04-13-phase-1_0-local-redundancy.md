# Phase 1.0: Local Redundancy Measurement

## Preregistration

Hypothesis:

- the local primary and synthetic clip buckets will show materially different
  static, shifted, and novel ratios under the current Qwen-aligned pixel-diff
  baseline

Track:

- A-supporting measurement

Primary metrics:

- mean static ratio across adjacent frame pairs
- mean shifted ratio across adjacent frame pairs
- mean novel ratio across adjacent frame pairs

Secondary metrics:

- mean reused ratio across adjacent frame pairs
- clip-level spread across content buckets

Unit of analysis:

- adjacent frame pair within a fixed contiguous window

Clip set:

- `xiph_akiyo_cif`
- `xiph_news_cif`
- `xiph_coastguard_cif`
- `xiph_mobile_cif`
- `synthetic_affine_pan`
- `synthetic_scene_cut`
- `synthetic_fullframe_flicker`
- `synthetic_color_swap`
- `synthetic_small_object`
- `synthetic_screen_ocr`

Sampling mode:

- `contiguous_window`

Window policy:

- Xiph clips: frames `0-11`
- synthetic clips: frames `18-29`

Preprocessing:

- decode backend: `pyav`
- colorspace: RGB
- no padding
- Qwen-aligned resize to exact `28 px` block multiples with target height
  `252 px`

Thresholds:

- default pixel-diff thresholds `(3, 8)`

Acceptance band:

- at least three clip buckets differ meaningfully in their reused ratio and the
  synthetic hard-cut or flicker buckets are not degenerate with the low-motion
  Xiph buckets

Rejection band:

- all local buckets cluster tightly enough that the local pilot would not test
  distinct temporal regimes

Inconclusive:

- preprocessing or frame selection issues dominate the ratios

## Execution

Run date:

- 2026-04-13

Decode and preprocessing:

- decode backend: `pyav`
- colorspace: RGB
- sampling mode: `contiguous_window`
- no padding
- Qwen-aligned resize to exact `28 px` multiples with target height `252 px`

Windows:

- Xiph clips: frames `0-11`
- synthetic clips: frames `18-29`

Thresholds:

- default pixel-diff thresholds `(3, 8)`

Artifact:

- [phase1_0.json](artifacts/phase1_0.json)

## Result

Accepted.

Clip-level reused ratios:

- `xiph_akiyo_cif`: `1.000`
- `xiph_news_cif`: `0.959`
- `xiph_coastguard_cif`: `0.595`
- `xiph_mobile_cif`: `0.214`
- `synthetic_affine_pan`: `1.000`
- `synthetic_scene_cut`: `0.909`
- `synthetic_fullframe_flicker`: `0.019`
- `synthetic_color_swap`: `0.990`
- `synthetic_small_object`: `0.985`
- `synthetic_screen_ocr`: `0.997`

Key spread:

- lowest reuse: full-frame flicker (`0.019`)
- highest reuse: talking-head proxy and synthetic affine pan (`1.000`)
- moderate middle bucket: coastguard (`0.595`)
- low-reuse natural stress case: mobile (`0.214`)

Important nuance:

- `synthetic_scene_cut` still averaged `0.909` reused ratio because only one adjacent pair in the `12`-frame window crosses the cut
- this means average reuse can hide semantically critical one-step novelty bursts

## Interpretation

The corpus is not degenerate.

What got stronger:

- the local clip set spans genuinely different temporal regimes before any semantic-substitution comparison
- the synthetic stress tier is doing useful work, especially for novelty amplification and scene cuts

What this implies for the next phase:

- perfect or near-perfect reuse on several synthetic clips does not imply semantic triviality
- scene-cut and global-motion buckets need event-sensitive interpretation, not just average reuse summaries

## Links

- [PLAN.md](../../../PLAN.md)
- [docs/methodology/preprocessing.md](../../../docs/methodology/preprocessing.md)
- [research/prompt_bank/local_suite_v1.toml](../../prompt_bank/local_suite_v1.toml)
- [phase1_0.json](artifacts/phase1_0.json)
