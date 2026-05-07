from __future__ import annotations

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
