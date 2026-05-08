#!/usr/bin/env python3
# ruff: noqa: E501,I001
"""Emit the sequential OneVision + VLMaxxing experiment schedule.

This script is intentionally a planner, not an executor. It records the order,
gates, skip rules, compute lane, and setup effort so a later runner can consume
the JSON without risking model or GPU work during planning.
"""

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
    setup_effort: str
    eta_m3: str
    eta_m5: str
    compute_lane: str
    uses_local_accelerator: bool
    requires_nvidia: bool
    defer_until: str
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
                "A deterministic motion/residual Top-K allocator with full-frame anchors and THW visible indices "
                "reproduces the algorithmic surface needed for local tests."
            ),
            success_gate=(
                "Unit tests pass for anchors, budget overflow, stable tie-breaking, toy score localization, "
                "temporal coverage, spatial-bias diagnostics, and macroblock fusion projection invariants."
            ),
            skip_rule="If these tests fail, skip every downstream OneVision integration.",
            setup_effort="complete",
            eta_m3="< 10 minutes",
            eta_m5="< 10 minutes",
            compute_lane="CPU",
            uses_local_accelerator=False,
            requires_nvidia=False,
            defer_until="none",
            commands=[
                "uv run pytest tests/codec/test_onevision_patchification.py tests/codec/test_continuous_score.py",
            ],
            artifacts=[],
        ),
        ExperimentStep(
            stage="OV-1",
            track="visualization-method",
            question="Do codec scores allocate tokens sensibly on existing paper videos before any VLM inference?",
            hypothesis=(
                "Motion/residual fusion will expose whether anchor budget, temporal coverage, center bias, and edge/OCR "
                "starvation are sane enough to justify model runs."
            ),
            success_gate=(
                "Render token-allocation-over-time plus selected-patch overlays for the three established clips when "
                "raw source videos are present; scheduled evidence must fail closed when any source clip is missing."
            ),
            skip_rule=(
                "If raw videos are absent, restore benchmark assets first. Do not promote synthetic or generated-overlay "
                "artifacts as OV-1 evidence."
            ),
            setup_effort="real-video artifact path implemented; preflight checks source assets before render",
            eta_m3="3-6 hours with video extraction after assets are restored",
            eta_m5="1-3 hours with video extraction after assets are restored",
            compute_lane="CPU plus optional PyAV research dependency",
            uses_local_accelerator=False,
            requires_nvidia=False,
            defer_until="after OV-0",
            commands=[
                "uv run python scripts/preflight_onevision_vlmaxxing.py --scope ov1",
                "uv run python scripts/render_onevision_vlmaxxing_visual.py",
                "uv run python scripts/render_codec_through_video_overlays.py",
            ],
            artifacts=[
                "research/experiments/2026/artifacts/onevision_vlmaxxing_visuals/",
                "research/experiments/2026/artifacts/codec_through_video_overlays_exploratory/",
            ],
        ),
        ExperimentStep(
            stage="OV-2",
            track="implementation-wiring",
            question="Can OneVision-style fused scores be consumed by existing Track A planners?",
            hypothesis=(
                "The safest first runnable integration is a continuous-score adapter over existing H.264 metadata, "
                "not a new hard BlockStatistic label."
            ),
            success_gate=(
                "CLI flags, artifact schema, lazy-runtime guards, and regression tests exist for motion-only, "
                "residual-only, fused weighted, and max-age staleness gating in "
                "run_phase1_29_planner_accuracy_probe.py."
            ),
            skip_rule=(
                "If the adapter cannot reproduce existing Phase 1.29 codec-score behavior on cached/small inputs, "
                "do not start OV-3 model inference."
            ),
            setup_effort="implemented; pending final CPU-only checks and optional cached-input smoke",
            eta_m3="< 1 hour checks; no model run",
            eta_m5="< 1 hour checks; no model run",
            compute_lane="CPU",
            uses_local_accelerator=False,
            requires_nvidia=False,
            defer_until="after OV-1 visual sanity or explicit override",
            commands=[
                "uv run pytest tests/codec/test_continuous_score.py tests/codec/test_onevision_patchification.py",
                "uv run python scripts/run_phase1_29_planner_accuracy_probe.py --help",
            ],
            artifacts=[
                "research/experiments/2026/artifacts/onevision_track_a_wiring/",
            ],
        ),
        ExperimentStep(
            stage="OV-3",
            track="Track A dev",
            question="Does OneVision-style scoring improve semantic substitution before real work is skipped?",
            hypothesis=(
                "Continuous motion+residual scoring with per-item calibration will beat pixel max_abs and motion-only/"
                "residual-only ablations on paired answer stability at matched fresh budgets."
            ),
            success_gate=(
                "No increase in parse failures, <= 1% paired-choice drift on gated dev cells, and a strict Pareto "
                "improvement in fresh-budget versus current Track A baselines."
            ),
            skip_rule=(
                "If fused scoring underperforms pixel max_abs on the first dev tranche, skip holdout promotion, skip "
                "OV-4/OV-6 model runs, and report a diagnostic related-work result."
            ),
            setup_effort="requires OV-2 runner wiring",
            eta_m3="18-30 hours sequential after wiring",
            eta_m5="8-14 hours sequential after wiring",
            compute_lane="local MLX one model at a time",
            uses_local_accelerator=True,
            requires_nvidia=False,
            defer_until="after OV-2 passes",
            commands=[
                "uv run python scripts/run_phase1_29_planner_accuracy_probe.py --codec-score-source motion <dev args>",
                "uv run python scripts/run_phase1_29_planner_accuracy_probe.py --codec-score-source residual <dev args>",
                "uv run python scripts/run_phase1_29_planner_accuracy_probe.py --codec-score-source fused --fusion-mode weighted <dev args>",
                "uv run python scripts/run_benchmark_track_a.py <promoted onevision planner args>",
            ],
            artifacts=[
                "research/experiments/2026/artifacts/onevision_track_a_dev/",
            ],
        ),
        ExperimentStep(
            stage="OV-4",
            track="external-parity",
            question="Does the clean-room allocator agree with upstream OneVision preprocessing?",
            hypothesis=(
                "After matching frame sampling, padding, grid size, anchors, and budget, allocator selection should match "
                "upstream under identical score planes; independent residual-score correlation is expected to be weaker "
                "unless we use cv_reader or an equivalent codec-internal residual extractor."
            ),
            success_gate=(
                "Identical-score Jaccard >= 0.90 for selected positions; independent-extraction results reported with "
                "separate motion-only and residual-only correlations rather than a single brittle Spearman gate."
            ),
            skip_rule=(
                "Defer this until OV-3 dev passes. If it fails, debug sampling, padding, score normalization, cv_reader "
                "residuals, and I-frame policy one variable at a time."
            ),
            setup_effort=(
                "NVIDIA/Linux environment plus cv_reader patched-FFmpeg build; add 2-4 hours first-time dependency "
                "setup before the parity run"
            ),
            eta_m3="not feasible",
            eta_m5="not recommended; CUDA/cv_reader stack is the wrong target",
            compute_lane="NVIDIA Linux box or Lambda 1xH100/A100",
            uses_local_accelerator=False,
            requires_nvidia=True,
            defer_until="after OV-3 dev passes",
            commands=[
                "external: run upstream stage1/stage2 in an isolated NVIDIA/Linux environment",
                "external: compare upstream visidx_thw.npy and positions_thw.npy against clean-room visible indices",
            ],
            artifacts=[
                "research/experiments/2026/artifacts/onevision_parity_oracle/",
            ],
        ),
        ExperimentStep(
            stage="OV-5",
            track="Track A holdout",
            question="Does a dev-positive fused codec planner transfer to holdout and cross-family slices?",
            hypothesis=(
                "If OneVision-style scoring is real rather than calibration noise, it should survive duration buckets, "
                "benchmark splits, and at least one cross-family check."
            ),
            success_gate=(
                "Holdout cells remain parse-clean, preserve paired correctness within gate, and improve or match the "
                "current Track A Pareto frontier."
            ),
            skip_rule="If holdout regresses, do not promote as a paper result; preserve as a bounded diagnostic.",
            setup_effort="requires OV-3 dev pass",
            eta_m3="+12 hours Qwen/Gemma after dev",
            eta_m5="+6 hours Qwen/Gemma after dev",
            compute_lane="local MLX one model at a time",
            uses_local_accelerator=True,
            requires_nvidia=False,
            defer_until="after OV-3 dev passes",
            commands=[
                "uv run python scripts/run_benchmark_track_a.py <onevision-holdout args>",
            ],
            artifacts=[
                "research/experiments/2026/artifacts/onevision_track_a_holdout/",
            ],
        ),
        ExperimentStep(
            stage="OV-6",
            track="Track B",
            question="Can OneVision-style allocation improve real sparse vision work skipped?",
            hypothesis=(
                "Within already-fresh VLMaxxing regions, OneVision-style Top-K patch allocation may recover more task "
                "fidelity per token than current magnitude_norm keep-rate policies, but frozen towers are likely brittle."
            ),
            success_gate=(
                "At matched keep-rate, improve paired correctness/format over Phase 1.63J Qwen and Phase 1.63G Gemma "
                "boundaries while preserving measured vision-stage timing gains."
            ),
            skip_rule=(
                "If the first Qwen dev tranche fails fidelity at all keep-rates, skip Gemma and treat the result as "
                "evidence that trained sparse encoders are needed."
            ),
            setup_effort="requires OV-3/OV-5 evidence and separate sparse-tower scorer wiring",
            eta_m3="not recommended for broad sweeps",
            eta_m5="16-28 hours Qwen, +12 hours Gemma only if Qwen gates",
            compute_lane="M5 128GB preferred; no concurrent model jobs",
            uses_local_accelerator=True,
            requires_nvidia=False,
            defer_until="after OV-5 or explicit high-risk override",
            commands=[
                "uv run python scripts/run_phase1_51V.py <onevision-allocator args>",
                "uv run python scripts/run_phase1_63G_gemma_track_b.py <onevision-allocator args>",
            ],
            artifacts=[
                "research/experiments/2026/artifacts/onevision_track_b_sparse/",
            ],
        ),
        ExperimentStep(
            stage="OV-7",
            track="OV-Encoder local feasibility",
            question="Should OV-Encoder itself become a third local model family?",
            hypothesis=(
                "OV-Encoder can be a third vision-encoder probe locally, but it is not a third VLM comparable to Qwen/Gemma "
                "until an LMM head or probe stack is reproduced."
            ),
            success_gate=(
                "When the machine is free, run PyTorch/MPS or MLX-parity smoke on image and sparse-video encoder outputs; "
                "treat output-shape/parity as feasibility evidence, not QA accuracy."
            ),
            skip_rule=(
                "Skip if it requires flash-attention/CUDA for inference or if eager attention at target token counts exceeds "
                "local memory; move to NVIDIA only if encoder probes answer a paper-relevant question."
            ),
            setup_effort=(
                "1-3 days for PyTorch/MPS feasibility with load plus single-clip forward parity; "
                "about 1 calendar week for a careful MLX port with weight conversion, 3D RoPE parity, "
                "and single-clip forward parity"
            ),
            eta_m3="defer until machine free; smoke only",
            eta_m5="defer until machine free; smoke plus small probes",
            compute_lane="local encoder-only first; NVIDIA only for official stack",
            uses_local_accelerator=True,
            requires_nvidia=False,
            defer_until="after OV-1/OV-3 clarifies paper value",
            commands=[
                "manual future: transformers eager-attention smoke without flash_attention_2",
                "manual future: MLX weight-conversion parity smoke if PyTorch/MPS is too slow",
            ],
            artifacts=[
                "research/experiments/2026/artifacts/onevision_encoder_local_feasibility/",
            ],
        ),
        ExperimentStep(
            stage="OV-8",
            track="C-PERSIST",
            question="How do cold-ingest sparse allocation and follow-up reuse compose without double counting?",
            hypothesis=(
                "A OneVision-like cold ingest can reduce first-query vision work, while C-PERSIST dominates same-video "
                "follow-up latency; session-inclusive speedups must be reported by query count, not multiplied."
            ),
            success_gate=(
                "Report setup-inclusive session curves for 1, 2, 5, 10, and 50 same-video questions with paired drift and "
                "stage-share accounting."
            ),
            skip_rule=(
                "If OV-6 has no fidelity-clean sparse-vision cell, use synthetic stage-share ceilings only and do not claim "
                "a working combined runtime."
            ),
            setup_effort="requires OV-6 pass for model-backed runtime; otherwise accounting-only",
            eta_m3="6-10 hours accounting only; model run deferred",
            eta_m5="8-14 hours model-backed if OV-6 gates",
            compute_lane="M5 128GB for model-backed replication",
            uses_local_accelerator=True,
            requires_nvidia=False,
            defer_until="after OV-6 or as accounting-only after OV-5",
            commands=[
                "uv run python scripts/run_phase1_55L_many_turn_cpersist.py <combined args>",
                "uv run python scripts/build_c_persist_setup_inclusive.py <combined artifacts>",
            ],
            artifacts=[
                "research/experiments/2026/artifacts/onevision_cpersist_session/",
            ],
        ),
        ExperimentStep(
            stage="OV-9",
            track="comparison-table",
            question="How should OneVision, VLMaxxing, and combined techniques be compared without denominator drift?",
            hypothesis=(
                "A fixed comparison table with status labels and denominator columns will prevent imported patch "
                "compression, Track A answer stability, Track B timing, and C-PERSIST session savings from being "
                "collapsed into one speedup number."
            ),
            success_gate=(
                "Emit JSON/CSV/Markdown rows for OneVision imported results, local patchification reproduction, "
                "VLMaxxing baselines, fused Track A, sparse Track B, C-PERSIST, combined session accounting, and "
                "OV-Encoder feasibility, including headline_numeric and target_to_beat fields."
            ),
            skip_rule="If model results are absent, emit the preregistered plan table with hypothesis rows only.",
            setup_effort="implemented planning artifact; update after experiments complete",
            eta_m3="< 1 minute",
            eta_m5="< 1 minute",
            compute_lane="CPU/documentation",
            uses_local_accelerator=False,
            requires_nvidia=False,
            defer_until="after OV-0 for plan table; after OV-3/OV-8 for result-filled table",
            commands=[
                "uv run python scripts/build_onevision_vlmaxxing_comparison_table.py",
            ],
            artifacts=[
                "research/experiments/2026/artifacts/onevision_vlmaxxing_plan/comparison_table_plan.json",
                "research/experiments/2026/artifacts/onevision_vlmaxxing_plan/comparison_table_plan.csv",
                "research/experiments/2026/artifacts/onevision_vlmaxxing_plan/comparison_table_plan.md",
            ],
        ),
        ExperimentStep(
            stage="OV-10",
            track="paper-editor-feedback",
            question="What manuscript changes are justified after the evidence is in?",
            hypothesis=(
                "The editor-facing update will either add OneVision as trained codec-aligned related work plus diagnostic "
                "evidence, or promote a new combined runtime result only if Track B gates pass."
            ),
            success_gate=(
                "Prepare an editor memo listing imported OneVision claims, reproduced local claims, failed hypotheses, "
                "decision-log reopen status, and exact paper sections that should change."
            ),
            skip_rule="Do not edit manuscript prose until this memo is reviewed.",
            setup_effort="1-3 hours after artifacts exist",
            eta_m3="1-3 hours",
            eta_m5="1-3 hours",
            compute_lane="CPU/documentation",
            uses_local_accelerator=False,
            requires_nvidia=False,
            defer_until="after OV-3 through OV-9 outcomes are known",
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
        "concurrency_policy": "no concurrent model jobs; no model jobs while user benchmarks are active",
        "field_notes": {
            "uses_local_accelerator": "Apple MLX/MPS/GPU-style local acceleration may be used later; do not run now.",
            "requires_nvidia": "Requires NVIDIA/Linux/CUDA stack, not merely Apple Silicon local acceleration.",
        },
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
