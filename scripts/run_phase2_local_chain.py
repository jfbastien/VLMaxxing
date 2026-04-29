#!/usr/bin/env python3
"""Run the phase-2 local closeout experiment chain autonomously."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "research" / "experiments" / "2026" / "artifacts"
STATUS_PATH = ARTIFACT_ROOT / "phase2_local_chain_status.json"


@dataclass(frozen=True, slots=True)
class Step:
    name: str
    command: tuple[str, ...]
    artifact_paths: tuple[Path, ...]
    summary_path: Path
    timeout_s: int
    commit_message: str
    required_gates: tuple[str, ...] = ()


def _steps() -> list[Step]:
    return [
        Step(
            name="A1-1.63G-format-diagnostic",
            command=("scripts/run_phase1_63G_format_diagnostic.sh",),
            artifact_paths=(
                ARTIFACT_ROOT / "phase1_63G_gemma_track_b" / "format_diagnostic_summary.json",
            ),
            summary_path=ARTIFACT_ROOT
            / "phase1_63G_gemma_track_b"
            / "format_diagnostic_summary.json",
            timeout_s=30 * 60,
            commit_message="research(1.63G): land Gemma format diagnostic",
            required_gates=("pass_matched_failure_diagnostic", "pass_parser_not_fixable"),
        ),
        Step(
            name="A2-1.65v2-richer-predictor",
            command=("scripts/run_phase1_65v2_richer_predictor.sh",),
            artifact_paths=(ARTIFACT_ROOT / "phase1_65v2_richer_predictor",),
            summary_path=ARTIFACT_ROOT / "phase1_65v2_richer_predictor" / "prediction_summary.json",
            timeout_s=30 * 60,
            commit_message="research(1.65v2): land richer stability predictor",
        ),
        Step(
            name="A3-1.62D-lowfps-dense",
            command=("scripts/run_phase1_62D_lowfps_dense_videomme.sh",),
            artifact_paths=(ARTIFACT_ROOT / "phase1_62D_lowfps_dense_videomme",),
            summary_path=ARTIFACT_ROOT / "phase1_62D_lowfps_dense_videomme" / "summary.json",
            timeout_s=5 * 60 * 60,
            commit_message="research(1.62D): land low-fps dense baseline",
            required_gates=("pass_complete_pairing", "pass_format"),
        ),
        Step(
            name="A4-1.63I-qwen-16f-kr-bracket",
            command=("scripts/run_phase1_63I_16f_kr_fine_bracket.sh",),
            artifact_paths=(ARTIFACT_ROOT / "phase1_63I_16f_kr_fine_bracket",),
            summary_path=ARTIFACT_ROOT
            / "phase1_63I_16f_kr_fine_bracket"
            / "fine_bracket_summary.json",
            timeout_s=12 * 60 * 60,
            commit_message="research(1.63I): land Qwen 16f keep-rate bracket",
            required_gates=("complete",),
        ),
        Step(
            name="A6-1.55L-many-turn-cpersist",
            command=("scripts/run_phase1_55L_many_turn_cpersist.sh",),
            artifact_paths=(ARTIFACT_ROOT / "phase1_55L_many_turn_cpersist",),
            summary_path=ARTIFACT_ROOT / "phase1_55L_many_turn_cpersist" / "summary.json",
            timeout_s=14 * 60 * 60,
            commit_message="research(1.55L): land many-turn C-PERSIST horizon",
            required_gates=(
                "pass_complete_row_counts",
                "pass_complete_cells",
                "pass_complete_chain_counts",
                "pass_complete_turn_coverage",
                "pass_complete_policy_horizon_grid",
            ),
        ),
        Step(
            name="A7-1.55K-extended-seed-sweep",
            command=("scripts/run_phase1_55K_extended_seed_sweep.sh",),
            artifact_paths=(ARTIFACT_ROOT / "phase1_55K_extended_seed_sweep",),
            summary_path=ARTIFACT_ROOT
            / "phase1_55K_extended_seed_sweep"
            / "extended_seed_sweep_summary.json",
            timeout_s=9 * 60 * 60,
            commit_message="research(1.55K): land sampler seed sweep",
            required_gates=("pass_expected_grid", "pass_expected_row_counts"),
        ),
        Step(
            name="A5-1.30AG-kcache-distance",
            command=("scripts/run_phase1_30AG_kcache_distance_probe.sh",),
            artifact_paths=(ARTIFACT_ROOT / "phase1_30AG_kcache_distance_probe",),
            summary_path=ARTIFACT_ROOT
            / "phase1_30AG_kcache_distance_probe"
            / "kcache_distance_summary.json",
            timeout_s=4 * 60 * 60,
            commit_message="research(1.30AG): land K/V cache-distance probe",
            required_gates=(
                "pass_H1_capture",
                "pass_H2_distance_report",
                "pass_H3_outcome_link",
            ),
        ),
    ]


def _run(cmd: tuple[str, ...], *, timeout_s: int) -> None:
    print(f"[phase2] $ {' '.join(cmd)}", flush=True)
    subprocess.run(
        cmd,
        cwd=ROOT,
        check=True,
        timeout=timeout_s,
    )


def _git_status_short(paths: list[Path] | None = None) -> list[str]:
    cmd = ["git", "status", "--short"]
    if paths:
        cmd.extend(path.as_posix() for path in paths)
    out = subprocess.check_output(cmd, cwd=ROOT, text=True)
    return [line for line in out.splitlines() if line.strip()]


def _check_clean_worktree() -> None:
    dirty = _git_status_short()
    if dirty:
        rendered = "\n".join(dirty[:30])
        raise SystemExit(
            f"phase2 local chain requires a clean worktree before launch; dirty paths:\n{rendered}"
        )


def _paths_have_changes(paths: tuple[Path, ...]) -> bool:
    return bool(_git_status_short(list(paths)))


def _auto_commit(step: Step) -> None:
    paths = [path for path in step.artifact_paths if path.exists()]
    paths.append(STATUS_PATH)
    if not paths:
        return
    subprocess.run(
        ["git", "add", *[path.as_posix() for path in paths]],
        cwd=ROOT,
        check=True,
    )
    if not _paths_have_changes(tuple(paths)):
        print(f"[phase2] no artifact changes to commit for {step.name}", flush=True)
        return
    subprocess.run(
        ["git", "commit", "-m", step.commit_message],
        cwd=ROOT,
        check=True,
    )


def _load_summary(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {"unparseable_summary": path.as_posix()}


def _validate_summary(step: Step) -> dict[str, Any]:
    summary = _load_summary(step.summary_path)
    if summary is None:
        raise RuntimeError(f"{step.name} did not produce summary {step.summary_path}")
    if "unparseable_summary" in summary:
        raise RuntimeError(f"{step.name} produced unparseable summary {step.summary_path}")
    failed = [gate for gate in step.required_gates if not bool(summary.get(gate))]
    if failed:
        raise RuntimeError(f"{step.name} failed required gate(s): {', '.join(failed)}")
    return summary


def _status_payload(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "phase": "phase2-local-chain",
        "records": records,
        "updated_at_unix_s": time.time(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--auto-commit", action="store_true")
    parser.add_argument(
        "--start-at",
        default=None,
        help="Step name or prefix to resume from.",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Skip the initial clean-worktree check. Intended only for smoke testing.",
    )
    parser.add_argument(
        "--continue-on-failure",
        action="store_true",
        help="Continue after a failed step. Default is fail-closed.",
    )
    parser.add_argument(
        "--commit-failed-artifacts",
        action="store_true",
        help="With --auto-commit, also commit artifacts from failed steps.",
    )
    args = parser.parse_args()

    steps = _steps()
    if args.start_at:
        matches = [idx for idx, step in enumerate(steps) if step.name.startswith(args.start_at)]
        if not matches:
            raise SystemExit(f"unknown --start-at {args.start_at!r}")
        steps = steps[matches[0] :]

    if args.dry_run:
        print(
            json.dumps(
                {
                    "steps": [
                        {
                            "name": step.name,
                            "command": list(step.command),
                            "summary_path": step.summary_path.as_posix(),
                            "timeout_s": step.timeout_s,
                            "required_gates": list(step.required_gates),
                        }
                        for step in steps
                    ]
                },
                indent=2,
            )
        )
        return 0

    if not args.allow_dirty:
        _check_clean_worktree()

    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    STATUS_PATH.write_text(json.dumps(_status_payload(records), indent=2) + "\n")
    for step in steps:
        start = time.perf_counter()
        record: dict[str, Any] = {
            "name": step.name,
            "command": list(step.command),
            "status": "running",
            "summary_path": step.summary_path.as_posix(),
        }
        records.append(record)
        STATUS_PATH.write_text(json.dumps(_status_payload(records), indent=2) + "\n")
        try:
            _run(step.command, timeout_s=step.timeout_s)
        except subprocess.TimeoutExpired as exc:
            record.update(
                {
                    "status": "timeout",
                    "returncode": None,
                    "elapsed_s": time.perf_counter() - start,
                    "error": str(exc),
                }
            )
            STATUS_PATH.write_text(json.dumps(_status_payload(records), indent=2) + "\n")
            if args.auto_commit and args.commit_failed_artifacts:
                _auto_commit(step)
            if args.continue_on_failure:
                continue
            return 1
        except subprocess.CalledProcessError as exc:
            record.update(
                {
                    "status": "failed",
                    "returncode": exc.returncode,
                    "elapsed_s": time.perf_counter() - start,
                    "error": str(exc),
                }
            )
            STATUS_PATH.write_text(json.dumps(_status_payload(records), indent=2) + "\n")
            if args.auto_commit and args.commit_failed_artifacts:
                _auto_commit(step)
            if args.continue_on_failure:
                continue
            return int(exc.returncode)
        except OSError as exc:
            record.update(
                {
                    "status": "failed-launch",
                    "returncode": None,
                    "elapsed_s": time.perf_counter() - start,
                    "error": str(exc),
                }
            )
            STATUS_PATH.write_text(json.dumps(_status_payload(records), indent=2) + "\n")
            if args.auto_commit and args.commit_failed_artifacts:
                _auto_commit(step)
            if args.continue_on_failure:
                continue
            return 1

        try:
            summary = _validate_summary(step)
        except RuntimeError as exc:
            record.update(
                {
                    "status": "failed-summary-validation",
                    "elapsed_s": time.perf_counter() - start,
                    "error": str(exc),
                }
            )
            STATUS_PATH.write_text(json.dumps(_status_payload(records), indent=2) + "\n")
            if args.auto_commit and args.commit_failed_artifacts:
                _auto_commit(step)
            if args.continue_on_failure:
                continue
            return 1
        record.update(
            {
                "status": "completed",
                "elapsed_s": time.perf_counter() - start,
                "summary": summary,
            }
        )
        STATUS_PATH.write_text(json.dumps(_status_payload(records), indent=2) + "\n")
        if args.auto_commit:
            _auto_commit(step)

    print(f"[phase2] wrote {STATUS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
