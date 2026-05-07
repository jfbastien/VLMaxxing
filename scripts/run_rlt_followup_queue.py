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
DEFAULT_ARTIFACT_DIR = Path("research/experiments/2026/artifacts/rlt_followup_queue")
DEFAULT_MODEL_PATH = Path.home() / "models" / "gemma-4-e4b-it-4bit"
DEFAULT_VIDEOMME_MANIFEST = Path("research/benchmark_manifests/videomme_combined_v1_n60.toml")
DEFAULT_SMOKE_MANIFEST = Path("research/benchmark_manifests/videomme_dev_v1.toml")
DEFAULT_TOMATO_MANIFEST = Path("research/benchmark_manifests/tomato_motion_dev_v2.toml")
DEFAULT_MVBENCH_MANIFEST = Path("research/benchmark_manifests/mvbench_motion_dev_v2.toml")

PHASE_ESTIMATES_HOURS = {
    "prefill-step-1500-n20": [0.4, 0.9],
    "prefill-step-4096-n20": [0.4, 0.9],
    "cvision-rlt-smoke": [0.1, 0.4],
    "cvision-rlt-videomme-n20": [0.8, 1.8],
    "cvision-rlt-tomato-n30": [1.0, 2.0],
    "cvision-rlt-mvbench-n30": [1.0, 2.0],
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
) -> list[list[str]]:
    dense_jsonl = artifact_dir / f"{label}_dense.jsonl"
    dense_summary = artifact_dir / f"{label}_dense_summary.json"
    sparse_jsonl = artifact_dir / f"{label}_rlt_topk.jsonl"
    sparse_summary = artifact_dir / f"{label}_rlt_topk_summary.json"
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
        "rlt_topk",
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
            "Gemma C-VISION sparse execution with fixed-K RLT same-position motion "
            "scores as the token scorer; scatter-back preserves prompt geometry."
        ),
    ]
    return [dense, sparse, analyze]


def _run_command_group(
    commands: list[list[str]], *, allow_failure: bool = True
) -> list[dict[str, Any]]:
    return [_run(command, allow_failure=allow_failure) for command in commands]


def _phase_passed_cvision(analysis: dict[str, Any]) -> bool:
    return bool(
        analysis.get("pass_complete_pairing")
        and analysis.get("pass_fidelity")
        and analysis.get("pass_sparse_vision")
        and analysis.get("pass_e2e_positive")
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
    parser.add_argument("--prefill-diagnostic-n-items", type=int, default=20)
    parser.add_argument("--cvision-n-items", type=int, default=20)
    parser.add_argument("--run-prefill-diagnostics", action="store_true")
    parser.add_argument("--run-cvision-rlt", action="store_true")
    parser.add_argument("--run-cvision-expansion", action="store_true")
    parser.add_argument("--max-planned-hours", type=float, default=8.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()

    if args.prefill_diagnostic_n_items < 1:
        raise SystemExit("--prefill-diagnostic-n-items must be positive")
    if args.cvision_n_items < 1:
        raise SystemExit("--cvision-n-items must be positive")
    phases: list[str] = []
    if args.run_prefill_diagnostics:
        phases.append("prefill-step-1500-n20")
        phases.append("prefill-step-4096-n20")
    if args.run_cvision_rlt:
        phases.extend(["cvision-rlt-smoke", "cvision-rlt-videomme-n20"])
    if args.run_cvision_expansion:
        phases.extend(["cvision-rlt-tomato-n30", "cvision-rlt-mvbench-n30"])
    budget = _budget(phases)
    if budget["high_hours"] > args.max_planned_hours:
        raise SystemExit(
            f"planned high estimate {budget['high_hours']:.1f}h exceeds "
            f"--max-planned-hours {args.max_planned_hours:.1f}h"
        )
    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.summary or args.artifact_dir / "queue_summary.json"
    planned: list[dict[str, Any]] = []

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
        ),
    }
    if args.run_prefill_diagnostics:
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
    if args.run_cvision_expansion:
        for benchmark, phase_commands in expansion_commands.items():
            planned.extend(
                {"phase": f"cvision_rlt_{benchmark}_if_videomme_passes", "command": c}
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
                    (
                        "Run prefill_step_size=1500 first; skip 4096 if "
                        "same-path chunking makes RLT faster."
                    ),
                    "Run C-VISION RLT n=1 smoke; skip VideoMME decision if smoke fails.",
                    (
                        "Run C-VISION RLT VideoMME n=20; skip TOMATO/MVBench "
                        "expansion unless it passes fidelity, sparse-vision, and E2E gates."
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
        commands.extend(_run_command_group(prefill_1500_commands))
        analysis_1500 = _read_json(args.artifact_dir / "h3b_prefill_step1500_analysis.json")
        analyses["h3b_prefill_step1500"] = analysis_1500
        if _phase_passed_prefill_same_path(analysis_1500):
            decisions.append(
                {
                    "decision": "skip",
                    "reason": "prefill_step_1500_confirmed_same_path_speedup",
                    "skipped_phase": "prefill_step_4096",
                }
            )
        else:
            commands.extend(_run_command_group(prefill_4096_commands))
            analyses["h3b_prefill_step4096"] = _read_json(
                args.artifact_dir / "h3b_prefill_step4096_analysis.json"
            )
    cvision_videomme_passed = False
    if args.run_cvision_rlt:
        commands.extend(_run_command_group(cvision_smoke_commands))
        smoke_analysis = _read_json(args.artifact_dir / "cvision_rlt_smoke_analysis.json")
        analyses["cvision_rlt_smoke"] = smoke_analysis
        if not smoke_analysis.get("pass_complete_pairing"):
            decisions.append(
                {
                    "decision": "stop",
                    "reason": "cvision_rlt_smoke_failed_pairing",
                    "skip": ["cvision_rlt_videomme", "cvision_rlt_expansion"],
                }
            )
        else:
            commands.extend(_run_command_group(cvision_videomme_commands))
            videomme_analysis = _read_json(args.artifact_dir / "cvision_rlt_videomme_analysis.json")
            analyses["cvision_rlt_videomme"] = videomme_analysis
            cvision_videomme_passed = _phase_passed_cvision(videomme_analysis)
            if not cvision_videomme_passed:
                decisions.append(
                    {
                        "decision": "skip",
                        "reason": "cvision_rlt_videomme_gate_failed",
                        "skip": ["cvision_rlt_expansion"],
                    }
                )
    if args.run_cvision_expansion and cvision_videomme_passed:
        for benchmark, phase_commands in expansion_commands.items():
            commands.extend(_run_command_group(phase_commands))
            analyses[f"cvision_rlt_{benchmark}"] = _read_json(
                args.artifact_dir / f"cvision_rlt_{benchmark}_analysis.json"
            )
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
