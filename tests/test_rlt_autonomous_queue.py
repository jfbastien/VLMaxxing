from __future__ import annotations

from pathlib import Path

import pytest

import scripts.run_rlt_autonomous_queue as queue


def test_analysis_contract_without_skip_phase_is_advisory() -> None:
    assert not queue._analysis_blocks_downstream(
        {"decisions": [{"decision": "contract"}], "skip_phases": []}
    )


def test_analysis_blocks_downstream_on_skipped_h3_phase() -> None:
    assert queue._analysis_blocks_downstream(
        {"decisions": [{"decision": "continue"}], "skip_phases": ["RLT-3G-B"]}
    )


def test_analysis_allows_downstream_on_continue() -> None:
    assert not queue._analysis_blocks_downstream(
        {"decisions": [{"decision": "continue"}], "skip_phases": []}
    )


def test_analysis_hard_fails_unknown_decision() -> None:
    with pytest.raises(ValueError, match="unknown analyzer decision"):
        queue._analysis_blocks_downstream(
            {"decisions": [{"decision": "stop_or_contract"}], "skip_phases": []}
        )


def test_analysis_blocks_downstream_on_inconclusive_skip_phase() -> None:
    assert queue._analysis_blocks_downstream(
        {
            "decisions": [{"decision": "inconclusive"}],
            "skip_phases": ["RLT-3G-B"],
        }
    )


def test_gemma_admission_command_uses_resume_and_abba(tmp_path: Path) -> None:
    command = queue._gemma_admission_commands(
        artifact_dir=tmp_path,
        manifest=tmp_path / "manifest.toml",
        model_path=tmp_path / "model",
        frame_count=8,
        n_items=1,
        rss_guard_mb=9000,
        n_warmup=1,
        enforce_overhead_gate=False,
        timing_min_n=20,
        cell_type="h3b_admission",
        label="smoke",
    )[0]

    assert "--resume" in command
    assert command[command.index("--arm-order") + 1] == "abba"
