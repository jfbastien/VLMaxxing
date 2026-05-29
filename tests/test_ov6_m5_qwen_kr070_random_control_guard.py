from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_ov6_m5_qwen_kr070_random_control.sh"
REGISTRY_PATH = "research/experiments/registry.md"
PREREG_PATH = "research/experiments/2026/2026-05-26-qwen-kr070-random-control-prereg.md"
WRAPPER_PATH = "scripts/run_ov6_m5_qwen_kr070_random_control.sh"
CONTROL_ROOT = "m5_ov6_qwen_n57_kr070_l2_random_control"
COMPARATOR_PATHS = (
    f"{CONTROL_ROOT}/dense/",
    f"{CONTROL_ROOT}/magnitude_norm/",
    f"{CONTROL_ROOT}/codec_novel_coded/",
)
SEED_PATHS = (
    f"{CONTROL_ROOT}/uniform_random_seed1/",
    f"{CONTROL_ROOT}/uniform_random_seed7/",
    f"{CONTROL_ROOT}/uniform_random_seed42/",
    f"{CONTROL_ROOT}/uniform_random_seed100/",
)
AUDIT_FILENAME = "codec_vs_random_multiseed_audit.json"


def _base_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in (
        "M5Q_CLEAN_CONTROL_PREREG",
        "M5Q70_CLEAN_CONTROL_PREREG",
        "M5Q70_OUT_DIR",
        "OV6_CANONICAL_OUT_DIR_FOR_TESTS",
        "OV6_PREFLIGHT_ONLY",
        "FAKE_GIT_DIRTY_PATH",
        "FAKE_GIT_STATUS_OUTPUT",
        "FAKE_GIT_STATUS_EXCLUDE_PATH",
        "FAKE_GIT_CAT_FILE_ERROR",
    ):
        env.pop(key, None)
    return env


def _write_fake_git(
    tmp_path: Path,
    known_paths: tuple[str, ...],
    allowed_grep_markers: tuple[tuple[str, str], ...],
) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_path = tmp_path / "git-grep.log"
    cat_cases = "\n".join(f'    "HEAD:{path}") echo blob; exit 0 ;;' for path in known_paths)
    grep_cases = "\n".join(
        f'    "{path}::{pattern}") exit 0 ;;' for path, pattern in allowed_grep_markers
    )
    git_script = bin_dir / "git"
    git_script.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
if [[ "$1" == "cat-file" && "$2" == "-t" ]]; then
  if [[ -n "${{FAKE_GIT_CAT_FILE_ERROR:-}}" ]]; then
    echo "fatal: injected cat-file failure" >&2
    exit 128
  fi
  case "$3" in
{cat_cases}
  esac
  echo "fatal: path '${{3#HEAD:}}' does not exist in 'HEAD'" >&2
  exit 128
fi
if [[ "$1" == "grep" ]]; then
  pattern=""
  for ((i = 1; i <= $#; i++)); do
    if [[ "${{!i}}" == "--fixed-strings" ]]; then
      j=$((i + 1))
      pattern="${{!j}}"
    fi
  done
  if [[ -z "$pattern" ]]; then
    echo "fake git grep missing --fixed-strings pattern: $*" >&2
    exit 1
  fi
  path="${{!#}}"
  echo "$path::$pattern" >> "{log_path}"
  case "$path::$pattern" in
{grep_cases}
  esac
  exit 1
fi
if [[ "$1" == "diff" ]]; then
  path="${{!#}}"
  if [[ "${{FAKE_GIT_DIRTY_PATH:-}}" == "$path" ]]; then
    exit 1
  fi
  exit 0
fi
if [[ "$1" == "status" ]]; then
  if [[ -n "${{FAKE_GIT_STATUS_OUTPUT:-}}" ]]; then
    if [[ -n "${{FAKE_GIT_STATUS_EXCLUDE_PATH:-}}" ]]; then
      for arg in "$@"; do
        if [[ "$arg" == ":(exclude)${{FAKE_GIT_STATUS_EXCLUDE_PATH}}" ]]; then
          exit 0
        fi
      done
    fi
    echo "${{FAKE_GIT_STATUS_OUTPUT}}"
  fi
  exit 0
fi
if [[ "$1" == "rev-parse" && "$2" == "HEAD" ]]; then
  echo fake-head
  exit 0
fi
echo "unexpected fake git call: $*" >&2
exit 1
"""
    )
    git_script.chmod(0o755)
    return bin_dir


def _required_prereg_markers() -> tuple[str, ...]:
    return (WRAPPER_PATH, CONTROL_ROOT, *COMPARATOR_PATHS, *SEED_PATHS, AUDIT_FILENAME)


def _required_registry_markers() -> tuple[str, ...]:
    return (PREREG_PATH, WRAPPER_PATH, *COMPARATOR_PATHS, *SEED_PATHS, AUDIT_FILENAME)


def _preflight_env(
    tmp_path: Path,
    known_paths: tuple[str, ...],
    allowed_grep_markers: tuple[tuple[str, str], ...],
) -> dict[str, str]:
    env = _base_env()
    fake_bin = _write_fake_git(tmp_path, known_paths, allowed_grep_markers)
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["OV6_PREFLIGHT_ONLY"] = "1"
    env["OV6_CANONICAL_OUT_DIR_FOR_TESTS"] = str(tmp_path / CONTROL_ROOT)
    return env


def _complete_preflight_env(tmp_path: Path) -> dict[str, str]:
    allowed_markers = (
        *((PREREG_PATH, marker) for marker in _required_prereg_markers()),
        *((REGISTRY_PATH, marker) for marker in _required_registry_markers()),
    )
    env = _preflight_env(tmp_path, (PREREG_PATH, REGISTRY_PATH), allowed_markers)
    env["M5Q_CLEAN_CONTROL_PREREG"] = PREREG_PATH
    return env


def test_random_control_wrapper_requires_committed_preregistration(tmp_path: Path) -> None:
    env = _preflight_env(tmp_path, (REGISTRY_PATH,), ())

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "requires a complete, committed preregistration" in result.stderr
    assert WRAPPER_PATH in result.stderr


def test_random_control_wrapper_clean_preregistration_preflight_passes(
    tmp_path: Path,
) -> None:
    env = _complete_preflight_env(tmp_path)

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "preflight passed" in result.stdout
    log = (tmp_path / "git-grep.log").read_text()
    assert f"{PREREG_PATH}::{WRAPPER_PATH}" in log
    assert f"{REGISTRY_PATH}::{WRAPPER_PATH}" in log
    for arm_path in (*COMPARATOR_PATHS, *SEED_PATHS):
        assert f"{PREREG_PATH}::{arm_path}" in log
        assert f"{REGISTRY_PATH}::{arm_path}" in log


def test_random_control_wrapper_uses_full_historical_equivalence_gate() -> None:
    text = SCRIPT.read_text()

    assert "EQUIV_SOURCES=(novel_coded motion residual)" in text
    gate_call = text.split("scripts/validate_ov6_sidecar_equivalence_gate.py \\", maxsplit=1)[1]
    gate_call = gate_call.split('if [[ ! -f "$SIDECAR_MANIFEST" ]]', maxsplit=1)[0]
    assert '--sources "${EQUIV_SOURCES[@]}" \\' in gate_call
    assert "--allow-historical-commit" in gate_call
    sidecar_cache_validation = text.split(
        "scripts/validate_ov6_codec_score_sidecars.py \\", maxsplit=1
    )[1]
    sidecar_cache_validation = sidecar_cache_validation.split("validate_arm() {", maxsplit=1)[0]
    assert '--sources "$SOURCE"' in sidecar_cache_validation
    assert "--allow-historical-commit" not in sidecar_cache_validation


def test_random_control_wrapper_rejects_missing_wrapper_marker(
    tmp_path: Path,
) -> None:
    allowed_markers = (
        *((PREREG_PATH, marker) for marker in _required_prereg_markers() if marker != WRAPPER_PATH),
        *((REGISTRY_PATH, marker) for marker in _required_registry_markers()),
    )
    env = _preflight_env(tmp_path, (PREREG_PATH, REGISTRY_PATH), allowed_markers)
    env["M5Q_CLEAN_CONTROL_PREREG"] = PREREG_PATH

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "requires a complete, committed preregistration" in result.stderr
    assert f"{PREREG_PATH}::{WRAPPER_PATH}" in (tmp_path / "git-grep.log").read_text()


def test_random_control_wrapper_rejects_dirty_preregistration(tmp_path: Path) -> None:
    env = _complete_preflight_env(tmp_path)
    env["FAKE_GIT_DIRTY_PATH"] = PREREG_PATH

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "clean-control preregistration" in result.stderr
    assert "staged or unstaged edits" in result.stderr


def test_random_control_wrapper_rejects_dirty_registry(tmp_path: Path) -> None:
    env = _complete_preflight_env(tmp_path)
    env["FAKE_GIT_DIRTY_PATH"] = REGISTRY_PATH

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "experiment registry" in result.stderr
    assert "staged or unstaged edits" in result.stderr


def test_random_control_wrapper_rejects_output_override(tmp_path: Path) -> None:
    env = _complete_preflight_env(tmp_path)
    env["M5Q70_OUT_DIR"] = str(tmp_path / "alternate")

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "output-root overrides" in result.stderr
    assert "allowed" in result.stderr


@pytest.mark.parametrize(
    ("env_name", "env_value"),
    (
        ("M5Q70_MANIFEST", "research/benchmark_manifests/other.toml"),
        ("M5Q70_MODEL_PATH", "/tmp/not-the-preregistered-model"),
        ("M5Q70_FRAME_COUNT", "16"),
        ("M5Q70_MAX_TOKENS", "64"),
        ("M5Q70_LAYER", "8"),
        ("M5Q70_KEEP_RATE", "0.50"),
        ("M5Q70_EQUIV_ROOT", "research/experiments/2026/artifacts/other_gate"),
        ("M5Q70_SIDECAR_DIR", "research/experiments/2026/artifacts/other_sidecars"),
        ("M5Q70_SIDECAR_MANIFEST", "research/experiments/2026/artifacts/other.json"),
    ),
)
def test_random_control_wrapper_rejects_protocol_config_overrides(
    tmp_path: Path,
    env_name: str,
    env_value: str,
) -> None:
    env = _complete_preflight_env(tmp_path)
    env[env_name] = env_value

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert env_name in result.stderr
    assert "fixed by the preregistration" in result.stderr


def test_random_control_wrapper_rejects_existing_artifact_without_marker(
    tmp_path: Path,
) -> None:
    env = _complete_preflight_env(tmp_path)
    root = tmp_path / CONTROL_ROOT
    (root / "uniform_random_seed42").mkdir(parents=True)

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "wrapper marker is missing" in result.stderr


def test_random_control_wrapper_rejects_existing_sidecar_manifest_without_marker(
    tmp_path: Path,
) -> None:
    env = _complete_preflight_env(tmp_path)
    root = tmp_path / CONTROL_ROOT
    root.mkdir(parents=True)
    (root / "sidecar_manifest.json").write_text("{}\n")

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "wrapper marker is missing" in result.stderr


def test_random_control_wrapper_rejects_unrelated_dirty_worktree(tmp_path: Path) -> None:
    env = _complete_preflight_env(tmp_path)
    env["FAKE_GIT_STATUS_OUTPUT"] = " M README.md"

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "changes outside" in result.stderr
    assert "README.md" in result.stderr


def test_random_control_wrapper_allows_absolute_in_repo_output_root_dirtiness(
    tmp_path: Path,
) -> None:
    env = _complete_preflight_env(tmp_path)
    absolute_root = REPO_ROOT / "research/experiments/2026/artifacts/test-random-control-root"
    relative_root = "research/experiments/2026/artifacts/test-random-control-root"
    env["OV6_CANONICAL_OUT_DIR_FOR_TESTS"] = str(absolute_root)
    env["FAKE_GIT_STATUS_OUTPUT"] = f"?? {relative_root}/dense/summary.json"
    env["FAKE_GIT_STATUS_EXCLUDE_PATH"] = relative_root

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "preflight passed" in result.stdout


def test_random_control_wrapper_rejects_unexpected_cat_file_failure(
    tmp_path: Path,
) -> None:
    env = _complete_preflight_env(tmp_path)
    env["FAKE_GIT_CAT_FILE_ERROR"] = "1"

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "git cat-file failed" in result.stderr
    assert "injected cat-file failure" in result.stderr


def test_random_control_wrapper_accepts_existing_artifact_with_matching_marker(
    tmp_path: Path,
) -> None:
    env = _complete_preflight_env(tmp_path)
    root = tmp_path / CONTROL_ROOT
    (root / "uniform_random_seed42").mkdir(parents=True)
    (root / "clean_control_run_marker.json").write_text(
        json_marker := (
            "{\n"
            '  "schema": "ov6_qwen_kr070_random_control_run_v1",\n'
            '  "git_commit": "fake-head",\n'
            f'  "preregistration": "{PREREG_PATH}",\n'
            f'  "wrapper": "{WRAPPER_PATH}",\n'
            f'  "root": "{CONTROL_ROOT}",\n'
            '  "manifest": "research/benchmark_manifests/videomme_short_present_v1_n57.toml",\n'
            '  "model": "Qwen2.5-VL-7B-Instruct-4bit",\n'
            '  "frame_count": "8",\n'
            '  "layer": "2",\n'
            '  "configured_keep_rate": "0.70",\n'
            '  "seeds": "1 7 42 100"\n'
            "}\n"
        )
    )
    assert json_marker

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "preflight passed" in result.stdout


def test_random_control_wrapper_rejects_existing_marker_from_other_commit(
    tmp_path: Path,
) -> None:
    env = _complete_preflight_env(tmp_path)
    root = tmp_path / CONTROL_ROOT
    (root / "uniform_random_seed42").mkdir(parents=True)
    (root / "clean_control_run_marker.json").write_text(
        "{\n"
        '  "schema": "ov6_qwen_kr070_random_control_run_v1",\n'
        '  "git_commit": "other-head",\n'
        f'  "preregistration": "{PREREG_PATH}",\n'
        f'  "wrapper": "{WRAPPER_PATH}",\n'
        f'  "root": "{CONTROL_ROOT}",\n'
        '  "manifest": "research/benchmark_manifests/videomme_short_present_v1_n57.toml",\n'
        '  "model": "Qwen2.5-VL-7B-Instruct-4bit",\n'
        '  "frame_count": "8",\n'
        '  "layer": "2",\n'
        '  "configured_keep_rate": "0.70",\n'
        '  "seeds": "1 7 42 100"\n'
        "}\n"
    )

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "run marker does not match" in result.stderr
    assert "fake-head" in result.stderr
