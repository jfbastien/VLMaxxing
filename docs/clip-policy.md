# Clip Policy

This repo does not check fetched or source media into git.

Generated static figures and thumbnails may be committed when they are paper,
README, or review artifacts. Generated videos are heavier and may include
benchmark-derived frames; keep them out of git unless they are deliberate
review or publication artifacts with adjacent provenance and regeneration
notes.

Fetched and source media stays local. The repo tracks only:

- manifest metadata
- download or reproduction instructions
- local generator scripts
- experiment notes that reference local clip ids
- generated static figures and thumbnails needed for the paper, README, or
  review
- exceptional generated videos with explicit provenance notes

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
- Xiph/Derf surveillance-like proxy:
  - `xiph_hall_monitor_cif`

Why this set:

- small enough for quick local bring-up
- stable enough for long-lived reproducibility
- diverse enough to separate low-motion, surveillance-like, and higher-motion
  behavior early

These clips are downloaded locally and then re-encoded locally with fixed codec
settings for codec-metadata experiments.

### 2. Synthetic Local Stress Corpus

Keep a generated local tier for controlled failure analysis:

- `synthetic_affine_pan`
- `synthetic_affine_pan_v2`
- `synthetic_scene_cut`
- `synthetic_scene_cut_v2`
- `synthetic_fullframe_flicker`
- `synthetic_color_swap`
- `synthetic_mid_color_flash`
- `synthetic_small_object`
- `synthetic_screen_ocr`
- `synthetic_mid_text_flash`

Why this tier exists:

- reproducible without checking media into git
- exact answer keys are possible
- lets us stress OCR, color, small-object, flicker, and scene-cut behavior
- lets us build temporal-necessity items where the middle matters and the
  endpoints alone are insufficient

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
    ├── crosscheck/
    └── synthetic/
```

Do not commit downloaded media or raw benchmark assets. Generated videos should
normally be regenerated locally; if committed as review artifacts, keep an
adjacent manifest or README documenting provenance and regeneration.

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

TOMATO and MVBench metadata/assets are handled by
[docs/benchmark-setup.md](benchmark-setup.md) and
`scripts/fetch_benchmarks.py`. VideoMME uses the same benchmark root but fetches
videos by checked manifest subset; see
[docs/videomme-download-handoff.md](videomme-download-handoff.md).

Keep benchmark-native source assets in their dataset-native layout under
ignored `data/benchmarks/` paths. Do not turn them into a custom committed
derived dataset. Small generated review or publication previews may be
committed only with adjacent provenance and regeneration notes.

## What Comes Later

Planned later, not part of the initial local setup:

- UVG 4K sequences once we pin exact download URLs and local handling
- one more public natural-motion clip if the current Xiph set proves too narrow

## Source Notes

- Xiph/Derf is appropriate for stable local bring-up because Xiph documents the
  set as publicly accessible test media believed to be freely redistributable
  with per-sequence copyright notes where available.
- The predecessor YouTube clips remain useful for local cross-checks, but they
  are not stable enough to carry primary evidence.
