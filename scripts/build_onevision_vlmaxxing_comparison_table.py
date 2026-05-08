#!/usr/bin/env python3
"""Emit the planned OneVision / VLMaxxing comparison table.

This is a CPU-only planning artifact. It records denominators and claim status
before model-bearing experiments run, so later results can fill the same table
without mixing patch savings, Track A answer stability, Track B timing, and
C-PERSIST session economics.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_OUT_DIR = Path("research/experiments/2026/artifacts/onevision_vlmaxxing_plan")


@dataclass(frozen=True, slots=True)
class ComparisonRow:
    system: str
    status: str
    intervention_layer: str
    denominator: str
    primary_metric: str
    e2e_policy: str
    local_reproduction: str
    planned_gate: str
    artifact_or_source: str


ROWS = (
    ComparisonRow(
        system="OneVision-Encoder paper",
        status="imported result",
        intervention_layer="trained codec-aligned visual encoder",
        denominator="visual patches/tokens and benchmark accuracy",
        primary_metric="reported patch reduction and multimodal benchmark accuracy",
        e2e_policy="do not convert to wall-clock speedup without measured stage share",
        local_reproduction="not fully reproduced locally; full pretraining is cluster-scale",
        planned_gate="cite only as imported trained-encoder counterpart",
        artifact_or_source="arXiv v3 and LMMS-Lab page",
    ),
    ComparisonRow(
        system="OneVision clean-room patchification",
        status="reproduced here",
        intervention_layer="codec-derived motion/residual Top-K allocator",
        denominator="selected token locations before VLM inference",
        primary_metric="visible-index parity, token allocation over time, spatial-bias audit",
        e2e_policy="no E2E speedup claim",
        local_reproduction=(
            "CPU tests plus real-video allocation artifact path; audit pending until "
            "raw clips are present"
        ),
        planned_gate="allocation must not collapse to anchor-only or edge/OCR starvation",
        artifact_or_source="src/codec_through/codec/onevision_patchification.py",
    ),
    ComparisonRow(
        system="VLMaxxing Track A pixel-diff baseline",
        status="reproduced here",
        intervention_layer="semantic substitution over frozen VLM features",
        denominator="paired answer stability at matched reuse/fresh budget",
        primary_metric="paired choice/correctness drift and parse failures",
        e2e_policy="not a work-skipped speedup claim",
        local_reproduction="existing Phase 1.29/1.57-style artifacts",
        planned_gate="baseline for fused-codec planner comparison",
        artifact_or_source="scripts/run_phase1_29_planner_accuracy_probe.py",
    ),
    ComparisonRow(
        system="OneVision-style fused planner + VLMaxxing Track A",
        status="hypothesis",
        intervention_layer="motion/residual score source for VLMaxxing planner",
        denominator="paired answer stability at matched reuse/fresh budget",
        primary_metric="codec-minus-pixel accuracy, dense agreement, selection Jaccard",
        e2e_policy="not a work-skipped speedup claim",
        local_reproduction="sequential Qwen then Gemma planner ablation",
        planned_gate="beat pixel max_abs on dev and holdout without higher drift",
        artifact_or_source="planned OV-3/OV-5 results",
    ),
    ComparisonRow(
        system="OneVision-style sparse evidence + VLMaxxing Track B",
        status="hypothesis",
        intervention_layer="real vision-stage work skipped or sparse evidence lane",
        denominator="vision-stage and end-to-end wall-clock timing",
        primary_metric="latency, paired drift, parse failures, stage-share ceiling",
        e2e_policy="report component and E2E separately; no multiplied speedups",
        local_reproduction="M5-only Qwen first; Gemma only if Qwen gates clean",
        planned_gate="fidelity-clean cell at useful keep-rate",
        artifact_or_source="planned OV-6 results",
    ),
    ComparisonRow(
        system="VLMaxxing C-PERSIST",
        status="reproduced here",
        intervention_layer="same-video follow-up prefix/cache reuse",
        denominator="setup-inclusive same-video session latency",
        primary_metric="follow-up latency, paired drift, session speedup by turns",
        e2e_policy="report separately from first-ingest pruning",
        local_reproduction="existing local Qwen/Gemma C-PERSIST runs",
        planned_gate="unchanged baseline for composition accounting",
        artifact_or_source="current paper claim matrix and C-PERSIST artifacts",
    ),
    ComparisonRow(
        system="OneVision-style first ingest + VLMaxxing C-PERSIST",
        status="hypothesis",
        intervention_layer="codec-sparse ingest plus same-video state reuse",
        denominator=(
            "two lanes: first-query vision tokens; follow-up setup-inclusive session wall-clock"
        ),
        primary_metric="lane-separated stage-share ceiling, session speedup, paired drift",
        e2e_policy="only report measured E2E when Track B backend skips real work",
        local_reproduction="run only after Track A/Track B gates decide what is meaningful",
        planned_gate="composition must improve session economics without conflating denominators",
        artifact_or_source="planned OV-8 results",
    ),
    ComparisonRow(
        system="OneVision-Encoder local feasibility",
        status="hypothesis",
        intervention_layer="third encoder-only representation probe",
        denominator="encoder feature extraction and saliency diagnostics",
        primary_metric="load parity, patch-size/3D-RoPE correctness, saliency correlation",
        e2e_policy="not a third VLM unless an LMM head is reproduced",
        local_reproduction="deferred MLX or CPU smoke after planner results",
        planned_gate="single-clip feature parity before any paper claim",
        artifact_or_source="planned OV-7 result",
    ),
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    rows = [asdict(row) for row in ROWS]
    json_path = args.out_dir / "comparison_table_plan.json"
    csv_path = args.out_dir / "comparison_table_plan.csv"
    md_path = args.out_dir / "comparison_table_plan.md"

    json_path.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    headers = list(rows[0].keys())
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row[header]) for header in headers) + " |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json_path)
    print(csv_path)
    print(md_path)


if __name__ == "__main__":
    main()
