# VideoMME Subset Acquisition

This repo's VideoMME protocol uses checked-in manifest subsets, not the full
VideoMME corpus. The acquisition path below is for reviewers or maintainers who
need to recreate the local video assets used by the benchmark runners.

## Required Subset

The Track A VideoMME protocol uses these manifests:

- `research/benchmark_manifests/videomme_dev_v1.toml`
- `research/benchmark_manifests/videomme_holdout_v1.toml`

Together they reference 57 unique `videoID` values. The loader keys on the
parquet `videoID` column, not the row-index-like `video_id` column. The target
layout is a flat directory:

```text
data/benchmarks/videomme/
├── SOURCE.json
├── hf/
│   ├── README.md
│   └── videomme/
│       └── test-00000-of-00001.parquet
├── downloads/
│   └── hf_cache/
└── videos/
    └── <videoID>.mp4
```

Supported video suffixes are `.mp4`, `.mkv`, `.webm`, `.avi`, and `.mov`.

## Inspect The Required IDs

Run from the repository root:

```bash
.venv/bin/python scripts/fetch_videomme_subset.py \
    --manifest research/benchmark_manifests/videomme_dev_v1.toml \
    --manifest research/benchmark_manifests/videomme_holdout_v1.toml \
    --dry-run
```

## Fetch From The Hugging Face Mirror

The official VideoMME mirror `lmms-lab/Video-MME` stores videos as chunked zip
archives. `scripts/fetch_videomme_subset.py` walks those archives one at a time,
extracts only requested `videoID` files, and removes each chunk after use.

Dev split only:

```bash
.venv/bin/python scripts/fetch_videomme_subset.py \
    --manifest research/benchmark_manifests/videomme_dev_v1.toml \
    --cache-dir data/benchmarks/videomme/downloads/hf_cache
```

Dev plus holdout:

```bash
.venv/bin/python scripts/fetch_videomme_subset.py \
    --manifest research/benchmark_manifests/videomme_dev_v1.toml \
    --manifest research/benchmark_manifests/videomme_holdout_v1.toml \
    --cache-dir data/benchmarks/videomme/downloads/hf_cache
```

The full corpus is roughly 101 GB, but the checked-in protocol should need only
the manifest subset on disk after extraction. Peak staging space is roughly one
archive chunk plus the extracted subset.

If a local proxy or Hugging Face Xet configuration interferes with downloads,
clear proxy variables and force the legacy HTTP download path for this command:

```bash
env -u ALL_PROXY -u all_proxy -u GRPC_PROXY -u grpc_proxy \
    -u FTP_PROXY -u ftp_proxy \
    HF_HUB_DISABLE_XET=1 HF_XET_DISABLE=1 \
    HF_HUB_DOWNLOAD_TIMEOUT=600 HF_HUB_ETAG_TIMEOUT=60 \
    .venv/bin/python scripts/fetch_videomme_subset.py ...
```

## Verify Completeness

Run from the repository root after extraction:

```bash
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
        p.stem
        for p in (root / "data/benchmarks/videomme/videos").glob("*")
        if p.is_file()
        and p.suffix.lower() in {".mp4", ".mkv", ".webm", ".avi", ".mov"}
    }
    missing = sorted(want - have)
    print(
        f"{manifest}: wanted={len(want)}, "
        f"present={len(want & have)}, missing={len(missing)}"
    )
    if missing:
        print("  sample missing:", missing[:5])
PY
```

Both manifests should report `missing=0` before running VideoMME benchmark
reproduction.

## Provenance

`scripts/fetch_videomme_subset.py` writes `data/benchmarks/videomme/SOURCE.json`
with per-video source entries. Use `--record-sha256` when a release artifact or
reviewer request requires file-level hashes; it is slower and off by default.

Manual `yt-dlp` acquisition from the parquet `url` column is a last-resort
fallback because it may produce different resolution or encoding than the hosted
VideoMME files. Record that deviation in `SOURCE.json` if used.
