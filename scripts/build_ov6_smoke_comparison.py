#!/usr/bin/env python3
"""Build the OV-6 Track B smoke cross-arm comparison summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_OUT_DIR = Path("research/experiments/2026/artifacts/phase1_51V_ov6_smoke")
ARMS = (
    "dense",
    "magnitude_norm_kr050",
    "uniform_random_kr050",
    "codec_novel_coded_kr050",
    "codec_motion_kr050",
    "codec_residual_kr050",
)


def _load(out_dir: Path, arm: str) -> dict[str, object]:
    return json.loads((out_dir / arm / "summary.json").read_text())


def _row(arm: str, summary: dict[str, object]) -> dict[str, object]:
    return {
        "arm": arm,
        "n_items": summary["n_items"],
        "accuracy": summary["dense_accuracy"],
        "mean_vision_ms": summary["mean_dense_vision_ms"],
        "mean_e2e_ms": summary["mean_dense_end_to_end_ms"],
        "median_e2e_ms": summary["median_dense_end_to_end_ms"],
        "mean_peak_memory_gb": summary["mean_peak_memory_gb"],
        "effective_keep_rate": summary["mean_effective_keep_rate"],
        "codec_extract_mean_s_per_item": summary.get("codec_extract_mean_s_per_item"),
    }


def _markdown(rows: list[dict[str, object]]) -> str:
    headers = ("arm", "n", "acc", "vision_ms", "e2e_ms", "peak_gb", "eff_kr", "codec_extract_s")
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for r in rows:
        cer = r["codec_extract_mean_s_per_item"]
        lines.append(
            "| "
            + " | ".join(
                [
                    str(r["arm"]),
                    str(r["n_items"]),
                    f"{r['accuracy']:.3f}",
                    f"{r['mean_vision_ms']:.0f}",
                    f"{r['mean_e2e_ms']:.0f}",
                    f"{r['mean_peak_memory_gb']:.2f}",
                    f"{r['effective_keep_rate']:.3f}",
                    f"{cer:.2f}" if cer is not None else "-",
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    rows = [_row(arm, _load(args.out_dir, arm)) for arm in ARMS]
    payload = {
        "phase": "OV-6",
        "manifest": "videomme_dev_v1_short_only.toml",
        "model": "Qwen2.5-VL-7B-Instruct-4bit",
        "frame_count": 8,
        "keep_rate": 0.5,
        "layer": 2,
        "rows": rows,
    }
    json_path = args.out_dir / "comparison.json"
    md_path = args.out_dir / "comparison.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    md_path.write_text(_markdown(rows))
    print(_markdown(rows))


if __name__ == "__main__":
    main()
