#!/usr/bin/env python3
"""Fetch benchmark-native assets for TOMATO and MVBench."""

from __future__ import annotations

import argparse
import importlib
import json
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

TOMATO_DATASET_ID = "yale-nlp/TOMATO"
TOMATO_DRIVE_FILE_ID = "1-dNt9bZcp6C3RXuGoAO3EBgWkAHg8NWR"
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


def _extract_zip(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(destination)


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
    _write_source_record(
        paths.source_record_path,
        {
            "dataset": "tomato",
            "metadata_source": f"hf://datasets/{TOMATO_DATASET_ID}",
            "video_source": f"gdrive://{TOMATO_DRIVE_FILE_ID}",
        },
    )
    _validate_tomato(paths, metadata=True, assets=False)


def _fetch_tomato_assets(paths: BenchmarkPaths, *, dry_run: bool) -> None:
    archive_path = paths.downloads_dir / "tomato_videos.zip"
    if dry_run:
        print(f"[dry-run] gdown {TOMATO_DRIVE_FILE_ID} -> {archive_path}")
        print(f"[dry-run] extract {archive_path} -> {paths.asset_dir}")
        return
    gdown = _load_gdown()
    if not archive_path.exists():
        downloaded = gdown.download(
            id=TOMATO_DRIVE_FILE_ID,
            output=str(archive_path),
            quiet=False,
            fuzzy=False,
        )
        if downloaded is None:
            raise RuntimeError("gdown did not return a downloaded TOMATO archive path")
    _extract_zip(archive_path, paths.asset_dir)
    _normalize_tomato_layout(paths.asset_dir)
    _validate_tomato(paths, metadata=False, assets=True)


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
            "manual_component": "NTU RGB+D videos listed in video/MVBench_videos_ntu.txt",
        },
    )
    _validate_mvbench(paths, metadata=True, assets=False)


def _fetch_mvbench_assets(paths: BenchmarkPaths, *, dry_run: bool) -> None:
    if dry_run:
        for archive_name in MVBENCH_HOSTED_ZIPS:
            print(
                "[dry-run] hf_hub_download "
                f"{MVBENCH_DATASET_ID} video/{archive_name} -> {paths.downloads_dir}"
            )
        print(f"[dry-run] extract all hosted MVBench archives -> {paths.asset_dir}")
        return
    hf_hub_download, _ = _load_hf()
    downloaded_archives: list[Path] = []
    for archive_name in MVBENCH_HOSTED_ZIPS:
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
) -> None:
    paths = _paths_for(dataset)
    _ensure_dirs(paths)
    if dataset == "tomato":
        if mode in {"metadata", "all"}:
            _fetch_tomato_metadata(paths, dry_run=dry_run)
        if mode in {"assets", "all"}:
            _fetch_tomato_assets(paths, dry_run=dry_run)
        return
    if mode in {"metadata", "all"}:
        _fetch_mvbench_metadata(paths, dry_run=dry_run)
    if mode in {"assets", "all"}:
        _fetch_mvbench_assets(paths, dry_run=dry_run)


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
    args = parser.parse_args()

    selected_datasets = (
        ["tomato", "mvbench"] if args.dataset == "both" else [args.dataset]
    )
    for dataset in selected_datasets:
        _fetch_dataset(
            cast(Literal["tomato", "mvbench"], dataset),
            mode=args.mode,
            dry_run=args.dry_run,
        )


if __name__ == "__main__":
    main()
