#!/usr/bin/env python3
"""Build the OV-3 cross-source comparison summary from per-source results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_OUT_DIR = Path("research/experiments/2026/artifacts/phase1_29_onevision_dev")
SOURCES = ("novel_coded", "motion", "residual", "fused")


def _load(out_dir: Path, source: str) -> dict[str, object]:
    return json.loads((out_dir / source / "summary.json").read_text())


def _format_row(source: str, summary: dict[str, object]) -> dict[str, object]:
    return {
        "source": source,
        "n_items": summary["n_items"],
        "dense_accuracy": summary["dense_accuracy"],
        "pixel_accuracy": summary["pixel_accuracy"],
        "codec_accuracy": summary["codec_accuracy"],
        "codec_minus_pixel_accuracy": summary["codec_minus_pixel_accuracy"],
        "pixel_dense_agreement": summary["pixel_dense_agreement"],
        "codec_dense_agreement": summary["codec_dense_agreement"],
        "codec_pixel_agreement": summary["codec_pixel_agreement"],
        "pair_selection_jaccard_mean": summary["pair_selection_jaccard_mean"],
        "pixel_reuse_ratio_mean_active": summary["pixel_reuse_ratio_mean_active"],
        "codec_reuse_ratio_mean_active": summary["codec_reuse_ratio_mean_active"],
        "codec_score_units": summary["codec_score_units"],
    }


def _markdown_table(rows: list[dict[str, object]]) -> str:
    headers = (
        "source",
        "n",
        "dense",
        "pixel",
        "codec",
        "codec-pixel",
        "pixel→dense",
        "codec→dense",
        "codec→pixel",
        "jaccard",
        "pixel reuse",
        "codec reuse",
    )
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["source"]),
                    str(row["n_items"]),
                    f"{row['dense_accuracy']:.3f}",
                    f"{row['pixel_accuracy']:.3f}",
                    f"{row['codec_accuracy']:.3f}",
                    f"{row['codec_minus_pixel_accuracy']:+.3f}",
                    f"{row['pixel_dense_agreement']:.3f}",
                    f"{row['codec_dense_agreement']:.3f}",
                    f"{row['codec_pixel_agreement']:.3f}",
                    f"{row['pair_selection_jaccard_mean']:.3f}",
                    f"{row['pixel_reuse_ratio_mean_active']:.3f}",
                    f"{row['codec_reuse_ratio_mean_active']:.3f}",
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    summaries = {source: _load(args.out_dir, source) for source in SOURCES}
    rows = [_format_row(source, summaries[source]) for source in SOURCES]
    manifests = sorted({str(summaries[source]["manifest_path"]) for source in SOURCES})
    if len(manifests) != 1:
        raise ValueError(f"per-source summaries disagree on manifest_path: {manifests}")
    frame_counts = sorted({int(summaries[source]["frame_count"]) for source in SOURCES})  # type: ignore[arg-type]
    if len(frame_counts) != 1:
        raise ValueError(f"per-source summaries disagree on frame_count: {frame_counts}")
    payload = {
        "phase": "OV-3",
        "manifest": manifests[0],
        "model": "Qwen2.5-VL-7B-Instruct-4bit",
        "frame_count": frame_counts[0],
        "max_tokens": 32,
        "rows": rows,
    }
    json_path = args.out_dir / "comparison.json"
    md_path = args.out_dir / "comparison.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    md_path.write_text(_markdown_table(rows))
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    print(_markdown_table(rows))


if __name__ == "__main__":
    main()
