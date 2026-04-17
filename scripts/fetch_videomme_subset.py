#!/usr/bin/env python3
"""Fetch the manifest-subset of Video-MME videos from Hugging Face.

Video-MME's official HF mirror (lmms-lab/Video-MME) ships videos as 20 chunked
zips totaling ~101 GB. The checked-in dev+holdout protocol only needs 57
unique videoIDs, so downloading the full corpus wastes ~95% of the transfer.

This script walks the chunks one at a time, extracts only the wanted
videoIDs, deletes each chunk after (unless --keep-chunks), and stops early
once every wanted videoID has been extracted. Peak disk ~= one chunk (~5 GB)
plus the subset (~3-15 GB depending on video length).

Scope: fetches only what checked-in manifests point at. If you change the
manifests you have to re-run this.

Typical usage:
    # dev-first unblock (29 videos)
    uv run python scripts/fetch_videomme_subset.py \\
        --manifest research/benchmark_manifests/videomme_dev_v1.toml

    # full paper subset (57 videos; dev+holdout)
    uv run python scripts/fetch_videomme_subset.py \\
        --manifest research/benchmark_manifests/videomme_dev_v1.toml \\
        --manifest research/benchmark_manifests/videomme_holdout_v1.toml

The script is idempotent: already-present videoIDs are skipped, and already-
satisfied subsets short-circuit the chunk walk.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
import zipfile
from pathlib import Path
from typing import Any, cast

VIDEOMME_DATASET_ID = "lmms-lab/Video-MME"
VIDEOMME_ROOT = Path("data/benchmarks/videomme")
VIDEOS_DIR = VIDEOMME_ROOT / "videos"
PARQUET_GLOB = VIDEOMME_ROOT / "hf" / "videomme"
SUPPORTED_VIDEO_SUFFIXES = (".mp4", ".mkv", ".webm", ".avi", ".mov")

CHUNK_NAMES = [f"videos_chunked_{i:02d}.zip" for i in range(1, 21)]


def _load_parquet_rows(parquet_path: Path) -> list[dict[str, Any]]:
    import pyarrow.parquet as pq

    table = pq.read_table(parquet_path)
    return cast(list[dict[str, Any]], table.to_pylist())


def _resolve_parquet() -> Path:
    candidates = sorted(PARQUET_GLOB.rglob("*.parquet"))
    if not candidates:
        raise FileNotFoundError(
            f"no VideoMME parquet found under {PARQUET_GLOB}; "
            f"run scripts/fetch_benchmarks.py --dataset videomme --mode metadata first"
        )
    return candidates[0]


def _wanted_video_ids(manifest_paths: list[Path], parquet_path: Path) -> dict[str, str]:
    rows = _load_parquet_rows(parquet_path)
    by_qid = {str(row["question_id"]): row for row in rows}
    wanted: dict[str, str] = {}
    for manifest_path in manifest_paths:
        data = tomllib.loads(manifest_path.read_text())
        for item_id in data["item_ids"]:
            prefix, _duration, qid = item_id.split(":", maxsplit=2)
            if prefix != "videomme":
                raise ValueError(f"non-VideoMME item in manifest {manifest_path}: {item_id!r}")
            if qid not in by_qid:
                raise KeyError(f"question_id {qid!r} from {manifest_path} not found in parquet")
            row = by_qid[qid]
            wanted[str(row["videoID"])] = str(row.get("url", ""))
    return wanted


def _existing_video_ids(videos_dir: Path) -> set[str]:
    present: set[str] = set()
    if videos_dir.exists():
        for child in videos_dir.iterdir():
            if child.is_file() and child.suffix.lower() in SUPPORTED_VIDEO_SUFFIXES:
                present.add(child.stem)
    return present


def _member_video_id(member_name: str) -> tuple[str, str] | None:
    """Return (videoID, suffix) if member_name looks like a videoID file, else None."""
    path = Path(member_name)
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_VIDEO_SUFFIXES:
        return None
    stem = path.stem
    if not stem:
        return None
    return stem, path.suffix  # preserve original case on suffix


def _extract_matching_members(
    chunk_path: Path,
    wanted_remaining: set[str],
    videos_dir: Path,
) -> set[str]:
    extracted: set[str] = set()
    with zipfile.ZipFile(chunk_path) as zf:
        for member in zf.infolist():
            if member.is_dir():
                continue
            parsed = _member_video_id(member.filename)
            if parsed is None:
                continue
            video_id, suffix = parsed
            if video_id not in wanted_remaining:
                continue
            target_path = videos_dir / f"{video_id}{suffix}"
            tmp_path = videos_dir / f"{video_id}{suffix}.part"
            with zf.open(member) as src, tmp_path.open("wb") as dst:
                while True:
                    block = src.read(1024 * 1024)
                    if not block:
                        break
                    dst.write(block)
            tmp_path.rename(target_path)
            extracted.add(video_id)
    return extracted


def _download_chunk(chunk_name: str, cache_dir: Path) -> Path:
    from huggingface_hub import hf_hub_download

    local_path = hf_hub_download(
        repo_id=VIDEOMME_DATASET_ID,
        repo_type="dataset",
        filename=chunk_name,
        cache_dir=str(cache_dir),
    )
    return Path(local_path)


def _update_source_record(record_path: Path, extracted: dict[str, dict[str, Any]]) -> None:
    existing: dict[str, Any] = {}
    if record_path.exists():
        try:
            existing = json.loads(record_path.read_text())
        except json.JSONDecodeError:
            existing = {}
    existing["dataset"] = "videomme"
    existing["metadata_source"] = f"hf://datasets/{VIDEOMME_DATASET_ID}"
    existing["video_source"] = (
        f"subset extracted from hf://datasets/{VIDEOMME_DATASET_ID} "
        f"videos_chunked_*.zip; see scripts/fetch_videomme_subset.py"
    )
    existing.setdefault("subset", {})
    existing["subset"].update(extracted)
    record_path.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n")


def _sha256_hex(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            block = fh.read(1024 * 1024)
            if not block:
                break
            hasher.update(block)
    return hasher.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        action="append",
        type=Path,
        required=True,
        help="benchmark manifest TOML (repeatable)",
    )
    parser.add_argument(
        "--videos-dir",
        type=Path,
        default=VIDEOS_DIR,
        help="flat directory where <videoID>.<ext> files will be written",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=VIDEOMME_ROOT / "downloads" / "hf_cache",
        help="staging cache for HF chunk downloads (deleted after extraction unless --keep-chunks)",
    )
    parser.add_argument(
        "--keep-chunks",
        action="store_true",
        help="do not delete each chunk zip after extracting the wanted videos",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list wanted/missing videoIDs, do not download",
    )
    parser.add_argument(
        "--record-sha256",
        action="store_true",
        help="compute SHA-256 of each extracted file (slow, optional, for provenance)",
    )
    args = parser.parse_args()

    videos_dir: Path = args.videos_dir
    videos_dir.mkdir(parents=True, exist_ok=True)
    cache_dir: Path = args.cache_dir
    cache_dir.mkdir(parents=True, exist_ok=True)

    parquet_path = _resolve_parquet()
    wanted = _wanted_video_ids(args.manifest, parquet_path)
    present = _existing_video_ids(videos_dir)
    remaining = {vid for vid in wanted if vid not in present}

    print(f"wanted (manifest union): {len(wanted)} videos")
    print(f"already on disk         : {len(wanted) - len(remaining)}")
    print(f"remaining to fetch      : {len(remaining)}")
    if not remaining:
        print("nothing to do")
        return 0
    if args.dry_run:
        for vid in sorted(remaining):
            print(f"MISS\t{vid}\t{wanted.get(vid, '')}")
        return 0

    record: dict[str, dict[str, Any]] = {}
    total = len(remaining)
    for chunk_index, chunk_name in enumerate(CHUNK_NAMES, start=1):
        if not remaining:
            print(f"all wanted videos extracted after {chunk_index - 1} chunk(s); stopping")
            break
        print(
            f"[{chunk_index:02d}/{len(CHUNK_NAMES):02d}] downloading {chunk_name} "
            f"({len(remaining)}/{total} remaining)"
        )
        try:
            chunk_path = _download_chunk(chunk_name, cache_dir)
        except Exception as exc:  # noqa: BLE001 — propagate after logging
            print(f"  chunk download failed: {exc!r}")
            raise
        try:
            extracted = _extract_matching_members(chunk_path, remaining, videos_dir)
        finally:
            if not args.keep_chunks:
                chunk_path.unlink(missing_ok=True)
        if not extracted:
            print("  (no wanted videoIDs in this chunk)")
        else:
            print(f"  extracted {len(extracted)}: {sorted(extracted)}")
            remaining -= extracted
            for vid in extracted:
                target = next(
                    (
                        videos_dir / f"{vid}{s}"
                        for s in SUPPORTED_VIDEO_SUFFIXES
                        if (videos_dir / f"{vid}{s}").exists()
                    ),
                    None,
                )
                if target is None:
                    continue
                entry: dict[str, Any] = {
                    "path": str(target.relative_to(VIDEOMME_ROOT)),
                    "source": (f"hf://datasets/{VIDEOMME_DATASET_ID}/{chunk_name}!{vid}"),
                    "size_bytes": target.stat().st_size,
                }
                if args.record_sha256:
                    entry["sha256"] = _sha256_hex(target)
                record[vid] = entry

    if record:
        _update_source_record(VIDEOMME_ROOT / "SOURCE.json", record)

    if remaining:
        print(
            f"WARNING: {len(remaining)} wanted videoIDs still missing after all chunks: "
            f"{sorted(remaining)}"
        )
        return 1
    print(f"done: {len(wanted)} wanted videoIDs now present in {videos_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
