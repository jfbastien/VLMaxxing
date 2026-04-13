# Clip Policy

This repo does not check media into git.

Media stays local. The repo tracks only:

- manifest metadata
- download or reproduction instructions
- local generator scripts
- experiment notes that reference local clip ids

## Corpus Tiers

### 1. Primary Local Corpus

Use stable, publicly accessible clips with explicit provenance.

Current initial set:

- Xiph/Derf low-motion proxies:
  - `xiph_akiyo_cif`
  - `xiph_news_cif`
- Xiph/Derf motion/detail proxies:
  - `xiph_coastguard_cif`
  - `xiph_mobile_cif`

Why this set:

- small enough for quick local bring-up
- stable enough for long-lived reproducibility
- diverse enough to separate low-motion from higher-motion behavior early

These clips are downloaded locally and then re-encoded locally with fixed codec
settings for codec-metadata experiments.

### 2. Synthetic Local Stress Corpus

Keep a generated local tier for controlled failure analysis:

- `synthetic_affine_pan`
- `synthetic_scene_cut`
- `synthetic_fullframe_flicker`
- `synthetic_color_swap`
- `synthetic_small_object`
- `synthetic_screen_ocr`

Why this tier exists:

- reproducible without checking media into git
- exact answer keys are possible
- lets us stress OCR, color, small-object, flicker, and scene-cut behavior

These clips are generated locally by:

- `scripts/generate_synthetic_corpus.py`

### 3. Benchmark-Native Assets

Use TOMATO and MVBench clips exactly as shipped by their datasets when running
benchmark comparisons.

These assets are for benchmark comparability, not for the local primary corpus.

### 4. Predecessor Cross-Check Set

Keep the predecessor repo's three YouTube clips as a local cross-check only:

- `crosscheck_talking_head`
- `crosscheck_surveillance`
- `crosscheck_fpv_drone`

Use them only to compare against predecessor-specific claims or plots.

Do not use them as primary paper evidence because the bitstreams and licensing
are not stable enough.

## Local Directory Layout

Recommended local layout:

```text
data/
└── corpus/
    ├── raw/
    ├── derived/
    └── crosscheck/
    └── synthetic/
```

Do not commit downloaded media.

## Initial Setup Commands

Create local directories and fetch the primary corpus:

```bash
uv run python scripts/fetch_corpus.py --tier primary --encode
```

Generate the synthetic local stress corpus:

```bash
uv run python scripts/generate_synthetic_corpus.py
```

Optional predecessor cross-check downloads:

```bash
uv run python scripts/fetch_corpus.py --tier crosscheck
```

The primary local pilot does not require the YouTube cross-check set.

## Benchmark-Native Assets

TOMATO and MVBench assets are not automated yet in this repo.

Use them only after:

- Phase 0.5
- Phase 0.75
- the local synthetic and Xiph bring-up work is stable

When that setup lands, it should preserve the dataset-native structure instead
of inventing a custom local derivative without documentation.

## What Comes Later

Planned later, not part of the initial local setup:

- UVG 4K sequences once we pin exact download URLs and local handling
- one more public natural-motion clip if the current Xiph set proves too narrow
- benchmark-native dataset helpers once the local suite is stable

## Source Notes

- Xiph/Derf is appropriate for stable local bring-up because Xiph documents the
  set as publicly accessible test media believed to be freely redistributable
  with per-sequence copyright notes where available.
- The predecessor YouTube clips remain useful for local cross-checks, but they
  are not stable enough to carry primary evidence.
