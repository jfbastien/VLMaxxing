#!/usr/bin/env python3
"""Run the M3 Gemma cost-accounting follow-up queue.

This queue is intentionally narrow. It adds operating points to the
2026-05-19/20 Gemma stage-cost table without reopening query-aware routing.
The default ``core`` tier runs only the cleanest immediate M3 follow-up:
VideoMME-short admission keep-rate bracketing. The explicit ``extended`` tier
adds broader MVBench-hosted and composition checks:

* VideoMME-short admission keep-rate bracket at kr=0.3 and kr=0.7, holding
  random-valid C-VISION fixed at kr=0.5.
* Extended tier: MVBench hosted-dev admission bracket at the same kr values.
* Extended tier: TOMATO motion-dev and VideoMME-short RLT composition checks,
  using RLT for both placeholder admission and C-VISION.
* A cost-model refit that combines the existing N=11 rows with the new rows.

The queue runs no learned router, no active repair, and no query-text policy.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "rlt_m3_cost_accounting_followup_queue_v1"
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ARTIFACT_DIR = Path("research/experiments/2026/artifacts/rlt_m3_cost_accounting_followup")
DEFAULT_MODEL_PATH = Path.home() / "models" / "gemma-4-e4b-it-4bit"
DEFAULT_MVBENCH_HOSTED_MANIFEST = Path("research/benchmark_manifests/mvbench_hosted_dev_v1.toml")
DEFAULT_TOMATO_MANIFEST = Path("research/benchmark_manifests/tomato_motion_dev_v2.toml")
DEFAULT_VIDEOMME_SHORT_MANIFEST = Path(
    "research/benchmark_manifests/videomme_short_dev_holdout_v1_n20.toml"
)

BASE_COST_MODEL_ROWS: tuple[tuple[str, Path], ...] = (
    (
        "mvbench_dev_admon",
        Path(
            "research/experiments/2026/artifacts/rlt_query_routing_active_repair_targeted/"
            "query_q1b_mvbench_random_seed11_admission_on_cost_model.json"
        ),
    ),
    (
        "mvbench_holdout",
        Path(
            "research/experiments/2026/artifacts/rlt_followup_queue/full_composition_rlt_holdout_mvbench_cost_model.json"
        ),
    ),
    (
        "videomme_holdout_long",
        Path(
            "research/experiments/2026/artifacts/rlt_followup_queue/full_composition_rlt_holdout_videomme_cost_model.json"
        ),
    ),
    (
        "tomato_holdout",
        Path(
            "research/experiments/2026/artifacts/rlt_followup_queue/full_composition_rlt_holdout_tomato_cost_model.json"
        ),
    ),
    (
        "mvbench_mvattr_kr100",
        Path(
            "research/experiments/2026/artifacts/rlt_followup_queue/"
            "full_composition_rlt_mvbench_moving_attribute_kr100_cost_model.json"
        ),
    ),
    (
        "mvbench_hosted_RND",
        Path(
            "research/experiments/2026/artifacts/rlt_query_routing_cost_accounting/"
            "mvbench_hosted_dev/query_q1b_random_admission_on_cost_model.json"
        ),
    ),
    (
        "mvbench_hosted_FIX",
        Path(
            "research/experiments/2026/artifacts/rlt_query_routing_cost_accounting/"
            "mvbench_hosted_dev/query_q1b_fixed_admission_on_cost_model.json"
        ),
    ),
    (
        "tomato_dev_RND",
        Path(
            "research/experiments/2026/artifacts/rlt_query_routing_cost_accounting/"
            "tomato_motion_dev/query_q1b_random_admission_on_cost_model.json"
        ),
    ),
    (
        "tomato_dev_FIX",
        Path(
            "research/experiments/2026/artifacts/rlt_query_routing_cost_accounting/"
            "tomato_motion_dev/query_q1b_fixed_admission_on_cost_model.json"
        ),
    ),
    (
        "videomme_short_RND",
        Path(
            "research/experiments/2026/artifacts/rlt_query_routing_cost_accounting/"
            "videomme_short/query_q1b_random_admission_on_cost_model.json"
        ),
    ),
    (
        "videomme_short_FIX",
        Path(
            "research/experiments/2026/artifacts/rlt_query_routing_cost_accounting/"
            "videomme_short/query_q1b_fixed_admission_on_cost_model.json"
        ),
    ),
)


@dataclass(frozen=True)
class Cell:
    label: str
    benchmark: str
    manifest: Path
    expected_items: int
    keep_rate: float
    prune_placeholders: str
    vision_tower_keep_rate: float
    vision_tower_score_mode: str
    vision_random_seed: int | None = None


@dataclass(frozen=True)
class Step:
    phase: str
    command: list[str]


def _portable_arg(arg: str) -> str:
    path = Path(arg)
    if not path.is_absolute():
        return arg
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        pass
    home = Path.home()
    try:
        return f"$HOME/{path.relative_to(home).as_posix()}"
    except ValueError:
        return arg


def _portable_command(command: list[str]) -> list[str]:
    return [_portable_arg(arg) for arg in command]


def _manifest_item_count(path: Path) -> int:
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    item_ids = payload.get("item_ids")
    if isinstance(item_ids, list):
        if not all(isinstance(item_id, str) for item_id in item_ids):
            raise ValueError(f"{path} contains non-string item_ids")
        return len(item_ids)
    items = payload.get("items")
    if isinstance(items, list):
        return len(items)
    raise ValueError(f"{path} is missing item_ids/items")


def _expected_items(path: Path, *, n_items: int) -> int:
    count = _manifest_item_count(path)
    if count <= 0:
        raise ValueError(f"{path} has no benchmark items")
    return min(count, n_items) if n_items > 0 else count


def _rate_tag(rate: float) -> str:
    return f"kr{int(round(rate * 100)):03d}"


def _run(command: list[str]) -> dict[str, Any]:
    started = time.perf_counter()
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    payload = {
        "command": _portable_command(command),
        "returncode": completed.returncode,
        "elapsed_seconds": time.perf_counter() - started,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }
    if completed.returncode != 0:
        raise RuntimeError(json.dumps(payload, indent=2))
    return payload


def _gemma_command(
    *,
    manifest: Path,
    frame_count: int,
    model_path: Path,
    prefill_step_size: int,
    mlx_memory_limit_gb: float,
    rss_guard_mb: int,
    n_items: int,
    keep_rate: float,
    prune_placeholders: str,
    vision_tower_keep_rate: float,
    vision_tower_score_mode: str,
    output: Path,
    summary: Path,
    vision_random_seed: int | None = None,
) -> list[str]:
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
        f"{keep_rate:.6g}",
        "--prune-placeholders",
        prune_placeholders,
        "--prefill-step-size",
        str(prefill_step_size),
        "--model-path",
        str(model_path),
        "--rss-guard-mb",
        str(rss_guard_mb),
        "--mlx-memory-limit-gb",
        f"{mlx_memory_limit_gb:.6g}",
        "--n-warmup",
        "1",
        "--arm-order",
        "abba",
        "--resume",
        "--vision-tower-keep-rate",
        f"{vision_tower_keep_rate:.6g}",
        "--vision-tower-score-mode",
        vision_tower_score_mode,
        "--output",
        str(output),
        "--summary",
        str(summary),
    ]
    if vision_random_seed is not None:
        command.extend(["--vision-random-seed", str(vision_random_seed)])
    if n_items > 0:
        command.extend(["--n-items", str(n_items)])
    return command


def _analyze_command(
    *,
    dense_jsonl: Path,
    composed_jsonl: Path,
    analysis: Path,
    paired: Path,
    expected_items: int,
    bucket_min_n: int,
    n_bootstrap: int,
) -> list[str]:
    return [
        sys.executable,
        "scripts/analyze_gemma_full_composition.py",
        "--dense-jsonl",
        str(dense_jsonl),
        "--composed-jsonl",
        str(composed_jsonl),
        "--dense-source",
        "composed-jsonl-same-run",
        "--output",
        str(analysis),
        "--paired-items",
        str(paired),
        "--expected-items",
        str(expected_items),
        "--bucket-min-n",
        str(bucket_min_n),
        "--n-bootstrap",
        str(n_bootstrap),
    ]


def _cost_command(
    *,
    paired: Path,
    output: Path,
    label: str,
    n_bootstrap: int,
) -> list[str]:
    return [
        sys.executable,
        "scripts/analyze_gemma_paired_cost_model.py",
        "--paired-items",
        str(paired),
        "--output",
        str(output),
        "--label",
        label,
        "--n-bootstrap",
        str(n_bootstrap),
    ]


def _fit_command(*, cost_rows: list[tuple[str, Path]], output: Path) -> list[str]:
    command = [sys.executable, "scripts/fit_gemma_cost_model.py"]
    for label, path in cost_rows:
        command.extend(["--cost-model-json", f"{label}={path}"])
    command.extend(["--output", str(output)])
    return command


def _cell_paths(artifact_dir: Path, cell: Cell) -> dict[str, Path]:
    base = artifact_dir / cell.benchmark
    return {
        "jsonl": base / f"{cell.label}.jsonl",
        "summary": base / f"{cell.label}_summary.json",
        "analysis": base / f"{cell.label}_analysis.json",
        "paired": base / f"{cell.label}_paired.jsonl",
        "cost": base / f"{cell.label}_cost_model.json",
    }


def _build_steps(args: argparse.Namespace) -> tuple[list[Step], list[tuple[str, Path]]]:
    mvbench_expected = _expected_items(args.mvbench_hosted_manifest, n_items=args.n_items)
    tomato_expected = _expected_items(args.tomato_manifest, n_items=args.n_items)
    videomme_expected = _expected_items(args.videomme_short_manifest, n_items=args.n_items)
    bucket_min_n = 1 if args.n_items else args.bucket_min_n
    analysis_bootstrap = args.smoke_bootstrap if args.n_items else args.n_bootstrap
    cost_bootstrap = args.smoke_bootstrap if args.n_items else args.cost_bootstrap

    dense_cells = {
        "videomme_short": Cell(
            label="dense_reference",
            benchmark="videomme_short",
            manifest=args.videomme_short_manifest,
            expected_items=videomme_expected,
            keep_rate=1.0,
            prune_placeholders="none",
            vision_tower_keep_rate=1.0,
            vision_tower_score_mode="random_valid",
        )
    }

    candidate_cells: list[Cell] = [
        Cell(
            label="videomme_short_random_cvision_no_admission",
            benchmark="videomme_short",
            manifest=args.videomme_short_manifest,
            expected_items=videomme_expected,
            keep_rate=1.0,
            prune_placeholders="none",
            vision_tower_keep_rate=0.5,
            vision_tower_score_mode="random_valid",
            vision_random_seed=11,
        ),
        *[
            Cell(
                label=f"videomme_short_random_cvision_admission_{_rate_tag(rate)}",
                benchmark="videomme_short",
                manifest=args.videomme_short_manifest,
                expected_items=videomme_expected,
                keep_rate=rate,
                prune_placeholders="rlt",
                vision_tower_keep_rate=0.5,
                vision_tower_score_mode="random_valid",
                vision_random_seed=11,
            )
            for rate in (0.3, 0.7)
        ],
    ]
    if args.tier == "extended":
        dense_cells["mvbench_hosted"] = Cell(
            label="dense_reference",
            benchmark="mvbench_hosted",
            manifest=args.mvbench_hosted_manifest,
            expected_items=mvbench_expected,
            keep_rate=1.0,
            prune_placeholders="none",
            vision_tower_keep_rate=1.0,
            vision_tower_score_mode="random_valid",
        )
        dense_cells["tomato_motion_dev"] = Cell(
            label="dense_reference",
            benchmark="tomato_motion_dev",
            manifest=args.tomato_manifest,
            expected_items=tomato_expected,
            keep_rate=1.0,
            prune_placeholders="none",
            vision_tower_keep_rate=1.0,
            vision_tower_score_mode="random_valid",
        )
        candidate_cells.extend(
            [
                Cell(
                    label="mvbench_hosted_random_cvision_no_admission",
                    benchmark="mvbench_hosted",
                    manifest=args.mvbench_hosted_manifest,
                    expected_items=mvbench_expected,
                    keep_rate=1.0,
                    prune_placeholders="none",
                    vision_tower_keep_rate=0.5,
                    vision_tower_score_mode="random_valid",
                    vision_random_seed=11,
                ),
                *[
                    Cell(
                        label=f"mvbench_hosted_random_cvision_admission_{_rate_tag(rate)}",
                        benchmark="mvbench_hosted",
                        manifest=args.mvbench_hosted_manifest,
                        expected_items=mvbench_expected,
                        keep_rate=rate,
                        prune_placeholders="rlt",
                        vision_tower_keep_rate=0.5,
                        vision_tower_score_mode="random_valid",
                        vision_random_seed=11,
                    )
                    for rate in (0.3, 0.7)
                ],
                Cell(
                    label="tomato_motion_dev_rlt_composition_kr050",
                    benchmark="tomato_motion_dev",
                    manifest=args.tomato_manifest,
                    expected_items=tomato_expected,
                    keep_rate=0.5,
                    prune_placeholders="rlt",
                    vision_tower_keep_rate=0.5,
                    vision_tower_score_mode="rlt_topk",
                ),
                Cell(
                    label="videomme_short_rlt_composition_kr050",
                    benchmark="videomme_short",
                    manifest=args.videomme_short_manifest,
                    expected_items=videomme_expected,
                    keep_rate=0.5,
                    prune_placeholders="rlt",
                    vision_tower_keep_rate=0.5,
                    vision_tower_score_mode="rlt_topk",
                ),
            ]
        )

    steps: list[Step] = []
    for dense in dense_cells.values():
        paths = _cell_paths(args.artifact_dir, dense)
        steps.append(
            Step(
                phase=f"{dense.benchmark}_dense_reference",
                command=_gemma_command(
                    manifest=dense.manifest,
                    frame_count=args.frame_count,
                    model_path=args.gemma_model_path,
                    prefill_step_size=args.prefill_step_size,
                    mlx_memory_limit_gb=args.mlx_memory_limit_gb,
                    rss_guard_mb=args.rss_guard_mb,
                    n_items=args.n_items,
                    keep_rate=dense.keep_rate,
                    prune_placeholders=dense.prune_placeholders,
                    vision_tower_keep_rate=dense.vision_tower_keep_rate,
                    vision_tower_score_mode=dense.vision_tower_score_mode,
                    output=paths["jsonl"],
                    summary=paths["summary"],
                ),
            )
        )

    new_cost_rows: list[tuple[str, Path]] = []
    for cell in candidate_cells:
        dense_paths = _cell_paths(args.artifact_dir, dense_cells[cell.benchmark])
        paths = _cell_paths(args.artifact_dir, cell)
        steps.append(
            Step(
                phase=f"{cell.label}_run",
                command=_gemma_command(
                    manifest=cell.manifest,
                    frame_count=args.frame_count,
                    model_path=args.gemma_model_path,
                    prefill_step_size=args.prefill_step_size,
                    mlx_memory_limit_gb=args.mlx_memory_limit_gb,
                    rss_guard_mb=args.rss_guard_mb,
                    n_items=args.n_items,
                    keep_rate=cell.keep_rate,
                    prune_placeholders=cell.prune_placeholders,
                    vision_tower_keep_rate=cell.vision_tower_keep_rate,
                    vision_tower_score_mode=cell.vision_tower_score_mode,
                    vision_random_seed=cell.vision_random_seed,
                    output=paths["jsonl"],
                    summary=paths["summary"],
                ),
            )
        )
        steps.append(
            Step(
                phase=f"{cell.label}_analyze",
                command=_analyze_command(
                    dense_jsonl=dense_paths["jsonl"],
                    composed_jsonl=paths["jsonl"],
                    analysis=paths["analysis"],
                    paired=paths["paired"],
                    expected_items=cell.expected_items,
                    bucket_min_n=bucket_min_n,
                    n_bootstrap=analysis_bootstrap,
                ),
            )
        )
        steps.append(
            Step(
                phase=f"{cell.label}_cost_model",
                command=_cost_command(
                    paired=paths["paired"],
                    output=paths["cost"],
                    label=cell.label,
                    n_bootstrap=cost_bootstrap,
                ),
            )
        )
        new_cost_rows.append((cell.label, paths["cost"]))

    cost_rows = list(BASE_COST_MODEL_ROWS) + new_cost_rows
    steps.append(
        Step(
            phase=f"fit_cost_model_n{len(cost_rows)}",
            command=_fit_command(
                cost_rows=cost_rows,
                output=args.artifact_dir / f"cost_model_fit_n{len(cost_rows)}.json",
            ),
        )
    )
    return steps, cost_rows


def _write_summary(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--gemma-model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument(
        "--mvbench-hosted-manifest", type=Path, default=DEFAULT_MVBENCH_HOSTED_MANIFEST
    )
    parser.add_argument("--tomato-manifest", type=Path, default=DEFAULT_TOMATO_MANIFEST)
    parser.add_argument(
        "--videomme-short-manifest", type=Path, default=DEFAULT_VIDEOMME_SHORT_MANIFEST
    )
    parser.add_argument(
        "--tier",
        choices=("core", "extended"),
        default="core",
        help=(
            "core = VideoMME-short kr bracket only; extended adds MVBench "
            "bracket and composition cells."
        ),
    )
    parser.add_argument("--frame-count", type=int, default=8)
    parser.add_argument("--prefill-step-size", type=int, default=1024)
    parser.add_argument("--mlx-memory-limit-gb", type=float, default=12.0)
    parser.add_argument("--rss-guard-mb", type=int, default=9000)
    parser.add_argument("--n-items", type=int, default=0, help="Smoke cap; 0 means full manifests.")
    parser.add_argument("--bucket-min-n", type=int, default=3)
    parser.add_argument("--n-bootstrap", type=int, default=500)
    parser.add_argument("--cost-bootstrap", type=int, default=2000)
    parser.add_argument("--smoke-bootstrap", type=int, default=25)
    parser.add_argument("--max-planned-hours", type=float, default=4.5)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    if args.n_items < 0:
        raise SystemExit("--n-items must be non-negative")
    if args.prefill_step_size <= 0:
        raise SystemExit("--prefill-step-size must be positive")
    if args.bucket_min_n <= 0:
        raise SystemExit("--bucket-min-n must be positive")
    if args.n_bootstrap < 0 or args.cost_bootstrap < 0 or args.smoke_bootstrap < 0:
        raise SystemExit("bootstrap counts must be non-negative")
    if args.max_planned_hours <= 0:
        raise SystemExit("--max-planned-hours must be positive")

    steps, cost_rows = _build_steps(args)
    planned_hours = 0.75 if args.n_items else (1.3 if args.tier == "core" else 4.0)
    if planned_hours > args.max_planned_hours:
        raise SystemExit(
            f"planned budget {planned_hours:.2f}h exceeds --max-planned-hours "
            f"{args.max_planned_hours:.2f}h"
        )
    summary_path = args.summary or args.artifact_dir / "queue_summary.json"
    summary: dict[str, Any] = {
        "schema": SCHEMA_VERSION,
        "dry_run": args.dry_run,
        "tier": args.tier,
        "artifact_dir": str(args.artifact_dir),
        "planned_count": len(steps),
        "planned_hours": planned_hours,
        "cost_model_rows": [{"label": label, "path": str(path)} for label, path in cost_rows],
        "hypotheses": {
            "mvbench_keep_rate_bracket": (
                "Extended tier only: lower admission keep-rate should buy speed at quality "
                "cost; higher keep-rate should preserve quality at lower speed, with E2E "
                "predicted by stage shares."
            ),
            "videomme_short_keep_rate_bracket": (
                "On the cleanest current row, lower admission keep-rate should buy speed "
                "at quality cost; higher keep-rate should preserve quality at lower speed, "
                "with E2E predicted by stage shares."
            ),
            "composition_checks": (
                "RLT composition on TOMATO and VideoMME-short should either follow the "
                "prefill+vision cost ceiling or expose a quality/tail-cost residual."
            ),
        },
        "falsification": {
            "cost_model": (
                "Any new cell with absolute relative E2E error > 0.08 "
                "weakens the current predictive claim."
            ),
            "quality": (
                "Any cell with bucket-quality failure or |accuracy_delta| above one item "
                "is timing evidence only, not a fidelity win."
            ),
        },
        "planned": [
            {"phase": step.phase, "command": _portable_command(step.command)} for step in steps
        ],
        "commands": [],
    }

    if args.dry_run:
        if args.summary is not None:
            _write_summary(summary_path, summary)
        print(
            json.dumps(
                {
                    "summary": (str(summary_path) if args.summary is not None else None),
                    "dry_run": True,
                    "planned_count": len(steps),
                },
                sort_keys=True,
            )
        )
        return 0

    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    _write_summary(summary_path, summary)
    commands: list[dict[str, Any]] = []
    for step in steps:
        result = _run(step.command)
        commands.append({"phase": step.phase, **result})
        summary["commands"] = commands
        _write_summary(summary_path, summary)
    summary["completed"] = True
    _write_summary(summary_path, summary)
    print(json.dumps({"summary": str(summary_path), "completed": True}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
