#!/usr/bin/env python3
"""Validate a Track B arm artifact before skip-if-exists reuse."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return cast(dict[str, Any], payload)


def _line_count(path: Path) -> int:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open() as handle:
        return sum(1 for _ in handle)


def _norm_path(value: str | None) -> str | None:
    if value is None:
        return None
    return str(Path(value).expanduser().resolve(strict=False))


def _assert_equal(actual: object, expected: object, field: str) -> None:
    if actual != expected:
        raise ValueError(f"{field} mismatch: actual={actual!r} expected={expected!r}")


def validate(args: Any) -> None:
    summary = _load_json(args.arm_dir / "summary.json")
    n_results = _line_count(args.arm_dir / "results.jsonl")
    _assert_equal(n_results, int(summary["n_items"]), "results row count")

    if args.n_items is not None and args.n_items > 0:
        _assert_equal(int(summary["n_items"]), args.n_items, "n_items")
    _assert_equal(_norm_path(str(summary["manifest"])), _norm_path(args.manifest), "manifest")
    _assert_equal(_norm_path(str(summary["model_path"])), _norm_path(args.model_path), "model_path")
    _assert_equal(int(summary["frame_count"]), args.frame_count, "frame_count")
    _assert_equal(int(summary["max_tokens"]), args.max_tokens, "max_tokens")

    patched = args.vision_tower_keep_rate < 1.0
    _assert_equal(bool(summary["vision_tower_patched"]), patched, "vision_tower_patched")
    if patched:
        _assert_equal(
            int(summary["vision_tower_layer"]),
            args.vision_tower_layer,
            "vision_tower_layer",
        )
        if abs(float(summary["vision_tower_keep_rate"]) - args.vision_tower_keep_rate) > 1e-9:
            raise ValueError(
                "vision_tower_keep_rate mismatch: "
                f"actual={summary['vision_tower_keep_rate']!r} "
                f"expected={args.vision_tower_keep_rate!r}"
            )
        _assert_equal(summary["score_mode"], args.score_mode, "score_mode")
        expected_seed = args.score_seed if args.score_mode == "uniform_random" else None
        _assert_equal(summary["score_seed"], expected_seed, "score_seed")
        _assert_equal(summary["codec_score_source"], args.codec_score_source, "codec_score_source")
    else:
        _assert_equal(summary["vision_tower_layer"], None, "vision_tower_layer")
        _assert_equal(summary["vision_tower_keep_rate"], None, "vision_tower_keep_rate")
        _assert_equal(summary["score_mode"], None, "score_mode")
        _assert_equal(summary["codec_score_source"], None, "codec_score_source")

    missing_provenance = [
        field
        for field in ("generated_at", "git_commit", "git_dirty", "git_dirty_scope")
        if field not in summary
    ]
    if missing_provenance:
        raise ValueError(f"missing provenance fields: {missing_provenance}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm-dir", type=Path, required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--frame-count", type=int, required=True)
    parser.add_argument("--max-tokens", type=int, required=True)
    parser.add_argument("--n-items", type=int, default=None)
    parser.add_argument("--vision-tower-layer", type=int, default=2)
    parser.add_argument("--vision-tower-keep-rate", type=float, default=1.0)
    parser.add_argument(
        "--score-mode",
        choices=("magnitude_norm", "uniform_random", "codec_grid"),
        default="magnitude_norm",
    )
    parser.add_argument("--score-seed", type=int, default=42)
    parser.add_argument("--codec-score-source", default=None)
    args, _unknown = parser.parse_known_args()
    validate(args)


if __name__ == "__main__":
    main()
