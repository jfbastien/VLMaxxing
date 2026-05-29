import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_ov6_m5_qwen_parity.sh"
REGISTRY_PATH = "research/experiments/registry.md"
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
        "M5Q_OUT_DIR",
        "OV6_CANONICAL_OUT_DIR_FOR_TESTS",
        "OV6_ALLOW_CLOSE_RANDOM_CONTROL_WINDOW",
        "OV6_CLOSURE_RECORD",
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
echo "unexpected fake git call: $*" >&2
exit 1
"""
    )
    git_script.chmod(0o755)
    return bin_dir


def _preflight_env(
    tmp_path: Path,
    known_paths: tuple[str, ...],
    allowed_grep_markers: tuple[tuple[str, str], ...],
) -> dict[str, str]:
    env = _base_env()
    fake_bin = _write_fake_git(tmp_path, known_paths, allowed_grep_markers)
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["OV6_PREFLIGHT_ONLY"] = "1"
    env["OV6_CANONICAL_OUT_DIR_FOR_TESTS"] = str(tmp_path / "canonical-parity-root")
    return env


def test_m5_qwen_parity_requires_clean_control_preregistration(tmp_path: Path) -> None:
    # The positive path proceeds into sidecar validation and model-arm launch.
    # Unit coverage pins the preflight's no-launch safety boundaries instead.
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
    assert "without a complete, committed clean-control" in result.stderr
    assert "M5Q_CLEAN_CONTROL_PREREG=" in result.stderr
    assert "Required registry arm-path strings:" in result.stderr


def test_m5_qwen_parity_closure_override_requires_closure_record(tmp_path: Path) -> None:
    env = _preflight_env(tmp_path, (REGISTRY_PATH,), ())
    env["OV6_ALLOW_CLOSE_RANDOM_CONTROL_WINDOW"] = "1"

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "requires a committed closure record" in result.stderr
    assert "OV6_CLOSURE_RECORD=" in result.stderr


def test_m5_qwen_parity_clean_preregistration_preflight_passes(
    tmp_path: Path,
) -> None:
    prereg_path = "research/experiments/2026/2026-05-26-qwen-kr070-random-control-prereg.md"
    required_prereg_markers = (
        WRAPPER_PATH,
        CONTROL_ROOT,
        *COMPARATOR_PATHS,
        *SEED_PATHS,
        AUDIT_FILENAME,
    )
    required_registry_markers = (
        prereg_path,
        WRAPPER_PATH,
        *COMPARATOR_PATHS,
        *SEED_PATHS,
        AUDIT_FILENAME,
    )
    allowed_markers = (
        *((prereg_path, marker) for marker in required_prereg_markers),
        *((REGISTRY_PATH, marker) for marker in required_registry_markers),
    )
    env = _preflight_env(tmp_path, (prereg_path, REGISTRY_PATH), allowed_markers)
    env["M5Q_CLEAN_CONTROL_PREREG"] = prereg_path

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
    assert f"{prereg_path}::{WRAPPER_PATH}" in log
    assert f"{REGISTRY_PATH}::{WRAPPER_PATH}" in log
    assert f"{prereg_path}::{CONTROL_ROOT}" in log
    assert f"{REGISTRY_PATH}::{prereg_path}" in log
    for arm_path in (*COMPARATOR_PATHS, *SEED_PATHS):
        assert f"{prereg_path}::{arm_path}" in log
        assert f"{REGISTRY_PATH}::{arm_path}" in log
    assert f"{prereg_path}::{AUDIT_FILENAME}" in log
    assert f"{REGISTRY_PATH}::{AUDIT_FILENAME}" in log


def test_m5_qwen_parity_rejects_incomplete_preregistration(
    tmp_path: Path,
) -> None:
    prereg_path = "research/experiments/2026/2026-05-26-qwen-kr070-random-control-prereg.md"
    required_prereg_markers = (
        WRAPPER_PATH,
        CONTROL_ROOT,
        COMPARATOR_PATHS[0],
        COMPARATOR_PATHS[1],
        *SEED_PATHS,
        AUDIT_FILENAME,
    )
    required_registry_markers = (
        prereg_path,
        WRAPPER_PATH,
        *COMPARATOR_PATHS,
        *SEED_PATHS,
        AUDIT_FILENAME,
    )
    allowed_markers = (
        *((prereg_path, marker) for marker in required_prereg_markers),
        *((REGISTRY_PATH, marker) for marker in required_registry_markers),
    )
    env = _preflight_env(tmp_path, (prereg_path, REGISTRY_PATH), allowed_markers)
    env["M5Q_CLEAN_CONTROL_PREREG"] = prereg_path

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "without a complete, committed clean-control" in result.stderr
    log = (tmp_path / "git-grep.log").read_text()
    assert f"{prereg_path}::{COMPARATOR_PATHS[2]}" in log


def test_m5_qwen_parity_rejects_preregistration_missing_wrapper_marker(
    tmp_path: Path,
) -> None:
    prereg_path = "research/experiments/2026/2026-05-26-qwen-kr070-random-control-prereg.md"
    required_prereg_markers = (
        CONTROL_ROOT,
        *COMPARATOR_PATHS,
        *SEED_PATHS,
        AUDIT_FILENAME,
    )
    required_registry_markers = (
        prereg_path,
        WRAPPER_PATH,
        *COMPARATOR_PATHS,
        *SEED_PATHS,
        AUDIT_FILENAME,
    )
    allowed_markers = (
        *((prereg_path, marker) for marker in required_prereg_markers),
        *((REGISTRY_PATH, marker) for marker in required_registry_markers),
    )
    env = _preflight_env(tmp_path, (prereg_path, REGISTRY_PATH), allowed_markers)
    env["M5Q_CLEAN_CONTROL_PREREG"] = prereg_path

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "without a complete, committed clean-control" in result.stderr
    log = (tmp_path / "git-grep.log").read_text()
    assert f"{prereg_path}::{WRAPPER_PATH}" in log


def test_m5_qwen_parity_rejects_registry_missing_audit_marker(
    tmp_path: Path,
) -> None:
    prereg_path = "research/experiments/2026/2026-05-26-qwen-kr070-random-control-prereg.md"
    required_prereg_markers = (
        WRAPPER_PATH,
        CONTROL_ROOT,
        *COMPARATOR_PATHS,
        *SEED_PATHS,
        AUDIT_FILENAME,
    )
    required_registry_markers = (prereg_path, WRAPPER_PATH, *COMPARATOR_PATHS, *SEED_PATHS)
    allowed_markers = (
        *((prereg_path, marker) for marker in required_prereg_markers),
        *((REGISTRY_PATH, marker) for marker in required_registry_markers),
    )
    env = _preflight_env(tmp_path, (prereg_path, REGISTRY_PATH), allowed_markers)
    env["M5Q_CLEAN_CONTROL_PREREG"] = prereg_path

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "without a complete, committed clean-control" in result.stderr
    log = (tmp_path / "git-grep.log").read_text()
    assert f"{REGISTRY_PATH}::{AUDIT_FILENAME}" in log


def test_m5_qwen_parity_rejects_incomplete_registry_marker(
    tmp_path: Path,
) -> None:
    prereg_path = "research/experiments/2026/2026-05-26-qwen-kr070-random-control-prereg.md"
    required_prereg_markers = (
        WRAPPER_PATH,
        CONTROL_ROOT,
        *COMPARATOR_PATHS,
        *SEED_PATHS,
        AUDIT_FILENAME,
    )
    required_registry_markers = (
        prereg_path,
        WRAPPER_PATH,
        COMPARATOR_PATHS[0],
        COMPARATOR_PATHS[1],
        *SEED_PATHS,
        AUDIT_FILENAME,
    )
    allowed_markers = (
        *((prereg_path, marker) for marker in required_prereg_markers),
        *((REGISTRY_PATH, marker) for marker in required_registry_markers),
    )
    env = _preflight_env(tmp_path, (prereg_path, REGISTRY_PATH), allowed_markers)
    env["M5Q_CLEAN_CONTROL_PREREG"] = prereg_path

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "without a complete, committed clean-control" in result.stderr
    log = (tmp_path / "git-grep.log").read_text()
    assert f"{REGISTRY_PATH}::{COMPARATOR_PATHS[2]}" in log


def test_m5_qwen_parity_rejects_dirty_preregistration(tmp_path: Path) -> None:
    prereg_path = "research/experiments/2026/2026-05-26-qwen-kr070-random-control-prereg.md"
    required_prereg_markers = (
        WRAPPER_PATH,
        CONTROL_ROOT,
        *COMPARATOR_PATHS,
        *SEED_PATHS,
        AUDIT_FILENAME,
    )
    required_registry_markers = (
        prereg_path,
        WRAPPER_PATH,
        *COMPARATOR_PATHS,
        *SEED_PATHS,
        AUDIT_FILENAME,
    )
    allowed_markers = (
        *((prereg_path, marker) for marker in required_prereg_markers),
        *((REGISTRY_PATH, marker) for marker in required_registry_markers),
    )
    env = _preflight_env(tmp_path, (prereg_path, REGISTRY_PATH), allowed_markers)
    env["M5Q_CLEAN_CONTROL_PREREG"] = prereg_path
    env["FAKE_GIT_DIRTY_PATH"] = prereg_path

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "clean-control preregistration has staged" in result.stderr


def test_m5_qwen_parity_rejects_dirty_registry(tmp_path: Path) -> None:
    prereg_path = "research/experiments/2026/2026-05-26-qwen-kr070-random-control-prereg.md"
    required_prereg_markers = (
        WRAPPER_PATH,
        CONTROL_ROOT,
        *COMPARATOR_PATHS,
        *SEED_PATHS,
        AUDIT_FILENAME,
    )
    required_registry_markers = (
        prereg_path,
        WRAPPER_PATH,
        *COMPARATOR_PATHS,
        *SEED_PATHS,
        AUDIT_FILENAME,
    )
    allowed_markers = (
        *((prereg_path, marker) for marker in required_prereg_markers),
        *((REGISTRY_PATH, marker) for marker in required_registry_markers),
    )
    env = _preflight_env(tmp_path, (prereg_path, REGISTRY_PATH), allowed_markers)
    env["M5Q_CLEAN_CONTROL_PREREG"] = prereg_path
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
    assert "experiment registry has staged" in result.stderr


@pytest.mark.parametrize("artifact_name", ("summary.json", "results.jsonl", "run.log"))
def test_m5_qwen_parity_rejects_clean_prereg_after_seed42_artifact(
    tmp_path: Path,
    artifact_name: str,
) -> None:
    prereg_path = "research/experiments/2026/2026-05-26-qwen-kr070-random-control-prereg.md"
    required_prereg_markers = (
        WRAPPER_PATH,
        CONTROL_ROOT,
        *COMPARATOR_PATHS,
        *SEED_PATHS,
        AUDIT_FILENAME,
    )
    required_registry_markers = (
        prereg_path,
        WRAPPER_PATH,
        *COMPARATOR_PATHS,
        *SEED_PATHS,
        AUDIT_FILENAME,
    )
    allowed_markers = (
        *((prereg_path, marker) for marker in required_prereg_markers),
        *((REGISTRY_PATH, marker) for marker in required_registry_markers),
    )
    canonical_parity_root = tmp_path / "canonical-parity-root"
    uniform_random_dir = canonical_parity_root / "uniform_random"
    uniform_random_dir.mkdir(parents=True)
    artifact_path = uniform_random_dir / artifact_name
    artifact_path.write_text("{}")
    env = _preflight_env(tmp_path, (prereg_path, REGISTRY_PATH), allowed_markers)
    env["M5Q_CLEAN_CONTROL_PREREG"] = prereg_path
    env["OV6_CANONICAL_OUT_DIR_FOR_TESTS"] = str(canonical_parity_root)

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "seed-42 parity artifacts already exist" in result.stderr
    assert "clean four-seed random-control window is closed" in result.stderr


def test_m5_qwen_parity_rejects_clean_prereg_after_seed42_directory(
    tmp_path: Path,
) -> None:
    prereg_path = "research/experiments/2026/2026-05-26-qwen-kr070-random-control-prereg.md"
    required_prereg_markers = (
        WRAPPER_PATH,
        CONTROL_ROOT,
        *COMPARATOR_PATHS,
        *SEED_PATHS,
        AUDIT_FILENAME,
    )
    required_registry_markers = (
        prereg_path,
        WRAPPER_PATH,
        *COMPARATOR_PATHS,
        *SEED_PATHS,
        AUDIT_FILENAME,
    )
    allowed_markers = (
        *((prereg_path, marker) for marker in required_prereg_markers),
        *((REGISTRY_PATH, marker) for marker in required_registry_markers),
    )
    canonical_parity_root = tmp_path / "canonical-parity-root"
    (canonical_parity_root / "uniform_random").mkdir(parents=True)
    env = _preflight_env(tmp_path, (prereg_path, REGISTRY_PATH), allowed_markers)
    env["M5Q_CLEAN_CONTROL_PREREG"] = prereg_path

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "seed-42 parity artifacts already exist" in result.stderr
    assert "clean four-seed random-control window is closed" in result.stderr


def test_m5_qwen_parity_rejects_out_dir_override_on_clean_path(
    tmp_path: Path,
) -> None:
    prereg_path = "research/experiments/2026/2026-05-26-qwen-kr070-random-control-prereg.md"
    required_prereg_markers = (
        WRAPPER_PATH,
        CONTROL_ROOT,
        *COMPARATOR_PATHS,
        *SEED_PATHS,
        AUDIT_FILENAME,
    )
    required_registry_markers = (
        prereg_path,
        WRAPPER_PATH,
        *COMPARATOR_PATHS,
        *SEED_PATHS,
        AUDIT_FILENAME,
    )
    allowed_markers = (
        *((prereg_path, marker) for marker in required_prereg_markers),
        *((REGISTRY_PATH, marker) for marker in required_registry_markers),
    )
    env = _preflight_env(tmp_path, (prereg_path, REGISTRY_PATH), allowed_markers)
    env["M5Q_CLEAN_CONTROL_PREREG"] = prereg_path
    env["M5Q_OUT_DIR"] = str(tmp_path / "alternate-parity-root")

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "M5Q_OUT_DIR override is not allowed" in result.stderr


def test_m5_qwen_parity_rejects_unrelated_dirty_worktree(tmp_path: Path) -> None:
    prereg_path = "research/experiments/2026/2026-05-26-qwen-kr070-random-control-prereg.md"
    required_prereg_markers = (
        WRAPPER_PATH,
        CONTROL_ROOT,
        *COMPARATOR_PATHS,
        *SEED_PATHS,
        AUDIT_FILENAME,
    )
    required_registry_markers = (
        prereg_path,
        WRAPPER_PATH,
        *COMPARATOR_PATHS,
        *SEED_PATHS,
        AUDIT_FILENAME,
    )
    allowed_markers = (
        *((prereg_path, marker) for marker in required_prereg_markers),
        *((REGISTRY_PATH, marker) for marker in required_registry_markers),
    )
    env = _preflight_env(tmp_path, (prereg_path, REGISTRY_PATH), allowed_markers)
    env["M5Q_CLEAN_CONTROL_PREREG"] = prereg_path
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


def test_m5_qwen_parity_allows_absolute_in_repo_output_root_dirtiness(
    tmp_path: Path,
) -> None:
    prereg_path = "research/experiments/2026/2026-05-26-qwen-kr070-random-control-prereg.md"
    required_prereg_markers = (
        WRAPPER_PATH,
        CONTROL_ROOT,
        *COMPARATOR_PATHS,
        *SEED_PATHS,
        AUDIT_FILENAME,
    )
    required_registry_markers = (
        prereg_path,
        WRAPPER_PATH,
        *COMPARATOR_PATHS,
        *SEED_PATHS,
        AUDIT_FILENAME,
    )
    allowed_markers = (
        *((prereg_path, marker) for marker in required_prereg_markers),
        *((REGISTRY_PATH, marker) for marker in required_registry_markers),
    )
    env = _preflight_env(tmp_path, (prereg_path, REGISTRY_PATH), allowed_markers)
    absolute_root = REPO_ROOT / "research/experiments/2026/artifacts/test-parity-root"
    relative_root = "research/experiments/2026/artifacts/test-parity-root"
    env["M5Q_CLEAN_CONTROL_PREREG"] = prereg_path
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


def test_m5_qwen_parity_rejects_unexpected_cat_file_failure(tmp_path: Path) -> None:
    env = _preflight_env(tmp_path, (REGISTRY_PATH,), ())
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


def test_m5_qwen_parity_rejects_wrong_clean_preregistration_name(
    tmp_path: Path,
) -> None:
    prereg_path = "research/experiments/2026/2026-05-26-random-control-prereg.md"
    allowed_markers = ((REGISTRY_PATH, prereg_path),)
    env = _preflight_env(tmp_path, (prereg_path, REGISTRY_PATH), allowed_markers)
    env["M5Q_CLEAN_CONTROL_PREREG"] = prereg_path

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "without a complete, committed clean-control" in result.stderr
    assert "research/experiments/2026/*qwen*kr070*random*control*prereg.md" in result.stderr


def test_m5_qwen_parity_rejects_wrong_clean_preregistration_year(
    tmp_path: Path,
) -> None:
    prereg_path = "research/experiments/2025/2026-05-26-qwen-kr070-random-control-prereg.md"
    allowed_markers = ((REGISTRY_PATH, prereg_path),)
    env = _preflight_env(tmp_path, (prereg_path, REGISTRY_PATH), allowed_markers)
    env["M5Q_CLEAN_CONTROL_PREREG"] = prereg_path

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "without a complete, committed clean-control" in result.stderr
    assert "research/experiments/2026/*qwen*kr070*random*control*prereg.md" in result.stderr


def test_m5_qwen_parity_bad_prereg_name_not_masked_by_dirty_registry(
    tmp_path: Path,
) -> None:
    prereg_path = "research/experiments/2026/2026-05-26-random-control-prereg.md"
    allowed_markers = ((REGISTRY_PATH, prereg_path),)
    env = _preflight_env(tmp_path, (prereg_path, REGISTRY_PATH), allowed_markers)
    env["M5Q_CLEAN_CONTROL_PREREG"] = prereg_path
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
    assert "without a complete, committed clean-control" in result.stderr
    assert "experiment registry has staged" not in result.stderr


def test_m5_qwen_parity_closure_record_preflight_passes(tmp_path: Path) -> None:
    closure_path = "research/experiments/2026/2026-05-26-qwen-kr070-random-control-closure.md"
    allowed_markers = (
        (closure_path, "OV6_ALLOW_CLOSE_RANDOM_CONTROL_WINDOW=1"),
        (closure_path, "seed-42"),
        (closure_path, "clean-control window"),
        (REGISTRY_PATH, closure_path),
    )
    env = _preflight_env(tmp_path, (closure_path, REGISTRY_PATH), allowed_markers)
    env["OV6_ALLOW_CLOSE_RANDOM_CONTROL_WINDOW"] = "1"
    env["OV6_CLOSURE_RECORD"] = closure_path

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
    assert f"{closure_path}::OV6_ALLOW_CLOSE_RANDOM_CONTROL_WINDOW=1" in log
    assert f"{closure_path}::seed-42" in log
    assert f"{closure_path}::clean-control window" in log
    assert f"{REGISTRY_PATH}::{closure_path}" in log


def test_m5_qwen_parity_closure_record_allows_existing_seed42_artifact(
    tmp_path: Path,
) -> None:
    closure_path = "research/experiments/2026/2026-05-26-qwen-kr070-random-control-closure.md"
    allowed_markers = (
        (closure_path, "OV6_ALLOW_CLOSE_RANDOM_CONTROL_WINDOW=1"),
        (closure_path, "seed-42"),
        (closure_path, "clean-control window"),
        (REGISTRY_PATH, closure_path),
    )
    out_dir = tmp_path / "m5_ov6_qwen_n57_kr070_l2_parity"
    uniform_random_dir = out_dir / "uniform_random"
    uniform_random_dir.mkdir(parents=True)
    (uniform_random_dir / "summary.json").write_text("{}")
    env = _preflight_env(tmp_path, (closure_path, REGISTRY_PATH), allowed_markers)
    env["OV6_ALLOW_CLOSE_RANDOM_CONTROL_WINDOW"] = "1"
    env["OV6_CLOSURE_RECORD"] = closure_path
    env["M5Q_OUT_DIR"] = str(out_dir)

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


def test_m5_qwen_parity_closure_rejects_dirty_registry(tmp_path: Path) -> None:
    closure_path = "research/experiments/2026/2026-05-26-qwen-kr070-random-control-closure.md"
    allowed_markers = (
        (closure_path, "OV6_ALLOW_CLOSE_RANDOM_CONTROL_WINDOW=1"),
        (closure_path, "seed-42"),
        (closure_path, "clean-control window"),
        (REGISTRY_PATH, closure_path),
    )
    env = _preflight_env(tmp_path, (closure_path, REGISTRY_PATH), allowed_markers)
    env["OV6_ALLOW_CLOSE_RANDOM_CONTROL_WINDOW"] = "1"
    env["OV6_CLOSURE_RECORD"] = closure_path
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
    assert "experiment registry has staged" in result.stderr


def test_m5_qwen_parity_closure_rejects_dirty_record(tmp_path: Path) -> None:
    closure_path = "research/experiments/2026/2026-05-26-qwen-kr070-random-control-closure.md"
    allowed_markers = (
        (closure_path, "OV6_ALLOW_CLOSE_RANDOM_CONTROL_WINDOW=1"),
        (closure_path, "seed-42"),
        (closure_path, "clean-control window"),
        (REGISTRY_PATH, closure_path),
    )
    env = _preflight_env(tmp_path, (closure_path, REGISTRY_PATH), allowed_markers)
    env["OV6_ALLOW_CLOSE_RANDOM_CONTROL_WINDOW"] = "1"
    env["OV6_CLOSURE_RECORD"] = closure_path
    env["FAKE_GIT_DIRTY_PATH"] = closure_path

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "closure record has staged" in result.stderr
