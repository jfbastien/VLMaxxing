from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

from pytest import MonkeyPatch

import scripts.run_rlt_followup_queue as queue


def test_prefill_kernel_command_uses_paper_grade_controls(tmp_path: Path) -> None:
    command = queue._prefill_kernel_benchmark_command(
        artifact_dir=tmp_path,
        model_path=tmp_path / "model",
        rss_guard_mb=8123,
    )

    assert "--warm-all-shapes" in command
    assert "--shuffle" in command
    assert command[command.index("--rss-guard-mb") + 1] == "8123"


def test_portable_command_rewrites_repo_and_home_paths() -> None:
    command = [
        str(queue.REPO_ROOT / ".venv" / "bin" / "python3"),
        str(Path.home() / "models" / "gemma-4-e4b-it-4bit"),
        "scripts/run.py",
    ]

    portable = queue._portable_command(command)

    assert portable == [
        ".venv/bin/python3",
        "$HOME/models/gemma-4-e4b-it-4bit",
        "scripts/run.py",
    ]


def test_expected_items_for_manifest_uses_full_manifest_or_run_limit(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.toml"
    manifest.write_text(
        'benchmark = "mvbench"\nitem_ids = ["a", "b", "c", "d"]\n',
        encoding="utf-8",
    )

    assert queue._expected_items_for_manifest(manifest, n_items=0) == 4
    assert queue._expected_items_for_manifest(manifest, n_items=2) == 2
    assert queue._expected_items_for_manifest(manifest, n_items=8) == 4


def test_phase_passed_cvision_requires_sparse_induced_parse_gate_only() -> None:
    base: dict[str, Any] = {
        "pass_complete_pairing": True,
        "pass_fidelity": True,
        "pass_sparse_vision": True,
        "pass_e2e_positive": True,
        "pass_bucket_e2e_positive": True,
        "pass_parse_failure_delta": True,
        "pass_parse_failure_rate": True,
        "pass_ceiling_explained": True,
    }
    assert queue._phase_passed_cvision(base)

    candidate = dict(base)
    candidate["pass_parse_failure_delta"] = False
    assert not queue._phase_passed_cvision(candidate)

    for key in ("pass_parse_failure_rate", "pass_ceiling_explained"):
        candidate = dict(base)
        candidate[key] = False
        assert queue._phase_passed_cvision(candidate)


def test_run_command_group_stops_after_first_failure(monkeypatch: MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], *, allow_failure: bool = False) -> dict[str, Any]:
        calls.append(command)
        return {
            "command": command,
            "returncode": 7 if command == ["fail"] else 0,
            "elapsed_seconds": 0.0,
            "stdout_tail": "",
            "stderr_tail": "",
        }

    monkeypatch.setattr(queue, "_run", fake_run)
    results = queue._run_command_group([["ok"], ["fail"], ["stale_analyzer"]])

    assert [result["returncode"] for result in results] == [0, 7]
    assert calls == [["ok"], ["fail"]]


def test_expansion_requires_video_mme_rlt_gate(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_rlt_followup_queue.py",
            "--run-cvision-expansion",
            "--dry-run",
            "--summary",
            str(tmp_path / "summary.json"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "--run-cvision-expansion requires --run-cvision-rlt" in completed.stderr


def test_holdout_composition_requires_video_mme_rlt_gate(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_rlt_followup_queue.py",
            "--run-composition-holdout",
            "--dry-run",
            "--summary",
            str(tmp_path / "summary.json"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "--run-composition-holdout requires --run-cvision-rlt" in completed.stderr


def test_holdout_dry_run_plans_disjoint_direct_and_rescue_cells(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.json"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_rlt_followup_queue.py",
            "--run-cvision-rlt",
            "--run-composition-holdout",
            "--run-composition-rescue-holdout",
            "--dry-run",
            "--summary",
            str(summary_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    planned = payload["planned_commands"]
    phases = {item["phase"] for item in planned}
    commands = [item["command"] for item in planned]

    assert "full_composition_rlt_holdout_mvbench_if_rlt_videomme_core_passes" in phases
    assert (
        "full_composition_rlt_rescue_holdout_mvbench_"
        "if_holdout_direct_composition_needs_quality_rescue"
    ) in phases
    assert any(
        "research/benchmark_manifests/mvbench_motion_holdout_v2.toml" in command
        and any(
            arg.endswith("full_composition_rlt_holdout_mvbench_composed.jsonl") for arg in command
        )
        for command in commands
    )
    assert any(
        "--group-keep-rates" in command
        and "moving_attribute=0.85,object_interaction=0.85" in command
        and "research/benchmark_manifests/mvbench_motion_holdout_v2.toml" in command
        and any(
            arg.endswith("full_composition_rlt_rescue_holdout_mvbench_composed.jsonl")
            for arg in command
        )
        for command in commands
    )


def test_benchmark_holdout_manifests_are_disjoint_from_dev() -> None:
    def manifest_item_ids(path: Path) -> set[str]:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
        if "item_ids" in payload:
            return {str(item_id) for item_id in payload["item_ids"]}
        return {str(item["id"]) for item in payload["items"]}

    pairs = [
        (
            Path("research/benchmark_manifests/videomme_dev_v1.toml"),
            Path("research/benchmark_manifests/videomme_holdout_v1.toml"),
        ),
        (
            Path("research/benchmark_manifests/tomato_motion_dev_v2.toml"),
            Path("research/benchmark_manifests/tomato_motion_holdout_v2.toml"),
        ),
        (
            Path("research/benchmark_manifests/mvbench_motion_dev_v2.toml"),
            Path("research/benchmark_manifests/mvbench_motion_holdout_v2.toml"),
        ),
    ]
    for dev_path, holdout_path in pairs:
        assert manifest_item_ids(dev_path).isdisjoint(manifest_item_ids(holdout_path)), (
            dev_path,
            holdout_path,
        )


def test_moving_attribute_bracket_dry_run_plans_kr100_cell(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.json"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_rlt_followup_queue.py",
            "--run-cvision-rlt",
            "--run-moving-attribute-bracket",
            "--dry-run",
            "--summary",
            str(summary_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    commands = [item["command"] for item in payload["planned_commands"]]

    assert any(
        "--group-keep-rates" in command
        and "moving_attribute=1,object_interaction=0.85" in command
        and any(
            arg.endswith("full_composition_rlt_mvbench_moving_attribute_kr100_composed.jsonl")
            for arg in command
        )
        for command in commands
    )


def test_moving_attribute_holdout_bracket_uses_holdout_manifest(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.json"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_rlt_followup_queue.py",
            "--run-cvision-rlt",
            "--run-moving-attribute-holdout-bracket",
            "--dry-run",
            "--summary",
            str(summary_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    commands = [item["command"] for item in payload["planned_commands"]]

    assert any(
        "--group-keep-rates" in command
        and "moving_attribute=1,object_interaction=0.85" in command
        and "research/benchmark_manifests/mvbench_motion_holdout_v2.toml" in command
        and any(
            arg.endswith(
                "full_composition_rlt_holdout_mvbench_moving_attribute_kr100_composed.jsonl"
            )
            for arg in command
        )
        for command in commands
    )


def test_combined_composition_analysis_dry_run_uses_dev_and_holdout_jsonls(
    tmp_path: Path,
) -> None:
    summary_path = tmp_path / "summary.json"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_rlt_followup_queue.py",
            "--run-cvision-rlt",
            "--run-composition-combined-analysis",
            "--dry-run",
            "--summary",
            str(summary_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    commands = [item["command"] for item in payload["planned_commands"]]
    combined = next(
        command
        for command in commands
        if any(
            arg.endswith("full_composition_rlt_combined_mvbench_analysis.json") for arg in command
        )
    )

    assert combined.count("--dense-jsonl") == 2
    assert combined.count("--composed-jsonl") == 2
    assert (
        "research/experiments/2026/artifacts/rlt_followup_queue/"
        "full_composition_dense_mvbench.jsonl"
    ) in combined
    assert (
        "research/experiments/2026/artifacts/rlt_followup_queue/"
        "full_composition_rlt_holdout_mvbench_composed.jsonl"
    ) in combined
    assert combined[combined.index("--expected-items") + 1] == "60"


def test_cvision_commands_can_reuse_dense_and_set_keep_rate(tmp_path: Path) -> None:
    commands = queue._cvision_commands(
        artifact_dir=tmp_path,
        manifest=Path("manifest.toml"),
        model_path=Path("model"),
        frame_count=8,
        n_items=30,
        rss_guard_mb=9000,
        mlx_memory_limit_gb=12.0,
        label="cvision_rlt_tomato_kr030",
        expected_items=30,
        score_mode="rlt_topk",
        keep_rate=0.3,
        dense_source_label="cvision_rlt_tomato",
        include_dense_command=False,
    )

    assert len(commands) == 2
    sparse, analyze = commands
    assert sparse[sparse.index("--vision-tower-keep-rate") + 1] == "0.3"
    assert str(tmp_path / "cvision_rlt_tomato_dense.jsonl") in analyze
    assert str(tmp_path / "cvision_rlt_tomato_kr030_analysis.json") in analyze


def test_cvision_commands_can_run_valid_position_magnitude(tmp_path: Path) -> None:
    commands = queue._cvision_commands(
        artifact_dir=tmp_path,
        manifest=Path("manifest.toml"),
        model_path=Path("model"),
        frame_count=8,
        n_items=30,
        rss_guard_mb=9000,
        mlx_memory_limit_gb=60.0,
        label="cvision_magnitude_valid_videomme",
        expected_items=30,
        score_mode="magnitude_valid",
        dense_source_label="cvision_rlt_videomme",
        include_dense_command=False,
    )

    sparse, analyze = commands

    assert len(commands) == 2
    assert sparse[sparse.index("--vision-tower-score-mode") + 1] == "magnitude_valid"
    assert sparse[sparse.index("--mlx-memory-limit-gb") + 1] == "60"
    assert str(tmp_path / "cvision_rlt_videomme_dense.jsonl") in analyze
    assert str(tmp_path / "cvision_magnitude_valid_videomme_analysis.json") in analyze


def test_composition_command_uses_rlt_for_admission_and_cvision(tmp_path: Path) -> None:
    run_command, analyze_command = queue._gemma_composition_commands(
        artifact_dir=tmp_path,
        manifest=Path("manifest.toml"),
        model_path=Path("model"),
        frame_count=8,
        n_items=30,
        rss_guard_mb=9000,
        mlx_memory_limit_gb=12.0,
        label="composition_rlt_videomme",
    )

    assert run_command[run_command.index("--prune-placeholders") + 1] == "rlt"
    assert run_command[run_command.index("--vision-tower-score-mode") + 1] == "rlt_topk"
    assert run_command[run_command.index("--mlx-memory-limit-gb") + 1] == "12"
    assert run_command[run_command.index("--prefill-step-size") + 1] == "1024"
    assert analyze_command[analyze_command.index("--cell-type") + 1] == "h3b_admission"


def test_composition_command_allows_prefill_step_override(tmp_path: Path) -> None:
    run_command, _analyze_command = queue._gemma_composition_commands(
        artifact_dir=tmp_path,
        manifest=Path("manifest.toml"),
        model_path=Path("model"),
        frame_count=8,
        n_items=30,
        rss_guard_mb=9000,
        mlx_memory_limit_gb=60.0,
        label="composition_rlt_videomme",
        prefill_step_size=1536,
    )

    assert run_command[run_command.index("--prefill-step-size") + 1] == "1536"
    assert run_command[run_command.index("--mlx-memory-limit-gb") + 1] == "60"


def test_composition_command_can_set_group_specific_keep_rates(tmp_path: Path) -> None:
    run_command, _analyze_command = queue._gemma_composition_commands(
        artifact_dir=tmp_path,
        manifest=Path("manifest.toml"),
        model_path=Path("model"),
        frame_count=8,
        n_items=30,
        rss_guard_mb=9000,
        mlx_memory_limit_gb=12.0,
        label="composition_rlt_mvbench_rescue",
        group_keep_rates={"moving_attribute": 0.85, "object_interaction": 0.85},
        group_vision_keep_rates={"moving_attribute": 0.85, "object_interaction": 0.85},
    )

    assert run_command[run_command.index("--group-keep-rates") + 1] == (
        "moving_attribute=0.85,object_interaction=0.85"
    )
    assert run_command[run_command.index("--group-vision-keep-rates") + 1] == (
        "moving_attribute=0.85,object_interaction=0.85"
    )


def test_full_composition_commands_build_dense_reference_and_composed_arm(tmp_path: Path) -> None:
    dense, composed, analyze = queue._gemma_full_composition_commands(
        artifact_dir=tmp_path,
        manifest=Path("manifest.toml"),
        model_path=Path("model"),
        frame_count=8,
        n_items=30,
        expected_items=30,
        rss_guard_mb=9000,
        mlx_memory_limit_gb=60.0,
        benchmark="videomme",
        prefill_step_size=1024,
    )

    assert dense[dense.index("--prune-placeholders") + 1] == "none"
    assert dense[dense.index("--mlx-memory-limit-gb") + 1] == "60"
    assert dense[dense.index("--vision-tower-keep-rate") + 1] == "1.0"
    assert composed[composed.index("--prune-placeholders") + 1] == "rlt"
    assert composed[composed.index("--vision-tower-score-mode") + 1] == "rlt_topk"
    assert composed[composed.index("--prefill-step-size") + 1] == "1024"
    assert "scripts/analyze_gemma_full_composition.py" in analyze
    assert str(tmp_path / "full_composition_rlt_videomme_analysis.json") in analyze


def test_full_composition_commands_can_build_adaptive_rescue_label(tmp_path: Path) -> None:
    dense, composed, analyze = queue._gemma_full_composition_commands(
        artifact_dir=tmp_path,
        manifest=Path("manifest.toml"),
        model_path=Path("model"),
        frame_count=8,
        n_items=30,
        expected_items=30,
        rss_guard_mb=9000,
        mlx_memory_limit_gb=60.0,
        benchmark="mvbench",
        prefill_step_size=1024,
        label="full_composition_rlt_rescue_mvbench",
        group_keep_rates={"moving_attribute": 0.85, "object_interaction": 0.85},
        group_vision_keep_rates={"moving_attribute": 0.85, "object_interaction": 0.85},
    )

    assert str(tmp_path / "full_composition_rlt_rescue_mvbench_dense.jsonl") in dense
    assert str(tmp_path / "full_composition_rlt_rescue_mvbench_composed.jsonl") in composed
    assert composed[composed.index("--group-keep-rates") + 1] == (
        "moving_attribute=0.85,object_interaction=0.85"
    )
    assert composed[composed.index("--group-vision-keep-rates") + 1] == (
        "moving_attribute=0.85,object_interaction=0.85"
    )
    assert str(tmp_path / "full_composition_rlt_rescue_mvbench_analysis.json") in analyze


def test_full_composition_commands_can_build_cvision_only_q0b_arm(tmp_path: Path) -> None:
    commands = queue._gemma_full_composition_commands(
        artifact_dir=tmp_path,
        manifest=Path("manifest.toml"),
        model_path=Path("model"),
        frame_count=8,
        n_items=30,
        expected_items=30,
        rss_guard_mb=9000,
        mlx_memory_limit_gb=12.0,
        benchmark="mvbench",
        label="query_q0b_cvision_only_mvbench_kr050",
        dense_source_label="query_q0b_dense_mvbench",
        include_dense_command=False,
        composed_keep_rate=1.0,
        composed_prune_placeholders="none",
        vision_keep_rate=0.5,
        vision_score_mode="rlt_topk",
    )

    composed, analyze = commands
    assert composed[composed.index("--prune-placeholders") + 1] == "none"
    assert composed[composed.index("--keep-rate") + 1] == "1"
    assert composed[composed.index("--vision-tower-keep-rate") + 1] == "0.5"
    assert composed[composed.index("--vision-tower-score-mode") + 1] == "rlt_topk"
    assert str(tmp_path / "query_q0b_dense_mvbench_dense.jsonl") in analyze
    assert str(tmp_path / "query_q0b_cvision_only_mvbench_kr050_analysis.json") in analyze


def test_full_composition_commands_keep_cvision_oracle_patched_at_one(
    tmp_path: Path,
) -> None:
    commands = queue._gemma_full_composition_commands(
        artifact_dir=tmp_path,
        manifest=Path("manifest.toml"),
        model_path=Path("model"),
        frame_count=8,
        n_items=30,
        expected_items=30,
        rss_guard_mb=9000,
        mlx_memory_limit_gb=12.0,
        benchmark="mvbench",
        label="query_q0b_cvision_only_mvbench_kr100",
        dense_source_label="query_q0b_dense_mvbench",
        include_dense_command=False,
        composed_keep_rate=1.0,
        composed_prune_placeholders="none",
        vision_keep_rate=1.0,
        vision_score_mode="rlt_topk",
    )

    composed, analyze = commands
    assert composed[composed.index("--prune-placeholders") + 1] == "none"
    assert composed[composed.index("--vision-tower-keep-rate") + 1] == "1"
    assert composed[composed.index("--vision-tower-score-mode") + 1] == "rlt_topk"
    assert str(tmp_path / "query_q0b_cvision_only_mvbench_kr100_analysis.json") in analyze


def test_query_routing_requires_q0b_for_q1(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_rlt_followup_queue.py",
            "--run-cvision-rlt",
            "--run-query-routing-q1",
            "--dry-run",
            "--summary",
            str(tmp_path / "summary.json"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "--run-query-routing-q1 requires --run-cvision-rlt and --run-query-routing-q0b" in (
        completed.stderr
    )


def test_query_routing_dry_run_plans_q0b_and_q1_controls(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.json"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_rlt_followup_queue.py",
            "--run-cvision-rlt",
            "--run-query-routing-q0b",
            "--run-query-routing-q1",
            "--query-routing-benchmarks",
            "mvbench",
            "--dry-run",
            "--summary",
            str(summary_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    commands = [item["command"] for item in payload["planned_commands"]]
    assert any(
        "--prune-placeholders" in command
        and command[command.index("--prune-placeholders") + 1] == "none"
        and "--vision-tower-score-mode" in command
        and command[command.index("--vision-tower-score-mode") + 1] == "rlt_topk"
        and any(
            arg.endswith("query_q0b_cvision_only_mvbench_kr050_composed.jsonl") for arg in command
        )
        for command in commands
    )
    assert any(
        "--vision-tower-score-mode" in command
        and command[command.index("--vision-tower-score-mode") + 1] == "rlt_topk_static_floor"
        and "--vision-static-floor-stride" in command
        and any(arg.endswith("query_q1_mvbench_static_floor_s4_composed.jsonl") for arg in command)
        for command in commands
    )
    assert any(
        "--vision-tower-score-mode" in command
        and command[command.index("--vision-tower-score-mode") + 1] == "random_valid"
        and "--vision-random-seed" in command
        for command in commands
    )


def test_query_routing_hosted_manifest_uses_manifest_item_count(tmp_path: Path) -> None:
    manifest = tmp_path / "mvbench_hosted.toml"
    manifest.write_text(
        'benchmark = "mvbench"\n'
        "item_ids = [\n"
        + "".join(f'  "mvbench:action_antonym:{idx}",\n' for idx in range(4))
        + "]\n",
        encoding="utf-8",
    )
    summary_path = tmp_path / "summary.json"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_rlt_followup_queue.py",
            "--run-cvision-rlt",
            "--run-query-routing-q0b",
            "--run-query-routing-q1",
            "--query-routing-benchmarks",
            "mvbench",
            "--mvbench-manifest",
            str(manifest),
            "--dry-run",
            "--summary",
            str(summary_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    analyze_commands = [
        item["command"]
        for item in payload["planned_commands"]
        if item["command"][1] == "scripts/analyze_gemma_full_composition.py"
        and any("query_q1_mvbench" in arg for arg in item["command"])
    ]
    assert analyze_commands
    assert all(
        command[command.index("--expected-items") + 1] == "4" for command in analyze_commands
    )


def test_query_routing_q1b_dry_run_plans_endpoint_and_repair_cells(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.json"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_rlt_followup_queue.py",
            "--run-cvision-rlt",
            "--run-query-routing-q0b",
            "--run-query-routing-q1",
            "--run-query-routing-q1b-followup",
            "--query-routing-benchmarks",
            "mvbench",
            "--dry-run",
            "--summary",
            str(summary_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    commands = [item["command"] for item in payload["planned_commands"]]
    assert any(
        "--vision-tower-score-mode" in command
        and command[command.index("--vision-tower-score-mode") + 1] == "rlt_topk_endpoint_anchor"
        and any(arg.endswith("query_q1b_mvbench_endpoint_anchor_composed.jsonl") for arg in command)
        for command in commands
    )
    assert any(
        "--vision-tower-score-mode" in command
        and command[command.index("--vision-tower-score-mode") + 1] == "random_valid"
        and "--group-vision-keep-rates" in command
        and command[command.index("--group-vision-keep-rates") + 1] == "action_localization=1"
        and any(
            arg.endswith("query_q1b_mvbench_random_seed11_actionloc_dense_composed.jsonl")
            for arg in command
        )
        for command in commands
    )
    assert any(
        "--prune-placeholders" in command
        and command[command.index("--prune-placeholders") + 1] == "rlt"
        and "--vision-tower-score-mode" in command
        and command[command.index("--vision-tower-score-mode") + 1] == "fixed_uniform"
        and any(
            arg.endswith("query_q1b_mvbench_fixed_uniform_admission_on_composed.jsonl")
            for arg in command
        )
        for command in commands
    )


def test_query_routing_q1b_requires_q1(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_rlt_followup_queue.py",
            "--run-cvision-rlt",
            "--run-query-routing-q0b",
            "--run-query-routing-q1b-followup",
            "--dry-run",
            "--summary",
            str(tmp_path / "summary.json"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "--run-query-routing-q1b-followup requires" in completed.stderr


def test_query_routing_q1c_dry_run_plans_safe_admission_cells(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.json"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_rlt_followup_queue.py",
            "--run-cvision-rlt",
            "--run-query-routing-q0b",
            "--run-query-routing-q1",
            "--run-query-routing-q1b-followup",
            "--run-query-routing-q1c-admission-scheduler",
            "--query-routing-benchmarks",
            "mvbench",
            "--dry-run",
            "--summary",
            str(summary_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    commands = [item["command"] for item in payload["planned_commands"]]
    assert any(
        "--prune-placeholders" in command
        and command[command.index("--prune-placeholders") + 1] == "none"
        and "--keep-rate" in command
        and command[command.index("--keep-rate") + 1] == "1"
        and "--group-prune-placeholders" in command
        and command[command.index("--group-prune-placeholders") + 1]
        == "fine_grained_action=rlt,moving_direction=rlt"
        and "--vision-tower-score-mode" in command
        and command[command.index("--vision-tower-score-mode") + 1] == "random_valid"
        and any(
            arg.endswith("query_q1c_mvbench_random_seed11_safe_admission_composed.jsonl")
            for arg in command
        )
        for command in commands
    )
    assert any(
        "--group-vision-keep-rates" in command
        and command[command.index("--group-vision-keep-rates") + 1] == "action_localization=1"
        and any(
            arg.endswith(
                "query_q1c_mvbench_random_seed11_safe_admission_actionloc_dense_composed.jsonl"
            )
            for arg in command
        )
        for command in commands
    )


def test_query_routing_q1c_requires_q1b(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_rlt_followup_queue.py",
            "--run-cvision-rlt",
            "--run-query-routing-q0b",
            "--run-query-routing-q1",
            "--run-query-routing-q1c-admission-scheduler",
            "--dry-run",
            "--summary",
            str(tmp_path / "summary.json"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "--run-query-routing-q1c-admission-scheduler requires" in completed.stderr


def test_query_q1b_verdict_compares_against_best_fixed_or_random_control() -> None:
    def analysis(*, delta: float, target_delta: float, speedup: float = 1.2) -> dict[str, Any]:
        return {
            "summary": {
                "accuracy_delta_composed_minus_dense": delta,
                "e2e_speedup_dense_over_composed": speedup,
                "pass_fidelity": delta >= -0.05,
                "pass_parse_failure_delta": True,
                "bucket_failures": [],
                "by_group": {
                    "moving_attribute": {
                        "n": 6,
                        "dense_accuracy": 0.5,
                        "composed_accuracy": 0.5 + target_delta,
                    },
                    "object_interaction": {
                        "n": 6,
                        "dense_accuracy": 0.5,
                        "composed_accuracy": 0.5,
                    },
                },
            }
        }

    analyses = {
        "query_q1_mvbench_random_seed11": analysis(delta=-0.10, target_delta=-0.10, speedup=1.20),
        "query_q1_mvbench_fixed_uniform": analysis(delta=0.00, target_delta=0.00, speedup=1.20),
        "query_q1b_mvbench_endpoint_anchor": analysis(delta=0.00, target_delta=-0.05),
        "query_q1b_mvbench_random_seed11_actionloc_dense": analysis(
            delta=-0.10, target_delta=-0.10
        ),
        "query_q1b_mvbench_fixed_uniform_actionloc_dense": analysis(delta=0.00, target_delta=0.00),
        "query_q1b_mvbench_random_seed11_admission_on": analysis(
            delta=-0.10, target_delta=-0.10, speedup=1.30
        ),
        "query_q1b_mvbench_fixed_uniform_admission_on": analysis(
            delta=0.00, target_delta=0.00, speedup=1.30
        ),
    }

    verdict = queue._query_q1b_followup_verdict(analyses)

    assert verdict["best_base_target_accuracy_delta"] == 0.0
    assert verdict["endpoint_anchor_competitive"] is False
    assert verdict["coverage_repair_by_control"] == {
        "fixed_uniform": True,
        "random_seed11": True,
    }
    assert verdict["admission_preserves_best_control"] is True


def test_query_q1b_admission_verdict_requires_e2e_improvement() -> None:
    def analysis(*, target_delta: float, speedup: float) -> dict[str, Any]:
        return {
            "summary": {
                "accuracy_delta_composed_minus_dense": target_delta,
                "e2e_speedup_dense_over_composed": speedup,
                "pass_fidelity": True,
                "pass_parse_failure_delta": True,
                "bucket_failures": [],
                "by_group": {
                    "moving_attribute": {
                        "n": 6,
                        "dense_accuracy": 0.5,
                        "composed_accuracy": 0.5 + target_delta,
                    },
                    "object_interaction": {
                        "n": 6,
                        "dense_accuracy": 0.5,
                        "composed_accuracy": 0.5,
                    },
                },
            }
        }

    analyses = {
        "query_q1_mvbench_random_seed11": analysis(target_delta=0.0, speedup=1.25),
        "query_q1_mvbench_fixed_uniform": analysis(target_delta=0.0, speedup=1.25),
        "query_q1b_mvbench_endpoint_anchor": analysis(target_delta=0.0, speedup=1.1),
        "query_q1b_mvbench_random_seed11_actionloc_dense": analysis(target_delta=0.0, speedup=1.2),
        "query_q1b_mvbench_fixed_uniform_actionloc_dense": analysis(target_delta=0.0, speedup=1.2),
        "query_q1b_mvbench_random_seed11_admission_on": analysis(target_delta=0.0, speedup=1.25),
        "query_q1b_mvbench_fixed_uniform_admission_on": analysis(target_delta=0.0, speedup=1.20),
    }

    verdict = queue._query_q1b_followup_verdict(analyses)

    assert verdict["admission_preserves_by_control"] == {
        "fixed_uniform": False,
        "random_seed11": False,
    }
    assert verdict["admission_preserves_best_control"] is False


def test_query_q1c_verdict_requires_accuracy_and_speed_gain() -> None:
    def analysis(*, delta: float, target_delta: float, speedup: float) -> dict[str, Any]:
        return {
            "summary": {
                "accuracy_delta_composed_minus_dense": delta,
                "e2e_speedup_dense_over_composed": speedup,
                "pass_fidelity": delta >= -0.05,
                "pass_parse_failure_delta": True,
                "bucket_failures": [],
                "by_group": {
                    "moving_attribute": {
                        "n": 6,
                        "dense_accuracy": 0.5,
                        "composed_accuracy": 0.5 + target_delta,
                    },
                    "object_interaction": {
                        "n": 6,
                        "dense_accuracy": 0.5,
                        "composed_accuracy": 0.5,
                    },
                },
            }
        }

    analyses = {
        "query_q1_mvbench_random_seed11": analysis(delta=0.0, target_delta=0.0, speedup=1.25),
        "query_q1b_mvbench_random_seed11_actionloc_dense": analysis(
            delta=0.03, target_delta=0.0, speedup=1.14
        ),
        "query_q1c_mvbench_random_seed11_safe_admission": analysis(
            delta=0.03, target_delta=0.0, speedup=1.28
        ),
        "query_q1c_mvbench_random_seed11_safe_admission_actionloc_dense": analysis(
            delta=0.03, target_delta=0.0, speedup=1.18
        ),
    }

    verdict = queue._query_q1c_admission_scheduler_verdict(analyses)

    assert verdict["safe_admission_beats_q1_random"]
    assert verdict["safe_admission_actionloc_dense_beats_q1b_actionloc_dense"]
    assert verdict["proceed_to_holdout_admission_scheduler"]


def test_query_q1c_verdict_rejects_speed_only_regression() -> None:
    def analysis(*, delta: float, target_delta: float, speedup: float) -> dict[str, Any]:
        return {
            "summary": {
                "accuracy_delta_composed_minus_dense": delta,
                "e2e_speedup_dense_over_composed": speedup,
                "pass_fidelity": delta >= -0.05,
                "pass_parse_failure_delta": True,
                "bucket_failures": [],
                "by_group": {
                    "moving_attribute": {
                        "n": 6,
                        "dense_accuracy": 0.5,
                        "composed_accuracy": 0.5 + target_delta,
                    },
                    "object_interaction": {
                        "n": 6,
                        "dense_accuracy": 0.5,
                        "composed_accuracy": 0.5,
                    },
                },
            }
        }

    analyses = {
        "query_q1_mvbench_random_seed11": analysis(delta=0.0, target_delta=0.0, speedup=1.25),
        "query_q1b_mvbench_random_seed11_actionloc_dense": analysis(
            delta=0.03, target_delta=0.0, speedup=1.14
        ),
        "query_q1c_mvbench_random_seed11_safe_admission": analysis(
            delta=-0.10, target_delta=-0.10, speedup=1.45
        ),
        "query_q1c_mvbench_random_seed11_safe_admission_actionloc_dense": analysis(
            delta=0.03, target_delta=-0.10, speedup=1.45
        ),
    }

    verdict = queue._query_q1c_admission_scheduler_verdict(analyses)

    assert not verdict["safe_admission_beats_q1_random"]
    assert not verdict["safe_admission_actionloc_dense_beats_q1b_actionloc_dense"]
    assert not verdict["proceed_to_holdout_admission_scheduler"]


def _direct_summary(
    *,
    cell_type: str,
    accuracy_delta: float = 0.0,
    e2e_speedup: float = 1.1,
    dense_equivalent: bool | None = None,
) -> dict[str, Any]:
    return {
        "summary": {
            "cell_type": cell_type,
            "pass_complete_pairing": True,
            "pass_dense_equivalence": dense_equivalent,
            "pass_fidelity": accuracy_delta >= -0.05,
            "pass_e2e_positive": e2e_speedup > 1.0,
            "pass_parse_failure_delta": True,
            "pass_bucket_quality_and_e2e": True,
            "accuracy_delta_composed_minus_dense": accuracy_delta,
            "e2e_speedup_dense_over_composed": e2e_speedup,
            "by_group": {
                "moving_attribute": {
                    "n": 5,
                    "dense_accuracy": 0.6,
                    "composed_accuracy": 0.6 + accuracy_delta,
                },
                "object_interaction": {
                    "n": 5,
                    "dense_accuracy": 0.6,
                    "composed_accuracy": 0.6 + accuracy_delta,
                },
            },
        }
    }


def test_query_q0b_gate_requires_full_diagnostic_grid() -> None:
    analyses: dict[str, Any] = {
        "query_q0b_dense_equivalent_mvbench": _direct_summary(
            cell_type="dense_equivalent",
            dense_equivalent=True,
        )
    }

    gate = queue._query_q0b_gate(analyses, ["mvbench"])

    assert not gate["proceed_to_q1"]
    assert gate["by_benchmark"]["mvbench"]["missing"]

    analyses.update(
        {
            "query_q0b_admission_only_mvbench": _direct_summary(cell_type="rlt_admission_only"),
            "query_q0b_cvision_only_mvbench_kr050": _direct_summary(cell_type="rlt_cvision_only"),
            "query_q0b_cvision_only_mvbench_kr100": _direct_summary(cell_type="rlt_cvision_only"),
            "query_q0b_full_mvbench_kr050": _direct_summary(
                cell_type="rlt_admission_plus_rlt_cvision"
            ),
            "query_q0b_full_mvbench_kr070": _direct_summary(
                cell_type="rlt_admission_plus_rlt_cvision"
            ),
            "query_q0b_full_mvbench_kr085": _direct_summary(
                cell_type="rlt_admission_plus_rlt_cvision"
            ),
            "query_q0b_full_mvbench_kr100": _direct_summary(
                cell_type="rlt_admission_plus_rlt_cvision"
            ),
        }
    )

    gate = queue._query_q0b_gate(analyses, ["mvbench"])

    assert gate["proceed_to_q1"]
    assert gate["by_benchmark"]["mvbench"]["passed"]


def test_query_q1_verdict_requires_typed_operator_to_beat_controls() -> None:
    analyses: dict[str, Any] = {
        "query_q1_mvbench_redundancy_kr050": _direct_summary(
            cell_type="rlt_cvision_only",
            accuracy_delta=0.0,
        ),
        "query_q1_mvbench_redundancy_kr070": _direct_summary(
            cell_type="rlt_cvision_only",
            accuracy_delta=0.0,
        ),
        "query_q1_mvbench_static_floor_s4": _direct_summary(
            cell_type="rlt_topk_static_floor_cvision_only",
            accuracy_delta=0.1,
        ),
        "query_q1_mvbench_fixed_uniform": _direct_summary(
            cell_type="fixed_uniform_cvision_only",
            accuracy_delta=0.0,
        ),
        "query_q1_mvbench_random_seed11": _direct_summary(
            cell_type="random_valid_cvision_only",
            accuracy_delta=0.0,
        ),
        "query_q1_mvbench_random_seed23": _direct_summary(
            cell_type="random_valid_cvision_only",
            accuracy_delta=0.0,
        ),
        "query_q1_mvbench_random_seed37": _direct_summary(
            cell_type="random_valid_cvision_only",
            accuracy_delta=0.0,
        ),
    }

    verdict = queue._query_q1_verdict(analyses, ["mvbench"])

    assert verdict["proceed_to_q2_scalar_query_baseline"]

    analyses["query_q1_mvbench_fixed_uniform"] = _direct_summary(
        cell_type="fixed_uniform_cvision_only",
        accuracy_delta=0.2,
    )
    verdict = queue._query_q1_verdict(analyses, ["mvbench"])

    assert not verdict["proceed_to_q2_scalar_query_baseline"]


def test_phase_passed_full_composition_requires_direct_gates() -> None:
    analysis = {
        "summary": {
            "pass_fidelity": True,
            "pass_e2e_positive": True,
            "pass_parse_failure_delta": True,
            "pass_bucket_quality_and_e2e": True,
        }
    }
    assert queue._phase_passed_full_composition(analysis)

    analysis["summary"]["pass_bucket_quality_and_e2e"] = False
    assert not queue._phase_passed_full_composition(analysis)
