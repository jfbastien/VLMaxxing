#!/usr/bin/env python3
"""Run the deep-mechanism paper closeout queue.

This queue is intentionally separate from the reviewer-defense queue. It adds
the larger mechanism tests requested after Track B landed:

* 1.63E: Qwen Track B frame-budget scaling.
* 1.63G: Gemma Track B architecture check.
* 1.55F-stage-timing: adaptive-vs-fixed timing attribution.
* 1.55K: adaptive sampler-temperature sweep.
* 1.30AF: cache-boundary row-level attribution.
* 1.65: within-1.30 dense logit-margin predictor scout.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Any

from run_paper_closeout_queue import (
    ARTIFACT_ROOT,
    REPO_ROOT,
    QueueStep,
    _format_float,
    _load_json,
    _paths_have_changes,
    _preflight,
    _run,
    _timestamp,
    _write_status,
)

PREFLIGHT_JSON = ARTIFACT_ROOT / "paper_deep_mechanism_preflight.json"
QUEUE_STATUS_JSON = ARTIFACT_ROOT / "paper_deep_mechanism_queue_status.json"


def _allowed_startup_dirty_paths() -> tuple[Path, ...]:
    return (
        PREFLIGHT_JSON,
        QUEUE_STATUS_JSON,
        ARTIFACT_ROOT / "phase1_63E_track_b_frame_scaling",
        ARTIFACT_ROOT / "phase1_63G_gemma_track_b",
        ARTIFACT_ROOT / "phase1_55F_stage_timing",
        ARTIFACT_ROOT / "phase1_55K_adaptive_temperature_sweep",
        ARTIFACT_ROOT / "phase1_30AF_cache_boundary_attribution",
        ARTIFACT_ROOT / "phase1_65_logit_margin_failure_predictor",
    )


def _is_allowed_startup_dirty_path(path: Path) -> bool:
    resolved = (REPO_ROOT / path).resolve()
    for allowed in _allowed_startup_dirty_paths():
        allowed_resolved = allowed.resolve()
        if resolved == allowed_resolved or allowed_resolved in resolved.parents:
            return True
    return False


def _check_queue_worktree() -> None:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    disallowed: list[str] = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        path_text = line[3:]
        if " -> " in path_text:
            _old, path_text = path_text.split(" -> ", 1)
        if not _is_allowed_startup_dirty_path(Path(path_text)):
            disallowed.append(line)
    if disallowed:
        details = "\n".join(disallowed)
        raise SystemExit(
            "deep-mechanism queue requires a clean source tree; only its own "
            f"artifact/status paths may be dirty before resume.\n{details}"
        )


def _steps() -> list[QueueStep]:
    return [
        QueueStep(
            phase="1.55F-stage-timing",
            runtime_estimate="~1 min (analysis-only)",
            rationale=(
                "Attribute the adaptive-vs-fixed C-PERSIST speedup gap from "
                "existing artifacts by comparing Q3 elapsed time and tail-token "
                "counts. This explains why adaptive is faster without another "
                "accuracy run."
            ),
            command=("bash", str(REPO_ROOT / "scripts/run_phase1_55F_stage_timing_analysis.sh")),
            timeout_seconds=600,
            artifact_dir=ARTIFACT_ROOT / "phase1_55F_stage_timing",
            readiness_key="1.55F-stage-timing",
        ),
        QueueStep(
            phase="1.63E",
            runtime_estimate="~7.5-9.5 h with 8f/16f/20f/32f default",
            rationale=(
                "Run Track B compact Qwen ViT at 8f, 16f, 20f, and 32f to test "
                "whether the arithmetic ceiling predicts measured wall-clock "
                "across frame budgets rather than using 8f as a non-veto reference."
            ),
            command=("bash", str(REPO_ROOT / "scripts/run_phase1_63E_track_b_frame_scaling.sh")),
            timeout_seconds=36_000,
            artifact_dir=ARTIFACT_ROOT / "phase1_63E_track_b_frame_scaling",
            readiness_key="1.63E",
        ),
        QueueStep(
            phase="1.63G",
            runtime_estimate="~2.5-3.5 h",
            rationale=(
                "Run the same vision-tower-only Track B compact execution on "
                "Gemma 4 E4B to test whether the ceiling/sparse-execution story "
                "is architecture-general rather than Qwen-only."
            ),
            command=("bash", str(REPO_ROOT / "scripts/run_phase1_63G_gemma_track_b.sh")),
            timeout_seconds=18_000,
            artifact_dir=ARTIFACT_ROOT / "phase1_63G_gemma_track_b",
            readiness_key="1.63G",
        ),
        QueueStep(
            phase="1.55K",
            runtime_estimate="~4-6 h",
            rationale=(
                "Run the adaptive 1.55F policy across practical sampling "
                "temperatures to test whether the headline 0-drift result is "
                "greedy-only or sampler-stable."
            ),
            command=("bash", str(REPO_ROOT / "scripts/run_phase1_55K_k1_temperature_sweep.sh")),
            timeout_seconds=28_800,
            artifact_dir=ARTIFACT_ROOT / "phase1_55K_adaptive_temperature_sweep",
            readiness_key="1.55K",
        ),
        QueueStep(
            phase="1.30AF",
            runtime_estimate="~1 min (analysis-only)",
            rationale=(
                "Compare the 1.30AC cache-invalidated and 1.30AD cache-reuse "
                "failure sets to verify whether their equal aggregate loss is "
                "row-identical or a boundary aggregate reached through different "
                "mechanisms."
            ),
            command=(
                "bash",
                str(REPO_ROOT / "scripts/run_phase1_30AF_cache_boundary_attribution.sh"),
            ),
            timeout_seconds=600,
            artifact_dir=ARTIFACT_ROOT / "phase1_30AF_cache_boundary_attribution",
            readiness_key="1.30AF",
        ),
        QueueStep(
            phase="1.65",
            runtime_estimate="~5-8 h at default PHASE1_65_MAX_ROWS=0",
            rationale=(
                "Re-score the 1.30 cache-boundary paired artifacts with dense "
                "Qwen answer-letter logprobs, using a grouped train/test split, "
                "to test whether logit margin predicts paired stability."
            ),
            command=("bash", str(REPO_ROOT / "scripts/run_phase1_65_logit_margin_probe.sh")),
            timeout_seconds=36_000,
            artifact_dir=ARTIFACT_ROOT / "phase1_65_logit_margin_failure_predictor",
            readiness_key="1.65",
        ),
    ]


def _gate_phase_163e(artifact_dir: Path) -> dict[str, Any]:
    summary = _load_json(artifact_dir / "scaling_summary.json")
    return {
        "complete": summary["complete"],
        "headline_pass": summary["headline_pass"],
        "n_cells": summary["n_cells"],
        "frame_counts": summary["frame_counts"],
        "headline_frame_counts": summary.get("headline_frame_counts"),
        "reference_frame_counts": summary.get("reference_frame_counts"),
        "max_abs_actual_minus_predicted": summary["max_abs_actual_minus_predicted"],
        "headline_max_abs_actual_minus_predicted": summary.get(
            "headline_max_abs_actual_minus_predicted"
        ),
        "cells": [
            {
                "frame_count": cell["frame_count"],
                "n_paired_items": cell["n_paired_items"],
                "accuracy_delta": cell["accuracy_delta"],
                "vision_reduction": cell["vision_reduction"],
                "actual_e2e_speedup": cell["actual_e2e_speedup"],
                "predicted_e2e_speedup": cell["predicted_e2e_speedup"],
                "actual_minus_predicted": cell["actual_minus_predicted"],
                "pass_fidelity": cell["pass_fidelity"],
                "pass_sparse_vision": cell["pass_sparse_vision"],
                "pass_e2e_positive": cell["pass_e2e_positive"],
                "pass_ceiling_explained": cell["pass_ceiling_explained"],
            }
            for cell in summary["cells"]
        ],
    }


def _gate_phase_163g(artifact_dir: Path) -> dict[str, Any]:
    summary = _load_json(artifact_dir / "pair_summary.json")
    all_summary = summary["all"]
    return {
        "n_paired_items": summary["n_paired_items"],
        "pass_complete_pairing": summary["pass_complete_pairing"],
        "pass_format": summary["pass_format"],
        "accuracy_delta": all_summary["accuracy_delta_sparse_minus_dense"],
        "choice_agreement": all_summary["choice_agreement"],
        "mean_keep_rate": all_summary["mean_keep_rate"],
        "vision_reduction": all_summary["vision_reduction"],
        "vision_speedup_dense_over_sparse": all_summary["vision_speedup_dense_over_sparse"],
        "actual_e2e_speedup_dense_over_sparse": all_summary["actual_e2e_speedup_dense_over_sparse"],
        "predicted_e2e_speedup_from_vision_only": all_summary[
            "predicted_e2e_speedup_from_vision_only"
        ],
        "actual_minus_predicted_e2e_speedup": all_summary["actual_minus_predicted_e2e_speedup"],
        "pass_fidelity": summary["pass_fidelity"],
        "pass_sparse_vision": summary["pass_sparse_vision"],
        "pass_e2e_positive": summary["pass_e2e_positive"],
        "pass_ceiling_explained": summary["pass_ceiling_explained"],
    }


def _gate_phase_165(artifact_dir: Path) -> dict[str, Any]:
    summary = _load_json(artifact_dir / "prediction_summary.json")
    train_safe_filter = summary.get("train_safe_filter") or {}
    test_safe_filter = summary.get("test_safe_filter_at_train_threshold") or {}
    return {
        "n_loaded_rows": summary["n_loaded_rows"],
        "n_loaded_rows_raw": summary["n_loaded_rows_raw"],
        "n_selected_rows": summary["n_selected_rows"],
        "n_scored_rows": summary["n_scored_rows"],
        "n_rejected_logit_choice_mismatch": summary["n_rejected_logit_choice_mismatch"],
        "n_train_rows": summary["n_train_rows"],
        "n_test_rows": summary["n_test_rows"],
        "n_unique_scored_prompts": summary["n_unique_scored_prompts"],
        "n_stable_rows": summary["n_stable_rows"],
        "n_drift_rows": summary["n_drift_rows"],
        "source_counts": summary["source_counts"],
        "q_index_counts": summary["q_index_counts"],
        "test_auc_stability_from_dense_margin": summary["test_auc_stability_from_dense_margin"],
        "test_auc_stability_from_dense_margin_ci95": summary[
            "test_auc_stability_from_dense_margin_ci95"
        ],
        "mean_margin_stable": summary["mean_margin_stable"],
        "mean_margin_drift": summary["mean_margin_drift"],
        "safe_filter_threshold": train_safe_filter.get("threshold"),
        "train_safe_filter_precision_stable": train_safe_filter.get("precision_stable"),
        "train_safe_filter_coverage": train_safe_filter.get("coverage"),
        "test_safe_filter_precision_stable": test_safe_filter.get("precision_stable"),
        "test_safe_filter_coverage": test_safe_filter.get("coverage"),
        "pass_class_presence": summary["pass_class_presence"],
        "pass_margin_signal": summary["pass_margin_signal"],
        "pass_safe_filter": summary["pass_safe_filter"],
    }


def _gate_phase_155f_stage_timing(artifact_dir: Path) -> dict[str, Any]:
    summary = _load_json(artifact_dir / "stage_timing_summary.json")
    return {
        "q3_fixed_over_adaptive_speedup": summary["q3_fixed_over_adaptive_speedup"],
        "q3_tail_token_reduction": summary["q3_tail_token_reduction"],
        "adaptive_q3": summary["adaptive"]["q_index"].get("q3"),
        "fixed_k1_q3": summary["fixed_k1"]["q_index"].get("q3"),
        "pass_mechanism": summary["pass_mechanism"],
        "pass_tail_work": summary["pass_tail_work"],
    }


def _gate_phase_155k(artifact_dir: Path) -> dict[str, Any]:
    summary = _load_json(artifact_dir / "temperature_sweep_summary.json")
    return {
        "n_cells": summary["n_cells"],
        "temperatures": summary["temperatures"],
        "pass_sampler_stability": summary["pass_sampler_stability"],
        "strict_exact_match_temperatures": summary["strict_exact_match_temperatures"],
        "cells": summary["cells"],
    }


def _gate_phase_130af(artifact_dir: Path) -> dict[str, Any]:
    summary = _load_json(artifact_dir / "attribution_summary.json")
    return {
        "common_pair_rows": summary["common_pair_rows"],
        "accuracy_delta_gap": summary["accuracy_delta_gap"],
        "any_drift_set_overlap": {
            key: summary["any_drift_set_overlap"][key]
            for key in (
                "left_count",
                "right_count",
                "intersection_count",
                "left_only_count",
                "right_only_count",
                "jaccard",
            )
        },
        "cache_reuse_active_fraction": summary["cache_reuse"]["streaming_summary"][
            "follow_up_vision_pruning_active_fraction"
        ],
        "cache_invalidated_active_fraction": summary["cache_invalidated"]["streaming_summary"][
            "follow_up_vision_pruning_active_fraction"
        ],
        "pass_complete_overlap": summary["pass_complete_overlap"],
        "pass_same_net_delta": summary["pass_same_net_delta"],
        "pass_mechanism_contrast": summary["pass_mechanism_contrast"],
        "pass_row_set_nonidentity": summary["pass_row_set_nonidentity"],
    }


def _commit_message(step: QueueStep, record: dict[str, Any]) -> str:
    gate = record.get("gate", {})
    if step.phase == "1.55F-stage-timing":
        return (
            "research(1.55F): land adaptive stage-timing attribution\n\n"
            "Summarize existing adaptive and fixed-K=1 short-tranche artifacts "
            "to explain where adaptive's speedup comes from. This analysis is "
            "accuracy-neutral and attributes the Q3 gap to the post-Q2 repaired "
            "cache reducing tail prompt work.\n"
            "Gate summary: q3_fixed_over_adaptive_speedup="
            f"{_format_float(gate.get('q3_fixed_over_adaptive_speedup'))}x, "
            f"q3_tail_token_reduction={_format_float(gate.get('q3_tail_token_reduction'))}. "
            f"mechanism={'PASS' if gate.get('pass_mechanism') else 'FAIL'}, "
            f"tail_work={'PASS' if gate.get('pass_tail_work') else 'FAIL'}."
        )
    if step.phase == "1.63E":
        cells = gate.get("cells", [])
        cell_bits = ", ".join(
            f"{cell.get('frame_count')}f: e2e="
            f"{_format_float(cell.get('actual_e2e_speedup'))}x, pred="
            f"{_format_float(cell.get('predicted_e2e_speedup'))}x, "
            f"Δ={_format_float(cell.get('actual_minus_predicted'))}"
            for cell in cells
        )
        return (
            "research(1.63E): land Track B frame-budget scaling\n\n"
            "Record Qwen compact post-layer L=2/kr=0.50 Track B sparse-ViT "
            "execution at 8f, 16f, 20f, and 32f by default. This tests whether the arithmetic "
            "ceiling predicts measured end-to-end wall-clock across frame "
            "budgets while keeping LM prompt geometry dense.\n"
            f"Cells: {cell_bits}. "
            f"headline_pass={gate.get('headline_pass')}, "
            "headline_max_abs_actual_minus_predicted="
            f"{_format_float(gate.get('headline_max_abs_actual_minus_predicted'))}."
        )
    if step.phase == "1.63G":
        return (
            "research(1.63G): land Gemma Track B sparse ViT check\n\n"
            "Record Gemma 4 E4B dense versus compact post-layer L=2/kr=0.50 "
            "vision execution on the VideoMME n=60 Track B manifest. The scope "
            "is vision-tower-only: compact execution is scattered back before "
            "pooler/merger so the LM prompt remains dense.\n"
            f"Gate summary: n={gate.get('n_paired_items')}, "
            f"Δacc={_format_float(gate.get('accuracy_delta'))}, "
            f"vision_reduction={_format_float(gate.get('vision_reduction'))}, "
            "e2e_speedup="
            f"{_format_float(gate.get('actual_e2e_speedup_dense_over_sparse'))}x, "
            "ceiling_pred="
            f"{_format_float(gate.get('predicted_e2e_speedup_from_vision_only'))}x. "
            f"Fidelity={'PASS' if gate.get('pass_fidelity') else 'FAIL'}, "
            f"sparse_vision={'PASS' if gate.get('pass_sparse_vision') else 'FAIL'}, "
            f"e2e_positive={'PASS' if gate.get('pass_e2e_positive') else 'FAIL'}, "
            f"ceiling={'PASS' if gate.get('pass_ceiling_explained') else 'FAIL'}."
        )
    if step.phase == "1.55K":
        cell_bits = ", ".join(
            f"T={cell.get('temperature')}: diffs="
            f"{cell.get('paired_correctness_diffs')}/{cell.get('paired_choice_diffs')}, "
            f"speed={_format_float(cell.get('speedup_all_query_median_cold_over_session_follow_up'))}x"
            for cell in gate.get("cells", [])
        )
        return (
            "research(1.55K): land adaptive sampler-temperature sweep\n\n"
            "Run the adaptive Q2=K1/Q3=K0 post-Q2-state policy on the short "
            "tranche across non-greedy sampling temperatures. Session and "
            "baseline arms use identical sampler settings, so paired diffs "
            "measure cache-policy sensitivity rather than sampler mismatch.\n"
            f"Cells: {cell_bits}. "
            f"sampler_stability={'PASS' if gate.get('pass_sampler_stability') else 'FAIL'}, "
            f"strict_exact_match_temperatures={gate.get('strict_exact_match_temperatures')}."
        )
    if step.phase == "1.30AF":
        overlap = gate.get("any_drift_set_overlap", {})
        return (
            "research(1.30AF): land cache-boundary attribution\n\n"
            "Compare 1.30AD cache-reuse and 1.30AC cache-invalidated follow-up "
            "artifacts to determine whether their equal aggregate accuracy "
            "drop is row-identical or a boundary aggregate reached through "
            "different row-level flips. This is a post-hoc attribution, not a "
            "direct KV tensor-distance probe.\n"
            f"Gate summary: common_rows={gate.get('common_pair_rows')}, "
            f"delta_gap={_format_float(gate.get('accuracy_delta_gap'))}, "
            f"drift_jaccard={_format_float(overlap.get('jaccard'))}, "
            f"reuse_active={_format_float(gate.get('cache_reuse_active_fraction'))}, "
            f"invalidated_active={_format_float(gate.get('cache_invalidated_active_fraction'))}. "
            f"same_net={'PASS' if gate.get('pass_same_net_delta') else 'FAIL'}, "
            f"mechanism_contrast={'PASS' if gate.get('pass_mechanism_contrast') else 'FAIL'}, "
            f"row_nonidentity={'PASS' if gate.get('pass_row_set_nonidentity') else 'FAIL'}."
        )
    return (
        "research(1.65): land logit-margin stability predictor scout\n\n"
        "Record dense Qwen answer-letter logprob margins over a deterministic "
        "1.30 cache-boundary paired artifacts with a grouped train/test split. "
        "This is an oracle-feature predictor scout, not a deployed guard, and "
        "tests whether 1.30 drift concentrates on intrinsically uncertain items.\n"
        f"Gate summary: n_scored={gate.get('n_scored_rows')}, "
        f"rejected={gate.get('n_rejected_logit_choice_mismatch')}, "
        f"test_n={gate.get('n_test_rows')}, drift={gate.get('n_drift_rows')}, "
        f"stable={gate.get('n_stable_rows')}, "
        f"test_AUC={_format_float(gate.get('test_auc_stability_from_dense_margin'))}, "
        f"test_CI={gate.get('test_auc_stability_from_dense_margin_ci95')}, "
        "test_safe_filter_precision="
        f"{_format_float(gate.get('test_safe_filter_precision_stable'))}, "
        f"coverage={_format_float(gate.get('test_safe_filter_coverage'))}. "
        f"Class_presence={'PASS' if gate.get('pass_class_presence') else 'FAIL'}, "
        f"Margin_signal={'PASS' if gate.get('pass_margin_signal') else 'FAIL'}, "
        f"safe_filter={'PASS' if gate.get('pass_safe_filter') else 'FAIL'}."
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
        _check_queue_worktree()

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
        elif step.phase == "1.55F-stage-timing":
            record["gate"] = _gate_phase_155f_stage_timing(step.artifact_dir)
        elif step.phase == "1.63E":
            record["gate"] = _gate_phase_163e(step.artifact_dir)
        elif step.phase == "1.63G":
            record["gate"] = _gate_phase_163g(step.artifact_dir)
        elif step.phase == "1.55K":
            record["gate"] = _gate_phase_155k(step.artifact_dir)
        elif step.phase == "1.30AF":
            record["gate"] = _gate_phase_130af(step.artifact_dir)
        else:
            record["gate"] = _gate_phase_165(step.artifact_dir)

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

    print(f"[paper-deep-mechanism] wrote {args.queue_status_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
