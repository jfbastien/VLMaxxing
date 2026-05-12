from __future__ import annotations

import json
from pathlib import Path

from scripts.analyze_ov6_qwen_random_multiseed import analyze as analyze_random_multiseed
from scripts.analyze_ov6_track_b import build_payload


def _write_arm(
    path: Path,
    *,
    rows: list[tuple[str, bool, int]],
    vision_ms: float = 10.0,
    e2e_ms: float = 100.0,
    codec_extract_s: float | None = None,
) -> None:
    path.mkdir(parents=True)
    with (path / "results.jsonl").open("w") as handle:
        for item_id, correct, choice_index in rows:
            handle.write(
                json.dumps(
                    {
                        "item_id": item_id,
                        "correct": correct,
                        "parse_failure": False,
                        "choice_index": choice_index,
                    }
                )
                + "\n"
            )
    (path / "summary.json").write_text(
        json.dumps(
            {
                "mean_dense_vision_ms": vision_ms,
                "mean_dense_end_to_end_ms": e2e_ms,
                "mean_effective_keep_rate": 0.5,
                "codec_extract_mean_s_per_item": codec_extract_s,
            }
        )
        + "\n"
    )


def _populate_minimal_ov6_tree(root: Path) -> None:
    n57 = root / "phase1_51V_ov6_n57"
    kr070 = root / "phase1_51V_ov6_n57_kr070_l2"
    l8 = root / "phase1_51V_ov6_n57_kr050_l8"
    dense_rows = [("a", True, 0), ("b", False, 1), ("c", True, 2)]
    magnitude_rows = [("a", True, 0), ("b", False, 1), ("c", False, 3)]
    random_rows = [("a", False, 1), ("b", True, 0), ("c", False, 3)]
    codec_rows = [("a", True, 0), ("b", True, 0), ("c", False, 3)]

    for base in (n57,):
        _write_arm(base / "dense", rows=dense_rows)
        _write_arm(base / "magnitude_norm_kr050", rows=magnitude_rows)
        _write_arm(base / "uniform_random_kr050", rows=random_rows)
        _write_arm(base / "codec_novel_coded_kr050", rows=codec_rows, codec_extract_s=2.0)
        _write_arm(base / "codec_motion_kr050", rows=codec_rows, codec_extract_s=2.0)
        _write_arm(base / "codec_residual_kr050", rows=codec_rows, codec_extract_s=2.0)

    for base in (kr070, l8):
        _write_arm(base / "magnitude_norm", rows=magnitude_rows)
        _write_arm(base / "codec_novel_coded", rows=codec_rows, codec_extract_s=2.0)
        _write_arm(base / "codec_motion", rows=codec_rows, codec_extract_s=2.0)
        _write_arm(base / "codec_residual", rows=codec_rows, codec_extract_s=2.0)


def test_ov6_track_b_audit_computes_paired_mcnemar_and_net_e2e(tmp_path: Path) -> None:
    _populate_minimal_ov6_tree(tmp_path)
    payload = build_payload(tmp_path)
    cell = next(c for c in payload["cells"] if c["label"] == "kr0.7_layer2_n57")

    codec = cell["arms"]["codec_novel_coded"]
    assert codec["accuracy"]["successes"] == 2
    assert codec["accuracy"]["n"] == 3
    assert codec["mean_e2e_ms_excluding_codec_extract"] == 100.0
    assert codec["mean_e2e_ms_including_codec_extract"] == 2100.0

    paired = cell["paired_comparisons"]["codec_novel_coded_vs_magnitude_norm"]
    assert paired["a_correct_b_wrong"] == 1
    assert paired["a_wrong_b_correct"] == 0
    assert paired["mcnemar_exact_p_two_sided"] == 1.0


def test_ov6_random_multiseed_flags_unstable_random_baseline(tmp_path: Path) -> None:
    rows_mag = [
        ("a", True, 0),
        ("b", True, 1),
        ("c", True, 2),
        ("d", False, 3),
    ]
    rows_seed1 = [
        ("a", True, 0),
        ("b", True, 1),
        ("c", False, 0),
        ("d", True, 3),
    ]
    rows_seed7 = [
        ("a", False, 1),
        ("b", False, 2),
        ("c", False, 3),
        ("d", False, 0),
    ]
    _write_arm(tmp_path / "magnitude_norm", rows=rows_mag)
    _write_arm(tmp_path / "uniform_random_seed1", rows=rows_seed1)
    _write_arm(tmp_path / "uniform_random_seed7", rows=rows_seed7)

    payload = analyze_random_multiseed(tmp_path)

    assert payload["magnitude_norm"]["accuracy"]["correct"] == 3
    assert payload["gate_status"]["seeds_random_ge_magnitude"] == 1
    assert payload["gate_status"]["n_seeds"] == 2
    assert payload["gate_status"]["passes_point_estimate_gate"] is False
    assert payload["gate_status"]["falsifying_seeds"] == ["uniform_random_seed7"]
