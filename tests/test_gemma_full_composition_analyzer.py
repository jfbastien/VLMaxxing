from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _schema(
    *,
    prune_placeholders: str,
    vision_keep_rate: float,
    frame_count: int = 8,
    vision_score_mode: str | None = None,
    group_prune_placeholders: dict[str, str] | None = None,
) -> dict[str, Any]:
    if vision_score_mode is None:
        vision_score_mode = "rlt_topk" if vision_keep_rate < 1.0 else "magnitude"
    return {
        "kind": "schema",
        "schema_version": "phase1_51r_gemma_admission_v4",
        "artifact_payload": {
            "manifest": "manifest.toml",
            "frame_count": frame_count,
            "prefill_step_size": 1024,
            "prune_placeholders": prune_placeholders,
            "group_prune_placeholders": group_prune_placeholders or {},
            "vision_tower_keep_rate": vision_keep_rate,
            "vision_tower_score_mode": vision_score_mode,
        },
    }


def _row(item_id: str, *, group: str, dense_correct: bool, pruned_correct: bool) -> dict[str, Any]:
    return {
        "kind": "item",
        "item_id": item_id,
        "benchmark": "videomme",
        "group": group,
        "answer_index": 1,
        "dense_correct": dense_correct,
        "pruned_correct": pruned_correct,
        "dense_parse_failure": False,
        "pruned_parse_failure": False,
        "dense_choice": 1 if dense_correct else 0,
        "pruned_choice": 1 if pruned_correct else 0,
        "dense_first_generated_top2_margin": 1.5,
        "pruned_first_generated_top2_margin": 0.25,
        "dense_first_generated_selected_margin": 1.4,
        "pruned_first_generated_selected_margin": 0.2,
        "dense_first_generated_confidence_capture_ms": 1.0,
        "pruned_first_generated_confidence_capture_ms": 2.0,
        "dense_first_generated_candidate_top2_margin": 1.1,
        "pruned_first_generated_candidate_top2_margin": 0.15,
        "dense_prompt_tokens": 2200,
        "pruned_prompt_tokens": 1400,
        "dense_timing_ms": {
            "end_to_end": 1000.0,
            "vision": 300.0,
            "multimodal_prefill_ms": 400.0,
        },
        "pruned_timing_ms": {
            "end_to_end": 800.0,
            "vision": 120.0,
            "multimodal_prefill_ms": 250.0,
        },
        "metadata": {
            "prune_placeholders": "rlt",
            "vision_tower_keep_rate": 0.5,
            "vision_tower_score_mode": "rlt_topk",
            "dense_placeholder_count": 2048,
            "pruned_placeholder_count": 1240,
            "placeholder_prune_bypassed": False,
            "gemma_encoder_valid_positions_per_frame": [1024] * 8,
            "gemma_encoder_kept_per_frame": [512] * 8,
        },
    }


def _dense_equiv_row(
    item_id: str, *, group: str, dense_correct: bool, pruned_correct: bool
) -> dict[str, Any]:
    row = _row(item_id, group=group, dense_correct=dense_correct, pruned_correct=pruned_correct)
    row["pruned_prompt_tokens"] = row["dense_prompt_tokens"]
    row["metadata"] = {
        "vision_tower_keep_rate": 1.0,
        "vision_tower_score_mode": "magnitude",
        "dense_placeholder_count": 2048,
        "pruned_placeholder_count": 2048,
        "placeholder_prune_bypassed": True,
    }
    return row


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n")


def test_full_composition_analyzer_pairs_dense_reference_against_composed(tmp_path: Path) -> None:
    dense = tmp_path / "dense.jsonl"
    composed = tmp_path / "composed.jsonl"
    output = tmp_path / "analysis.json"
    paired = tmp_path / "paired.jsonl"
    items = [
        _row(f"item-{idx}", group="short", dense_correct=True, pruned_correct=True)
        for idx in range(5)
    ]
    _write_jsonl(dense, [_schema(prune_placeholders="none", vision_keep_rate=1.0), *items])
    _write_jsonl(composed, [_schema(prune_placeholders="rlt", vision_keep_rate=0.5), *items])

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_full_composition.py",
            "--dense-jsonl",
            str(dense),
            "--composed-jsonl",
            str(composed),
            "--output",
            str(output),
            "--paired-items",
            str(paired),
            "--expected-items",
            "5",
            "--n-bootstrap",
            "50",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    analysis = json.loads(output.read_text())
    assert analysis["decisions"][0]["decision"] == "continue"
    assert analysis["cell_type"] == "rlt_admission_plus_rlt_cvision"
    assert analysis["summary"]["e2e_speedup_dense_over_composed"] == 1.25
    assert analysis["summary"]["pass_bucket_quality_and_e2e"]
    paired_rows = [json.loads(line) for line in paired.read_text().strip().splitlines()]
    assert len(paired_rows) == 5
    assert paired_rows[0]["placeholder_reduction"] > 0.0
    assert paired_rows[0]["vision_reduction"] == 0.5
    assert paired_rows[0]["dense_first_generated_top2_margin"] == 1.5
    assert paired_rows[0]["composed_first_generated_top2_margin"] == 0.25
    assert paired_rows[0]["dense_first_generated_confidence_capture_ms"] == 1.0
    assert paired_rows[0]["composed_first_generated_confidence_capture_ms"] == 2.0
    assert paired_rows[0]["dense_first_generated_candidate_top2_margin"] == 1.1
    assert paired_rows[0]["composed_first_generated_candidate_top2_margin"] == 0.15


def test_full_composition_analyzer_can_use_composed_same_run_dense_timing(
    tmp_path: Path,
) -> None:
    dense = tmp_path / "dense.jsonl"
    composed = tmp_path / "composed.jsonl"
    output = tmp_path / "analysis.json"
    paired = tmp_path / "paired.jsonl"
    dense_items = [
        _row(f"item-{idx}", group="short", dense_correct=True, pruned_correct=True)
        for idx in range(5)
    ]
    composed_items = [
        _row(f"item-{idx}", group="short", dense_correct=True, pruned_correct=True)
        for idx in range(5)
    ]
    for item in dense_items:
        item["dense_timing_ms"]["end_to_end"] = 2000.0
    for item in composed_items:
        item["dense_timing_ms"]["end_to_end"] = 1000.0
        item["pruned_timing_ms"]["end_to_end"] = 500.0
    _write_jsonl(dense, [_schema(prune_placeholders="none", vision_keep_rate=1.0), *dense_items])
    _write_jsonl(
        composed,
        [_schema(prune_placeholders="rlt", vision_keep_rate=0.5), *composed_items],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_full_composition.py",
            "--dense-jsonl",
            str(dense),
            "--composed-jsonl",
            str(composed),
            "--dense-source",
            "composed-jsonl-same-run",
            "--output",
            str(output),
            "--paired-items",
            str(paired),
            "--expected-items",
            "5",
            "--n-bootstrap",
            "50",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    analysis = json.loads(output.read_text())
    assert analysis["dense_source"] == "composed-jsonl-same-run"
    assert analysis["summary"]["e2e_speedup_dense_over_composed"] == 2.0
    paired_rows = [json.loads(line) for line in paired.read_text().strip().splitlines()]
    assert paired_rows[0]["dense_end_to_end_ms"] == 1000.0
    assert paired_rows[0]["dense_metadata_source"] == "schema_override"
    assert paired_rows[0]["dense_metadata"]["metadata_source"] == "dense_reference_schema"
    assert paired_rows[0]["dense_metadata"]["prune_placeholders"] == "none"
    assert paired_rows[0]["composed_metadata"]["prune_placeholders"] == "rlt"


def test_full_composition_analyzer_accepts_scheduled_admission_with_cvision(
    tmp_path: Path,
) -> None:
    dense = tmp_path / "dense.jsonl"
    composed = tmp_path / "composed.jsonl"
    output = tmp_path / "analysis.json"
    paired = tmp_path / "paired.jsonl"
    dense_items = [
        _row(f"item-{idx}", group="short", dense_correct=True, pruned_correct=True)
        for idx in range(5)
    ]
    composed_items = [
        _row(f"item-{idx}", group="short", dense_correct=True, pruned_correct=True)
        for idx in range(5)
    ]
    for idx, item in enumerate(composed_items):
        item["metadata"]["vision_tower_score_mode"] = "random_valid"
        if idx % 2:
            item["metadata"]["pruned_placeholder_count"] = 2048
            item["metadata"]["placeholder_prune_bypassed"] = True
        else:
            item["metadata"]["pruned_placeholder_count"] = 1240
            item["metadata"]["placeholder_prune_bypassed"] = False
    _write_jsonl(dense, [_schema(prune_placeholders="none", vision_keep_rate=1.0), *dense_items])
    _write_jsonl(
        composed,
        [
            _schema(
                prune_placeholders="none",
                vision_keep_rate=0.5,
                vision_score_mode="random_valid",
                group_prune_placeholders={"short": "rlt"},
            ),
            *composed_items,
        ],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_full_composition.py",
            "--dense-jsonl",
            str(dense),
            "--composed-jsonl",
            str(composed),
            "--output",
            str(output),
            "--paired-items",
            str(paired),
            "--expected-items",
            "5",
            "--n-bootstrap",
            "50",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    analysis = json.loads(output.read_text())
    assert analysis["cell_type"] == "scheduled_rlt_admission_plus_random_valid_cvision"
    paired_rows = [json.loads(line) for line in paired.read_text().strip().splitlines()]
    assert {row["placeholder_prune_bypassed"] for row in paired_rows} == {False, True}


def test_full_composition_analyzer_combines_disjoint_sources(tmp_path: Path) -> None:
    dense_dev = tmp_path / "dense_dev.jsonl"
    composed_dev = tmp_path / "composed_dev.jsonl"
    dense_holdout = tmp_path / "dense_holdout.jsonl"
    composed_holdout = tmp_path / "composed_holdout.jsonl"
    output = tmp_path / "analysis.json"
    paired = tmp_path / "paired.jsonl"
    dev_items = [
        _row(f"dev-{idx}", group="short", dense_correct=True, pruned_correct=True)
        for idx in range(5)
    ]
    holdout_items = [
        _row(f"holdout-{idx}", group="short", dense_correct=True, pruned_correct=True)
        for idx in range(5)
    ]
    dense_schema = _schema(prune_placeholders="none", vision_keep_rate=1.0)
    composed_schema = _schema(prune_placeholders="rlt", vision_keep_rate=0.5)
    _write_jsonl(dense_dev, [dense_schema, *dev_items])
    _write_jsonl(composed_dev, [composed_schema, *dev_items])
    _write_jsonl(dense_holdout, [dense_schema, *holdout_items])
    _write_jsonl(composed_holdout, [composed_schema, *holdout_items])

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_full_composition.py",
            "--dense-jsonl",
            str(dense_dev),
            "--dense-jsonl",
            str(dense_holdout),
            "--composed-jsonl",
            str(composed_dev),
            "--composed-jsonl",
            str(composed_holdout),
            "--output",
            str(output),
            "--paired-items",
            str(paired),
            "--expected-items",
            "10",
            "--bucket-min-n",
            "10",
            "--n-bootstrap",
            "50",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    analysis = json.loads(output.read_text())
    assert analysis["summary"]["n_items"] == 10
    assert analysis["source_pairs"] == [
        {
            "dense_jsonl": str(dense_dev),
            "composed_jsonl": str(composed_dev),
            "dense_source": "reference-jsonl",
            "n_items": 5,
        },
        {
            "dense_jsonl": str(dense_holdout),
            "composed_jsonl": str(composed_holdout),
            "dense_source": "reference-jsonl",
            "n_items": 5,
        },
    ]
    assert len(paired.read_text().strip().splitlines()) == 10


def test_full_composition_analyzer_rejects_mixed_combined_policy(
    tmp_path: Path,
) -> None:
    dense_dev = tmp_path / "dense_dev.jsonl"
    composed_dev = tmp_path / "composed_dev.jsonl"
    dense_holdout = tmp_path / "dense_holdout.jsonl"
    composed_holdout = tmp_path / "composed_holdout.jsonl"
    output = tmp_path / "analysis.json"
    paired = tmp_path / "paired.jsonl"
    dev_items = [_row("dev-0", group="short", dense_correct=True, pruned_correct=True)]
    holdout_items = [_row("holdout-0", group="short", dense_correct=True, pruned_correct=True)]
    _write_jsonl(
        dense_dev,
        [_schema(prune_placeholders="none", vision_keep_rate=1.0), *dev_items],
    )
    _write_jsonl(
        composed_dev,
        [_schema(prune_placeholders="rlt", vision_keep_rate=0.5), *dev_items],
    )
    _write_jsonl(
        dense_holdout,
        [
            _schema(prune_placeholders="none", vision_keep_rate=1.0, frame_count=16),
            *holdout_items,
        ],
    )
    _write_jsonl(
        composed_holdout,
        [
            _schema(prune_placeholders="rlt", vision_keep_rate=0.5, frame_count=16),
            *holdout_items,
        ],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_full_composition.py",
            "--dense-jsonl",
            str(dense_dev),
            "--dense-jsonl",
            str(dense_holdout),
            "--composed-jsonl",
            str(composed_dev),
            "--composed-jsonl",
            str(composed_holdout),
            "--output",
            str(output),
            "--paired-items",
            str(paired),
            "--expected-items",
            "2",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "source pairs disagree on policy/config invariants" in completed.stderr


def test_full_composition_analyzer_rejects_sparse_dense_reference(tmp_path: Path) -> None:
    dense = tmp_path / "dense.jsonl"
    composed = tmp_path / "composed.jsonl"
    output = tmp_path / "analysis.json"
    paired = tmp_path / "paired.jsonl"
    item = _row("item-0", group="short", dense_correct=True, pruned_correct=True)
    _write_jsonl(dense, [_schema(prune_placeholders="none", vision_keep_rate=0.5), item])
    _write_jsonl(composed, [_schema(prune_placeholders="rlt", vision_keep_rate=0.5), item])

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_full_composition.py",
            "--dense-jsonl",
            str(dense),
            "--composed-jsonl",
            str(composed),
            "--output",
            str(output),
            "--paired-items",
            str(paired),
            "--expected-items",
            "1",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "dense reference must not use sparse vision" in completed.stderr


def test_full_composition_analyzer_accepts_cvision_only_arm(tmp_path: Path) -> None:
    dense = tmp_path / "dense.jsonl"
    composed = tmp_path / "composed.jsonl"
    output = tmp_path / "analysis.json"
    paired = tmp_path / "paired.jsonl"
    items = [
        _dense_equiv_row(f"item-{idx}", group="short", dense_correct=True, pruned_correct=True)
        for idx in range(5)
    ]
    for item in items:
        item["metadata"]["gemma_encoder_valid_positions_per_frame"] = [1024] * 8
        item["metadata"]["gemma_encoder_kept_per_frame"] = [512] * 8
    composed_schema = _schema(prune_placeholders="none", vision_keep_rate=0.5)
    _write_jsonl(dense, [_schema(prune_placeholders="none", vision_keep_rate=1.0), *items])
    _write_jsonl(composed, [composed_schema, *items])

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_full_composition.py",
            "--dense-jsonl",
            str(dense),
            "--composed-jsonl",
            str(composed),
            "--output",
            str(output),
            "--paired-items",
            str(paired),
            "--expected-items",
            "5",
            "--n-bootstrap",
            "50",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    analysis = json.loads(output.read_text())
    assert analysis["cell_type"] == "rlt_cvision_only"
    paired_rows = [json.loads(line) for line in paired.read_text().strip().splitlines()]
    assert paired_rows[0]["placeholder_prune_bypassed"]
    assert paired_rows[0]["placeholder_reduction"] == 0.0


def test_full_composition_analyzer_accepts_cvision_oracle_at_keep_rate_one(
    tmp_path: Path,
) -> None:
    dense = tmp_path / "dense.jsonl"
    composed = tmp_path / "composed.jsonl"
    output = tmp_path / "analysis.json"
    paired = tmp_path / "paired.jsonl"
    items = [
        _dense_equiv_row(f"item-{idx}", group="short", dense_correct=True, pruned_correct=True)
        for idx in range(5)
    ]
    for item in items:
        item["metadata"]["vision_tower_score_mode"] = "rlt_topk"
        item["metadata"]["gemma_encoder_valid_positions_per_frame"] = [1024] * 8
        item["metadata"]["gemma_encoder_kept_per_frame"] = [1024] * 8
    _write_jsonl(dense, [_schema(prune_placeholders="none", vision_keep_rate=1.0), *items])
    _write_jsonl(
        composed,
        [
            _schema(
                prune_placeholders="none",
                vision_keep_rate=1.0,
                vision_score_mode="rlt_topk",
            ),
            *items,
        ],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_full_composition.py",
            "--dense-jsonl",
            str(dense),
            "--composed-jsonl",
            str(composed),
            "--output",
            str(output),
            "--paired-items",
            str(paired),
            "--expected-items",
            "5",
            "--n-bootstrap",
            "50",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    analysis = json.loads(output.read_text())
    assert analysis["cell_type"] == "rlt_cvision_only"
    paired_rows = [json.loads(line) for line in paired.read_text().strip().splitlines()]
    assert paired_rows[0]["vision_reduction"] == 0.0


def test_full_composition_analyzer_accepts_dense_equivalent_arm(tmp_path: Path) -> None:
    dense = tmp_path / "dense.jsonl"
    composed = tmp_path / "composed.jsonl"
    output = tmp_path / "analysis.json"
    paired = tmp_path / "paired.jsonl"
    items = [
        _dense_equiv_row(f"item-{idx}", group="short", dense_correct=True, pruned_correct=True)
        for idx in range(5)
    ]
    _write_jsonl(dense, [_schema(prune_placeholders="none", vision_keep_rate=1.0), *items])
    _write_jsonl(composed, [_schema(prune_placeholders="none", vision_keep_rate=1.0), *items])

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_full_composition.py",
            "--dense-jsonl",
            str(dense),
            "--composed-jsonl",
            str(composed),
            "--output",
            str(output),
            "--paired-items",
            str(paired),
            "--expected-items",
            "5",
            "--n-bootstrap",
            "50",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    analysis = json.loads(output.read_text())
    assert analysis["cell_type"] == "dense_equivalent"
    assert analysis["summary"]["pass_dense_equivalence"]
