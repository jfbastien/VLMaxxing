from __future__ import annotations

import scripts.run_rlt_autonomous_queue as queue


def test_analysis_blocks_downstream_on_contract_decision() -> None:
    assert queue._analysis_blocks_downstream(
        {"decisions": [{"decision": "stop_or_contract"}], "skip_phases": []}
    )


def test_analysis_blocks_downstream_on_skipped_h3_phase() -> None:
    assert queue._analysis_blocks_downstream(
        {"decisions": [{"decision": "continue"}], "skip_phases": ["RLT-3G-B"]}
    )


def test_analysis_allows_downstream_on_continue() -> None:
    assert not queue._analysis_blocks_downstream(
        {"decisions": [{"decision": "continue"}], "skip_phases": []}
    )
