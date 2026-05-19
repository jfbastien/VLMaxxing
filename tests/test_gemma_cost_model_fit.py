from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _cost_payload(
    *,
    observed: float,
    prefill_ceiling: float,
    prefill_vision_ceiling: float,
    prefill_share: float = 0.5,
) -> dict[str, object]:
    return {
        "schema": "gemma_paired_cost_model_v1",
        "summary": {
            "n": 30,
            "e2e_speedup_dense_over_composed": observed,
            "prefill_only_e2e_ceiling_speedup": prefill_ceiling,
            "prefill_plus_vision_e2e_ceiling_speedup": prefill_vision_ceiling,
            "dense_prefill_share_of_e2e": prefill_share,
            "dense_vision_share_of_e2e": 0.3,
            "dense_other_share_of_e2e": 0.2,
            "prefill_speedup_dense_over_composed": 1.5,
            "vision_speedup_dense_over_composed": 1.0,
            "accuracy_delta_composed_minus_dense": -0.1,
            "harmed_count": 3,
        },
    }


def test_cost_model_fit_reports_errors_and_ols(tmp_path: Path) -> None:
    one = tmp_path / "one.json"
    two = tmp_path / "two.json"
    output = tmp_path / "fit.json"
    one.write_text(
        json.dumps(_cost_payload(observed=1.2, prefill_ceiling=1.2, prefill_vision_ceiling=1.2)),
        encoding="utf-8",
    )
    two.write_text(
        json.dumps(_cost_payload(observed=1.5, prefill_ceiling=1.3, prefill_vision_ceiling=1.5)),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/fit_gemma_cost_model.py",
            "--cost-model-json",
            f"one={one}",
            "--cost-model-json",
            f"two={two}",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema"] == "gemma_stage_cost_model_fit_v1"
    assert payload["n_artifacts"] == 2
    assert payload["models"]["observed_e2e_vs_prefill_plus_vision_ceiling"]["r2"] == 1.0
    assert (
        payload["error_summaries"]["prefill_plus_vision_ceiling"]["max_abs_relative_error"] == 0.0
    )


def test_cost_model_fit_rejects_duplicate_labels(tmp_path: Path) -> None:
    one = tmp_path / "one.json"
    two = tmp_path / "two.json"
    output = tmp_path / "fit.json"
    one.write_text(
        json.dumps(_cost_payload(observed=1.2, prefill_ceiling=1.2, prefill_vision_ceiling=1.2)),
        encoding="utf-8",
    )
    two.write_text(
        json.dumps(_cost_payload(observed=1.5, prefill_ceiling=1.3, prefill_vision_ceiling=1.5)),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/fit_gemma_cost_model.py",
            "--cost-model-json",
            f"same={one}",
            "--cost-model-json",
            f"same={two}",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "duplicate labels" in completed.stderr


def test_cost_model_fit_rejects_bad_schema(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    good = tmp_path / "good.json"
    output = tmp_path / "fit.json"
    bad.write_text(json.dumps({"schema": "wrong", "summary": {}}), encoding="utf-8")
    good.write_text(
        json.dumps(_cost_payload(observed=1.5, prefill_ceiling=1.3, prefill_vision_ceiling=1.5)),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/fit_gemma_cost_model.py",
            "--cost-model-json",
            f"bad={bad}",
            "--cost-model-json",
            f"good={good}",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "expected gemma_paired_cost_model_v1" in completed.stderr
