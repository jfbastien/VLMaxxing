#!/usr/bin/env python3
"""Run the RLT/VLMaxxing queue in early-cancel order.

This queue intentionally starts with CPU-only evidence. It stops before model
work when preregistered null gates fire or when required MLX smoke artifacts
are absent.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, cast

SCHEMA_VERSION = "rlt_autonomous_queue_v2"
DEFAULT_ARTIFACT_DIR = Path("research/experiments/2026/artifacts/rlt_autonomous_queue")
DEFAULT_GEMMA_MODEL_PATH = Path.home() / "models" / "gemma-4-e4b-it-4bit"
DEFAULT_SWA_SMOKE_MODEL_ID = str(DEFAULT_GEMMA_MODEL_PATH)
DEFAULT_GEMMA_MANIFEST = Path("research/benchmark_manifests/videomme_combined_v1_n60.toml")
DEFAULT_GEMMA_SMOKE_MANIFEST = Path("research/benchmark_manifests/videomme_dev_v1.toml")
DEFAULT_DECISION_LOG = Path("research/decision-log.md")
DEFAULT_POSITIVE_CONTROL_CLIPS = [
    Path("data/corpus/derived/hall_monitor_cif_standard_h264_crf18_g30.mp4")
]
DEFAULT_THRESHOLD_SWEEP = [0.05, 0.10, 0.20, 0.50, 1.00]
PHASE_ESTIMATES_HOURS = {
    "RLT-1-preflight": [0.02, 0.05],
    "RLT-1-profiler-synthetic": [0.02, 0.10],
    "RLT-1-profiler-n60": [0.25, 0.50],
    "RLT-2G-gemma-smoke": [0.25, 0.75],
    "RLT-2G-gemma-n60": [7.5, 10.5],
    "RLT-3G-B-prefill-smoke": [0.25, 0.50],
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


def _file_sha256(path: Path | None) -> str | None:
    if path is None:
        return None
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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


def _repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def _append_decision_log(
    path: Path,
    *,
    summary_path: Path,
    decisions: list[dict[str, Any]],
) -> None:
    if not decisions:
        return
    date = dt.date.today().isoformat()
    phase_by_reason = {
        "rlt1_preflight_failed": "RLT-1",
        "synthetic_mask_gate_failed": "RLT-1",
        "positive_control_reduction_failed": "RLT-1",
        "real_positive_control_reduction_failed": "RLT-1",
        "threshold_monotonicity_failed": "RLT-1",
        "rlt_pixel_novelty_strong_co_cover": "RLT-1.5",
        "gemma_admission_quality_gate_failed": "RLT-2G",
        "gemma_admission_overhead_dominated": "RLT-2G",
        "prefill_split_smoke_missing": "RLT-3G-B",
        "swa_functional_smoke_missing": "RLT-5G",
    }
    stop_decisions = [
        decision
        for decision in decisions
        if str(decision.get("decision")) in {"stop", "contract", "block_h3b", "block_h4a_gemma"}
    ]
    if not stop_decisions:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for decision in stop_decisions:
            reason = str(decision.get("reason", "unknown"))
            phase = str(decision.get("phase") or phase_by_reason.get(reason, "RLT-unknown"))
            handle.write(
                "\n"
                f"| {date}: {phase} autonomous queue early stop | Screening result | "
                f"[summary]({_repo_rel(summary_path)}) | Reason: {reason}. "
                "Reopen by fixing the failing gate or rerunning with a replacement artifact under "
                "the same preregistered analyzer. |\n"
            )


def _write_terminal_summary(
    path: Path,
    payload: dict[str, Any],
    *,
    decision_log: Path | None,
) -> None:
    _write_summary(path, payload)
    if decision_log is not None:
        _append_decision_log(
            decision_log,
            summary_path=path,
            decisions=cast(list[dict[str, Any]], payload.get("decisions", [])),
        )


def _planned_command(command: list[str]) -> dict[str, Any]:
    return {"command": command}


def _analysis_blocks_downstream(analysis: dict[str, Any]) -> bool:
    known_decisions = {"continue", "stop", "contract", "skip_h1_5b", "downgrade"}
    for decision in analysis.get("decisions", []):
        value = str(decision.get("decision"))
        if value not in known_decisions:
            raise ValueError(f"unknown analyzer decision {value!r}")
    skip_phases = {str(phase) for phase in analysis.get("skip_phases", [])}
    if skip_phases.intersection({"RLT-3G-A", "RLT-3G-B", "RLT-4Q", "RLT-5G", "RLT-5Q"}):
        return True
    return any(decision.get("decision") == "stop" for decision in analysis.get("decisions", []))


def _run_gemma_admission_cell(
    *,
    artifact_dir: Path,
    manifest: Path,
    model_path: Path,
    frame_count: int,
    n_items: int,
    rss_guard_mb: int,
    n_warmup: int,
    enforce_overhead_gate: bool,
    timing_min_n: int,
    cell_type: str,
    label: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    analysis_path = artifact_dir / f"{label}_analysis.json"
    commands: list[dict[str, Any]] = []
    planned = _gemma_admission_commands(
        artifact_dir=artifact_dir,
        manifest=manifest,
        model_path=model_path,
        frame_count=frame_count,
        n_items=n_items,
        rss_guard_mb=rss_guard_mb,
        n_warmup=n_warmup,
        enforce_overhead_gate=enforce_overhead_gate,
        timing_min_n=timing_min_n,
        cell_type=cell_type,
        label=label,
    )
    for command in planned:
        commands.append(_run(command))
    return commands, _read_json(analysis_path)


def _profile_command(
    *,
    artifact_dir: Path,
    manifest: Path | None,
    frame_count: int,
    positive_control_clips: list[Path],
) -> list[str]:
    command = [
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
        str(frame_count),
        "--compare-pixel-novelty",
        "--project-grid-shape",
        "16x16",
        "--overwrite",
        "--output-jsonl",
        str(artifact_dir / "rlt_mask_profile.jsonl"),
        "--summary-json",
        str(artifact_dir / "rlt_mask_profile_summary.json"),
    ]
    for threshold in DEFAULT_THRESHOLD_SWEEP:
        command.extend(["--threshold-sweep", f"{threshold:g}"])
    if manifest is not None:
        command.extend(["--manifest", str(manifest)])
    for clip in positive_control_clips:
        if clip.exists():
            command.extend(["--clip", str(clip), "--clip-group", "fixed_camera_positive"])
    return command


def _prefill_split_smoke_command(
    *,
    artifact_dir: Path,
    output: Path,
    manifest: Path,
    model_path: Path,
    frame_count: int,
    rss_guard_mb: int,
) -> list[str]:
    command = [
        sys.executable,
        "scripts/build_rlt_prefill_split_smoke.py",
        "--artifact-dir",
        str(artifact_dir / "prefill_split_smoke"),
        "--output",
        str(output),
        "--manifest",
        str(manifest),
        "--model-path",
        str(model_path),
        "--frame-count",
        str(frame_count),
        "--n-items",
        "1",
    ]
    if rss_guard_mb > 0:
        command.extend(["--rss-guard-mb", str(rss_guard_mb)])
    return command


def _rlt3_preflight_command(
    *,
    artifact_dir: Path,
    prefill_split_smoke_json: Path | None,
) -> list[str]:
    command = [
        sys.executable,
        "scripts/preflight_rlt_vlmax.py",
        "--phase",
        "RLT-3G-B",
        "--output",
        str(artifact_dir / "rlt3gb_preflight.json"),
    ]
    if prefill_split_smoke_json is not None:
        command.extend(["--prefill-split-smoke-json", str(prefill_split_smoke_json)])
    return command


def _gemma_admission_commands(
    *,
    artifact_dir: Path,
    manifest: Path,
    model_path: Path,
    frame_count: int,
    n_items: int,
    rss_guard_mb: int,
    n_warmup: int,
    enforce_overhead_gate: bool,
    timing_min_n: int,
    cell_type: str,
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
        "--model-path",
        str(model_path),
        "--rss-guard-mb",
        str(rss_guard_mb),
        "--n-warmup",
        str(n_warmup),
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
        "--timing-min-n",
        str(timing_min_n),
        "--cell-type",
        cell_type,
    ]
    if not enforce_overhead_gate:
        analyze_command.append("--no-overhead-gate")
    return [run_command, analyze_command]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--frame-count", type=int, default=8)
    parser.add_argument("--prefill-split-smoke-json", type=Path)
    parser.add_argument(
        "--auto-prefill-split-smoke",
        action="store_true",
        help=(
            "Run the dense n=1 Gemma prefill-split smoke builder before H3B preflight. "
            "This is the autonomous path for unblocking RLT-3G-B."
        ),
    )
    parser.add_argument("--run-model-smokes", action="store_true")
    parser.add_argument("--run-gemma-decision-cell", action="store_true")
    parser.add_argument("--gemma-model-path", type=Path, default=DEFAULT_GEMMA_MODEL_PATH)
    parser.add_argument("--gemma-manifest", type=Path, default=DEFAULT_GEMMA_MANIFEST)
    parser.add_argument("--gemma-smoke-manifest", type=Path, default=DEFAULT_GEMMA_SMOKE_MANIFEST)
    parser.add_argument("--gemma-rss-guard-mb", type=int, default=9000)
    parser.add_argument("--gemma-n-warmup", type=int, default=1)
    parser.add_argument(
        "--gemma-cell-type",
        choices=["h2_pure_cvision", "h2_admission", "h3b_admission"],
        default="h2_admission",
        help="Analyzer stage-credit contract for optional Gemma smoke/decision cells.",
    )
    parser.add_argument("--timing-min-n", type=int, default=20)
    parser.add_argument(
        "--positive-control-clip",
        type=Path,
        action="append",
        default=None,
        help=(
            "Real fixed-camera positive-control clip. Repeatable. Defaults to the "
            "encoded Xiph hall-monitor clip when present."
        ),
    )
    parser.add_argument("--run-swa-smoke", action="store_true")
    parser.add_argument("--swa-smoke-model-id", default=DEFAULT_SWA_SMOKE_MODEL_ID)
    parser.add_argument("--max-planned-hours", type=float, default=30.0)
    parser.add_argument("--decision-log", type=Path, default=DEFAULT_DECISION_LOG)
    parser.add_argument("--no-decision-log", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    if args.gemma_n_warmup < 0:
        raise SystemExit("--gemma-n-warmup must be nonnegative")
    if args.timing_min_n < 1:
        raise SystemExit("--timing-min-n must be at least 1")
    if args.max_planned_hours <= 0:
        raise SystemExit("--max-planned-hours must be positive")
    decision_log = None if args.no_decision_log else args.decision_log
    prefill_split_smoke_json = args.prefill_split_smoke_json
    if args.auto_prefill_split_smoke and prefill_split_smoke_json is None:
        prefill_split_smoke_json = args.artifact_dir / "prefill_split_smoke.json"

    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.summary or args.artifact_dir / "queue_summary.json"
    positive_control_clips = (
        list(args.positive_control_clip)
        if args.positive_control_clip is not None
        else list(DEFAULT_POSITIVE_CONTROL_CLIPS)
    )
    commands: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    selected_budget = ["RLT-1-preflight", "RLT-1-profiler-synthetic"]
    if args.manifest is not None:
        selected_budget.append("RLT-1-profiler-n60")
    if args.auto_prefill_split_smoke:
        selected_budget.append("RLT-3G-B-prefill-smoke")
    if args.run_model_smokes:
        selected_budget.append("RLT-2G-gemma-smoke")
    if args.run_gemma_decision_cell:
        selected_budget.append(
            "RLT-3G-B" if args.gemma_cell_type == "h3b_admission" else "RLT-2G-gemma-n60"
        )
    budget = _total_budget(selected_budget)
    if budget["high_hours"] > args.max_planned_hours:
        raise SystemExit(
            f"planned queue high estimate {budget['high_hours']:.1f}h exceeds "
            f"--max-planned-hours {args.max_planned_hours:.1f}h"
        )
    input_hashes = {
        "manifest": _file_sha256(args.manifest),
        "gemma_manifest": _file_sha256(args.gemma_manifest),
        "gemma_smoke_manifest": _file_sha256(args.gemma_smoke_manifest),
        "positive_control_clips": {
            str(clip): _file_sha256(clip) for clip in positive_control_clips if clip.exists()
        },
    }
    if args.dry_run:
        h3b_preflight_planned_early = False
        planned_commands = [
            _planned_command(
                [
                    sys.executable,
                    "scripts/preflight_rlt_vlmax.py",
                    "--phase",
                    "RLT-1",
                    "--output",
                    str(args.artifact_dir / "rlt1_preflight.json"),
                ]
            ),
            _planned_command(
                _profile_command(
                    artifact_dir=args.artifact_dir,
                    manifest=args.manifest,
                    frame_count=args.frame_count,
                    positive_control_clips=positive_control_clips,
                )
            ),
            _planned_command(
                [
                    sys.executable,
                    "scripts/analyze_rlt_mask_profile.py",
                    "--profile-jsonl",
                    str(args.artifact_dir / "rlt_mask_profile.jsonl"),
                    "--output",
                    str(args.artifact_dir / "rlt_mask_profile_analysis.json"),
                ]
            ),
        ]
        if args.auto_prefill_split_smoke:
            planned_commands.append(
                _planned_command(
                    _prefill_split_smoke_command(
                        artifact_dir=args.artifact_dir,
                        output=cast(Path, prefill_split_smoke_json),
                        manifest=args.gemma_smoke_manifest,
                        model_path=args.gemma_model_path,
                        frame_count=args.frame_count,
                        rss_guard_mb=args.gemma_rss_guard_mb,
                    )
                )
            )
        if args.run_model_smokes:
            planned_commands.extend(
                _planned_command(command)
                for command in _gemma_admission_commands(
                    artifact_dir=args.artifact_dir,
                    manifest=args.gemma_smoke_manifest,
                    model_path=args.gemma_model_path,
                    frame_count=args.frame_count,
                    n_items=1,
                    rss_guard_mb=args.gemma_rss_guard_mb,
                    n_warmup=args.gemma_n_warmup,
                    enforce_overhead_gate=False,
                    timing_min_n=args.timing_min_n,
                    cell_type=args.gemma_cell_type,
                    label="rlt2g_gemma_rlt_smoke",
                )
            )
        if args.run_gemma_decision_cell:
            if args.gemma_cell_type == "h3b_admission":
                planned_commands.append(
                    _planned_command(
                        _rlt3_preflight_command(
                            artifact_dir=args.artifact_dir,
                            prefill_split_smoke_json=prefill_split_smoke_json,
                        )
                    )
                )
                h3b_preflight_planned_early = True
            planned_commands.extend(
                _planned_command(command)
                for command in _gemma_admission_commands(
                    artifact_dir=args.artifact_dir,
                    manifest=args.gemma_manifest,
                    model_path=args.gemma_model_path,
                    frame_count=args.frame_count,
                    n_items=0,
                    rss_guard_mb=args.gemma_rss_guard_mb,
                    n_warmup=args.gemma_n_warmup,
                    enforce_overhead_gate=True,
                    timing_min_n=args.timing_min_n,
                    cell_type=args.gemma_cell_type,
                    label="rlt2g_gemma_rlt_decision",
                )
            )
        rlt5_planned_command = [
            sys.executable,
            "scripts/preflight_rlt_vlmax.py",
            "--phase",
            "RLT-5G",
            "--output",
            str(args.artifact_dir / "rlt5g_preflight.json"),
            "--swa-smoke-model-id",
            args.swa_smoke_model_id,
        ]
        if args.run_swa_smoke:
            rlt5_planned_command.append("--run-swa-smoke")
        planned_commands.extend(
            (
                [
                    _planned_command(
                        _rlt3_preflight_command(
                            artifact_dir=args.artifact_dir,
                            prefill_split_smoke_json=prefill_split_smoke_json,
                        )
                    )
                ]
                if not h3b_preflight_planned_early
                else []
            )
            + [
                _planned_command(rlt5_planned_command),
            ]
        )
        payload = {
            "schema_version": SCHEMA_VERSION,
            "dry_run": True,
            "ready_for_model_runs": False,
            "selected_budget_phases": selected_budget,
            "budget": budget,
            "input_hashes": input_hashes,
            "planned_commands": planned_commands,
            "planned_gates": [
                "RLT-1 preflight",
                "CPU mask profile synthetic/optional manifest",
                "RLT profile analyzer early-cancel gates",
                "optional Gemma smoke with overhead gate disabled",
                "optional Gemma decision cell with timing_min_n gate",
                "H3B prefill split preflight",
                "Gemma SWA functional smoke preflight",
            ],
        }
        _write_summary(summary_path, payload)
        print(json.dumps({"summary": str(summary_path), "dry_run": True}, sort_keys=True))
        return 0

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
        _write_terminal_summary(
            summary_path,
            {
                "schema_version": SCHEMA_VERSION,
                "ready_for_model_runs": False,
                "budget": budget,
                "input_hashes": input_hashes,
                "commands": commands,
                "decisions": decisions,
            },
            decision_log=decision_log,
        )
        return 1

    profile_jsonl = args.artifact_dir / "rlt_mask_profile.jsonl"
    profile_command = _profile_command(
        artifact_dir=args.artifact_dir,
        manifest=args.manifest,
        frame_count=args.frame_count,
        positive_control_clips=positive_control_clips,
    )
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
        "synthetic_mask_gate_failed",
        "positive_control_reduction_failed",
        "real_positive_control_reduction_failed",
        "threshold_monotonicity_failed",
        "rlt_pixel_novelty_strong_co_cover",
    }
    if any(decision.get("reason") in stop_reasons for decision in analysis["decisions"]):
        _write_terminal_summary(
            summary_path,
            {
                "schema_version": SCHEMA_VERSION,
                "ready_for_model_runs": False,
                "budget": budget,
                "input_hashes": input_hashes,
                "commands": commands,
                "decisions": decisions,
                "analysis": analysis,
            },
            decision_log=decision_log,
        )
        return 0

    if args.auto_prefill_split_smoke:
        commands.append(
            _run(
                _prefill_split_smoke_command(
                    artifact_dir=args.artifact_dir,
                    output=cast(Path, prefill_split_smoke_json),
                    manifest=args.gemma_smoke_manifest,
                    model_path=args.gemma_model_path,
                    frame_count=args.frame_count,
                    rss_guard_mb=args.gemma_rss_guard_mb,
                )
            )
        )

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
            n_warmup=args.gemma_n_warmup,
            enforce_overhead_gate=False,
            timing_min_n=args.timing_min_n,
            cell_type=args.gemma_cell_type,
            label="rlt2g_gemma_rlt_smoke",
        )
        commands.extend(gemma_commands)
        gemma_analyses["rlt2g_gemma_rlt_smoke"] = gemma_smoke_analysis
        decisions.extend(gemma_smoke_analysis["decisions"])
        if _analysis_blocks_downstream(gemma_smoke_analysis):
            _write_terminal_summary(
                summary_path,
                {
                    "schema_version": SCHEMA_VERSION,
                    "ready_for_model_runs": False,
                    "budget": budget,
                    "input_hashes": input_hashes,
                    "commands": commands,
                    "decisions": decisions,
                    "analysis": analysis,
                    "gemma_analyses": gemma_analyses,
                },
                decision_log=decision_log,
            )
            return 0

    rlt3_preflight: dict[str, Any] | None = None
    if args.run_gemma_decision_cell and args.gemma_cell_type == "h3b_admission":
        rlt3_preflight_path = args.artifact_dir / "rlt3gb_preflight.json"
        commands.append(
            _run(
                _rlt3_preflight_command(
                    artifact_dir=args.artifact_dir,
                    prefill_split_smoke_json=prefill_split_smoke_json,
                ),
                allow_failure=True,
            )
        )
        rlt3_preflight = _read_json(rlt3_preflight_path)
        if not rlt3_preflight.get("ready"):
            decisions.append({"decision": "block_h3b", "reason": "prefill_split_smoke_missing"})
            _write_terminal_summary(
                summary_path,
                {
                    "schema_version": SCHEMA_VERSION,
                    "ready_for_model_runs": False,
                    "budget": budget,
                    "input_hashes": input_hashes,
                    "commands": commands,
                    "decisions": decisions,
                    "analysis": analysis,
                    "gemma_analyses": gemma_analyses,
                    "rlt3gb_preflight": rlt3_preflight,
                },
                decision_log=decision_log,
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
            n_warmup=args.gemma_n_warmup,
            enforce_overhead_gate=True,
            timing_min_n=args.timing_min_n,
            cell_type=args.gemma_cell_type,
            label="rlt2g_gemma_rlt_decision",
        )
        commands.extend(gemma_commands)
        gemma_analyses["rlt2g_gemma_rlt_decision"] = gemma_decision_analysis
        decisions.extend(gemma_decision_analysis["decisions"])
        if _analysis_blocks_downstream(gemma_decision_analysis):
            _write_terminal_summary(
                summary_path,
                {
                    "schema_version": SCHEMA_VERSION,
                    "ready_for_model_runs": False,
                    "budget": budget,
                    "input_hashes": input_hashes,
                    "commands": commands,
                    "decisions": decisions,
                    "analysis": analysis,
                    "gemma_analyses": gemma_analyses,
                },
                decision_log=decision_log,
            )
            return 0

    if rlt3_preflight is None:
        rlt3_preflight_path = args.artifact_dir / "rlt3gb_preflight.json"
        commands.append(
            _run(
                _rlt3_preflight_command(
                    artifact_dir=args.artifact_dir,
                    prefill_split_smoke_json=prefill_split_smoke_json,
                ),
                allow_failure=True,
            )
        )
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
        "--swa-smoke-model-id",
        args.swa_smoke_model_id,
    ]
    if args.run_swa_smoke:
        rlt5_command.append("--run-swa-smoke")
    commands.append(_run(rlt5_command, allow_failure=True))
    rlt5_preflight = _read_json(rlt5_preflight_path)
    if not rlt5_preflight.get("ready"):
        decisions.append({"decision": "block_h4a_gemma", "reason": "swa_functional_smoke_missing"})

    final_payload = {
        "schema_version": SCHEMA_VERSION,
        "ready_for_model_runs": rlt3_preflight.get("ready", False),
        "budget": budget,
        "input_hashes": input_hashes,
        "phase_estimates_hours": PHASE_ESTIMATES_HOURS,
        "commands": commands,
        "decisions": decisions,
        "analysis": analysis,
        "gemma_analyses": gemma_analyses,
        "rlt3gb_preflight": rlt3_preflight,
        "rlt5g_preflight": rlt5_preflight,
    }
    _write_terminal_summary(
        summary_path,
        final_payload,
        decision_log=decision_log if not final_payload["ready_for_model_runs"] else None,
    )
    print(json.dumps({"summary": str(summary_path), "decisions": decisions}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
