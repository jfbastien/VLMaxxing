#!/usr/bin/env python3
"""Build the OV-6 kr-sweep and layer-sweep cross-arm tables.

Reads per-arm summary.json files under the kr_sweep and layer_sweep tranche
directories and emits CSV + Markdown grids indexed by (score source, keep_rate)
and (score source, prune layer).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KR_DIR = REPO_ROOT / "research/experiments/2026/artifacts/phase1_51V_ov6_kr_sweep"
LY_DIR = REPO_ROOT / "research/experiments/2026/artifacts/phase1_51V_ov6_layer_sweep"
SOURCES = ("magnitude_norm", "codec_novel_coded", "codec_motion", "codec_residual")
KR_VALUES = (0.30, 0.50, 0.70, 0.90)
LAYER_VALUES = (1, 2, 4, 8)


def _read_summary(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _kr_dirname(source: str, kr: float) -> str:
    return f"{source}_kr{int(round(kr * 100)):03d}"


def _layer_dirname(source: str, layer: int) -> str:
    return f"{source}_l{layer}"


def _kr_table_rows() -> list[dict]:
    # Include kr=0.5 results from the smoke directory (same N=10 manifest).
    smoke_dir = REPO_ROOT / "research/experiments/2026/artifacts/phase1_51V_ov6_smoke"
    rows: list[dict] = []
    for source in SOURCES:
        row: dict = {"source": source}
        for kr in KR_VALUES:
            if kr == 0.50:
                summary = _read_summary(smoke_dir / f"{source}_kr050" / "summary.json")
            else:
                summary = _read_summary(KR_DIR / _kr_dirname(source, kr) / "summary.json")
            if summary is None:
                row[f"kr{kr:.2f}"] = None
            else:
                row[f"kr{kr:.2f}"] = {
                    "accuracy": summary["dense_accuracy"],
                    "vision_ms": summary["mean_dense_vision_ms"],
                    "e2e_ms": summary["mean_dense_end_to_end_ms"],
                    "effective_keep_rate": summary["mean_effective_keep_rate"],
                }
        rows.append(row)
    return rows


def _layer_table_rows() -> list[dict]:
    # Include layer=2 results from the smoke directory (same N=10 manifest at kr=0.5).
    smoke_dir = REPO_ROOT / "research/experiments/2026/artifacts/phase1_51V_ov6_smoke"
    rows: list[dict] = []
    for source in SOURCES:
        row: dict = {"source": source}
        for layer in LAYER_VALUES:
            if layer == 2:
                summary = _read_summary(smoke_dir / f"{source}_kr050" / "summary.json")
            else:
                summary = _read_summary(LY_DIR / _layer_dirname(source, layer) / "summary.json")
            if summary is None:
                row[f"l{layer}"] = None
            else:
                row[f"l{layer}"] = {
                    "accuracy": summary["dense_accuracy"],
                    "vision_ms": summary["mean_dense_vision_ms"],
                    "e2e_ms": summary["mean_dense_end_to_end_ms"],
                }
        rows.append(row)
    return rows


def _accuracy_md(rows: list[dict], col_keys: tuple[str, ...]) -> str:
    lines = ["| source | " + " | ".join(col_keys) + " |"]
    lines.append("| --- | " + " | ".join("---" for _ in col_keys) + " |")
    for row in rows:
        cells = []
        for key in col_keys:
            cell = row.get(key)
            cells.append(f"{cell['accuracy']:.3f}" if cell else "—")
        lines.append(f"| {row['source']} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "research/experiments/2026/artifacts/onevision_vlmaxxing_plan")
    args = parser.parse_args()

    kr_rows = _kr_table_rows()
    layer_rows = _layer_table_rows()

    payload = {
        "phase": "OV-6",
        "manifest": "videomme_dev_v1_short_only.toml",
        "n_items": 10,
        "kr_sweep": {
            "layer": 2,
            "keep_rates": list(KR_VALUES),
            "sources": list(SOURCES),
            "rows": kr_rows,
        },
        "layer_sweep": {
            "keep_rate": 0.5,
            "layers": list(LAYER_VALUES),
            "sources": list(SOURCES),
            "rows": layer_rows,
        },
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "ov6_sweep_summary.json"
    md_path = args.out_dir / "ov6_sweep_summary.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    kr_cols = tuple(f"kr{kr:.2f}" for kr in KR_VALUES)
    layer_cols = tuple(f"l{layer}" for layer in LAYER_VALUES)

    md = "# OV-6 Track B sweep summary — accuracy at keep_rate (layer=2) and layer (kr=0.5)\n\n"
    md += "## Keep-rate sweep at layer=2, N=10\n\n"
    md += _accuracy_md(kr_rows, kr_cols)
    md += "\n## Layer sweep at kr=0.5, N=10\n\n"
    md += _accuracy_md(layer_rows, layer_cols)
    md_path.write_text(md)

    print(md)


if __name__ == "__main__":
    main()
