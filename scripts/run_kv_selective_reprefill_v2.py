#!/usr/bin/env python3
"""Phase 1.55D v2 — Qwen selective re-prefill with explicit tail continuation."""

from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import mlx.core as mx
import numpy as np
from mlx_vlm import load
from mlx_vlm.utils import prepare_inputs

from codec_through.answers import extract_choice
from codec_through.qwen_selective_reprefill import (
    compute_qwen_position_ids,
    compute_qwen_reprefill_plan,
    generate_qwen_tail_with_explicit_positions,
    make_qwen_prefix_cache,
    rewind_qwen_prefix_cache,
    slice_qwen_prompt_for_reprefill,
)

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_benchmark_track_a import (  # noqa: E402
    DEFAULT_MODEL_PATH,
    BenchmarkItem,
    PreparedSample,
    _decode_uniform_frames,
    _find_videomme_video,
    _load_videomme_rows,
    _multiple_choice_prompt,
    _videomme_choice_text,
)
from run_kv_cache_session import _peak_rss_gb, _run_query  # noqa: E402

DEFAULT_SHORT_VIDEO_IDS: tuple[str, ...] = (
    "037",
    "100",
    "116",
    "120",
    "158",
    "160",
    "210",
)
DEFAULT_OUTPUT_DIR = Path("research/experiments/2026/artifacts/phase1_55D_selective_reprefill_v2")
QWEN_IMAGE_TOKEN_ID = 151655


@dataclass(frozen=True, slots=True)
class SessionClip:
    video_id: str
    duration: str
    questions: list[BenchmarkItem]


def _questions_for_video_id(video_id: str, rows: list[dict[str, Any]]) -> list[BenchmarkItem]:
    matching = [
        row
        for row in rows
        if str(row.get("video_id")) == video_id or str(row.get("videoID")) == video_id
    ]
    if len(matching) < 3:
        raise ValueError(f"expected ≥3 questions for video_id {video_id!r}, got {len(matching)}")

    def _q_suffix(row: dict[str, Any]) -> int:
        qid = str(row["question_id"])
        return int(qid.split("-")[-1])

    matching.sort(key=_q_suffix)
    items: list[BenchmarkItem] = []
    for row in matching[:3]:
        duration = str(row["duration"])
        video_id_str = str(row["videoID"])
        question_id = str(row["question_id"])
        raw_options = [str(opt) for opt in row["options"]]
        choices = [_videomme_choice_text(opt) for opt in raw_options]
        answer_letter = str(row["answer"]).strip().upper()
        answer_index = ord(answer_letter) - ord("A")
        question_text = str(row["question"])
        items.append(
            BenchmarkItem(
                item_id=f"videomme:{duration}:{question_id}",
                benchmark="videomme",
                group=duration,
                video_path=_find_videomme_video(video_id_str),
                question=_multiple_choice_prompt(question_text, choices),
                candidates=choices,
                answer_index=answer_index,
            )
        )
    return items


def _prepare_sample(
    processor: Any,
    item: BenchmarkItem,
    *,
    frame_count: int,
    frame_cache: dict[str, tuple[list[Any], list[tuple[int, int, int, int]]]],
) -> PreparedSample:
    if hasattr(processor, "image_processor"):
        if hasattr(processor.image_processor, "do_resize"):
            processor.image_processor.do_resize = False
        if hasattr(processor.image_processor, "do_image_splitting"):
            processor.image_processor.do_image_splitting = False
    video_key = str(item.video_path)
    if video_key not in frame_cache:
        frames, active_boxes = _decode_uniform_frames(
            item.video_path,
            frame_count=frame_count,
            start_seconds=item.start_seconds,
            end_seconds=item.end_seconds,
        )
        frame_cache[video_key] = (frames, active_boxes)
    frames, active_boxes = frame_cache[video_key]
    messages = [
        {
            "role": "user",
            "content": [
                *({"type": "image"} for _ in frames),
                {"type": "text", "text": item.question},
            ],
        }
    ]
    rendered_prompt = processor.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    raw_inputs = prepare_inputs(processor, images=frames, prompts=rendered_prompt)
    input_ids = mx.array(raw_inputs["input_ids"])
    pixel_values = mx.array(raw_inputs["pixel_values"])
    mask = mx.array(raw_inputs["attention_mask"])
    extra_kwargs = {
        key: mx.array(value)
        for key, value in raw_inputs.items()
        if key not in {"input_ids", "pixel_values", "attention_mask"}
    }
    return PreparedSample(
        item=item,
        frames=frames,
        active_boxes=active_boxes,
        input_ids=input_ids,
        pixel_values=pixel_values,
        mask=mask,
        extra_kwargs=extra_kwargs,
    )


def _score_answer(response_text: str, item: BenchmarkItem) -> tuple[str | None, bool]:
    letters = [chr(ord("A") + i) for i in range(len(item.candidates))]
    choice_index = extract_choice(response_text, letters)
    if choice_index is None:
        return None, False
    choice_letter = chr(ord("A") + choice_index)
    return choice_letter, choice_index == item.answer_index


def _summarise(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    if not rows:
        return {}
    elapsed = sorted(float(row["elapsed_ms"]) for row in rows)
    n_correct = sum(1 for row in rows if row["correct"])
    return {
        "label": key,
        "n": len(rows),
        "n_correct": n_correct,
        "accuracy": n_correct / len(rows),
        "mean_elapsed_ms": sum(elapsed) / len(elapsed),
        "median_elapsed_ms": elapsed[len(elapsed) // 2],
        "p05_elapsed_ms": elapsed[int(0.05 * (len(elapsed) - 1))],
        "p95_elapsed_ms": elapsed[int(0.95 * (len(elapsed) - 1))],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video-ids", type=str, default=",".join(DEFAULT_SHORT_VIDEO_IDS))
    parser.add_argument("--frame-count", type=int, default=20)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--reprefill-k", type=int, required=True)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--mode", choices=("session", "baseline", "both"), default="both")
    parser.add_argument("--temperature", type=float, default=0.0)
    args = parser.parse_args()

    if args.reprefill_k <= 0:
        raise SystemExit("--reprefill-k must be > 0")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = _load_videomme_rows()
    clips = [
        SessionClip(
            video_id=vid.strip(), duration="", questions=_questions_for_video_id(vid.strip(), rows)
        )
        for vid in args.video_ids.split(",")
        if vid.strip()
    ]
    clips = [
        SessionClip(
            video_id=clip.video_id, duration=clip.questions[0].group, questions=clip.questions
        )
        for clip in clips
    ]

    model, processor = load(str(args.model_path))
    if getattr(model.config, "model_type", None) != "qwen2_5_vl":
        raise SystemExit(
            f"run_kv_selective_reprefill_v2.py currently supports qwen2_5_vl only; got "
            f"{getattr(model.config, 'model_type', None)!r}"
        )

    image_token_id = getattr(model.config, "image_token_id", QWEN_IMAGE_TOKEN_ID)
    spatial_merge_size = int(model.config.vision_config.spatial_merge_size)
    frame_cache: dict[str, Any] = {}
    session_rows: list[dict[str, Any]] = []
    baseline_rows: list[dict[str, Any]] = []
    tag = f"k{args.reprefill_k}_n{len(clips)}"
    session_path = args.output_dir / f"session_{tag}.jsonl"
    baseline_path = args.output_dir / f"baseline_{tag}.jsonl"
    summary_path = args.output_dir / f"summary_{tag}.json"
    t_wall_start = time.perf_counter_ns()

    try:
        if args.mode in ("session", "both"):
            sf = open(session_path, "w")  # noqa: SIM115
        if args.mode in ("baseline", "both"):
            bf = open(baseline_path, "w")  # noqa: SIM115

        for clip in clips:
            print(f"[1.55D v2] clip {clip.video_id} duration={clip.duration}")
            if args.mode in ("session", "both"):
                base_cache = None
                base_cache_build_ms = None
                base_plan = None
                base_prefix_ids = None
                base_prefix_grid = None
                for q_index, item in enumerate(clip.questions):
                    sample = _prepare_sample(
                        processor,
                        item,
                        frame_count=args.frame_count,
                        frame_cache=frame_cache,
                    )
                    if q_index == 0:
                        # Q1 stays on the standard path; v2 targets follow-up recovery.
                        result = _run_query(
                            model,
                            processor,
                            sample,
                            max_tokens=args.max_tokens,
                            prompt_cache_state=None,
                            temperature=args.temperature,
                        )
                        full_position_ids = compute_qwen_position_ids(
                            model=model,
                            input_ids=sample.input_ids,
                            image_grid_thw=sample.extra_kwargs["image_grid_thw"],
                            mask=sample.mask,
                        )
                        plan = compute_qwen_reprefill_plan(
                            input_ids=sample.input_ids.flatten().tolist(),
                            image_grid_thw=np.asarray(
                                sample.extra_kwargs["image_grid_thw"].tolist(),
                                dtype=np.int64,
                            ),
                            reprefill_k=args.reprefill_k,
                            image_token_id=image_token_id,
                            spatial_merge_size=spatial_merge_size,
                        )
                        prefix, tail = slice_qwen_prompt_for_reprefill(
                            input_ids=sample.input_ids,
                            mask=sample.mask,
                            pixel_values=sample.pixel_values,
                            image_grid_thw=sample.extra_kwargs["image_grid_thw"],
                            position_ids=full_position_ids,
                            plan=plan,
                        )
                        full_prompt_tokens = int(sample.input_ids.shape[1])
                        base_cache, base_cache_build_ms = make_qwen_prefix_cache(
                            model=model,
                            prefix=prefix,
                        )
                        base_plan = plan
                        base_prefix_ids = np.asarray(prefix.input_ids.tolist(), dtype=np.int64)
                        base_prefix_grid = np.asarray(
                            prefix.image_grid_thw.tolist(),
                            dtype=np.int64,
                        )
                        generation_tokens = int(result["generation_tokens"])
                    else:
                        assert base_cache is not None
                        assert base_plan is not None
                        assert base_prefix_ids is not None
                        assert base_prefix_grid is not None
                        full_position_ids = compute_qwen_position_ids(
                            model=model,
                            input_ids=sample.input_ids,
                            image_grid_thw=sample.extra_kwargs["image_grid_thw"],
                            mask=sample.mask,
                        )
                        plan = compute_qwen_reprefill_plan(
                            input_ids=sample.input_ids.flatten().tolist(),
                            image_grid_thw=np.asarray(
                                sample.extra_kwargs["image_grid_thw"].tolist(),
                                dtype=np.int64,
                            ),
                            reprefill_k=args.reprefill_k,
                            image_token_id=image_token_id,
                            spatial_merge_size=spatial_merge_size,
                        )
                        prefix, tail = slice_qwen_prompt_for_reprefill(
                            input_ids=sample.input_ids,
                            mask=sample.mask,
                            pixel_values=sample.pixel_values,
                            image_grid_thw=sample.extra_kwargs["image_grid_thw"],
                            position_ids=full_position_ids,
                            plan=plan,
                        )
                        prefix_ids = np.asarray(prefix.input_ids.tolist(), dtype=np.int64)
                        prefix_grid = np.asarray(prefix.image_grid_thw.tolist(), dtype=np.int64)
                        if plan.trunc_token_idx != base_plan.trunc_token_idx:
                            raise RuntimeError(
                                "selective re-prefill truncation moved across follow-up "
                                f"queries for video_id={clip.video_id}: "
                                f"{plan.trunc_token_idx} != {base_plan.trunc_token_idx}"
                            )
                        if not np.array_equal(prefix_ids, base_prefix_ids):
                            raise RuntimeError(
                                "shared Qwen prefix differs across follow-up queries for "
                                f"video_id={clip.video_id}; refusing to reuse an "
                                "incompatible prefix cache"
                            )
                        if not np.array_equal(prefix_grid, base_prefix_grid):
                            raise RuntimeError(
                                "shared Qwen image-grid prefix differs across follow-up "
                                f"queries for video_id={clip.video_id}"
                            )
                        full_prompt_tokens = int(sample.input_ids.shape[1])
                        result = generate_qwen_tail_with_explicit_positions(
                            model=model,
                            processor=processor,
                            prompt_cache=base_cache,
                            tail=tail,
                            full_prompt_tokens=full_prompt_tokens,
                            max_tokens=args.max_tokens,
                            temperature=args.temperature,
                        )
                        generation_tokens = int(result["generation_tokens"])
                        rewind_qwen_prefix_cache(
                            prompt_cache=base_cache,
                            appended_prompt_tokens=plan.tail_prompt_tokens,
                            appended_generation_tokens=generation_tokens,
                        )

                    choice, correct = _score_answer(result["text"], item)
                    row = {
                        "mode": "session",
                        "video_id": clip.video_id,
                        "duration": clip.duration,
                        "item_id": item.item_id,
                        "q_index": q_index,
                        "prompt_tokens": int(result["prompt_tokens"]),
                        "tail_prompt_tokens": int(
                            result.get("tail_prompt_tokens", result["prompt_tokens"])
                        ),
                        "generation_tokens": generation_tokens,
                        "elapsed_ms": float(result["elapsed_ms"]),
                        "peak_memory_gb": float(result["peak_memory_gb"]),
                        "prefix_hit": int(result["prefix_hit"]),
                        "input_len": int(result["input_len"]),
                        "prefix_coverage": float(result["prefix_coverage"]),
                        "base_cache_build_ms": base_cache_build_ms if q_index == 0 else None,
                        "trunc_idx": plan.trunc_token_idx if plan is not None else None,
                        "reprefill_k": args.reprefill_k,
                        "response": str(result["text"]).strip()[:400],
                        "choice": choice,
                        "correct": correct,
                    }
                    session_rows.append(row)
                    sf.write(json.dumps(row) + "\n")
                    sf.flush()
                    print(
                        f"   session Q{q_index + 1}: {row['elapsed_ms']:.0f} ms "
                        f"prefix={row['prefix_coverage']:.2%} correct={correct}"
                    )
                del base_cache
                gc.collect()

            if args.mode in ("baseline", "both"):
                for q_index, item in enumerate(clip.questions):
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
                    )
                    choice, correct = _score_answer(result["text"], item)
                    row = {
                        "mode": "baseline",
                        "video_id": clip.video_id,
                        "duration": clip.duration,
                        "item_id": item.item_id,
                        "q_index": q_index,
                        "prompt_tokens": int(result["prompt_tokens"]),
                        "generation_tokens": int(result["generation_tokens"]),
                        "elapsed_ms": float(result["elapsed_ms"]),
                        "peak_memory_gb": float(result["peak_memory_gb"]),
                        "response": str(result["text"]).strip()[:400],
                        "choice": choice,
                        "correct": correct,
                    }
                    baseline_rows.append(row)
                    bf.write(json.dumps(row) + "\n")
                    bf.flush()
    finally:
        if args.mode in ("session", "both"):
            sf.close()
        if args.mode in ("baseline", "both"):
            bf.close()

    total_wall_ms = (time.perf_counter_ns() - t_wall_start) / 1_000_000
    session_follow = [row for row in session_rows if row["q_index"] > 0]
    follow_prefix = [float(row["prefix_coverage"]) for row in session_follow]
    summary = {
        "phase": "1.55D_v2",
        "model": args.model_path.name.lower(),
        "frame_count": args.frame_count,
        "reprefill_k": args.reprefill_k,
        "n_clips": len(clips),
        "n_queries_per_mode": 3 * len(clips),
        "total_wall_ms": total_wall_ms,
        "peak_rss_gb": _peak_rss_gb(),
        "session": _summarise(session_rows, "session"),
        "session_follow_up": _summarise(session_follow, "session_follow_up"),
        "baseline": _summarise(baseline_rows, "baseline"),
        "mean_follow_up_prefix_coverage": (
            sum(follow_prefix) / len(follow_prefix) if follow_prefix else 0.0
        ),
        "accuracy_delta_session_minus_baseline": (
            _summarise(session_rows, "session").get("accuracy", 0.0)
            - _summarise(baseline_rows, "baseline").get("accuracy", 0.0)
            if session_rows and baseline_rows
            else None
        ),
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"[1.55D v2] wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
