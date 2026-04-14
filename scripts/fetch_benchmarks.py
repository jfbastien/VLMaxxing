#!/usr/bin/env python3
"""Fetch benchmark-native assets for TOMATO and MVBench."""

from __future__ import annotations

import argparse
import importlib
import json
import shutil
import subprocess
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

TOMATO_DATASET_ID = "yale-nlp/TOMATO"
TOMATO_DRIVE_FILE_ID = "1-dNt9bZcp6C3RXuGoAO3EBgWkAHg8NWR"
TOMATO_FALLBACK_DATASET_ID = "ellisbrown/TOMATO"
MVBENCH_DATASET_ID = "OpenGVLab/MVBench"

TOMATO_ROOT = Path("data/benchmarks/tomato")
MVBENCH_ROOT = Path("data/benchmarks/mvbench")

MVBENCH_HOSTED_ZIPS = [
    "FunQA_test.zip",
    "Moments_in_Time_Raw.zip",
    "clevrer.zip",
    "data0613.zip",
    "perception.zip",
    "scene_qa.zip",
    "ssv2_video.zip",
    "sta.zip",
    "star.zip",
    "tvqa.zip",
    "vlnqa.zip",
]

MVBENCH_PREDECESSOR18_ZIPS = [
    "FunQA_test.zip",
    "Moments_in_Time_Raw.zip",
    "clevrer.zip",
    "data0613.zip",
    "perception.zip",
    "scene_qa.zip",
    "ssv2_video.zip",
    "sta.zip",
    "star.zip",
    "vlnqa.zip",
]

TOMATO_FALLBACK_SHARDS = [f"video_shard_{index:03d}.tar.zst" for index in range(6)]


@dataclass(frozen=True, slots=True)
class BenchmarkPaths:
    root: Path
    downloads_dir: Path
    hf_dir: Path
    asset_dir: Path
    source_record_path: Path


def _load_hf() -> tuple[Any, Any]:
    from huggingface_hub import hf_hub_download, snapshot_download

    return hf_hub_download, snapshot_download


def _load_gdown() -> Any:
    return importlib.import_module("gdown")


def _ensure_dirs(paths: BenchmarkPaths) -> None:
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.downloads_dir.mkdir(parents=True, exist_ok=True)
    paths.hf_dir.mkdir(parents=True, exist_ok=True)
    paths.asset_dir.mkdir(parents=True, exist_ok=True)


def _write_source_record(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _merge_source_record(path: Path, payload: dict[str, Any]) -> None:
    existing: dict[str, Any] = {}
    if path.exists():
        existing = cast(dict[str, Any], json.loads(path.read_text()))
    existing.update(payload)
    _write_source_record(path, existing)


def _extract_zip(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(destination)


def _zip_is_valid(archive_path: Path) -> bool:
    try:
        with zipfile.ZipFile(archive_path) as archive:
            return archive.testzip() is None
    except zipfile.BadZipFile:
        return False


def _quarantine_corrupt_archive(archive_path: Path) -> Path:
    candidate = archive_path.with_suffix(archive_path.suffix + ".corrupt")
    counter = 1
    while candidate.exists():
        candidate = archive_path.with_suffix(f"{archive_path.suffix}.corrupt.{counter}")
        counter += 1
    shutil.move(str(archive_path), str(candidate))
    return candidate


def _quarantine_path(path: Path, *, suffix: str) -> Path:
    candidate = path.with_name(path.name + suffix)
    counter = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.name}{suffix}.{counter}")
        counter += 1
    shutil.move(str(path), str(candidate))
    return candidate


def _quarantine_matching_parts(archive_path: Path) -> list[Path]:
    quarantined: list[Path] = []
    for part_path in sorted(archive_path.parent.glob(f"{archive_path.name}*.part")):
        quarantined.append(_quarantine_path(part_path, suffix=".corrupt"))
    return quarantined


def _download_tomato_archive(archive_path: Path, *, gdown: Any, attempts: int = 5) -> None:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            downloaded = gdown.download(
                id=TOMATO_DRIVE_FILE_ID,
                output=str(archive_path),
                quiet=False,
                resume=True,
            )
            if downloaded is None and not archive_path.exists():
                raise RuntimeError("gdown did not materialize the TOMATO archive")
        except FileNotFoundError as exc:
            if archive_path.exists():
                return
            last_error = exc
        except Exception as exc:
            last_error = exc
        else:
            if archive_path.exists():
                return

        if attempt == attempts:
            break
        time.sleep(2)

    raise RuntimeError(
        f"failed to download TOMATO archive after {attempts} attempts"
    ) from last_error


def _extract_tomato_mirror_shards(paths: BenchmarkPaths, *, dry_run: bool) -> None:
    if dry_run:
        for shard_name in TOMATO_FALLBACK_SHARDS:
            print(
                "[dry-run] hf_hub_download "
                f"{TOMATO_FALLBACK_DATASET_ID} {shard_name} -> {paths.downloads_dir}"
            )
        print(f"[dry-run] tar -xf each TOMATO mirror shard into {paths.asset_dir}")
        return
    hf_hub_download, _ = _load_hf()
    for shard_name in TOMATO_FALLBACK_SHARDS:
        shard_path = Path(
            hf_hub_download(
                TOMATO_FALLBACK_DATASET_ID,
                filename=shard_name,
                repo_type="dataset",
                local_dir=str(paths.downloads_dir),
            )
        )
        subprocess.run(
            ["tar", "-xf", str(shard_path), "-C", str(paths.asset_dir)],
            check=True,
            capture_output=True,
            text=True,
        )


def _normalize_tomato_layout(asset_dir: Path) -> None:
    if (asset_dir / "videos" / "human").exists():
        return
    candidates = [
        path
        for path in asset_dir.rglob("videos")
        if path.is_dir() and (path / "human").exists() and (path / "object").exists()
    ]
    if len(candidates) != 1:
        raise RuntimeError(
            "expected exactly one TOMATO videos/ directory after extraction, "
            f"found {len(candidates)}"
        )
    candidate = candidates[0]
    destination = asset_dir / "videos"
    if candidate == destination:
        return
    if destination.exists():
        raise RuntimeError(f"refusing to overwrite existing TOMATO videos dir: {destination}")
    shutil.move(str(candidate), str(destination))


def _validate_tomato(paths: BenchmarkPaths, *, metadata: bool, assets: bool) -> None:
    if metadata:
        parquet_files = sorted((paths.hf_dir / "data").glob("*.parquet"))
        if len(parquet_files) != 6:
            raise RuntimeError(
                "expected 6 TOMATO parquet splits under "
                f"{paths.hf_dir / 'data'}, found {len(parquet_files)}"
            )
    if assets:
        videos_root = paths.asset_dir / "videos"
        required = ["human", "object", "simulated"]
        missing = [name for name in required if not (videos_root / name).exists()]
        if missing:
            raise RuntimeError(f"TOMATO videos layout missing: {missing}")


def _validate_mvbench(paths: BenchmarkPaths, *, metadata: bool, assets: bool) -> None:
    if metadata:
        json_files = sorted((paths.hf_dir / "json").glob("*.json"))
        if len(json_files) != 20:
            raise RuntimeError(
                "expected 20 MVBench task JSON files under "
                f"{paths.hf_dir / 'json'}, found {len(json_files)}"
            )
        ntu_list = paths.hf_dir / "video" / "MVBench_videos_ntu.txt"
        if not ntu_list.exists():
            raise RuntimeError(f"missing MVBench NTU reference list: {ntu_list}")
    if assets:
        hosted_marker_paths = [
            paths.asset_dir / "clevrer",
            paths.asset_dir / "star",
            paths.asset_dir / "ssv2_video",
        ]
        if not any(path.exists() for path in hosted_marker_paths):
            raise RuntimeError(
                "MVBench asset extraction did not create expected hosted bundle directories"
            )


def _fetch_tomato_metadata(paths: BenchmarkPaths, *, dry_run: bool) -> None:
    allow_patterns = ["README.md", "data/*.parquet"]
    if dry_run:
        print(f"[dry-run] snapshot {TOMATO_DATASET_ID} -> {paths.hf_dir} {allow_patterns}")
        return
    _, snapshot_download = _load_hf()
    snapshot_download(
        TOMATO_DATASET_ID,
        repo_type="dataset",
        local_dir=str(paths.hf_dir),
        allow_patterns=allow_patterns,
    )
    _merge_source_record(
        paths.source_record_path,
        {
            "dataset": "tomato",
            "metadata_source": f"hf://datasets/{TOMATO_DATASET_ID}",
            "video_source_primary": f"gdrive://{TOMATO_DRIVE_FILE_ID}",
            "video_source_fallback": (
                f"hf://datasets/{TOMATO_FALLBACK_DATASET_ID} {','.join(TOMATO_FALLBACK_SHARDS)}"
            ),
        },
    )
    _validate_tomato(paths, metadata=True, assets=False)


def _fetch_tomato_assets(
    paths: BenchmarkPaths,
    *,
    dry_run: bool,
    video_source: Literal["auto", "official", "mirror"],
) -> None:
    archive_path = paths.downloads_dir / "tomato_videos.zip"
    videos_root = paths.asset_dir / "videos"
    if dry_run:
        if video_source in {"auto", "official"}:
            print(f"[dry-run] gdown {TOMATO_DRIVE_FILE_ID} -> {archive_path}")
            print(f"[dry-run] extract {archive_path} -> {paths.asset_dir}")
        if video_source in {"auto", "mirror"}:
            _extract_tomato_mirror_shards(paths, dry_run=True)
        return
    if videos_root.exists():
        try:
            _validate_tomato(paths, metadata=False, assets=True)
            return
        except RuntimeError:
            _quarantine_path(videos_root, suffix=".partial")
    if video_source in {"auto", "official"}:
        gdown = _load_gdown()
        if archive_path.exists() and not _zip_is_valid(archive_path):
            _quarantine_corrupt_archive(archive_path)
            _quarantine_matching_parts(archive_path)
        if not archive_path.exists():
            try:
                _download_tomato_archive(archive_path, gdown=gdown)
            except RuntimeError:
                if video_source == "official":
                    raise
                _quarantine_matching_parts(archive_path)
                _extract_tomato_mirror_shards(paths, dry_run=dry_run)
                _validate_tomato(paths, metadata=False, assets=True)
                _merge_source_record(
                    paths.source_record_path,
                    {
                        "video_source_selected": (
                            f"hf://datasets/{TOMATO_FALLBACK_DATASET_ID} "
                            f"{','.join(TOMATO_FALLBACK_SHARDS)}"
                        )
                    },
                )
                return
        if _zip_is_valid(archive_path):
            _extract_zip(archive_path, paths.asset_dir)
            _normalize_tomato_layout(paths.asset_dir)
            _validate_tomato(paths, metadata=False, assets=True)
            _merge_source_record(
                paths.source_record_path,
                {"video_source_selected": f"gdrive://{TOMATO_DRIVE_FILE_ID}"},
            )
            return
        if video_source == "official":
            quarantined = _quarantine_corrupt_archive(archive_path)
            quarantined_parts = _quarantine_matching_parts(archive_path)
            raise RuntimeError(
                "downloaded TOMATO archive failed zip validation and was quarantined: "
                f"{quarantined}; parts="
                f"{','.join(str(path) for path in quarantined_parts) or 'none'}"
            )
        quarantined = _quarantine_corrupt_archive(archive_path)
        quarantined_parts = _quarantine_matching_parts(archive_path)
        _extract_tomato_mirror_shards(paths, dry_run=dry_run)
        _validate_tomato(paths, metadata=False, assets=True)
        _merge_source_record(
            paths.source_record_path,
            {
                "video_source_selected": (
                    f"hf://datasets/{TOMATO_FALLBACK_DATASET_ID} {','.join(TOMATO_FALLBACK_SHARDS)}"
                ),
                "quarantined_primary_archive": str(quarantined),
                "quarantined_primary_parts": [str(path) for path in quarantined_parts],
            },
        )
        return

    _extract_tomato_mirror_shards(paths, dry_run=dry_run)
    _validate_tomato(paths, metadata=False, assets=True)
    _merge_source_record(
        paths.source_record_path,
        {
            "video_source_selected": (
                f"hf://datasets/{TOMATO_FALLBACK_DATASET_ID} {','.join(TOMATO_FALLBACK_SHARDS)}"
            )
        },
    )


def _fetch_mvbench_metadata(paths: BenchmarkPaths, *, dry_run: bool) -> None:
    allow_patterns = ["README.md", "json/*.json", "video/MVBench_videos_ntu.txt"]
    if dry_run:
        print(f"[dry-run] snapshot {MVBENCH_DATASET_ID} -> {paths.hf_dir} {allow_patterns}")
        return
    _, snapshot_download = _load_hf()
    snapshot_download(
        MVBENCH_DATASET_ID,
        repo_type="dataset",
        local_dir=str(paths.hf_dir),
        allow_patterns=allow_patterns,
    )
    _write_source_record(
        paths.source_record_path,
        {
            "dataset": "mvbench",
            "metadata_source": f"hf://datasets/{MVBENCH_DATASET_ID}",
            "hosted_video_archives": MVBENCH_HOSTED_ZIPS,
            "default_hosted_profile": "predecessor18",
            "manual_component": "NTU RGB+D videos listed in video/MVBench_videos_ntu.txt",
        },
    )
    _validate_mvbench(paths, metadata=True, assets=False)


def _fetch_mvbench_assets(
    paths: BenchmarkPaths,
    *,
    dry_run: bool,
    archive_names: list[str],
) -> None:
    if dry_run:
        for archive_name in archive_names:
            print(
                "[dry-run] hf_hub_download "
                f"{MVBENCH_DATASET_ID} video/{archive_name} -> {paths.downloads_dir}"
            )
        print(f"[dry-run] extract all hosted MVBench archives -> {paths.asset_dir}")
        return
    hf_hub_download, _ = _load_hf()
    downloaded_archives: list[Path] = []
    for archive_name in archive_names:
        local_path = Path(
            hf_hub_download(
                MVBENCH_DATASET_ID,
                filename=f"video/{archive_name}",
                repo_type="dataset",
                local_dir=str(paths.downloads_dir),
            )
        )
        downloaded_archives.append(local_path)
    for archive_path in downloaded_archives:
        _extract_zip(archive_path, paths.asset_dir)
    _validate_mvbench(paths, metadata=False, assets=True)


def _paths_for(dataset: Literal["tomato", "mvbench"]) -> BenchmarkPaths:
    if dataset == "tomato":
        root = TOMATO_ROOT
        return BenchmarkPaths(
            root=root,
            downloads_dir=root / "downloads",
            hf_dir=root / "hf",
            asset_dir=root,
            source_record_path=root / "SOURCE.json",
        )
    root = MVBENCH_ROOT
    return BenchmarkPaths(
        root=root,
        downloads_dir=root / "downloads",
        hf_dir=root / "hf",
        asset_dir=root / "video",
        source_record_path=root / "SOURCE.json",
    )


def _fetch_dataset(
    dataset: Literal["tomato", "mvbench"],
    *,
    mode: Literal["metadata", "assets", "all"],
    dry_run: bool,
    mvbench_profile: Literal["predecessor18", "all"],
    tomato_video_source: Literal["auto", "official", "mirror"],
) -> None:
    paths = _paths_for(dataset)
    _ensure_dirs(paths)
    if dataset == "tomato":
        if mode in {"metadata", "all"}:
            _fetch_tomato_metadata(paths, dry_run=dry_run)
        if mode in {"assets", "all"}:
            _fetch_tomato_assets(
                paths,
                dry_run=dry_run,
                video_source=tomato_video_source,
            )
        return
    if mode in {"metadata", "all"}:
        _fetch_mvbench_metadata(paths, dry_run=dry_run)
    if mode in {"assets", "all"}:
        archive_names = (
            MVBENCH_PREDECESSOR18_ZIPS
            if mvbench_profile == "predecessor18"
            else MVBENCH_HOSTED_ZIPS
        )
        _fetch_mvbench_assets(paths, dry_run=dry_run, archive_names=archive_names)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        choices=["tomato", "mvbench", "both"],
        required=True,
        help="Benchmark stack to fetch.",
    )
    parser.add_argument(
        "--mode",
        choices=["metadata", "assets", "all"],
        default="all",
        help="Which portion of each benchmark stack to fetch.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the fetch plan without downloading anything.",
    )
    parser.add_argument(
        "--mvbench-profile",
        choices=["predecessor18", "all"],
        default="predecessor18",
        help=(
            "Which hosted MVBench archive profile to fetch. "
            "`predecessor18` matches the predecessor-style 18-task slice; "
            "`all` fetches every hosted archive except the manual NTU component."
        ),
    )
    parser.add_argument(
        "--tomato-video-source",
        choices=["auto", "official", "mirror"],
        default="auto",
        help=(
            "Where TOMATO videos should come from. "
            "`auto` tries the official Drive bundle then falls back to the "
            "public ellisbrown/TOMATO Hugging Face mirror; "
            "`mirror` skips Drive entirely."
        ),
    )
    args = parser.parse_args()

    selected_datasets = ["tomato", "mvbench"] if args.dataset == "both" else [args.dataset]
    for dataset in selected_datasets:
        _fetch_dataset(
            cast(Literal["tomato", "mvbench"], dataset),
            mode=args.mode,
            dry_run=args.dry_run,
            mvbench_profile=cast(Literal["predecessor18", "all"], args.mvbench_profile),
            tomato_video_source=cast(
                Literal["auto", "official", "mirror"],
                args.tomato_video_source,
            ),
        )


if __name__ == "__main__":
    main()
