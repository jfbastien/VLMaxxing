#!/usr/bin/env python3
"""Build the RLT H3B prefill-split smoke artifact.

The artifact is intentionally small: it runs a dense n=1 Gemma first-turn cell
through the canonical Track-B runner, then validates that multimodal prefill and
text generation are split into nonzero JSONL fields before H3B can start.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "rlt_prefill_split_smoke_v1"
DEFAULT_ARTIFACT_DIR = Path("research/experiments/2026/artifacts/rlt_prefill_split_smoke")
DEFAULT_MANIFEST = Path("research/benchmark_manifests/videomme_dev_v1.toml")
DEFAULT_MODEL_PATH = Path.home() / "models" / "gemma-4-e4b-it-4bit"


def _load_jsonl(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    schema: dict[str, Any] | None = None
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            if payload.get("kind") == "schema":
                schema = payload
            elif payload.get("kind") == "item":
                rows.append(payload)
            else:
                raise ValueError(f"unexpected row kind in {path}: {payload.get('kind')!r}")
    if schema is None:
        raise ValueError(f"{path} is missing a schema row")
    if not rows:
        raise ValueError(f"{path} contains no item rows")
    return schema, rows


def _split_residual(timing_ms: dict[str, Any]) -> dict[str, float]:
    prefill_ms = float(timing_ms["multimodal_prefill_ms"])
    text_generation_ms = float(timing_ms["text_generation_ms"])
    generate_ms = float(timing_ms["generate"])
    residual_ms = abs(generate_ms - (prefill_ms + text_generation_ms))
    residual_pct = residual_ms / max(generate_ms, 1e-9)
    return {
        "multimodal_prefill_ms": prefill_ms,
        "text_generation_ms": text_generation_ms,
        "generate_ms": generate_ms,
        "split_residual_ms": residual_ms,
        "split_residual_pct": residual_pct,
    }


def _source_contains(path: Path, needles: list[str]) -> dict[str, bool]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return {needle: needle in text for needle in needles}


def validate_prefill_split_artifact(
    *,
    jsonl_path: Path,
    summary_path: Path,
    max_split_residual_pct: float,
    max_split_residual_ms: float,
) -> dict[str, Any]:
    schema, rows = _load_jsonl(jsonl_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if not isinstance(summary, dict):
        raise ValueError(f"{summary_path} did not contain a JSON object")

    failures: list[dict[str, Any]] = []
    item_summaries: list[dict[str, Any]] = []
    required_timing_fields = {
        "multimodal_prefill_ms",
        "text_generation_ms",
        "generate",
    }
    for row in rows:
        timing_ms = row.get("timing_ms")
        if not isinstance(timing_ms, dict):
            failures.append({"item_id": row.get("item_id"), "reason": "missing_timing_ms"})
            continue
        missing = sorted(required_timing_fields.difference(timing_ms))
        if missing:
            failures.append(
                {"item_id": row.get("item_id"), "reason": "missing_fields", "fields": missing}
            )
            continue
        split = _split_residual(timing_ms)
        if split["multimodal_prefill_ms"] <= 0.0:
            failures.append(
                {"item_id": row.get("item_id"), "reason": "nonpositive_multimodal_prefill_ms"}
            )
        if split["text_generation_ms"] <= 0.0:
            failures.append(
                {"item_id": row.get("item_id"), "reason": "nonpositive_text_generation_ms"}
            )
        split_residual_within_tolerance = (
            split["split_residual_pct"] <= max_split_residual_pct
            or split["split_residual_ms"] <= max_split_residual_ms
        )
        if not split_residual_within_tolerance:
            failures.append(
                {
                    "item_id": row.get("item_id"),
                    "reason": "split_residual_exceeds_tolerance",
                    "split_residual_ms": split["split_residual_ms"],
                    "split_residual_pct": split["split_residual_pct"],
                    "max_split_residual_ms": max_split_residual_ms,
                    "max_split_residual_pct": max_split_residual_pct,
                }
            )
        item_summaries.append(
            {
                "item_id": row.get("item_id"),
                "prompt_tokens": row.get("prompt_tokens"),
                "generation_tokens": row.get("generation_tokens"),
                "split_residual_within_tolerance": split_residual_within_tolerance,
                **split,
            }
        )

    qwen_reference_path = Path("src/codec_through/qwen_selective_reprefill.py")
    qwen_reference = _source_contains(
        qwen_reference_path,
        ["time.perf_counter_ns", "prompt_ms", '"prefill_ms"'],
    )
    if not all(qwen_reference.values()):
        failures.append(
            {
                "reason": "qwen_selective_reprefill_reference_missing",
                "reference_hits": qwen_reference,
            }
        )

    runner_fields = _source_contains(
        Path("scripts/run_phase1_63G_gemma_track_b.py"),
        ["multimodal_prefill_ms", "text_generation_ms"],
    )
    if not all(runner_fields.values()):
        failures.append({"reason": "runner_source_fields_missing", "field_hits": runner_fields})

    ready = not failures
    return {
        "schema_version": SCHEMA_VERSION,
        "ready": ready,
        "runner": "scripts/run_phase1_63G_gemma_track_b.py",
        "jsonl": str(jsonl_path),
        "summary": str(summary_path),
        "runner_schema": schema,
        "runner_summary_schema_version": summary.get("schema_version"),
        "n_items": len(rows),
        "max_split_residual_pct": max_split_residual_pct,
        "max_split_residual_ms": max_split_residual_ms,
        "split_residual_contract": (
            "Hard gate. The first-turn runner must split generate_ms into direct "
            "first-yield multimodal_prefill_ms plus remaining text_generation_ms within "
            "the preregistered tolerance before H3B can start."
        ),
        "items": item_summaries,
        "failures": failures,
        "fields_present": sorted(required_timing_fields),
        "semantic_reference": {
            "qwen_selective_reprefill_path": str(qwen_reference_path),
            "qwen_selective_reprefill_uses_wall_prefill_timer": all(qwen_reference.values()),
            "gemma_track_b_timing_split": schema.get("timing_split"),
            "interpretation": (
                "Gemma first-turn runners and qwen_selective_reprefill both expose a "
                "wall-clock prefill boundary; the Gemma smoke checks that the split "
                "adds back to generate_ms before allowing H3B."
            ),
        },
    }


def _run(command: list[str], *, timeout_seconds: int) -> dict[str, Any]:
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_seconds,
    )
    elapsed = time.perf_counter() - started
    payload = {
        "command": command,
        "returncode": completed.returncode,
        "elapsed_seconds": elapsed,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }
    if completed.returncode != 0:
        raise RuntimeError(json.dumps(payload, indent=2))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--frame-count", type=int, default=8)
    parser.add_argument("--n-items", type=int, default=1)
    parser.add_argument("--max-tokens", type=int, default=32)
    parser.add_argument("--rss-guard-mb", type=int, default=9000)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--max-split-residual-pct", type=float, default=0.03)
    parser.add_argument("--max-split-residual-ms", type=float, default=50.0)
    parser.add_argument("--reuse-existing", action="store_true")
    args = parser.parse_args()
    if args.n_items < 1:
        raise SystemExit("--n-items must be at least 1")
    if args.frame_count < 1:
        raise SystemExit("--frame-count must be positive")
    if args.max_split_residual_pct < 0.0:
        raise SystemExit("--max-split-residual-pct must be nonnegative")
    if args.max_split_residual_ms < 0.0:
        raise SystemExit("--max-split-residual-ms must be nonnegative")

    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output or args.artifact_dir / "prefill_split_smoke.json"
    jsonl_path = args.artifact_dir / "phase1_63g_dense_prefill_split_smoke.jsonl"
    summary_path = args.artifact_dir / "phase1_63g_dense_prefill_split_smoke_summary.json"
    run_payload: dict[str, Any] | None = None
    if not args.reuse_existing or not (jsonl_path.exists() and summary_path.exists()):
        command = [
            sys.executable,
            "scripts/run_phase1_63G_gemma_track_b.py",
            "--manifest",
            str(args.manifest),
            "--n-items",
            str(args.n_items),
            "--frame-count",
            str(args.frame_count),
            "--max-tokens",
            str(args.max_tokens),
            "--model-path",
            str(args.model_path),
            "--output",
            str(jsonl_path),
            "--summary",
            str(summary_path),
            "--allow-dirty",
        ]
        if args.rss_guard_mb > 0:
            command.extend(["--rss-guard-mb", str(args.rss_guard_mb)])
        run_payload = _run(command, timeout_seconds=args.timeout_seconds)

    payload = validate_prefill_split_artifact(
        jsonl_path=jsonl_path,
        summary_path=summary_path,
        max_split_residual_pct=args.max_split_residual_pct,
        max_split_residual_ms=args.max_split_residual_ms,
    )
    payload["run"] = run_payload
    payload["manifest"] = str(args.manifest)
    payload["model_path"] = str(args.model_path)
    payload["frame_count"] = args.frame_count
    payload["max_tokens"] = args.max_tokens
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output_path), "ready": payload["ready"]}, sort_keys=True))
    return 0 if payload["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
