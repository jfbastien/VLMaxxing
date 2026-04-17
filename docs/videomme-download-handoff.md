# VideoMME download handoff

**Audience**: the human user. Machine agents cannot complete this step;
the VideoMME video bundle is gated and must be fetched interactively
from an external host.

**Status at time of writing (2026-04-17)**:

- Metadata (parquet manifests + README) is already fetched:
  `data/benchmarks/videomme/hf/videomme/*.parquet` exist on disk.
- Video assets directory exists but is EMPTY:
  `data/benchmarks/videomme/videos/` → 0 files.
- Until videos land, `scripts/run_benchmark_track_a.py --benchmark videomme`
  cannot start; the loader will fail at first video open.

## What to download

**Source of truth**: https://video-mme.github.io/home_page.html

Per the VideoMME authors (§ "Dataset Download" on the home page), the
dataset ships as:

- A **Hugging Face mirror** for parquet metadata at
  `lmms-lab/Video-MME` (which we already fetched). This mirror does
  **NOT** host the video files — only the questions, options, and
  video IDs.
- A separate **video bundle**, linked from the home page under
  "Videos", hosted by the authors. Follow the current link on the
  official home page — exact URLs change over time and I don't want
  to hard-code a URL here that may rot (user-visible URL rot was
  specifically flagged as an anti-pattern in the system rules).
- Some mirrors exist on Hugging Face under individual users
  (e.g. `lyx97/Video-MME` with `videos_chunked_*.zip` files). If the
  official host is slow or rate-limited, search HF for
  `Video-MME videos chunked` — but **verify the SHA256 of the
  resulting video files against any hashes the authors publish**
  before using a mirror.

The total corpus is **~900 videos** spanning short/medium/long/very-long
durations, **~80 GB** after unpack (as of 2025 — check the current
home-page estimate).

## Where to put it

**Target layout** (matches the existing `data/benchmarks/{tomato, mvbench, videomme}/` pattern):

```
data/benchmarks/videomme/
├── SOURCE.json                 # already present; do not delete
├── hf/
│   ├── README.md               # already present
│   └── videomme/
│       └── videomme_test.parquet  # already present; metadata
├── downloads/                  # scratch for zip/tar staging
│   └── (your downloaded archives go here, then unpack into videos/)
└── videos/
    └── <video_id>.mp4           # flat directory of videos, one per row in the parquet
```

**Critical**: the loader (`scripts/run_benchmark_track_a.py`,
`VIDEOMME_VIDEO_DIR = Path("data/benchmarks/videomme/videos")`) expects
a **flat directory of videos**, keyed by the video identifier that the
parquet uses. Do **NOT** preserve an intermediate `video_id_chunks/`
layer — move all files to the top of `videos/`.

## Recommended procedure (exact commands)

1. **Download from the official VideoMME page into `downloads/`**:
   ```bash
   cd /Users/jfb/s/codec-through/data/benchmarks/videomme/downloads
   # fetch whatever archives the home page offers — wget, curl, or
   # a browser download; keep the originals here.
   ```

2. **Unpack into `videos/`** (exact command depends on archive format):
   ```bash
   cd /Users/jfb/s/codec-through/data/benchmarks/videomme
   # if single zip:
   unzip downloads/VideoMME_videos.zip -d videos/
   # if chunked (e.g., videos_chunked_0.zip .. videos_chunked_N.zip):
   for f in downloads/videos_chunked_*.zip; do unzip "$f" -d videos/; done
   # flatten if unpack preserved subdirectories:
   find videos -mindepth 2 -name "*.mp4" -exec mv -i {} videos/ \;
   find videos -type d -empty -delete
   ```

3. **Verify count and naming**:
   ```bash
   cd /Users/jfb/s/codec-through/data/benchmarks/videomme
   ls videos/*.mp4 | wc -l
   # Expect ≈ 900 (VideoMME Test set).

   # Cross-check that the video IDs in the parquet match file names:
   uv run python - <<'PY'
   import pandas as pd
   from pathlib import Path
   df = pd.read_parquet("hf/videomme/videomme_test.parquet")
   vids = set(Path("videos").glob("*.mp4"))
   want = set(Path("videos") / f"{v}.mp4" for v in df["video_id"].unique())
   missing = want - vids
   print(f"{len(vids)} files present, {len(missing)} missing from parquet")
   if missing:
       print("Sample missing:", list(missing)[:5])
   PY
   ```
   If > 0 missing after unpack, the naming convention used by the
   archive doesn't match the parquet — check the VideoMME authors'
   README in `hf/README.md` for the naming scheme (usually
   `<videoID>.mp4`).

4. **Probe the loader** (~5 s, no MLX):
   ```bash
   cd /Users/jfb/s/codec-through
   uv run python scripts/fetch_benchmarks.py --dataset videomme --mode all --dry-run
   # If both "metadata present" and "assets present" print cleanly,
   # the handoff is complete.
   ```

5. **Once videos are in place**, phase 1.41 is unblocked. Kick off
   N=30 Qwen + VideoMME with:
   ```bash
   uv run python scripts/run_benchmark_track_a.py run \
     --benchmark videomme \
     --manifest research/benchmark_manifests/videomme_dev_v2.toml \
     --frame-count 8 \
     --statistic max_abs --static-threshold 8.0 --shifted-threshold 32.0 \
     --reuse-classes static,shifted --max-age 4 \
     --output-path research/experiments/2026/artifacts/phase1_41_videomme_qwen_n30/cached.jsonl \
     --summary-path research/experiments/2026/artifacts/phase1_41_videomme_qwen_n30/cached_summary.json
   ```
   (Actual manifest path TBD — not yet checked in.)

## Disk budget and hash provenance

- Reserve **~80 GB** for `videos/` after unpack.
- Reserve **~40 GB** for `downloads/` during transfer (can delete
  afterwards).
- Record SHA256 sums of every unpacked `*.mp4` in `data/benchmarks/videomme/SOURCE.json`
  so downstream runs are reproducible. `shasum -a 256 videos/*.mp4 > checksums.txt`.

## Why this can't be automated

The VideoMME video host requires interactive agreement to the dataset
license; our agent environment cannot accept that on the user's behalf.
This is the only benchmark blocker where the agent cannot do the work
itself — everything else ran autonomously.

## Once this lands

- Unblocks phase 1.41 Qwen + VideoMME N=30 (claim 8).
- Unblocks phase 1.51 novelty-pruning on Gemma + VideoMME N=30 (claim 11 — the big-numbers headline).
- Unblocks phase 1.52 combined temporal+spatial on Gemma + VideoMME (claim 10).

These three phases are **the entire Lane B (Gemma big-numbers) critical
path**. VideoMME videos on disk is the single external-blocker before
Lane B can execute autonomously.
