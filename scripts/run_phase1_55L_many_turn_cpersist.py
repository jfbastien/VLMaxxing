#!/usr/bin/env python3
"""Phase 1.55L — many-turn C-PERSIST horizon probe.

This extends the existing same-video follow-up protocol beyond the three-query
VideoMME sessions by cycling the per-video question bank for 10/20/50 turns.
It is intentionally not a conversational-history benchmark: the dense control
and cached arms see the same stateless question sequence, so any drift is
attributable to cache policy rather than accumulated chat text.
"""

from __future__ import annotations

import argparse
import gc
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import mlx.core as mx
import numpy as np
from mlx_vlm import load

mx.set_memory_limit(12 * 1024**3)

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_kv_cache_session import _peak_rss_gb, _run_query  # noqa: E402
from run_kv_selective_reprefill_v2 import (  # noqa: E402
    DEFAULT_MODEL_PATH,
    DEFAULT_SHORT_VIDEO_IDS,
    QWEN_IMAGE_TOKEN_ID,
    _is_pathological_like_response,
    _load_videomme_rows,
    _prepare_sample,
    _questions_for_video_id,
    _score_answer,
)

from codec_through.qwen_selective_reprefill import (  # noqa: E402
    common_prefix_token_count,
    compute_qwen_position_ids,
    compute_qwen_reprefill_plan,
    compute_qwen_token_cut_plan,
    generate_qwen_tail_with_explicit_positions,
    make_qwen_prefix_cache,
    rewind_qwen_prefix_cache,
    slice_qwen_prompt_for_reprefill,
)

DEFAULT_OUTPUT_DIR = Path("research/experiments/2026/artifacts/phase1_55L_many_turn_cpersist")


def _jsonl_write(handle: Any, row: dict[str, Any]) -> None:
    handle.write(json.dumps(row, sort_keys=True) + "\n")
    handle.flush()


def _spatial_merge_size(model: Any) -> int:
    vision_config = getattr(model, "vision_config", None)
    if vision_config is not None and hasattr(vision_config, "spatial_merge_size"):
        return int(vision_config.spatial_merge_size)
    config_vision = getattr(getattr(model, "config", None), "vision_config", None)
    if isinstance(config_vision, dict):
        return int(config_vision.get("spatial_merge_size", 2))
    if config_vision is not None and hasattr(config_vision, "spatial_merge_size"):
        return int(config_vision.spatial_merge_size)
    return 2


def _build_k_cache(
    *,
    model: Any,
    sample: Any,
    reprefill_k: int,
    image_token_id: int,
    spatial_merge_size: int,
) -> tuple[list[Any], float, Any, np.ndarray, np.ndarray]:
    position_ids = compute_qwen_position_ids(
        model=model,
        input_ids=sample.input_ids,
        image_grid_thw=sample.extra_kwargs["image_grid_thw"],
        mask=sample.mask,
    )
    plan = compute_qwen_reprefill_plan(
        input_ids=sample.input_ids.flatten().tolist(),
        image_grid_thw=np.asarray(sample.extra_kwargs["image_grid_thw"].tolist(), dtype=np.int64),
        reprefill_k=reprefill_k,
        image_token_id=image_token_id,
        spatial_merge_size=spatial_merge_size,
    )
    prefix, _tail = slice_qwen_prompt_for_reprefill(
        input_ids=sample.input_ids,
        mask=sample.mask,
        pixel_values=sample.pixel_values,
        image_grid_thw=sample.extra_kwargs["image_grid_thw"],
        position_ids=position_ids,
        plan=plan,
    )
    cache, build_ms = make_qwen_prefix_cache(model=model, prefix=prefix)
    prefix_ids = np.asarray(prefix.input_ids.tolist(), dtype=np.int64)
    prefix_grid = np.asarray(prefix.image_grid_thw.tolist(), dtype=np.int64)
    return cache, build_ms, plan, prefix_ids, prefix_grid


def _run_k1_turn(
    *,
    model: Any,
    processor: Any,
    sample: Any,
    base_cache: list[Any],
    base_plan: Any,
    base_prefix_ids: np.ndarray,
    base_prefix_grid: np.ndarray,
    image_token_id: int,
    spatial_merge_size: int,
    max_tokens: int,
    temperature: float,
    top_p: float,
    min_p: float,
    seed: int,
) -> tuple[dict[str, Any], Any]:
    position_ids = compute_qwen_position_ids(
        model=model,
        input_ids=sample.input_ids,
        image_grid_thw=sample.extra_kwargs["image_grid_thw"],
        mask=sample.mask,
    )
    plan = compute_qwen_reprefill_plan(
        input_ids=sample.input_ids.flatten().tolist(),
        image_grid_thw=np.asarray(sample.extra_kwargs["image_grid_thw"].tolist(), dtype=np.int64),
        reprefill_k=1,
        image_token_id=image_token_id,
        spatial_merge_size=spatial_merge_size,
    )
    prefix, tail = slice_qwen_prompt_for_reprefill(
        input_ids=sample.input_ids,
        mask=sample.mask,
        pixel_values=sample.pixel_values,
        image_grid_thw=sample.extra_kwargs["image_grid_thw"],
        position_ids=position_ids,
        plan=plan,
    )
    prefix_ids = np.asarray(prefix.input_ids.tolist(), dtype=np.int64)
    prefix_grid = np.asarray(prefix.image_grid_thw.tolist(), dtype=np.int64)
    if plan.trunc_token_idx != base_plan.trunc_token_idx:
        raise RuntimeError("K=1 truncation moved across many-turn replay")
    if not np.array_equal(prefix_ids, base_prefix_ids):
        raise RuntimeError("K=1 text/image prefix changed across many-turn replay")
    if not np.array_equal(prefix_grid, base_prefix_grid):
        raise RuntimeError("K=1 image-grid prefix changed across many-turn replay")
    result = generate_qwen_tail_with_explicit_positions(
        model=model,
        processor=processor,
        prompt_cache=base_cache,
        tail=tail,
        full_prompt_tokens=int(sample.input_ids.shape[1]),
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        min_p=min_p,
        seed=seed,
    )
    return result, plan


def _run_k0_turn(
    *,
    model: Any,
    processor: Any,
    sample: Any,
    repaired_cache: list[Any],
    previous_input_ids: np.ndarray,
    previous_prompt_tokens: int,
    previous_generation_tokens: int,
    image_token_id: int,
    spatial_merge_size: int,
    max_tokens: int,
    temperature: float,
    top_p: float,
    min_p: float,
    seed: int,
) -> tuple[dict[str, Any], Any, int]:
    position_ids = compute_qwen_position_ids(
        model=model,
        input_ids=sample.input_ids,
        image_grid_thw=sample.extra_kwargs["image_grid_thw"],
        mask=sample.mask,
    )
    current_input_ids = np.asarray(sample.input_ids.tolist(), dtype=np.int64).reshape(-1)
    shared_prefix_tokens = common_prefix_token_count(previous_input_ids, current_input_ids)
    if shared_prefix_tokens <= 0:
        raise RuntimeError("many-turn K=0 replay found no shared prefix")
    plan = compute_qwen_token_cut_plan(
        input_ids=current_input_ids,
        image_grid_thw=np.asarray(sample.extra_kwargs["image_grid_thw"].tolist(), dtype=np.int64),
        trunc_token_idx=shared_prefix_tokens,
        image_token_id=image_token_id,
        spatial_merge_size=spatial_merge_size,
    )
    _prefix, tail = slice_qwen_prompt_for_reprefill(
        input_ids=sample.input_ids,
        mask=sample.mask,
        pixel_values=sample.pixel_values,
        image_grid_thw=sample.extra_kwargs["image_grid_thw"],
        position_ids=position_ids,
        plan=plan,
    )
    rewind_qwen_prefix_cache(
        prompt_cache=repaired_cache,
        appended_prompt_tokens=previous_prompt_tokens - shared_prefix_tokens,
        appended_generation_tokens=previous_generation_tokens,
    )
    result = generate_qwen_tail_with_explicit_positions(
        model=model,
        processor=processor,
        prompt_cache=repaired_cache,
        tail=tail,
        full_prompt_tokens=int(sample.input_ids.shape[1]),
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        min_p=min_p,
        seed=seed,
    )
    return result, plan, shared_prefix_tokens


def _summarize_cell(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    n = len(rows)
    choice_drift = sum(1 for row in rows if row["choice_drift"])
    correctness_drift = sum(1 for row in rows if row["correctness_drift"])
    pathological = sum(1 for row in rows if row["pathological"])
    elapsed = [float(row["elapsed_ms"]) for row in rows]
    total_elapsed = [float(row["total_elapsed_ms"]) for row in rows]
    return {
        "n": n,
        "choice_drift": choice_drift,
        "choice_drift_rate": choice_drift / n,
        "correctness_drift": correctness_drift,
        "correctness_drift_rate": correctness_drift / n,
        "pathological": pathological,
        "pathological_rate": pathological / n,
        "median_elapsed_ms": statistics.median(elapsed),
        "median_total_elapsed_ms": statistics.median(total_elapsed),
        "max_peak_memory_gb": max(float(row["peak_memory_gb"]) for row in rows),
    }


def _bucket_summaries(rows: list[dict[str, Any]], bucket_size: int = 10) -> list[dict[str, Any]]:
    if not rows:
        return []
    max_turn = max(int(row["turn_index"]) for row in rows)
    out: list[dict[str, Any]] = []
    for start in range(0, max_turn + 1, bucket_size):
        end = start + bucket_size
        bucket = [row for row in rows if start <= int(row["turn_index"]) < end]
        if not bucket:
            continue
        payload = _summarize_cell(bucket)
        payload["turn_start"] = start
        payload["turn_end_exclusive"] = end
        out.append(payload)
    return out


def _expected_post_repair_rows(policy: str, horizon: int, n_videos: int) -> int:
    if policy == "fixed_k1" or horizon <= 1:
        return 0
    if policy == "adaptive_post_q2":
        return n_videos * max(horizon - 2, 0)
    if policy.startswith("refresh"):
        interval = int(policy.removeprefix("refresh"))
        k1_followup_turns = {1}
        k1_followup_turns.update(
            turn_index for turn_index in range(1, horizon) if turn_index % interval == 0
        )
        return n_videos * max((horizon - 1) - len(k1_followup_turns), 0)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video-ids", type=str, default=",".join(DEFAULT_SHORT_VIDEO_IDS))
    parser.add_argument("--turn-counts", type=str, default="10,20,50")
    parser.add_argument(
        "--policies",
        type=str,
        default="fixed_k1,adaptive_post_q2,refresh10",
        help="Comma-separated fixed_k1, adaptive_post_q2, refresh<N> policies.",
    )
    parser.add_argument("--frame-count", type=int, default=20)
    parser.add_argument("--max-tokens", type=int, default=32)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--min-p", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--rss-guard-mb", type=int, default=12000)
    args = parser.parse_args()

    video_ids = [vid.strip() for vid in args.video_ids.split(",") if vid.strip()]
    turn_counts = [int(value) for value in args.turn_counts.split(",") if value.strip()]
    policies = [value.strip() for value in args.policies.split(",") if value.strip()]
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1.55L] loading model from {args.model_path}")
    model, processor = load(str(args.model_path))
    spatial_merge_size = _spatial_merge_size(model)
    print(
        f"[1.55L] model loaded; videos={video_ids} turns={turn_counts} "
        f"policies={policies} frames={args.frame_count}"
    )

    rows = _load_videomme_rows()
    question_bank = {vid: _questions_for_video_id(vid, rows) for vid in video_ids}
    frame_cache: dict[str, Any] = {}
    t_start_ns = time.perf_counter_ns()

    baseline_path = args.output_dir / "baseline_many_turn.jsonl"
    session_path = args.output_dir / "session_many_turn.jsonl"
    paired_path = args.output_dir / "paired_many_turn.jsonl"
    summary_path = args.output_dir / "summary.json"

    baseline_by_key: dict[tuple[str, int, int], dict[str, Any]] = {}
    baseline_rows: list[dict[str, Any]] = []
    session_rows: list[dict[str, Any]] = []
    paired_rows: list[dict[str, Any]] = []

    # Baseline phase is stateless_question_cycle with a fixed seed: outputs only
    # depend on (vid, source_q_index). Compute each unique baseline once and
    # replicate the row per (horizon, turn_index) so the analyzer's pairing
    # logic (baseline_by_key[(vid, horizon, turn_index)]) is unchanged.
    unique_baselines: dict[tuple[str, int], dict[str, Any]] = {}
    n_unique_total = sum(len(question_bank[vid]) for vid in video_ids)
    n_unique_done = 0
    for vid in video_ids:
        questions = question_bank[vid]
        for source_q_index, item in enumerate(questions):
            sample = _prepare_sample(
                processor,
                item,
                frame_count=args.frame_count,
                frame_cache=frame_cache,
            )
            result = _run_query(
                model,
                processor,
                sample,
                max_tokens=args.max_tokens,
                prompt_cache_state=None,
                temperature=args.temperature,
                top_p=args.top_p,
                min_p=args.min_p,
                seed=args.seed,
            )
            choice, correct = _score_answer(result["text"], item)
            unique_baselines[(vid, source_q_index)] = {
                "video_id": vid,
                "duration": item.group,
                "source_q_index": source_q_index,
                "item_id": item.item_id,
                "choice": choice,
                "correct": correct,
                "response": str(result["text"]).strip()[:400],
                "elapsed_ms": float(result["elapsed_ms"]),
                "peak_memory_gb": float(result["peak_memory_gb"]),
                "pathological": _is_pathological_like_response(result["text"]),
            }
            n_unique_done += 1
            print(
                f"[1.55L] baseline unique {vid} q{source_q_index} "
                f"({n_unique_done}/{n_unique_total}): "
                f"{result['elapsed_ms']:.0f} ms correct={correct}"
            )
            check_memory_mb = _peak_rss_gb() * 1000
            if check_memory_mb > args.rss_guard_mb:
                raise MemoryError(
                    f"RSS guard exceeded: {check_memory_mb:.0f} MB > {args.rss_guard_mb} MB"
                )

    with baseline_path.open("w") as bf:
        for horizon in turn_counts:
            for vid in video_ids:
                questions = question_bank[vid]
                for turn_index in range(horizon):
                    source_q_index = turn_index % len(questions)
                    unique = unique_baselines[(vid, source_q_index)]
                    row = {
                        "mode": "baseline",
                        "history_mode": "stateless_question_cycle",
                        "horizon": horizon,
                        "turn_index": turn_index,
                        **unique,
                    }
                    key = (vid, horizon, turn_index)
                    baseline_by_key[key] = row
                    baseline_rows.append(row)
                    _jsonl_write(bf, row)

    with session_path.open("w") as sf, paired_path.open("w") as pf:
        for policy in policies:
            for horizon in turn_counts:
                for vid in video_ids:
                    questions = question_bank[vid]
                    fixed_base: tuple[list[Any], float, Any, np.ndarray, np.ndarray] | None = None
                    repaired_cache: list[Any] | None = None
                    repaired_input_ids: np.ndarray | None = None
                    repaired_prompt_tokens: int | None = None
                    repaired_generation_tokens: int | None = None
                    for turn_index in range(horizon):
                        item = questions[turn_index % len(questions)]
                        sample = _prepare_sample(
                            processor,
                            item,
                            frame_count=args.frame_count,
                            frame_cache=frame_cache,
                        )
                        base_cache_build_ms: float | None = None
                        shared_prefix_tokens: int | None = None
                        if turn_index == 0:
                            result = _run_query(
                                model,
                                processor,
                                sample,
                                max_tokens=args.max_tokens,
                                prompt_cache_state=None,
                                temperature=args.temperature,
                                top_p=args.top_p,
                                min_p=args.min_p,
                                seed=args.seed,
                            )
                            effective_k = 0
                            cache_source = "cold_q0"
                            tail_prompt_tokens = int(result["prompt_tokens"])
                        else:
                            refresh_interval: int | None = None
                            if policy.startswith("refresh"):
                                refresh_interval = int(policy.removeprefix("refresh"))
                            use_k1 = policy == "fixed_k1" or turn_index == 1
                            if refresh_interval is not None and turn_index % refresh_interval == 0:
                                use_k1 = True
                            if policy == "adaptive_post_q2" and turn_index > 1:
                                use_k1 = False

                            if use_k1:
                                fixed_base_was_created = fixed_base is not None
                                if policy == "fixed_k1":
                                    if fixed_base is None:
                                        fixed_base = _build_k_cache(
                                            model=model,
                                            sample=sample,
                                            reprefill_k=1,
                                            image_token_id=QWEN_IMAGE_TOKEN_ID,
                                            spatial_merge_size=spatial_merge_size,
                                        )
                                    (
                                        base_cache,
                                        base_cache_build_ms,
                                        base_plan,
                                        base_prefix_ids,
                                        base_prefix_grid,
                                    ) = fixed_base
                                    if fixed_base_was_created:
                                        base_cache_build_ms = None
                                else:
                                    (
                                        base_cache,
                                        base_cache_build_ms,
                                        base_plan,
                                        base_prefix_ids,
                                        base_prefix_grid,
                                    ) = _build_k_cache(
                                        model=model,
                                        sample=sample,
                                        reprefill_k=1,
                                        image_token_id=QWEN_IMAGE_TOKEN_ID,
                                        spatial_merge_size=spatial_merge_size,
                                    )
                                result, plan = _run_k1_turn(
                                    model=model,
                                    processor=processor,
                                    sample=sample,
                                    base_cache=base_cache,
                                    base_plan=base_plan,
                                    base_prefix_ids=base_prefix_ids,
                                    base_prefix_grid=base_prefix_grid,
                                    image_token_id=QWEN_IMAGE_TOKEN_ID,
                                    spatial_merge_size=spatial_merge_size,
                                    max_tokens=args.max_tokens,
                                    temperature=args.temperature,
                                    top_p=args.top_p,
                                    min_p=args.min_p,
                                    seed=args.seed,
                                )
                                if policy == "fixed_k1":
                                    rewind_qwen_prefix_cache(
                                        prompt_cache=base_cache,
                                        appended_prompt_tokens=plan.tail_prompt_tokens,
                                        appended_generation_tokens=int(result["generation_tokens"]),
                                    )
                                else:
                                    repaired_cache = base_cache
                                    repaired_input_ids = np.asarray(
                                        sample.input_ids.tolist(), dtype=np.int64
                                    ).reshape(-1)
                                    repaired_prompt_tokens = int(sample.input_ids.shape[1])
                                    repaired_generation_tokens = int(result["generation_tokens"])
                                effective_k = 1
                                cache_source = "reprefill_k=1"
                                tail_prompt_tokens = int(result["tail_prompt_tokens"])
                            else:
                                if (
                                    repaired_cache is None
                                    or repaired_input_ids is None
                                    or repaired_prompt_tokens is None
                                    or repaired_generation_tokens is None
                                ):
                                    raise RuntimeError(
                                        f"policy {policy} requested K=0 before a repaired "
                                        "cache was available"
                                    )
                                result, plan, shared_prefix_tokens = _run_k0_turn(
                                    model=model,
                                    processor=processor,
                                    sample=sample,
                                    repaired_cache=repaired_cache,
                                    previous_input_ids=repaired_input_ids,
                                    previous_prompt_tokens=repaired_prompt_tokens,
                                    previous_generation_tokens=repaired_generation_tokens,
                                    image_token_id=QWEN_IMAGE_TOKEN_ID,
                                    spatial_merge_size=spatial_merge_size,
                                    max_tokens=args.max_tokens,
                                    temperature=args.temperature,
                                    top_p=args.top_p,
                                    min_p=args.min_p,
                                    seed=args.seed,
                                )
                                repaired_input_ids = np.asarray(
                                    sample.input_ids.tolist(), dtype=np.int64
                                ).reshape(-1)
                                repaired_prompt_tokens = int(sample.input_ids.shape[1])
                                repaired_generation_tokens = int(result["generation_tokens"])
                                effective_k = 0
                                cache_source = "post_previous_repaired"
                                tail_prompt_tokens = int(result["tail_prompt_tokens"])

                        choice, correct = _score_answer(result["text"], item)
                        total_elapsed_ms = float(result["elapsed_ms"]) + float(
                            base_cache_build_ms or 0.0
                        )
                        row = {
                            "mode": "session",
                            "history_mode": "stateless_question_cycle",
                            "policy": policy,
                            "horizon": horizon,
                            "video_id": vid,
                            "duration": item.group,
                            "turn_index": turn_index,
                            "source_q_index": turn_index % len(questions),
                            "item_id": item.item_id,
                            "reprefill_k": effective_k,
                            "cache_source": cache_source,
                            "shared_prefix_tokens": shared_prefix_tokens,
                            "prompt_tokens": int(result["prompt_tokens"]),
                            "tail_prompt_tokens": tail_prompt_tokens,
                            "generation_tokens": int(result["generation_tokens"]),
                            "elapsed_ms": float(result["elapsed_ms"]),
                            "base_cache_build_ms": base_cache_build_ms,
                            "total_elapsed_ms": total_elapsed_ms,
                            "peak_memory_gb": float(result["peak_memory_gb"]),
                            "prefix_coverage": float(result["prefix_coverage"]),
                            "choice": choice,
                            "correct": correct,
                            "response": str(result["text"]).strip()[:400],
                            "pathological": _is_pathological_like_response(result["text"]),
                        }
                        session_rows.append(row)
                        _jsonl_write(sf, row)
                        base = baseline_by_key[(vid, horizon, turn_index)]
                        paired = {
                            **row,
                            "baseline_choice": base["choice"],
                            "baseline_correct": base["correct"],
                            "baseline_elapsed_ms": base["elapsed_ms"],
                            "choice_drift": row["choice"] != base["choice"],
                            "correctness_drift": row["correct"] != base["correct"],
                            "speedup_dense_over_session": (
                                float(base["elapsed_ms"]) / total_elapsed_ms
                                if total_elapsed_ms > 0
                                else None
                            ),
                        }
                        paired_rows.append(paired)
                        _jsonl_write(pf, paired)
                        print(
                            f"[1.55L] {policy} h={horizon} {vid} t={turn_index + 1}: "
                            f"{total_elapsed_ms:.0f} ms K={effective_k} "
                            f"choice_drift={paired['choice_drift']}"
                        )
                    gc.collect()

    cell_summaries: list[dict[str, Any]] = []
    for policy in policies:
        for horizon in turn_counts:
            rows_for_cell = [
                row for row in paired_rows if row["policy"] == policy and row["horizon"] == horizon
            ]
            followup_rows_for_cell = [row for row in rows_for_cell if int(row["turn_index"]) > 0]
            post_repair_rows_for_cell = [
                row for row in rows_for_cell if row.get("cache_source") == "post_previous_repaired"
            ]
            payload = _summarize_cell(rows_for_cell)
            payload["policy"] = policy
            payload["horizon"] = horizon
            payload["expected_n"] = len(video_ids) * horizon
            payload["expected_followup_only_n"] = len(video_ids) * max(horizon - 1, 0)
            payload["expected_post_repair_only_n"] = _expected_post_repair_rows(
                policy, horizon, len(video_ids)
            )
            payload["all_turns"] = _summarize_cell(rows_for_cell)
            payload["followup_only"] = _summarize_cell(followup_rows_for_cell)
            payload["post_repair_only"] = _summarize_cell(post_repair_rows_for_cell)
            payload["turn_buckets"] = _bucket_summaries(rows_for_cell)
            payload["followup_turn_buckets"] = _bucket_summaries(followup_rows_for_cell)
            payload["post_repair_turn_buckets"] = _bucket_summaries(post_repair_rows_for_cell)
            drift_basis = payload["followup_only"] or payload["all_turns"]
            payload["drift_gate_basis"] = (
                "followup_only" if payload["followup_only"] else "all_turns"
            )
            payload["pass_three_percent_drift_all_turns"] = (
                payload["all_turns"].get("choice_drift_rate", 1.0) <= 0.03
                and payload["all_turns"].get("correctness_drift_rate", 1.0) <= 0.03
            )
            payload["pass_three_percent_drift_followup_only"] = (
                payload["followup_only"].get("choice_drift_rate", 1.0) <= 0.03
                and payload["followup_only"].get("correctness_drift_rate", 1.0) <= 0.03
            )
            payload["pass_three_percent_drift_post_repair_only"] = not payload[
                "post_repair_only"
            ] or (
                payload["post_repair_only"].get("choice_drift_rate", 1.0) <= 0.03
                and payload["post_repair_only"].get("correctness_drift_rate", 1.0) <= 0.03
            )
            payload["pass_three_percent_drift"] = (
                drift_basis.get("choice_drift_rate", 1.0) <= 0.03
                and drift_basis.get("correctness_drift_rate", 1.0) <= 0.03
            )
            payload["cliff_bucket_detected"] = any(
                bucket.get("choice_drift_rate", 0.0) > 0.10
                or bucket.get("correctness_drift_rate", 0.0) > 0.10
                for bucket in payload["followup_turn_buckets"]
            )
            cell_summaries.append(payload)

    longest_safe_by_policy: dict[str, int | None] = {}
    for policy in policies:
        safe = [
            int(cell["horizon"])
            for cell in cell_summaries
            if cell["policy"] == policy and cell["pass_three_percent_drift"]
        ]
        longest_safe_by_policy[policy] = max(safe) if safe else None

    expected_baseline_rows = len(video_ids) * sum(turn_counts)
    expected_session_rows = len(policies) * expected_baseline_rows
    expected_paired_rows = expected_session_rows
    expected_cell_count = len(policies) * len(turn_counts)
    expected_cell_rows = {
        (policy, horizon): len(video_ids) * horizon
        for policy in policies
        for horizon in turn_counts
    }
    expected_policy_horizon_grid = {
        (policy, horizon) for policy in policies for horizon in turn_counts
    }
    observed_policy_horizon_grid = {
        (str(cell["policy"]), int(cell["horizon"])) for cell in cell_summaries
    }
    pass_complete_cells = (
        len(cell_summaries) == expected_cell_count
        and all(
            int(cell.get("n", -1)) == expected_cell_rows[(cell["policy"], int(cell["horizon"]))]
            for cell in cell_summaries
        )
        and all(
            int(cell.get("followup_only", {}).get("n", -1))
            == len(video_ids) * (int(cell["horizon"]) - 1)
            for cell in cell_summaries
        )
        and all(
            int(cell.get("post_repair_only", {}).get("n", 0))
            == int(cell["expected_post_repair_only_n"])
            for cell in cell_summaries
        )
    )
    baseline_chains = {(str(row["video_id"]), int(row["horizon"])) for row in baseline_rows}
    session_chains = {
        (str(row["policy"]), str(row["video_id"]), int(row["horizon"])) for row in session_rows
    }
    paired_chains = {
        (str(row["policy"]), str(row["video_id"]), int(row["horizon"])) for row in paired_rows
    }
    pass_complete_row_counts = (
        len(baseline_rows) == expected_baseline_rows
        and len(session_rows) == expected_session_rows
        and len(paired_rows) == expected_paired_rows
    )
    pass_complete_chain_counts = (
        len(baseline_chains) == len(video_ids) * len(turn_counts)
        and len(session_chains) == len(policies) * len(video_ids) * len(turn_counts)
        and len(paired_chains) == len(policies) * len(video_ids) * len(turn_counts)
    )
    pass_complete_policy_horizon_grid = observed_policy_horizon_grid == expected_policy_horizon_grid
    pass_complete_turn_coverage = all(
        {
            int(row["turn_index"])
            for row in paired_rows
            if row["policy"] == policy and row["video_id"] == vid and int(row["horizon"]) == horizon
        }
        == set(range(horizon))
        for policy in policies
        for vid in video_ids
        for horizon in turn_counts
    )
    pass_complete_horizon_policy_grid = (
        pass_complete_row_counts
        and pass_complete_cells
        and pass_complete_chain_counts
        and pass_complete_turn_coverage
        and pass_complete_policy_horizon_grid
    )

    summary = {
        "phase": "1.55L",
        "history_mode": "stateless_question_cycle",
        "frame_count": args.frame_count,
        "turn_counts": turn_counts,
        "policies": policies,
        "video_ids": video_ids,
        "sampling": {
            "temperature": args.temperature,
            "top_p": args.top_p,
            "min_p": args.min_p,
            "seed": args.seed,
        },
        "max_tokens": args.max_tokens,
        "n_baseline_rows": len(baseline_rows),
        "n_session_rows": len(session_rows),
        "n_paired_rows": len(paired_rows),
        "expected_baseline_rows": expected_baseline_rows,
        "expected_session_rows": expected_session_rows,
        "expected_paired_rows": expected_paired_rows,
        "expected_cell_count": expected_cell_count,
        "n_baseline_chains": len(baseline_chains),
        "n_session_chains": len(session_chains),
        "n_paired_chains": len(paired_chains),
        "pass_complete_row_counts": pass_complete_row_counts,
        "pass_complete_cells": pass_complete_cells,
        "pass_complete_chain_counts": pass_complete_chain_counts,
        "pass_complete_turn_coverage": pass_complete_turn_coverage,
        "pass_complete_policy_horizon_grid": pass_complete_policy_horizon_grid,
        "pass_complete_horizon_policy_grid": pass_complete_horizon_policy_grid,
        "longest_safe_horizon_by_policy": longest_safe_by_policy,
        "cells": cell_summaries,
        "paths": {
            "baseline_jsonl": baseline_path.as_posix(),
            "session_jsonl": session_path.as_posix(),
            "paired_jsonl": paired_path.as_posix(),
        },
        "wall_time_s": (time.perf_counter_ns() - t_start_ns) / 1e9,
        "peak_rss_gb": _peak_rss_gb(),
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(f"[1.55L] wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
