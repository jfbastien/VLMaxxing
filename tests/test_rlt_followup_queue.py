from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from pytest import MonkeyPatch

import scripts.run_rlt_followup_queue as queue


def test_prefill_kernel_command_uses_paper_grade_controls(tmp_path: Path) -> None:
    command = queue._prefill_kernel_benchmark_command(
        artifact_dir=tmp_path,
        model_path=tmp_path / "model",
        rss_guard_mb=8123,
    )

    assert "--warm-all-shapes" in command
    assert "--shuffle" in command
    assert command[command.index("--rss-guard-mb") + 1] == "8123"


def test_phase_passed_cvision_requires_parse_gates() -> None:
    base: dict[str, Any] = {
        "pass_complete_pairing": True,
        "pass_fidelity": True,
        "pass_sparse_vision": True,
        "pass_e2e_positive": True,
        "pass_bucket_e2e_positive": True,
        "pass_parse_failure_delta": True,
        "pass_parse_failure_rate": True,
        "pass_ceiling_explained": True,
    }
    assert queue._phase_passed_cvision(base)

    for key in ("pass_parse_failure_delta", "pass_parse_failure_rate"):
        candidate = dict(base)
        candidate[key] = False
        assert not queue._phase_passed_cvision(candidate)


def test_run_command_group_stops_after_first_failure(monkeypatch: MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], *, allow_failure: bool = False) -> dict[str, Any]:
        calls.append(command)
        return {
            "command": command,
            "returncode": 7 if command == ["fail"] else 0,
            "elapsed_seconds": 0.0,
            "stdout_tail": "",
            "stderr_tail": "",
        }

    monkeypatch.setattr(queue, "_run", fake_run)
    results = queue._run_command_group([["ok"], ["fail"], ["stale_analyzer"]])

    assert [result["returncode"] for result in results] == [0, 7]
    assert calls == [["ok"], ["fail"]]


def test_expansion_requires_video_mme_rlt_gate(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_rlt_followup_queue.py",
            "--run-cvision-expansion",
            "--dry-run",
            "--summary",
            str(tmp_path / "summary.json"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "--run-cvision-expansion requires --run-cvision-rlt" in completed.stderr
