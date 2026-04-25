#!/usr/bin/env python3
"""Run the remaining paper-closeout experiment queue with prereg gates."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = REPO_ROOT / "research/experiments/2026/artifacts"
PREFLIGHT_SCRIPT = REPO_ROOT / "scripts/preflight_remaining_paper_experiments.py"
PREFLIGHT_JSON = ARTIFACT_ROOT / "paper_closeout_preflight.json"
QUEUE_STATUS_JSON = ARTIFACT_ROOT / "paper_closeout_queue_status.json"


@dataclass(frozen=True, slots=True)
class QueueStep:
    phase: str
    runtime_estimate: str
    rationale: str
    command: tuple[str, ...]
    readiness_key: str | None = None


def _run(command: tuple[str, ...], *, dry_run: bool) -> None:
    print(f"[paper-closeout] $ {' '.join(command)}")
    if dry_run:
        return
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _preflight(*, dry_run: bool, output_path: Path) -> dict[str, Any]:
    _run(
        (
            sys.executable,
            str(PREFLIGHT_SCRIPT),
            "--output",
            str(output_path),
        ),
        dry_run=dry_run,
    )
    if dry_run and not output_path.exists():
        return {}
    return _load_json(output_path)


def _gate_phase_130(summary: dict[str, Any]) -> dict[str, Any]:
    accuracy_delta = float(summary["accuracy_delta_streaming_minus_cold"])
    speedup = float(summary["amortized_speedup_cold_over_streaming"])
    parse_failures = int(summary.get("streaming_parse_failures", 0))
    degenerates = int(summary.get("streaming_degenerate_count", 0))
    return {
        "accuracy_delta": accuracy_delta,
        "speedup": speedup,
        "parse_failures": parse_failures,
        "degenerates": degenerates,
        "pass_rescue": accuracy_delta >= -0.10 and speedup >= 3.0,
        "pass_format": parse_failures == 0 and degenerates == 0,
        "follow_up_vision_pruning_active_fraction": summary.get(
            "streaming_follow_up_vision_pruning_active_fraction"
        ),
        "follow_up_all_image_tokens_reused_fraction": summary.get(
            "streaming_follow_up_all_image_tokens_reused_fraction"
        ),
    }


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
) -> dict[str, Any]:
    paired_correctness_diffs = int(pair_metrics["paired_correctness_diffs"])
    paired_choice_diffs = int(pair_metrics["paired_choice_diffs"])
    pathological_q3_hits = int(pair_metrics.get("pathological_q3_hits", 0))
    speedup = pair_metrics.get("speedup_all_query_median_cold_over_session_follow_up")
    session_follow_up_median_ms = pair_metrics.get("session_follow_up_median_ms")
    peak_rss_gb = float(summary["peak_rss_gb"])
    pass_speed = True
    if min_speedup is not None:
        pass_speed = speedup is not None and float(speedup) >= min_speedup
    if max_session_follow_up_median_ms is not None:
        pass_speed = pass_speed and (
            session_follow_up_median_ms is not None
            and float(session_follow_up_median_ms) < max_session_follow_up_median_ms
        )
    return {
        "paired_correctness_diffs": paired_correctness_diffs,
        "paired_choice_diffs": paired_choice_diffs,
        "pathological_q3_hits": pathological_q3_hits,
        "speedup_all_query_median_cold_over_session_follow_up": speedup,
        "session_follow_up_median_ms": session_follow_up_median_ms,
        "peak_rss_gb": peak_rss_gb,
        "pass_fidelity": (
            paired_correctness_diffs <= correctness_limit and paired_choice_diffs <= choice_limit
        ),
        "pass_q3_pathology": pathological_q3_hits <= q3_pathological_limit,
        "pass_speed": pass_speed,
        "pass_memory": peak_rss_gb <= max_rss_gb,
    }


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
    args = parser.parse_args()

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
        "steps": [],
    }

    should_launch_130aa = True
    for step in queue_steps:
        ready = bool(experiments_ready.get(step.readiness_key or "", {}).get("ready", True))
        record: dict[str, Any] = {
            "phase": step.phase,
            "runtime_estimate": step.runtime_estimate,
            "rationale": step.rationale,
            "ready": ready,
            "command": list(step.command),
        }
        if not ready:
            record["status"] = "blocked-by-preflight"
            status["steps"].append(record)
            continue
        if step.phase == "1.30AA" and not should_launch_130aa:
            record["status"] = "skipped-by-1.30Z-gate"
            status["steps"].append(record)
            continue

        _run(step.command, dry_run=args.dry_run)
        record["status"] = "completed" if not args.dry_run else "dry-run"

        if step.phase in {"1.30Z", "1.30AA"}:
            summary_path = (
                ARTIFACT_ROOT / "phase1_30Z_long_q0_kr067_20260424/pair_summary.json"
                if step.phase == "1.30Z"
                else ARTIFACT_ROOT / "phase1_30AA_duration_conditioned_union/pair_summary.json"
            )
            if args.dry_run:
                record["gate"] = "pending"
            else:
                gate = _gate_phase_130(_load_json(summary_path))
                record["gate"] = gate
                if step.phase == "1.30Z":
                    should_launch_130aa = bool(gate["pass_rescue"] and gate["pass_format"])
        elif step.phase == "1.55F":
            if args.dry_run:
                record["gate"] = "pending"
            else:
                gate = _gate_phase_155(
                    pair_metrics=_load_json(
                        ARTIFACT_ROOT / "phase1_55F_q3_post_q2_state/pair_metrics_k1_n7.json"
                    ),
                    summary=_load_json(
                        ARTIFACT_ROOT / "phase1_55F_q3_post_q2_state/summary_k1_n7.json"
                    ),
                    correctness_limit=1,
                    choice_limit=2,
                    q3_pathological_limit=2,
                    max_rss_gb=5.0,
                    max_session_follow_up_median_ms=10135.5433955,
                )
                record["gate"] = gate
        elif step.phase == "1.55G":
            if args.dry_run:
                record["gate"] = "pending"
            else:
                gate = _gate_phase_155(
                    pair_metrics=_load_json(
                        ARTIFACT_ROOT / "phase1_55G_k1_medium_replication/pair_metrics_k1_n10.json"
                    ),
                    summary=_load_json(
                        ARTIFACT_ROOT / "phase1_55G_k1_medium_replication/summary_k1_n10.json"
                    ),
                    correctness_limit=2,
                    choice_limit=3,
                    q3_pathological_limit=2,
                    max_rss_gb=5.5,
                    min_speedup=8.0,
                )
                record["gate"] = gate

        status["steps"].append(record)

    if args.dry_run:
        print(json.dumps(status, indent=2))
        return 0

    args.queue_status_json.parent.mkdir(parents=True, exist_ok=True)
    args.queue_status_json.write_text(json.dumps(status, indent=2) + "\n")
    print(f"[paper-closeout] wrote {args.queue_status_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
