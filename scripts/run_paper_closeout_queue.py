#!/usr/bin/env python3
"""Run the remaining paper-closeout experiment queue with prereg gates."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = REPO_ROOT / "research/experiments/2026/artifacts"
PREFLIGHT_SCRIPT = REPO_ROOT / "scripts/preflight_remaining_paper_experiments.py"
PREFLIGHT_JSON = ARTIFACT_ROOT / "paper_closeout_preflight.json"
QUEUE_STATUS_JSON = ARTIFACT_ROOT / "paper_closeout_queue_status.json"
PHASE155D_K1_PAIR_METRICS = (
    ARTIFACT_ROOT / "phase1_55D_selective_reprefill_v2/pair_metrics_k1_n7.json"
)


@dataclass(frozen=True, slots=True)
class QueueStep:
    phase: str
    runtime_estimate: str
    rationale: str
    command: tuple[str, ...]
    timeout_seconds: int
    artifact_dir: Path
    readiness_key: str | None = None


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _run(command: tuple[str, ...], *, dry_run: bool, timeout_seconds: int) -> None:
    print(f"[paper-closeout] $ {' '.join(command)}")
    if dry_run:
        return
    subprocess.run(command, cwd=REPO_ROOT, check=True, timeout=timeout_seconds)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _write_status(path: Path, status: dict[str, Any], *, dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    status["updated_at"] = _timestamp()
    path.write_text(json.dumps(status, indent=2) + "\n")


def _preflight(*, dry_run: bool, output_path: Path) -> dict[str, Any]:
    _run(
        (
            sys.executable,
            str(PREFLIGHT_SCRIPT),
            "--output",
            str(output_path),
        ),
        dry_run=dry_run,
        timeout_seconds=60,
    )
    if dry_run and not output_path.exists():
        return {}
    return _load_json(output_path)


def _gate_phase_130(
    summary: dict[str, Any],
    *,
    expected_paired_queries: int | None = None,
    expected_paired_sessions: int | None = None,
) -> dict[str, Any]:
    accuracy_delta = float(summary["accuracy_delta_streaming_minus_cold"])
    speedup = float(summary["amortized_speedup_cold_over_streaming"])
    parse_failures = int(summary.get("streaming_parse_failures", 0))
    degenerates = int(summary.get("streaming_degenerate_count", 0))
    n_paired_queries = int(summary.get("n_paired_queries", 0))
    n_paired_sessions = int(summary.get("n_paired_sessions", 0))
    follow_up_active_fraction = summary.get("streaming_follow_up_vision_pruning_active_fraction")
    materially_active = (
        follow_up_active_fraction is not None and float(follow_up_active_fraction) >= 0.10
    )
    pass_complete_pairing = True
    if expected_paired_queries is not None:
        pass_complete_pairing = pass_complete_pairing and (
            n_paired_queries == expected_paired_queries
        )
    if expected_paired_sessions is not None:
        pass_complete_pairing = pass_complete_pairing and (
            n_paired_sessions == expected_paired_sessions
        )
    return {
        "accuracy_delta": accuracy_delta,
        "accuracy_delta_ci95": summary.get("accuracy_delta_streaming_minus_cold_ci95"),
        "speedup": speedup,
        "parse_failures": parse_failures,
        "degenerates": degenerates,
        "n_paired_queries": n_paired_queries,
        "n_paired_sessions": n_paired_sessions,
        "pass_complete_pairing": pass_complete_pairing,
        "pass_rescue": pass_complete_pairing and accuracy_delta >= -0.10 and speedup >= 3.0,
        "pass_format": parse_failures == 0 and degenerates == 0,
        "follow_up_vision_pruning_active_fraction": follow_up_active_fraction,
        "follow_up_all_image_tokens_reused_fraction": summary.get(
            "streaming_follow_up_all_image_tokens_reused_fraction"
        ),
        "follow_up_pruning_materially_active": materially_active,
    }


def _load_phase155d_k1_reference_follow_up_median_ms() -> float:
    pair_metrics = _load_json(PHASE155D_K1_PAIR_METRICS)
    value = pair_metrics.get("session_follow_up_median_ms")
    if value is None:
        raise SystemExit(f"missing session_follow_up_median_ms in {PHASE155D_K1_PAIR_METRICS}")
    return float(value)


def _gate_phase_155(
    *,
    pair_metrics: dict[str, Any],
    summary: dict[str, Any],
    correctness_limit: int,
    choice_limit: int,
    q3_pathological_limit: int,
    max_rss_gb: float,
    min_speedup: float | None = None,
    max_session_follow_up_median_ms: float | None = None,
    strict_correctness_limit: int | None = None,
    strict_choice_limit: int | None = None,
    baseline_accuracy_floor: float | None = None,
) -> dict[str, Any]:
    paired_correctness_diffs = int(pair_metrics["paired_correctness_diffs"])
    paired_choice_diffs = int(pair_metrics["paired_choice_diffs"])
    pathological_q3_hits = int(pair_metrics.get("pathological_q3_hits", 0))
    speedup = pair_metrics.get("speedup_all_query_median_cold_over_session_follow_up")
    session_follow_up_median_ms = pair_metrics.get("session_follow_up_median_ms")
    peak_rss_gb = float(summary["peak_rss_gb"])
    baseline_accuracy = summary.get("baseline", {}).get("accuracy")

    pass_speed = True
    if min_speedup is not None:
        pass_speed = speedup is not None and float(speedup) >= min_speedup
    if max_session_follow_up_median_ms is not None:
        pass_speed = pass_speed and (
            session_follow_up_median_ms is not None
            and float(session_follow_up_median_ms) <= max_session_follow_up_median_ms
        )

    pass_exact_match = None
    if strict_correctness_limit is not None and strict_choice_limit is not None:
        pass_exact_match = (
            paired_correctness_diffs <= strict_correctness_limit
            and paired_choice_diffs <= strict_choice_limit
        )

    pass_signal_floor = None
    if baseline_accuracy_floor is not None:
        pass_signal_floor = (
            baseline_accuracy is not None and float(baseline_accuracy) >= baseline_accuracy_floor
        )

    return {
        "paired_correctness_diffs": paired_correctness_diffs,
        "paired_choice_diffs": paired_choice_diffs,
        "pathological_q3_hits": pathological_q3_hits,
        "speedup_all_query_median_cold_over_session_follow_up": speedup,
        "session_follow_up_median_ms": session_follow_up_median_ms,
        "peak_rss_gb": peak_rss_gb,
        "baseline_accuracy": baseline_accuracy,
        "pass_fidelity": (
            paired_correctness_diffs <= correctness_limit and paired_choice_diffs <= choice_limit
        ),
        "pass_exact_match": pass_exact_match,
        "pass_q3_pathology": pathological_q3_hits <= q3_pathological_limit,
        "pass_speed": pass_speed,
        "pass_memory": peak_rss_gb <= max_rss_gb,
        "pass_signal_floor": pass_signal_floor,
    }


def _phase_gate_paths(phase: str) -> Path:
    return {
        "1.30Z": ARTIFACT_ROOT / "phase1_30Z_long_q0_kr067_20260424/pair_summary.json",
        "1.30AA": ARTIFACT_ROOT / "phase1_30AA_duration_conditioned_union/pair_summary.json",
        "1.55F": ARTIFACT_ROOT / "phase1_55F_q3_post_q2_state/pair_metrics_k1_n7.json",
        "1.55G": ARTIFACT_ROOT / "phase1_55G_k1_medium_replication/pair_metrics_k1_n10.json",
    }[phase]


def _phase_summary_paths(phase: str) -> Path | None:
    return {
        "1.55F": ARTIFACT_ROOT / "phase1_55F_q3_post_q2_state/summary_k1_n7.json",
        "1.55G": ARTIFACT_ROOT / "phase1_55G_k1_medium_replication/summary_k1_n10.json",
    }.get(phase)


def _check_clean_worktree() -> None:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    if result.stdout.strip():
        raise SystemExit(
            "--auto-commit requires a clean worktree at queue start; commit or stash "
            "existing changes first."
        )


def _paths_have_changes(paths: tuple[Path, ...]) -> bool:
    command = ["git", "status", "--porcelain", "--untracked-files=all", "--"]
    command.extend(path.as_posix() for path in paths)
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def _format_float(value: Any, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}f}"


def _commit_message(step: QueueStep, record: dict[str, Any]) -> str:
    gate = record.get("gate", {})
    if step.phase == "1.30Z":
        subject = "research(1.30Z): land long-bucket q0 kr0.67 continuation"
        body = (
            "Record the fully measured long-bucket generalization test so the admission-policy "
            "lane no longer depends on the selection-biased 1.30Y residual-pair scout.\n"
            f"Gate summary: Δacc={_format_float(gate.get('accuracy_delta'))}, "
            f"CI95={gate.get('accuracy_delta_ci95')}, "
            f"speedup={_format_float(gate.get('speedup'))}×, "
            f"parse_failures={gate.get('parse_failures')}, "
            f"degenerates={gate.get('degenerates')}, "
            f"follow-up activity={gate.get('follow_up_vision_pruning_active_fraction')}.\n"
            f"Rescue={'PASS' if gate.get('pass_rescue') else 'FAIL'} and "
            f"format={'PASS' if gate.get('pass_format') else 'FAIL'}; queue status snapshot "
            "was updated with the same adjudication."
        )
    elif step.phase == "1.30AA":
        subject = "research(1.30AA): land duration-conditioned union rerun"
        body = (
            "Record the first no-splice duration-conditioned bridge measurement so the paper "
            "can cite a fully measured local admission-policy result rather than an oracle or "
            "cross-run splice.\n"
            f"Gate summary: Δacc={_format_float(gate.get('accuracy_delta'))}, "
            f"CI95={gate.get('accuracy_delta_ci95')}, "
            f"speedup={_format_float(gate.get('speedup'))}×, "
            f"parse_failures={gate.get('parse_failures')}, "
            f"degenerates={gate.get('degenerates')}, "
            f"follow-up activity={gate.get('follow_up_vision_pruning_active_fraction')}.\n"
            f"Rescue={'PASS' if gate.get('pass_rescue') else 'FAIL'} and "
            f"format={'PASS' if gate.get('pass_format') else 'FAIL'}; the artifact commit is "
            "meant to preserve the exact measured bridge state for later paper sync."
        )
    elif step.phase == "1.55F":
        subject = "research(1.55F): land q3 post-q2 repaired-state probe"
        body = (
            "Record the causal follow-up to 1.55E so the C-PERSIST story can distinguish "
            "between Q3 cache-source failure and a deeper adaptive-repair failure.\n"
            f"Gate summary: paired_correctness_diffs={gate.get('paired_correctness_diffs')}, "
            f"paired_choice_diffs={gate.get('paired_choice_diffs')}, "
            f"q3_pathology_hits={gate.get('pathological_q3_hits')}, "
            f"follow-up median={_format_float(gate.get('session_follow_up_median_ms'), 1)} ms, "
            "speedup="
            f"{_format_float(gate.get('speedup_all_query_median_cold_over_session_follow_up'))}×, "
            f"peak_rss={_format_float(gate.get('peak_rss_gb'))} GB.\n"
            f"Exact-match={'PASS' if gate.get('pass_exact_match') else 'FAIL'} and "
            f"primary fidelity={'PASS' if gate.get('pass_fidelity') else 'FAIL'}; queue status "
            "snapshot stores the same gate evaluation."
        )
    else:
        subject = "research(1.55G): land medium-bucket k1 replication"
        body = (
            "Record the first medium-bucket scope test for the landed 1.55D K=1 point so the "
            "paper can state whether the recovery frontier is short-only or multi-regime.\n"
            f"Gate summary: paired_correctness_diffs={gate.get('paired_correctness_diffs')}, "
            f"paired_choice_diffs={gate.get('paired_choice_diffs')}, "
            f"baseline_accuracy={_format_float(gate.get('baseline_accuracy'))}, "
            "speedup="
            f"{_format_float(gate.get('speedup_all_query_median_cold_over_session_follow_up'))}×, "
            f"peak_rss={_format_float(gate.get('peak_rss_gb'))} GB.\n"
            f"Fidelity={'PASS' if gate.get('pass_fidelity') else 'FAIL'}, "
            f"signal-floor={'PASS' if gate.get('pass_signal_floor') else 'FAIL'} and "
            f"memory={'PASS' if gate.get('pass_memory') else 'FAIL'}; commit preserves the exact "
            "artifact state used for later paper updates."
        )
    return f"{subject}\n\n{body}"


def _commit_step(step: QueueStep, *, queue_status_json: Path, record: dict[str, Any]) -> None:
    subprocess.run(
        ["git", "add", step.artifact_dir.as_posix(), queue_status_json.as_posix()],
        cwd=REPO_ROOT,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", _commit_message(step, record)],
        cwd=REPO_ROOT,
        check=True,
    )


def _steps() -> list[QueueStep]:
    return [
        QueueStep(
            phase="1.30Z",
            runtime_estimate="~3.5-5.0 h",
            rationale=(
                "Generalize the selection-biased 1.30Y residual scout to the full "
                "long bucket before any no-splice union rerun."
            ),
            command=("bash", str(REPO_ROOT / "scripts/run_phase1_30Z_long_q0_kr067.sh")),
            timeout_seconds=27_000,
            artifact_dir=ARTIFACT_ROOT / "phase1_30Z_long_q0_kr067_20260424",
            readiness_key="1.30Z",
        ),
        QueueStep(
            phase="1.30AA",
            runtime_estimate="~5.5-7.5 h",
            rationale=(
                "Replace the 1.30Y splice with a fully measured, duration-conditioned "
                "no-splice union rerun."
            ),
            command=(
                "bash",
                str(REPO_ROOT / "scripts/run_phase1_30AA_duration_conditioned_union.sh"),
            ),
            timeout_seconds=40_500,
            artifact_dir=ARTIFACT_ROOT / "phase1_30AA_duration_conditioned_union",
            readiness_key="1.30AA",
        ),
        QueueStep(
            phase="1.55F",
            runtime_estimate="~60-75 min",
            rationale=(
                "Test whether the 1.55E Q3 collapse is caused by falling back to the "
                "unrepaired Q1 cache instead of reusing the repaired Q2 state."
            ),
            command=("bash", str(REPO_ROOT / "scripts/run_phase1_55F_q3_post_q2_state.sh")),
            timeout_seconds=7_200,
            artifact_dir=ARTIFACT_ROOT / "phase1_55F_q3_post_q2_state",
            readiness_key="1.55F",
        ),
        QueueStep(
            phase="1.55G",
            runtime_estimate="~1.7-2.2 h",
            rationale=(
                "Replicate the 1.55D K=1 no-observed-drift point on the fixed "
                "medium-bucket tranche."
            ),
            command=("bash", str(REPO_ROOT / "scripts/run_phase1_55G_k1_medium_replication.sh")),
            timeout_seconds=12_600,
            artifact_dir=ARTIFACT_ROOT / "phase1_55G_k1_medium_replication",
            readiness_key="1.55G",
        ),
    ]


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

    should_launch_130aa = True
    for step in queue_steps:
        ready = bool(experiments_ready.get(step.readiness_key or "", {}).get("ready", True))
        record: dict[str, Any] = {
            "phase": step.phase,
            "runtime_estimate": step.runtime_estimate,
            "rationale": step.rationale,
            "ready": ready,
            "command": list(step.command),
            "timeout_seconds": step.timeout_seconds,
            "artifact_dir": step.artifact_dir.as_posix(),
        }
        if not ready:
            record["status"] = "blocked-by-preflight"
            status["steps"].append(record)
            _write_status(args.queue_status_json, status, dry_run=args.dry_run)
            continue
        if step.phase == "1.30AA" and not should_launch_130aa:
            record["status"] = "skipped-by-1.30Z-gate"
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
            if step.phase == "1.30Z":
                should_launch_130aa = False
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
            if step.phase == "1.30Z":
                should_launch_130aa = False
            status["steps"].append(record)
            _write_status(args.queue_status_json, status, dry_run=args.dry_run)
            if args.strict:
                raise
            continue

        record["status"] = "completed" if not args.dry_run else "dry-run"

        if step.phase in {"1.30Z", "1.30AA"}:
            if args.dry_run:
                record["gate"] = "pending"
            else:
                expected_queries = 54 if step.phase == "1.30Z" else 171
                expected_sessions = 18 if step.phase == "1.30Z" else 57
                gate = _gate_phase_130(
                    _load_json(_phase_gate_paths(step.phase)),
                    expected_paired_queries=expected_queries,
                    expected_paired_sessions=expected_sessions,
                )
                record["gate"] = gate
                if step.phase == "1.30Z":
                    should_launch_130aa = bool(gate["pass_rescue"] and gate["pass_format"])
        elif step.phase == "1.55F":
            if args.dry_run:
                record["gate"] = "pending"
            else:
                summary_path = _phase_summary_paths(step.phase)
                assert summary_path is not None
                reference_follow_up_median_ms = _load_phase155d_k1_reference_follow_up_median_ms()
                record["gate"] = _gate_phase_155(
                    pair_metrics=_load_json(_phase_gate_paths(step.phase)),
                    summary=_load_json(summary_path),
                    correctness_limit=1,
                    choice_limit=2,
                    q3_pathological_limit=2,
                    max_rss_gb=5.0,
                    max_session_follow_up_median_ms=reference_follow_up_median_ms,
                    strict_correctness_limit=0,
                    strict_choice_limit=0,
                )
        elif step.phase == "1.55G":
            if args.dry_run:
                record["gate"] = "pending"
            else:
                summary_path = _phase_summary_paths(step.phase)
                assert summary_path is not None
                record["gate"] = _gate_phase_155(
                    pair_metrics=_load_json(_phase_gate_paths(step.phase)),
                    summary=_load_json(summary_path),
                    correctness_limit=2,
                    choice_limit=3,
                    q3_pathological_limit=2,
                    max_rss_gb=5.5,
                    min_speedup=8.0,
                    baseline_accuracy_floor=0.40,
                )

        if args.auto_commit and not args.dry_run:
            record["auto_commit"] = (
                "committed"
                if _paths_have_changes((step.artifact_dir, args.queue_status_json))
                else "no-changes"
            )
        status["steps"].append(record)
        _write_status(args.queue_status_json, status, dry_run=args.dry_run)
        if args.auto_commit and not args.dry_run and record["auto_commit"] == "committed":
            _commit_step(step, queue_status_json=args.queue_status_json, record=record)

    if args.dry_run:
        print(json.dumps(status, indent=2))
        return 0

    print(f"[paper-closeout] wrote {args.queue_status_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
