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


def _repo_relative(repo_root: Path, path: Path) -> str | None:
    repo = repo_root.resolve(strict=False)
    resolved = path.resolve(strict=False)
    try:
        relative = resolved.relative_to(repo)
    except ValueError:
        return None
    if relative == Path("."):
        return None
    return relative.as_posix()


def artifact_metadata(
    repo_root: Path,
    *,
    dirty_scope: str,
    exclude_paths: list[Path] | None = None,
) -> dict[str, object]:
    """Return lightweight git/timestamp metadata for a run artifact."""

    status_args = ["status", "--short"]
    if exclude_paths:
        status_args.append("--")
        status_args.append(".")
        for path in exclude_paths:
            relative = _repo_relative(repo_root, path)
            if relative is not None:
                status_args.append(f":(exclude){relative}")
    status = _git_output(repo_root, status_args)
    return {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "git_commit": _git_output(repo_root, ["rev-parse", "HEAD"]),
        "git_dirty": bool(status),
        "git_dirty_scope": dirty_scope,
    }
