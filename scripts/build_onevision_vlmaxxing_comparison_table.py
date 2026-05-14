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
            "CPU tests plus real-video allocation artifacts under "
            "onevision_vlmaxxing_visuals/ and onevision_vlmaxxing_explainer_videos/"
        ),
        planned_gate=(
            "real-video allocation gate passed; use as explanation artifact, not accuracy evidence"
        ),
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
        status="reproduced here",
        intervention_layer="real vision-stage work skipped or sparse evidence lane",
        denominator="vision-stage and end-to-end wall-clock timing",
        primary_metric=(
            "accuracy, paired sparse-vs-baseline correctness, vision-stage timing, "
            "E2E timing with and without codec extraction"
        ),
        headline_numeric=(
            "OV-6 N=57 VideoMME short, Qwen 7B 8f: at kr=0.7/layer=2, "
            "codec_novel_coded=35/57 (0.614) vs magnitude_norm=31/57 (0.544), "
            "paired fixes/breaks=5/1, McNemar p=0.2188; model-side E2E 33.3s "
            "excludes 18.8s/item PyAV extraction, so current net E2E is 52.1s. "
            "At kr=0.5/layer=8, codec_residual ties magnitude_norm at 31/57. "
            "Follow-up controls: random beats magnitude on 4/4 Qwen seeds at "
            "kr=0.5/layer=2; Gemma N=10 codec_novel_coded smoke is 6/10 vs "
            "magnitude 4/10; TOMATO motion remains low-headroom with codec_novel_coded "
            "5/30 vs magnitude 4/30. Sidecar equivalence gates: Qwen 8f, "
            "Qwen 16f, and Gemma 8f all have zero choice/correctness/kept-count "
            "drift; H.264 score loading drops from 16.8-23.8s/item live PyAV "
            "to 0.001-0.005s/item sidecar load."
        ),
        target_to_beat=(
            "promote only as bounded point-estimate evidence: cross-family and "
            "multi-seed controls are directionally supportive, TOMATO is a boundary, "
            "and no net wall-clock speedup is claimable unless codec metadata "
            "extraction is precomputed or decoder-integrated"
        ),
        e2e_policy="report component and E2E separately; no multiplied speedups",
        local_reproduction=(
            "research/experiments/2026/artifacts/phase1_51V_ov6_n57_kr070_l2/ "
            "and phase1_51V_ov6_n57_kr050_l8/; statistical audit in "
            "onevision_vlmaxxing_plan/ov6_track_b_statistical_audit.json; follow-up "
            "artifacts in phase1_51V_ov6_random_multiseed/, "
            "phase1_63G_ov6_gemma_codec_smoke/, and "
            "phase1_51V_ov6_tomato_motion_kr070_l2/ with TOMATO statistical_audit.json; "
            "sidecar gates in phase1_51V_ov6_sidecar_equivalence/, "
            "phase1_51V_ov6_sidecar_equivalence_f16/, and "
            "phase1_63G_ov6_gemma_sidecar_equivalence/"
        ),
        planned_gate=(
            "M3 follow-up gates completed; M5 is for broader confirmation only after "
            "a fresh preregistered power/transfer question"
        ),
        artifact_or_source="OV-6 Qwen M3 artifacts and statistical audit",
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
        status="reproduced here (artifact-level accounting)",
        intervention_layer="codec-sparse ingest plus same-video state reuse",
        denominator=(
            "two lanes: first-query vision tokens; follow-up setup-inclusive session wall-clock"
        ),
        primary_metric="lane-separated stage-share ceiling, session speedup, paired drift",
        headline_numeric=(
            "OV-8 accounting with Qwen codec_novel_coded kr=0.7/layer=2 first query: "
            "model-side sparse first query is 33.3s vs dense 38.7s; including current "
            "PyAV extraction it is 52.1s; first-query correctness drift is 12/57 versus "
            "dense. With existing C-PERSIST horizon-50 followups, setup-inclusive "
            "speedups remain positive by Q>=2 under included extraction for "
            "adaptive_post_q2/refresh10, but this is not a live combined run."
        ),
        target_to_beat=(
            "live combined runtime only after a fidelity-clean first-query sparse cell "
            "or a preregistered accuracy/speed trade-off justifies a fresh protocol; "
            "keep included/excluded codec-extraction denominators separate"
        ),
        e2e_policy="only report measured E2E when Track B backend skips real work",
        local_reproduction=(
            "research/experiments/2026/artifacts/onevision_cpersist_session/accounting.json"
        ),
        planned_gate=("accounting-only result; live session requires a separate preregistered run"),
        artifact_or_source="OV-8 artifact-level accounting",
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
