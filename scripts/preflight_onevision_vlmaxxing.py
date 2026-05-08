#!/usr/bin/env python3
"""Preflight checks for OneVision + VLMaxxing experiments.

This script is intentionally CPU-only. It does not download assets, import
model runtimes, decode videos, or run VLM inference. It fails loudly when a
required real benchmark asset is missing; generated overlays and synthetic
figures are never accepted as substitutes for source media.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSON = (
    REPO_ROOT
    / "research"
    / "experiments"
    / "2026"
    / "artifacts"
    / "onevision_vlmaxxing_plan"
    / "preflight_status.json"
)
SUPPORTED_VIDEO_SUFFIXES = (".mp4", ".mkv", ".webm", ".avi", ".mov")
LOCAL_RESTORE_ROOTS = (REPO_ROOT.parent / "codec-through",)


@dataclass(frozen=True, slots=True)
class RequiredClip:
    key: str
    benchmark: str
    item_id: str
    role: str
    path: Path
    fetch_hint: str


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    status: Literal["ok", "missing", "warning"]
    detail: str
    used_for: str
    remedy: str | None = None


Scope = Literal["all", "ov1", "ov3"]


REQUIRED_CLIPS = (
    RequiredClip(
        key="tomato_0298_00",
        benchmark="TOMATO",
        item_id="tomato:rotation:0298-00",
        role="existing paper visualization: high-reuse routing example",
        path=Path("data/benchmarks/tomato/videos/object/0298-00.mp4"),
        fetch_hint=(
            "uv run python scripts/fetch_benchmarks.py --dataset tomato --mode all "
            "--tomato-video-source auto"
        ),
    ),
    RequiredClip(
        key="videomme_380",
        benchmark="VideoMME",
        item_id="videomme:medium:380-3",
        role="existing paper visualization: VideoMME visual anchor",
        path=Path("data/benchmarks/videomme/videos/2Bns2m5Bg4M.mp4"),
        fetch_hint=(
            "uv run python scripts/fetch_videomme_subset.py "
            "--manifest research/benchmark_manifests/videomme_dev_v1.toml "
            "--cache-dir data/benchmarks/videomme/downloads/hf_cache"
        ),
    ),
    RequiredClip(
        key="videomme_267",
        benchmark="VideoMME",
        item_id="videomme:short:267-2",
        role="existing paper visualization: lower-reuse boundary",
        path=Path("data/benchmarks/videomme/videos/Atf_Af1q_5w.mp4"),
        fetch_hint=(
            "uv run python scripts/fetch_videomme_subset.py "
            "--manifest research/benchmark_manifests/videomme_dev_v1.toml "
            "--manifest research/benchmark_manifests/videomme_holdout_v1.toml "
            "--cache-dir data/benchmarks/videomme/downloads/hf_cache"
        ),
    ),
)

REQUIRED_MANIFESTS = (
    Path("research/benchmark_manifests/videomme_dev_v1_short_only.toml"),
    Path("research/benchmark_manifests/videomme_dev_v1.toml"),
    Path("research/benchmark_manifests/videomme_holdout_v1.toml"),
    Path("research/benchmark_manifests/tomato_motion_holdout_v2.toml"),
)

SYNTHETIC_ARTIFACTS = (
    Path(
        "research/experiments/2026/artifacts/onevision_vlmaxxing_visuals/"
        "onevision_vlmaxxing_synthetic_explainer.png"
    ),
    Path(
        "research/experiments/2026/artifacts/onevision_vlmaxxing_visuals/"
        "onevision_vlmaxxing_synthetic_explainer.json"
    ),
)


def _check_path(
    *,
    name: str,
    path: Path,
    used_for: str,
    remedy: str | None,
) -> Check:
    full_path = REPO_ROOT / path
    if full_path.exists():
        return Check(name=name, status="ok", detail=str(path), used_for=used_for)
    local_restore = _local_restore_remedy(path)
    combined_remedy = remedy
    if local_restore is not None:
        combined_remedy = f"{local_restore}; or {remedy}" if remedy else local_restore
    return Check(
        name=name,
        status="missing",
        detail=str(path),
        used_for=used_for,
        remedy=combined_remedy,
    )


def _local_restore_remedy(relative_path: Path) -> str | None:
    if relative_path.is_absolute():
        return None
    for root in LOCAL_RESTORE_ROOTS:
        candidate = root / relative_path
        if candidate.exists():
            destination = REPO_ROOT / relative_path
            return (
                f"local copy available: mkdir -p {destination.parent} && "
                f"cp {candidate} {destination}"
            )
    return None


def _find_videomme_parquet() -> Path | None:
    root = REPO_ROOT / "data" / "benchmarks" / "videomme" / "hf"
    candidates = sorted(root.rglob("*.parquet")) if root.exists() else []
    return candidates[0] if candidates else None


def _find_tomato_parquets() -> list[Path]:
    root = REPO_ROOT / "data" / "benchmarks" / "tomato" / "hf"
    return sorted(root.rglob("*.parquet")) if root.exists() else []


def _find_local_restore_parquets(relative_root: Path) -> list[Path]:
    found: list[Path] = []
    for root in LOCAL_RESTORE_ROOTS:
        candidate_root = root / relative_root
        if candidate_root.exists():
            found.extend(sorted(candidate_root.rglob("*.parquet")))
    return found


def _existing_video_ids(videos_dir: Path) -> set[str]:
    if not videos_dir.exists():
        return set()
    return {
        path.stem
        for path in videos_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_VIDEO_SUFFIXES
    }


def _local_restore_video_ids(relative_videos_dir: Path) -> set[str]:
    ids: set[str] = set()
    for root in LOCAL_RESTORE_ROOTS:
        ids.update(_existing_video_ids(root / relative_videos_dir))
    return ids


def _videomme_manifest_video_ids(
    manifest: Path,
    *,
    parquet_path: Path,
) -> set[str]:
    import pyarrow.parquet as pq

    rows = pq.read_table(parquet_path).to_pylist()
    by_qid = {str(row["question_id"]): str(row["videoID"]) for row in rows}
    data = tomllib.loads((REPO_ROOT / manifest).read_text())
    video_ids: set[str] = set()
    for item_id in data["item_ids"]:
        prefix, _duration, qid = str(item_id).split(":", maxsplit=2)
        if prefix != "videomme":
            continue
        if qid not in by_qid:
            raise KeyError(f"question_id {qid!r} from {manifest} not found in VideoMME parquet")
        video_ids.add(by_qid[qid])
    return video_ids


def _check_videomme_manifest_assets(
    manifest: Path,
    *,
    parquet_path: Path | None,
) -> Check:
    if parquet_path is None:
        return Check(
            name=f"videomme manifest assets: {manifest.name}",
            status="missing",
            detail="VideoMME parquet metadata unavailable; cannot resolve videoID values",
            used_for="OV-3/OV-5 manifest video availability",
            remedy="uv run python scripts/fetch_benchmarks.py --dataset videomme --mode metadata",
        )
    if importlib.util.find_spec("pyarrow") is None:
        return Check(
            name=f"videomme manifest assets: {manifest.name}",
            status="missing",
            detail="pyarrow is unavailable; cannot inspect VideoMME parquet",
            used_for="OV-3/OV-5 manifest video availability",
            remedy="uv sync --group benchmark",
        )
    wanted = _videomme_manifest_video_ids(manifest, parquet_path=parquet_path)
    present = _existing_video_ids(REPO_ROOT / "data" / "benchmarks" / "videomme" / "videos")
    missing = sorted(wanted - present)
    if not missing:
        return Check(
            name=f"videomme manifest assets: {manifest.name}",
            status="ok",
            detail=f"{len(wanted)} videos present",
            used_for="OV-3/OV-5 manifest video availability",
        )
    restorable = sorted(
        set(missing) & _local_restore_video_ids(Path("data/benchmarks/videomme/videos"))
    )
    restore_note = (
        f"local restore has {len(restorable)}/{len(missing)} missing videoIDs under "
        f"{LOCAL_RESTORE_ROOTS[0] / 'data/benchmarks/videomme/videos'}; or "
        if restorable
        else ""
    )
    return Check(
        name=f"videomme manifest assets: {manifest.name}",
        status="missing",
        detail=f"missing {len(missing)}/{len(wanted)} videoIDs: {', '.join(missing)}",
        used_for="OV-3/OV-5 manifest video availability",
        remedy=(
            f"{restore_note}uv run python scripts/fetch_videomme_subset.py "
            f"--manifest {manifest} --cache-dir data/benchmarks/videomme/downloads/hf_cache"
        ),
    )


def _build_checks(*, scope: Scope) -> list[Check]:
    checks: list[Check] = []
    checks.append(
        Check(
            name="no synthetic visual fallback",
            status="ok",
            detail=(
                "render_onevision_vlmaxxing_visual.py defaults to real-video rendering and "
                "fails on missing clips"
            ),
            used_for="OV-1 scientific visualization gate",
        )
    )
    for artifact in SYNTHETIC_ARTIFACTS:
        if (REPO_ROOT / artifact).exists():
            checks.append(
                Check(
                    name=f"synthetic artifact absent: {artifact.name}",
                    status="warning",
                    detail=str(artifact),
                    used_for="prevent synthetic figures from being mistaken for evidence",
                    remedy="remove generated synthetic artifacts before paper-facing review",
                )
            )
    checks.append(
        Check(
            name="preflight scope",
            status="ok",
            detail=scope,
            used_for="scope-specific readiness gate",
        )
    )
    if scope in {"all", "ov3"}:
        checks.append(
            _check_path(
                name="Qwen default model path",
                path=Path.home() / "models" / "Qwen2.5-VL-7B-Instruct-4bit",
                used_for="OV-3 local Qwen model-bearing run",
                remedy="restore ~/models/Qwen2.5-VL-7B-Instruct-4bit before model runs",
            )
        )
        checks.append(
            _check_path(
                name="Phase 1.57 reference summary",
                path=Path("research/experiments/2026/artifacts/phase1_57/qwen_8f_dev30.json"),
                used_for="OV-2/OV-3 --calibration-source=artifact option",
                remedy="run live-pixel calibration or restore the Phase 1.57 artifact",
            )
        )
        for manifest in REQUIRED_MANIFESTS:
            checks.append(
                _check_path(
                    name=f"manifest: {manifest.name}",
                    path=manifest,
                    used_for="experiment item selection",
                    remedy=None,
                )
            )
    if scope in {"all", "ov3"}:
        tomato_parquets = _find_tomato_parquets()
        tomato_restore_parquets = _find_local_restore_parquets(Path("data/benchmarks/tomato/hf"))
        checks.append(
            Check(
                name="TOMATO metadata parquet",
                status="ok" if tomato_parquets else "missing",
                detail=f"{len(tomato_parquets)} parquet files"
                if tomato_parquets
                else "no TOMATO parquet files under data/benchmarks/tomato/hf",
                used_for="TOMATO manifest loading and clip provenance",
                remedy=None
                if tomato_parquets
                else (
                    f"local restore has {len(tomato_restore_parquets)} parquets under "
                    f"{LOCAL_RESTORE_ROOTS[0] / 'data/benchmarks/tomato/hf'}; or "
                    "uv run python scripts/fetch_benchmarks.py --dataset tomato --mode metadata"
                ),
            )
        )
        videomme_parquet = _find_videomme_parquet()
        videomme_restore_parquets = _find_local_restore_parquets(
            Path("data/benchmarks/videomme/hf")
        )
        checks.append(
            Check(
                name="VideoMME metadata parquet",
                status="ok" if videomme_parquet is not None else "missing",
                detail=str(videomme_parquet.relative_to(REPO_ROOT))
                if videomme_parquet is not None
                else "no VideoMME parquet under data/benchmarks/videomme/hf",
                used_for="VideoMME item_id to videoID resolution",
                remedy=None
                if videomme_parquet is not None
                else (
                    f"local restore has {len(videomme_restore_parquets)} parquets under "
                    f"{LOCAL_RESTORE_ROOTS[0] / 'data/benchmarks/videomme/hf'}; or "
                    "uv run python scripts/fetch_benchmarks.py --dataset videomme --mode metadata"
                ),
            )
        )
        for manifest in (
            Path("research/benchmark_manifests/videomme_dev_v1_short_only.toml"),
            Path("research/benchmark_manifests/videomme_dev_v1.toml"),
            Path("research/benchmark_manifests/videomme_holdout_v1.toml"),
        ):
            checks.append(_check_videomme_manifest_assets(manifest, parquet_path=videomme_parquet))
    if scope in {"all", "ov1"}:
        for clip in REQUIRED_CLIPS:
            checks.append(
                _check_path(
                    name=f"visualization clip: {clip.key}",
                    path=clip.path,
                    used_for=f"{clip.role}; item_id={clip.item_id}",
                    remedy=clip.fetch_hint,
                )
            )
    required_modules = [("av", "uv sync --group research")]
    if scope in {"all", "ov3"}:
        required_modules.append(("pyarrow", "uv sync --group benchmark"))
    for module_name, remedy in required_modules:
        present = importlib.util.find_spec(module_name) is not None
        checks.append(
            Check(
                name=f"python module: {module_name}",
                status="ok" if present else "missing",
                detail=module_name,
                used_for="codec metadata / benchmark manifest inspection",
                remedy=None if present else remedy,
            )
        )
    overlay_dir = (
        REPO_ROOT / "research/experiments/2026/artifacts/codec_through_video_overlays_exploratory"
    )
    if overlay_dir.exists() and any(check.status == "missing" for check in checks):
        checks.append(
            Check(
                name="generated overlay artifacts are not source media",
                status="warning",
                detail=str(overlay_dir.relative_to(REPO_ROOT)),
                used_for="scientific provenance",
                remedy="restore benchmark source videos; do not use generated overlays as inputs",
            )
        )
    return checks


def _summary(checks: list[Check]) -> dict[str, Any]:
    counts = {
        "ok": sum(check.status == "ok" for check in checks),
        "missing": sum(check.status == "missing" for check in checks),
        "warning": sum(check.status == "warning" for check in checks),
    }
    return {
        "schema": "onevision_vlmaxxing_preflight_v1",
        "repo_root": str(REPO_ROOT),
        "ready": counts["missing"] == 0,
        "counts": counts,
        "checks": [asdict(check) for check in checks],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scope",
        choices=("all", "ov1", "ov3"),
        default="all",
        help="Readiness scope: ov1 checks visualization inputs; ov3 checks model-run assets.",
    )
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--no-write-json", action="store_true")
    args = parser.parse_args()

    checks = _build_checks(scope=args.scope)
    payload = _summary(checks)
    if not args.no_write_json:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    for check in checks:
        prefix = {"ok": "OK", "missing": "MISSING", "warning": "WARN"}[check.status]
        print(f"{prefix}\t{check.name}\t{check.detail}")
        if check.remedy:
            print(f"  remedy: {check.remedy}")
    return 0 if payload["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
