"""Small provenance helpers for generated experiment artifacts."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path


def _git_output(repo_root: Path, args: list[str]) -> str | None:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def artifact_metadata(repo_root: Path, *, dirty_scope: str) -> dict[str, object]:
    """Return lightweight git/timestamp metadata for a run artifact."""

    status = _git_output(repo_root, ["status", "--short"])
    return {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "git_commit": _git_output(repo_root, ["rev-parse", "HEAD"]),
        "git_dirty": bool(status),
        "git_dirty_scope": dirty_scope,
    }
