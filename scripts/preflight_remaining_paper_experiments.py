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
import tomllib
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
DEFAULT_LONG_VIDEO_IDS = (
    "669",
    "711",
    "712",
    "737",
    "756",
    "758",
    "794",
)
VIDEOMME_PARQUET_DIR = Path("data/benchmarks/videomme/hf")
VIDEOMME_VIDEO_DIR = Path("data/benchmarks/videomme/videos")
PHASE130_LONG_COLD_REFERENCE_DIR = Path(
    "research/experiments/2026/artifacts/phase1_30Z_long_q0_kr067_20260424"
)
PHASE130W_REFERENCE_DIR = Path(
    "research/experiments/2026/artifacts/phase1_30W_q0_dense_followup_pruned_full"
)
PHASE165_REQUIRED_SOURCES = (
    Path(
        "research/experiments/2026/artifacts/phase1_55F_q3_post_q2_state/paired_queries_k1_n7.jsonl"
    ),
    Path(
        "research/experiments/2026/artifacts/"
        "phase1_55F_medium_adaptive_replication/paired_queries_k1_n10.jsonl"
    ),
    Path(
        "research/experiments/2026/artifacts/"
        "phase1_55F_long_adaptive_replication/paired_queries_k1_n7.jsonl"
    ),
    Path(
        "research/experiments/2026/artifacts/"
        "phase1_55F_32f_short_adaptive_replication/paired_queries_k1_n7.jsonl"
    ),
    Path(
        "research/experiments/2026/artifacts/"
        "phase1_55E_adaptive_reprefill_q2_k1_q3_k0/paired_queries_k1_n7.jsonl"
    ),
    Path(
        "research/experiments/2026/artifacts/phase1_30AD_instrumented_w_rerun/paired_queries.jsonl"
    ),
    Path(
        "research/experiments/2026/artifacts/phase1_30AC_cache_invalidated_followups/paired_queries.jsonl"
    ),
)


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


def _load_manifest_items(path: Path) -> list[str]:
    payload = tomllib.loads(path.read_text())
    return [str(item_id) for item_id in payload["item_ids"]]


def _video_id_from_item_id(item_id: str) -> str:
    parts = item_id.split(":")
    if len(parts) != 3:
        raise ValueError(f"unexpected VideoMME item_id format: {item_id!r}")
    return parts[2].split("-")[0]


def _unique_session_count_for_manifests(paths: list[Path]) -> int:
    video_ids: set[str] = set()
    for path in paths:
        for item_id in _load_manifest_items(path):
            video_ids.add(_video_id_from_item_id(item_id))
    return len(video_ids)


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
        "--gemma-4bit-model",
        type=Path,
        default=Path.home() / "models" / "gemma-4-e4b-it-4bit",
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
            "gemma_4bit": _status(
                args.gemma_4bit_model.exists(), detail=str(args.gemma_4bit_model)
            ),
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
            "videomme_combined_v1_n60": _status(
                Path("research/benchmark_manifests/videomme_combined_v1_n60.toml").exists(),
                detail="research/benchmark_manifests/videomme_combined_v1_n60.toml",
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
            "phase1_55I_long": {
                video_id: _status(
                    _video_ready(rows, video_id)[0],
                    detail=_video_ready(rows, video_id)[1],
                )
                for video_id in DEFAULT_LONG_VIDEO_IDS
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
    long_ready = all(entry["ready"] for entry in payload["video_sets"]["phase1_55I_long"].values())
    qwen_4bit_ready = payload["models"]["qwen_4bit"]["ready"]
    qwen_bf16_ready = payload["models"]["qwen_bf16"]["ready"]
    gemma_4bit_ready = payload["models"]["gemma_4bit"]["ready"]
    manifests = payload["manifests"]
    long_cold_ready = (
        PHASE130_LONG_COLD_REFERENCE_DIR.joinpath("cold_dense_long.jsonl").exists()
        and PHASE130_LONG_COLD_REFERENCE_DIR.joinpath("cold_dense_long_summary.json").exists()
    )
    full_union_cold_ready = (
        PHASE130W_REFERENCE_DIR.joinpath("cold_dense.jsonl").exists()
        and PHASE130W_REFERENCE_DIR.joinpath("cold_dense_summary.json").exists()
    )
    phase165_sources_ready = all(path.exists() for path in PHASE165_REQUIRED_SOURCES)
    lowfps_union_session_count = _unique_session_count_for_manifests(
        [
            Path("research/benchmark_manifests/videomme_dev_v1.toml"),
            Path("research/benchmark_manifests/videomme_holdout_v1.toml"),
        ]
    )

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
        "1.55I": _status(
            qwen_4bit_ready and long_ready,
            detail="K=1 long-bucket replication",
        ),
        "1.55F-medium": _status(
            qwen_4bit_ready and medium_ready,
            detail="adaptive post-Q2-state medium-bucket replication",
        ),
        "1.55F-long": _status(
            qwen_4bit_ready and long_ready,
            detail="adaptive post-Q2-state long-bucket replication",
        ),
        "1.55F-32f": _status(
            qwen_4bit_ready and short_ready,
            detail="adaptive post-Q2-state 32f short-bucket replication",
        ),
        "1.55J": _status(
            qwen_4bit_ready and short_ready,
            detail="K=1 short-bucket sampler-variation scout",
        ),
        "1.55F-16f": _status(
            qwen_4bit_ready and short_ready,
            detail="adaptive post-Q2-state 16f short-bucket interpolation",
        ),
        "1.57G": _status(
            gemma_4bit_ready and manifests["videomme_dev_v1"]["ready"],
            detail="Gemma short/medium/long feature-drift grid at 8/16/32f",
        ),
        "1.30AB": _status(
            qwen_4bit_ready
            and manifests["videomme_long_dev_holdout_v1"]["ready"]
            and long_cold_ready,
            detail={
                "phase": "long-bucket Q0 keep-rate boundary sweep",
                "reference_cold_dir": PHASE130_LONG_COLD_REFERENCE_DIR.as_posix(),
                "reference_cold_ready": long_cold_ready,
            },
        ),
        "1.30AE": _status(
            qwen_4bit_ready
            and manifests["videomme_dev_v1"]["ready"]
            and manifests["videomme_holdout_v1"]["ready"],
            detail="duration-conditioned full-union rerun with sweep-selected long keep-rate",
        ),
        "1.30AC": _status(
            qwen_4bit_ready
            and manifests["videomme_dev_v1"]["ready"]
            and manifests["videomme_holdout_v1"]["ready"]
            and full_union_cold_ready,
            detail={
                "phase": "cache-invalidated follow-up pruning",
                "reference_cold_dir": PHASE130W_REFERENCE_DIR.as_posix(),
                "reference_cold_ready": full_union_cold_ready,
            },
        ),
        "1.30AD": _status(
            qwen_4bit_ready
            and manifests["videomme_dev_v1"]["ready"]
            and manifests["videomme_holdout_v1"]["ready"]
            and full_union_cold_ready,
            detail={
                "phase": "instrumented 1.30W rerun",
                "reference_cold_dir": PHASE130W_REFERENCE_DIR.as_posix(),
                "reference_cold_ready": full_union_cold_ready,
            },
        ),
        "1.62D": _status(
            qwen_4bit_ready
            and manifests["videomme_dev_v1"]["ready"]
            and manifests["videomme_holdout_v1"]["ready"]
            and full_union_cold_ready
            and lowfps_union_session_count == 57,
            detail={
                "phase": "low-FPS dense VideoMME session baseline",
                "reference_cold_dir": PHASE130W_REFERENCE_DIR.as_posix(),
                "reference_cold_ready": full_union_cold_ready,
                "unique_manifest_sessions": lowfps_union_session_count,
                "expected_unique_manifest_sessions": 57,
            },
        ),
        "1.63": _status(
            qwen_4bit_ready and manifests["videomme_combined_v1_n60"]["ready"],
            detail="Track B compact Qwen ViT execution, dense vs L2 kr0.50 sparse",
        ),
        "1.63E": _status(
            qwen_4bit_ready and manifests["videomme_combined_v1_n60"]["ready"],
            detail="Track B compact Qwen ViT execution across 16f/20f/32f frame budgets",
        ),
        "1.63G": _status(
            gemma_4bit_ready and manifests["videomme_combined_v1_n60"]["ready"],
            detail="Track B compact Gemma ViT execution at 8f on VideoMME n=60",
        ),
        "1.65": _status(
            qwen_4bit_ready and phase165_sources_ready,
            detail={
                "phase": "dense logit-margin failure-predictor scout",
                "required_sources_ready": phase165_sources_ready,
                "required_sources": [path.as_posix() for path in PHASE165_REQUIRED_SOURCES],
            },
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
