from __future__ import annotations

import json
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


def test_query_routing_admission_scheduler_script_is_narrow_and_portable() -> None:
    script = Path("scripts/run_rlt_query_routing_admission_scheduler.sh")
    payload = script.read_text(encoding="utf-8")

    assert "/Users/" not in payload
    assert 'cd "$(dirname "$0")/.."' in payload
    assert 'PY="${PYTHON:-./.venv/bin/python}"' in payload
    assert "${GEMMA_MODEL_PATH:-$HOME/models/gemma-4-e4b-it-4bit}" in payload
    assert "--run-cvision-rlt" in payload
    assert "--run-query-routing-q0b" in payload
    assert "--run-query-routing-q1" in payload
    assert "--run-query-routing-q1b-followup" in payload
    assert "--run-query-routing-q1c-admission-scheduler" in payload
    assert "--query-routing-benchmarks" in payload
    assert "--run-composition-direct" not in payload
    assert "--run-max-min-triangulation" not in payload
    assert "Refusing out-of-scope queue override" in payload


def test_query_routing_hosted_sweep_script_is_narrow_and_portable() -> None:
    script = Path("scripts/run_rlt_query_routing_hosted_sweep.sh")
    payload = script.read_text(encoding="utf-8")

    assert "/Users/" not in payload
    assert 'cd "$(dirname "$0")/.."' in payload
    assert 'PY="${PYTHON:-./.venv/bin/python}"' in payload
    assert "${GEMMA_MODEL_PATH:-$HOME/models/gemma-4-e4b-it-4bit}" in payload
    assert "${MVBENCH_MANIFEST:-research/benchmark_manifests/mvbench_hosted_dev_v1.toml}" in (
        payload
    )
    assert "--run-cvision-rlt" in payload
    assert "--run-query-routing-q0b" in payload
    assert "--run-query-routing-q1" in payload
    assert "--run-query-routing-q1b-followup" not in payload
    assert "--run-query-routing-q1c-admission-scheduler" not in payload
    assert "--query-routing-benchmarks mvbench" in payload
    assert "--run-composition-direct" not in payload
    assert "--run-max-min-triangulation" not in payload
    assert "Refusing out-of-scope queue override" in payload


def test_query_routing_active_repair_probe_script_is_narrow_and_portable() -> None:
    script = Path("scripts/run_rlt_query_routing_active_repair_probe.sh")
    payload = script.read_text(encoding="utf-8")

    assert "/Users/" not in payload
    assert 'cd "$(dirname "$0")/.."' in payload
    assert 'PY="${PYTHON:-./.venv/bin/python}"' in payload
    assert "${GEMMA_MODEL_PATH:-$HOME/models/gemma-4-e4b-it-4bit}" in payload
    assert "--run-cvision-rlt" in payload
    assert "--run-query-routing-q0b" in payload
    assert "--run-query-routing-q1" in payload
    assert "--run-query-routing-q1b-followup" in payload
    assert "--run-query-routing-q1c-admission-scheduler" not in payload
    assert "--query-routing-benchmarks" in payload
    assert "analyze_gemma_active_repair_confidence.py" in payload
    assert "query_q1b_mvbench_random_seed11_admission_on_active_repair_confidence.json" in payload
    assert "query_q1b_mvbench_fixed_uniform_admission_on_active_repair_confidence.json" in payload
    assert "query_q1b_mvbench_admission_on_pooled_active_repair_confidence.json" in payload
    assert 'MARGIN_FIELD="${MARGIN_FIELD:-composed_first_generated_top2_margin}"' in payload
    assert "composed_first_generated_candidate_top2_margin" in payload
    assert 'MIN_SPEEDUP="${MIN_SPEEDUP:-1.254}"' in payload
    assert 'MAX_RETRY_RATE="${MAX_RETRY_RATE:-0.50}"' in payload
    assert 'MIN_AUC_LOWER_CI="${MIN_AUC_LOWER_CI:-0.65}"' in payload
    assert 'MIN_AUC_CLASS_COUNT="${MIN_AUC_CLASS_COUNT:-3}"' in payload
    assert 'BASELINE_REPAIR_PAIRED="${BASELINE_REPAIR_PAIRED:-}"' in payload
    assert "run_repair_analyzer" in payload
    assert "Expected paired artifact missing after queue run" in payload
    assert "Refusing out-of-scope queue override" in payload


def test_query_routing_active_repair_targeted_script_is_narrow_and_portable() -> None:
    script = Path("scripts/run_rlt_query_routing_active_repair_targeted.sh")
    payload = script.read_text(encoding="utf-8")

    assert "/Users/" not in payload
    assert 'cd "$(dirname "$0")/.."' in payload
    assert 'PY="${PYTHON:-./.venv/bin/python}"' in payload
    assert "${GEMMA_MODEL_PATH:-$HOME/models/gemma-4-e4b-it-4bit}" in payload
    assert "${MVBENCH_MANIFEST:-research/benchmark_manifests/mvbench_motion_dev_v2.toml}" in (
        payload
    )
    assert 'N_ITEMS="${N_ITEMS:-0}"' in payload
    assert "EXPECTED_ITEMS=30" in payload
    assert "BUCKET_MIN_N=1" in payload
    assert "N_BOOTSTRAP=50" in payload
    assert "rlt_query_routing_active_repair_targeted_smoke" in payload
    assert "base_args+=(--n-items" in payload
    assert 'if [[ "$DRY_RUN" != "1" ]]' in payload
    assert "--run-cvision-rlt" not in payload
    assert "--run-query-routing-q0b" not in payload
    assert "--run-query-routing-q1" not in payload
    assert "--run-query-routing-q1b-followup" not in payload
    assert "--vision-tower-score-mode random_valid" in payload
    assert "--vision-random-seed 11" in payload
    assert "--vision-tower-score-mode fixed_uniform" in payload
    assert "query_q1b_dense_mvbench_dense.jsonl" in payload
    assert "query_q1b_mvbench_random_seed11_admission_on_active_repair_confidence.json" in payload
    assert "query_q1b_mvbench_fixed_uniform_admission_on_active_repair_confidence.json" in payload
    assert "query_q1b_mvbench_admission_on_pooled_active_repair_confidence.json" in payload
    assert "query_q1_mvbench_random_seed11_no_admission_paired.jsonl" in payload
    assert 'MARGIN_FIELD="${MARGIN_FIELD:-composed_first_generated_top2_margin}"' in payload
    assert "composed_first_generated_candidate_top2_margin" in payload
    assert 'MIN_SPEEDUP="${MIN_SPEEDUP:-1.0}"' in payload
    assert 'MAX_RETRY_RATE="${MAX_RETRY_RATE:-0.50}"' in payload
    assert 'MIN_AUC_LOWER_CI="${MIN_AUC_LOWER_CI:-0.65}"' in payload
    assert 'MIN_AUC_CLASS_COUNT="${MIN_AUC_CLASS_COUNT:-3}"' in payload
    assert 'BASELINE_REPAIR_PAIRED="${BASELINE_REPAIR_PAIRED:-}"' in payload
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


def test_m3_cost_accounting_followup_script_is_narrow_and_portable() -> None:
    script = Path("scripts/run_rlt_m3_cost_accounting_followup.sh")
    payload = script.read_text(encoding="utf-8")

    assert "/Users/" not in payload
    assert 'cd "$(dirname "$0")/.."' in payload
    assert 'PY="${PYTHON:-./.venv/bin/python}"' in payload
    assert "${GEMMA_MODEL_PATH:-$HOME/models/gemma-4-e4b-it-4bit}" in payload
    assert 'MLX_MEMORY_LIMIT_GB="${MLX_MEMORY_LIMIT_GB:-12}"' in payload
    assert 'RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"' in payload
    assert 'N_ITEMS="${N_ITEMS:-0}"' in payload
    assert 'M3_FOLLOWUP_TIER="${M3_FOLLOWUP_TIER:-core}"' in payload
    assert "run_rlt_m3_cost_accounting_followup.py" in payload
    assert "--tier" in payload
    assert "--run-query-routing-q0b" not in payload
    assert "--run-query-routing-q1" not in payload
    assert "--run-query-routing-q1b-followup" not in payload
    assert "--run-query-routing-q1c-admission-scheduler" not in payload
    assert "--run-composition-direct" not in payload
    assert "--run-composition-rescue" not in payload
    assert "--run-cvision-expansion" not in payload
    assert "--run-max-min-triangulation" not in payload
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


def test_query_routing_admission_scheduler_rejects_extra_phase_flags() -> None:
    for forbidden in (
        "--run-composition-direct",
        "--query-routing-benchmarks=tomato",
        "--mvbench-manifest",
        "--composition-prefill-step-size=1",
    ):
        completed = subprocess.run(
            [
                "scripts/run_rlt_query_routing_admission_scheduler.sh",
                forbidden,
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        assert completed.returncode == 2
        assert "Refusing out-of-scope queue override" in completed.stderr


def test_query_routing_hosted_sweep_rejects_extra_phase_flags() -> None:
    for forbidden in (
        "--run-composition-direct",
        "--query-routing-benchmarks=tomato",
        "--mvbench-manifest",
        "--composition-prefill-step-size=1",
    ):
        completed = subprocess.run(
            [
                "scripts/run_rlt_query_routing_hosted_sweep.sh",
                forbidden,
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        assert completed.returncode == 2
        assert "Refusing out-of-scope queue override" in completed.stderr


def test_query_routing_active_repair_probe_rejects_extra_phase_flags() -> None:
    for forbidden in (
        "--run-composition-direct",
        "--query-routing-benchmarks=tomato",
        "--mvbench-manifest",
        "--composition-prefill-step-size=1",
    ):
        completed = subprocess.run(
            [
                "scripts/run_rlt_query_routing_active_repair_probe.sh",
                forbidden,
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        assert completed.returncode == 2
        assert "Refusing out-of-scope queue override" in completed.stderr


def test_query_routing_active_repair_probe_rejects_dense_margin_override() -> None:
    env = dict(os.environ)
    env["MARGIN_FIELD"] = "dense_first_generated_candidate_top2_margin"
    completed = subprocess.run(
        [
            "scripts/run_rlt_query_routing_active_repair_probe.sh",
            "--dry-run",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode == 2
    assert "Refusing margin field outside composed" in completed.stderr


def test_query_routing_active_repair_probe_accepts_candidate_margin_override(
    tmp_path: Path,
) -> None:
    env = dict(os.environ)
    env["MARGIN_FIELD"] = "composed_first_generated_candidate_top2_margin"
    env["ARTIFACT_DIR"] = str(tmp_path / "probe")
    completed = subprocess.run(
        [
            "scripts/run_rlt_query_routing_active_repair_probe.sh",
            "--dry-run",
            "--max-planned-hours",
            "999",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--margin-field composed_first_generated_candidate_top2_margin" in completed.stdout


def test_query_routing_active_repair_targeted_rejects_extra_phase_flags() -> None:
    for forbidden in (
        "--run-cvision-rlt",
        "--run-query-routing-q0b",
        "--mvbench-manifest",
        "--composition-prefill-step-size=1",
    ):
        completed = subprocess.run(
            [
                "scripts/run_rlt_query_routing_active_repair_targeted.sh",
                forbidden,
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        assert completed.returncode == 2
        assert "Refusing out-of-scope queue override" in completed.stderr


def test_query_routing_active_repair_targeted_rejects_dense_margin_override() -> None:
    env = dict(os.environ)
    env["MARGIN_FIELD"] = "dense_first_generated_candidate_top2_margin"
    completed = subprocess.run(
        [
            "scripts/run_rlt_query_routing_active_repair_targeted.sh",
            "--dry-run",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode == 2
    assert "Refusing margin field outside composed" in completed.stderr


def test_query_routing_active_repair_targeted_accepts_candidate_margin_override() -> None:
    env = dict(os.environ)
    env["MARGIN_FIELD"] = "composed_first_generated_candidate_top2_margin"
    env["N_ITEMS"] = "1"
    completed = subprocess.run(
        [
            "scripts/run_rlt_query_routing_active_repair_targeted.sh",
            "--dry-run",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--margin-field composed_first_generated_candidate_top2_margin" in completed.stdout


def test_query_routing_active_repair_targeted_rejects_bad_n_items() -> None:
    env = dict(os.environ)
    env["N_ITEMS"] = "not-an-int"
    completed = subprocess.run(
        [
            "scripts/run_rlt_query_routing_active_repair_targeted.sh",
            "--dry-run",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode == 2
    assert "Refusing non-integer N_ITEMS" in completed.stderr


def test_query_routing_active_repair_targeted_smoke_knobs_rewrite_expected_items() -> None:
    env = dict(os.environ)
    env["N_ITEMS"] = "1"
    completed = subprocess.run(
        [
            "scripts/run_rlt_query_routing_active_repair_targeted.sh",
            "--dry-run",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode == 0
    assert "--n-items 1" in completed.stdout
    assert "--expected-items 1" in completed.stdout
    assert "--bucket-min-n 1" in completed.stdout
    assert "--n-bootstrap 50" in completed.stdout
    assert "--n-bootstrap 100" in completed.stdout
    assert "--min-speedup 1.0" in completed.stdout
    assert "--max-retry-rate 0.50" in completed.stdout
    assert "--min-auc-lower-ci 0.65" in completed.stdout
    assert "--min-auc-class-count 3" in completed.stdout
    assert "--baseline-paired-items" in completed.stdout
    assert "query_q1_mvbench_random_seed11_no_admission_paired.jsonl" in completed.stdout
    assert "--keep-rate 1.0 --prune-placeholders none" in completed.stdout
    assert "--vision-tower-keep-rate 0.5 --vision-tower-score-mode random_valid" in (
        completed.stdout
    )
    assert "rlt_query_routing_active_repair_targeted_smoke" in completed.stdout


def test_query_routing_active_repair_targeted_dry_run_does_not_make_artifact_dir(
    tmp_path: Path,
) -> None:
    artifact_dir = tmp_path / "targeted"
    env = dict(os.environ)
    env["ARTIFACT_DIR"] = str(artifact_dir)
    completed = subprocess.run(
        [
            "scripts/run_rlt_query_routing_active_repair_targeted.sh",
            "--dry-run",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode == 0
    assert not artifact_dir.exists()


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


def test_m3_cost_accounting_followup_rejects_extra_phase_flags() -> None:
    for forbidden in (
        "--run-query-routing-q0b",
        "--run-composition-direct",
        "--run-cvision-expansion",
        "--gemma-model-path=/tmp/other-model",
        "--frame-count=32",
    ):
        completed = subprocess.run(
            [
                "scripts/run_rlt_m3_cost_accounting_followup.sh",
                forbidden,
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        assert completed.returncode == 2
        assert "Refusing out-of-scope queue override" in completed.stderr


def test_m3_cost_accounting_followup_rejects_bad_tier() -> None:
    env = dict(os.environ)
    env["M3_FOLLOWUP_TIER"] = "query-aware"
    completed = subprocess.run(
        [
            "scripts/run_rlt_m3_cost_accounting_followup.sh",
            "--dry-run",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode == 2
    assert "Refusing unknown M3_FOLLOWUP_TIER" in completed.stderr


def test_m3_cost_accounting_followup_dry_run_is_core_and_nonmutating(
    tmp_path: Path,
) -> None:
    artifact_dir = tmp_path / "m3_followup"
    env = dict(os.environ)
    env["ARTIFACT_DIR"] = str(artifact_dir)
    env["N_ITEMS"] = "1"
    completed = subprocess.run(
        [
            "scripts/run_rlt_m3_cost_accounting_followup.sh",
            "--dry-run",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode == 0, completed.stderr
    assert not artifact_dir.exists()
    assert '"planned_count": 11' in completed.stdout


def test_m3_cost_accounting_followup_core_summary(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "m3_followup"
    summary = tmp_path / "summary.json"
    env = dict(os.environ)
    env["ARTIFACT_DIR"] = str(artifact_dir)
    env["N_ITEMS"] = "1"
    completed = subprocess.run(
        [
            "scripts/run_rlt_m3_cost_accounting_followup.sh",
            "--dry-run",
            "--summary",
            str(summary),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(summary.read_text(encoding="utf-8"))
    assert payload["tier"] == "core"
    assert payload["planned_count"] == 11
    assert len(payload["cost_model_rows"]) == 14
    planned_phases = [step["phase"] for step in payload["planned"]]
    planned_commands = "\n".join(" ".join(step["command"]) for step in payload["planned"])
    assert "--n-items 1" in planned_commands
    assert "--expected-items 1" in planned_commands
    assert "--bucket-min-n 1" in planned_commands
    assert "videomme_short_random_cvision_admission_kr030" in planned_commands
    assert "videomme_short_random_cvision_admission_kr070" in planned_commands
    assert "fit_cost_model_n14" in planned_phases
    assert "mvbench_hosted_random_cvision_admission" not in planned_commands
    assert "tomato_motion_dev_rlt_composition" not in planned_commands


def test_m3_cost_accounting_followup_extended_summary(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "m3_followup"
    summary = tmp_path / "summary.json"
    env = dict(os.environ)
    env["ARTIFACT_DIR"] = str(artifact_dir)
    env["M3_FOLLOWUP_TIER"] = "extended"
    env["N_ITEMS"] = "1"
    completed = subprocess.run(
        [
            "scripts/run_rlt_m3_cost_accounting_followup.sh",
            "--dry-run",
            "--summary",
            str(summary),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode == 0, completed.stderr
    assert summary.exists()
    payload = json.loads(summary.read_text(encoding="utf-8"))
    assert payload["tier"] == "extended"
    assert payload["planned_count"] == 28
    assert len(payload["cost_model_rows"]) == 19
    planned_commands = "\n".join(" ".join(step["command"]) for step in payload["planned"])
    assert "mvbench_hosted_random_cvision_admission_kr030" in planned_commands
    assert "tomato_motion_dev_rlt_composition_kr050" in planned_commands
    assert "videomme_short_rlt_composition_kr050" in planned_commands
