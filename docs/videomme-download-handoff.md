# VideoMME download handoff

**Audience**: primarily machine agents; optionally the human user. Round-17b
update: Video-MME videos ARE on Hugging Face now, and our checked-in paper
protocol only needs a 57-video manifest subset, not the full ~900-video corpus.

**Status (2026-04-17 round-17b rewrite)**:

- Metadata (parquet manifests + README) already fetched:
  `data/benchmarks/videomme/hf/videomme/test-00000-of-00001.parquet` present,
  2,700 rows.
- Video assets directory exists but is EMPTY at rewrite time:
  `data/benchmarks/videomme/videos/` → 0 files.
- Authors' HF mirror `lmms-lab/Video-MME` does host the videos, as 20
  chunked zip archives `videos_chunked_{01..20}.zip`, ~5 GB each,
  **~101 GB total** for the full corpus.
- The checked-in paper protocol (phase 1.41 Qwen dev+holdout) needs
  only **57 unique videoIDs** (29 dev + 29 holdout, 1 overlap),
  ≈ 3–15 GB on disk after extraction. Fetching the full 101 GB
  corpus is wasteful and blocked as the default path.

## What this repo actually needs

The loader keys on the parquet `videoID` column (YouTube IDs like
`fFjv93ACGo8`), NOT the `video_id` column (a row index like `001`).
See `scripts/run_benchmark_track_a.py:420-441`.

The checked-in manifests are:

- `research/benchmark_manifests/videomme_dev_v1.toml` — 29 unique videoIDs
- `research/benchmark_manifests/videomme_holdout_v1.toml` — 29 unique videoIDs
- union (with one overlap) = **57 unique videoIDs**

A videoID inventory and URL list (for spot-check / manual fallback) is in
the parquet `url` column — each row has both the videoID and the original
YouTube URL it came from. You can dump the subset with:

```bash
cd /Users/jfb/s/codec-through
.venv/bin/python scripts/fetch_videomme_subset.py \
    --manifest research/benchmark_manifests/videomme_dev_v1.toml \
    --manifest research/benchmark_manifests/videomme_holdout_v1.toml \
    --dry-run
```

## Default path: subset fetch from the HF mirror (CPU-only, scriptable)

```bash
cd /Users/jfb/s/codec-through

# Dev-first (29 videos; smallest unblock for phase 1.41 dev tranche):
.venv/bin/python scripts/fetch_videomme_subset.py \
    --manifest research/benchmark_manifests/videomme_dev_v1.toml \
    --cache-dir data/benchmarks/videomme/downloads/hf_cache

# Or full paper subset (57 videos; dev+holdout for the full phase 1.41 run):
.venv/bin/python scripts/fetch_videomme_subset.py \
    --manifest research/benchmark_manifests/videomme_dev_v1.toml \
    --manifest research/benchmark_manifests/videomme_holdout_v1.toml \
    --cache-dir data/benchmarks/videomme/downloads/hf_cache
```

The fetcher walks the 20 `videos_chunked_*.zip` archives one at a time,
extracts only the wanted videoIDs from each chunk, and deletes each chunk
after. Peak disk use is ≈ one chunk (~5 GB) plus the growing extracted
subset. Typical early termination: after ~4–10 chunks, depending on how
the wanted videoIDs are distributed.

### Environment gotchas on this machine

The local venv's httpx picks up SOCKS-proxy env vars that break HF
streaming. If `huggingface_hub` fails with
`Using SOCKS proxy, but the 'socksio' package is not installed`, wrap the
call with:

```bash
env -u ALL_PROXY -u all_proxy -u GRPC_PROXY -u grpc_proxy \
    -u FTP_PROXY -u ftp_proxy \
    HF_HUB_DISABLE_XET=1 HF_XET_DISABLE=1 \
    HF_HUB_DOWNLOAD_TIMEOUT=600 HF_HUB_ETAG_TIMEOUT=60 \
    .venv/bin/python scripts/fetch_videomme_subset.py ...
```

`HF_HUB_DISABLE_XET=1` matters because HF's xet content-addressed storage
routes to `cas-server.xethub.hf.co`, which is NOT in the Claude Code sandbox
allowlist and fails TLS verification. Forcing the legacy HTTP path keeps
traffic on `huggingface.co`, which is allowlisted.

## Target layout on disk

Matches the existing `data/benchmarks/{tomato,mvbench,videomme}/` pattern:

```
data/benchmarks/videomme/
├── SOURCE.json                    # auto-updated by fetch_videomme_subset.py
├── hf/
│   ├── README.md
│   └── videomme/
│       └── test-00000-of-00001.parquet
├── downloads/
│   └── hf_cache/                  # HF snapshot cache, safe to delete after
└── videos/
    └── <videoID>.mp4              # flat directory of videos keyed by videoID
```

**Critical**: `scripts/run_benchmark_track_a.py::_find_videomme_video`
(line 420) expects a **flat directory of videos** keyed by the videoID.
Do NOT preserve an intermediate `video_id_chunks/` layer — move all files
to the top of `videos/`. The fetcher does this automatically.

Supported suffixes (from `run_benchmark_track_a.py:421`):
`.mp4`, `.mkv`, `.webm`, `.avi`, `.mov`.

## Verification

```bash
cd /Users/jfb/s/codec-through

# File-count vs manifest expectation
ls data/benchmarks/videomme/videos/*.mp4 2>/dev/null | wc -l
# Expect 29 for dev-only; 57 for dev+holdout.

# Per-manifest completeness:
.venv/bin/python - <<'PY'
import tomllib
from pathlib import Path
import pyarrow.parquet as pq

root = Path(".")
rows = pq.read_table(
    root / "data/benchmarks/videomme/hf/videomme/test-00000-of-00001.parquet"
).to_pylist()
by_q = {str(r["question_id"]): str(r["videoID"]) for r in rows}

for manifest in ("videomme_dev_v1.toml", "videomme_holdout_v1.toml"):
    path = root / "research/benchmark_manifests" / manifest
    data = tomllib.loads(path.read_text())
    want = {by_q[item.split(":", 2)[2]] for item in data["item_ids"]}
    have = {
        p.stem for p in (root / "data/benchmarks/videomme/videos").glob("*")
        if p.is_file() and p.suffix.lower() in {".mp4", ".mkv", ".webm", ".avi", ".mov"}
    }
    missing = sorted(want - have)
    print(f"{manifest}: wanted={len(want)}, present={len(want & have)}, missing={len(missing)}")
    if missing:
        print("  sample missing:", missing[:5])
PY
```

If both manifests print `missing=0`, phase 1.41 is unblocked.

## Fallback paths (when the default path does not apply)

### Fallback 1: manual per-video download via the parquet `url` column

The parquet's `url` column has the original YouTube URL each video came
from. If the HF mirror is unavailable or you need an ad-hoc video,
`yt-dlp` against that URL is an option — but the resulting file may
differ in resolution/encoding from the authors' hosted version, which
compromises reproducibility. Use only as a last resort and note the
provenance deviation in `SOURCE.json`.

### Fallback 2: full-corpus acquisition from the official page

https://video-mme.github.io/ still lists the dataset and directs users
to the HF mirror. Use this only if the subset path is inadequate (e.g.,
a reviewer asks for holdout regeneration from scratch). Budget ~101 GB
of bandwidth + ~101 GB of disk for the chunk archives, plus extraction
scratch.

## Phase 1.41 kickoff after videos land

Once the verification step above shows `missing=0` for the dev manifest,
the halo-veto sweep has finished (or paused), and the MLX queue is free:

```bash
.venv/bin/python scripts/run_benchmark_track_a.py run \
    --benchmark videomme \
    --manifest research/benchmark_manifests/videomme_dev_v1.toml \
    --frame-count 8 \
    --statistic max_abs --static-threshold 8.0 --shifted-threshold 32.0 \
    --reuse-classes static,shifted --max-age 4 \
    --output-path research/experiments/2026/artifacts/phase1_41_videomme_qwen_n30_dev/cached.jsonl \
    --summary-path research/experiments/2026/artifacts/phase1_41_videomme_qwen_n30_dev/cached_summary.json
```

Expected runtime: ≈ 2 h GPU wall time for N=30 on M3 Air 16 GB at 8 frames,
560×560, cold cache. See `paper/claim-matrix.md` claim #8.

## Disk budget

- `data/benchmarks/videomme/videos/` after dev-only unpack: ≈ 3–8 GB
  (29 videos × ~200 MB average).
- `data/benchmarks/videomme/videos/` after dev+holdout unpack: ≈ 6–15 GB
  (57 videos, same size distribution).
- `data/benchmarks/videomme/downloads/hf_cache/` peak during fetch:
  one chunk at a time (~5 GB); cleared progressively by the fetcher.
- Full-corpus fallback: ≈ 100 GB.

## Provenance recording

`fetch_videomme_subset.py` updates `data/benchmarks/videomme/SOURCE.json`
with per-video entries pointing at the HF chunk each one came from.
Passing `--record-sha256` computes a SHA-256 of each extracted file for
stronger provenance; this is slow and off by default.

## Why the subset-first path is the science-aware default

- Phase 1.41 needs only the manifest subset — full corpus ≠ needed.
- The holdout manifest is already disjoint from dev by seed, so holdout
  evaluation is re-runnable independently.
- Full-corpus acquisition would move ≈ 85 GB of data we never touch.

## Once this lands

- Unblocks phase 1.41 Qwen + VideoMME N=30 (claim #8).
- Unblocks phase 1.51R Sam novelty-pruning reproduction on
  Gemma + VideoMME (claim #11 — big-numbers headline).
- Unblocks phase 1.52R combined temporal+spatial on Gemma + VideoMME
  (claim #10).

These three phases are **the entire Lane B (Gemma big-numbers) critical
path**. VideoMME videos on disk is the single external-blocker before
Lane B can execute autonomously.
