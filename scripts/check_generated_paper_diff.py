#!/usr/bin/env python3
"""Fail on generated paper drift, except web-only PNG raster differences."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

CHECKED_ROOTS = ["paper/arxiv/generated", "paper/figures"]
IGNORED_SUFFIXES = {".png"}


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=False, capture_output=True, text=True)


def _changed_paths() -> list[str]:
    result = _run(["git", "diff", "--name-only", "--", *CHECKED_ROOTS])
    if result.returncode not in (0, 1):
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    return [line for line in result.stdout.splitlines() if line]


def _untracked_paths() -> list[str]:
    result = _run(["git", "status", "--porcelain", "--", *CHECKED_ROOTS])
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    paths: list[str] = []
    for line in result.stdout.splitlines():
        if not line.startswith("?? "):
            continue
        paths.append(line[3:])
    return paths


def _is_ignored_raster(path: str) -> bool:
    return Path(path).suffix.lower() in IGNORED_SUFFIXES


def _restore_ignored_rasters(paths: list[str]) -> None:
    tracked = [
        path for path in paths if not _run(["git", "ls-files", "--error-unmatch", path]).returncode
    ]
    untracked = [path for path in paths if path not in tracked]

    if tracked:
        result = _run(["git", "checkout", "--", *tracked])
        if result.returncode != 0:
            sys.stderr.write(result.stderr)
            raise SystemExit(result.returncode)

    for path in untracked:
        Path(path).unlink(missing_ok=True)


def main() -> int:
    changed = _changed_paths()
    untracked = _untracked_paths()
    blocking = [path for path in changed + untracked if not _is_ignored_raster(path)]

    if blocking:
        print("generated paper assets drifted:")
        for path in blocking:
            print(f"  {path}")
        subprocess.run(["git", "diff", "--", *blocking], check=False)
        return 1

    ignored = [path for path in changed + untracked if _is_ignored_raster(path)]
    if ignored:
        print("generated paper PNG raster drift ignored:")
        for path in ignored:
            print(f"  {path}")
        print("source assets remained stable; PNGs are web-friendly duplicates.")
        _restore_ignored_rasters(ignored)
        print("restored ignored PNG drift to keep later bundle checks clean.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
