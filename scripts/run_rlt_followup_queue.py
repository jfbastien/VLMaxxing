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
DEFAULT_ARTIFACT_DIR = Path("research/experiments/2026/artifacts/rlt_followup_queue")
DEFAULT_MODEL_PATH = Path.home() / "models" / "gemma-4-e4b-it-4bit"
DEFAULT_VIDEOMME_MANIFEST = Path("research/benchmark_manifests/videomme_combined_v1_n60.toml")
DEFAULT_SMOKE_MANIFEST = Path("research/benchmark_manifests/videomme_dev_v1.toml")
DEFAULT_TOMATO_MANIFEST = Path("research/benchmark_manifests/tomato_motion_dev_v2.toml")
DEFAULT_MVBENCH_MANIFEST = Path("research/benchmark_manifests/mvbench_motion_dev_v2.toml")

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
}


def _run(command: list[str], *, allow_failure: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    payload = {
        "command": command,
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


def _gemma_admission_commands(
    *,
    artifact_dir: Path,
    manifest: Path,
    model_path: Path,
    frame_count: int,
    n_items: int,
    rss_guard_mb: int,
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
    label: str,
    expected_items: int,
    score_mode: str = "rlt_topk",
) -> list[list[str]]:
    dense_jsonl = artifact_dir / f"{label}_dense.jsonl"
    dense_summary = artifact_dir / f"{label}_dense_summary.json"
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
        "0.5",
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
    ]
    return [dense, sparse, analyze]


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
    # failures independent of sparse execution. Ceiling and bucket E2E gates
    # are required before expensive expansion cells can run.
    return bool(
        analysis.get("pass_complete_pairing")
        and analysis.get("pass_fidelity")
        and analysis.get("pass_sparse_vision")
        and analysis.get("pass_e2e_positive")
        and analysis.get("pass_bucket_e2e_positive")
        and analysis.get("pass_parse_failure_delta")
        and analysis.get("pass_parse_failure_rate")
        and analysis.get("pass_ceiling_explained")
    )


def _phase_passed_prefill_same_path(analysis: dict[str, Any]) -> bool:
    speedup = analysis.get("e2e_speedup_dense_over_pruned")
    return bool(
        analysis.get("total_prefill_reduction_ms", 0.0) > 0.0
        and isinstance(speedup, (int, float))
        and float(speedup) > 1.0
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--gemma-model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--videomme-manifest", type=Path, default=DEFAULT_VIDEOMME_MANIFEST)
    parser.add_argument("--smoke-manifest", type=Path, default=DEFAULT_SMOKE_MANIFEST)
    parser.add_argument("--tomato-manifest", type=Path, default=DEFAULT_TOMATO_MANIFEST)
    parser.add_argument("--mvbench-manifest", type=Path, default=DEFAULT_MVBENCH_MANIFEST)
    parser.add_argument("--frame-count", type=int, default=8)
    parser.add_argument("--rss-guard-mb", type=int, default=9000)
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
    parser.add_argument("--max-planned-hours", type=float, default=19.0)
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
    if args.cooldown_after_microbench_seconds < 0:
        raise SystemExit("--cooldown-after-microbench-seconds must be nonnegative")
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
            label="cvision_maxmin_mvbench",
            expected_items=30,
            score_mode="max_min_diversity",
        ),
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
    if args.dry_run:
        _write_json(
            summary_path,
            {
                "schema_version": SCHEMA_VERSION,
                "dry_run": True,
                "budget": budget,
                "planned_commands": planned,
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
                                "expansion and max-min triangulation unless it passes "
                                "fidelity, parse-failure, sparse-vision, ceiling, bucket, "
                                "and E2E gates."
                            ),
                        ]
                        if args.run_cvision_rlt
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
