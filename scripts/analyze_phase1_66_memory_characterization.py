#!/usr/bin/env python3
"""Summarize memory envelope across landed paper-closeout artifacts.

This is analysis-only reviewer defense. It does not create a new model-quality
claim; it makes the local 16 GB laptop memory envelope explicit across the
1.30, 1.55, and Track B lanes.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, cast

ARTIFACT_ROOT = Path("research/experiments/2026/artifacts")
DEFAULT_SOURCE_DIRS = [
    ARTIFACT_ROOT / "phase1_30W_q0_dense_followup_pruned_full",
    ARTIFACT_ROOT / "phase1_30AC_cache_invalidated_followups",
    ARTIFACT_ROOT / "phase1_30AD_instrumented_w_rerun",
    ARTIFACT_ROOT / "phase1_55D_selective_reprefill_v2",
    ARTIFACT_ROOT / "phase1_55F_q3_post_q2_state",
    ARTIFACT_ROOT / "phase1_55F_medium_adaptive_replication",
    ARTIFACT_ROOT / "phase1_55F_long_adaptive_replication",
    ARTIFACT_ROOT / "phase1_55F_32f_short_adaptive_replication",
    ARTIFACT_ROOT / "phase1_55F_16f_short_adaptive",
    ARTIFACT_ROOT / "phase1_55G_k1_medium_replication",
    ARTIFACT_ROOT / "phase1_55H_k1_32f_short_probe",
    ARTIFACT_ROOT / "phase1_55I_k1_long_replication",
    ARTIFACT_ROOT / "phase1_55J_k1_sampler_variation",
    ARTIFACT_ROOT / "phase1_55K_adaptive_temperature_sweep",
    ARTIFACT_ROOT / "phase1_63_track_b_sparse_vit",
    ARTIFACT_ROOT / "phase1_63E_track_b_frame_scaling",
    ARTIFACT_ROOT / "phase1_63G_gemma_track_b",
]
REQUIRED_FAMILIES = ("C-VISION/1.30", "C-PERSIST/1.55", "Track-B/1.63")


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None
    return cast(dict[str, Any], payload) if isinstance(payload, dict) else None


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                payload = json.loads(stripped)
                if isinstance(payload, dict):
                    rows.append(cast(dict[str, Any], payload))
    return rows


def _phase_family(path: Path) -> str:
    text = path.as_posix()
    if "phase1_30" in text:
        return "C-VISION/1.30"
    if "phase1_55" in text:
        return "C-PERSIST/1.55"
    if "phase1_63" in text:
        return "Track-B/1.63"
    return "other"


def _phase_id(path: Path) -> str:
    for part in path.parts:
        if part.startswith("phase1_"):
            return part
    return path.parent.name


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _frame_count(payload: dict[str, Any], path: Path) -> int | None:
    for key in ("frame_count", "n_frames"):
        value = payload.get(key)
        if value is not None:
            return int(value)
    stem = path.stem
    for token in stem.replace("_", " ").split():
        if token.endswith("f") and token[:-1].isdigit():
            return int(token[:-1])
    return None


def _record_from_json(path: Path, payload: dict[str, Any]) -> dict[str, Any] | None:
    peak_rss_gb = _float_or_none(payload.get("peak_rss_gb"))
    final_rss_mb = _float_or_none(payload.get("final_rss_mb"))
    final_rss_gb = final_rss_mb / 1024 if final_rss_mb is not None else None
    mean_peak_memory_gb = _float_or_none(payload.get("mean_peak_memory_gb"))
    if peak_rss_gb is None and final_rss_gb is None and mean_peak_memory_gb is None:
        return None
    peak_observed = max(
        value for value in (peak_rss_gb, final_rss_gb, mean_peak_memory_gb) if value is not None
    )
    return {
        "source_path": path.as_posix(),
        "source_type": "json",
        "phase_id": _phase_id(path),
        "phase_family": _phase_family(path),
        "model": payload.get("model") or payload.get("model_path"),
        "frame_count": _frame_count(payload, path),
        "n_rows": payload.get("n_queries_per_mode") or payload.get("n_items"),
        "peak_rss_gb": peak_rss_gb,
        "final_rss_gb": final_rss_gb,
        "max_peak_memory_gb": None,
        "mean_peak_memory_gb": mean_peak_memory_gb,
        "peak_observed_gb": peak_observed,
    }


def _record_from_jsonl(path: Path, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    peak_values = [
        float(row["peak_memory_gb"]) for row in rows if _float_or_none(row.get("peak_memory_gb"))
    ]
    if not peak_values:
        return None
    frame_counts = {
        int(value)
        for row in rows
        for value in (row.get("frame_count"), row.get("n_frames"))
        if value is not None
    }
    models = sorted(
        {
            str(row.get("model") or row.get("model_path"))
            for row in rows
            if row.get("model") or row.get("model_path")
        }
    )
    return {
        "source_path": path.as_posix(),
        "source_type": "jsonl",
        "phase_id": _phase_id(path),
        "phase_family": _phase_family(path),
        "model": models[0] if len(models) == 1 else None,
        "frame_count": sorted(frame_counts)[0] if len(frame_counts) == 1 else None,
        "n_rows": len(rows),
        "peak_rss_gb": None,
        "final_rss_gb": None,
        "max_peak_memory_gb": max(peak_values),
        "mean_peak_memory_gb": sum(peak_values) / len(peak_values),
        "peak_observed_gb": max(peak_values),
    }


def _collect(source_dirs: list[Path]) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    for source_dir in source_dirs:
        if not source_dir.exists():
            continue
        for path in sorted(source_dir.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix == ".json":
                payload = _load_json(path)
                if payload is None:
                    continue
                record = _record_from_json(path, payload)
            elif path.suffix == ".jsonl":
                record = _record_from_jsonl(path, _load_jsonl(path))
            else:
                continue
            if record is not None:
                record["over_9gb"] = bool(float(record["peak_observed_gb"]) > 9.0)
                record["over_10gb"] = bool(float(record["peak_observed_gb"]) > 10.0)
                cells.append(record)
    cells.sort(key=lambda row: (str(row["phase_family"]), str(row["phase_id"]), row["source_path"]))
    return cells


def _by_family(cells: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for cell in cells:
        grouped.setdefault(str(cell["phase_family"]), []).append(cell)
    return {
        family: {
            "n_cells": len(rows),
            "max_peak_observed_gb": max(float(row["peak_observed_gb"]) for row in rows),
            "n_cells_over_9gb": sum(bool(row["over_9gb"]) for row in rows),
            "n_cells_over_10gb": sum(bool(row["over_10gb"]) for row in rows),
        }
        for family, rows in sorted(grouped.items())
    }


def _write_csv(path: Path, cells: list[dict[str, Any]]) -> None:
    fields = [
        "phase_family",
        "phase_id",
        "source_type",
        "frame_count",
        "model",
        "n_rows",
        "peak_rss_gb",
        "final_rss_gb",
        "max_peak_memory_gb",
        "mean_peak_memory_gb",
        "peak_observed_gb",
        "over_9gb",
        "over_10gb",
        "source_path",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for cell in cells:
            writer.writerow({field: cell.get(field) for field in fields})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, action="append", default=[])
    parser.add_argument(
        "--output",
        type=Path,
        default=ARTIFACT_ROOT
        / "phase1_66_memory_characterization"
        / "memory_characterization_summary.json",
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=ARTIFACT_ROOT / "phase1_66_memory_characterization" / "memory_cells.csv",
    )
    args = parser.parse_args()

    source_dirs = args.source_dir or DEFAULT_SOURCE_DIRS
    cells = _collect(source_dirs)
    families_present = sorted({str(cell["phase_family"]) for cell in cells})
    missing_required_families = [
        family for family in REQUIRED_FAMILIES if family not in families_present
    ]
    max_peak = max((float(cell["peak_observed_gb"]) for cell in cells), default=None)
    payload = {
        "phase": "1.66",
        "scope_note": (
            "Analysis-only memory envelope over landed artifacts. peak_observed_gb "
            "uses the largest available per-file memory signal: peak_rss_gb, "
            "final_rss_mb converted to GiB, or max/mean peak_memory_gb from JSONL rows."
        ),
        "source_dirs": [path.as_posix() for path in source_dirs if path.exists()],
        "missing_source_dirs": [path.as_posix() for path in source_dirs if not path.exists()],
        "required_families": list(REQUIRED_FAMILIES),
        "families_present": families_present,
        "missing_required_families": missing_required_families,
        "n_cells": len(cells),
        "max_observed_peak_gb": max_peak,
        "n_cells_over_9gb": sum(bool(cell["over_9gb"]) for cell in cells),
        "n_cells_over_10gb": sum(bool(cell["over_10gb"]) for cell in cells),
        "by_family": _by_family(cells),
        "high_watermark_cells": sorted(
            cells,
            key=lambda cell: float(cell["peak_observed_gb"]),
            reverse=True,
        )[:10],
        "cells": cells,
        "csv_output": args.csv_output.as_posix(),
        "pass_memory_characterized": (
            len(cells) >= 8 and max_peak is not None and not missing_required_families
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    _write_csv(args.csv_output, cells)
    print(f"[1.66] wrote {args.output}")
    print(f"[1.66] wrote {args.csv_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
