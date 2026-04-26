#!/usr/bin/env python3
"""Run the next paper queue: adaptive C-PERSIST breadth + 1.30 mechanism pins."""

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
    _gate_phase_130,
    _gate_phase_155,
    _load_json,
    _paths_have_changes,
    _preflight,
    _run,
    _timestamp,
    _write_status,
)

PREFLIGHT_JSON = ARTIFACT_ROOT / "paper_adaptive_mechanism_preflight.json"
QUEUE_STATUS_JSON = ARTIFACT_ROOT / "paper_adaptive_mechanism_queue_status.json"
PHASE130W_REFERENCE_PAIR_SUMMARY = (
    ARTIFACT_ROOT / "phase1_30W_q0_dense_followup_pruned_full/pair_summary.json"
)
PHASE155F_GATE_PROFILES: dict[str, dict[str, float]] = {
    "1.55F-medium": {
        "correctness_limit": 2,
        "choice_limit": 3,
        "q3_pathological_limit": 1,
        "follow_up_pathological_limit": 2,
        "max_rss_gb": 5.5,
        "min_speedup": 15.0,
        "strict_correctness_limit": 0,
        "strict_choice_limit": 0,
        "baseline_accuracy_floor": 0.40,
    },
    "1.55F-long": {
        "correctness_limit": 2,
        "choice_limit": 3,
        "q3_pathological_limit": 1,
        "follow_up_pathological_limit": 2,
        "max_rss_gb": 5.5,
        "min_speedup": 16.0,
        "strict_correctness_limit": 0,
        "strict_choice_limit": 0,
        "baseline_accuracy_floor": 0.30,
    },
    "1.55F-32f": {
        "correctness_limit": 2,
        "choice_limit": 3,
        "q3_pathological_limit": 1,
        "follow_up_pathological_limit": 2,
        "max_rss_gb": 6.0,
        "min_speedup": 30.0,
        "strict_correctness_limit": 0,
        "strict_choice_limit": 0,
        "baseline_accuracy_floor": 0.40,
    },
}


def _phase155_pair_metrics_path(phase: str) -> Path:
    return {
        "1.55F-medium": (
            ARTIFACT_ROOT / "phase1_55F_medium_adaptive_replication/pair_metrics_k1_n10.json"
        ),
        "1.55F-long": (
            ARTIFACT_ROOT / "phase1_55F_long_adaptive_replication/pair_metrics_k1_n7.json"
        ),
        "1.55F-32f": (
            ARTIFACT_ROOT / "phase1_55F_32f_short_adaptive_replication/pair_metrics_k1_n7.json"
        ),
        "1.55J": ARTIFACT_ROOT / "phase1_55J_k1_sampler_variation/pair_metrics_k1_n7.json",
    }[phase]


def _phase155_summary_path(phase: str) -> Path:
    return {
        "1.55F-medium": (
            ARTIFACT_ROOT / "phase1_55F_medium_adaptive_replication/summary_k1_n10.json"
        ),
        "1.55F-long": (ARTIFACT_ROOT / "phase1_55F_long_adaptive_replication/summary_k1_n7.json"),
        "1.55F-32f": (
            ARTIFACT_ROOT / "phase1_55F_32f_short_adaptive_replication/summary_k1_n7.json"
        ),
        "1.55J": ARTIFACT_ROOT / "phase1_55J_k1_sampler_variation/summary_k1_n7.json",
    }[phase]


def _phase130_pair_summary_path(phase: str) -> Path:
    return {
        "1.30AC": ARTIFACT_ROOT / "phase1_30AC_cache_invalidated_followups/pair_summary.json",
        "1.30AD": ARTIFACT_ROOT / "phase1_30AD_instrumented_w_rerun/pair_summary.json",
    }[phase]


def _gate_phase_130ac(summary: dict[str, Any]) -> dict[str, Any]:
    base = _gate_phase_130(summary, expected_paired_queries=171, expected_paired_sessions=57)
    active_fraction = summary.get("streaming_follow_up_vision_pruning_active_fraction")
    reused_fraction = summary.get("streaming_follow_up_all_image_tokens_reused_fraction")
    mean_recomputed = summary.get("streaming_follow_up_mean_image_tokens_recomputed")
    pass_activation = (
        active_fraction is not None
        and float(active_fraction) >= 0.90
        and mean_recomputed is not None
        and float(mean_recomputed) > 0.0
        and reused_fraction is not None
        and float(reused_fraction) <= 0.10
    )
    helpful = pass_activation and base["accuracy_delta"] >= -0.10 and base["speedup"] >= 2.0
    hurtful = pass_activation and not helpful
    return {
        **base,
        "pass_activation": pass_activation,
        "mechanism_outcome": (
            "helpful" if helpful else "hurtful" if hurtful else "activation_failed"
        ),
        "pass_helpful_rescue": helpful,
        "evidence_hurtful": hurtful,
        "follow_up_mean_image_tokens_recomputed": mean_recomputed,
    }


def _gate_phase_130ad(summary: dict[str, Any]) -> dict[str, Any]:
    base = _gate_phase_130(summary, expected_paired_queries=171, expected_paired_sessions=57)
    reference = _load_json(PHASE130W_REFERENCE_PAIR_SUMMARY)
    ref_delta = float(reference["accuracy_delta_streaming_minus_cold"])
    ref_ci = reference.get("accuracy_delta_streaming_minus_cold_ci95")
    observed_ci = summary.get("accuracy_delta_streaming_minus_cold_ci95")
    pass_repro_delta = abs(base["accuracy_delta"] - ref_delta) <= 0.030
    pass_repro_ci = None
    if (
        isinstance(ref_ci, list)
        and len(ref_ci) == 2
        and isinstance(observed_ci, list)
        and len(observed_ci) == 2
    ):
        pass_repro_ci = (
            abs(float(observed_ci[0]) - float(ref_ci[0])) <= 0.05
            and abs(float(observed_ci[1]) - float(ref_ci[1])) <= 0.05
        )
    active_fraction = summary.get("streaming_follow_up_vision_pruning_active_fraction")
    reused_fraction = summary.get("streaming_follow_up_all_image_tokens_reused_fraction")
    pass_mechanism = (
        active_fraction is not None
        and float(active_fraction) < 0.10
        and reused_fraction is not None
        and float(reused_fraction) > 0.90
    )
    return {
        **base,
        "reference_accuracy_delta": ref_delta,
        "reference_accuracy_delta_ci95": ref_ci,
        "pass_repro_delta": pass_repro_delta,
        "pass_repro_ci": pass_repro_ci,
        "pass_mechanism": pass_mechanism,
    }


def _gate_phase_155j(pair_metrics: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    base = _gate_phase_155(
        pair_metrics=pair_metrics,
        summary=summary,
        correctness_limit=1,
        choice_limit=2,
        q3_pathological_limit=1,
        follow_up_pathological_limit=1,
        max_rss_gb=5.5,
        strict_correctness_limit=0,
        strict_choice_limit=0,
    )
    same_class_speedup = pair_metrics.get("speedup_follow_up_median_cold_over_session")
    pass_same_class_speed = same_class_speedup is not None and float(same_class_speedup) >= 8.0
    session_summary = summary.get("session", {})
    session_n_correct = session_summary.get("n_correct")
    session_accuracy = session_summary.get("accuracy")
    pass_session_floor = session_n_correct is not None and int(session_n_correct) >= 14
    return {
        **base,
        "speedup_follow_up_median_cold_over_session": same_class_speedup,
        "pass_same_class_speed": pass_same_class_speed,
        "session_n_correct": session_n_correct,
        "session_accuracy": session_accuracy,
        "pass_session_floor": pass_session_floor,
        "sampler": {
            "temperature": summary.get("temperature"),
            "top_p": summary.get("top_p"),
            "min_p": summary.get("min_p"),
        },
    }


def _steps() -> list[QueueStep]:
    return [
        QueueStep(
            phase="1.55F-medium",
            runtime_estimate="~60-75 min",
            rationale=(
                "Extend the landed adaptive post-Q2-state policy from short to the fixed "
                "medium tranche so adaptive C-PERSIST can either become a two-regime result "
                "or be explicitly scoped to short only."
            ),
            command=(
                "bash",
                str(REPO_ROOT / "scripts/run_phase1_55F_medium_adaptive_replication.sh"),
            ),
            timeout_seconds=7_200,
            artifact_dir=ARTIFACT_ROOT / "phase1_55F_medium_adaptive_replication",
            readiness_key="1.55F-medium",
        ),
        QueueStep(
            phase="1.55F-long",
            runtime_estimate="~60-90 min",
            rationale=(
                "Test whether the adaptive post-Q2-state policy generalizes to the same long "
                "tranche where fixed K=1 already landed cleanly."
            ),
            command=(
                "bash",
                str(REPO_ROOT / "scripts/run_phase1_55F_long_adaptive_replication.sh"),
            ),
            timeout_seconds=7_800,
            artifact_dir=ARTIFACT_ROOT / "phase1_55F_long_adaptive_replication",
            readiness_key="1.55F-long",
        ),
        QueueStep(
            phase="1.55F-32f",
            runtime_estimate="~70-90 min",
            rationale=(
                "Intersect the adaptive repaired-state policy with the 32f short depth "
                "boundary now that fixed K=1 has already survived that regime."
            ),
            command=(
                "bash",
                str(REPO_ROOT / "scripts/run_phase1_55F_32f_short_adaptive_replication.sh"),
            ),
            timeout_seconds=9_000,
            artifact_dir=ARTIFACT_ROOT / "phase1_55F_32f_short_adaptive_replication",
            readiness_key="1.55F-32f",
        ),
        QueueStep(
            phase="1.55J",
            runtime_estimate="~60-90 min",
            rationale=(
                "Run the fixed K=1 short-bucket repaired frontier under deterministic "
                "temperature sampling so the no-drift claim is not greedy-only by default."
            ),
            command=("bash", str(REPO_ROOT / "scripts/run_phase1_55J_k1_sampler_variation.sh")),
            timeout_seconds=7_800,
            artifact_dir=ARTIFACT_ROOT / "phase1_55J_k1_sampler_variation",
            readiness_key="1.55J",
        ),
        QueueStep(
            phase="1.30AC",
            runtime_estimate="~5-6 h with 1.30W cold reuse",
            rationale=(
                "Force cache invalidation between follow-up queries so the follow-up vision "
                "tower actually fires, turning the 1.30 lane into a true follow-up-pruning "
                "mechanism experiment."
            ),
            command=(
                "bash",
                str(REPO_ROOT / "scripts/run_phase1_30AC_cache_invalidated_followups.sh"),
            ),
            timeout_seconds=25_200,
            artifact_dir=ARTIFACT_ROOT / "phase1_30AC_cache_invalidated_followups",
            readiness_key="1.30AC",
        ),
        QueueStep(
            phase="1.30AD",
            runtime_estimate="~1.5-2.5 h with 1.30W cold reuse",
            rationale=(
                "Re-run the landed 1.30W full union under image-token instrumentation so "
                "the published 1.30W mechanism can be stated from a measurement rather than "
                "from 1.30Z-only inference."
            ),
            command=("bash", str(REPO_ROOT / "scripts/run_phase1_30AD_instrumented_w_rerun.sh")),
            timeout_seconds=12_600,
            artifact_dir=ARTIFACT_ROOT / "phase1_30AD_instrumented_w_rerun",
            readiness_key="1.30AD",
        ),
    ]


def _commit_message(step: QueueStep, record: dict[str, Any]) -> str:
    gate = record.get("gate", {})
    phase = step.phase
    if phase == "1.55F-medium":
        subject = "research(1.55F-medium): land adaptive medium replication"
        body = (
            "Record the medium-bucket replication of the adaptive post-Q2-state policy so "
            "the paper can decide whether the strongest C-PERSIST cell is short-only or "
            "already multi-regime.\n"
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
            f"speed={'PASS' if gate.get('pass_speed') else 'FAIL'}."
        )
    elif phase == "1.55F-long":
        subject = "research(1.55F-long): land adaptive long replication"
        body = (
            "Record the long-bucket replication of the adaptive post-Q2-state policy so the "
            "paper can decide whether adaptive C-PERSIST is genuinely three-regime.\n"
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
            f"speed={'PASS' if gate.get('pass_speed') else 'FAIL'}."
        )
    elif phase == "1.55F-32f":
        subject = "research(1.55F-32f): land adaptive 32f short probe"
        body = (
            "Record the depth-boundary replication of the adaptive post-Q2-state policy so "
            "the paper can decide whether the adaptive repaired-state path survives the 32f "
            "short regime, not just the 20f cells.\n"
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
            f"speed={'PASS' if gate.get('pass_speed') else 'FAIL'}."
        )
    elif phase == "1.30AC":
        subject = "research(1.30AC): land cache-invalidated follow-up test"
        body = (
            "Record the first 1.30 run that explicitly invalidates cache reuse between "
            "queries so follow-up vision pruning is measured mechanically rather than "
            "assumed from configuration.\n"
            f"Gate summary: Δacc={_format_float(gate.get('accuracy_delta'))}, "
            f"CI95={gate.get('accuracy_delta_ci95')}, "
            f"speedup={_format_float(gate.get('speedup'))}x, "
            f"parse_failures={gate.get('parse_failures')}, "
            f"degenerates={gate.get('degenerates')}, "
            f"follow_up_activity={gate.get('follow_up_vision_pruning_active_fraction')}, "
            f"mean_recomputed={gate.get('follow_up_mean_image_tokens_recomputed')}.\n"
            f"Activation={'PASS' if gate.get('pass_activation') else 'FAIL'}, "
            f"helpful_rescue={'PASS' if gate.get('pass_helpful_rescue') else 'FAIL'}, "
            f"mechanism_outcome={gate.get('mechanism_outcome')}."
        )
    elif phase == "1.30AD":
        subject = "research(1.30AD): land instrumented 1.30W rerun"
        body = (
            "Record the instrumented rerun of the landed 1.30W line so the paper can lock "
            "its mechanism wording against a direct measurement on the published full-union "
            "cell.\n"
            f"Gate summary: Δacc={_format_float(gate.get('accuracy_delta'))}, "
            f"CI95={gate.get('accuracy_delta_ci95')}, "
            f"speedup={_format_float(gate.get('speedup'))}x, "
            f"follow_up_activity={gate.get('follow_up_vision_pruning_active_fraction')}, "
            f"follow_up_reuse={gate.get('follow_up_all_image_tokens_reused_fraction')}.\n"
            f"Repro_delta={'PASS' if gate.get('pass_repro_delta') else 'FAIL'}, "
            f"repro_ci={'PASS' if gate.get('pass_repro_ci') else 'FAIL'}, "
            f"mechanism={'PASS' if gate.get('pass_mechanism') else 'FAIL'}."
        )
    else:
        subject = "research(1.55J): land k1 sampler-variation scout"
        body = (
            "Record the fixed K=1 short-bucket repaired frontier under deterministic "
            "temperature sampling so the paper can distinguish greedy-only stability from "
            "sampler-robust paired fidelity.\n"
            f"Gate summary: correctness_diffs={gate.get('paired_correctness_diffs')}, "
            f"choice_diffs={gate.get('paired_choice_diffs')}, "
            f"follow_up_pathology={gate.get('pathological_follow_up_hits')}, "
            f"q3_pathology={gate.get('pathological_q3_hits')}, "
            "same_class_speedup="
            f"{_format_float(gate.get('speedup_follow_up_median_cold_over_session'))}x, "
            f"session_correct={gate.get('session_n_correct')}, "
            f"peak_rss={_format_float(gate.get('peak_rss_gb'))} GB.\n"
            f"Fidelity={'PASS' if gate.get('pass_fidelity') else 'FAIL'}, "
            f"exact_match={'PASS' if gate.get('pass_exact_match') else 'FAIL'}, "
            f"same_class_speed={'PASS' if gate.get('pass_same_class_speed') else 'FAIL'}, "
            f"session_floor={'PASS' if gate.get('pass_session_floor') else 'FAIL'}."
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
        if args.dry_run:
            record["gate"] = "pending"
        elif step.phase.startswith("1.55F-"):
            profile = PHASE155F_GATE_PROFILES[step.phase]
            record["gate"] = _gate_phase_155(
                pair_metrics=_load_json(_phase155_pair_metrics_path(step.phase)),
                summary=_load_json(_phase155_summary_path(step.phase)),
                correctness_limit=int(profile["correctness_limit"]),
                choice_limit=int(profile["choice_limit"]),
                q3_pathological_limit=int(profile["q3_pathological_limit"]),
                follow_up_pathological_limit=int(profile["follow_up_pathological_limit"]),
                max_rss_gb=profile["max_rss_gb"],
                min_speedup=profile["min_speedup"],
                strict_correctness_limit=int(profile["strict_correctness_limit"]),
                strict_choice_limit=int(profile["strict_choice_limit"]),
                baseline_accuracy_floor=profile["baseline_accuracy_floor"],
            )
        elif step.phase == "1.55J":
            record["gate"] = _gate_phase_155j(
                pair_metrics=_load_json(_phase155_pair_metrics_path(step.phase)),
                summary=_load_json(_phase155_summary_path(step.phase)),
            )
        elif step.phase == "1.30AC":
            record["gate"] = _gate_phase_130ac(_load_json(_phase130_pair_summary_path(step.phase)))
        else:
            record["gate"] = _gate_phase_130ad(_load_json(_phase130_pair_summary_path(step.phase)))

        step_for_commit = QueueStep(
            phase=step.phase,
            runtime_estimate=step.runtime_estimate,
            rationale=step.rationale,
            command=step.command,
            timeout_seconds=step.timeout_seconds,
            artifact_dir=step.artifact_dir,
            readiness_key=step.readiness_key,
        )
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
                step_for_commit,
                preflight_json=args.preflight_json,
                queue_status_json=args.queue_status_json,
                record=record,
            )

    if args.dry_run:
        import json

        print(json.dumps(status, indent=2))
        return 0

    print(f"[paper-adaptive-mechanism] wrote {args.queue_status_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
