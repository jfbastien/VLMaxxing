from __future__ import annotations

import os
import subprocess
from pathlib import Path


def test_query_routing_first_branch_script_is_narrow_and_portable() -> None:
    script = Path("scripts/run_rlt_query_routing_first_branch.sh")
    payload = script.read_text(encoding="utf-8")

    assert "/Users/" not in payload
    assert 'cd "$(dirname "$0")/.."' in payload
    assert 'PY="${PYTHON:-./.venv/bin/python}"' in payload
    assert "${GEMMA_MODEL_PATH:-$HOME/models/gemma-4-e4b-it-4bit}" in payload
    assert "--run-cvision-rlt" in payload
    assert "--run-query-routing-q0b" in payload
    assert "--run-query-routing-q1" in payload
    assert "--query-routing-benchmarks" in payload
    assert "--run-composition-direct" not in payload
    assert "--run-max-min-triangulation" not in payload
    assert "Refusing out-of-scope queue override" in payload


def test_query_routing_followup_script_is_narrow_and_portable() -> None:
    script = Path("scripts/run_rlt_query_routing_followup.sh")
    payload = script.read_text(encoding="utf-8")

    assert "/Users/" not in payload
    assert 'cd "$(dirname "$0")/.."' in payload
    assert 'PY="${PYTHON:-./.venv/bin/python}"' in payload
    assert "${GEMMA_MODEL_PATH:-$HOME/models/gemma-4-e4b-it-4bit}" in payload
    assert "--run-cvision-rlt" in payload
    assert "--run-query-routing-q0b" in payload
    assert "--run-query-routing-q1" in payload
    assert "--run-query-routing-q1b-followup" in payload
    assert "--query-routing-benchmarks" in payload
    assert "--run-composition-direct" not in payload
    assert "--run-max-min-triangulation" not in payload
    assert "Refusing out-of-scope queue override" in payload


def test_m5_scale_confirmation_script_requires_operator_model_path() -> None:
    script = Path("scripts/run_rlt_m5_scale_confirmation.sh")
    payload = script.read_text(encoding="utf-8")

    assert "/Users/" not in payload
    assert 'cd "$(dirname "$0")/.."' in payload
    assert 'PY="${PYTHON:-./.venv/bin/python}"' in payload
    assert "${GEMMA_MODEL_PATH:?" in payload
    assert "--gemma-model-path" in payload
    assert "--mlx-memory-limit-gb" in payload
    assert "--rss-guard-mb" in payload
    assert "--run-cvision-rlt" in payload
    assert "--run-cvision-expansion" in payload
    assert "--run-max-min-triangulation" in payload
    assert "--run-magnitude-valid-head-to-head" in payload
    assert "--run-query-routing-q0b" not in payload
    assert "--run-query-routing-q1" not in payload
    assert "Refusing out-of-scope queue override" in payload


def test_query_routing_first_branch_rejects_extra_phase_flags() -> None:
    for forbidden in (
        "--run-composition-direct",
        "--query-routing-benchmarks=tomato",
        "--mvbench-manifest",
        "--composition-prefill-step-size=1",
    ):
        completed = subprocess.run(
            [
                "scripts/run_rlt_query_routing_first_branch.sh",
                forbidden,
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        assert completed.returncode == 2
        assert "Refusing out-of-scope queue override" in completed.stderr


def test_query_routing_followup_rejects_extra_phase_flags() -> None:
    for forbidden in (
        "--run-composition-direct",
        "--query-routing-benchmarks=tomato",
        "--mvbench-manifest",
        "--composition-prefill-step-size=1",
    ):
        completed = subprocess.run(
            [
                "scripts/run_rlt_query_routing_followup.sh",
                forbidden,
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        assert completed.returncode == 2
        assert "Refusing out-of-scope queue override" in completed.stderr


def test_m5_scale_confirmation_rejects_query_routing_phase_flags() -> None:
    env = dict(os.environ)
    env["GEMMA_MODEL_PATH"] = "/private/tmp/fake-gemma-26b-model"
    for forbidden in (
        "--run-query-routing-q0b",
        "--gemma-model-path=/tmp/other-model",
        "--cvision-n-items",
        "--frame-count=32",
    ):
        completed = subprocess.run(
            [
                "scripts/run_rlt_m5_scale_confirmation.sh",
                forbidden,
            ],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

        assert completed.returncode == 2
        assert "Refusing out-of-scope queue override" in completed.stderr
