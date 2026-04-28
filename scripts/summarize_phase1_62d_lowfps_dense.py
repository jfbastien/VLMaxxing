#!/usr/bin/env python3
"""Summarize Phase 1.62D low-FPS dense baseline cells."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast


def _load(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cell", action="append", nargs=2, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    cells: list[dict[str, Any]] = []
    for frame_count, path in args.cell:
        payload = _load(Path(path))
        cells.append(
            {
                "frame_count": int(frame_count),
                "summary_path": str(path),
                "n_paired_queries": payload["n_paired_queries"],
                "n_paired_sessions": payload["n_paired_sessions"],
                "pass_complete_pairing": payload["pass_complete_pairing"],
                "pass_format": payload["pass_format"],
                "outcome": payload["outcome"],
                "accuracy_delta_candidate_minus_reference": payload["all"][
                    "accuracy_delta_candidate_minus_reference"
                ],
                "accuracy_delta_candidate_minus_reference_ci95": payload["all"][
                    "accuracy_delta_candidate_minus_reference_ci95"
                ],
                "speedup_reference_over_candidate": payload["all"][
                    "speedup_reference_over_candidate"
                ],
            }
        )
    cells.sort(key=lambda cell: int(cell["frame_count"]), reverse=True)
    by_frame = {str(cell["frame_count"]): cell for cell in cells}
    payload = {
        "phase": "1.62D",
        "n_cells": len(cells),
        "cells": cells,
        "pass_complete_pairing": all(cell["pass_complete_pairing"] for cell in cells),
        "pass_format": all(cell["pass_format"] for cell in cells),
        "four_f_outcome": by_frame.get("4", {}).get("outcome"),
        "two_f_outcome": by_frame.get("2", {}).get("outcome"),
        "headline_status": (
            "low_fps_competitive"
            if by_frame.get("4", {}).get("outcome") == "low_fps_competitive"
            else "low_fps_rejected_or_ambiguous"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"[1.62D] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
