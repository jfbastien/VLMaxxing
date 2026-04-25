#!/usr/bin/env python3
"""Run the post-closeout follow-up experiment queue with prereg gates."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from run_paper_closeout_queue import (
    ARTIFACT_ROOT,
    REPO_ROOT,
    QueueStep,
    _check_clean_worktree,
    _format_float,
    _gate_phase_130,
    _gate_phase_155,
    _load_json,
    _load_phase155d_k1_reference_follow_up_median_ms,
    _paths_have_changes,
    _preflight,
    _run,
    _timestamp,
    _write_status,
)

PREFLIGHT_JSON = ARTIFACT_ROOT / "paper_followup_preflight.json"
QUEUE_STATUS_JSON = ARTIFACT_ROOT / "paper_followup_queue_status.json"
LONG_Q0_RATES = (0.75, 0.80, 0.85, 0.90)


def _phase_gate_paths(phase: str) -> Path:
    return {
        "1.55F": ARTIFACT_ROOT / "phase1_55F_q3_post_q2_state/pair_metrics_k1_n7.json",
        "1.55H": ARTIFACT_ROOT / "phase1_55H_k1_32f_short_probe/pair_metrics_k1_n7.json",
        "1.55I": ARTIFACT_ROOT / "phase1_55I_k1_long_replication/pair_metrics_k1_n7.json",
    }[phase]


def _phase_summary_paths(phase: str) -> Path:
    return {
        "1.55F": ARTIFACT_ROOT / "phase1_55F_q3_post_q2_state/summary_k1_n7.json",
        "1.55H": ARTIFACT_ROOT / "phase1_55H_k1_32f_short_probe/summary_k1_n7.json",
        "1.55I": ARTIFACT_ROOT / "phase1_55I_k1_long_replication/summary_k1_n7.json",
    }[phase]


def _rate_tag(rate: float) -> str:
    return f"{rate:.2f}".replace(".", "")


def _130ab_artifact_dir(rate: float) -> Path:
    return ARTIFACT_ROOT / f"phase1_30AB_long_q0_kr{_rate_tag(rate)}"


def _130ae_artifact_dir(rate: float) -> Path:
    return ARTIFACT_ROOT / f"phase1_30AE_duration_conditioned_union_kr{_rate_tag(rate)}"


def _steps() -> list[QueueStep]:
    steps: list[QueueStep] = [
        QueueStep(
            phase="1.55F",
            runtime_estimate="~60-75 min",
            rationale=(
                "Rerun the adaptive Q3 post-Q2-state probe after the text-only-tail fix "
                "to test whether the 1.55E Q3 collapse was a cache-source bug rather than "
                "an adaptive impossibility."
            ),
            command=("bash", str(REPO_ROOT / "scripts/run_phase1_55F_q3_post_q2_state.sh")),
            timeout_seconds=7_200,
            artifact_dir=ARTIFACT_ROOT / "phase1_55F_q3_post_q2_state",
            readiness_key="1.55F",
        ),
        QueueStep(
            phase="1.55I",
            runtime_estimate="~60-90 min",
            rationale=(
                "Extend the landed K=1 selective re-prefill result to the long bucket so "
                "C-PERSIST can either become a three-regime result or be explicitly scoped "
                "to short+medium."
            ),
            command=("bash", str(REPO_ROOT / "scripts/run_phase1_55I_k1_long_replication.sh")),
            timeout_seconds=10_800,
            artifact_dir=ARTIFACT_ROOT / "phase1_55I_k1_long_replication",
            readiness_key="1.55I",
        ),
        QueueStep(
            phase="1.55H",
            runtime_estimate="~1.5-2.0 h",
            rationale=(
                "Probe the depth boundary of the repaired K=1 policy at 32f short bucket "
                "after 1.55G upgraded the result to short+medium."
            ),
            command=("bash", str(REPO_ROOT / "scripts/run_phase1_55H_k1_32f_short_probe.sh")),
            timeout_seconds=12_600,
            artifact_dir=ARTIFACT_ROOT / "phase1_55H_k1_32f_short_probe",
            readiness_key="1.55H",
        ),
    ]
    for rate in LONG_Q0_RATES:
        steps.append(
            QueueStep(
                phase=f"1.30AB@{rate:.2f}",
                runtime_estimate="~25-45 min",
                rationale=(
                    "Measure the long-bucket Q0 keep-rate boundary after 1.30Z falsified "
                    "kr_Q0=0.67, keeping the same follow-up cache-reuse regime."
                ),
                command=(
                    "bash",
                    str(REPO_ROOT / "scripts/run_phase1_30AB_long_q0_candidate.sh"),
                    f"{rate:.2f}",
                ),
                timeout_seconds=5_400,
                artifact_dir=_130ab_artifact_dir(rate),
                readiness_key="1.30AB",
            )
        )
    steps.append(
        QueueStep(
            phase="1.30AE",
            runtime_estimate="~5.5-7.5 h",
            rationale=(
                "Run the first no-splice full-union rerun with the smallest long-bucket "
                "Q0 keep rate that passes the 1.30AB long-only rescue band."
            ),
            command=(),
            timeout_seconds=40_500,
            artifact_dir=ARTIFACT_ROOT / "phase1_30AE_duration_conditioned_union_kr000",
            readiness_key="1.30AE",
        )
    )
    return steps


def _rate_from_phase(phase: str) -> float:
    return float(phase.split("@", 1)[1])


def _phase130_gate_from_artifact(
    path: Path, *, expected_queries: int, expected_sessions: int
) -> dict[str, Any]:
    return _gate_phase_130(
        _load_json(path),
        expected_paired_queries=expected_queries,
        expected_paired_sessions=expected_sessions,
    )


def _select_130ab_rate(status_steps: list[dict[str, Any]]) -> float | None:
    passing_rates: list[float] = []
    for record in status_steps:
        phase = str(record.get("phase", ""))
        gate = record.get("gate")
        if not phase.startswith("1.30AB@") or not isinstance(gate, dict):
            continue
        if bool(gate.get("pass_rescue")) and bool(gate.get("pass_format")):
            passing_rates.append(_rate_from_phase(phase))
    return min(passing_rates) if passing_rates else None


def _130ae_command(rate: float) -> tuple[str, ...]:
    return (
        "bash",
        str(REPO_ROOT / "scripts/run_phase1_30AE_duration_conditioned_union_candidate.sh"),
        f"{rate:.2f}",
    )


def _130ae_gate_path(rate: float) -> Path:
    return _130ae_artifact_dir(rate) / "pair_summary.json"


def _commit_message(step: QueueStep, record: dict[str, Any]) -> str:
    gate = record.get("gate", {})
    phase = step.phase
    pathology_pass = (
        gate.get("pass_follow_up_pathology") and gate.get("pass_q3_pathology")
        if phase in {"1.55F", "1.55I", "1.55H"}
        else None
    )
    if phase == "1.55F":
        subject = "research(1.55F): rerun q3 post-q2 repaired-state probe"
        body = (
            "Record the fixed rerun of the adaptive post-Q2-state path so the paper can "
            "distinguish a cache-source mechanism win from the earlier runner crash.\n"
            f"Gate summary: correctness_diffs={gate.get('paired_correctness_diffs')}, "
            f"choice_diffs={gate.get('paired_choice_diffs')}, "
            f"follow_up_pathology={gate.get('pathological_follow_up_hits')}, "
            f"q3_pathology={gate.get('pathological_q3_hits')}, "
            f"follow_up_median_ms={_format_float(gate.get('session_follow_up_median_ms'), 1)}, "
            "speedup="
            f"{_format_float(gate.get('speedup_all_query_median_cold_over_session_follow_up'))}x, "
            f"peak_rss={_format_float(gate.get('peak_rss_gb'))} GB.\n"
            f"Fidelity={'PASS' if gate.get('pass_fidelity') else 'FAIL'}, "
            f"exact_match={'PASS' if gate.get('pass_exact_match') else 'FAIL'}, "
            f"pathology={'PASS' if pathology_pass else 'FAIL'}."
        )
    elif phase == "1.55I":
        subject = "research(1.55I): land long-bucket k1 replication"
        body = (
            "Record the long-bucket scope test for K equals 1 selective re-prefill so the "
            "paper can decide whether C-PERSIST is short+medium only or truly multi-regime.\n"
            f"Gate summary: correctness_diffs={gate.get('paired_correctness_diffs')}, "
            f"choice_diffs={gate.get('paired_choice_diffs')}, "
            f"follow_up_pathology={gate.get('pathological_follow_up_hits')}, "
            f"q3_pathology={gate.get('pathological_q3_hits')}, "
            f"baseline_accuracy={_format_float(gate.get('baseline_accuracy'))}, "
            "speedup="
            f"{_format_float(gate.get('speedup_all_query_median_cold_over_session_follow_up'))}x, "
            f"peak_rss={_format_float(gate.get('peak_rss_gb'))} GB.\n"
            f"Fidelity={'PASS' if gate.get('pass_fidelity') else 'FAIL'}, "
            f"exact_match={'PASS' if gate.get('pass_exact_match') else 'FAIL'}, "
            f"pathology={'PASS' if pathology_pass else 'FAIL'}."
        )
    elif phase == "1.55H":
        subject = "research(1.55H): land short-bucket 32f boundary probe"
        body = (
            "Record the 32-frame short-bucket boundary test for K equals 1 so the repaired "
            "C-PERSIST envelope has an explicit depth limit or extension.\n"
            f"Gate summary: correctness_diffs={gate.get('paired_correctness_diffs')}, "
            f"choice_diffs={gate.get('paired_choice_diffs')}, "
            f"follow_up_pathology={gate.get('pathological_follow_up_hits')}, "
            f"q3_pathology={gate.get('pathological_q3_hits')}, "
            "speedup="
            f"{_format_float(gate.get('speedup_all_query_median_cold_over_session_follow_up'))}x, "
            f"peak_rss={_format_float(gate.get('peak_rss_gb'))} GB.\n"
            f"Fidelity={'PASS' if gate.get('pass_fidelity') else 'FAIL'}, "
            f"pathology={'PASS' if pathology_pass else 'FAIL'}."
        )
    elif phase.startswith("1.30AB@"):
        subject = f"research(1.30AB): land long-q0 candidate {phase.split('@', 1)[1]}"
        body = (
            "Record one long-bucket Q0 keep-rate candidate so the 1.30 lane can replace the "
            "selection-biased kr 0.67 scout with a real boundary sweep.\n"
            f"Gate summary: Δacc={_format_float(gate.get('accuracy_delta'))}, "
            f"CI95={gate.get('accuracy_delta_ci95')}, "
            f"speedup={_format_float(gate.get('speedup'))}x, "
            f"parse_failures={gate.get('parse_failures')}, "
            f"degenerates={gate.get('degenerates')}, "
            f"follow_up_activity={gate.get('follow_up_vision_pruning_active_fraction')}.\n"
            f"Rescue={'PASS' if gate.get('pass_rescue') else 'FAIL'}, "
            f"format={'PASS' if gate.get('pass_format') else 'FAIL'}, "
            f"pairing={'PASS' if gate.get('pass_complete_pairing') else 'FAIL'}."
        )
    else:
        subject = "research(1.30AE): land sweep-selected union rerun"
        body = (
            "Record the first no-splice full-union rerun selected from the 1.30AB long-rate "
            "boundary sweep so the paper can cite a fully measured bridge candidate or a "
            "measured failure.\n"
            f"Gate summary: Δacc={_format_float(gate.get('accuracy_delta'))}, "
            f"CI95={gate.get('accuracy_delta_ci95')}, "
            f"speedup={_format_float(gate.get('speedup'))}x, "
            f"parse_failures={gate.get('parse_failures')}, "
            f"degenerates={gate.get('degenerates')}, "
            f"follow_up_activity={gate.get('follow_up_vision_pruning_active_fraction')}.\n"
            f"Rescue={'PASS' if gate.get('pass_rescue') else 'FAIL'}, "
            f"format={'PASS' if gate.get('pass_format') else 'FAIL'}, "
            f"pairing={'PASS' if gate.get('pass_complete_pairing') else 'FAIL'}."
        )
    return f"{subject}\n\n{body}"


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
    parser.add_argument(
        "--preflight-json",
        type=Path,
        default=PREFLIGHT_JSON,
        help="Where to write/read the preflight summary.",
    )
    parser.add_argument(
        "--queue-status-json",
        type=Path,
        default=QUEUE_STATUS_JSON,
        help="Where to write the queue execution summary.",
    )
    parser.add_argument(
        "--start-at",
        choices=[step.phase for step in _steps()],
        default=None,
        help="Skip earlier steps in the queue.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Stop on the first failed command instead of continuing to independent steps.",
    )
    parser.add_argument(
        "--auto-commit",
        action="store_true",
        help="Commit each successful step's artifacts and queue-status snapshot as it lands.",
    )
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

    selected_130ab_rate: float | None = None

    for step in queue_steps:
        ready = bool(experiments_ready.get(step.readiness_key or "", {}).get("ready", True))
        record: dict[str, Any] = {
            "phase": step.phase,
            "runtime_estimate": step.runtime_estimate,
            "rationale": step.rationale,
            "ready": ready,
            "timeout_seconds": step.timeout_seconds,
            "artifact_dir": step.artifact_dir.as_posix(),
        }
        if not ready:
            record["status"] = "blocked-by-preflight"
            status["steps"].append(record)
            _write_status(args.queue_status_json, status, dry_run=args.dry_run)
            continue

        command = step.command
        artifact_dir = step.artifact_dir
        if step.phase == "1.30AE":
            selected_130ab_rate = _select_130ab_rate(status["steps"])
            record["selected_130ab_rate"] = selected_130ab_rate
            if selected_130ab_rate is None:
                record["status"] = "skipped-by-1.30AB-gate"
                status["steps"].append(record)
                _write_status(args.queue_status_json, status, dry_run=args.dry_run)
                continue
            command = _130ae_command(selected_130ab_rate)
            artifact_dir = _130ae_artifact_dir(selected_130ab_rate)
            record["command"] = list(command)
            record["artifact_dir"] = artifact_dir.as_posix()
        else:
            record["command"] = list(command)

        try:
            _run(command, dry_run=args.dry_run, timeout_seconds=step.timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            record["status"] = "failed-timeout"
            record["error"] = {
                "type": type(exc).__name__,
                "timeout_seconds": exc.timeout,
            }
            status["steps"].append(record)
            _write_status(args.queue_status_json, status, dry_run=args.dry_run)
            if args.strict:
                raise
            continue
        except subprocess.CalledProcessError as exc:
            record["status"] = "failed-command"
            record["error"] = {
                "type": type(exc).__name__,
                "returncode": exc.returncode,
            }
            status["steps"].append(record)
            _write_status(args.queue_status_json, status, dry_run=args.dry_run)
            if args.strict:
                raise
            continue

        record["status"] = "completed" if not args.dry_run else "dry-run"

        if step.phase.startswith("1.30AB@"):
            if args.dry_run:
                record["gate"] = "pending"
            else:
                record["gate"] = _phase130_gate_from_artifact(
                    artifact_dir / "pair_summary.json",
                    expected_queries=54,
                    expected_sessions=18,
                )
        elif step.phase == "1.30AE":
            if args.dry_run:
                record["gate"] = "pending"
            else:
                record["gate"] = _phase130_gate_from_artifact(
                    _130ae_gate_path(selected_130ab_rate),
                    expected_queries=171,
                    expected_sessions=57,
                )
        else:
            if args.dry_run:
                record["gate"] = "pending"
            else:
                summary_path = _phase_summary_paths(step.phase)
                pair_metrics_path = _phase_gate_paths(step.phase)
                if step.phase == "1.55F":
                    record["gate"] = _gate_phase_155(
                        pair_metrics=_load_json(pair_metrics_path),
                        summary=_load_json(summary_path),
                        correctness_limit=1,
                        choice_limit=2,
                        q3_pathological_limit=2,
                        follow_up_pathological_limit=2,
                        max_rss_gb=5.0,
                        max_session_follow_up_median_ms=_load_phase155d_k1_reference_follow_up_median_ms(),
                        strict_correctness_limit=0,
                        strict_choice_limit=0,
                    )
                elif step.phase == "1.55I":
                    record["gate"] = _gate_phase_155(
                        pair_metrics=_load_json(pair_metrics_path),
                        summary=_load_json(summary_path),
                        correctness_limit=2,
                        choice_limit=3,
                        q3_pathological_limit=1,
                        follow_up_pathological_limit=2,
                        max_rss_gb=7.5,
                        min_speedup=6.0,
                        strict_correctness_limit=0,
                        strict_choice_limit=0,
                        baseline_accuracy_floor=0.30,
                    )
                else:
                    record["gate"] = _gate_phase_155(
                        pair_metrics=_load_json(pair_metrics_path),
                        summary=_load_json(summary_path),
                        correctness_limit=3,
                        choice_limit=4,
                        q3_pathological_limit=3,
                        follow_up_pathological_limit=3,
                        max_rss_gb=6.5,
                        min_speedup=8.0,
                    )

        step_for_commit = QueueStep(
            phase=step.phase,
            runtime_estimate=step.runtime_estimate,
            rationale=step.rationale,
            command=command,
            timeout_seconds=step.timeout_seconds,
            artifact_dir=artifact_dir,
            readiness_key=step.readiness_key,
        )
        if args.auto_commit and not args.dry_run:
            record["auto_commit"] = (
                "committed"
                if _paths_have_changes((artifact_dir, args.preflight_json, args.queue_status_json))
                else "no-changes"
            )
        status["steps"].append(record)
        _write_status(args.queue_status_json, status, dry_run=args.dry_run)
        if args.auto_commit and not args.dry_run and record.get("auto_commit") == "committed":
            _commit_step(
                step_for_commit,
                preflight_json=args.preflight_json,
                queue_status_json=args.queue_status_json,
                record=record,
            )

    if args.dry_run:
        print(json.dumps(status, indent=2))
        return 0

    print(f"[paper-followup] wrote {args.queue_status_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
