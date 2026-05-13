#!/usr/bin/env python3
"""Validate an OV-3 pooled-calibration arm before skip-if-exists reuse."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, cast


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return cast(dict[str, Any], payload)


def _line_count(path: Path) -> int:
    with path.open() as handle:
        return sum(1 for _ in handle)


def _git_head(repo_root: Path) -> str | None:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def validate(args: Any) -> None:
    summary_path = args.arm_dir / "summary.json"
    results_path = args.arm_dir / "results.jsonl"
    cache_path = args.arm_dir / "precompute_cache.json"
    for path in (summary_path, results_path, cache_path):
        if not path.exists():
            raise FileNotFoundError(path)

    summary = _load_json(summary_path)
    n_results = _line_count(results_path)
    if n_results != int(summary["n_items"]):
        raise ValueError(
            f"results row count mismatch: actual={n_results} expected={summary['n_items']}"
        )
    if summary["codec_score_source"] != args.codec_score_source:
        raise ValueError(
            "codec_score_source mismatch: "
            f"actual={summary['codec_score_source']!r} expected={args.codec_score_source!r}"
        )
    if int(summary["frame_count"]) != args.frame_count:
        raise ValueError(
            f"frame_count mismatch: actual={summary['frame_count']!r} expected={args.frame_count!r}"
        )
    if summary["calibration_mode"] != args.calibration_mode:
        raise ValueError(
            "calibration_mode mismatch: "
            f"actual={summary['calibration_mode']!r} expected={args.calibration_mode!r}"
        )
    if summary["calibration_source"] != args.calibration_source:
        raise ValueError(
            "calibration_source mismatch: "
            f"actual={summary['calibration_source']!r} expected={args.calibration_source!r}"
        )

    environment = summary.get("environment")
    if not isinstance(environment, dict):
        raise ValueError("summary missing environment object")
    git_sha = environment.get("git_sha")
    if not isinstance(git_sha, str) or not git_sha:
        raise ValueError("summary missing environment.git_sha")
    current = _git_head(Path(__file__).resolve().parents[1])
    if current is not None and git_sha != current:
        raise ValueError(f"git_sha mismatch: actual={git_sha!r} current={current!r}")
    if environment.get("git_dirty") is not False:
        raise ValueError(f"artifact was produced from dirty tree: {environment.get('git_dirty')!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm-dir", type=Path, required=True)
    parser.add_argument("--codec-score-source", required=True)
    parser.add_argument("--frame-count", type=int, required=True)
    parser.add_argument("--calibration-mode", required=True)
    parser.add_argument("--calibration-source", required=True)
    args = parser.parse_args()
    validate(args)


if __name__ == "__main__":
    main()
