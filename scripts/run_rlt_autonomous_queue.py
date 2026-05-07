#!/usr/bin/env python3
"""Run the RLT/VLMaxxing queue in early-cancel order.

This queue intentionally starts with CPU-only evidence. It stops before model
work when preregistered null gates fire or when required MLX smoke artifacts
are absent.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, cast

SCHEMA_VERSION = "rlt_autonomous_queue_v1"
DEFAULT_ARTIFACT_DIR = Path("research/experiments/2026/artifacts/rlt_autonomous_queue")
DEFAULT_GEMMA_MODEL_PATH = Path.home() / "models" / "gemma-4-e4b-it-4bit"
DEFAULT_GEMMA_MANIFEST = Path("research/benchmark_manifests/videomme_combined_v1_n60.toml")
DEFAULT_GEMMA_SMOKE_MANIFEST = Path("research/benchmark_manifests/videomme_dev_v1.toml")
PHASE_ESTIMATES_HOURS = {
    "RLT-1-preflight": [0.02, 0.05],
    "RLT-1-profiler-synthetic": [0.02, 0.10],
    "RLT-1-profiler-n60": [0.25, 0.50],
    "RLT-2G-gemma-smoke": [0.25, 0.75],
    "RLT-2G-gemma-n60": [7.5, 10.5],
    "RLT-3G-A": [2.0, 6.0],
    "RLT-3G-B": [2.0, 6.0],
    "RLT-4Q": [7.0, 10.0],
    "RLT-5G": [1.5, 6.0],
    "RLT-5Q": [7.0, 10.0],
    "threshold-extension": [10.0, 20.0],
}


def _run(command: list[str], *, allow_failure: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    elapsed = time.perf_counter() - started
    payload = {
        "command": command,
        "returncode": completed.returncode,
        "elapsed_seconds": elapsed,
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


def _total_budget(selected: list[str]) -> dict[str, float]:
    low = 0.0
    high = 0.0
    for phase in selected:
        estimate = PHASE_ESTIMATES_HOURS[phase]
        low += estimate[0]
        high += estimate[1]
    return {"low_hours": low, "high_hours": high}


def _write_summary(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _analysis_blocks_downstream(analysis: dict[str, Any]) -> bool:
    skip_phases = {str(phase) for phase in analysis.get("skip_phases", [])}
    if skip_phases.intersection({"RLT-3G-A", "RLT-3G-B", "RLT-4Q", "RLT-5G", "RLT-5Q"}):
        return True
    return any(
        decision.get("decision") in {"stop", "stop_or_contract"}
        for decision in analysis.get("decisions", [])
    )


def _run_gemma_admission_cell(
    *,
    artifact_dir: Path,
    manifest: Path,
    model_path: Path,
    frame_count: int,
    n_items: int,
    rss_guard_mb: int,
    label: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    jsonl_path = artifact_dir / f"{label}.jsonl"
    summary_path = artifact_dir / f"{label}_summary.json"
    analysis_path = artifact_dir / f"{label}_analysis.json"
    commands: list[dict[str, Any]] = []
    command = [
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
        "--model-path",
        str(model_path),
        "--rss-guard-mb",
        str(rss_guard_mb),
        "--output",
        str(jsonl_path),
        "--summary",
        str(summary_path),
    ]
    if n_items > 0:
        command.extend(["--n-items", str(n_items)])
    commands.append(_run(command))
    commands.append(
        _run(
            [
                sys.executable,
                "scripts/analyze_gemma_admission.py",
                "--jsonl",
                str(jsonl_path),
                "--summary-json",
                str(summary_path),
                "--output",
                str(analysis_path),
            ]
        )
    )
    return commands, _read_json(analysis_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--frame-count", type=int, default=8)
    parser.add_argument("--prefill-split-smoke-json", type=Path)
    parser.add_argument("--run-model-smokes", action="store_true")
    parser.add_argument("--run-gemma-decision-cell", action="store_true")
    parser.add_argument("--gemma-model-path", type=Path, default=DEFAULT_GEMMA_MODEL_PATH)
    parser.add_argument("--gemma-manifest", type=Path, default=DEFAULT_GEMMA_MANIFEST)
    parser.add_argument("--gemma-smoke-manifest", type=Path, default=DEFAULT_GEMMA_SMOKE_MANIFEST)
    parser.add_argument("--gemma-rss-guard-mb", type=int, default=9000)
    parser.add_argument("--run-swa-smoke", action="store_true")
    parser.add_argument("--max-planned-hours", type=float, default=30.0)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()

    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.summary or args.artifact_dir / "queue_summary.json"
    commands: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    selected_budget = ["RLT-1-preflight", "RLT-1-profiler-synthetic"]
    if args.manifest is not None:
        selected_budget.append("RLT-1-profiler-n60")
    if args.run_model_smokes:
        selected_budget.append("RLT-2G-gemma-smoke")
    if args.run_gemma_decision_cell:
        selected_budget.append("RLT-2G-gemma-n60")
    budget = _total_budget(selected_budget)
    if budget["high_hours"] > args.max_planned_hours:
        raise SystemExit(
            f"planned queue high estimate {budget['high_hours']:.1f}h exceeds "
            f"--max-planned-hours {args.max_planned_hours:.1f}h"
        )

    preflight_path = args.artifact_dir / "rlt1_preflight.json"
    commands.append(
        _run(
            [
                sys.executable,
                "scripts/preflight_rlt_vlmax.py",
                "--phase",
                "RLT-1",
                "--output",
                str(preflight_path),
            ]
        )
    )
    preflight = _read_json(preflight_path)
    if not preflight.get("ready"):
        decisions.append({"decision": "stop", "reason": "rlt1_preflight_failed"})
        _write_summary(
            summary_path,
            {
                "schema_version": SCHEMA_VERSION,
                "ready_for_model_runs": False,
                "budget": budget,
                "commands": commands,
                "decisions": decisions,
            },
        )
        return 1

    profile_jsonl = args.artifact_dir / "rlt_mask_profile.jsonl"
    profile_summary = args.artifact_dir / "rlt_mask_profile_summary.json"
    profile_command = [
        sys.executable,
        "scripts/profile_rlt_masks.py",
        "--synthetic",
        "exact_static",
        "--synthetic",
        "single_frame_repeat",
        "--synthetic",
        "all_motion",
        "--synthetic",
        "fixed_camera_positive",
        "--synthetic",
        "camera_pan",
        "--frame-count",
        str(args.frame_count),
        "--compare-pixel-novelty",
        "--project-grid-shape",
        "16x16",
        "--overwrite",
        "--output-jsonl",
        str(profile_jsonl),
        "--summary-json",
        str(profile_summary),
    ]
    if args.manifest is not None:
        profile_command.extend(["--manifest", str(args.manifest)])
    commands.append(_run(profile_command))

    analysis_path = args.artifact_dir / "rlt_mask_profile_analysis.json"
    commands.append(
        _run(
            [
                sys.executable,
                "scripts/analyze_rlt_mask_profile.py",
                "--profile-jsonl",
                str(profile_jsonl),
                "--output",
                str(analysis_path),
            ]
        )
    )
    analysis = _read_json(analysis_path)
    decisions.extend(analysis["decisions"])
    stop_reasons = {
        "positive_control_reduction_failed",
        "rlt_pixel_novelty_strong_co_cover",
    }
    if any(decision.get("reason") in stop_reasons for decision in analysis["decisions"]):
        _write_summary(
            summary_path,
            {
                "schema_version": SCHEMA_VERSION,
                "ready_for_model_runs": False,
                "budget": budget,
                "commands": commands,
                "decisions": decisions,
                "analysis": analysis,
            },
        )
        return 0

    gemma_analyses: dict[str, Any] = {}
    if args.run_model_smokes:
        if not args.gemma_model_path.exists():
            raise SystemExit(f"Gemma model path missing: {args.gemma_model_path}")
        gemma_commands, gemma_smoke_analysis = _run_gemma_admission_cell(
            artifact_dir=args.artifact_dir,
            manifest=args.gemma_smoke_manifest,
            model_path=args.gemma_model_path,
            frame_count=args.frame_count,
            n_items=1,
            rss_guard_mb=args.gemma_rss_guard_mb,
            label="rlt2g_gemma_rlt_smoke",
        )
        commands.extend(gemma_commands)
        gemma_analyses["rlt2g_gemma_rlt_smoke"] = gemma_smoke_analysis
        decisions.extend(gemma_smoke_analysis["decisions"])
        if _analysis_blocks_downstream(gemma_smoke_analysis):
            _write_summary(
                summary_path,
                {
                    "schema_version": SCHEMA_VERSION,
                    "ready_for_model_runs": False,
                    "budget": budget,
                    "commands": commands,
                    "decisions": decisions,
                    "analysis": analysis,
                    "gemma_analyses": gemma_analyses,
                },
            )
            return 0

    if args.run_gemma_decision_cell:
        if not args.gemma_model_path.exists():
            raise SystemExit(f"Gemma model path missing: {args.gemma_model_path}")
        gemma_commands, gemma_decision_analysis = _run_gemma_admission_cell(
            artifact_dir=args.artifact_dir,
            manifest=args.gemma_manifest,
            model_path=args.gemma_model_path,
            frame_count=args.frame_count,
            n_items=0,
            rss_guard_mb=args.gemma_rss_guard_mb,
            label="rlt2g_gemma_rlt_decision",
        )
        commands.extend(gemma_commands)
        gemma_analyses["rlt2g_gemma_rlt_decision"] = gemma_decision_analysis
        decisions.extend(gemma_decision_analysis["decisions"])
        if _analysis_blocks_downstream(gemma_decision_analysis):
            _write_summary(
                summary_path,
                {
                    "schema_version": SCHEMA_VERSION,
                    "ready_for_model_runs": False,
                    "budget": budget,
                    "commands": commands,
                    "decisions": decisions,
                    "analysis": analysis,
                    "gemma_analyses": gemma_analyses,
                },
            )
            return 0

    rlt3_preflight_path = args.artifact_dir / "rlt3gb_preflight.json"
    rlt3_command = [
        sys.executable,
        "scripts/preflight_rlt_vlmax.py",
        "--phase",
        "RLT-3G-B",
        "--output",
        str(rlt3_preflight_path),
    ]
    if args.prefill_split_smoke_json is not None:
        rlt3_command.extend(["--prefill-split-smoke-json", str(args.prefill_split_smoke_json)])
    commands.append(_run(rlt3_command, allow_failure=True))
    rlt3_preflight = _read_json(rlt3_preflight_path)
    if not rlt3_preflight.get("ready"):
        decisions.append({"decision": "block_h3b", "reason": "prefill_split_smoke_missing"})

    rlt5_preflight_path = args.artifact_dir / "rlt5g_preflight.json"
    rlt5_command = [
        sys.executable,
        "scripts/preflight_rlt_vlmax.py",
        "--phase",
        "RLT-5G",
        "--output",
        str(rlt5_preflight_path),
    ]
    if args.run_swa_smoke:
        rlt5_command.append("--run-swa-smoke")
    commands.append(_run(rlt5_command, allow_failure=True))
    rlt5_preflight = _read_json(rlt5_preflight_path)
    if not rlt5_preflight.get("ready"):
        decisions.append({"decision": "block_h4a_gemma", "reason": "swa_functional_smoke_missing"})

    _write_summary(
        summary_path,
        {
            "schema_version": SCHEMA_VERSION,
            "ready_for_model_runs": rlt3_preflight.get("ready", False),
            "budget": budget,
            "phase_estimates_hours": PHASE_ESTIMATES_HOURS,
            "commands": commands,
            "decisions": decisions,
            "analysis": analysis,
            "gemma_analyses": gemma_analyses,
            "rlt3gb_preflight": rlt3_preflight,
            "rlt5g_preflight": rlt5_preflight,
        },
    )
    print(json.dumps({"summary": str(summary_path), "decisions": decisions}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
