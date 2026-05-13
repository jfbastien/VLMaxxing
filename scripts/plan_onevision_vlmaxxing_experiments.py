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
                "uv run python scripts/render_onevision_vlmaxxing_explainer_videos.py",
            ],
            artifacts=[
                "research/experiments/2026/artifacts/onevision_vlmaxxing_visuals/",
                "research/experiments/2026/artifacts/onevision_vlmaxxing_explainer_videos/",
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
            question="Do codec-native score sources improve semantic substitution before real work is skipped?",
            hypothesis=(
                "Continuous H.264 score planes can be a better Track A refresh oracle than pixel max_abs at the "
                "matched fresh-budget point, but the best frozen-backend source may be a simple codec signal rather "
                "than OneVision-style weighted fusion."
            ),
            success_gate=(
                "For paper-facing promotion, require no parse-failure increase, no rows broken versus pixel, "
                "positive codec-minus-pixel point estimates on a replication tranche, and confidence intervals / "
                "McNemar reported instead of treating small-N wins as significance."
            ),
            skip_rule=(
                "If every codec source fails to beat pixel at matched budget, stop at diagnostic evidence. If fused "
                "does not beat simpler sources, carry the best simple source into OV-6 rather than treating fusion "
                "as the method."
            ),
            setup_effort="requires OV-2 runner wiring",
            eta_m3="24-40 hours sequential after wiring; cache keys intentionally separate score sources",
            eta_m5="12-24 hours sequential after wiring; cache keys intentionally separate score sources",
            compute_lane="local MLX one model at a time",
            uses_local_accelerator=True,
            requires_nvidia=False,
            defer_until="after OV-2 passes",
            commands=[
                "uv run python scripts/run_phase1_29_planner_accuracy_probe.py --codec-score-source novel_coded <dev args>",
                "uv run python scripts/run_phase1_29_planner_accuracy_probe.py --codec-score-source motion <dev args>",
                "uv run python scripts/run_phase1_29_planner_accuracy_probe.py --codec-score-source residual <dev args>",
                "uv run python scripts/run_phase1_29_planner_accuracy_probe.py --codec-score-source fused --fusion-mode weighted <dev args>",
                "uv run python scripts/run_benchmark_track_a.py <promoted onevision planner args>",
            ],
            artifacts=[
                "research/experiments/2026/artifacts/phase1_29_onevision_n57/",
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
            question="Does the codec-source Track A signal transfer beyond VideoMME short / 8 frames?",
            hypothesis=(
                "If codec-native scoring is real rather than a VideoMME-short operating-point artifact, it should "
                "survive at least one cross-benchmark or calibration-sensitivity test. Frame=16 already shows that "
                "the advantage over pixel does not automatically transfer across frame budgets."
            ),
            success_gate=(
                "Report TOMATO or larger-VideoMME results with Wilson intervals, paired tests, and explicit "
                "operating-point labels; promote only sources that remain parse-clean and do not break pixel-correct rows."
            ),
            skip_rule=(
                "If cross-benchmark or pooled-calibration sensitivity collapses to pixel or reverses correctness, "
                "keep OV-3 as bounded VideoMME-short evidence and do not generalize."
            ),
            setup_effort="requires OV-3 N=57 artifacts; no query-aware tuning in this branch",
            eta_m3="completed: TOMATO focused cell plus pooled calibration; future M3 only with a fresh prereg",
            eta_m5="future: 2-4 hours per focused replication cell only after fresh preregistration",
            compute_lane="completed on local MLX; M5 only for broader preregistered confirmation",
            uses_local_accelerator=True,
            requires_nvidia=False,
            defer_until="complete for current branch",
            commands=[
                "DONE: scripts/run_ov6_qwen_tomato_replication.sh",
                "DONE: uv run python scripts/analyze_ov6_tomato_motion.py",
                "DONE: scripts/run_ov3_h264_calibration_sensitivity.sh",
            ],
            artifacts=[
                "research/experiments/2026/artifacts/phase1_51V_ov6_tomato_motion_kr070_l2/",
                "research/experiments/2026/artifacts/phase1_51V_ov6_tomato_motion_kr070_l2/statistical_audit.json",
                "research/experiments/2026/artifacts/phase1_29_onevision_n57_pooled_calibration/",
            ],
        ),
        ExperimentStep(
            stage="OV-6",
            track="Track B",
            question="Can OneVision-style allocation improve real sparse vision work skipped?",
            hypothesis=(
                "The OV-3 Track A signal can become a systems result only at operating points where codec score "
                "grids preserve sparse-vision fidelity. Qwen shows bounded point-estimate Track B evidence, not a "
                "broad net wall-clock speedup after current PyAV extraction."
            ),
            success_gate=(
                "For Qwen, report as bounded point-estimate evidence unless paired tests gate; for Gemma, first "
                "gate on exact geometry/provenance and paired dense-vs-sparse format/fidelity before any "
                "cross-family claim."
            ),
            skip_rule=(
                "If Gemma one-item/short smoke shows geometry mismatch, stale codec-grid reuse, or paired "
                "format/fidelity regressions beyond the existing Gemma Track B caveat, stop Gemma and keep OV-6 "
                "as Qwen-only bounded evidence."
            ),
            setup_effort=(
                "Qwen codec-grid complete; Gemma codec-grid N=10 smoke complete; sidecar build/load path and "
                "M5 wrapper scripts added with provenance-clean output dirs"
            ),
            eta_m3=(
                "sidecar equivalence: Qwen 8f, Qwen 16f, and Gemma 8f small-N gates, expected under 1 hour each "
                "plus sidecar build; TOMATO kr=0.9 balanced smoke is a small diagnostic"
            ),
            eta_m5=(
                "focused confirmation only: Qwen parity 4-8h, Gemma kr=0.5 inversion 4-8h, Gemma N=57 codec "
                "transfer 4-8h, Qwen 16f boundary 6-10h"
            ),
            compute_lane=(
                "Qwen and Gemma M3 follow-ups complete; remaining M3 work is geometry-specific sidecar "
                "equivalence plus balanced TOMATO smoke, then focused M5 confirmation"
            ),
            uses_local_accelerator=True,
            requires_nvidia=False,
            defer_until=(
                "run matching M3 sidecar equivalence for each sidecar-backed M5 geometry/frame budget before M5; "
                "live OV-8 remains blocked by first-query drift policy"
            ),
            commands=[
                "DONE: scripts/run_ov6_full_sweep.sh",
                "DONE: scripts/run_ov6_n57_promotions.sh",
                "DONE: scripts/analyze_ov6_track_b.py",
                "DONE: scripts/run_ov6_gemma_codec_smoke.sh",
                "DONE: scripts/run_ov6_qwen_random_multiseed.sh",
                "DONE: scripts/run_ov6_qwen_tomato_replication.sh",
                "DONE: scripts/run_ov3_h264_calibration_sensitivity.sh",
                "NEXT M3: scripts/run_ov6_sidecar_equivalence.sh",
                "NEXT M3: OV6S_FRAME_COUNT=16 scripts/run_ov6_sidecar_equivalence.sh",
                "NEXT M3: scripts/run_ov6_gemma_sidecar_equivalence.sh",
                "NEXT M3: scripts/run_ov6_tomato_kr090_boundary_smoke.sh",
                "M5 gated: scripts/run_ov6_m5_qwen_parity.sh",
                "M5 gated: scripts/run_ov6_m5_gemma_kr05_inversion.sh",
                "M5 gated: scripts/run_ov6_m5_gemma_n57_confirmation.sh",
                "M5 gated: scripts/run_ov6_m5_qwen_frame16_boundary.sh",
            ],
            artifacts=[
                "research/experiments/2026/artifacts/phase1_51V_ov6_n57/",
                "research/experiments/2026/artifacts/phase1_51V_ov6_n57_kr070_l2/",
                "research/experiments/2026/artifacts/phase1_51V_ov6_n57_kr050_l8/",
                "research/experiments/2026/artifacts/onevision_vlmaxxing_plan/ov6_track_b_statistical_audit.json",
                "research/experiments/2026/artifacts/phase1_51V_ov6_random_multiseed/",
                "research/experiments/2026/artifacts/phase1_63G_ov6_gemma_codec_smoke/",
                "research/experiments/2026/artifacts/phase1_51V_ov6_tomato_motion_kr070_l2/",
                "research/experiments/2026/artifacts/phase1_51V_ov6_sidecar_equivalence/",
                "research/experiments/2026/artifacts/phase1_51V_ov6_sidecar_equivalence_f16/",
                "research/experiments/2026/artifacts/phase1_63G_ov6_gemma_sidecar_equivalence/",
                "research/experiments/2026/artifacts/phase1_51V_ov6_tomato_motion_kr090_l2_balanced_smoke/",
                "research/experiments/2026/artifacts/m5_ov6_qwen_n57_kr070_l2_parity/",
                "research/experiments/2026/artifacts/m5_ov6_gemma_n57_kr050_l2_random_multiseed/",
                "research/experiments/2026/artifacts/m5_ov6_gemma_n57_kr070_l2_confirmation/",
                "research/experiments/2026/artifacts/m5_ov6_qwen_n57_16f_kr070_l2_boundary/",
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
                "If first-query sparse-vs-dense drift remains material, use analytic stage-share ceilings only and do not "
                "claim fidelity-clean composition."
            ),
            setup_effort=(
                "artifact-level accounting exists; live composition needs a new session driver or explicit accuracy/speed "
                "tradeoff because current best codec cell has first-query drift"
            ),
            eta_m3="accounting complete; live run not recommended on M3 until fidelity policy is chosen",
            eta_m5="6-10 hours model-backed only after fresh preregistration and a first-query drift policy",
            compute_lane="M5 128GB for model-backed replication",
            uses_local_accelerator=True,
            requires_nvidia=False,
            defer_until="after explicit decision to accept first-query drift or after a fidelity-clean sparse cell appears",
            commands=[
                "DONE/accounting: uv run python scripts/build_c_persist_setup_inclusive.py <combined artifacts>",
                "future/live: uv run python scripts/run_phase1_55L_many_turn_cpersist.py <combined args>",
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
