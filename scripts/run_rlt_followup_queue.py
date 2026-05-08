#!/usr/bin/env python3
"""Run post-H3B RLT/VLMaxxing follow-up experiments with early cancellation."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
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
    "full-composition-rlt-combined-videomme-n60-analysis": [0.02, 0.08],
    "full-composition-rlt-combined-tomato-n60-analysis": [0.02, 0.08],
    "full-composition-rlt-combined-mvbench-n60-analysis": [0.02, 0.08],
    "full-composition-rlt-rescue-combined-videomme-n60-analysis": [0.02, 0.08],
    "full-composition-rlt-rescue-combined-tomato-n60-analysis": [0.02, 0.08],
    "full-composition-rlt-rescue-combined-mvbench-n60-analysis": [0.02, 0.08],
    "cvision-kr-sweep-tomato": [1.2, 2.4],
    "cvision-kr-sweep-mvbench": [1.2, 2.4],
    "cvision-kr-sweep-videomme": [1.4, 3.0],
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
        dense_jsonl = artifact_dir / f"{label}_dense.jsonl"
        dense_summary = artifact_dir / f"{label}_dense_summary.json"
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
        "0.5",
        "--prune-placeholders",
        "rlt",
        "--vision-tower-keep-rate",
        f"{vision_keep_rate:.6g}",
        "--vision-tower-score-mode",
        "rlt_topk",
        "--output",
        str(composed_jsonl),
        "--summary",
        str(composed_summary),
    ]
    if n_items > 0:
        dense.extend(["--n-items", str(n_items)])
        composed.extend(["--n-items", str(n_items)])
    if group_keep_rates:
        composed.extend(["--group-keep-rates", _format_group_keep_rates(group_keep_rates)])
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
    return [dense, composed, analyze]


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


def _parse_keep_rates(raw: str) -> list[float]:
    rates = [float(part.strip()) for part in raw.replace(",", " ").split() if part.strip()]
    if not rates:
        raise ValueError("at least one keep rate is required")
    for rate in rates:
        if not (0.0 < rate <= 1.0):
            raise ValueError(f"keep rates must be in (0, 1], got {rate}")
    return rates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
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
    if args.run_composition_combined_analysis and not args.run_cvision_rlt:
        raise SystemExit("--run-composition-combined-analysis requires --run-cvision-rlt")
    if args.run_keep_rate_sweep and not args.run_cvision_rlt:
        raise SystemExit("--run-keep-rate-sweep requires --run-cvision-rlt")
    if args.cooldown_after_microbench_seconds < 0:
        raise SystemExit("--cooldown-after-microbench-seconds must be nonnegative")
    if args.mlx_memory_limit_gb < 0.0:
        raise SystemExit("--mlx-memory-limit-gb must be nonnegative")
    if args.composition_prefill_step_size <= 0:
        raise SystemExit("--composition-prefill-step-size must be positive")
    keep_rates = _parse_keep_rates(args.cvision_keep_rates)
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
            expected_items=30,
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
            expected_items=30,
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
            expected_items=30,
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
            expected_items=30,
            score_mode="max_min_diversity",
        ),
    }
    benchmark_manifests = {
        "videomme": args.videomme_manifest,
        "tomato": args.tomato_manifest,
        "mvbench": args.mvbench_manifest,
    }
    benchmark_expected_items = {
        "videomme": args.cvision_n_items,
        "tomato": 30,
        "mvbench": 30,
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
        "videomme": 30,
        "tomato": 30,
        "mvbench": 30,
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
        expected_items=30,
        rss_guard_mb=args.rss_guard_mb,
        mlx_memory_limit_gb=args.mlx_memory_limit_gb,
        benchmark="mvbench",
        prefill_step_size=args.composition_prefill_step_size,
        label="full_composition_rlt_mvbench_moving_attribute_kr100",
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
                                "Run pooled dev+holdout n=60 analyzer passes only after "
                                "RLT VideoMME core gates pass. These are analyzer-only "
                                "commands and require the corresponding dev and holdout "
                                "JSONLs to exist."
                            )
                        ]
                        if args.run_composition_combined_analysis
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

    _write_json(
        summary_path,
        {
            "schema_version": SCHEMA_VERSION,
            "budget": budget,
            "commands": commands,
            "decisions": decisions
            or [{"decision": "continue", "reason": "all_requested_phases_complete"}],
            "analyses": analyses,
        },
    )
    print(json.dumps({"summary": str(summary_path), "decisions": decisions}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
