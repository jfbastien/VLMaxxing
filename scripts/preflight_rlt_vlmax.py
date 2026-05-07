#!/usr/bin/env python3
"""Preflight RLT/VLMaxxing composition experiments.

The checks are intentionally conservative: selected phases fail before smokes
or long model runs when prerequisite instrumentation or cache-safety evidence
is missing.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Literal

PhaseName = Literal[
    "RLT-1",
    "RLT-1.5",
    "RLT-2G",
    "RLT-3G-A",
    "RLT-3G-B",
    "RLT-4Q",
    "RLT-5G",
    "RLT-5Q",
    "RLT-6",
    "RLT-7",
]

SCHEMA_VERSION = "rlt_vlmax_preflight_v1"
DEFAULT_OUTPUT = Path("research/experiments/2026/artifacts/rlt_vlmax_preflight.json")
PHASES_REQUIRING_PREFILL_SPLIT = {"RLT-3G-B"}
PHASES_REQUIRING_GEMMA_SWA = {"RLT-5G"}


def _status(ok: bool, *, detail: Any, required: bool = True) -> dict[str, Any]:
    return {"ready": ok, "required": required, "detail": detail}


def _file_contains(path: Path, needles: list[str]) -> dict[str, bool]:
    if not path.exists():
        return {needle: False for needle in needles}
    text = path.read_text(encoding="utf-8", errors="replace")
    return {needle: needle in text for needle in needles}


def _check_paths(paths: list[Path]) -> dict[str, dict[str, Any]]:
    return {str(path): _status(path.exists(), detail=str(path)) for path in paths}


def _python_module_path(module_name: str) -> Path | None:
    spec = importlib.util.find_spec(module_name)
    if spec is None or spec.origin is None:
        return None
    return Path(spec.origin).resolve()


def _check_prefill_split() -> dict[str, Any]:
    runners = [
        Path("scripts/run_phase1_51V.py"),
        Path("scripts/run_phase1_63G_gemma_track_b.py"),
    ]
    required_fields = ["multimodal_prefill_ms", "text_generation_ms"]
    details = {
        str(path): {
            "exists": path.exists(),
            "fields": _file_contains(path, required_fields),
        }
        for path in runners
    }
    ok = all(
        item["exists"] and all(bool(value) for value in item["fields"].values())
        for item in details.values()
    )
    return _status(ok, detail=details)


def _check_swa_marker() -> dict[str, Any]:
    module_path = _python_module_path("mlx_vlm.generate")
    if module_path is None:
        return _status(False, detail={"module": "missing"})
    markers = [
        "Topology-aware trim",
        "RotatingKVCache",
        "can_trim_prompt_cache",
        "trim_prompt_cache",
    ]
    found = _file_contains(module_path, markers)
    ok = (
        found["Topology-aware trim"] or found["can_trim_prompt_cache"] or found["trim_prompt_cache"]
    )
    return _status(
        ok,
        detail={
            "module_path": str(module_path),
            "marker_hits": found,
            "note": (
                "Marker presence is a fast screen only. Gemma H4A also requires "
                "the functional cache-correctness smoke."
            ),
        },
    )


def _run_swa_smoke(out_dir: Path, *, timeout_seconds: int) -> dict[str, Any]:
    if not os.environ.get("HF_TOKEN"):
        return _status(
            False,
            detail="HF_TOKEN is required by scripts/run_sam_b0b_cache_correctness.py",
        )
    smoke_out = out_dir / "rlt_swa_cache_correctness_smoke.jsonl"
    command = [
        sys.executable,
        "scripts/run_sam_b0b_cache_correctness.py",
        "--smoke",
        "--out",
        str(smoke_out),
    ]
    try:
        env = {**os.environ, "B0B_DISABLE_RUNTIME_GUARD": "1"}
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            env=env,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return _status(
            False,
            detail={
                "command": command,
                "error": f"{type(exc).__name__}: {exc}",
            },
        )
    ok = completed.returncode == 0 and smoke_out.exists()
    return _status(
        ok,
        detail={
            "command": command,
            "env_overrides": {"B0B_DISABLE_RUNTIME_GUARD": "1"},
            "returncode": completed.returncode,
            "stdout_tail": completed.stdout[-2000:],
            "stderr_tail": completed.stderr[-2000:],
            "artifact": str(smoke_out),
        },
    )


def _phase_requires_prefill_split(phases: list[PhaseName]) -> bool:
    return bool(PHASES_REQUIRING_PREFILL_SPLIT.intersection(phases))


def _phase_requires_gemma_swa(phases: list[PhaseName]) -> bool:
    return bool(PHASES_REQUIRING_GEMMA_SWA.intersection(phases))


def _all_required_ready(payload: dict[str, Any]) -> bool:
    for section in payload["checks"].values():
        if isinstance(section, dict) and "ready" in section:
            if section.get("required") and not section.get("ready"):
                return False
        elif isinstance(section, dict):
            for item in section.values():
                if isinstance(item, dict) and item.get("required") and not item.get("ready"):
                    return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        action="append",
        choices=[
            "RLT-1",
            "RLT-1.5",
            "RLT-2G",
            "RLT-3G-A",
            "RLT-3G-B",
            "RLT-4Q",
            "RLT-5G",
            "RLT-5Q",
            "RLT-6",
            "RLT-7",
        ],
        default=[],
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--run-swa-smoke", action="store_true")
    parser.add_argument("--swa-smoke-timeout-seconds", type=int, default=1800)
    parser.add_argument(
        "--allow-swa-marker-only",
        action="store_true",
        help="Diagnostic only; Gemma H4A remains blocked without the functional smoke.",
    )
    args = parser.parse_args()

    phases: list[PhaseName] = args.phase or ["RLT-1"]
    required_paths = [
        Path("research/experiments/2026/2026-05-07-rlt-vlmax-composition-design.md"),
        Path("scripts/profile_rlt_masks.py"),
        Path("src/codec_through/rlt_masks.py"),
        Path("research/benchmark_manifests/videomme_dev_v1.toml"),
        Path("research/benchmark_manifests/videomme_holdout_v1.toml"),
        Path("research/benchmark_manifests/videomme_combined_v1_n60.toml"),
        Path("research/benchmark_manifests/videomme_holdout_v1_short_only.toml"),
    ]
    checks: dict[str, Any] = {
        "required_paths": _check_paths(required_paths),
        "prefill_split": _check_prefill_split(),
    }
    if not _phase_requires_prefill_split(phases):
        checks["prefill_split"]["required"] = False

    swa_marker = _check_swa_marker()
    checks["swa_marker"] = swa_marker
    checks["swa_marker"]["required"] = False
    if _phase_requires_gemma_swa(phases):
        if args.run_swa_smoke:
            with tempfile.TemporaryDirectory(prefix="rlt_swa_smoke_") as tmp:
                checks["swa_functional_smoke"] = _run_swa_smoke(
                    Path(tmp),
                    timeout_seconds=args.swa_smoke_timeout_seconds,
                )
        else:
            checks["swa_functional_smoke"] = _status(
                args.allow_swa_marker_only and bool(swa_marker.get("ready")),
                detail=(
                    "Gemma H4A requires --run-swa-smoke for a go/no-go check. "
                    "--allow-swa-marker-only is diagnostic and does not support "
                    "paper-facing H4A claims."
                ),
            )

    payload = {
        "schema_version": SCHEMA_VERSION,
        "selected_phases": phases,
        "checks": checks,
    }
    payload["ready"] = _all_required_ready(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "ready": payload["ready"]}, sort_keys=True))
    return 0 if payload["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
