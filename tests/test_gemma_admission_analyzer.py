from __future__ import annotations

from typing import Any

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
    dense_vision_ms: float = 100.0,
    pruned_vision_ms: float = 50.0,
    mask_ms: float = 10.0,
    prune_ms: float = 5.0,
) -> dict[str, Any]:
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
        "dense_timing_ms": {"end_to_end": 1000.0, "vision": dense_vision_ms},
        "pruned_timing_ms": {
            "end_to_end": 800.0,
            "vision": pruned_vision_ms,
            "mask_compute": mask_ms,
            "placeholder_prune": prune_ms,
        },
    }


def _analyze(
    rows: list[dict[str, Any]],
    *,
    require_overhead_gate: bool = True,
    timing_min_n: int = 1,
    cell_type: analyzer.CellType = "h2_admission",
) -> dict[str, Any]:
    return analyzer.analyze(
        rows,
        quality_delta_floor=-0.05,
        bucket_min_n=20,
        require_overhead_gate=require_overhead_gate,
        timing_min_n=timing_min_n,
        n_bootstrap=0,
        cell_type=cell_type,
    )


def test_gemma_admission_analyzer_continues_when_quality_and_overhead_pass() -> None:
    rows = [_row(f"item-{idx}") for idx in range(3)]

    summary = _analyze(rows)

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

    summary = _analyze(rows)

    assert summary["accuracy_delta_pruned_minus_dense"] == -0.5
    assert summary["decisions"][0]["reason"] == "gemma_admission_quality_gate_failed"
    assert "RLT-3G-A" in summary["skip_phases"]


def test_gemma_admission_analyzer_stops_on_overhead_dominated_arm() -> None:
    rows = [
        _row(
            f"item-{idx}",
            dense_prompt_tokens=1000,
            pruned_prompt_tokens=950,
            mask_ms=400.0,
            prune_ms=200.0,
        )
        for idx in range(20)
    ]

    summary = _analyze(rows, timing_min_n=20)

    assert summary["overhead_gate_pass"] is False
    assert summary["overhead_gate_evaluated"] is True
    assert summary["decisions"][0]["decision"] == "contract"
    assert summary["decisions"][0]["reason"] == "gemma_admission_overhead_dominated"


def test_gemma_admission_analyzer_does_not_gate_overhead_below_timing_min_n() -> None:
    rows = [
        _row(
            "a",
            dense_prompt_tokens=1000,
            pruned_prompt_tokens=950,
            mask_ms=400.0,
            prune_ms=200.0,
        )
    ]

    summary = _analyze(rows, timing_min_n=20)

    assert summary["overhead_gate_evaluated"] is False
    assert summary["overhead_gate_pass"] is None
    assert summary["decisions"] == [
        {"decision": "continue", "reason": "gemma_admission_gates_survived"}
    ]


def test_gemma_admission_analyzer_smoke_can_disable_overhead_gate() -> None:
    rows = [
        _row(
            "a",
            dense_prompt_tokens=1000,
            pruned_prompt_tokens=950,
            mask_ms=400.0,
            prune_ms=200.0,
        )
    ]

    summary = _analyze(rows, require_overhead_gate=False)

    assert summary["overhead_gate_evaluated"] is False
    assert summary["overhead_gate_pass"] is None
    assert summary["decisions"] == [
        {"decision": "continue", "reason": "gemma_admission_gates_survived"}
    ]


def test_gemma_admission_analyzer_prefers_direct_multimodal_prefill_field() -> None:
    row = _row("a")
    row["dense_timing_ms"] = {
        "end_to_end": 1000.0,
        "vision": 100.0,
        "multimodal_prefill_ms": 300.0,
    }
    row["pruned_timing_ms"] = {
        "end_to_end": 800.0,
        "vision": 50.0,
        "multimodal_prefill_ms": 200.0,
        "mask_compute": 10.0,
        "placeholder_prune": 5.0,
    }

    summary = _analyze([row])

    assert summary["total_prefill_reduction_ms"] == 100.0
    assert summary["overhead_gate_pass"] is True


def test_gemma_admission_analyzer_pure_cvision_does_not_credit_prefill_noise() -> None:
    rows = [
        _row(
            f"item-{idx}",
            dense_prompt_tokens=1000,
            pruned_prompt_tokens=500,
            dense_vision_ms=100.0,
            pruned_vision_ms=100.0,
            mask_ms=2.0,
            prune_ms=1.0,
        )
        for idx in range(20)
    ]

    summary = _analyze(rows, timing_min_n=20, cell_type="h2_pure_cvision")

    assert summary["total_prefill_reduction_ms"] > 0.0
    assert summary["total_credited_stage_reduction_ms"] == 0.0
    assert summary["overhead_gate_pass"] is False
    assert summary["decisions"][0]["reason"] == "gemma_admission_overhead_dominated"


def test_gemma_admission_analyzer_reports_pruned_warmup_ratio() -> None:
    row = _row("a")
    row["metadata"] = {
        "pruned_warmup_generate_ms": [240.0],
        "pruned_warmup_multimodal_prefill_ms": [180.0],
    }
    row["pruned_timing_ms"]["generate"] = 120.0
    row["pruned_timing_ms"]["multimodal_prefill_ms"] = 90.0

    summary = _analyze([row], require_overhead_gate=False)

    assert summary["prefill_jit_warmup_ratio"] == 2.0
    assert summary["prefill_jit_warmup_suspected"] is True
    assert summary["pruned_generate_warmup_ratio_proxy"] == 2.0
    assert summary["pruned_generate_warmup_suspected"] is True


def test_gemma_admission_analyzer_enforces_bucket_gate_when_powered() -> None:
    rows = [
        _row(f"short-{idx}", group="short", dense_correct=True, pruned_correct=True)
        for idx in range(20)
    ]
    rows.extend(
        _row(f"long-{idx}", group="long", dense_correct=True, pruned_correct=False)
        for idx in range(20)
    )

    summary = _analyze(rows, require_overhead_gate=False)

    assert summary["bucket_quality_gate_pass"] is False
    assert summary["bucket_failures"] == ["long"]
