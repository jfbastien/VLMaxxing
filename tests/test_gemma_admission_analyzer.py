from __future__ import annotations

import scripts.analyze_gemma_admission as analyzer


def _row(
    item_id: str,
    *,
    group: str = "short",
    dense_correct: bool = True,
    pruned_correct: bool = True,
    dense_prompt_tokens: int = 1000,
    pruned_prompt_tokens: int = 500,
    dense_prompt_tps: float = 100.0,
    pruned_prompt_tps: float = 100.0,
    mask_ms: float = 10.0,
    prune_ms: float = 5.0,
) -> dict[str, object]:
    return {
        "kind": "item",
        "item_id": item_id,
        "group": group,
        "dense_correct": dense_correct,
        "pruned_correct": pruned_correct,
        "dense_choice": 0 if dense_correct else 1,
        "pruned_choice": 0 if pruned_correct else 2,
        "dense_parse_failure": False,
        "pruned_parse_failure": False,
        "dense_prompt_tokens": dense_prompt_tokens,
        "pruned_prompt_tokens": pruned_prompt_tokens,
        "dense_prompt_tps": dense_prompt_tps,
        "pruned_prompt_tps": pruned_prompt_tps,
        "dense_timing_ms": {"end_to_end": 1000.0},
        "pruned_timing_ms": {
            "end_to_end": 800.0,
            "mask_compute": mask_ms,
            "placeholder_prune": prune_ms,
        },
    }


def test_gemma_admission_analyzer_continues_when_quality_and_overhead_pass() -> None:
    rows = [_row(f"item-{idx}") for idx in range(3)]

    summary = analyzer.analyze(
        rows,
        quality_delta_floor=-0.05,
        bucket_min_n=20,
        require_overhead_gate=True,
    )

    assert summary["accuracy_delta_pruned_minus_dense"] == 0.0
    assert summary["overhead_gate_pass"] is True
    assert summary["decisions"] == [
        {"decision": "continue", "reason": "gemma_admission_gates_survived"}
    ]


def test_gemma_admission_analyzer_stops_on_aggregate_quality_failure() -> None:
    rows = [
        _row("a", dense_correct=True, pruned_correct=False),
        _row("b", dense_correct=True, pruned_correct=True),
    ]

    summary = analyzer.analyze(
        rows,
        quality_delta_floor=-0.05,
        bucket_min_n=20,
        require_overhead_gate=True,
    )

    assert summary["accuracy_delta_pruned_minus_dense"] == -0.5
    assert summary["decisions"][0]["reason"] == "gemma_admission_quality_gate_failed"
    assert "RLT-3G-A" in summary["skip_phases"]


def test_gemma_admission_analyzer_stops_on_overhead_dominated_arm() -> None:
    rows = [
        _row(
            "a",
            dense_prompt_tokens=1000,
            pruned_prompt_tokens=950,
            mask_ms=400.0,
            prune_ms=200.0,
        )
    ]

    summary = analyzer.analyze(
        rows,
        quality_delta_floor=-0.05,
        bucket_min_n=20,
        require_overhead_gate=True,
    )

    assert summary["overhead_gate_pass"] is False
    assert summary["decisions"][0]["reason"] == "gemma_admission_overhead_dominated"


def test_gemma_admission_analyzer_enforces_bucket_gate_when_powered() -> None:
    rows = [
        _row(f"short-{idx}", group="short", dense_correct=True, pruned_correct=True)
        for idx in range(20)
    ]
    rows.extend(
        _row(f"long-{idx}", group="long", dense_correct=True, pruned_correct=False)
        for idx in range(20)
    )

    summary = analyzer.analyze(
        rows,
        quality_delta_floor=-0.05,
        bucket_min_n=20,
        require_overhead_gate=False,
    )

    assert summary["bucket_quality_gate_pass"] is False
    assert summary["bucket_failures"] == ["long"]
