#!/usr/bin/env python3
"""Direct ground-truth correctness analysis across OV-3 result tranches.

Reads per-item results.jsonl from every codec source in every tranche, recovers the
ground-truth answer_index from each row's `<config>.correct` flag combined with
`<config>.choice_index`, and reports correctness rates that do not depend on dense
stability. Exposes the cases where dense flips between tranches and how often codec
or pixel "rescue" the correct answer where dense or pixel drift.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TRANCHES = (
    Path("research/experiments/2026/artifacts/phase1_29_onevision_dev"),
    Path("research/experiments/2026/artifacts/phase1_29_onevision_dev_n20_short"),
    Path("research/experiments/2026/artifacts/phase1_29_onevision_holdout_disjoint"),
)
SOURCES = ("novel_coded", "motion", "residual", "fused")


@dataclass(frozen=True, slots=True)
class ItemRow:
    item_id: str
    answer_index: int
    dense_choice: int | None
    pixel_choice: int | None
    codec_choice: int | None
    dense_correct: bool
    pixel_correct: bool
    codec_correct: bool


def _ground_truth(row: dict) -> int:
    """Recover answer_index from any of the three configs that has correct=True.

    If none is correct, fall back to dense.choice_index (we still need something to
    label as ground-truth-recovered for cross-source comparison; this case is the
    "all three agree on a wrong answer" pattern).
    """

    for key in ("dense", "pixel_cached", "codec_cached"):
        cfg = row.get(key, {})
        if cfg.get("correct"):
            return int(cfg["choice_index"])
    # All three wrong; we cannot recover answer_index without an external mapping.
    # Return -1 so downstream callers can flag.
    return -1


def _row(item: dict) -> ItemRow:
    answer = _ground_truth(item)
    return ItemRow(
        item_id=str(item["item_id"]),
        answer_index=answer,
        dense_choice=item.get("dense", {}).get("choice_index"),
        pixel_choice=item.get("pixel_cached", {}).get("choice_index"),
        codec_choice=item.get("codec_cached", {}).get("choice_index"),
        dense_correct=bool(item.get("dense", {}).get("correct", False)),
        pixel_correct=bool(item.get("pixel_cached", {}).get("correct", False)),
        codec_correct=bool(item.get("codec_cached", {}).get("correct", False)),
    )


def _load_source(tranche: Path, source: str) -> list[ItemRow]:
    path = tranche / source / "results.jsonl"
    if not path.exists():
        return []
    rows: list[ItemRow] = []
    with path.open() as handle:
        for line in handle:
            rows.append(_row(json.loads(line)))
    return rows


def _stats(rows: list[ItemRow]) -> dict[str, float | int]:
    n = len(rows)
    if n == 0:
        return {}
    return {
        "n": n,
        "dense_correct": sum(r.dense_correct for r in rows),
        "pixel_correct": sum(r.pixel_correct for r in rows),
        "codec_correct": sum(r.codec_correct for r in rows),
        "dense_acc": sum(r.dense_correct for r in rows) / n,
        "pixel_acc": sum(r.pixel_correct for r in rows) / n,
        "codec_acc": sum(r.codec_correct for r in rows) / n,
        "codec_rescues_pixel": sum(
            r.codec_correct and not r.pixel_correct for r in rows
        ),
        "pixel_rescues_codec": sum(
            r.pixel_correct and not r.codec_correct for r in rows
        ),
        "codec_matches_pixel_correct": sum(
            r.codec_correct == r.pixel_correct for r in rows
        ),
    }


def _disagreement_table(rows_by_source: dict[str, list[ItemRow]]) -> list[dict]:
    """For each item that appears in multiple sources, compare choices."""

    by_item: dict[str, dict[str, ItemRow]] = defaultdict(dict)
    for source, rows in rows_by_source.items():
        for row in rows:
            by_item[row.item_id][source] = row

    out: list[dict] = []
    for item_id, source_rows in by_item.items():
        # Find items where any of {pixel_correct, codec_correct, dense_correct}
        # disagrees across sources, or where pixel != codec on the same item.
        entries = []
        for source, row in source_rows.items():
            entries.append(
                {
                    "source": source,
                    "answer_index": row.answer_index,
                    "dense_choice": row.dense_choice,
                    "pixel_choice": row.pixel_choice,
                    "codec_choice": row.codec_choice,
                    "dense_correct": row.dense_correct,
                    "pixel_correct": row.pixel_correct,
                    "codec_correct": row.codec_correct,
                }
            )

        codec_choices = {e["codec_choice"] for e in entries}
        pixel_choice = entries[0]["pixel_choice"]
        any_disagrees_with_pixel = any(
            e["codec_choice"] != pixel_choice for e in entries
        )
        if len(codec_choices) > 1 or any_disagrees_with_pixel:
            out.append(
                {
                    "item_id": item_id,
                    "answer_index": entries[0]["answer_index"],
                    "by_source": entries,
                }
            )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tranche",
        type=Path,
        action="append",
        default=None,
        help="Tranche directory; repeatable. Defaults to all three OV-3 tranches.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(
            "research/experiments/2026/artifacts/phase1_29_onevision_dev/ground_truth_analysis.json"
        ),
    )
    args = parser.parse_args()

    tranches = tuple(args.tranche) if args.tranche else DEFAULT_TRANCHES

    payload: dict = {"tranches": [], "all_sources_aggregate": {}}
    aggregate_rows_by_source: dict[str, list[ItemRow]] = {s: [] for s in SOURCES}
    for tranche in tranches:
        tranche_payload: dict = {"path": str(tranche), "by_source": {}, "disagreements": []}
        rows_by_source: dict[str, list[ItemRow]] = {}
        for source in SOURCES:
            rows = _load_source(tranche, source)
            if not rows:
                continue
            rows_by_source[source] = rows
            aggregate_rows_by_source[source].extend(rows)
            tranche_payload["by_source"][source] = _stats(rows)
        if rows_by_source:
            tranche_payload["disagreements"] = _disagreement_table(rows_by_source)
        payload["tranches"].append(tranche_payload)

    for source, rows in aggregate_rows_by_source.items():
        if rows:
            payload["all_sources_aggregate"][source] = _stats(rows)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    # Print a terse summary table.
    print(f"# Direct ground-truth correctness across {len(tranches)} tranches\n")
    print("| tranche | source | n | dense_acc | pixel_acc | codec_acc | codec_rescues_pixel |")
    print("|---|---|---|---|---|---|---|")
    for tranche_payload in payload["tranches"]:
        tname = Path(tranche_payload["path"]).name
        for source, stats in tranche_payload["by_source"].items():
            print(
                f"| {tname} | {source} | {stats['n']} | {stats['dense_acc']:.3f} | "
                f"{stats['pixel_acc']:.3f} | {stats['codec_acc']:.3f} | "
                f"{stats['codec_rescues_pixel']} |"
            )
    print()
    print("# Items where any source disagreed with pixel:")
    seen_ids: set[str] = set()
    for tranche_payload in payload["tranches"]:
        for entry in tranche_payload["disagreements"]:
            tag = f"{Path(tranche_payload['path']).name}:{entry['item_id']}"
            if tag in seen_ids:
                continue
            seen_ids.add(tag)
            print(
                f"- {Path(tranche_payload['path']).name} {entry['item_id']} "
                f"(gt={entry['answer_index']})"
            )
            for src in entry["by_source"]:
                print(
                    f"  {src['source']:>11s}: dense={src['dense_choice']} "
                    f"pixel={src['pixel_choice']} codec={src['codec_choice']} "
                    f"d.ok={src['dense_correct']} p.ok={src['pixel_correct']} "
                    f"c.ok={src['codec_correct']}"
                )

    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
