from __future__ import annotations

import json
from pathlib import Path

from scripts.build_onevision_cpersist_session_accounting import build_payload


def _write_summary(path: Path, payload: dict[str, object]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "summary.json").write_text(json.dumps(payload) + "\n")


def test_onevision_cpersist_accounting_reports_codec_inclusion_modes(tmp_path: Path) -> None:
    dense = tmp_path / "dense"
    sparse = tmp_path / "sparse"
    cpersist = tmp_path / "cpersist.json"
    _write_summary(dense, {"mean_dense_end_to_end_ms": 100.0})
    _write_summary(
        sparse,
        {
            "mean_dense_end_to_end_ms": 70.0,
            "codec_extract_mean_s_per_item": 0.05,
        },
    )
    cpersist.write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "policy": "fixed_k1",
                        "horizon": 50,
                        "followup_only": {
                            "median_total_elapsed_ms": 10.0,
                            "choice_drift": 0,
                            "correctness_drift": 0,
                            "n": 49,
                            "pathological": 0,
                        },
                    }
                ]
            }
        )
        + "\n"
    )

    payload = build_payload(
        dense_dir=dense,
        sparse_dir=sparse,
        cpersist_summary_path=cpersist,
        horizon=50,
    )

    assert payload["sparse_first_query_ms_excluding_codec_extract"] == 70.0
    assert payload["sparse_first_query_ms_including_current_pyav_extract"] == 120.0
    rows = {row["codec_extraction_policy"]: row for row in payload["rows"]}
    excluded_q2 = rows["excluded_model_side"]["session_curve"][1]
    included_q2 = rows["included_current_pyav"]["session_curve"][1]
    assert excluded_q2["speedup_dense_over_combined"] == 2.5
    assert round(included_q2["speedup_dense_over_combined"], 4) == round(200 / 130, 4)
