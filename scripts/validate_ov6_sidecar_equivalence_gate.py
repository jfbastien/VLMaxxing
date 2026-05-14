#!/usr/bin/env python3
"""Validate that an M3 sidecar-equivalence gate passed before M5 reuse."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_ov6_codec_score_sidecars import validate as validate_sidecars  # noqa: E402


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"missing required sidecar-equivalence artifact: {path}")
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return cast(dict[str, Any], payload)


def _assert_equal(actual: object, expected: object, field: str) -> None:
    if actual != expected:
        raise ValueError(f"{field} mismatch: actual={actual!r} expected={expected!r}")


def validate(args: argparse.Namespace) -> None:
    root = args.root
    equivalence = _load_json(root / "sidecar_equivalence.json")
    sidecar_manifest = _load_json(root / "sidecar_manifest.json")
    sources = [str(source) for source in (args.sources or sidecar_manifest.get("sources", []))]
    if not sources:
        raise ValueError("no sources requested for sidecar-equivalence validation")

    _assert_equal(equivalence.get("schema"), "ov6_sidecar_equivalence_v1", "schema")
    if equivalence.get("gate_pass") is not True:
        raise ValueError(f"M3 sidecar-equivalence gate did not pass: {root}")
    pairs = equivalence.get("pairs")
    if not isinstance(pairs, dict):
        raise ValueError("sidecar_equivalence pairs must be an object")

    for source in sources:
        pair = pairs.get(source)
        if not isinstance(pair, dict):
            raise ValueError(f"missing sidecar-equivalence pair for source {source!r}")
        _assert_equal(pair.get("choice_drift"), 0, f"{source} choice_drift")
        _assert_equal(pair.get("correctness_drift"), 0, f"{source} correctness_drift")
        _assert_equal(pair.get("kept_count_drift"), 0, f"{source} kept_count_drift")
        _assert_equal(
            pair.get("kept_groups_per_frame_drift"),
            0,
            f"{source} kept_groups_per_frame_drift",
        )
        _assert_equal(pair.get("live_runtime_source"), "live_pyav", f"{source} live source")
        _assert_equal(pair.get("sidecar_runtime_source"), "sidecar", f"{source} sidecar source")
        if pair.get("sidecar_load_under_1s") is not True:
            raise ValueError(f"{source} sidecar load was not below 1s/item")
        if pair.get("sidecar_faster_than_live_extract") is not True:
            raise ValueError(f"{source} sidecar load was not faster than live extraction")

    validate_sidecars(
        argparse.Namespace(
            manifest_json=root / "sidecar_manifest.json",
            sidecar_dir=Path(str(sidecar_manifest["out_dir"])),
            input_manifest=Path(str(sidecar_manifest["manifest"])),
            geometry=args.geometry,
            frame_count=args.frame_count,
            n_items=int(sidecar_manifest["n_items"]),
            sources=sources,
            allow_dirty=args.allow_dirty,
            allow_historical_commit=bool(getattr(args, "allow_historical_commit", False)),
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--geometry", required=True)
    parser.add_argument("--frame-count", type=int, required=True)
    parser.add_argument("--sources", nargs="+", default=None)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument(
        "--allow-historical-commit",
        action="store_true",
        help=(
            "Allow clean sidecar gates generated at ancestor commits. Use this "
            "for committed M3 gate artifacts validated after later analysis commits."
        ),
    )
    args = parser.parse_args()
    validate(args)
    print(f"sidecar-equivalence gate OK: {args.root}")


if __name__ == "__main__":
    main()
