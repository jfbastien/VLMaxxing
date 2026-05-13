#!/usr/bin/env python3
"""Validate OV-8 accounting output against its source artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.build_onevision_cpersist_session_accounting import build_payload  # noqa: E402


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return cast(dict[str, Any], payload)


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def validate(args: argparse.Namespace) -> None:
    saved = _load_json(args.accounting_json)
    rebuilt = build_payload(
        dense_dir=args.dense_dir,
        sparse_dir=args.sparse_dir,
        cpersist_summary_path=args.cpersist_summary,
        horizon=args.horizon,
    )
    if _canonical(saved) != _canonical(rebuilt):
        raise ValueError("accounting.json does not match rebuilt source-artifact payload")

    pairing = saved["first_query_pairing"]
    if args.max_first_query_correctness_drift is not None and (
        int(pairing["correctness_drift"]) > args.max_first_query_correctness_drift
    ):
        raise ValueError(
            "first-query correctness drift exceeds policy: "
            f"{pairing['correctness_drift']} > {args.max_first_query_correctness_drift}"
        )
    if args.max_first_query_choice_drift is not None and (
        int(pairing["choice_drift"]) > args.max_first_query_choice_drift
    ):
        raise ValueError(
            "first-query choice drift exceeds policy: "
            f"{pairing['choice_drift']} > {args.max_first_query_choice_drift}"
        )

    for row in saved["rows"]:
        if int(row.get("followup_n", 0)) <= 0:
            raise ValueError(f"OV-8 row has no follow-up samples: {row}")
        if int(row.get("followup_choice_drift", 0)) != 0:
            raise ValueError(f"OV-8 follow-up choice drift is not clean: {row}")
        if int(row.get("followup_correctness_drift", 0)) != 0:
            raise ValueError(f"OV-8 follow-up correctness drift is not clean: {row}")
        if int(row.get("followup_pathological", 0)) != 0:
            raise ValueError(f"OV-8 follow-up pathological rows are not clean: {row}")
    if saved.get("status") != "artifact-level accounting only":
        raise ValueError("OV-8 accounting must remain artifact-level accounting only")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accounting-json", type=Path, required=True)
    parser.add_argument("--dense-dir", type=Path, required=True)
    parser.add_argument("--sparse-dir", type=Path, required=True)
    parser.add_argument("--cpersist-summary", type=Path, required=True)
    parser.add_argument("--horizon", type=int, default=50)
    parser.add_argument("--max-first-query-correctness-drift", type=int, default=None)
    parser.add_argument("--max-first-query-choice-drift", type=int, default=None)
    validate(parser.parse_args())


if __name__ == "__main__":
    main()
