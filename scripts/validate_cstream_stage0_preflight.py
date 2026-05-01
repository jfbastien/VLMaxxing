#!/usr/bin/env python3
"""Validate the <=1h C-STREAM candidate Stage 0 preflight.

This is an early stop/go gate, not a release-claim validator. It checks whether
the current Qwen session-streaming candidate is mechanically healthy enough to
justify Stage 1 / native event-window work.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _as_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    return float(value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair-summary", type=Path, required=True)
    parser.add_argument("--cold-summary", type=Path, required=True)
    parser.add_argument("--streaming-summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-wall-s", type=float, default=3600.0)
    parser.add_argument("--min-paired-queries", type=int, default=6)
    parser.add_argument("--max-accuracy-drop", type=float, default=0.10)
    parser.add_argument("--min-speedup", type=float, default=1.0)
    parser.add_argument("--min-followup-image-reuse-fraction", type=float, default=0.90)
    args = parser.parse_args()

    pair = _load(args.pair_summary)
    cold = _load(args.cold_summary)
    streaming = _load(args.streaming_summary)

    total_wall_s = (
        _as_float(cold.get("total_wall_ms")) + _as_float(streaming.get("total_wall_ms"))
    ) / 1000.0
    n_paired_queries = int(pair.get("n_paired_queries", 0))
    cold_parse_failures = int(pair.get("cold_parse_failures", 0))
    streaming_parse_failures = int(pair.get("streaming_parse_failures", 0))
    streaming_degenerate_count = int(pair.get("streaming_degenerate_count", 0))
    accuracy_delta = _as_float(pair.get("accuracy_delta_streaming_minus_cold"), default=-1.0)
    speedup = _as_float(pair.get("amortized_speedup_cold_over_streaming"), default=0.0)
    followup_reuse_fraction = _as_float(
        pair.get("streaming_follow_up_all_image_tokens_reused_fraction"),
        default=0.0,
    )
    followup_instrumented_n = int(pair.get("streaming_follow_up_image_token_instrumented_n", 0))
    followup_n = int(pair.get("streaming_follow_up_n", 0))

    gates = {
        "pass_wall_time": total_wall_s <= args.max_wall_s,
        "pass_min_paired_queries": n_paired_queries >= args.min_paired_queries,
        "pass_zero_parse_failures": cold_parse_failures == 0 and streaming_parse_failures == 0,
        "pass_zero_degenerate": streaming_degenerate_count == 0,
        "pass_quality_close": accuracy_delta >= -abs(args.max_accuracy_drop),
        "pass_positive_speedup": speedup >= args.min_speedup,
        "pass_followup_image_reuse_instrumented": followup_instrumented_n == followup_n
        and followup_n > 0,
        "pass_followup_image_reuse": (
            followup_reuse_fraction >= args.min_followup_image_reuse_fraction
        ),
    }
    go_to_stage1 = all(gates.values())
    payload = {
        "phase": "cstream_stage0_preflight",
        "claim_scope": (
            "stop/go preflight only; passing this does not promote C-STREAM to a paper headline"
        ),
        "go_to_stage1": go_to_stage1,
        "gates": gates,
        "thresholds": {
            "max_wall_s": args.max_wall_s,
            "min_paired_queries": args.min_paired_queries,
            "max_accuracy_drop": args.max_accuracy_drop,
            "min_speedup": args.min_speedup,
            "min_followup_image_reuse_fraction": args.min_followup_image_reuse_fraction,
        },
        "metrics": {
            "total_wall_s": total_wall_s,
            "n_paired_queries": n_paired_queries,
            "cold_parse_failures": cold_parse_failures,
            "streaming_parse_failures": streaming_parse_failures,
            "streaming_degenerate_count": streaming_degenerate_count,
            "accuracy_delta_streaming_minus_cold": accuracy_delta,
            "amortized_speedup_cold_over_streaming": speedup,
            "streaming_follow_up_n": followup_n,
            "streaming_follow_up_image_token_instrumented_n": followup_instrumented_n,
            "streaming_follow_up_all_image_tokens_reused_fraction": followup_reuse_fraction,
        },
        "inputs": {
            "pair_summary": args.pair_summary.as_posix(),
            "cold_summary": args.cold_summary.as_posix(),
            "streaming_summary": args.streaming_summary.as_posix(),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"[cstream-stage0] wrote {args.output}")
    print(f"[cstream-stage0] go_to_stage1={go_to_stage1}")
    if not go_to_stage1:
        failed = [name for name, passed in gates.items() if not passed]
        print("[cstream-stage0] failed gates: " + ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
