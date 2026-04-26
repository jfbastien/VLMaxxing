#!/usr/bin/env python3
"""Run reviewer-defense experiments after the adaptive-mechanism closeout."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Any

from run_paper_closeout_queue import (
    ARTIFACT_ROOT,
    REPO_ROOT,
    QueueStep,
    _check_clean_worktree,
    _format_float,
    _gate_phase_155,
    _load_json,
    _paths_have_changes,
    _preflight,
    _run,
    _timestamp,
    _write_status,
)

PREFLIGHT_JSON = ARTIFACT_ROOT / "paper_reviewer_defense_preflight.json"
QUEUE_STATUS_JSON = ARTIFACT_ROOT / "paper_reviewer_defense_queue_status.json"


def _steps() -> list[QueueStep]:
    return [
        QueueStep(
            phase="1.62D",
            runtime_estimate="~3.5-5.5 h",
            rationale=(
                "Run the cheapest deployment baseline: dense 4f and 2f over the same "
                "VideoMME session protocol as 1.30W, paired against the 8f cold reference."
            ),
            command=("bash", str(REPO_ROOT / "scripts/run_phase1_62D_lowfps_dense_videomme.sh")),
            timeout_seconds=24_000,
            artifact_dir=ARTIFACT_ROOT / "phase1_62D_lowfps_dense_videomme",
            readiness_key="1.62D",
        ),
        QueueStep(
            phase="1.55F-16f",
            runtime_estimate="~35-60 min",
            rationale=(
                "Fill the adaptive C-PERSIST 16f interpolation point between the landed "
                "20f and 32f short-bucket cells."
            ),
            command=(
                "bash",
                str(REPO_ROOT / "scripts/run_phase1_55F_16f_short_adaptive_replication.sh"),
            ),
            timeout_seconds=5_400,
            artifact_dir=ARTIFACT_ROOT / "phase1_55F_16f_short_adaptive_replication",
            readiness_key="1.55F-16f",
        ),
        QueueStep(
            phase="1.57G",
            runtime_estimate="~1-2 h",
            rationale=(
                "Run the matched Gemma short/medium/long feature-drift grid so the "
                "cross-architecture C-VISION mechanism story has comparable drift geometry."
            ),
            command=(
                "bash",
                str(REPO_ROOT / "scripts/run_phase1_57G_gemma_matched_duration_drift.sh"),
            ),
            timeout_seconds=9_000,
            artifact_dir=ARTIFACT_ROOT / "phase1_57G_gemma_matched_duration_drift",
            readiness_key="1.57G",
        ),
    ]


def _gate_phase_162d(artifact_dir: Path) -> dict[str, Any]:
    by_frame: dict[str, dict[str, Any]] = {}
    for frame_count in (4, 2):
        summary = _load_json(artifact_dir / f"lowfps_{frame_count}f_vs_8f_summary.json")
        by_frame[str(frame_count)] = {
            "outcome": summary["outcome"],
            "n_paired_queries": summary["n_paired_queries"],
            "n_paired_sessions": summary["n_paired_sessions"],
            "pass_complete_pairing": summary["pass_complete_pairing"],
            "pass_format": summary["pass_format"],
            "accuracy_delta": summary["all"]["accuracy_delta_candidate_minus_reference"],
            "accuracy_delta_ci95": summary["all"]["accuracy_delta_candidate_minus_reference_ci95"],
            "reference_accuracy": summary["all"]["reference_accuracy"],
            "candidate_accuracy": summary["all"]["candidate_accuracy"],
            "speedup_reference_over_candidate": summary["all"]["speedup_reference_over_candidate"],
            "first_query_delta": summary["first_queries"][
                "accuracy_delta_candidate_minus_reference"
            ],
            "follow_up_delta": summary["follow_ups"]["accuracy_delta_candidate_minus_reference"],
        }
    return {
        "frame_4": by_frame["4"],
        "frame_2": by_frame["2"],
        "primary_outcome": by_frame["4"]["outcome"],
        "pass_format": bool(by_frame["4"]["pass_format"] and by_frame["2"]["pass_format"]),
        "pass_complete_pairing": bool(
            by_frame["4"]["pass_complete_pairing"] and by_frame["2"]["pass_complete_pairing"]
        ),
    }


def _gate_phase_155f16(artifact_dir: Path) -> dict[str, Any]:
    return _gate_phase_155(
        pair_metrics=_load_json(artifact_dir / "pair_metrics_k1_n7.json"),
        summary=_load_json(artifact_dir / "summary_k1_n7.json"),
        correctness_limit=2,
        choice_limit=3,
        q3_pathological_limit=1,
        follow_up_pathological_limit=2,
        max_rss_gb=5.5,
        min_speedup=12.0,
        strict_correctness_limit=0,
        strict_choice_limit=0,
        baseline_accuracy_floor=0.40,
    )


def _gate_phase_157g(artifact_dir: Path) -> dict[str, Any]:
    summary = _load_json(artifact_dir / "summary.json")
    static_means = {
        f"{cell['group']}_{cell['frame_count']}f": cell.get("static_mean_cos")
        for cell in summary.get("cells", [])
    }
    return {
        "complete": bool(summary.get("complete")),
        "n_cells": len(summary.get("cells", [])),
        "missing": summary.get("missing", []),
        "static_means": static_means,
    }


def _commit_message(step: QueueStep, record: dict[str, Any]) -> str:
    gate = record.get("gate", {})
    if step.phase == "1.62D":
        frame4 = gate.get("frame_4", {})
        frame2 = gate.get("frame_2", {})
        return (
            "research(1.62D): land low-fps dense baseline\n\n"
            "Record the cheapest deployment-style baseline against the same "
            "VideoMME session protocol as 1.30W: dense 4f and 2f paired against "
            "the existing 8f cold reference.\n"
            f"4f outcome={frame4.get('outcome')}, "
            f"Δacc={_format_float(frame4.get('accuracy_delta'))}, "
            f"speedup={_format_float(frame4.get('speedup_reference_over_candidate'))}x; "
            f"2f outcome={frame2.get('outcome')}, "
            f"Δacc={_format_float(frame2.get('accuracy_delta'))}, "
            f"speedup={_format_float(frame2.get('speedup_reference_over_candidate'))}x. "
            "This determines whether the paper needs a low-FPS dense caveat or "
            "gets a clean defense against that baseline objection."
        )
    if step.phase == "1.55F-16f":
        return (
            "research(1.55F-16f): land adaptive interpolation point\n\n"
            "Record the 16f short-bucket interpolation point for the adaptive "
            "post-Q2-state C-PERSIST policy, between the landed 20f and 32f cells.\n"
            f"Gate summary: correctness_diffs={gate.get('paired_correctness_diffs')}, "
            f"choice_diffs={gate.get('paired_choice_diffs')}, "
            "speedup="
            f"{_format_float(gate.get('speedup_all_query_median_cold_over_session_follow_up'))}x, "
            f"peak_rss={_format_float(gate.get('peak_rss_gb'))} GB. "
            f"Fidelity={'PASS' if gate.get('pass_fidelity') else 'FAIL'}, "
            f"exact_match={'PASS' if gate.get('pass_exact_match') else 'FAIL'}, "
            f"speed={'PASS' if gate.get('pass_speed') else 'FAIL'}."
        )
    return (
        "research(1.57G): land Gemma matched-duration drift grid\n\n"
        "Record Gemma feature-drift geometry across short, medium, and long "
        "VideoMME buckets at 8/16/32f so the cross-architecture C-VISION story "
        "has a matched mechanism proxy rather than answer-level transfer alone.\n"
        f"Grid complete={gate.get('complete')}, n_cells={gate.get('n_cells')}, "
        f"missing={gate.get('missing')}."
    )


def _commit_step(
    step: QueueStep,
    *,
    preflight_json: Path,
    queue_status_json: Path,
    record: dict[str, Any],
) -> None:
    subprocess.run(
        [
            "git",
            "add",
            step.artifact_dir.as_posix(),
            preflight_json.as_posix(),
            queue_status_json.as_posix(),
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", _commit_message(step, record)],
        cwd=REPO_ROOT,
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--auto-commit", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--preflight-json", type=Path, default=PREFLIGHT_JSON)
    parser.add_argument("--queue-status-json", type=Path, default=QUEUE_STATUS_JSON)
    parser.add_argument("--start-at", choices=[step.phase for step in _steps()], default=None)
    args = parser.parse_args()

    if args.auto_commit and args.dry_run:
        raise SystemExit("--auto-commit cannot be combined with --dry-run")
    if args.auto_commit:
        _check_clean_worktree()

    preflight = _preflight(dry_run=args.dry_run, output_path=args.preflight_json)
    experiments_ready = preflight.get("experiments", {})
    queue_steps = _steps()
    if args.start_at is not None:
        start_index = next(
            index for index, step in enumerate(queue_steps) if step.phase == args.start_at
        )
        queue_steps = queue_steps[start_index:]

    status: dict[str, Any] = {
        "preflight_json": args.preflight_json.as_posix(),
        "dry_run": args.dry_run,
        "strict": args.strict,
        "auto_commit": args.auto_commit,
        "started_at": _timestamp(),
        "steps": [],
    }
    _write_status(args.queue_status_json, status, dry_run=args.dry_run)

    for step in queue_steps:
        ready = bool(experiments_ready.get(step.readiness_key or "", {}).get("ready", True))
        record: dict[str, Any] = {
            "phase": step.phase,
            "runtime_estimate": step.runtime_estimate,
            "rationale": step.rationale,
            "ready": ready,
            "timeout_seconds": step.timeout_seconds,
            "artifact_dir": step.artifact_dir.as_posix(),
            "command": list(step.command),
        }
        if not ready:
            record["status"] = "blocked-by-preflight"
            status["steps"].append(record)
            _write_status(args.queue_status_json, status, dry_run=args.dry_run)
            continue

        try:
            _run(step.command, dry_run=args.dry_run, timeout_seconds=step.timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            record["status"] = "failed-timeout"
            record["error"] = {"type": type(exc).__name__, "timeout_seconds": exc.timeout}
            status["steps"].append(record)
            _write_status(args.queue_status_json, status, dry_run=args.dry_run)
            if args.strict:
                raise
            continue
        except subprocess.CalledProcessError as exc:
            record["status"] = "failed-command"
            record["error"] = {"type": type(exc).__name__, "returncode": exc.returncode}
            status["steps"].append(record)
            _write_status(args.queue_status_json, status, dry_run=args.dry_run)
            if args.strict:
                raise
            continue

        record["status"] = "completed" if not args.dry_run else "dry-run"
        if args.dry_run:
            record["gate"] = "pending"
        elif step.phase == "1.62D":
            record["gate"] = _gate_phase_162d(step.artifact_dir)
        elif step.phase == "1.55F-16f":
            record["gate"] = _gate_phase_155f16(step.artifact_dir)
        else:
            record["gate"] = _gate_phase_157g(step.artifact_dir)

        if args.auto_commit and not args.dry_run:
            record["auto_commit"] = (
                "committed"
                if _paths_have_changes(
                    (step.artifact_dir, args.preflight_json, args.queue_status_json)
                )
                else "no-changes"
            )
        status["steps"].append(record)
        _write_status(args.queue_status_json, status, dry_run=args.dry_run)
        if args.auto_commit and not args.dry_run and record.get("auto_commit") == "committed":
            _commit_step(
                step,
                preflight_json=args.preflight_json,
                queue_status_json=args.queue_status_json,
                record=record,
            )

    if args.dry_run:
        import json

        print(json.dumps(status, indent=2))
        return 0

    print(f"[paper-reviewer-defense] wrote {args.queue_status_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
