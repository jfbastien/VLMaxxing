#!/usr/bin/env python3
"""Preflight the remaining paper-closeout experiment queue.

This is intentionally read-only and CPU-only. It verifies the local pieces that
should exist before we spend MLX wall-clock on the remaining experiment slate.
It avoids importing the MLX runners directly so it can run on CI and on hosts
without Metal access.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

DEFAULT_SHORT_VIDEO_IDS = ("037", "100", "116", "120", "158", "160", "210")
DEFAULT_MEDIUM_VIDEO_IDS = (
    "320",
    "354",
    "364",
    "380",
    "407",
    "408",
    "426",
    "484",
    "486",
    "531",
)
VIDEOMME_PARQUET_DIR = Path("data/benchmarks/videomme/hf")
VIDEOMME_VIDEO_DIR = Path("data/benchmarks/videomme/videos")


def _videomme_parquet_path() -> Path:
    candidates = sorted(VIDEOMME_PARQUET_DIR.rglob("*.parquet"))
    if not candidates:
        raise FileNotFoundError(f"no VideoMME parquet found under {VIDEOMME_PARQUET_DIR}")
    return candidates[0]


def _load_videomme_rows() -> list[dict[str, Any]]:
    return list(pq.read_table(_videomme_parquet_path()).to_pylist())


def _find_videomme_video(video_id: str) -> Path:
    extensions = (".mp4", ".mkv", ".webm", ".avi", ".mov")
    for extension in extensions:
        candidate = VIDEOMME_VIDEO_DIR / f"{video_id}{extension}"
        if candidate.exists():
            return candidate
    matches: list[Path] = []
    if VIDEOMME_VIDEO_DIR.exists():
        for extension in extensions:
            matches.extend(VIDEOMME_VIDEO_DIR.rglob(f"{video_id}{extension}"))
    unique_matches = sorted({match.resolve() for match in matches})
    if len(unique_matches) == 1:
        return unique_matches[0]
    if len(unique_matches) > 1:
        raise RuntimeError(f"ambiguous VideoMME video lookup for {video_id!r}: {unique_matches}")
    raise FileNotFoundError(
        f"could not locate VideoMME video {video_id!r} under {VIDEOMME_VIDEO_DIR}"
    )


def _video_ready(rows: list[dict[str, Any]], video_id: str) -> tuple[bool, str]:
    matching = [
        row
        for row in rows
        if str(row.get("video_id")) == video_id or str(row.get("videoID")) == video_id
    ]
    if len(matching) < 3:
        return False, f"expected >=3 questions for video_id {video_id}, found {len(matching)}"
    try:
        video_path = _find_videomme_video(str(matching[0]["videoID"]))
    except Exception as exc:  # pragma: no cover - diagnostic path
        return False, f"video lookup failed for {video_id}: {type(exc).__name__}: {exc}"
    return True, video_path.as_posix()


def _status(ok: bool, *, detail: Any) -> dict[str, Any]:
    return {"ready": ok, "detail": detail}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--qwen-4bit-model",
        type=Path,
        default=Path.home() / "models" / "Qwen2.5-VL-7B-Instruct-4bit",
    )
    parser.add_argument(
        "--qwen-bf16-model",
        type=Path,
        default=Path.home() / "models" / "Qwen2.5-VL-7B-Instruct",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/experiments/2026/artifacts/paper_closeout_preflight.json"),
    )
    parser.add_argument(
        "--max-safe-rss-gb",
        type=float,
        default=10.0,
        help="Operator memory ceiling for autonomous runs on the 16 GB laptop.",
    )
    args = parser.parse_args()

    rows = _load_videomme_rows()
    payload: dict[str, Any] = {
        "machine_policy": {
            "max_safe_rss_gb": args.max_safe_rss_gb,
            "note": (
                "The closeout queue is planned for a 16 GB unified-memory laptop. "
                "Treat experiments expected to exceed the operator ceiling as blocked "
                "even if weights exist locally."
            ),
        },
        "models": {
            "qwen_4bit": _status(args.qwen_4bit_model.exists(), detail=str(args.qwen_4bit_model)),
            "qwen_bf16": _status(args.qwen_bf16_model.exists(), detail=str(args.qwen_bf16_model)),
        },
        "manifests": {
            "videomme_dev_v1": _status(
                Path("research/benchmark_manifests/videomme_dev_v1.toml").exists(),
                detail="research/benchmark_manifests/videomme_dev_v1.toml",
            ),
            "videomme_holdout_v1": _status(
                Path("research/benchmark_manifests/videomme_holdout_v1.toml").exists(),
                detail="research/benchmark_manifests/videomme_holdout_v1.toml",
            ),
            "videomme_long_dev_holdout_v1": _status(
                Path("research/benchmark_manifests/videomme_long_dev_holdout_v1.toml").exists(),
                detail="research/benchmark_manifests/videomme_long_dev_holdout_v1.toml",
            ),
        },
        "video_sets": {
            "phase1_55F_short": {
                video_id: _status(
                    _video_ready(rows, video_id)[0],
                    detail=_video_ready(rows, video_id)[1],
                )
                for video_id in DEFAULT_SHORT_VIDEO_IDS
            },
            "phase1_55G_medium": {
                video_id: _status(
                    _video_ready(rows, video_id)[0],
                    detail=_video_ready(rows, video_id)[1],
                )
                for video_id in DEFAULT_MEDIUM_VIDEO_IDS
            },
        },
        "experiments": {},
    }

    short_ready = all(
        entry["ready"] for entry in payload["video_sets"]["phase1_55F_short"].values()
    )
    medium_ready = all(
        entry["ready"] for entry in payload["video_sets"]["phase1_55G_medium"].values()
    )
    qwen_4bit_ready = payload["models"]["qwen_4bit"]["ready"]
    qwen_bf16_ready = payload["models"]["qwen_bf16"]["ready"]
    manifests = payload["manifests"]

    payload["experiments"] = {
        "1.30Z": _status(
            qwen_4bit_ready and manifests["videomme_long_dev_holdout_v1"]["ready"],
            detail="long-bucket kr_Q0=0.67 continuation",
        ),
        "1.30AA": _status(
            qwen_4bit_ready
            and manifests["videomme_dev_v1"]["ready"]
            and manifests["videomme_holdout_v1"]["ready"],
            detail="duration-conditioned full-union rerun",
        ),
        "1.55F": _status(
            qwen_4bit_ready and short_ready,
            detail="Q3 from repaired post-Q2 state",
        ),
        "1.55G": _status(
            qwen_4bit_ready and medium_ready,
            detail="K=1 medium-bucket replication",
        ),
        "1.55H": _status(
            qwen_4bit_ready and short_ready,
            detail="K=1 short-bucket 32f boundary probe",
        ),
        "1.58": _status(
            qwen_4bit_ready and qwen_bf16_ready and args.max_safe_rss_gb >= 14.0,
            detail={
                "phase": "bf16 quantization control",
                "bf16_checkpoint_present": qwen_bf16_ready,
                "required_safe_rss_gb": 14.0,
                "configured_safe_rss_gb": args.max_safe_rss_gb,
                "blocked_reason": (
                    None
                    if qwen_bf16_ready and args.max_safe_rss_gb >= 14.0
                    else (
                        "bf16 path exceeds the current local memory policy "
                        "and/or weights are absent"
                    )
                ),
            },
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
