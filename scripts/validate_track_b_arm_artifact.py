#!/usr/bin/env python3
"""Validate a Track B arm artifact before skip-if-exists reuse."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from codec_through.codec.score_sidecar import (  # noqa: E402
    SCORE_SIDECAR_PROJECTION_VERSION,
    score_config_id,
)


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


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    with path.open() as handle:
        for line in handle:
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"results row is not an object: {path}")
            row = cast(dict[str, Any], payload)
            item_id = str(row["item_id"])
            if item_id in seen:
                raise ValueError(f"duplicate item_id in results: {item_id}")
            seen.add(item_id)
            rows.append(row)
    return rows


def _norm_path(value: str | None) -> str | None:
    if value is None:
        return None
    return str(Path(value).expanduser().resolve(strict=False))


def _assert_equal(actual: object, expected: object, field: str) -> None:
    if actual != expected:
        raise ValueError(f"{field} mismatch: actual={actual!r} expected={expected!r}")


def _current_git_commit() -> str | None:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def _manifest_item_ids(path: str, *, n_items: int | None) -> list[str]:
    payload = tomllib.loads(Path(path).read_text())
    item_ids = [str(item_id) for item_id in payload["item_ids"]]
    if n_items is not None and n_items > 0:
        item_ids = item_ids[:n_items]
    return item_ids


def validate(args: Any) -> None:
    summary = _load_json(args.arm_dir / "summary.json")
    rows = _load_rows(args.arm_dir / "results.jsonl")
    current_commit = _current_git_commit()
    n_results = len(rows)
    _assert_equal(n_results, int(summary["n_items"]), "results row count")
    if _line_count(args.arm_dir / "results.jsonl") != n_results:
        raise AssertionError("line count and loaded row count diverged")
    parse_failures = sum(1 for row in rows if bool(row.get("parse_failure", False)))
    if not args.allow_parse_failures:
        if parse_failures:
            raise ValueError(f"parse failures present in reused artifact: {parse_failures}")
    elif parse_failures > args.max_parse_failures:
        raise ValueError(
            f"parse failures exceed explicit bound: {parse_failures} > {args.max_parse_failures}"
        )

    if args.n_items is not None and args.n_items > 0:
        _assert_equal(int(summary["n_items"]), args.n_items, "n_items")
    _assert_equal(_norm_path(str(summary["manifest"])), _norm_path(args.manifest), "manifest")
    expected_item_ids = _manifest_item_ids(args.manifest, n_items=args.n_items)
    _assert_equal([str(row["item_id"]) for row in rows], expected_item_ids, "results item_ids")
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
        expected_sidecar = (
            _norm_path(args.codec_score_sidecar_dir)
            if getattr(args, "codec_score_sidecar_dir", None) is not None
            else None
        )
        actual_sidecar = _norm_path(summary.get("codec_score_sidecar_dir"))
        _assert_equal(actual_sidecar, expected_sidecar, "codec_score_sidecar_dir")
        if args.score_mode == "codec_grid":
            expected_runtime_source = "sidecar" if expected_sidecar is not None else "live_pyav"
            _assert_equal(
                summary.get("codec_score_runtime_source"),
                expected_runtime_source,
                "codec_score_runtime_source",
            )
            if expected_sidecar is not None:
                expected_geometry = args.codec_score_sidecar_geometry
                _assert_equal(
                    summary.get("codec_score_sidecar_geometry"),
                    expected_geometry,
                    "codec_score_sidecar_geometry",
                )
                expected_config_id = score_config_id(
                    source=str(args.codec_score_source),
                    frame_count=args.frame_count,
                    projection_version=SCORE_SIDECAR_PROJECTION_VERSION,
                    fusion_mode=str(args.fusion_mode),
                    motion_weight=float(args.motion_weight),
                    residual_weight=float(args.residual_weight),
                    normalize_fusion_inputs=not bool(args.no_normalize_fusion_inputs),
                )
                _assert_equal(
                    summary.get("codec_score_sidecar_config_id"),
                    expected_config_id,
                    "codec_score_sidecar_config_id",
                )
                _assert_equal(
                    summary.get("codec_score_projection_version"),
                    SCORE_SIDECAR_PROJECTION_VERSION,
                    "codec_score_projection_version",
                )
                sidecar_items = summary.get("codec_sidecar_items")
                if not isinstance(sidecar_items, list):
                    raise ValueError("codec_sidecar_items must be a list for sidecar artifacts")
                _assert_equal(len(sidecar_items), int(summary["n_items"]), "codec_sidecar_items")
                for item in sidecar_items:
                    if not isinstance(item, dict):
                        raise ValueError(f"codec_sidecar_items row is not an object: {item!r}")
                    if bool(item.get("sidecar_git_dirty", False)) and not args.allow_dirty_artifact:
                        raise ValueError(f"dirty sidecar used for item {item.get('item_id')!r}")
                    if current_commit is not None and not args.allow_dirty_artifact:
                        _assert_equal(
                            item.get("sidecar_git_commit"),
                            current_commit,
                            f"{item.get('item_id')!r} sidecar_git_commit",
                        )
                    if item.get("sidecar_score_projection_version") != (
                        SCORE_SIDECAR_PROJECTION_VERSION
                    ):
                        raise ValueError(
                            "sidecar projection-version mismatch for item "
                            f"{item.get('item_id')!r}: "
                            f"{item.get('sidecar_score_projection_version')!r}"
                        )
                    if item.get("sidecar_score_config_id") != expected_config_id:
                        raise ValueError(
                            f"sidecar config mismatch for item {item.get('item_id')!r}: "
                            f"{item.get('sidecar_score_config_id')!r} != {expected_config_id!r}"
                        )
                    digest = item.get("sidecar_score_grid_sha256")
                    if not isinstance(digest, str) or len(digest) != 64:
                        raise ValueError(f"missing sidecar hash for item {item.get('item_id')!r}")
                    extract_s = item.get("sidecar_codec_extract_s")
                    if not isinstance(extract_s, int | float) or not math.isfinite(extract_s):
                        raise ValueError(
                            "missing finite sidecar extract timing for item "
                            f"{item.get('item_id')!r}"
                        )
                load_mean = summary.get("codec_sidecar_load_mean_s_per_item")
                if not isinstance(load_mean, int | float) or not math.isfinite(load_mean):
                    raise ValueError("missing finite codec_sidecar_load_mean_s_per_item")
            else:
                extract_mean = summary.get("codec_extract_mean_s_per_item")
                if not isinstance(extract_mean, int | float) or not math.isfinite(extract_mean):
                    raise ValueError("missing finite codec_extract_mean_s_per_item")
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
    if bool(summary.get("git_dirty", False)) and not args.allow_dirty_artifact:
        raise ValueError("artifact was generated from a dirty git tree")
    if current_commit is not None and not args.allow_dirty_artifact:
        _assert_equal(summary.get("git_commit"), current_commit, "git_commit")


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
    parser.add_argument("--codec-score-sidecar-dir", default=None)
    parser.add_argument("--codec-score-sidecar-geometry", default=None)
    parser.add_argument("--fusion-mode", default="weighted")
    parser.add_argument("--motion-weight", type=float, default=1.0)
    parser.add_argument("--residual-weight", type=float, default=1.0)
    parser.add_argument("--no-normalize-fusion-inputs", action="store_true")
    parser.add_argument("--allow-dirty-artifact", action="store_true")
    parser.add_argument("--allow-parse-failures", action="store_true")
    parser.add_argument("--max-parse-failures", type=int, default=0)
    args, _unknown = parser.parse_known_args()
    validate(args)


if __name__ == "__main__":
    main()
