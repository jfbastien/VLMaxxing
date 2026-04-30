#!/usr/bin/env python3
"""Audit tracked artifacts for partial-snapshot integrity.

Current scope:

1. Every tracked `*_summary.json` with both `completed_item_ids` and
   `requested_item_ids` present: flag rows where
   `len(completed) < len(requested)` unless explicitly marked
   `stopped_early: true`.
2. Every `*_summary.json` with zero completed items but a non-zero
   `cached_accuracy` / `dense_accuracy` / `agreement` is flagged
   (sanity guard against malformed summaries).
3. Paper figure/data snapshots must cite source paths that exist in the
   checkout and are tracked by git.

Not yet implemented (see TODOs in code):

- summary/jsonl row-count cross-check
- note-to-artifact path reference check (scan is stubbed)
- nested wrapper schemas (e.g., phase 1.16 aggregate wrappers)

Run: `uv run python scripts/audit_artifact_integrity.py`

Exit codes:

- 0: clean
- 1: integrity violations found (printed to stderr)

This is a CPU-only check. Safe to run while GPU-bound phases are
in-flight.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path  # noqa: I001

ARTIFACTS_ROOT = Path("research/experiments/2026/artifacts")
EXPERIMENTS_ROOT = Path("research/experiments/2026")
PAPER_DATA_ROOTS = (Path("paper/figures"), Path("paper/arxiv/generated/data"))
SOURCE_KEYS = {
    "source",
    "artifact",
    "patched_source",
    "reference_source",
    "metrics_source",
    "summary_source",
}


def _check_summary(path: Path) -> list[str]:
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return [f"JSON decode error in {path}: {exc}"]

    problems: list[str] = []
    completed = payload.get("completed_item_ids")
    requested = payload.get("requested_item_ids")
    stopped_early = bool(payload.get("stopped_early", False))

    if (
        requested is not None
        and completed is not None
        and len(completed) < len(requested)
        and not stopped_early
    ):
        problems.append(
            f"{path}: partial snapshot ({len(completed)}/{len(requested)}) but stopped_early=false"
        )

    # sanity check: if a cached_accuracy is reported but no items are
    # completed, something is off.
    if completed is not None and len(completed) == 0:
        for field in ("cached_accuracy", "dense_accuracy", "agreement"):
            if field in payload and payload[field] not in (None, 0.0):
                problems.append(f"{path}: reports {field}={payload[field]} but 0 completed items")
    return problems


def _scan_summaries() -> list[str]:
    problems: list[str] = []
    for path in ARTIFACTS_ROOT.rglob("*_summary.json"):
        if "phase" not in path.name and "phase" not in str(path.parent):
            continue
        problems.extend(_check_summary(path))
    return problems


def _scan_note_references() -> list[str]:
    problems: list[str] = []
    for note in EXPERIMENTS_ROOT.glob("*.md"):
        text = note.read_text()
        for line in text.splitlines():
            stripped = line.strip()
            if "phase1_" not in stripped or "artifacts/" not in stripped:
                continue
            # crude path extract: find 'research/experiments/2026/artifacts/'
            # in the line and grab a path-like token
            marker = "research/experiments/2026/artifacts/"
            idx = stripped.find(marker)
            if idx < 0:
                continue
            raw = stripped[idx:]
            for term in (" ", ")", "`", "]", "(", ","):
                if term in raw:
                    raw = raw.split(term, 1)[0]
            if not raw:
                continue
            path = Path(raw)
            if not path.exists():
                problems.append(f"{note}: references non-existent artifact {path}")
    return problems


def _tracked_paths() -> set[str]:
    output = subprocess.check_output(["git", "ls-files"], text=True)
    return set(output.splitlines())


def _iter_source_paths(payload: object) -> list[str]:
    paths: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in SOURCE_KEYS and isinstance(value, str):
                paths.append(value)
            elif (key == "source_paths" or key.endswith("_source_paths")) and isinstance(
                value, list
            ):
                paths.extend(str(item) for item in value)
            else:
                paths.extend(_iter_source_paths(value))
    elif isinstance(payload, list):
        for value in payload:
            paths.extend(_iter_source_paths(value))
    return paths


def _is_repo_path(path: str) -> bool:
    return path.startswith(("docs/", "paper/", "research/", "scripts/", "src/", "tests/"))


def _scan_paper_data_sources() -> list[str]:
    problems: list[str] = []
    tracked = _tracked_paths()
    for root in PAPER_DATA_ROOTS:
        if not root.exists():
            continue
        for path in root.glob("*.json"):
            try:
                payload = json.loads(path.read_text())
            except json.JSONDecodeError as exc:
                problems.append(f"{path}: JSON decode error: {exc}")
                continue
            for source in _iter_source_paths(payload):
                if not _is_repo_path(source):
                    continue
                source_path = Path(source)
                if not source_path.exists():
                    problems.append(f"{path}: cites missing source path {source}")
                elif source not in tracked:
                    problems.append(f"{path}: cites untracked source path {source}")
    return problems


def main() -> int:
    problems: list[str] = []
    problems.extend(_scan_summaries())
    problems.extend(_scan_paper_data_sources())
    # Note-reference check is noisy for preregs that reference
    # pending artifacts; skip for now but leave the hook in place.
    # problems.extend(_scan_note_references())

    if not problems:
        print("artifact-integrity: OK")
        return 0
    print("artifact-integrity: FAILED", file=sys.stderr)
    for problem in problems:
        print(f"  - {problem}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
