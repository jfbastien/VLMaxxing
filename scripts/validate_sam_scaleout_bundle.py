#!/usr/bin/env python3
"""Validate a Sam scale-out result bundle.

This wrapper runs the row-level validator with the phase-specific gates from
the Sam handoff. It is intentionally file-name based so Sam can hand us one
artifact directory and one validation summary.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[1]
ROW_VALIDATOR: Final = ROOT / "scripts/validate_sam_scaleout_artifact.py"


@dataclass(frozen=True)
class BundleCheck:
    filename: str
    required_for_minimum: bool
    args: tuple[str, ...]


CHECKS: Final[tuple[BundleCheck, ...]] = (
    BundleCheck(
        filename="sam_b0b_cache_correctness.jsonl",
        required_for_minimum=True,
        args=(
            "--phase",
            "B0b",
            "--min-rows",
            "42",
            "--require-zero-choice-diffs",
            "--require-zero-correctness-diffs",
            "--require-zero-text-diffs",
            "--require-zero-parse-failures",
            "--require-matching-input-hash",
            "--require-matching-prompt-hash",
            "--require-matching-frame-hashes",
            "--require-positive-prefix-on-followups",
            "--require-b0b-protocol",
        ),
    ),
    BundleCheck(
        filename="sam_b1_cpersist_replication.jsonl",
        required_for_minimum=False,
        args=(
            "--phase",
            "B1",
            "--min-rows",
            "21",
            "--require-zero-parse-failures",
        ),
    ),
    BundleCheck(
        filename="sam_b2_many_turn_horizon.jsonl",
        required_for_minimum=False,
        args=(
            "--phase",
            "B2",
            "--min-rows",
            "1",
            "--require-zero-parse-failures",
        ),
    ),
    BundleCheck(
        filename="sam_b3_streaming_baselines.jsonl",
        required_for_minimum=True,
        args=(
            "--phase",
            "B3",
            "--min-rows",
            "80",
            "--min-pair-keys",
            "20",
            "--min-videos",
            "2",
            "--require-arms",
            "screenshot_polling,low_fps_dense,recency_last_k,sam_policy",
            "--require-zero-parse-failures",
            "--require-b3-matched-events",
        ),
    ),
    BundleCheck(
        filename="sam_b4_sparse_vit_ceiling.jsonl",
        required_for_minimum=False,
        args=(
            "--phase",
            "B4",
            "--min-rows",
            "1",
            "--require-zero-parse-failures",
        ),
    ),
    BundleCheck(
        filename="sam_b5_s4_accuracy_1937.jsonl",
        required_for_minimum=True,
        args=(
            "--phase",
            "B5",
            "--expected-row-count",
            "1937",
            "--require-zero-correctness-diffs",
            "--require-zero-parse-failures",
            "--require-b5-provenance",
        ),
    ),
    BundleCheck(
        filename="sam_b5_s4_raw_paired_513.jsonl",
        required_for_minimum=True,
        args=(
            "--phase",
            "B5",
            "--expected-row-count",
            "513",
            "--require-zero-choice-diffs",
            "--require-zero-correctness-diffs",
            "--require-zero-text-diffs",
            "--require-zero-parse-failures",
            "--require-b5-provenance",
        ),
    ),
)


def _run_check(bundle_dir: Path, output_dir: Path, check: BundleCheck) -> dict[str, object]:
    jsonl = bundle_dir / check.filename
    if not jsonl.exists():
        return {
            "filename": check.filename,
            "present": False,
            "required_for_minimum": check.required_for_minimum,
            "passed": not check.required_for_minimum,
            "summary_path": None,
        }

    summary_path = output_dir / f"{jsonl.stem}_validation_summary.json"
    cmd = [
        sys.executable,
        str(ROW_VALIDATOR),
        "--jsonl",
        str(jsonl),
        *check.args,
        "--summary-output",
        str(summary_path),
    ]
    result = subprocess.run(cmd, check=False)
    return {
        "filename": check.filename,
        "present": True,
        "required_for_minimum": check.required_for_minimum,
        "passed": result.returncode == 0,
        "returncode": result.returncode,
        "summary_path": str(summary_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir", type=Path, required=True)
    parser.add_argument(
        "--summary-output",
        type=Path,
        help="Overall bundle validation summary JSON",
    )
    parser.add_argument(
        "--allow-missing-minimum",
        action="store_true",
        help="Validate files that are present but do not fail when B0b/B3/B5 are missing.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle_dir = args.bundle_dir
    if not bundle_dir.is_dir():
        raise SystemExit(f"bundle directory does not exist: {bundle_dir}")

    output_dir = args.summary_output.parent if args.summary_output else bundle_dir / "validation"
    output_dir.mkdir(parents=True, exist_ok=True)

    checks = [_run_check(bundle_dir, output_dir, check) for check in CHECKS]
    if args.allow_missing_minimum:
        for check in checks:
            if not check["present"] and check["required_for_minimum"]:
                check["passed"] = True
    else:
        by_filename = {str(check["filename"]): check for check in checks}
        b0b = by_filename["sam_b0b_cache_correctness.jsonl"]
        if b0b["present"] and b0b["passed"]:
            for filename in (
                "sam_b1_cpersist_replication.jsonl",
                "sam_b2_many_turn_horizon.jsonl",
            ):
                check = by_filename[filename]
                if not check["present"]:
                    check["passed"] = False
                    check["blocked_reason"] = "B0b passed, so B1/B2 are required"

    summary = {
        "bundle_dir": str(bundle_dir),
        "checks": checks,
        "pass": all(bool(check["passed"]) for check in checks),
    }
    summary_output = args.summary_output or output_dir / "sam_scaleout_bundle_validation.json"
    summary_output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
