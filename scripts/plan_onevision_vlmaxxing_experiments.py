#!/usr/bin/env python3
"""Emit the sequential OneVision + VLMaxxing experiment schedule.

This script is intentionally a planner, not an executor. It records the order,
gates, skip rules, and compute lane for the work so a later runner can consume
the JSON without risking model or GPU work during planning.
"""
# ruff: noqa: E501

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_OUTPUT = Path(
    "research/experiments/2026/artifacts/onevision_vlmaxxing_plan/experiment_schedule.json"
)


@dataclass(frozen=True, slots=True)
class ExperimentStep:
    stage: str
    track: str
    question: str
    hypothesis: str
    success_gate: str
    skip_rule: str
    eta_m3: str
    eta_m5: str
    compute_lane: str
    runs_models: bool
    requires_gpu: bool
    commands: list[str]
    artifacts: list[str]


def build_schedule() -> list[ExperimentStep]:
    """Return the preregistered sequential schedule."""

    return [
        ExperimentStep(
            stage="OV-0",
            track="reproduction-method",
            question="Can the clean-room patch allocator match OneVision's public codec input contract?",
            hypothesis=(
                "A deterministic motion/residual Top-K allocator with full-frame anchors and "
                "THW visible indices reproduces the algorithmic surface needed for local tests."
            ),
            success_gate=(
                "Unit tests pass for anchors, budget overflow, stable tie-breaking, synthetic "
                "motion localization, temporal coverage, and spatial-bias diagnostics."
            ),
            skip_rule="If these tests fail, skip every downstream OneVision integration.",
            eta_m3="< 10 minutes",
            eta_m5="< 10 minutes",
            compute_lane="CPU",
            runs_models=False,
            requires_gpu=False,
            commands=[
                "uv run pytest tests/codec/test_onevision_patchification.py",
            ],
            artifacts=[],
        ),
        ExperimentStep(
            stage="OV-1",
            track="reproduction-method",
            question="Do codec scores allocate tokens sensibly on local videos before any VLM inference?",
            hypothesis=(
                "Motion/residual fusion will place more sparse tokens on moving actors, text flashes, "
                "and camera-change boundaries than uniform frame sampling at the same token budget."
            ),
            success_gate=(
                "For the three existing visualization clips and a small benchmark subset, report "
                "token counts by frame, center/boundary fractions, temporal entropy, and overlays."
            ),
            skip_rule=(
                "If raw videos are absent, generate metadata-only/synthetic visualizations and defer "
                "real-video overlays until benchmark assets are restored."
            ),
            eta_m3="1-3 hours depending on codec metadata extraction",
            eta_m5="30-90 minutes",
            compute_lane="CPU plus optional PyAV research dependency",
            runs_models=False,
            requires_gpu=False,
            commands=[
                "uv run python scripts/render_onevision_vlmaxxing_visual.py",
                "uv run python scripts/run_phase1_29_planner_accuracy_probe.py --help",
            ],
            artifacts=[
                "research/experiments/2026/artifacts/onevision_vlmaxxing_visuals/",
            ],
        ),
        ExperimentStep(
            stage="OV-2",
            track="external-parity",
            question="Does the clean-room allocator agree with upstream OneVision preprocessing?",
            hypothesis=(
                "After matching sampled frames, padding policy, grid size, anchors, and budget, "
                "selected THW positions should be equivalent up to decoder and residual-proxy differences."
            ),
            success_gate=(
                "On 20-50 clips, Jaccard >= 0.90 for selected positions when the same score planes are "
                "used, and Spearman >= 0.85 for per-patch scores under independent extraction."
            ),
            skip_rule=(
                "If parity fails, stop model-facing claims and inspect frame sampling, padding, "
                "I-frame policy, and score normalization one variable at a time."
            ),
            eta_m3="not recommended",
            eta_m5="4-8 hours if upstream deps build",
            compute_lane="NVIDIA oracle preferred; CPU can validate only score-free invariants",
            runs_models=False,
            requires_gpu=True,
            commands=[
                "external: run upstream stage1/stage2 in an isolated checkout",
                "external: compare upstream visidx_thw.npy against clean-room visible indices",
            ],
            artifacts=[
                "research/experiments/2026/artifacts/onevision_parity_oracle/",
            ],
        ),
        ExperimentStep(
            stage="OV-3",
            track="Track A",
            question="Does OneVision-style scoring improve semantic substitution before real work is skipped?",
            hypothesis=(
                "Continuous motion+residual scoring with per-item calibration will beat pixel max_abs "
                "and motion-only/residual-only ablations on paired answer stability at matched budgets."
            ),
            success_gate=(
                "No increase in parse failures, <= 1% paired-choice drift on gated cells, and a "
                "strict Pareto improvement in fresh-budget versus current Track A baselines."
            ),
            skip_rule=(
                "If residual-only or fused scoring underperforms pixel max_abs on the first dev tranche, "
                "skip holdout promotion and keep it as a diagnostic related-work result."
            ),
            eta_m3="6-18 hours sequential, model-dependent",
            eta_m5="3-8 hours sequential",
            compute_lane="local MLX one model at a time",
            runs_models=True,
            requires_gpu=False,
            commands=[
                "uv run python scripts/run_phase1_29_planner_accuracy_probe.py <codec-ablation args>",
                "uv run python scripts/run_benchmark_track_a.py <promoted planner args>",
            ],
            artifacts=[
                "research/experiments/2026/artifacts/onevision_track_a_ablation/",
            ],
        ),
        ExperimentStep(
            stage="OV-4",
            track="Track B",
            question="Can OneVision-style allocation improve real sparse vision work skipped?",
            hypothesis=(
                "Within already-fresh VLMaxxing regions, OneVision-style Top-K patch allocation will "
                "recover more task fidelity per token than current magnitude_norm keep-rate policies."
            ),
            success_gate=(
                "At matched keep-rate, improve paired correctness/format over Phase 1.63J Qwen and "
                "Phase 1.63G Gemma boundaries while preserving measured vision-stage timing gains."
            ),
            skip_rule=(
                "If the first Qwen dev tranche fails fidelity at all keep-rates, skip Gemma and treat "
                "the result as a trained-encoder motivation rather than a frozen-backend claim."
            ),
            eta_m3="not recommended for broad sweeps",
            eta_m5="8-24 hours sequential",
            compute_lane="M5 128GB preferred; no concurrent model jobs",
            runs_models=True,
            requires_gpu=False,
            commands=[
                "uv run python scripts/run_phase1_51V.py <onevision-allocator args>",
                "uv run python scripts/run_phase1_63G_gemma_track_b.py <onevision-allocator args>",
            ],
            artifacts=[
                "research/experiments/2026/artifacts/onevision_track_b_sparse/",
            ],
        ),
        ExperimentStep(
            stage="OV-5",
            track="C-PERSIST",
            question="How do cold-ingest sparse allocation and follow-up reuse compose without double counting?",
            hypothesis=(
                "A OneVision-like cold ingest can reduce first-query vision work, while C-PERSIST "
                "dominates same-video follow-up latency; session-inclusive speedups must be reported "
                "by query count, not multiplied."
            ),
            success_gate=(
                "Report setup-inclusive session curves for 1, 2, 5, 10, and 50 same-video questions "
                "with paired drift and stage-share accounting."
            ),
            skip_rule=(
                "If OV-4 has no fidelity-clean sparse-vision cell, use synthetic stage-share ceilings "
                "only and do not claim a working combined runtime."
            ),
            eta_m3="2-6 hours for accounting only; model run deferred",
            eta_m5="4-12 hours sequential for model-backed replication",
            compute_lane="M5 128GB for model-backed replication",
            runs_models=True,
            requires_gpu=False,
            commands=[
                "uv run python scripts/run_phase1_55L_many_turn_cpersist.py <combined args>",
                "uv run python scripts/build_c_persist_setup_inclusive.py <combined artifacts>",
            ],
            artifacts=[
                "research/experiments/2026/artifacts/onevision_cpersist_session/",
            ],
        ),
        ExperimentStep(
            stage="OV-6",
            track="visualization",
            question="Can humans see the distinction between saliency, freshness, and cache reuse?",
            hypothesis=(
                "A four-stage OneVision-style explainer plus VLMaxxing fresh/reused overlays will make "
                "the denominator separation visually legible."
            ),
            success_gate=(
                "Render original/dense, codec-score, VLMaxxing reuse, and combined fresh-thinned panels "
                "for the three established videos or synthetic fallbacks, with separate token budgets."
            ),
            skip_rule=(
                "If raw videos are missing, publish synthetic/metadata figures only and mark real-video "
                "renders as blocked on local assets."
            ),
            eta_m3="< 1 hour synthetic; 1-3 hours with video extraction",
            eta_m5="< 1 hour synthetic; 30-90 minutes with video extraction",
            compute_lane="CPU",
            runs_models=False,
            requires_gpu=False,
            commands=[
                "uv run python scripts/render_onevision_vlmaxxing_visual.py",
                "uv run python scripts/render_codec_through_video_overlays.py",
            ],
            artifacts=[
                "research/experiments/2026/artifacts/onevision_vlmaxxing_visuals/",
                "research/experiments/2026/artifacts/codec_through_video_overlays_exploratory/",
            ],
        ),
        ExperimentStep(
            stage="OV-7",
            track="paper-editor-feedback",
            question="What manuscript changes are justified after the evidence is in?",
            hypothesis=(
                "The editor-facing update will either add OneVision as trained codec-aligned related "
                "work plus new negative/diagnostic evidence, or promote a new combined runtime result "
                "if Track B gates pass."
            ),
            success_gate=(
                "Prepare an editor memo listing imported OneVision claims, reproduced local claims, "
                "failed hypotheses, and exact paper sections that should change."
            ),
            skip_rule=(
                "Do not edit manuscript prose until OV-3 through OV-6 have completed and the editor "
                "feedback packet has been reviewed."
            ),
            eta_m3="1-2 hours after artifacts exist",
            eta_m5="1-2 hours after artifacts exist",
            compute_lane="CPU/documentation",
            runs_models=False,
            requires_gpu=False,
            commands=[
                "manual: draft editor feedback from completed artifacts",
            ],
            artifacts=[
                "research/experiments/2026/artifacts/onevision_editor_feedback/",
            ],
        ),
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--print-json", action="store_true")
    args = parser.parse_args()

    schedule = build_schedule()
    payload = {
        "name": "onevision_vlmaxxing_sequential_schedule",
        "concurrency_policy": "no concurrent GPU/model jobs; execute steps in listed order",
        "generated_by": Path(__file__).name,
        "steps": [asdict(step) for step in schedule],
    }
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8")
    if args.print_json:
        print(encoded, end="")
    else:
        print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
