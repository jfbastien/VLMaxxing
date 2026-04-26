from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_lowfps_analyzer_pairs_sessions_and_reports_outcome(tmp_path: Path) -> None:
    reference = tmp_path / "reference.jsonl"
    candidate = tmp_path / "candidate.jsonl"
    output = tmp_path / "summary.json"
    pairs = tmp_path / "pairs.jsonl"

    reference_rows = []
    candidate_rows = []
    for q_index, ref_correct, cand_correct in [
        (0, True, True),
        (1, True, False),
        (2, False, False),
    ]:
        reference_rows.append(
            {
                "seed_item_id": "videomme:short:001-1",
                "item_id": f"videomme:short:001-{q_index + 1}",
                "duration": "short",
                "q_index": q_index,
                "frame_count": 8,
                "choice": "A" if ref_correct else "B",
                "correct": ref_correct,
                "parse_failure": False,
                "degenerate": False,
                "end_to_end_ms": 1000.0,
                "prompt_tokens": 1000,
            }
        )
        candidate_rows.append(
            {
                "seed_item_id": "videomme:short:001-1",
                "item_id": f"videomme:short:001-{q_index + 1}",
                "duration": "short",
                "q_index": q_index,
                "frame_count": 4,
                "choice": "A" if cand_correct else "C",
                "correct": cand_correct,
                "parse_failure": False,
                "degenerate": False,
                "end_to_end_ms": 500.0,
                "prompt_tokens": 700,
            }
        )

    _write_jsonl(reference, reference_rows)
    _write_jsonl(candidate, candidate_rows)

    subprocess.run(
        [
            sys.executable,
            "scripts/analyze_phase1_62_lowfps_dense.py",
            "--reference-jsonl",
            str(reference),
            "--candidate-jsonl",
            str(candidate),
            "--output",
            str(output),
            "--paired-queries",
            str(pairs),
        ],
        check=True,
    )

    summary = json.loads(output.read_text())
    assert summary["reference_frame_count"] == 8
    assert summary["candidate_frame_count"] == 4
    assert summary["n_paired_queries"] == 3
    assert summary["n_paired_sessions"] == 1
    assert summary["pass_format"] is True
    assert summary["all"]["reference_accuracy"] == 2 / 3
    assert summary["all"]["candidate_accuracy"] == 1 / 3
    assert summary["all"]["accuracy_delta_candidate_minus_reference"] == -1 / 3
    assert summary["all"]["speedup_reference_over_candidate"] == 2.0
    assert summary["first_queries"]["accuracy_delta_candidate_minus_reference"] == 0.0
    assert summary["follow_ups"]["accuracy_delta_candidate_minus_reference"] == -0.5
    assert summary["outcome"] == "low_fps_rejected"
    assert len(pairs.read_text().strip().splitlines()) == 3


def test_lowfps_analyzer_requires_clean_format_for_outcome(tmp_path: Path) -> None:
    reference = tmp_path / "reference.jsonl"
    candidate = tmp_path / "candidate.jsonl"
    output = tmp_path / "summary.json"

    base_row = {
        "seed_item_id": "videomme:short:001-1",
        "item_id": "videomme:short:001-1",
        "duration": "short",
        "q_index": 0,
        "frame_count": 8,
        "choice": "A",
        "correct": True,
        "parse_failure": False,
        "degenerate": False,
        "end_to_end_ms": 1000.0,
        "prompt_tokens": 1000,
    }
    candidate_row = dict(base_row)
    candidate_row.update(
        {
            "frame_count": 4,
            "parse_failure": True,
            "end_to_end_ms": 500.0,
        }
    )
    _write_jsonl(reference, [base_row])
    _write_jsonl(candidate, [candidate_row])

    subprocess.run(
        [
            sys.executable,
            "scripts/analyze_phase1_62_lowfps_dense.py",
            "--reference-jsonl",
            str(reference),
            "--candidate-jsonl",
            str(candidate),
            "--output",
            str(output),
        ],
        check=True,
    )

    summary = json.loads(output.read_text())
    assert summary["pass_format"] is False
    assert summary["outcome"] == "format_invalid"
