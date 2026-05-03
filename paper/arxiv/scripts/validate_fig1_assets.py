#!/usr/bin/env python3
"""Validate Figure-1/appendix candidate manifests after packaging."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ASSET_KEYS = ("frames", "subtle_overlays", "readable_masks", "exact_overlays")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def resolve_asset_path(root: Path, rel_path: str) -> Path:
    rel = Path(rel_path)
    candidates = [root / rel]
    prefix = Path("paper") / "arxiv"
    if len(rel.parts) >= 2 and Path(*rel.parts[:2]) == prefix:
        candidates.append(root / Path(*rel.parts[2:]))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def validate_manifest(repo_root: Path, manifest: Path) -> list[str]:
    data = load_json(manifest)
    missing: list[str] = []
    for cidx, candidate in enumerate(data.get("candidates", []), start=1):
        candidate_id = candidate.get("candidate_id", f"candidate_{cidx}")
        assets = candidate.get("assets") or {}
        for key in ASSET_KEYS:
            for rel in assets.get(key, []):
                path = resolve_asset_path(repo_root, rel)
                if not path.exists():
                    missing.append(f"{manifest.name}: {candidate_id}: missing {key}: {rel}")
        for tidx, transition in enumerate(assets.get("transitions", []), start=1):
            for required in (
                "fresh_fraction_active",
                "raw_novel_fraction_active",
                "stale_fraction_active",
            ):
                if required not in transition:
                    missing.append(
                        f"{manifest.name}: {candidate_id}: transition {tidx} "
                        f"missing metadata {required}"
                    )
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("manifest", type=Path, nargs="+")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    failures: list[str] = []
    for manifest in args.manifest:
        failures.extend(validate_manifest(repo_root, manifest.resolve()))

    if failures:
        print("Figure candidate manifest validation FAILED:")
        for line in failures[:80]:
            print(f"  - {line}")
        if len(failures) > 80:
            print(f"  ... {len(failures) - 80} more")
        return 2

    print("Figure candidate manifest validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
