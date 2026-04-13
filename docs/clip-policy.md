# Clip Policy

This repo does not check media into git.

Media stays local. The repo tracks only:

- manifest metadata
- download or reproduction instructions
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

### 2. Benchmark-Native Assets

Use TOMATO and MVBench clips exactly as shipped by their datasets when running
benchmark comparisons.

These assets are for benchmark comparability, not for the local primary corpus.

### 3. Predecessor Cross-Check Set

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
```

Do not commit downloaded media.

## Initial Download Commands

Create local directories:

```bash
mkdir -p data/corpus/raw data/corpus/derived data/corpus/crosscheck
```

Download the primary Xiph clips:

```bash
curl -L https://media.xiph.org/video/derf/y4m/akiyo_cif.y4m -o data/corpus/raw/akiyo_cif.y4m
curl -L https://media.xiph.org/video/derf/y4m/news_cif.y4m -o data/corpus/raw/news_cif.y4m
curl -L https://media.xiph.org/video/derf/y4m/coastguard_cif.y4m -o data/corpus/raw/coastguard_cif.y4m
curl -L https://media.xiph.org/video/derf/y4m/mobile_cif.y4m -o data/corpus/raw/mobile_cif.y4m
```

Encode local H.264 derivatives with a fixed policy:

```bash
ffmpeg -y -i data/corpus/raw/akiyo_cif.y4m -c:v libx264 -preset medium -crf 18 -g 30 -pix_fmt yuv420p data/corpus/derived/akiyo_cif_h264_crf18_g30.mp4
ffmpeg -y -i data/corpus/raw/news_cif.y4m -c:v libx264 -preset medium -crf 18 -g 30 -pix_fmt yuv420p data/corpus/derived/news_cif_h264_crf18_g30.mp4
ffmpeg -y -i data/corpus/raw/coastguard_cif.y4m -c:v libx264 -preset medium -crf 18 -g 30 -pix_fmt yuv420p data/corpus/derived/coastguard_cif_h264_crf18_g30.mp4
ffmpeg -y -i data/corpus/raw/mobile_cif.y4m -c:v libx264 -preset medium -crf 18 -g 30 -pix_fmt yuv420p data/corpus/derived/mobile_cif_h264_crf18_g30.mp4
```

Optional predecessor cross-check downloads:

```bash
yt-dlp -f "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]" --download-sections "*0:00-0:30" -o "data/corpus/crosscheck/talking_head.%(ext)s" "https://www.youtube.com/watch?v=DxREm3s1scA"
yt-dlp -f "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]" --download-sections "*0:30-1:00" -o "data/corpus/crosscheck/surveillance.%(ext)s" "https://www.youtube.com/watch?v=MNn9qKG2UFI"
yt-dlp -f "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]" --download-sections "*0:10-0:40" -o "data/corpus/crosscheck/fpv_drone.%(ext)s" "https://www.youtube.com/watch?v=YPNtouPtkJY"
```

## What Comes Later

Planned later, not part of the initial local setup:

- UVG 4K sequences once we pin exact download URLs and local handling
- explicit screen-content corpus entries
- a scripted fetcher that reads the checked-in manifest

## Source Notes

- Xiph/Derf is appropriate for stable local bring-up because Xiph documents the
  set as publicly accessible test media believed to be freely redistributable
  with per-sequence copyright notes where available.
- The predecessor YouTube clips remain useful for local cross-checks, but they
  are not stable enough to carry primary evidence.
