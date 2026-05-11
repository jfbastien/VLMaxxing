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
    headline_numeric: str
    target_to_beat: str
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
        headline_numeric=(
            "imported: 3.1%-25.0% dense patches retained, i.e. 75.0%-96.9% "
            "patch reduction versus 64 dense frames / 16,384 patches"
        ),
        target_to_beat=(
            "not a local target; use as trained-encoder prior and compare only under "
            "its own patch/accuracy denominator"
        ),
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
        headline_numeric=(
            "reproduced: deterministic visible-index allocator; no accuracy/speed claim"
        ),
        target_to_beat=(
            "identical-score upstream Jaccard >= 0.90 if OV-4 parity is funded; "
            "real-video allocation must avoid anchor collapse and starvation"
        ),
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
        headline_numeric=(
            "OV-3 N=57 VideoMME short, 8 frames: pixel_acc=0.649, dense_acc=0.667, "
            "pixel→dense=54/57, mean active reuse=0.108"
        ),
        target_to_beat=(
            "serves as matched-budget baseline; codec sources must beat pixel at the same "
            "fresh budget without increasing parse failures or rows broken versus pixel"
        ),
        e2e_policy="not a work-skipped speedup claim",
        local_reproduction=(
            "research/experiments/2026/artifacts/phase1_29_onevision_n57/comparison.md"
        ),
        planned_gate="baseline for codec-source Track A comparison",
        artifact_or_source="scripts/run_phase1_29_planner_accuracy_probe.py",
    ),
    ComparisonRow(
        system="VLMaxxing Track A simple codec sources",
        status="reproduced here",
        intervention_layer="legacy continuous H.264 intra|cbf, motion, and residual score sources",
        denominator="paired answer stability at matched reuse/fresh budget",
        primary_metric="codec accuracy, pixel comparison, dense agreement, selection Jaccard",
        headline_numeric=(
            "OV-3 N=57 VideoMME short, 8 frames: novel_coded codec_acc=0.702 "
            "(+3/57 over pixel, McNemar p=0.25), motion/residual codec_acc=0.684 "
            "(+2/57 over pixel, p=0.50), codec→dense=54-56/57, mean active reuse=0.098-0.104"
        ),
        target_to_beat=(
            "reopens continuous H.264 spatial scoring only as a bounded Track A "
            "hypothesis: positive point estimates and no rows broken versus pixel, "
            "but individual McNemar cells remain inconclusive"
        ),
        e2e_policy="not a work-skipped speedup claim",
        local_reproduction=(
            "research/experiments/2026/artifacts/phase1_29_onevision_n57/{novel_coded,motion,residual}/"
        ),
        planned_gate="bounded decision-log reopen; use best simple source for Track B smoke",
        artifact_or_source="scripts/run_phase1_29_planner_accuracy_probe.py",
    ),
    ComparisonRow(
        system="OneVision-style fused planner + VLMaxxing Track A",
        status="reproduced here",
        intervention_layer="motion/residual score source for VLMaxxing planner",
        denominator="paired answer stability at matched reuse/fresh budget",
        primary_metric="codec-minus-pixel accuracy, dense agreement, selection Jaccard",
        headline_numeric=(
            "OV-3 N=57 VideoMME short, 8 frames: fused codec_acc=0.684 (+2/57 over "
            "pixel, McNemar p=0.50), codec→dense=54/57, codec→pixel=55/57; N=20 "
            "fused-equals-pixel was a manifest-coverage artifact, while frame=16 is "
            "a separate operating-point boundary where all codec sources collapse to pixel"
        ),
        target_to_beat=(
            "does not beat the simpler codec sources at N=57, so do not promote fusion "
            "as the preferred frozen-backend planner without a separate tuned/design "
            "split"
        ),
        e2e_policy="not a work-skipped speedup claim",
        local_reproduction=(
            "research/experiments/2026/artifacts/phase1_29_onevision_n57/fused/ and "
            "phase1_29_onevision_dev_n20_short_f16/fused/"
        ),
        planned_gate=(
            "descriptive positive at N=57; boundary at frame=16; simple sources remain "
            "the OV-6 candidates"
        ),
        artifact_or_source="OV-3 N=57 and frame=16 artifacts",
    ),
    ComparisonRow(
        system="OneVision-style sparse evidence + VLMaxxing Track B",
        status="hypothesis",
        intervention_layer="real vision-stage work skipped or sparse evidence lane",
        denominator="vision-stage and end-to-end wall-clock timing",
        primary_metric="latency, paired drift, parse failures, stage-share ceiling",
        headline_numeric="pending local result",
        target_to_beat=(
            "beat current sparse-vision boundaries at matched keep-rate: Qwen clean "
            "VideoMME 8f around 1.113x E2E, Gemma 32f short around 1.316x, and "
            "Qwen low-gain boundary around 1.032x only with fidelity caveat"
        ),
        e2e_policy="report component and E2E separately; no multiplied speedups",
        local_reproduction=(
            "M3 8f smoke first; M5 128GB only after smoke validates alignment and fidelity"
        ),
        planned_gate=(
            "M5 broad sweep only after M3 8f smoke is fidelity-clean; 16f only after "
            "8f gates; 32f only after 16f gates"
        ),
        artifact_or_source="planned OV-6 results",
    ),
    ComparisonRow(
        system="VLMaxxing C-PERSIST",
        status="reproduced here",
        intervention_layer="same-video follow-up prefix/cache reuse",
        denominator="setup-inclusive same-video session latency",
        primary_metric="follow-up latency, paired drift, session speedup by turns",
        headline_numeric=(
            "reproduced: repaired same-video follow-up speedup 14.90x-35.92x with "
            "0/93 paired choice/correctness drift in the tested breadth setting"
        ),
        target_to_beat=(
            "unchanged baseline for after-ingest reuse; combined rows must improve "
            "session economics without changing C-PERSIST fidelity"
        ),
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
        headline_numeric="pending local result",
        target_to_beat=(
            "setup-inclusive session curve at 1/2/5/10/50 same-video questions; "
            "do not multiply OneVision patch reduction by C-PERSIST follow-up speedup"
        ),
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
        headline_numeric="imported model size: about 0.3B params / 631 MB BF16 encoder",
        target_to_beat=(
            "single-clip PyTorch/MPS or MLX forward parity before any encoder-derived "
            "saliency result is used in the paper"
        ),
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
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
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
