#!/usr/bin/env python3
"""Compare live-PyAV and precomputed-sidecar OV-6 codec arms."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

SOURCES = ("novel_coded", "motion", "residual")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return cast(dict[str, Any], payload)


def _load_rows(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with path.open() as handle:
        for line in handle:
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"expected object JSONL row: {path}")
            item_id = str(payload["item_id"])
            if item_id in rows:
                raise ValueError(f"duplicate item_id {item_id} in {path}")
            rows[item_id] = cast(dict[str, Any], payload)
    return rows


def _compare_pair(live_dir: Path, sidecar_dir: Path) -> dict[str, Any]:
    live_summary = _load_json(live_dir / "summary.json")
    sidecar_summary = _load_json(sidecar_dir / "summary.json")
    live_rows = _load_rows(live_dir / "results.jsonl")
    sidecar_rows = _load_rows(sidecar_dir / "results.jsonl")
    if set(live_rows) != set(sidecar_rows):
        raise ValueError(
            "live/sidecar item mismatch: "
            f"live_only={sorted(set(live_rows) - set(sidecar_rows))[:5]} "
            f"sidecar_only={sorted(set(sidecar_rows) - set(live_rows))[:5]}"
        )
    choice_drift = 0
    correctness_drift = 0
    kept_count_drift = 0
    per_frame_drift = 0
    for item_id in sorted(live_rows):
        live = live_rows[item_id]
        sidecar = sidecar_rows[item_id]
        choice_drift += int(live.get("choice_index") != sidecar.get("choice_index"))
        correctness_drift += int(bool(live["correct"]) != bool(sidecar["correct"]))
        kept_count_drift += int(int(live["kept_groups"]) != int(sidecar["kept_groups"]))
        per_frame_drift += int(
            list(live.get("kept_groups_per_frame", []))
            != list(sidecar.get("kept_groups_per_frame", []))
        )
    sidecar_load = sidecar_summary.get("codec_sidecar_load_mean_s_per_item")
    live_extract = live_summary.get("codec_extract_mean_s_per_item")
    return {
        "n_items": len(live_rows),
        "choice_drift": choice_drift,
        "correctness_drift": correctness_drift,
        "kept_count_drift": kept_count_drift,
        "kept_groups_per_frame_drift": per_frame_drift,
        "live_runtime_source": live_summary.get("codec_score_runtime_source"),
        "sidecar_runtime_source": sidecar_summary.get("codec_score_runtime_source"),
        "live_extract_mean_s_per_item": live_extract,
        "sidecar_load_mean_s_per_item": sidecar_load,
        "sidecar_faster_than_live_extract": (
            sidecar_load is not None and live_extract is not None and sidecar_load < live_extract
        ),
        "sidecar_load_under_1s": sidecar_load is not None and float(sidecar_load) < 1.0,
    }


def analyze(root: Path, *, sources: tuple[str, ...] = SOURCES) -> dict[str, Any]:
    pairs = {}
    for source in sources:
        pairs[source] = _compare_pair(root / f"live_{source}", root / f"sidecar_{source}")
    gate_pass = all(
        pair["choice_drift"] == 0
        and pair["correctness_drift"] == 0
        and pair["kept_count_drift"] == 0
        and pair["kept_groups_per_frame_drift"] == 0
        and pair["live_runtime_source"] == "live_pyav"
        and pair["sidecar_runtime_source"] == "sidecar"
        and pair["sidecar_load_under_1s"]
        and pair["sidecar_faster_than_live_extract"]
        for pair in pairs.values()
    )
    return {
        "schema": "ov6_sidecar_equivalence_v1",
        "root": str(root),
        "hypothesis": (
            "Precomputed H.264 score sidecars preserve live-PyAV codec-grid behavior "
            "while moving extraction cost outside model-run timing."
        ),
        "gate": (
            "zero choice/correctness/kept-count drift for every source; live runtime "
            "source is live_pyav; sidecar runtime source is sidecar; sidecar load < 1s/item "
            "and below live extraction time."
        ),
        "falsification": "any drift, missing runtime-source provenance, or sidecar load >= 1s/item",
        "gate_pass": gate_pass,
        "pairs": pairs,
    }


def _markdown(payload: dict[str, Any]) -> str:
    def _fmt_optional_float(value: Any) -> str:
        if value is None:
            return "missing"
        return f"{float(value):.6f}"

    lines = [
        "# OV-6 Sidecar Equivalence",
        "",
        f"Hypothesis: {payload['hypothesis']}",
        f"Gate: {payload['gate']}",
        f"Falsification: {payload['falsification']}",
        "",
        "| source | n | choice drift | correctness drift | kept-count drift | "
        "live source | sidecar source | live extract s/item | sidecar load s/item | gate |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | --- |",
    ]
    for source, pair in payload["pairs"].items():
        gate = (
            pair["choice_drift"] == 0
            and pair["correctness_drift"] == 0
            and pair["kept_count_drift"] == 0
            and pair["kept_groups_per_frame_drift"] == 0
            and pair["live_runtime_source"] == "live_pyav"
            and pair["sidecar_runtime_source"] == "sidecar"
            and pair["sidecar_load_under_1s"]
            and pair["sidecar_faster_than_live_extract"]
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    source,
                    str(pair["n_items"]),
                    str(pair["choice_drift"]),
                    str(pair["correctness_drift"]),
                    str(pair["kept_count_drift"]),
                    str(pair["live_runtime_source"]),
                    str(pair["sidecar_runtime_source"]),
                    _fmt_optional_float(pair["live_extract_mean_s_per_item"]),
                    _fmt_optional_float(pair["sidecar_load_mean_s_per_item"]),
                    "PASS" if gate else "FAIL",
                ]
            )
            + " |"
        )
    lines.extend(["", f"Overall gate: {'PASS' if payload['gate_pass'] else 'FAIL'}"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, default=None)
    parser.add_argument("--out-md", type=Path, default=None)
    args = parser.parse_args()

    payload = analyze(args.root)
    out_json = args.out_json or args.root / "sidecar_equivalence.json"
    out_md = args.out_md or args.root / "sidecar_equivalence.md"
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    out_md.write_text(_markdown(payload))
    print(out_json)
    print(out_md)


if __name__ == "__main__":
    main()
