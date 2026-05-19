#!/usr/bin/env python3
"""Run post-H3B RLT/VLMaxxing follow-up experiments with early cancellation."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import tomllib
from pathlib import Path
from typing import Any, cast

SCHEMA_VERSION = "rlt_followup_queue_v1"
GEMMA_TRACK_B_SCHEMA_VERSION = "phase1_63g_gemma_track_b_v5"
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ARTIFACT_DIR = Path("research/experiments/2026/artifacts/rlt_followup_queue")
DEFAULT_MODEL_PATH = Path.home() / "models" / "gemma-4-e4b-it-4bit"
DEFAULT_VIDEOMME_MANIFEST = Path("research/benchmark_manifests/videomme_combined_v1_n60.toml")
DEFAULT_SMOKE_MANIFEST = Path("research/benchmark_manifests/videomme_dev_v1.toml")
DEFAULT_TOMATO_MANIFEST = Path("research/benchmark_manifests/tomato_motion_dev_v2.toml")
DEFAULT_MVBENCH_MANIFEST = Path("research/benchmark_manifests/mvbench_motion_dev_v2.toml")
DEFAULT_VIDEOMME_HOLDOUT_MANIFEST = Path("research/benchmark_manifests/videomme_holdout_v1.toml")
DEFAULT_TOMATO_HOLDOUT_MANIFEST = Path("research/benchmark_manifests/tomato_motion_holdout_v2.toml")
DEFAULT_MVBENCH_HOLDOUT_MANIFEST = Path(
    "research/benchmark_manifests/mvbench_motion_holdout_v2.toml"
)
DEFAULT_COMPOSITION_PREFILL_STEP_SIZE = 1024
ADAPTIVE_COMPOSITION_GROUP_KEEP_RATES: dict[str, dict[str, float]] = {
    # Round-18 direct-composition failures were bucket-local. These rescue
    # policies raise K only in the failed groups instead of paying a global
    # speed penalty.
    "videomme": {"long": 0.7, "medium": 0.7},
    "tomato": {"direction": 0.85},
    "mvbench": {"moving_attribute": 0.85, "object_interaction": 0.85},
}
MVBENCH_MOVING_ATTRIBUTE_BRACKET_KEEP_RATES: dict[str, float] = {
    # Round-19 rescue recovered object_interaction at 0.85 but not
    # moving_attribute. This bracket keeps the known rescue for
    # object_interaction while testing whether full retention recovers the
    # remaining moving_attribute failure.
    "moving_attribute": 1.0,
    "object_interaction": 0.85,
}
QUERY_ROUTING_Q1_RANDOM_SEEDS = (11, 23, 37)
QUERY_ROUTING_Q1B_ACTIONLOC_REPAIR_KEEP_RATES = {"action_localization": 1.0}
QUERY_ROUTING_Q1C_SAFE_ADMISSION_KEEP_RATES = {
    "fine_grained_action": 0.5,
    "moving_direction": 0.5,
}
QUERY_ROUTING_Q1C_MOVING_ATTRIBUTE_SAFE_ADMISSION_GROUPS = {
    "action_localization",
    "fine_grained_action",
    "moving_direction",
    "object_interaction",
}
QUERY_ROUTING_Q1C_ACTIONLOC_DENSE_KEEP_RATES = {"action_localization": 1.0}

PHASE_ESTIMATES_HOURS = {
    "prefill-kernel-microbench": [0.35, 1.35],
    "prefill-step-1500-n30": [0.6, 1.3],
    "prefill-step-4096-n30": [0.6, 1.3],
    "cvision-rlt-smoke": [0.1, 0.4],
    "cvision-rlt-videomme-n30": [1.0, 2.4],
    "cvision-maxmin-videomme-n30": [1.2, 2.8],
    "cvision-rlt-tomato-n30": [1.0, 2.0],
    "cvision-rlt-mvbench-n30": [1.0, 2.0],
    "cvision-maxmin-tomato-n30": [1.2, 2.4],
    "cvision-maxmin-mvbench-n30": [1.2, 2.4],
    "cvision-magnitude-videomme-n30": [0.8, 1.8],
    "cvision-magnitude-tomato-n30": [0.8, 1.6],
    "cvision-magnitude-mvbench-n30": [0.8, 1.6],
    "cvision-magnitude-valid-videomme-n30": [0.8, 1.8],
    "cvision-magnitude-valid-tomato-n30": [0.8, 1.6],
    "cvision-magnitude-valid-mvbench-n30": [0.8, 1.6],
    "composition-rlt-videomme-n30": [0.6, 1.3],
    "composition-rlt-tomato-n30": [0.6, 1.2],
    "composition-rlt-mvbench-n30": [0.6, 1.2],
    "full-composition-rlt-videomme-n30": [1.0, 2.2],
    "full-composition-rlt-tomato-n30": [1.0, 2.0],
    "full-composition-rlt-mvbench-n30": [1.0, 2.0],
    "full-composition-rlt-rescue-videomme-n30": [1.0, 2.2],
    "full-composition-rlt-rescue-tomato-n30": [1.0, 2.0],
    "full-composition-rlt-rescue-mvbench-n30": [1.0, 2.0],
    "full-composition-rlt-holdout-videomme-n30": [1.0, 2.2],
    "full-composition-rlt-holdout-tomato-n30": [1.0, 2.0],
    "full-composition-rlt-holdout-mvbench-n30": [1.0, 2.0],
    "full-composition-rlt-rescue-holdout-videomme-n30": [1.0, 2.2],
    "full-composition-rlt-rescue-holdout-tomato-n30": [1.0, 2.0],
    "full-composition-rlt-rescue-holdout-mvbench-n30": [1.0, 2.0],
    "full-composition-rlt-mvbench-moving-attribute-kr100-n30": [1.0, 2.0],
    "full-composition-rlt-holdout-mvbench-moving-attribute-kr100-n30": [1.0, 2.0],
    "full-composition-rlt-combined-videomme-n60-analysis": [0.02, 0.08],
    "full-composition-rlt-combined-tomato-n60-analysis": [0.02, 0.08],
    "full-composition-rlt-combined-mvbench-n60-analysis": [0.02, 0.08],
    "full-composition-rlt-rescue-combined-videomme-n60-analysis": [0.02, 0.08],
    "full-composition-rlt-rescue-combined-tomato-n60-analysis": [0.02, 0.08],
    "full-composition-rlt-rescue-combined-mvbench-n60-analysis": [0.02, 0.08],
    "cvision-kr-sweep-tomato": [1.2, 2.4],
    "cvision-kr-sweep-mvbench": [1.2, 2.4],
    "cvision-kr-sweep-videomme": [1.4, 3.0],
    "query-routing-q0b-videomme-n30": [5.0, 10.0],
    "query-routing-q0b-tomato-n30": [5.0, 9.0],
    "query-routing-q0b-mvbench-n30": [5.0, 9.0],
    "query-routing-q1-videomme-n30": [4.0, 9.0],
    "query-routing-q1-tomato-n30": [4.0, 8.0],
    "query-routing-q1-mvbench-n30": [4.0, 8.0],
    "query-routing-q1b-mvbench-n30": [2.5, 5.5],
    "query-routing-q1c-mvbench-n30": [2.0, 5.0],
}


def _portable_arg(arg: str) -> str:
    path = Path(arg)
    if not path.is_absolute():
        return arg
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        pass
    home = Path.home()
    try:
        return f"$HOME/{path.relative_to(home).as_posix()}"
    except ValueError:
        return arg


def _portable_command(command: list[str]) -> list[str]:
    return [_portable_arg(arg) for arg in command]


def _portable_planned(planned: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            **item,
            "command": _portable_command(cast(list[str], item["command"])),
        }
        for item in planned
    ]


def _manifest_item_count(path: Path) -> int:
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    item_ids = payload.get("item_ids")
    if isinstance(item_ids, list):
        if not all(isinstance(item_id, str) for item_id in item_ids):
            raise ValueError(f"{path} has non-string item_ids")
        return len(item_ids)
    items = payload.get("items")
    if isinstance(items, list):
        return len(items)
    raise ValueError(f"{path} is missing item_ids/items")


def _expected_items_for_manifest(path: Path, *, n_items: int) -> int:
    manifest_count = _manifest_item_count(path)
    if manifest_count <= 0:
        raise ValueError(f"{path} has no benchmark items")
    if n_items <= 0:
        return manifest_count
    return min(n_items, manifest_count)


def _run(command: list[str], *, allow_failure: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    payload = {
        "command": _portable_command(command),
        "returncode": completed.returncode,
        "elapsed_seconds": time.perf_counter() - started,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }
    if completed.returncode != 0 and not allow_failure:
        raise RuntimeError(json.dumps(payload, indent=2))
    return payload


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} did not contain a JSON object")
    return cast(dict[str, Any], payload)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _budget(phases: list[str]) -> dict[str, float]:
    low = sum(PHASE_ESTIMATES_HOURS[phase][0] for phase in phases)
    high = sum(PHASE_ESTIMATES_HOURS[phase][1] for phase in phases)
    return {"low_hours": low, "high_hours": high}


def _format_group_keep_rates(rates: dict[str, float]) -> str:
    return ",".join(f"{group}={rate:.6g}" for group, rate in sorted(rates.items()))


def _gemma_admission_commands(
    *,
    artifact_dir: Path,
    manifest: Path,
    model_path: Path,
    frame_count: int,
    n_items: int,
    rss_guard_mb: int,
    mlx_memory_limit_gb: float,
    prefill_step_size: int,
    label: str,
) -> list[list[str]]:
    jsonl_path = artifact_dir / f"{label}.jsonl"
    summary_path = artifact_dir / f"{label}_summary.json"
    analysis_path = artifact_dir / f"{label}_analysis.json"
    run_command = [
        sys.executable,
        "scripts/run_novelty_pruning_gemma.py",
        "--manifest",
        str(manifest),
        "--frame-count",
        str(frame_count),
        "--anchor-arm",
        "gemma_structural",
        "--keep-rate",
        "0.5",
        "--prune-placeholders",
        "rlt",
        "--prefill-step-size",
        str(prefill_step_size),
        "--model-path",
        str(model_path),
        "--rss-guard-mb",
        str(rss_guard_mb),
        "--mlx-memory-limit-gb",
        f"{mlx_memory_limit_gb:.6g}",
        "--n-warmup",
        "1",
        "--arm-order",
        "abba",
        "--resume",
        "--output",
        str(jsonl_path),
        "--summary",
        str(summary_path),
    ]
    if n_items > 0:
        run_command.extend(["--n-items", str(n_items)])
    analyze_command = [
        sys.executable,
        "scripts/analyze_gemma_admission.py",
        "--jsonl",
        str(jsonl_path),
        "--summary-json",
        str(summary_path),
        "--output",
        str(analysis_path),
        "--cell-type",
        "h3b_admission",
        "--bucket-min-n",
        "1",
        "--timing-min-n",
        "5",
        "--n-bootstrap",
        "500",
    ]
    return [run_command, analyze_command]


def _prefill_kernel_benchmark_command(
    *, artifact_dir: Path, model_path: Path, rss_guard_mb: int
) -> list[str]:
    return [
        sys.executable,
        "scripts/benchmark_mlx_vlm_prefill_kernel.py",
        "--model-path",
        str(model_path),
        "--warm-all-shapes",
        "--shuffle",
        "--rss-guard-mb",
        str(rss_guard_mb),
        "--output",
        str(artifact_dir / "prefill_kernel_microbench.json"),
    ]


def _cvision_commands(
    *,
    artifact_dir: Path,
    manifest: Path,
    model_path: Path,
    frame_count: int,
    n_items: int,
    rss_guard_mb: int,
    mlx_memory_limit_gb: float,
    label: str,
    expected_items: int,
    score_mode: str = "rlt_topk",
    keep_rate: float = 0.5,
    dense_source_label: str | None = None,
    include_dense_command: bool = True,
    parse_failure_max_fraction: float = 0.30,
    bucket_e2e_min_n: int = 5,
    ceiling_tolerance: float = 0.07,
) -> list[list[str]]:
    dense_label = dense_source_label or label
    dense_jsonl = artifact_dir / f"{dense_label}_dense.jsonl"
    dense_summary = artifact_dir / f"{dense_label}_dense_summary.json"
    sparse_jsonl = artifact_dir / f"{label}_{score_mode}.jsonl"
    sparse_summary = artifact_dir / f"{label}_{score_mode}_summary.json"
    analysis = artifact_dir / f"{label}_analysis.json"
    paired = artifact_dir / f"{label}_paired.jsonl"
    base = [
        sys.executable,
        "scripts/run_phase1_63G_gemma_track_b.py",
        "--manifest",
        str(manifest),
        "--frame-count",
        str(frame_count),
        "--max-tokens",
        "32",
        "--model-path",
        str(model_path),
        "--rss-guard-mb",
        str(rss_guard_mb),
        "--mlx-memory-limit-gb",
        f"{mlx_memory_limit_gb:.6g}",
        "--resume",
        "--allow-dirty",
        "--warmup-items",
        "3",
    ]
    dense = [
        *base,
        "--vision-tower-keep-rate",
        "1.0",
        "--output",
        str(dense_jsonl),
        "--summary",
        str(dense_summary),
    ]
    sparse = [
        *base,
        "--vision-tower-keep-rate",
        f"{keep_rate:.6g}",
        "--vision-tower-score-mode",
        score_mode,
        "--output",
        str(sparse_jsonl),
        "--summary",
        str(sparse_summary),
    ]
    if n_items > 0:
        dense.extend(["--n-items", str(n_items)])
        sparse.extend(["--n-items", str(n_items)])
    analyze = [
        sys.executable,
        "scripts/analyze_phase1_63_track_b_sparse.py",
        "--dense-jsonl",
        str(dense_jsonl),
        "--sparse-jsonl",
        str(sparse_jsonl),
        "--dense-summary",
        str(dense_summary),
        "--sparse-summary",
        str(sparse_summary),
        "--output",
        str(analysis),
        "--paired-items",
        str(paired),
        "--expected-items",
        str(expected_items),
        "--sparse-execution-scope",
        (
            "Gemma C-VISION sparse execution with fixed-K token scoring "
            f"({score_mode}); scatter-back preserves prompt geometry."
        ),
        "--require-schema-version",
        GEMMA_TRACK_B_SCHEMA_VERSION,
        "--require-scorer-timings",
        "--parse-failure-max-fraction",
        f"{parse_failure_max_fraction:.6g}",
        "--bucket-e2e-min-n",
        str(bucket_e2e_min_n),
        "--ceiling-tolerance",
        f"{ceiling_tolerance:.6g}",
    ]
    return ([dense] if include_dense_command else []) + [sparse, analyze]


def _gemma_composition_commands(
    *,
    artifact_dir: Path,
    manifest: Path,
    model_path: Path,
    frame_count: int,
    n_items: int,
    rss_guard_mb: int,
    mlx_memory_limit_gb: float,
    label: str,
    prefill_step_size: int = DEFAULT_COMPOSITION_PREFILL_STEP_SIZE,
    vision_keep_rate: float = 0.5,
    group_keep_rates: dict[str, float] | None = None,
    group_vision_keep_rates: dict[str, float] | None = None,
) -> list[list[str]]:
    jsonl_path = artifact_dir / f"{label}.jsonl"
    summary_path = artifact_dir / f"{label}_summary.json"
    analysis_path = artifact_dir / f"{label}_analysis.json"
    run_command = [
        sys.executable,
        "scripts/run_novelty_pruning_gemma.py",
        "--manifest",
        str(manifest),
        "--frame-count",
        str(frame_count),
        "--anchor-arm",
        "gemma_structural",
        "--keep-rate",
        "0.5",
        "--prune-placeholders",
        "rlt",
        "--prefill-step-size",
        str(prefill_step_size),
        "--vision-tower-keep-rate",
        f"{vision_keep_rate:.6g}",
        "--vision-tower-score-mode",
        "rlt_topk",
        "--model-path",
        str(model_path),
        "--rss-guard-mb",
        str(rss_guard_mb),
        "--mlx-memory-limit-gb",
        f"{mlx_memory_limit_gb:.6g}",
        "--n-warmup",
        "1",
        "--arm-order",
        "abba",
        "--resume",
        "--output",
        str(jsonl_path),
        "--summary",
        str(summary_path),
    ]
    if n_items > 0:
        run_command.extend(["--n-items", str(n_items)])
    if group_keep_rates:
        run_command.extend(["--group-keep-rates", _format_group_keep_rates(group_keep_rates)])
    if group_vision_keep_rates:
        run_command.extend(
            ["--group-vision-keep-rates", _format_group_keep_rates(group_vision_keep_rates)]
        )
    analyze_command = [
        sys.executable,
        "scripts/analyze_gemma_admission.py",
        "--jsonl",
        str(jsonl_path),
        "--summary-json",
        str(summary_path),
        "--output",
        str(analysis_path),
        "--cell-type",
        "h3b_admission",
        "--bucket-min-n",
        "1",
        "--timing-min-n",
        "5",
        "--n-bootstrap",
        "500",
    ]
    return [run_command, analyze_command]


def _gemma_full_composition_commands(
    *,
    artifact_dir: Path,
    manifest: Path,
    model_path: Path,
    frame_count: int,
    n_items: int,
    expected_items: int,
    rss_guard_mb: int,
    mlx_memory_limit_gb: float,
    benchmark: str,
    prefill_step_size: int = DEFAULT_COMPOSITION_PREFILL_STEP_SIZE,
    vision_keep_rate: float = 0.5,
    label: str | None = None,
    dense_source_label: str | None = None,
    include_dense_command: bool = True,
    composed_keep_rate: float = 0.5,
    composed_prune_placeholders: str = "rlt",
    vision_score_mode: str = "rlt_topk",
    vision_static_floor_stride: int | None = None,
    vision_random_seed: int | None = None,
    group_prune_placeholders: dict[str, str] | None = None,
    group_keep_rates: dict[str, float] | None = None,
    group_vision_keep_rates: dict[str, float] | None = None,
) -> list[list[str]]:
    if label is None:
        dense_jsonl = artifact_dir / f"full_composition_dense_{benchmark}.jsonl"
        dense_summary = artifact_dir / f"full_composition_dense_{benchmark}_summary.json"
        composed_jsonl = artifact_dir / f"full_composition_rlt_{benchmark}.jsonl"
        composed_summary = artifact_dir / f"full_composition_rlt_{benchmark}_summary.json"
        analysis_path = artifact_dir / f"full_composition_rlt_{benchmark}_analysis.json"
        paired_path = artifact_dir / f"full_composition_rlt_{benchmark}_paired.jsonl"
    else:
        dense_label = dense_source_label or label
        dense_jsonl = artifact_dir / f"{dense_label}_dense.jsonl"
        dense_summary = artifact_dir / f"{dense_label}_dense_summary.json"
        composed_jsonl = artifact_dir / f"{label}_composed.jsonl"
        composed_summary = artifact_dir / f"{label}_composed_summary.json"
        analysis_path = artifact_dir / f"{label}_analysis.json"
        paired_path = artifact_dir / f"{label}_paired.jsonl"
    base = [
        sys.executable,
        "scripts/run_novelty_pruning_gemma.py",
        "--manifest",
        str(manifest),
        "--frame-count",
        str(frame_count),
        "--anchor-arm",
        "gemma_structural",
        "--prefill-step-size",
        str(prefill_step_size),
        "--model-path",
        str(model_path),
        "--rss-guard-mb",
        str(rss_guard_mb),
        "--mlx-memory-limit-gb",
        f"{mlx_memory_limit_gb:.6g}",
        "--n-warmup",
        "1",
        "--arm-order",
        "abba",
        "--resume",
    ]
    dense = [
        *base,
        "--keep-rate",
        "1.0",
        "--prune-placeholders",
        "none",
        "--vision-tower-keep-rate",
        "1.0",
        "--output",
        str(dense_jsonl),
        "--summary",
        str(dense_summary),
    ]
    composed = [
        *base,
        "--keep-rate",
        f"{composed_keep_rate:.6g}",
        "--prune-placeholders",
        composed_prune_placeholders,
        "--vision-tower-keep-rate",
        f"{vision_keep_rate:.6g}",
        "--vision-tower-score-mode",
        vision_score_mode,
        "--output",
        str(composed_jsonl),
        "--summary",
        str(composed_summary),
    ]
    if vision_static_floor_stride is not None:
        composed.extend(["--vision-static-floor-stride", str(vision_static_floor_stride)])
    if vision_random_seed is not None:
        composed.extend(["--vision-random-seed", str(vision_random_seed)])
    if n_items > 0:
        dense.extend(["--n-items", str(n_items)])
        composed.extend(["--n-items", str(n_items)])
    if group_keep_rates:
        composed.extend(["--group-keep-rates", _format_group_keep_rates(group_keep_rates)])
    if group_prune_placeholders:
        composed.extend(
            [
                "--group-prune-placeholders",
                ",".join(
                    f"{group}={mode}" for group, mode in sorted(group_prune_placeholders.items())
                ),
            ]
        )
    if group_vision_keep_rates:
        composed.extend(
            ["--group-vision-keep-rates", _format_group_keep_rates(group_vision_keep_rates)]
        )
    analyze = [
        sys.executable,
        "scripts/analyze_gemma_full_composition.py",
        "--dense-jsonl",
        str(dense_jsonl),
        "--composed-jsonl",
        str(composed_jsonl),
        "--dense-source",
        "composed-jsonl-same-run",
        "--output",
        str(analysis_path),
        "--paired-items",
        str(paired_path),
        "--expected-items",
        str(expected_items),
        "--bucket-min-n",
        "5",
        "--n-bootstrap",
        "500",
    ]
    commands = [composed, analyze]
    if include_dense_command:
        commands.insert(0, dense)
    return commands


def _gemma_full_composition_combined_analysis_command(
    *,
    artifact_dir: Path,
    dense_jsonls: list[Path],
    composed_jsonls: list[Path],
    expected_items: int,
    output_label: str,
) -> list[str]:
    output = artifact_dir / f"{output_label}_analysis.json"
    paired = artifact_dir / f"{output_label}_paired.jsonl"
    command = [
        sys.executable,
        "scripts/analyze_gemma_full_composition.py",
    ]
    for dense_jsonl in dense_jsonls:
        command.extend(["--dense-jsonl", str(dense_jsonl)])
    for composed_jsonl in composed_jsonls:
        command.extend(["--composed-jsonl", str(composed_jsonl)])
    command.extend(["--dense-source", "composed-jsonl-same-run"])
    command.extend(
        [
            "--output",
            str(output),
            "--paired-items",
            str(paired),
            "--expected-items",
            str(expected_items),
            "--bucket-min-n",
            "10",
            "--n-bootstrap",
            "1000",
        ]
    )
    return command


def _run_command_group(
    commands: list[list[str]], *, allow_failure: bool = True
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for command in commands:
        result = _run(command, allow_failure=True)
        results.append(result)
        if int(result["returncode"]) != 0:
            if not allow_failure:
                raise RuntimeError(json.dumps(result, indent=2))
            break
    return results


def _has_failed(results: list[dict[str, Any]]) -> bool:
    return any(int(result["returncode"]) != 0 for result in results)


def _failure_decision(
    *,
    phase: str,
    results: list[dict[str, Any]],
    skipped: list[str] | None = None,
) -> dict[str, Any]:
    failed = [result for result in results if int(result["returncode"]) != 0]
    return {
        "decision": "stop" if skipped is None else "skip",
        "reason": f"{phase}_command_failed",
        "phase": phase,
        "failed_command": failed[0]["command"] if failed else None,
        "returncode": failed[0]["returncode"] if failed else None,
        **({"skip": skipped} if skipped is not None else {}),
    }


def _read_analysis_after_success(
    *,
    results: list[dict[str, Any]],
    path: Path,
    phase: str,
    decisions: list[dict[str, Any]],
    skipped: list[str] | None = None,
) -> dict[str, Any] | None:
    if _has_failed(results):
        decisions.append(_failure_decision(phase=phase, results=results, skipped=skipped))
        return None
    if not path.exists():
        decisions.append(
            {
                "decision": "stop" if skipped is None else "skip",
                "reason": f"{phase}_analysis_missing",
                "phase": phase,
                "missing_path": str(path),
                **({"skip": skipped} if skipped is not None else {}),
            }
        )
        return None
    return _read_json(path)


def _phase_passed_cvision(analysis: dict[str, Any]) -> bool:
    # pass_format is informational here: some dense baselines have parse
    # failures independent of sparse execution. Absolute parse-rate and
    # ceiling-model diagnostics are persisted but do not block follow-up
    # execution because dense baseline format failures and non-Amdahl decode
    # covariance produced false cancellations in the completed n=30 series.
    return bool(
        analysis.get("pass_complete_pairing")
        and analysis.get("pass_fidelity")
        and analysis.get("pass_sparse_vision")
        and analysis.get("pass_e2e_positive")
        and analysis.get("pass_bucket_e2e_positive")
        and analysis.get("pass_parse_failure_delta")
    )


def _phase_passed_prefill_same_path(analysis: dict[str, Any]) -> bool:
    speedup = analysis.get("e2e_speedup_dense_over_pruned")
    return bool(
        analysis.get("total_prefill_reduction_ms", 0.0) > 0.0
        and isinstance(speedup, (int, float))
        and float(speedup) > 1.0
    )


def _phase_passed_full_composition(analysis: dict[str, Any]) -> bool:
    summary = analysis.get("summary")
    return bool(
        isinstance(summary, dict)
        and summary.get("pass_fidelity")
        and summary.get("pass_e2e_positive")
        and summary.get("pass_parse_failure_delta")
        and summary.get("pass_bucket_quality_and_e2e")
    )


def _query_q0b_gate(analyses: dict[str, Any], benchmarks: list[str]) -> dict[str, Any]:
    required_suffixes = (
        "dense_equivalent",
        "admission_only",
        "cvision_only_{benchmark}_kr050",
        "cvision_only_{benchmark}_kr100",
        "full_{benchmark}_kr050",
        "full_{benchmark}_kr070",
        "full_{benchmark}_kr085",
        "full_{benchmark}_kr100",
    )
    expected_cell_types = {
        "dense_equivalent": "dense_equivalent",
        "admission_only": "rlt_admission_only",
        "cvision_only_{benchmark}_kr050": "rlt_cvision_only",
        "cvision_only_{benchmark}_kr100": "rlt_cvision_only",
        "full_{benchmark}_kr050": "rlt_admission_plus_rlt_cvision",
        "full_{benchmark}_kr070": "rlt_admission_plus_rlt_cvision",
        "full_{benchmark}_kr085": "rlt_admission_plus_rlt_cvision",
        "full_{benchmark}_kr100": "rlt_admission_plus_rlt_cvision",
    }
    per_benchmark: dict[str, Any] = {}
    proceed = True
    for benchmark in benchmarks:
        missing: list[str] = []
        failed: list[str] = []
        cell_mismatch: list[dict[str, str]] = []
        summaries: dict[str, dict[str, Any]] = {}
        for suffix_template in required_suffixes:
            suffix = suffix_template.format(benchmark=benchmark)
            label = (
                f"query_q0b_{suffix}_{benchmark}"
                if suffix
                in {
                    "dense_equivalent",
                    "admission_only",
                }
                else f"query_q0b_{suffix}"
            )
            analysis = analyses.get(label)
            if not isinstance(analysis, dict):
                missing.append(label)
                continue
            summary = analysis.get("summary")
            if not isinstance(summary, dict) or not summary.get("pass_complete_pairing"):
                failed.append(label)
                continue
            expected_cell_type = expected_cell_types[suffix_template]
            actual_cell_type = str(summary.get("cell_type"))
            if actual_cell_type != expected_cell_type:
                cell_mismatch.append(
                    {
                        "label": label,
                        "expected": expected_cell_type,
                        "actual": actual_cell_type,
                    }
                )
            summaries[label] = summary
        dense_label = f"query_q0b_dense_equivalent_{benchmark}"
        dense_summary = summaries.get(dense_label, {})
        dense_equivalence_passed = bool(dense_summary.get("pass_dense_equivalence"))
        benchmark_passed = (
            not missing and not failed and not cell_mismatch and dense_equivalence_passed
        )
        proceed = proceed and benchmark_passed
        full_kr050 = summaries.get(f"query_q0b_full_{benchmark}_kr050", {})
        full_kr100 = summaries.get(f"query_q0b_full_{benchmark}_kr100", {})
        cvision_kr050 = summaries.get(f"query_q0b_cvision_only_{benchmark}_kr050", {})
        cvision_kr100 = summaries.get(f"query_q0b_cvision_only_{benchmark}_kr100", {})
        interpretation = "incomplete"
        if benchmark_passed:
            if not bool(full_kr050.get("pass_fidelity")) and bool(full_kr100.get("pass_fidelity")):
                interpretation = "budget_bound_candidate"
            elif not bool(cvision_kr100.get("pass_fidelity")):
                interpretation = "cvision_oracle_not_dense_equivalent"
            elif not bool(cvision_kr050.get("pass_fidelity")):
                interpretation = "cvision_budget_or_operator_candidate"
            elif not bool(full_kr100.get("pass_fidelity")):
                interpretation = "admission_or_interaction_candidate"
            else:
                interpretation = "no_q0b_quality_failure"
        per_benchmark[benchmark] = {
            "passed": benchmark_passed,
            "dense_equivalence_passed": dense_equivalence_passed,
            "missing": missing,
            "failed": failed,
            "cell_mismatch": cell_mismatch,
            "interpretation": interpretation,
            "full_kr050_accuracy_delta": full_kr050.get("accuracy_delta_composed_minus_dense"),
            "full_kr100_accuracy_delta": full_kr100.get("accuracy_delta_composed_minus_dense"),
            "cvision_kr050_accuracy_delta": cvision_kr050.get(
                "accuracy_delta_composed_minus_dense"
            ),
            "cvision_kr100_accuracy_delta": cvision_kr100.get(
                "accuracy_delta_composed_minus_dense"
            ),
        }
    return {
        "benchmarks": benchmarks,
        "by_benchmark": per_benchmark,
        "proceed_to_q1": proceed,
    }


def _target_accuracy_delta(summary: dict[str, Any], benchmark: str) -> float:
    target_groups = {
        "mvbench": {"moving_attribute", "object_interaction"},
    }.get(benchmark)
    if not target_groups:
        return float(summary.get("accuracy_delta_composed_minus_dense", 0.0))
    by_group = summary.get("by_group")
    if not isinstance(by_group, dict):
        return float(summary.get("accuracy_delta_composed_minus_dense", 0.0))
    dense_correct = 0.0
    composed_correct = 0.0
    n_total = 0
    for group in target_groups:
        group_summary = by_group.get(group)
        if not isinstance(group_summary, dict):
            continue
        n = int(group_summary.get("n", 0))
        dense_correct += n * float(group_summary.get("dense_accuracy", 0.0))
        composed_correct += n * float(group_summary.get("composed_accuracy", 0.0))
        n_total += n
    if n_total == 0:
        return float(summary.get("accuracy_delta_composed_minus_dense", 0.0))
    return (composed_correct / n_total) - (dense_correct / n_total)


def _query_q1_verdict(analyses: dict[str, Any], benchmarks: list[str]) -> dict[str, Any]:
    typed_suffixes = ("static_floor_s4",)
    matched_control_suffixes = (
        "redundancy_kr050",
        "fixed_uniform",
        "random_seed11",
        "random_seed23",
        "random_seed37",
    )
    budget_control_suffixes = ("redundancy_kr070",)
    by_benchmark: dict[str, Any] = {}
    proceed = True
    for benchmark in benchmarks:
        rows: dict[str, dict[str, Any]] = {}
        missing: list[str] = []
        for suffix in (*typed_suffixes, *matched_control_suffixes, *budget_control_suffixes):
            label = f"query_q1_{benchmark}_{suffix}"
            analysis = analyses.get(label)
            summary = analysis.get("summary") if isinstance(analysis, dict) else None
            if not isinstance(summary, dict):
                missing.append(label)
                continue
            rows[suffix] = {
                "accuracy_delta": float(summary.get("accuracy_delta_composed_minus_dense", 0.0)),
                "target_accuracy_delta": _target_accuracy_delta(summary, benchmark),
                "e2e_speedup": float(summary.get("e2e_speedup_dense_over_composed", 0.0)),
                "pass_fidelity": bool(summary.get("pass_fidelity")),
                "pass_parse_failure_delta": bool(summary.get("pass_parse_failure_delta")),
            }
        matched_controls = [rows[suffix] for suffix in matched_control_suffixes if suffix in rows]
        typed_rows = [rows[suffix] for suffix in typed_suffixes if suffix in rows]
        best_control_delta = max(
            (row["target_accuracy_delta"] for row in matched_controls),
            default=float("-inf"),
        )
        best_typed = max(
            typed_rows,
            key=lambda row: (row["target_accuracy_delta"], row["e2e_speedup"]),
            default=None,
        )
        typed_beats_controls = (
            best_typed is not None
            and best_typed["target_accuracy_delta"] > best_control_delta + 1e-12
            and best_typed["pass_parse_failure_delta"]
            and best_typed["e2e_speedup"] > 1.0
        )
        benchmark_passed = not missing and typed_beats_controls
        proceed = proceed and benchmark_passed
        by_benchmark[benchmark] = {
            "passed": benchmark_passed,
            "missing": missing,
            "best_matched_control_target_accuracy_delta": (
                None if best_control_delta == float("-inf") else best_control_delta
            ),
            "best_typed_target_accuracy_delta": (
                None if best_typed is None else best_typed["target_accuracy_delta"]
            ),
            "rows": rows,
        }
    return {
        "benchmarks": benchmarks,
        "by_benchmark": by_benchmark,
        "proceed_to_q2_scalar_query_baseline": proceed,
    }


def _query_q1b_followup_verdict(analyses: dict[str, Any]) -> dict[str, Any]:
    """Summarize the narrow post-Q1 diagnostic cells without promoting a planner."""

    benchmark = "mvbench"

    def row(label: str) -> dict[str, Any] | None:
        analysis = analyses.get(label)
        summary = analysis.get("summary") if isinstance(analysis, dict) else None
        if not isinstance(summary, dict):
            return None
        return {
            "accuracy_delta": float(summary.get("accuracy_delta_composed_minus_dense", 0.0)),
            "target_accuracy_delta": _target_accuracy_delta(summary, benchmark),
            "e2e_speedup": float(summary.get("e2e_speedup_dense_over_composed", 0.0)),
            "pass_fidelity": bool(summary.get("pass_fidelity")),
            "pass_parse_failure_delta": bool(summary.get("pass_parse_failure_delta")),
            "bucket_failures": summary.get("bucket_failures", []),
        }

    labels = {
        "q1_random_seed11": "query_q1_mvbench_random_seed11",
        "q1_fixed_uniform": "query_q1_mvbench_fixed_uniform",
        "endpoint_anchor": "query_q1b_mvbench_endpoint_anchor",
        "random_seed11_actionloc_dense": "query_q1b_mvbench_random_seed11_actionloc_dense",
        "fixed_uniform_actionloc_dense": "query_q1b_mvbench_fixed_uniform_actionloc_dense",
        "random_seed11_admission_on": "query_q1b_mvbench_random_seed11_admission_on",
        "fixed_uniform_admission_on": "query_q1b_mvbench_fixed_uniform_admission_on",
    }
    rows = {name: row(label) for name, label in labels.items()}
    missing = [name for name, payload in rows.items() if payload is None]
    q1_bases = {
        "random_seed11": rows.get("q1_random_seed11") or {},
        "fixed_uniform": rows.get("q1_fixed_uniform") or {},
    }
    repair_rows = {
        "random_seed11": rows.get("random_seed11_actionloc_dense") or {},
        "fixed_uniform": rows.get("fixed_uniform_actionloc_dense") or {},
    }
    admission_rows = {
        "random_seed11": rows.get("random_seed11_admission_on") or {},
        "fixed_uniform": rows.get("fixed_uniform_admission_on") or {},
    }
    best_base_target_delta = max(
        (
            float(payload.get("target_accuracy_delta", float("-inf")))
            for payload in q1_bases.values()
        ),
        default=float("-inf"),
    )
    best_base_accuracy_delta = max(
        (float(payload.get("accuracy_delta", float("-inf"))) for payload in q1_bases.values()),
        default=float("-inf"),
    )
    coverage_repair_by_control = {
        name: (
            not missing
            and bool(repair.get("pass_parse_failure_delta"))
            and float(repair.get("accuracy_delta", -1.0)) >= float(base.get("accuracy_delta", 0.0))
            and float(repair.get("e2e_speedup", 0.0)) > 1.1
        )
        for name, (base, repair) in {
            key: (q1_bases[key], repair_rows[key]) for key in q1_bases
        }.items()
    }
    admission_preserves_by_control = {
        name: (
            not missing
            and bool(admission.get("pass_parse_failure_delta"))
            and float(admission.get("target_accuracy_delta", -1.0))
            >= float(base.get("target_accuracy_delta", 0.0))
            and float(admission.get("e2e_speedup", 0.0)) > float(base.get("e2e_speedup", 0.0))
        )
        for name, (base, admission) in {
            key: (q1_bases[key], admission_rows[key]) for key in q1_bases
        }.items()
    }
    coverage_repair_has_headroom = (
        not missing
        and any(coverage_repair_by_control.values())
        and max(float(row.get("accuracy_delta", -1.0)) for row in repair_rows.values())
        >= best_base_accuracy_delta
    )
    admission_preserves_best_control = (
        not missing
        and any(admission_preserves_by_control.values())
        and max(float(row.get("target_accuracy_delta", -1.0)) for row in admission_rows.values())
        >= best_base_target_delta
        and max(float(row.get("e2e_speedup", 0.0)) for row in admission_rows.values())
        > max(float(row.get("e2e_speedup", 0.0)) for row in q1_bases.values())
    )
    endpoint_anchor_competitive = (
        not missing
        and rows["endpoint_anchor"] is not None
        and bool(rows["endpoint_anchor"].get("pass_parse_failure_delta"))
        and float(rows["endpoint_anchor"].get("target_accuracy_delta", -1.0))
        >= best_base_target_delta
        and float(rows["endpoint_anchor"].get("e2e_speedup", 0.0)) > 1.0
    )
    return {
        "benchmark": benchmark,
        "missing": missing,
        "rows": rows,
        "best_base_target_accuracy_delta": (
            None if best_base_target_delta == float("-inf") else best_base_target_delta
        ),
        "coverage_repair_by_control": coverage_repair_by_control,
        "coverage_repair_has_headroom": coverage_repair_has_headroom,
        "admission_preserves_by_control": admission_preserves_by_control,
        "admission_preserves_best_control": admission_preserves_best_control,
        "endpoint_anchor_competitive": endpoint_anchor_competitive,
        "paper_feedback": (
            "Q1b is diagnostic only. A positive row motivates a fresh held-out "
            "planner experiment; a negative row keeps query-routing in the appendix."
        ),
    }


def _query_q1c_admission_scheduler_verdict(analyses: dict[str, Any]) -> dict[str, Any]:
    """Summarize exploratory admission-scheduler rows against Q1/Q1b controls."""

    benchmark = "mvbench"

    def row(label: str) -> dict[str, Any] | None:
        analysis = analyses.get(label)
        summary = analysis.get("summary") if isinstance(analysis, dict) else None
        if not isinstance(summary, dict):
            return None
        return {
            "accuracy_delta": float(summary.get("accuracy_delta_composed_minus_dense", 0.0)),
            "target_accuracy_delta": _target_accuracy_delta(summary, benchmark),
            "e2e_speedup": float(summary.get("e2e_speedup_dense_over_composed", 0.0)),
            "pass_fidelity": bool(summary.get("pass_fidelity")),
            "pass_parse_failure_delta": bool(summary.get("pass_parse_failure_delta")),
            "bucket_failures": summary.get("bucket_failures", []),
        }

    labels = {
        "q1_random_seed11": "query_q1_mvbench_random_seed11",
        "q1b_random_seed11_actionloc_dense": "query_q1b_mvbench_random_seed11_actionloc_dense",
        "q1c_random_seed11_no_admission_baseline": (
            "query_q1c_mvbench_random_seed11_no_admission_baseline"
        ),
        "q1c_random_seed11_safe_admission": "query_q1c_mvbench_random_seed11_safe_admission",
        "q1c_random_seed11_moving_attribute_safe_admission": (
            "query_q1c_mvbench_random_seed11_moving_attribute_safe_admission"
        ),
        "q1c_random_seed11_safe_admission_actionloc_dense": (
            "query_q1c_mvbench_random_seed11_safe_admission_actionloc_dense"
        ),
    }
    rows = {name: row(label) for name, label in labels.items()}
    missing = [name for name, payload in rows.items() if payload is None]
    base = rows.get("q1_random_seed11") or {}
    actionloc_base = rows.get("q1b_random_seed11_actionloc_dense") or {}
    q1c_baseline = rows.get("q1c_random_seed11_no_admission_baseline") or base
    safe = rows.get("q1c_random_seed11_safe_admission") or {}
    moving_attribute_safe = rows.get("q1c_random_seed11_moving_attribute_safe_admission") or {}
    safe_actionloc = rows.get("q1c_random_seed11_safe_admission_actionloc_dense") or {}

    def improves(candidate: dict[str, Any], baseline: dict[str, Any]) -> bool:
        return (
            not missing
            and bool(candidate.get("pass_fidelity"))
            and bool(candidate.get("pass_parse_failure_delta"))
            and float(candidate.get("accuracy_delta", -1.0))
            >= float(baseline.get("accuracy_delta", 0.0))
            and float(candidate.get("target_accuracy_delta", -1.0))
            >= float(baseline.get("target_accuracy_delta", 0.0))
            and float(candidate.get("e2e_speedup", 0.0)) > float(baseline.get("e2e_speedup", 0.0))
        )

    return {
        "benchmark": benchmark,
        "missing": missing,
        "rows": rows,
        "baseline_for_q1c_admission": (
            "query_q1c_mvbench_random_seed11_no_admission_baseline"
            if rows.get("q1c_random_seed11_no_admission_baseline")
            else "query_q1_mvbench_random_seed11"
        ),
        "safe_admission_beats_q1_random": improves(safe, base),
        "safe_admission_beats_q1c_baseline": improves(safe, q1c_baseline),
        "moving_attribute_safe_admission_beats_q1_random": improves(moving_attribute_safe, base),
        "moving_attribute_safe_admission_beats_q1c_baseline": improves(
            moving_attribute_safe, q1c_baseline
        ),
        "safe_admission_actionloc_dense_beats_q1b_actionloc_dense": improves(
            safe_actionloc, actionloc_base
        ),
        "proceed_to_holdout_admission_scheduler": improves(safe, q1c_baseline)
        or improves(moving_attribute_safe, q1c_baseline)
        or improves(safe_actionloc, actionloc_base),
        "paper_feedback": (
            "Q1c is still exploratory dev evidence. A positive row authorizes a "
            "single held-out admission-scheduler confirmation, not a standalone "
            "planner claim."
        ),
    }


def _paper_feedback(*, analyses: dict[str, Any], decisions: list[dict[str, Any]]) -> dict[str, Any]:
    """Machine-readable editor notes from the autonomous supervisor."""

    q0b_gate = analyses.get("query_routing_q0b_gate")
    q0b_ready = isinstance(q0b_gate, dict) and bool(q0b_gate.get("proceed_to_q1"))
    q1_labels = sorted(label for label in analyses if label.startswith("query_q1_"))
    q1_verdict = analyses.get("query_routing_q1_verdict")
    q1_ready = isinstance(q1_verdict, dict) and bool(
        q1_verdict.get("proceed_to_q2_scalar_query_baseline")
    )
    q1c_verdict = analyses.get("query_routing_q1c_admission_scheduler_verdict")
    q1c_ready = isinstance(q1c_verdict, dict) and bool(
        q1c_verdict.get("proceed_to_holdout_admission_scheduler")
    )
    failed_reasons = sorted(
        {
            str(decision.get("reason"))
            for decision in decisions
            if decision.get("decision") in {"skip", "stop", "contract"}
        }
    )
    allowed_claims: list[str] = []
    disallowed_claims: list[str] = [
        (
            "Do not claim query-aware visual routing beats scalar-query allocation until "
            "Q2b/QuoTA-style controls run."
        ),
        "Do not claim M5 scale transfer until an M5 n=1 smoke and winner-only confirmation run.",
    ]
    if q0b_ready:
        allowed_claims.append(
            "Q0b dense-equivalence passed for the requested benchmarks; "
            "Q1 operator ablations may run."
        )
    elif isinstance(q0b_gate, dict):
        disallowed_claims.append(
            "Q0b dense-equivalence failed or was incomplete; query-routing "
            "operator results are not interpretable."
        )
    if q1_labels:
        if q1_ready:
            allowed_claims.append(
                "Q1 matched-budget operator controls have analyzer outputs and a "
                "typed operator beat fixed/random/redundancy controls on the "
                "preregistered target; proceed to Q2b scalar-query controls."
            )
        else:
            disallowed_claims.append(
                "Q1 outputs cannot justify proceed-to-Q2 unless the aggregate "
                "matched-budget verdict beats fixed/random/redundancy controls."
            )
    if q1c_ready:
        allowed_claims.append(
            "Q1c admission-scheduler rows beat their preregistered dev control; "
            "run one held-out confirmation before claiming a planner win."
        )
    return {
        "allowed_claims": allowed_claims,
        "disallowed_claims": disallowed_claims,
        "failed_or_skipped_reasons": failed_reasons,
        "reviewer_objections_addressed": [
            "prompt-admission and C-VISION denominators are separated",
            "dense-equivalence harness gate is explicit",
            "fixed/random/higher-K controls are first-class Q1 arms",
            "paper wording is constrained until scalar-query controls run",
        ],
    }


def _parse_keep_rates(raw: str) -> list[float]:
    rates = [float(part.strip()) for part in raw.replace(",", " ").split() if part.strip()]
    if not rates:
        raise ValueError("at least one keep rate is required")
    for rate in rates:
        if not (0.0 < rate <= 1.0):
            raise ValueError(f"keep rates must be in (0, 1], got {rate}")
    return rates


def _parse_benchmarks(raw: str) -> list[str]:
    allowed = {"videomme", "tomato", "mvbench"}
    values = [part.strip() for part in raw.split(",") if part.strip()]
    if not values:
        raise SystemExit("--query-routing-benchmarks must name at least one benchmark")
    unknown = sorted(set(values) - allowed)
    if unknown:
        raise SystemExit(f"unknown query-routing benchmark(s): {', '.join(unknown)}")
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--gemma-model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--videomme-manifest", type=Path, default=DEFAULT_VIDEOMME_MANIFEST)
    parser.add_argument("--smoke-manifest", type=Path, default=DEFAULT_SMOKE_MANIFEST)
    parser.add_argument("--tomato-manifest", type=Path, default=DEFAULT_TOMATO_MANIFEST)
    parser.add_argument("--mvbench-manifest", type=Path, default=DEFAULT_MVBENCH_MANIFEST)
    parser.add_argument(
        "--videomme-holdout-manifest",
        type=Path,
        default=DEFAULT_VIDEOMME_HOLDOUT_MANIFEST,
    )
    parser.add_argument(
        "--tomato-holdout-manifest",
        type=Path,
        default=DEFAULT_TOMATO_HOLDOUT_MANIFEST,
    )
    parser.add_argument(
        "--mvbench-holdout-manifest",
        type=Path,
        default=DEFAULT_MVBENCH_HOLDOUT_MANIFEST,
    )
    parser.add_argument("--frame-count", type=int, default=8)
    parser.add_argument("--rss-guard-mb", type=int, default=9000)
    parser.add_argument(
        "--mlx-memory-limit-gb",
        type=float,
        default=12.0,
        help=(
            "MLX allocator cap passed to Track-B C-VISION subprocesses. "
            "Use a larger value or 0 on high-memory hosts such as the M5 "
            "128GB machine; local default stays conservative for 16GB Macs."
        ),
    )
    parser.add_argument("--prefill-diagnostic-n-items", type=int, default=30)
    parser.add_argument("--cvision-n-items", type=int, default=30)
    parser.add_argument("--cooldown-after-microbench-seconds", type=float, default=180.0)
    parser.add_argument("--run-prefill-diagnostics", action="store_true")
    parser.add_argument("--run-cvision-rlt", action="store_true")
    parser.add_argument("--run-cvision-expansion", action="store_true")
    parser.add_argument(
        "--run-max-min-triangulation",
        action="store_true",
        help=(
            "After RLT-as-C-VISION passes VideoMME, run max_min_diversity on the "
            "same manifests for head-to-head interpretation."
        ),
    )
    parser.add_argument(
        "--run-magnitude-head-to-head",
        action="store_true",
        help=(
            "Run the existing MLX-native magnitude scorer on the same three "
            "manifests. This closes the scorer-comparison triangle: dense, "
            "RLT, max-min, and magnitude."
        ),
    )
    parser.add_argument(
        "--run-magnitude-valid-head-to-head",
        action="store_true",
        help=(
            "Run the hidden-state magnitude scorer with K budgeted over valid "
            "Gemma encoder positions. This is the fair control for the old "
            "padded-row magnitude scorer."
        ),
    )
    parser.add_argument(
        "--run-composition-incremental",
        action="store_true",
        help=(
            "Run RLT prompt admission on top of RLT-as-C-VISION at "
            "the composition prefill step size. This measures incremental "
            "composition, not a full dense-vs-composed baseline."
        ),
    )
    parser.add_argument(
        "--run-composition-direct",
        action="store_true",
        help=(
            "Run direct dense baseline versus RLT-as-C-VISION plus RLT prompt "
            "admission at the same prefill step size. This is the paper-facing "
            "full-stack composition cell."
        ),
    )
    parser.add_argument(
        "--run-composition-rescue",
        action="store_true",
        help=(
            "Run bucket-specific keep-rate rescue cells after the direct "
            "composition measurement. The policy raises K only in groups that "
            "failed the round-18 direct-composition quality gate."
        ),
    )
    parser.add_argument(
        "--run-composition-holdout",
        action="store_true",
        help=(
            "Run direct dense-vs-composed cells on disjoint holdout manifests. "
            "This is the replication path for the paper-facing composition claim."
        ),
    )
    parser.add_argument(
        "--run-composition-rescue-holdout",
        action="store_true",
        help=(
            "Run the bucket-specific rescue policy on disjoint holdout manifests. "
            "Skips a benchmark if its base holdout direct-composition gate passes."
        ),
    )
    parser.add_argument(
        "--run-moving-attribute-bracket",
        action="store_true",
        help=(
            "Run an MVBench full-composition bracket cell with moving_attribute "
            "at kr=1.0 and object_interaction at the known rescue kr=0.85. "
            "This distinguishes budget-bound failure from structural query need."
        ),
    )
    parser.add_argument(
        "--run-moving-attribute-holdout-bracket",
        action="store_true",
        help=(
            "Run the same MVBench moving_attribute kr=1.0 bracket on the disjoint "
            "holdout manifest. This is an optional standalone diagnostic; interpret "
            "it against the existing dev bracket and holdout rescue rows before "
            "claiming whether the dev failure is slice-specific."
        ),
    )
    parser.add_argument(
        "--run-composition-combined-analysis",
        action="store_true",
        help=(
            "After dev and holdout direct-composition artifacts exist, run pooled "
            "n=60 analyzer passes for direct and rescue composition claims."
        ),
    )
    parser.add_argument(
        "--composition-prefill-step-size",
        type=int,
        default=DEFAULT_COMPOSITION_PREFILL_STEP_SIZE,
        help=(
            "Prefill step size for incremental composition cells. The default "
            "keeps typical pruned prompts on the chunked prefill path to avoid "
            "the MLX-VLM single-shot substrate trap observed near 1500 tokens."
        ),
    )
    parser.add_argument(
        "--run-keep-rate-sweep",
        action="store_true",
        help="Run an RLT-as-C-VISION keep-rate Pareto sweep on one benchmark.",
    )
    parser.add_argument(
        "--run-query-routing-q0b",
        action="store_true",
        help=(
            "Run the query-routing Q0b 2x2/oracle probe: dense-equivalent, "
            "admission-only, C-VISION-only, and full composition arms. This is "
            "the publish-or-kill gate before Q1 operator ablations."
        ),
    )
    parser.add_argument(
        "--run-query-routing-q1",
        action="store_true",
        help=(
            "Run first-branch matched-budget operator ablations after Q0b dense "
            "equivalence passes. Includes RLT redundancy, higher-K, static floor, "
            "fixed uniform, and preregistered random controls."
        ),
    )
    parser.add_argument(
        "--run-query-routing-q1b-followup",
        action="store_true",
        help=(
            "Run the narrow Q1b follow-up after Q1: endpoint-anchor, admission-on "
            "coverage controls, and action_localization dense fallback. This is a "
            "diagnostic for remaining query-planning headroom, not a planner launch."
        ),
    )
    parser.add_argument(
        "--run-query-routing-q1c-admission-scheduler",
        action="store_true",
        help=(
            "Run the narrow Q1c admission-scheduler follow-up after Q1b. This "
            "keeps C-VISION coverage-first, disables prompt admission by "
            "default, and admits only preregistered low-risk groups."
        ),
    )
    parser.add_argument(
        "--query-routing-benchmarks",
        default="mvbench",
        help=(
            "Comma-separated subset of {videomme,tomato,mvbench} for Q0b/Q1. "
            "Default is mvbench because the query-routing primary endpoint is "
            "the pooled MVBench moving_attribute/object_interaction target."
        ),
    )
    parser.add_argument(
        "--keep-rate-sweep-benchmark",
        choices=("tomato", "mvbench", "videomme"),
        default="tomato",
    )
    parser.add_argument("--cvision-keep-rates", default="0.3,0.5,0.7,0.85")
    parser.add_argument("--max-planned-hours", type=float, default=60.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()

    if args.prefill_diagnostic_n_items < 1:
        raise SystemExit("--prefill-diagnostic-n-items must be positive")
    if args.cvision_n_items < 1:
        raise SystemExit("--cvision-n-items must be positive")
    if args.run_max_min_triangulation and not args.run_cvision_rlt:
        raise SystemExit("--run-max-min-triangulation requires --run-cvision-rlt")
    if args.run_cvision_expansion and not args.run_cvision_rlt:
        raise SystemExit("--run-cvision-expansion requires --run-cvision-rlt")
    if args.run_magnitude_head_to_head and not args.run_cvision_rlt:
        raise SystemExit("--run-magnitude-head-to-head requires --run-cvision-rlt")
    if args.run_magnitude_valid_head_to_head and not args.run_cvision_rlt:
        raise SystemExit("--run-magnitude-valid-head-to-head requires --run-cvision-rlt")
    if args.run_composition_incremental and not args.run_cvision_rlt:
        raise SystemExit("--run-composition-incremental requires --run-cvision-rlt")
    if args.run_composition_direct and not args.run_cvision_rlt:
        raise SystemExit("--run-composition-direct requires --run-cvision-rlt")
    if args.run_composition_rescue and not args.run_cvision_rlt:
        raise SystemExit("--run-composition-rescue requires --run-cvision-rlt")
    if args.run_composition_holdout and not args.run_cvision_rlt:
        raise SystemExit("--run-composition-holdout requires --run-cvision-rlt")
    if args.run_composition_rescue_holdout and not args.run_cvision_rlt:
        raise SystemExit("--run-composition-rescue-holdout requires --run-cvision-rlt")
    if args.run_moving_attribute_bracket and not args.run_cvision_rlt:
        raise SystemExit("--run-moving-attribute-bracket requires --run-cvision-rlt")
    if args.run_moving_attribute_holdout_bracket and not args.run_cvision_rlt:
        raise SystemExit("--run-moving-attribute-holdout-bracket requires --run-cvision-rlt")
    if args.run_composition_combined_analysis and not args.run_cvision_rlt:
        raise SystemExit("--run-composition-combined-analysis requires --run-cvision-rlt")
    if args.run_keep_rate_sweep and not args.run_cvision_rlt:
        raise SystemExit("--run-keep-rate-sweep requires --run-cvision-rlt")
    if args.run_query_routing_q0b and not args.run_cvision_rlt:
        raise SystemExit("--run-query-routing-q0b requires --run-cvision-rlt")
    if args.run_query_routing_q1 and not (args.run_cvision_rlt and args.run_query_routing_q0b):
        raise SystemExit(
            "--run-query-routing-q1 requires --run-cvision-rlt and --run-query-routing-q0b"
        )
    if args.run_query_routing_q1b_followup and not (
        args.run_cvision_rlt and args.run_query_routing_q0b and args.run_query_routing_q1
    ):
        raise SystemExit(
            "--run-query-routing-q1b-followup requires --run-cvision-rlt, "
            "--run-query-routing-q0b, and --run-query-routing-q1"
        )
    if args.run_query_routing_q1c_admission_scheduler and not (
        args.run_cvision_rlt
        and args.run_query_routing_q0b
        and args.run_query_routing_q1
        and args.run_query_routing_q1b_followup
    ):
        raise SystemExit(
            "--run-query-routing-q1c-admission-scheduler requires --run-cvision-rlt, "
            "--run-query-routing-q0b, --run-query-routing-q1, and "
            "--run-query-routing-q1b-followup"
        )
    if args.cooldown_after_microbench_seconds < 0:
        raise SystemExit("--cooldown-after-microbench-seconds must be nonnegative")
    if args.mlx_memory_limit_gb < 0.0:
        raise SystemExit("--mlx-memory-limit-gb must be nonnegative")
    if args.composition_prefill_step_size <= 0:
        raise SystemExit("--composition-prefill-step-size must be positive")
    keep_rates = _parse_keep_rates(args.cvision_keep_rates)
    query_routing_benchmarks = _parse_benchmarks(args.query_routing_benchmarks)
    if args.run_query_routing_q1b_followup and query_routing_benchmarks != ["mvbench"]:
        raise SystemExit("--run-query-routing-q1b-followup currently supports mvbench only")
    if args.run_query_routing_q1c_admission_scheduler and query_routing_benchmarks != ["mvbench"]:
        raise SystemExit(
            "--run-query-routing-q1c-admission-scheduler currently supports mvbench only"
        )
    phases: list[str] = []
    if args.run_prefill_diagnostics:
        phases.append("prefill-kernel-microbench")
        phases.append("prefill-step-1500-n30")
        phases.append("prefill-step-4096-n30")
    if args.run_cvision_rlt:
        phases.extend(["cvision-rlt-smoke", "cvision-rlt-videomme-n30"])
        if args.run_max_min_triangulation:
            phases.append("cvision-maxmin-videomme-n30")
    if args.run_cvision_expansion:
        phases.extend(["cvision-rlt-tomato-n30", "cvision-rlt-mvbench-n30"])
        if args.run_max_min_triangulation:
            phases.extend(["cvision-maxmin-tomato-n30", "cvision-maxmin-mvbench-n30"])
    if args.run_magnitude_head_to_head:
        phases.extend(
            [
                "cvision-magnitude-videomme-n30",
                "cvision-magnitude-tomato-n30",
                "cvision-magnitude-mvbench-n30",
            ]
        )
    if args.run_magnitude_valid_head_to_head:
        phases.extend(
            [
                "cvision-magnitude-valid-videomme-n30",
                "cvision-magnitude-valid-tomato-n30",
                "cvision-magnitude-valid-mvbench-n30",
            ]
        )
    if args.run_composition_incremental:
        phases.extend(
            [
                "composition-rlt-videomme-n30",
                "composition-rlt-tomato-n30",
                "composition-rlt-mvbench-n30",
            ]
        )
    if args.run_composition_direct:
        phases.extend(
            [
                "full-composition-rlt-videomme-n30",
                "full-composition-rlt-tomato-n30",
                "full-composition-rlt-mvbench-n30",
            ]
        )
    if args.run_composition_rescue:
        phases.extend(
            [
                "full-composition-rlt-rescue-videomme-n30",
                "full-composition-rlt-rescue-tomato-n30",
                "full-composition-rlt-rescue-mvbench-n30",
            ]
        )
    if args.run_composition_holdout:
        phases.extend(
            [
                "full-composition-rlt-holdout-videomme-n30",
                "full-composition-rlt-holdout-tomato-n30",
                "full-composition-rlt-holdout-mvbench-n30",
            ]
        )
    if args.run_composition_rescue_holdout:
        phases.extend(
            [
                "full-composition-rlt-rescue-holdout-videomme-n30",
                "full-composition-rlt-rescue-holdout-tomato-n30",
                "full-composition-rlt-rescue-holdout-mvbench-n30",
            ]
        )
    if args.run_moving_attribute_bracket:
        phases.append("full-composition-rlt-mvbench-moving-attribute-kr100-n30")
    if args.run_moving_attribute_holdout_bracket:
        phases.append("full-composition-rlt-holdout-mvbench-moving-attribute-kr100-n30")
    if args.run_composition_combined_analysis:
        phases.extend(
            [
                "full-composition-rlt-combined-videomme-n60-analysis",
                "full-composition-rlt-combined-tomato-n60-analysis",
                "full-composition-rlt-combined-mvbench-n60-analysis",
                "full-composition-rlt-rescue-combined-videomme-n60-analysis",
                "full-composition-rlt-rescue-combined-tomato-n60-analysis",
                "full-composition-rlt-rescue-combined-mvbench-n60-analysis",
            ]
        )
    if args.run_keep_rate_sweep:
        phases.append(f"cvision-kr-sweep-{args.keep_rate_sweep_benchmark}")
    if args.run_query_routing_q0b:
        phases.extend(
            f"query-routing-q0b-{benchmark}-n30" for benchmark in query_routing_benchmarks
        )
    if args.run_query_routing_q1:
        phases.extend(f"query-routing-q1-{benchmark}-n30" for benchmark in query_routing_benchmarks)
    if args.run_query_routing_q1b_followup:
        phases.append("query-routing-q1b-mvbench-n30")
    if args.run_query_routing_q1c_admission_scheduler:
        phases.append("query-routing-q1c-mvbench-n30")
    budget = _budget(phases)
    if budget["high_hours"] > args.max_planned_hours:
        raise SystemExit(
            f"planned high estimate {budget['high_hours']:.1f}h exceeds "
            f"--max-planned-hours {args.max_planned_hours:.1f}h"
        )
    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.summary or args.artifact_dir / "queue_summary.json"
    planned: list[dict[str, Any]] = []

    prefill_kernel_command = _prefill_kernel_benchmark_command(
        artifact_dir=args.artifact_dir,
        model_path=args.gemma_model_path,
        rss_guard_mb=args.rss_guard_mb,
    )
    prefill_1500_commands = _gemma_admission_commands(
        artifact_dir=args.artifact_dir,
        manifest=args.videomme_manifest,
        model_path=args.gemma_model_path,
        frame_count=args.frame_count,
        n_items=args.prefill_diagnostic_n_items,
        rss_guard_mb=args.rss_guard_mb,
        mlx_memory_limit_gb=args.mlx_memory_limit_gb,
        prefill_step_size=1500,
        label="h3b_prefill_step1500",
    )
    prefill_4096_commands = _gemma_admission_commands(
        artifact_dir=args.artifact_dir,
        manifest=args.videomme_manifest,
        model_path=args.gemma_model_path,
        frame_count=args.frame_count,
        n_items=args.prefill_diagnostic_n_items,
        rss_guard_mb=args.rss_guard_mb,
        mlx_memory_limit_gb=args.mlx_memory_limit_gb,
        prefill_step_size=4096,
        label="h3b_prefill_step4096",
    )
    cvision_smoke_commands = _cvision_commands(
        artifact_dir=args.artifact_dir,
        manifest=args.smoke_manifest,
        model_path=args.gemma_model_path,
        frame_count=args.frame_count,
        n_items=1,
        rss_guard_mb=args.rss_guard_mb,
        mlx_memory_limit_gb=args.mlx_memory_limit_gb,
        label="cvision_rlt_smoke",
        expected_items=1,
        score_mode="rlt_topk",
    )
    cvision_videomme_commands = _cvision_commands(
        artifact_dir=args.artifact_dir,
        manifest=args.videomme_manifest,
        model_path=args.gemma_model_path,
        frame_count=args.frame_count,
        n_items=args.cvision_n_items,
        rss_guard_mb=args.rss_guard_mb,
        mlx_memory_limit_gb=args.mlx_memory_limit_gb,
        label="cvision_rlt_videomme",
        expected_items=args.cvision_n_items,
        score_mode="rlt_topk",
    )
    cvision_maxmin_videomme_commands = _cvision_commands(
        artifact_dir=args.artifact_dir,
        manifest=args.videomme_manifest,
        model_path=args.gemma_model_path,
        frame_count=args.frame_count,
        n_items=args.cvision_n_items,
        rss_guard_mb=args.rss_guard_mb,
        mlx_memory_limit_gb=args.mlx_memory_limit_gb,
        label="cvision_maxmin_videomme",
        expected_items=args.cvision_n_items,
        score_mode="max_min_diversity",
    )
    benchmark_manifests = {
        "videomme": args.videomme_manifest,
        "tomato": args.tomato_manifest,
        "mvbench": args.mvbench_manifest,
    }
    benchmark_run_n_items = {
        "videomme": args.cvision_n_items,
        "tomato": 0,
        "mvbench": 0,
    }
    benchmark_expected_items = {
        benchmark: _expected_items_for_manifest(
            manifest,
            n_items=benchmark_run_n_items[benchmark],
        )
        for benchmark, manifest in benchmark_manifests.items()
    }
    expansion_commands = {
        "tomato": _cvision_commands(
            artifact_dir=args.artifact_dir,
            manifest=args.tomato_manifest,
            model_path=args.gemma_model_path,
            frame_count=args.frame_count,
            n_items=0,
            rss_guard_mb=args.rss_guard_mb,
            mlx_memory_limit_gb=args.mlx_memory_limit_gb,
            label="cvision_rlt_tomato",
            expected_items=benchmark_expected_items["tomato"],
            score_mode="rlt_topk",
        ),
        "mvbench": _cvision_commands(
            artifact_dir=args.artifact_dir,
            manifest=args.mvbench_manifest,
            model_path=args.gemma_model_path,
            frame_count=args.frame_count,
            n_items=0,
            rss_guard_mb=args.rss_guard_mb,
            mlx_memory_limit_gb=args.mlx_memory_limit_gb,
            label="cvision_rlt_mvbench",
            expected_items=benchmark_expected_items["mvbench"],
            score_mode="rlt_topk",
        ),
    }
    maxmin_expansion_commands = {
        "tomato": _cvision_commands(
            artifact_dir=args.artifact_dir,
            manifest=args.tomato_manifest,
            model_path=args.gemma_model_path,
            frame_count=args.frame_count,
            n_items=0,
            rss_guard_mb=args.rss_guard_mb,
            mlx_memory_limit_gb=args.mlx_memory_limit_gb,
            label="cvision_maxmin_tomato",
            expected_items=benchmark_expected_items["tomato"],
            score_mode="max_min_diversity",
        ),
        "mvbench": _cvision_commands(
            artifact_dir=args.artifact_dir,
            manifest=args.mvbench_manifest,
            model_path=args.gemma_model_path,
            frame_count=args.frame_count,
            n_items=0,
            rss_guard_mb=args.rss_guard_mb,
            mlx_memory_limit_gb=args.mlx_memory_limit_gb,
            label="cvision_maxmin_mvbench",
            expected_items=benchmark_expected_items["mvbench"],
            score_mode="max_min_diversity",
        ),
    }
    magnitude_commands = {
        benchmark: _cvision_commands(
            artifact_dir=args.artifact_dir,
            manifest=manifest,
            model_path=args.gemma_model_path,
            frame_count=args.frame_count,
            n_items=args.cvision_n_items if benchmark == "videomme" else 0,
            rss_guard_mb=args.rss_guard_mb,
            mlx_memory_limit_gb=args.mlx_memory_limit_gb,
            label=f"cvision_magnitude_{benchmark}",
            expected_items=benchmark_expected_items[benchmark],
            score_mode="magnitude",
            dense_source_label=f"cvision_rlt_{benchmark}",
            include_dense_command=False,
        )
        for benchmark, manifest in benchmark_manifests.items()
    }
    magnitude_valid_commands = {
        benchmark: _cvision_commands(
            artifact_dir=args.artifact_dir,
            manifest=manifest,
            model_path=args.gemma_model_path,
            frame_count=args.frame_count,
            n_items=args.cvision_n_items if benchmark == "videomme" else 0,
            rss_guard_mb=args.rss_guard_mb,
            mlx_memory_limit_gb=args.mlx_memory_limit_gb,
            label=f"cvision_magnitude_valid_{benchmark}",
            expected_items=benchmark_expected_items[benchmark],
            score_mode="magnitude_valid",
            dense_source_label=f"cvision_rlt_{benchmark}",
            include_dense_command=False,
        )
        for benchmark, manifest in benchmark_manifests.items()
    }
    composition_commands = {
        benchmark: _gemma_composition_commands(
            artifact_dir=args.artifact_dir,
            manifest=manifest,
            model_path=args.gemma_model_path,
            frame_count=args.frame_count,
            n_items=args.cvision_n_items if benchmark == "videomme" else 0,
            rss_guard_mb=args.rss_guard_mb,
            mlx_memory_limit_gb=args.mlx_memory_limit_gb,
            label=f"composition_rlt_{benchmark}",
            prefill_step_size=args.composition_prefill_step_size,
        )
        for benchmark, manifest in benchmark_manifests.items()
    }
    full_composition_commands = {
        benchmark: _gemma_full_composition_commands(
            artifact_dir=args.artifact_dir,
            manifest=manifest,
            model_path=args.gemma_model_path,
            frame_count=args.frame_count,
            n_items=args.cvision_n_items if benchmark == "videomme" else 0,
            expected_items=benchmark_expected_items[benchmark],
            rss_guard_mb=args.rss_guard_mb,
            mlx_memory_limit_gb=args.mlx_memory_limit_gb,
            benchmark=benchmark,
            prefill_step_size=args.composition_prefill_step_size,
        )
        for benchmark, manifest in benchmark_manifests.items()
    }
    composition_rescue_commands = {
        benchmark: _gemma_full_composition_commands(
            artifact_dir=args.artifact_dir,
            manifest=manifest,
            model_path=args.gemma_model_path,
            frame_count=args.frame_count,
            n_items=args.cvision_n_items if benchmark == "videomme" else 0,
            expected_items=benchmark_expected_items[benchmark],
            rss_guard_mb=args.rss_guard_mb,
            mlx_memory_limit_gb=args.mlx_memory_limit_gb,
            benchmark=benchmark,
            prefill_step_size=args.composition_prefill_step_size,
            label=f"full_composition_rlt_rescue_{benchmark}",
            group_keep_rates=ADAPTIVE_COMPOSITION_GROUP_KEEP_RATES[benchmark],
            group_vision_keep_rates=ADAPTIVE_COMPOSITION_GROUP_KEEP_RATES[benchmark],
        )
        for benchmark, manifest in benchmark_manifests.items()
    }
    holdout_manifests = {
        "videomme": args.videomme_holdout_manifest,
        "tomato": args.tomato_holdout_manifest,
        "mvbench": args.mvbench_holdout_manifest,
    }
    holdout_expected_items = {
        benchmark: _expected_items_for_manifest(manifest, n_items=0)
        for benchmark, manifest in holdout_manifests.items()
    }
    full_composition_holdout_commands = {
        benchmark: _gemma_full_composition_commands(
            artifact_dir=args.artifact_dir,
            manifest=manifest,
            model_path=args.gemma_model_path,
            frame_count=args.frame_count,
            n_items=0,
            expected_items=holdout_expected_items[benchmark],
            rss_guard_mb=args.rss_guard_mb,
            mlx_memory_limit_gb=args.mlx_memory_limit_gb,
            benchmark=benchmark,
            prefill_step_size=args.composition_prefill_step_size,
            label=f"full_composition_rlt_holdout_{benchmark}",
        )
        for benchmark, manifest in holdout_manifests.items()
    }
    composition_rescue_holdout_commands = {
        benchmark: _gemma_full_composition_commands(
            artifact_dir=args.artifact_dir,
            manifest=manifest,
            model_path=args.gemma_model_path,
            frame_count=args.frame_count,
            n_items=0,
            expected_items=holdout_expected_items[benchmark],
            rss_guard_mb=args.rss_guard_mb,
            mlx_memory_limit_gb=args.mlx_memory_limit_gb,
            benchmark=benchmark,
            prefill_step_size=args.composition_prefill_step_size,
            label=f"full_composition_rlt_rescue_holdout_{benchmark}",
            group_keep_rates=ADAPTIVE_COMPOSITION_GROUP_KEEP_RATES[benchmark],
            group_vision_keep_rates=ADAPTIVE_COMPOSITION_GROUP_KEEP_RATES[benchmark],
        )
        for benchmark, manifest in holdout_manifests.items()
    }
    moving_attribute_bracket_commands = _gemma_full_composition_commands(
        artifact_dir=args.artifact_dir,
        manifest=args.mvbench_manifest,
        model_path=args.gemma_model_path,
        frame_count=args.frame_count,
        n_items=0,
        expected_items=benchmark_expected_items["mvbench"],
        rss_guard_mb=args.rss_guard_mb,
        mlx_memory_limit_gb=args.mlx_memory_limit_gb,
        benchmark="mvbench",
        prefill_step_size=args.composition_prefill_step_size,
        label="full_composition_rlt_mvbench_moving_attribute_kr100",
        group_keep_rates=MVBENCH_MOVING_ATTRIBUTE_BRACKET_KEEP_RATES,
        group_vision_keep_rates=MVBENCH_MOVING_ATTRIBUTE_BRACKET_KEEP_RATES,
    )
    moving_attribute_holdout_bracket_commands = _gemma_full_composition_commands(
        artifact_dir=args.artifact_dir,
        manifest=args.mvbench_holdout_manifest,
        model_path=args.gemma_model_path,
        frame_count=args.frame_count,
        n_items=0,
        expected_items=holdout_expected_items["mvbench"],
        rss_guard_mb=args.rss_guard_mb,
        mlx_memory_limit_gb=args.mlx_memory_limit_gb,
        benchmark="mvbench",
        prefill_step_size=args.composition_prefill_step_size,
        label="full_composition_rlt_holdout_mvbench_moving_attribute_kr100",
        group_keep_rates=MVBENCH_MOVING_ATTRIBUTE_BRACKET_KEEP_RATES,
        group_vision_keep_rates=MVBENCH_MOVING_ATTRIBUTE_BRACKET_KEEP_RATES,
    )
    full_composition_combined_commands = {
        benchmark: _gemma_full_composition_combined_analysis_command(
            artifact_dir=args.artifact_dir,
            dense_jsonls=[
                args.artifact_dir / f"full_composition_dense_{benchmark}.jsonl",
                args.artifact_dir / f"full_composition_rlt_holdout_{benchmark}_dense.jsonl",
            ],
            composed_jsonls=[
                args.artifact_dir / f"full_composition_rlt_{benchmark}.jsonl",
                args.artifact_dir / f"full_composition_rlt_holdout_{benchmark}_composed.jsonl",
            ],
            expected_items=60,
            output_label=f"full_composition_rlt_combined_{benchmark}",
        )
        for benchmark in benchmark_manifests
    }
    full_composition_rescue_combined_commands = {
        benchmark: _gemma_full_composition_combined_analysis_command(
            artifact_dir=args.artifact_dir,
            dense_jsonls=[
                args.artifact_dir / f"full_composition_rlt_rescue_{benchmark}_dense.jsonl",
                args.artifact_dir / f"full_composition_rlt_rescue_holdout_{benchmark}_dense.jsonl",
            ],
            composed_jsonls=[
                args.artifact_dir / f"full_composition_rlt_rescue_{benchmark}_composed.jsonl",
                args.artifact_dir
                / f"full_composition_rlt_rescue_holdout_{benchmark}_composed.jsonl",
            ],
            expected_items=60,
            output_label=f"full_composition_rlt_rescue_combined_{benchmark}",
        )
        for benchmark in benchmark_manifests
    }
    sweep_manifest = benchmark_manifests[args.keep_rate_sweep_benchmark]
    sweep_expected_items = benchmark_expected_items[args.keep_rate_sweep_benchmark]
    keep_rate_sweep_commands = {
        rate: _cvision_commands(
            artifact_dir=args.artifact_dir,
            manifest=sweep_manifest,
            model_path=args.gemma_model_path,
            frame_count=args.frame_count,
            n_items=(args.cvision_n_items if args.keep_rate_sweep_benchmark == "videomme" else 0),
            rss_guard_mb=args.rss_guard_mb,
            mlx_memory_limit_gb=args.mlx_memory_limit_gb,
            label=(f"cvision_rlt_{args.keep_rate_sweep_benchmark}_kr{int(round(rate * 100)):03d}"),
            expected_items=sweep_expected_items,
            score_mode="rlt_topk",
            keep_rate=rate,
            dense_source_label=f"cvision_rlt_{args.keep_rate_sweep_benchmark}",
            include_dense_command=False,
        )
        for rate in keep_rates
    }
    query_q0b_commands: dict[str, list[list[str]]] = {}
    for benchmark in query_routing_benchmarks:
        manifest = benchmark_manifests[benchmark]
        expected = benchmark_expected_items[benchmark]
        n_items = args.cvision_n_items if benchmark == "videomme" else 0
        dense_source_label = f"query_q0b_dense_{benchmark}"
        q0b_specs = [
            (
                f"query_q0b_dense_equivalent_{benchmark}",
                True,
                "none",
                1.0,
                1.0,
                "magnitude",
                None,
                None,
            ),
            (
                f"query_q0b_admission_only_{benchmark}",
                False,
                "rlt",
                0.5,
                1.0,
                "magnitude",
                None,
                None,
            ),
            (
                f"query_q0b_cvision_only_{benchmark}_kr050",
                False,
                "none",
                1.0,
                0.5,
                "rlt_topk",
                None,
                None,
            ),
            (
                f"query_q0b_cvision_only_{benchmark}_kr100",
                False,
                "none",
                1.0,
                1.0,
                "rlt_topk",
                None,
                None,
            ),
            (
                f"query_q0b_full_{benchmark}_kr050",
                False,
                "rlt",
                0.5,
                0.5,
                "rlt_topk",
                None,
                None,
            ),
            (
                f"query_q0b_full_{benchmark}_kr070",
                False,
                "rlt",
                0.5,
                0.7,
                "rlt_topk",
                None,
                None,
            ),
            (
                f"query_q0b_full_{benchmark}_kr085",
                False,
                "rlt",
                0.5,
                0.85,
                "rlt_topk",
                None,
                None,
            ),
            (
                f"query_q0b_full_{benchmark}_kr100",
                False,
                "rlt",
                0.5,
                1.0,
                "rlt_topk",
                None,
                None,
            ),
        ]
        for (
            label,
            include_dense,
            prune_placeholders,
            composed_keep_rate,
            vision_keep_rate,
            score_mode,
            floor_stride,
            random_seed,
        ) in q0b_specs:
            query_q0b_commands[label] = _gemma_full_composition_commands(
                artifact_dir=args.artifact_dir,
                manifest=manifest,
                model_path=args.gemma_model_path,
                frame_count=args.frame_count,
                n_items=n_items,
                expected_items=expected,
                rss_guard_mb=args.rss_guard_mb,
                mlx_memory_limit_gb=args.mlx_memory_limit_gb,
                benchmark=benchmark,
                prefill_step_size=args.composition_prefill_step_size,
                vision_keep_rate=vision_keep_rate,
                label=label,
                dense_source_label=dense_source_label,
                include_dense_command=include_dense,
                composed_keep_rate=composed_keep_rate,
                composed_prune_placeholders=prune_placeholders,
                vision_score_mode=score_mode,
                vision_static_floor_stride=floor_stride,
                vision_random_seed=random_seed,
            )
    query_q1_commands: dict[str, list[list[str]]] = {}
    for benchmark in query_routing_benchmarks:
        manifest = benchmark_manifests[benchmark]
        expected = benchmark_expected_items[benchmark]
        n_items = args.cvision_n_items if benchmark == "videomme" else 0
        dense_source_label = f"query_q1_dense_{benchmark}"
        q1_specs: list[tuple[str, bool, float, str, int | None, int | None]] = [
            (f"query_q1_{benchmark}_redundancy_kr050", True, 0.5, "rlt_topk", None, None),
            (f"query_q1_{benchmark}_redundancy_kr070", False, 0.7, "rlt_topk", None, None),
            (
                f"query_q1_{benchmark}_static_floor_s4",
                False,
                0.5,
                "rlt_topk_static_floor",
                4,
                None,
            ),
            (f"query_q1_{benchmark}_fixed_uniform", False, 0.5, "fixed_uniform", None, None),
        ]
        q1_specs.extend(
            (
                f"query_q1_{benchmark}_random_seed{seed}",
                False,
                0.5,
                "random_valid",
                None,
                seed,
            )
            for seed in QUERY_ROUTING_Q1_RANDOM_SEEDS
        )
        for (
            label,
            include_dense,
            vision_keep_rate,
            score_mode,
            floor_stride,
            random_seed,
        ) in q1_specs:
            query_q1_commands[label] = _gemma_full_composition_commands(
                artifact_dir=args.artifact_dir,
                manifest=manifest,
                model_path=args.gemma_model_path,
                frame_count=args.frame_count,
                n_items=n_items,
                expected_items=expected,
                rss_guard_mb=args.rss_guard_mb,
                mlx_memory_limit_gb=args.mlx_memory_limit_gb,
                benchmark=benchmark,
                prefill_step_size=args.composition_prefill_step_size,
                vision_keep_rate=vision_keep_rate,
                label=label,
                dense_source_label=dense_source_label,
                include_dense_command=include_dense,
                composed_keep_rate=1.0,
                composed_prune_placeholders="none",
                vision_score_mode=score_mode,
                vision_static_floor_stride=floor_stride,
                vision_random_seed=random_seed,
            )
    query_q1b_commands: dict[str, list[list[str]]] = {}
    query_q1c_commands: dict[str, list[list[str]]] = {}
    if "mvbench" in query_routing_benchmarks:
        benchmark = "mvbench"
        manifest = benchmark_manifests[benchmark]
        expected = benchmark_expected_items[benchmark]
        dense_source_label = f"query_q1b_dense_{benchmark}"
        q1b_specs: list[
            tuple[
                str,
                bool,
                str,
                float,
                str,
                int | None,
                int | None,
                dict[str, float] | None,
            ]
        ] = [
            (
                f"query_q1b_{benchmark}_endpoint_anchor",
                True,
                "none",
                0.5,
                "rlt_topk_endpoint_anchor",
                None,
                None,
                None,
            ),
            (
                f"query_q1b_{benchmark}_random_seed11_actionloc_dense",
                False,
                "none",
                0.5,
                "random_valid",
                None,
                11,
                QUERY_ROUTING_Q1B_ACTIONLOC_REPAIR_KEEP_RATES,
            ),
            (
                f"query_q1b_{benchmark}_fixed_uniform_actionloc_dense",
                False,
                "none",
                0.5,
                "fixed_uniform",
                None,
                None,
                QUERY_ROUTING_Q1B_ACTIONLOC_REPAIR_KEEP_RATES,
            ),
            (
                f"query_q1b_{benchmark}_random_seed11_admission_on",
                False,
                "rlt",
                0.5,
                "random_valid",
                None,
                11,
                None,
            ),
            (
                f"query_q1b_{benchmark}_fixed_uniform_admission_on",
                False,
                "rlt",
                0.5,
                "fixed_uniform",
                None,
                None,
                None,
            ),
        ]
        for (
            label,
            include_dense,
            prune_placeholders,
            vision_keep_rate,
            score_mode,
            floor_stride,
            random_seed,
            group_vision_keep_rates,
        ) in q1b_specs:
            query_q1b_commands[label] = _gemma_full_composition_commands(
                artifact_dir=args.artifact_dir,
                manifest=manifest,
                model_path=args.gemma_model_path,
                frame_count=args.frame_count,
                n_items=0,
                expected_items=expected,
                rss_guard_mb=args.rss_guard_mb,
                mlx_memory_limit_gb=args.mlx_memory_limit_gb,
                benchmark=benchmark,
                prefill_step_size=args.composition_prefill_step_size,
                vision_keep_rate=vision_keep_rate,
                label=label,
                dense_source_label=dense_source_label,
                include_dense_command=include_dense,
                composed_keep_rate=0.5 if prune_placeholders == "rlt" else 1.0,
                composed_prune_placeholders=prune_placeholders,
                vision_score_mode=score_mode,
                vision_static_floor_stride=floor_stride,
                vision_random_seed=random_seed,
                group_vision_keep_rates=group_vision_keep_rates,
            )
        q1c_specs: list[
            tuple[
                str,
                set[str],
                dict[str, float] | None,
            ]
        ] = [
            (
                f"query_q1c_{benchmark}_random_seed11_no_admission_baseline",
                set(),
                None,
            ),
            (
                f"query_q1c_{benchmark}_random_seed11_safe_admission",
                set(QUERY_ROUTING_Q1C_SAFE_ADMISSION_KEEP_RATES),
                None,
            ),
            (
                f"query_q1c_{benchmark}_random_seed11_moving_attribute_safe_admission",
                QUERY_ROUTING_Q1C_MOVING_ATTRIBUTE_SAFE_ADMISSION_GROUPS,
                None,
            ),
            (
                f"query_q1c_{benchmark}_random_seed11_safe_admission_actionloc_dense",
                set(QUERY_ROUTING_Q1C_SAFE_ADMISSION_KEEP_RATES),
                QUERY_ROUTING_Q1C_ACTIONLOC_DENSE_KEEP_RATES,
            ),
        ]
        for label, admission_groups, group_vision_keep_rates in q1c_specs:
            query_q1c_commands[label] = _gemma_full_composition_commands(
                artifact_dir=args.artifact_dir,
                manifest=manifest,
                model_path=args.gemma_model_path,
                frame_count=args.frame_count,
                n_items=0,
                expected_items=expected,
                rss_guard_mb=args.rss_guard_mb,
                mlx_memory_limit_gb=args.mlx_memory_limit_gb,
                benchmark=benchmark,
                prefill_step_size=args.composition_prefill_step_size,
                vision_keep_rate=0.5,
                label=label,
                dense_source_label=dense_source_label,
                include_dense_command=False,
                composed_keep_rate=1.0,
                composed_prune_placeholders="none",
                vision_score_mode="random_valid",
                vision_random_seed=11,
                group_prune_placeholders={group: "rlt" for group in admission_groups},
                group_vision_keep_rates=group_vision_keep_rates,
            )
    if args.run_prefill_diagnostics:
        planned.append({"phase": "prefill_kernel_microbench", "command": prefill_kernel_command})
        planned.extend({"phase": "prefill_step_1500", "command": c} for c in prefill_1500_commands)
        planned.extend(
            {"phase": "prefill_step_4096_if_needed", "command": c} for c in prefill_4096_commands
        )
    if args.run_cvision_rlt:
        planned.extend({"phase": "cvision_rlt_smoke", "command": c} for c in cvision_smoke_commands)
        planned.extend(
            {"phase": "cvision_rlt_videomme_if_smoke_passes", "command": c}
            for c in cvision_videomme_commands
        )
        if args.run_max_min_triangulation:
            planned.extend(
                {
                    "phase": "cvision_maxmin_videomme_if_rlt_videomme_passes",
                    "command": c,
                }
                for c in cvision_maxmin_videomme_commands
            )
    if args.run_cvision_expansion:
        for benchmark, phase_commands in expansion_commands.items():
            planned.extend(
                {"phase": f"cvision_rlt_{benchmark}_if_videomme_passes", "command": c}
                for c in phase_commands
            )
        if args.run_max_min_triangulation:
            for benchmark, phase_commands in maxmin_expansion_commands.items():
                planned.extend(
                    {
                        "phase": f"cvision_maxmin_{benchmark}_if_rlt_videomme_passes",
                        "command": c,
                    }
                    for c in phase_commands
                )
    if args.run_magnitude_head_to_head:
        for benchmark, phase_commands in magnitude_commands.items():
            planned.extend(
                {
                    "phase": f"cvision_magnitude_{benchmark}_if_rlt_videomme_core_passes",
                    "command": c,
                }
                for c in phase_commands
            )
    if args.run_magnitude_valid_head_to_head:
        for benchmark, phase_commands in magnitude_valid_commands.items():
            planned.extend(
                {
                    "phase": f"cvision_magnitude_valid_{benchmark}_if_rlt_videomme_core_passes",
                    "command": c,
                }
                for c in phase_commands
            )
    if args.run_composition_incremental:
        for benchmark, phase_commands in composition_commands.items():
            planned.extend(
                {
                    "phase": f"composition_rlt_{benchmark}_if_rlt_videomme_core_passes",
                    "command": c,
                }
                for c in phase_commands
            )
    if args.run_composition_direct:
        for benchmark, phase_commands in full_composition_commands.items():
            planned.extend(
                {
                    "phase": f"full_composition_rlt_{benchmark}_if_rlt_videomme_core_passes",
                    "command": c,
                }
                for c in phase_commands
            )
    if args.run_composition_rescue:
        for benchmark, phase_commands in composition_rescue_commands.items():
            planned.extend(
                {
                    "phase": (
                        f"full_composition_rlt_rescue_{benchmark}_"
                        "if_base_direct_composition_needs_quality_rescue"
                    ),
                    "command": c,
                }
                for c in phase_commands
            )
    if args.run_composition_holdout:
        for benchmark, phase_commands in full_composition_holdout_commands.items():
            planned.extend(
                {
                    "phase": (
                        f"full_composition_rlt_holdout_{benchmark}_if_rlt_videomme_core_passes"
                    ),
                    "command": c,
                }
                for c in phase_commands
            )
    if args.run_composition_rescue_holdout:
        for benchmark, phase_commands in composition_rescue_holdout_commands.items():
            planned.extend(
                {
                    "phase": (
                        f"full_composition_rlt_rescue_holdout_{benchmark}_"
                        "if_holdout_direct_composition_needs_quality_rescue"
                    ),
                    "command": c,
                }
                for c in phase_commands
            )
    if args.run_moving_attribute_bracket:
        planned.extend(
            {
                "phase": (
                    "full_composition_rlt_mvbench_moving_attribute_kr100_"
                    "if_rlt_videomme_core_passes"
                ),
                "command": c,
            }
            for c in moving_attribute_bracket_commands
        )
    if args.run_moving_attribute_holdout_bracket:
        planned.extend(
            {
                "phase": (
                    "full_composition_rlt_holdout_mvbench_moving_attribute_kr100_"
                    "if_rlt_videomme_core_passes"
                ),
                "command": c,
            }
            for c in moving_attribute_holdout_bracket_commands
        )
    if args.run_composition_combined_analysis:
        for benchmark, command in full_composition_combined_commands.items():
            planned.append(
                {
                    "phase": (
                        f"full_composition_rlt_combined_{benchmark}_"
                        "if_dev_and_holdout_artifacts_exist"
                    ),
                    "command": command,
                }
            )
        for benchmark, command in full_composition_rescue_combined_commands.items():
            planned.append(
                {
                    "phase": (
                        f"full_composition_rlt_rescue_combined_{benchmark}_"
                        "if_dev_and_holdout_artifacts_exist"
                    ),
                    "command": command,
                }
            )
    if args.run_keep_rate_sweep:
        for rate, phase_commands in keep_rate_sweep_commands.items():
            planned.extend(
                {
                    "phase": (
                        f"cvision_rlt_{args.keep_rate_sweep_benchmark}_"
                        f"kr{int(round(rate * 100)):03d}_if_rlt_videomme_core_passes"
                    ),
                    "command": c,
                }
                for c in phase_commands
            )
    if args.run_query_routing_q0b:
        for label, phase_commands in query_q0b_commands.items():
            planned.extend(
                {
                    "phase": f"{label}_if_rlt_videomme_core_passes",
                    "command": c,
                }
                for c in phase_commands
            )
    if args.run_query_routing_q1:
        for label, phase_commands in query_q1_commands.items():
            planned.extend(
                {
                    "phase": f"{label}_if_q0b_dense_equivalence_passes",
                    "command": c,
                }
                for c in phase_commands
            )
    if args.run_query_routing_q1b_followup:
        for label, phase_commands in query_q1b_commands.items():
            planned.extend(
                {
                    "phase": f"{label}_after_q1_negative_verdict",
                    "command": c,
                }
                for c in phase_commands
            )
    if args.run_query_routing_q1c_admission_scheduler:
        for label, phase_commands in query_q1c_commands.items():
            planned.extend(
                {
                    "phase": f"{label}_after_q1b_admission_damage",
                    "command": c,
                }
                for c in phase_commands
            )
    if args.dry_run:
        _write_json(
            summary_path,
            {
                "schema_version": SCHEMA_VERSION,
                "dry_run": True,
                "budget": budget,
                "planned_commands": _portable_planned(planned),
                "early_cancel_tree": [
                    *(
                        [
                            (
                                "Run a synthetic mlx-vlm prefill-kernel micro-benchmark "
                                "with all shapes warmed and shuffled; cooldown before "
                                "video timing diagnostics."
                            ),
                            (
                                "Run prefill_step_size=1500 first; skip 4096 if "
                                "same-path chunking makes RLT faster."
                            ),
                        ]
                        if args.run_prefill_diagnostics
                        else []
                    ),
                    *(
                        [
                            ("Run C-VISION RLT n=1 smoke; skip VideoMME decision if smoke fails."),
                            (
                                "Run C-VISION RLT VideoMME n=30; skip TOMATO/MVBench "
                                "expansion and head-to-head follow-ups unless it passes "
                                "fidelity, sparse-induced parse-failure, sparse-vision, "
                                "bucket, and E2E gates. Absolute parse-rate and ceiling "
                                "diagnostics are reported but no longer hard-cancel "
                                "scientifically useful follow-ups."
                            ),
                        ]
                        if args.run_cvision_rlt
                        else []
                    ),
                    *(
                        [
                            (
                                "Run bucket-specific full-composition rescue only after "
                                "RLT VideoMME core gates pass. The rescue raises keep-rate "
                                "only in quality-failed groups from the direct composition "
                                "cell, and skips a benchmark whose base direct composition "
                                "already passes all full-composition gates."
                            )
                        ]
                        if args.run_composition_rescue
                        else []
                    ),
                    *(
                        [
                            (
                                "Run direct dense-vs-full-composition on disjoint holdout "
                                "manifests after RLT VideoMME core gates pass. These rows "
                                "replicate or weaken the dev-slice composition story; they "
                                "do not inherit dev results."
                            )
                        ]
                        if args.run_composition_holdout
                        else []
                    ),
                    *(
                        [
                            (
                                "Run holdout rescue only for benchmarks whose holdout "
                                "direct-composition cell does not clear all direct gates. "
                                "A rescue result supersedes a failed holdout row only if "
                                "it clears aggregate and bucket quality gates."
                            )
                        ]
                        if args.run_composition_rescue_holdout
                        else []
                    ),
                    *(
                        [
                            (
                                "Run the MVBench moving_attribute kr=1.0 bracket only "
                                "after RLT VideoMME core gates pass. This brackets "
                                "whether the residual moving_attribute failure is a "
                                "token-budget problem or a structural saliency problem."
                            )
                        ]
                        if args.run_moving_attribute_bracket
                        else []
                    ),
                    *(
                        [
                            (
                                "Run the disjoint-holdout MVBench moving_attribute "
                                "kr=1.0 bracket only after RLT VideoMME core gates pass. "
                                "Compare its by-group moving_attribute row against the "
                                "dev bracket before claiming structural failure."
                            )
                        ]
                        if args.run_moving_attribute_holdout_bracket
                        else []
                    ),
                    *(
                        [
                            (
                                "Run pooled dev+holdout n=60 analyzer passes only after "
                                "RLT VideoMME core gates pass. These are analyzer-only "
                                "commands and require the corresponding dev and holdout "
                                "JSONLs to exist."
                            )
                        ]
                        if args.run_composition_combined_analysis
                        else []
                    ),
                    *(
                        [
                            (
                                "Run Q0b dense-equivalence first, then admission-only, "
                                "C-VISION-only, and full-composition oracle arms. Skip Q1 "
                                "if dense-equivalence fails or required placeholder/encoder "
                                "ledgers are missing."
                            )
                        ]
                        if args.run_query_routing_q0b
                        else []
                    ),
                    *(
                        [
                            (
                                "Run Q1 matched-budget operator ablations only after Q0b "
                                "dense-equivalence passes. These cells can earn "
                                "proceed-to-Q2 evidence, not a standalone query-planning "
                                "claim until scalar-query baselines are beaten."
                            )
                        ]
                        if args.run_query_routing_q1
                        else []
                    ),
                    *(
                        [
                            (
                                "Run Q1b only after Q1. This is a narrow negative-result "
                                "follow-up: endpoint anchors, admission-on coverage "
                                "controls, and action_localization dense fallback. It "
                                "does not authorize QuoTA, repair-pass, or full planner work."
                            )
                        ]
                        if args.run_query_routing_q1b_followup
                        else []
                    ),
                    *(
                        [
                            (
                                "Run Q1c only after Q1b. This is a narrow admission-scheduler "
                                "diagnostic: coverage-first random C-VISION, prompt admission "
                                "off by default, and admission enabled only for preregistered "
                                "low-risk groups. A positive row authorizes holdout confirmation, "
                                "not a standalone planner claim."
                            )
                        ]
                        if args.run_query_routing_q1c_admission_scheduler
                        else []
                    ),
                ],
            },
        )
        print(json.dumps({"summary": str(summary_path), "dry_run": True}, sort_keys=True))
        return 0

    commands: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    analyses: dict[str, Any] = {}
    if args.run_prefill_diagnostics:
        kernel_result = _run(prefill_kernel_command, allow_failure=True)
        commands.append(kernel_result)
        kernel_path = args.artifact_dir / "prefill_kernel_microbench.json"
        if int(kernel_result["returncode"]) == 0 and kernel_path.exists():
            analyses["prefill_kernel_microbench"] = _read_json(kernel_path)
        else:
            decisions.append(
                {
                    "decision": "continue",
                    "reason": "prefill_kernel_microbench_unavailable",
                    "phase": "prefill_kernel_microbench",
                    "returncode": kernel_result["returncode"],
                }
            )
        if args.cooldown_after_microbench_seconds > 0:
            cooldown_started = time.perf_counter()
            time.sleep(args.cooldown_after_microbench_seconds)
            commands.append(
                {
                    "command": [
                        "sleep",
                        str(args.cooldown_after_microbench_seconds),
                    ],
                    "returncode": 0,
                    "elapsed_seconds": time.perf_counter() - cooldown_started,
                    "stdout_tail": "",
                    "stderr_tail": "",
                    "reason": "cooldown_after_prefill_kernel_microbench",
                }
            )
        prefill_1500_results = _run_command_group(prefill_1500_commands)
        commands.extend(prefill_1500_results)
        analysis_1500 = _read_analysis_after_success(
            results=prefill_1500_results,
            path=args.artifact_dir / "h3b_prefill_step1500_analysis.json",
            phase="h3b_prefill_step1500",
            decisions=decisions,
            skipped=["prefill_step_4096"],
        )
        if analysis_1500 is not None:
            analyses["h3b_prefill_step1500"] = analysis_1500
        if analysis_1500 is not None and _phase_passed_prefill_same_path(analysis_1500):
            decisions.append(
                {
                    "decision": "skip",
                    "reason": "prefill_step_1500_confirmed_same_path_speedup",
                    "skipped_phase": "prefill_step_4096",
                }
            )
        elif analysis_1500 is not None:
            prefill_4096_results = _run_command_group(prefill_4096_commands)
            commands.extend(prefill_4096_results)
            analysis_4096 = _read_analysis_after_success(
                results=prefill_4096_results,
                path=args.artifact_dir / "h3b_prefill_step4096_analysis.json",
                phase="h3b_prefill_step4096",
                decisions=decisions,
            )
            if analysis_4096 is not None:
                analyses["h3b_prefill_step4096"] = analysis_4096
    cvision_videomme_passed = False
    if args.run_cvision_rlt:
        smoke_results = _run_command_group(cvision_smoke_commands)
        commands.extend(smoke_results)
        smoke_analysis = _read_analysis_after_success(
            results=smoke_results,
            path=args.artifact_dir / "cvision_rlt_smoke_analysis.json",
            phase="cvision_rlt_smoke",
            decisions=decisions,
            skipped=["cvision_rlt_videomme", "cvision_rlt_expansion"],
        )
        if smoke_analysis is not None:
            analyses["cvision_rlt_smoke"] = smoke_analysis
        if smoke_analysis is None:
            pass
        elif not smoke_analysis.get("pass_complete_pairing"):
            decisions.append(
                {
                    "decision": "stop",
                    "reason": "cvision_rlt_smoke_failed_pairing",
                    "skip": ["cvision_rlt_videomme", "cvision_rlt_expansion"],
                }
            )
        else:
            videomme_results = _run_command_group(cvision_videomme_commands)
            commands.extend(videomme_results)
            videomme_analysis = _read_analysis_after_success(
                results=videomme_results,
                path=args.artifact_dir / "cvision_rlt_videomme_analysis.json",
                phase="cvision_rlt_videomme",
                decisions=decisions,
                skipped=[
                    "cvision_rlt_expansion",
                    "cvision_maxmin_videomme",
                    "cvision_maxmin_expansion",
                ],
            )
            if videomme_analysis is not None:
                analyses["cvision_rlt_videomme"] = videomme_analysis
                cvision_videomme_passed = _phase_passed_cvision(videomme_analysis)
            if videomme_analysis is not None and not cvision_videomme_passed:
                decisions.append(
                    {
                        "decision": "skip",
                        "reason": "cvision_rlt_videomme_gate_failed",
                        "skip": [
                            "cvision_rlt_expansion",
                            "cvision_maxmin_videomme",
                            "cvision_maxmin_expansion",
                        ],
                    }
                )
    if args.run_max_min_triangulation and cvision_videomme_passed:
        maxmin_videomme_results = _run_command_group(cvision_maxmin_videomme_commands)
        commands.extend(maxmin_videomme_results)
        maxmin_videomme_analysis = _read_analysis_after_success(
            results=maxmin_videomme_results,
            path=args.artifact_dir / "cvision_maxmin_videomme_analysis.json",
            phase="cvision_maxmin_videomme",
            decisions=decisions,
        )
        if maxmin_videomme_analysis is not None:
            analyses["cvision_maxmin_videomme"] = maxmin_videomme_analysis
    elif args.run_max_min_triangulation and args.run_cvision_rlt and not cvision_videomme_passed:
        decisions.append(
            {
                "decision": "skip",
                "reason": "cvision_maxmin_requires_rlt_videomme_pass",
            }
        )
    if args.run_cvision_expansion and cvision_videomme_passed:
        for benchmark, phase_commands in expansion_commands.items():
            expansion_results = _run_command_group(phase_commands)
            commands.extend(expansion_results)
            expansion_analysis = _read_analysis_after_success(
                results=expansion_results,
                path=args.artifact_dir / f"cvision_rlt_{benchmark}_analysis.json",
                phase=f"cvision_rlt_{benchmark}",
                decisions=decisions,
            )
            if expansion_analysis is not None:
                analyses[f"cvision_rlt_{benchmark}"] = expansion_analysis
        if args.run_max_min_triangulation:
            for benchmark, phase_commands in maxmin_expansion_commands.items():
                maxmin_expansion_results = _run_command_group(phase_commands)
                commands.extend(maxmin_expansion_results)
                maxmin_expansion_analysis = _read_analysis_after_success(
                    results=maxmin_expansion_results,
                    path=args.artifact_dir / f"cvision_maxmin_{benchmark}_analysis.json",
                    phase=f"cvision_maxmin_{benchmark}",
                    decisions=decisions,
                )
                if maxmin_expansion_analysis is not None:
                    analyses[f"cvision_maxmin_{benchmark}"] = maxmin_expansion_analysis
    elif args.run_cvision_expansion and not cvision_videomme_passed:
        decisions.append(
            {
                "decision": "skip",
                "reason": "cvision_rlt_expansion_requires_videomme_pass",
            }
        )
    if args.run_magnitude_head_to_head and cvision_videomme_passed:
        for benchmark, phase_commands in magnitude_commands.items():
            magnitude_results = _run_command_group(phase_commands)
            commands.extend(magnitude_results)
            magnitude_analysis = _read_analysis_after_success(
                results=magnitude_results,
                path=args.artifact_dir / f"cvision_magnitude_{benchmark}_analysis.json",
                phase=f"cvision_magnitude_{benchmark}",
                decisions=decisions,
            )
            if magnitude_analysis is not None:
                analyses[f"cvision_magnitude_{benchmark}"] = magnitude_analysis
    elif args.run_magnitude_head_to_head and not cvision_videomme_passed:
        decisions.append(
            {
                "decision": "skip",
                "reason": "cvision_magnitude_requires_rlt_videomme_pass",
            }
        )
    if args.run_magnitude_valid_head_to_head and cvision_videomme_passed:
        for benchmark, phase_commands in magnitude_valid_commands.items():
            magnitude_valid_results = _run_command_group(phase_commands)
            commands.extend(magnitude_valid_results)
            magnitude_valid_analysis = _read_analysis_after_success(
                results=magnitude_valid_results,
                path=args.artifact_dir / f"cvision_magnitude_valid_{benchmark}_analysis.json",
                phase=f"cvision_magnitude_valid_{benchmark}",
                decisions=decisions,
            )
            if magnitude_valid_analysis is not None:
                analyses[f"cvision_magnitude_valid_{benchmark}"] = magnitude_valid_analysis
    elif args.run_magnitude_valid_head_to_head and not cvision_videomme_passed:
        decisions.append(
            {
                "decision": "skip",
                "reason": "cvision_magnitude_valid_requires_rlt_videomme_pass",
            }
        )
    if args.run_composition_incremental and cvision_videomme_passed:
        for benchmark, phase_commands in composition_commands.items():
            composition_results = _run_command_group(phase_commands)
            commands.extend(composition_results)
            composition_analysis = _read_analysis_after_success(
                results=composition_results,
                path=args.artifact_dir / f"composition_rlt_{benchmark}_analysis.json",
                phase=f"composition_rlt_{benchmark}",
                decisions=decisions,
            )
            if composition_analysis is not None:
                analyses[f"composition_rlt_{benchmark}"] = composition_analysis
                if any(
                    decision.get("decision") in {"stop", "contract"}
                    for decision in composition_analysis.get("decisions", [])
                ):
                    decisions.append(
                        {
                            "decision": "continue",
                            "reason": f"composition_rlt_{benchmark}_did_not_earn_gate",
                            "phase": f"composition_rlt_{benchmark}",
                            "details": composition_analysis.get("decisions", []),
                        }
                    )
    elif args.run_composition_incremental and not cvision_videomme_passed:
        decisions.append(
            {
                "decision": "skip",
                "reason": "composition_requires_rlt_videomme_pass",
            }
        )
    if args.run_composition_direct and cvision_videomme_passed:
        for benchmark, phase_commands in full_composition_commands.items():
            full_composition_results = _run_command_group(phase_commands)
            commands.extend(full_composition_results)
            full_composition_analysis = _read_analysis_after_success(
                results=full_composition_results,
                path=args.artifact_dir / f"full_composition_rlt_{benchmark}_analysis.json",
                phase=f"full_composition_rlt_{benchmark}",
                decisions=decisions,
            )
            if full_composition_analysis is not None:
                analyses[f"full_composition_rlt_{benchmark}"] = full_composition_analysis
                if not _phase_passed_full_composition(full_composition_analysis):
                    decisions.append(
                        {
                            "decision": "continue",
                            "reason": f"full_composition_rlt_{benchmark}_did_not_earn_gate",
                            "phase": f"full_composition_rlt_{benchmark}",
                            "details": full_composition_analysis.get("decisions", []),
                        }
                    )
    elif args.run_composition_direct and not cvision_videomme_passed:
        decisions.append(
            {
                "decision": "skip",
                "reason": "full_composition_requires_rlt_videomme_pass",
            }
        )
    if args.run_composition_rescue and cvision_videomme_passed:
        for benchmark, phase_commands in composition_rescue_commands.items():
            base_analysis = analyses.get(f"full_composition_rlt_{benchmark}")
            if isinstance(base_analysis, dict) and _phase_passed_full_composition(base_analysis):
                decisions.append(
                    {
                        "decision": "skip",
                        "reason": f"full_composition_rlt_{benchmark}_already_passed",
                        "skipped_phase": f"full_composition_rlt_rescue_{benchmark}",
                    }
                )
                continue
            rescue_results = _run_command_group(phase_commands)
            commands.extend(rescue_results)
            rescue_label = f"full_composition_rlt_rescue_{benchmark}"
            rescue_analysis = _read_analysis_after_success(
                results=rescue_results,
                path=args.artifact_dir / f"{rescue_label}_analysis.json",
                phase=rescue_label,
                decisions=decisions,
            )
            if rescue_analysis is not None:
                analyses[rescue_label] = rescue_analysis
                if not _phase_passed_full_composition(rescue_analysis):
                    decisions.append(
                        {
                            "decision": "continue",
                            "reason": f"{rescue_label}_did_not_earn_gate",
                            "phase": rescue_label,
                            "details": rescue_analysis.get("decisions", []),
                        }
                    )
    elif args.run_composition_rescue and not cvision_videomme_passed:
        decisions.append(
            {
                "decision": "skip",
                "reason": "full_composition_rescue_requires_rlt_videomme_pass",
            }
        )
    if args.run_composition_holdout and cvision_videomme_passed:
        for benchmark, phase_commands in full_composition_holdout_commands.items():
            holdout_results = _run_command_group(phase_commands)
            commands.extend(holdout_results)
            holdout_label = f"full_composition_rlt_holdout_{benchmark}"
            holdout_analysis = _read_analysis_after_success(
                results=holdout_results,
                path=args.artifact_dir / f"{holdout_label}_analysis.json",
                phase=holdout_label,
                decisions=decisions,
            )
            if holdout_analysis is not None:
                analyses[holdout_label] = holdout_analysis
                if not _phase_passed_full_composition(holdout_analysis):
                    decisions.append(
                        {
                            "decision": "continue",
                            "reason": f"{holdout_label}_did_not_earn_gate",
                            "phase": holdout_label,
                            "details": holdout_analysis.get("decisions", []),
                        }
                    )
    elif args.run_composition_holdout and not cvision_videomme_passed:
        decisions.append(
            {
                "decision": "skip",
                "reason": "full_composition_holdout_requires_rlt_videomme_pass",
            }
        )
    if args.run_composition_rescue_holdout and cvision_videomme_passed:
        for benchmark, phase_commands in composition_rescue_holdout_commands.items():
            holdout_label = f"full_composition_rlt_holdout_{benchmark}"
            base_analysis = analyses.get(holdout_label)
            if not isinstance(base_analysis, dict):
                base_path = args.artifact_dir / f"{holdout_label}_analysis.json"
                if base_path.exists():
                    base_analysis = _read_json(base_path)
                    analyses[holdout_label] = base_analysis
            if isinstance(base_analysis, dict) and _phase_passed_full_composition(base_analysis):
                decisions.append(
                    {
                        "decision": "skip",
                        "reason": f"{holdout_label}_already_passed",
                        "skipped_phase": f"full_composition_rlt_rescue_holdout_{benchmark}",
                    }
                )
                continue
            rescue_holdout_results = _run_command_group(phase_commands)
            commands.extend(rescue_holdout_results)
            rescue_holdout_label = f"full_composition_rlt_rescue_holdout_{benchmark}"
            rescue_holdout_analysis = _read_analysis_after_success(
                results=rescue_holdout_results,
                path=args.artifact_dir / f"{rescue_holdout_label}_analysis.json",
                phase=rescue_holdout_label,
                decisions=decisions,
            )
            if rescue_holdout_analysis is not None:
                analyses[rescue_holdout_label] = rescue_holdout_analysis
                if not _phase_passed_full_composition(rescue_holdout_analysis):
                    decisions.append(
                        {
                            "decision": "continue",
                            "reason": f"{rescue_holdout_label}_did_not_earn_gate",
                            "phase": rescue_holdout_label,
                            "details": rescue_holdout_analysis.get("decisions", []),
                        }
                    )
    elif args.run_composition_rescue_holdout and not cvision_videomme_passed:
        decisions.append(
            {
                "decision": "skip",
                "reason": "full_composition_rescue_holdout_requires_rlt_videomme_pass",
            }
        )
    if args.run_moving_attribute_bracket and cvision_videomme_passed:
        bracket_label = "full_composition_rlt_mvbench_moving_attribute_kr100"
        bracket_results = _run_command_group(moving_attribute_bracket_commands)
        commands.extend(bracket_results)
        bracket_analysis = _read_analysis_after_success(
            results=bracket_results,
            path=args.artifact_dir / f"{bracket_label}_analysis.json",
            phase=bracket_label,
            decisions=decisions,
        )
        if bracket_analysis is not None:
            analyses[bracket_label] = bracket_analysis
            if not _phase_passed_full_composition(bracket_analysis):
                decisions.append(
                    {
                        "decision": "continue",
                        "reason": f"{bracket_label}_did_not_earn_gate",
                        "phase": bracket_label,
                        "details": bracket_analysis.get("decisions", []),
                    }
                )
    elif args.run_moving_attribute_bracket and not cvision_videomme_passed:
        decisions.append(
            {
                "decision": "skip",
                "reason": "moving_attribute_bracket_requires_rlt_videomme_pass",
            }
        )
    if args.run_moving_attribute_holdout_bracket and cvision_videomme_passed:
        bracket_label = "full_composition_rlt_holdout_mvbench_moving_attribute_kr100"
        bracket_results = _run_command_group(moving_attribute_holdout_bracket_commands)
        commands.extend(bracket_results)
        bracket_analysis = _read_analysis_after_success(
            results=bracket_results,
            path=args.artifact_dir / f"{bracket_label}_analysis.json",
            phase=bracket_label,
            decisions=decisions,
        )
        if bracket_analysis is not None:
            analyses[bracket_label] = bracket_analysis
            if not _phase_passed_full_composition(bracket_analysis):
                decisions.append(
                    {
                        "decision": "continue",
                        "reason": "moving_attribute_holdout_bracket_did_not_earn_gate",
                        "phase": bracket_label,
                        "details": bracket_analysis.get("decisions", []),
                    }
                )
    elif args.run_moving_attribute_holdout_bracket and not cvision_videomme_passed:
        decisions.append(
            {
                "decision": "skip",
                "reason": "moving_attribute_holdout_bracket_requires_rlt_videomme_pass",
            }
        )
    if args.run_composition_combined_analysis and cvision_videomme_passed:
        combined_commands = [
            (f"full_composition_rlt_combined_{benchmark}", command)
            for benchmark, command in full_composition_combined_commands.items()
        ] + [
            (f"full_composition_rlt_rescue_combined_{benchmark}", command)
            for benchmark, command in full_composition_rescue_combined_commands.items()
        ]
        for label, command in combined_commands:
            combined_results = _run_command_group([command])
            commands.extend(combined_results)
            combined_analysis = _read_analysis_after_success(
                results=combined_results,
                path=args.artifact_dir / f"{label}_analysis.json",
                phase=label,
                decisions=decisions,
            )
            if combined_analysis is not None:
                analyses[label] = combined_analysis
                if not _phase_passed_full_composition(combined_analysis):
                    decisions.append(
                        {
                            "decision": "continue",
                            "reason": f"{label}_did_not_earn_gate",
                            "phase": label,
                            "details": combined_analysis.get("decisions", []),
                        }
                    )
    elif args.run_composition_combined_analysis and not cvision_videomme_passed:
        decisions.append(
            {
                "decision": "skip",
                "reason": "full_composition_combined_analysis_requires_rlt_videomme_pass",
            }
        )
    if args.run_keep_rate_sweep and cvision_videomme_passed:
        sweep_results: dict[str, Any] = {}
        for rate, phase_commands in keep_rate_sweep_commands.items():
            rate_results = _run_command_group(phase_commands)
            commands.extend(rate_results)
            rate_label = (
                f"cvision_rlt_{args.keep_rate_sweep_benchmark}_kr{int(round(rate * 100)):03d}"
            )
            rate_analysis = _read_analysis_after_success(
                results=rate_results,
                path=args.artifact_dir / f"{rate_label}_analysis.json",
                phase=rate_label,
                decisions=decisions,
            )
            if rate_analysis is not None:
                analyses[rate_label] = rate_analysis
                sweep_results[f"{rate:.6g}"] = {
                    "speedup": rate_analysis.get("all", {}).get(
                        "actual_e2e_speedup_dense_over_sparse"
                    ),
                    "accuracy_delta": rate_analysis.get("all", {}).get(
                        "accuracy_delta_sparse_minus_dense"
                    ),
                    "pass_core": _phase_passed_cvision(rate_analysis),
                }
        analyses[f"cvision_rlt_{args.keep_rate_sweep_benchmark}_keep_rate_sweep"] = {
            "benchmark": args.keep_rate_sweep_benchmark,
            "keep_rates": keep_rates,
            "results": sweep_results,
        }
    elif args.run_keep_rate_sweep and not cvision_videomme_passed:
        decisions.append(
            {
                "decision": "skip",
                "reason": "keep_rate_sweep_requires_rlt_videomme_pass",
            }
        )
    q0b_dense_equivalence_passed_by_benchmark: dict[str, bool] = {}
    if args.run_query_routing_q0b and cvision_videomme_passed:
        failed_benchmarks: set[str] = set()
        for label, phase_commands in query_q0b_commands.items():
            benchmark = next(
                benchmark for benchmark in benchmark_manifests if f"_{benchmark}" in label
            )
            is_dense_equivalence = "_dense_equivalent_" in label
            if benchmark in failed_benchmarks and not is_dense_equivalence:
                decisions.append(
                    {
                        "decision": "skip",
                        "reason": f"query_q0b_{benchmark}_dense_equivalence_failed",
                        "skipped_phase": label,
                    }
                )
                continue
            q0b_results = _run_command_group(phase_commands)
            commands.extend(q0b_results)
            q0b_analysis = _read_analysis_after_success(
                results=q0b_results,
                path=args.artifact_dir / f"{label}_analysis.json",
                phase=label,
                decisions=decisions,
            )
            if q0b_analysis is None:
                if is_dense_equivalence:
                    failed_benchmarks.add(benchmark)
                    q0b_dense_equivalence_passed_by_benchmark[benchmark] = False
                continue
            analyses[label] = q0b_analysis
            if is_dense_equivalence:
                passed = bool(q0b_analysis.get("summary", {}).get("pass_dense_equivalence"))
                q0b_dense_equivalence_passed_by_benchmark[benchmark] = passed
                if not passed:
                    failed_benchmarks.add(benchmark)
                    decisions.append(
                        {
                            "decision": "skip",
                            "reason": f"query_q0b_{benchmark}_dense_equivalence_failed",
                            "skip": [
                                candidate
                                for candidate in query_q0b_commands
                                if f"_{benchmark}" in candidate and candidate != label
                            ],
                        }
                    )
        q0b_gate = _query_q0b_gate(analyses, query_routing_benchmarks)
        analyses["query_routing_q0b_gate"] = q0b_gate
        if not q0b_gate["proceed_to_q1"]:
            decisions.append(
                {
                    "decision": "skip",
                    "reason": "query_routing_q0b_diagnostics_incomplete_or_failed",
                    "details": q0b_gate,
                }
            )
    elif args.run_query_routing_q0b and not cvision_videomme_passed:
        decisions.append(
            {
                "decision": "skip",
                "reason": "query_routing_q0b_requires_rlt_videomme_pass",
            }
        )
    if args.run_query_routing_q1 and cvision_videomme_passed:
        q0b_gate = analyses.get("query_routing_q0b_gate", {})
        q0b_ok = isinstance(q0b_gate, dict) and bool(q0b_gate.get("proceed_to_q1"))
        if not q0b_ok:
            decisions.append(
                {
                    "decision": "skip",
                    "reason": "query_routing_q1_requires_q0b_diagnostics",
                }
            )
        else:
            for label, phase_commands in query_q1_commands.items():
                q1_results = _run_command_group(phase_commands)
                commands.extend(q1_results)
                q1_analysis = _read_analysis_after_success(
                    results=q1_results,
                    path=args.artifact_dir / f"{label}_analysis.json",
                    phase=label,
                    decisions=decisions,
                )
                if q1_analysis is not None:
                    analyses[label] = q1_analysis
                    if not _phase_passed_full_composition(q1_analysis):
                        decisions.append(
                            {
                                "decision": "continue",
                                "reason": f"{label}_did_not_earn_gate",
                                "phase": label,
                                "details": q1_analysis.get("decisions", []),
                            }
                        )
            analyses["query_routing_q1_verdict"] = _query_q1_verdict(
                analyses, query_routing_benchmarks
            )
            if not analyses["query_routing_q1_verdict"]["proceed_to_q2_scalar_query_baseline"]:
                decisions.append(
                    {
                        "decision": "continue",
                        "reason": "query_routing_q1_typed_operator_not_yet_a_winner",
                        "details": analyses["query_routing_q1_verdict"],
                    }
                )
    elif args.run_query_routing_q1 and not cvision_videomme_passed:
        decisions.append(
            {
                "decision": "skip",
                "reason": "query_routing_q1_requires_rlt_videomme_pass",
            }
        )
    if args.run_query_routing_q1b_followup and cvision_videomme_passed:
        q0b_gate = analyses.get("query_routing_q0b_gate", {})
        q0b_ok = isinstance(q0b_gate, dict) and bool(q0b_gate.get("proceed_to_q1"))
        q1_verdict = analyses.get("query_routing_q1_verdict", {})
        q1_by_benchmark = q1_verdict.get("by_benchmark") if isinstance(q1_verdict, dict) else None
        q1_complete = (
            isinstance(q1_by_benchmark, dict)
            and bool(q1_by_benchmark)
            and not any(
                bool(payload.get("missing"))
                for payload in q1_by_benchmark.values()
                if isinstance(payload, dict)
            )
        )
        q1_negative = isinstance(q1_verdict, dict) and not bool(
            q1_verdict.get("proceed_to_q2_scalar_query_baseline")
        )
        if not q0b_ok:
            decisions.append(
                {
                    "decision": "skip",
                    "reason": "query_routing_q1b_requires_q0b_diagnostics",
                }
            )
        elif not q1_complete:
            decisions.append(
                {
                    "decision": "skip",
                    "reason": "query_routing_q1b_requires_q1_verdict",
                }
            )
        elif not q1_negative:
            decisions.append(
                {
                    "decision": "skip",
                    "reason": "query_routing_q1b_is_only_for_negative_q1_verdicts",
                    "details": q1_verdict,
                }
            )
        else:
            for label, phase_commands in query_q1b_commands.items():
                q1b_results = _run_command_group(phase_commands)
                commands.extend(q1b_results)
                q1b_analysis = _read_analysis_after_success(
                    results=q1b_results,
                    path=args.artifact_dir / f"{label}_analysis.json",
                    phase=label,
                    decisions=decisions,
                )
                if q1b_analysis is not None:
                    analyses[label] = q1b_analysis
                    if not _phase_passed_full_composition(q1b_analysis):
                        decisions.append(
                            {
                                "decision": "continue",
                                "reason": f"{label}_did_not_earn_gate",
                                "phase": label,
                                "details": q1b_analysis.get("decisions", []),
                            }
                        )
            analyses["query_routing_q1b_followup_verdict"] = _query_q1b_followup_verdict(analyses)
    elif args.run_query_routing_q1b_followup and not cvision_videomme_passed:
        decisions.append(
            {
                "decision": "skip",
                "reason": "query_routing_q1b_requires_rlt_videomme_pass",
            }
        )
    if args.run_query_routing_q1c_admission_scheduler and cvision_videomme_passed:
        q0b_gate = analyses.get("query_routing_q0b_gate", {})
        q0b_ok = isinstance(q0b_gate, dict) and bool(q0b_gate.get("proceed_to_q1"))
        q1_verdict = analyses.get("query_routing_q1_verdict", {})
        q1_by_benchmark = q1_verdict.get("by_benchmark") if isinstance(q1_verdict, dict) else None
        q1_complete = (
            isinstance(q1_by_benchmark, dict)
            and bool(q1_by_benchmark)
            and not any(
                bool(payload.get("missing"))
                for payload in q1_by_benchmark.values()
                if isinstance(payload, dict)
            )
        )
        q1b_verdict = analyses.get("query_routing_q1b_followup_verdict", {})
        q1b_complete = (
            isinstance(q1b_verdict, dict)
            and bool(q1b_verdict)
            and not bool(q1b_verdict.get("missing"))
        )
        if not q0b_ok:
            decisions.append(
                {
                    "decision": "skip",
                    "reason": "query_routing_q1c_requires_q0b_diagnostics",
                }
            )
        elif not q1_complete:
            decisions.append(
                {
                    "decision": "skip",
                    "reason": "query_routing_q1c_requires_q1_verdict",
                }
            )
        elif not q1b_complete:
            decisions.append(
                {
                    "decision": "skip",
                    "reason": "query_routing_q1c_requires_q1b_verdict",
                }
            )
        else:
            for label, phase_commands in query_q1c_commands.items():
                q1c_results = _run_command_group(phase_commands)
                commands.extend(q1c_results)
                q1c_analysis = _read_analysis_after_success(
                    results=q1c_results,
                    path=args.artifact_dir / f"{label}_analysis.json",
                    phase=label,
                    decisions=decisions,
                )
                if q1c_analysis is not None:
                    analyses[label] = q1c_analysis
                    if not _phase_passed_full_composition(q1c_analysis):
                        decisions.append(
                            {
                                "decision": "continue",
                                "reason": f"{label}_did_not_earn_gate",
                                "phase": label,
                                "details": q1c_analysis.get("decisions", []),
                            }
                        )
            q1c_verdict = _query_q1c_admission_scheduler_verdict(analyses)
            analyses["query_routing_q1c_admission_scheduler_verdict"] = q1c_verdict
            if not q1c_verdict["proceed_to_holdout_admission_scheduler"]:
                decisions.append(
                    {
                        "decision": "continue",
                        "reason": "query_routing_q1c_admission_scheduler_not_yet_a_winner",
                        "details": q1c_verdict,
                    }
                )
    elif args.run_query_routing_q1c_admission_scheduler and not cvision_videomme_passed:
        decisions.append(
            {
                "decision": "skip",
                "reason": "query_routing_q1c_requires_rlt_videomme_pass",
            }
        )

    _write_json(
        summary_path,
        {
            "schema_version": SCHEMA_VERSION,
            "budget": budget,
            "commands": commands,
            "decisions": decisions
            or [{"decision": "continue", "reason": "all_requested_phases_complete"}],
            "analyses": analyses,
            "paper_feedback": _paper_feedback(analyses=analyses, decisions=decisions),
        },
    )
    print(json.dumps({"summary": str(summary_path), "decisions": decisions}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
