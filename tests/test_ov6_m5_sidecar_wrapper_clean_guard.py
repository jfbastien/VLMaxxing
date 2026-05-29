from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_fake_git(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    git_script = bin_dir / "git"
    git_script.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
if [[ "$1" == "status" ]]; then
  if [[ -n "${FAKE_GIT_STATUS_OUTPUT:-}" ]]; then
    echo "${FAKE_GIT_STATUS_OUTPUT}"
  fi
  exit 0
fi
echo "unexpected fake git call: $*" >&2
exit 1
"""
    )
    git_script.chmod(0o755)
    return bin_dir


@pytest.mark.parametrize(
    ("script", "env_prefix", "label"),
    (
        (
            "scripts/run_ov6_m5_gemma_n57_confirmation.sh",
            "M5G",
            "m5-gemma-n57",
        ),
        (
            "scripts/run_ov6_m5_qwen_frame16_boundary.sh",
            "M5F16",
            "m5-qwen-f16",
        ),
    ),
)
def test_sidecar_backed_m5_wrappers_reject_unrelated_dirty_worktree(
    tmp_path: Path,
    script: str,
    env_prefix: str,
    label: str,
) -> None:
    env = os.environ.copy()
    fake_bin = _write_fake_git(tmp_path)
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["FAKE_GIT_STATUS_OUTPUT"] = " M README.md"
    env[f"{env_prefix}_OUT_DIR"] = str(tmp_path / "out")

    result = subprocess.run(
        ["bash", str(REPO_ROOT / script)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert f"[{label}] refusing to launch" in result.stderr
    assert "changes outside the output root" in result.stderr
    assert "README.md" in result.stderr
