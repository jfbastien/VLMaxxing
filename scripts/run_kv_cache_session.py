#!/usr/bin/env python3
"""Persistent KV-cache follow-up-latency session driver (Phase 1.55A).

Protocol from Sam whitepaper §2.13.3: per video, run N sequential
questions while threading ``PromptCacheState`` so the common
system+image+instruction prefix is reused across queries. We report
first-query vs. follow-up-query latency, prefix-hit coverage, accuracy
delta vs. cold-start, and peak RSS.

Scope: Qwen 2.5-VL-7B-Instruct-4bit only. Gemma 4 reproduction is
deferred per prereg scope.
"""

from __future__ import annotations

import argparse
import gc
import json
import resource
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import mlx.core as mx
from mlx_vlm import generate, load
from mlx_vlm.generate import PromptCacheState
from mlx_vlm.utils import prepare_inputs
from PIL import Image

import sys

# Reuse helpers from Track A to avoid duplication.
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from run_benchmark_track_a import (  # noqa: E402
    BenchmarkItem,
    BENCHMARK_FRAME_SIZE,
    DEFAULT_MODEL_PATH,
    PreparedSample,
    _decode_uniform_frames,
    _load_videomme_rows,
    _multiple_choice_prompt,
    _videomme_choice_text,
    _find_videomme_video,
)
from codec_through.answers import extract_choice  # noqa: E402


DEFAULT_SHORT_VIDEO_IDS: tuple[str, ...] = (
    "037",
    "100",
    "116",
    "120",
    "158",
    "160",
    "210",
)

DEFAULT_OUTPUT_DIR = Path(
    "research/experiments/2026/artifacts/phase1_55A_persistent_kv_qwen"
)


@dataclass(frozen=True, slots=True)
class SessionClip:
    video_id: str
    duration: str
    questions: list[BenchmarkItem]


def _questions_for_video_id(
    video_id: str,
    rows: list[dict[str, Any]],
) -> list[BenchmarkItem]:
    """Return all 3 VideoMME questions for a given videoID, ordered 1..3."""

    # Parquet exposes both ``video_id`` (3-digit numeric subset key we use
    # in manifests) and ``videoID`` (raw YouTube ID). Match on both.
    matching = [
        row
        for row in rows
        if str(row.get("video_id")) == video_id or str(row.get("videoID")) == video_id
    ]
    if len(matching) < 3:
        raise ValueError(
            f"expected ≥3 questions for video_id {video_id!r}, got {len(matching)}"
        )
    # Questions are numbered :1 :2 :3 via trailing suffix on question_id.
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
    frame_cache: dict[str, tuple[list[Image.Image], list[tuple[int, int, int, int]]]],
) -> PreparedSample:
    """Prepare input_ids + pixel_values + mask for an item, caching frames by video."""

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


def _peak_rss_gb() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # On macOS ru_maxrss is bytes; on Linux it's KB. Detect by magnitude.
    if usage > 10**9:  # ≥1 GB raw → assume bytes (macOS)
        return usage / 1e9
    return usage / 1e6  # else KB → GB


def _run_query(
    model: Any,
    processor: Any,
    sample: PreparedSample,
    *,
    max_tokens: int,
    prompt_cache_state: PromptCacheState | None,
) -> dict[str, Any]:
    mx.random.seed(42)
    kwargs = dict(sample.extra_kwargs)
    prefix_hit_before = 0
    input_len = int(sample.input_ids.size)
    if prompt_cache_state is not None:
        # Pass the state unconditionally so mlx-vlm populates it on the
        # first turn. find_prefix_length is for pre-call logging only;
        # on a fresh state it returns 0 (token_ids is None) and generate()
        # correctly treats it as a cold start.
        if prompt_cache_state.token_ids is not None:
            prefix_hit_before = prompt_cache_state.find_prefix_length(
                sample.input_ids.flatten().tolist()
            )
        kwargs["prompt_cache_state"] = prompt_cache_state
    start_ns = time.perf_counter_ns()
    response = generate(
        model,
        processor,
        "",
        input_ids=sample.input_ids,
        pixel_values=sample.pixel_values,
        mask=sample.mask,
        max_tokens=max_tokens,
        temperature=0.0,
        **kwargs,
    )
    elapsed_ms = (time.perf_counter_ns() - start_ns) / 1e6
    return {
        "text": response.text,
        "elapsed_ms": elapsed_ms,
        "prompt_tokens": response.prompt_tokens,
        "generation_tokens": response.generation_tokens,
        "peak_memory_gb": response.peak_memory,
        "prefix_hit": prefix_hit_before,
        "input_len": input_len,
        "prefix_coverage": (prefix_hit_before / input_len) if input_len else 0.0,
    }


def _score_answer(response_text: str, item: BenchmarkItem) -> tuple[str | None, bool]:
    letters = [chr(ord("A") + i) for i in range(len(item.candidates))]
    choice_index = extract_choice(response_text, letters)
    if choice_index is None:
        return None, False
    choice_letter = chr(ord("A") + choice_index)
    correct = choice_index == item.answer_index
    return choice_letter, correct


def main() -> int:
    parser = argparse.ArgumentParser(description="1.55A persistent-KV session driver")
    parser.add_argument(
        "--video-ids",
        type=str,
        default=",".join(DEFAULT_SHORT_VIDEO_IDS),
        help="Comma-separated VideoMME short-bucket videoIDs",
    )
    parser.add_argument("--frame-count", type=int, default=8)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument(
        "--model-path",
        type=Path,
        default=DEFAULT_MODEL_PATH,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
    )
    parser.add_argument(
        "--mode",
        choices=("session", "baseline", "both"),
        default="both",
        help="session = cache-threading; baseline = cold-start; both = run each clip twice",
    )
    args = parser.parse_args()

    video_ids = [vid.strip() for vid in args.video_ids.split(",") if vid.strip()]
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1.55A] loading model from {args.model_path}")
    model, processor = load(str(args.model_path))
    print(f"[1.55A] model loaded; video_ids={video_ids} frames={args.frame_count}")

    rows = _load_videomme_rows()
    clips: list[SessionClip] = []
    for vid in video_ids:
        items = _questions_for_video_id(vid, rows)
        clips.append(
            SessionClip(
                video_id=vid,
                duration=items[0].group,
                questions=items,
            )
        )
    print(f"[1.55A] prepared {len(clips)} clips × 3 questions = {3 * len(clips)} queries")

    session_path = args.output_dir / "session_qwen7b_n7.jsonl"
    baseline_path = args.output_dir / "baseline_qwen7b_n7.jsonl"
    summary_path = args.output_dir / "summary.json"

    frame_cache: dict[str, Any] = {}
    session_rows: list[dict[str, Any]] = []
    baseline_rows: list[dict[str, Any]] = []
    t_wall_start = time.perf_counter_ns()

    try:
        if args.mode in ("session", "both"):
            sf = open(session_path, "w")
        if args.mode in ("baseline", "both"):
            bf = open(baseline_path, "w")

        for clip in clips:
            print(f"[1.55A] clip {clip.video_id} duration={clip.duration}")

            if args.mode in ("session", "both"):
                # SESSION MODE: one PromptCacheState shared across the 3 queries.
                state = PromptCacheState()
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
                        prompt_cache_state=state,
                    )
                    choice, correct = _score_answer(result["text"], item)
                    row = {
                        "mode": "session",
                        "video_id": clip.video_id,
                        "duration": clip.duration,
                        "item_id": item.item_id,
                        "q_index": q_index,
                        "prompt_tokens": result["prompt_tokens"],
                        "generation_tokens": result["generation_tokens"],
                        "elapsed_ms": result["elapsed_ms"],
                        "peak_memory_gb": result["peak_memory_gb"],
                        "prefix_hit": result["prefix_hit"],
                        "input_len": result["input_len"],
                        "prefix_coverage": result["prefix_coverage"],
                        "response": result["text"].strip()[:200],
                        "choice": choice,
                        "correct": correct,
                    }
                    session_rows.append(row)
                    sf.write(json.dumps(row) + "\n")
                    sf.flush()
                    print(
                        f"   session Q{q_index+1}: {result['elapsed_ms']:.0f} ms "
                        f"prefix={result['prefix_hit']}/{result['input_len']} "
                        f"({result['prefix_coverage']:.2%}) correct={correct}"
                    )
                del state
                gc.collect()

            if args.mode in ("baseline", "both"):
                # BASELINE MODE: cold-start per query (no state).
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
                    )
                    choice, correct = _score_answer(result["text"], item)
                    row = {
                        "mode": "baseline",
                        "video_id": clip.video_id,
                        "duration": clip.duration,
                        "item_id": item.item_id,
                        "q_index": q_index,
                        "prompt_tokens": result["prompt_tokens"],
                        "generation_tokens": result["generation_tokens"],
                        "elapsed_ms": result["elapsed_ms"],
                        "peak_memory_gb": result["peak_memory_gb"],
                        "response": result["text"].strip()[:200],
                        "choice": choice,
                        "correct": correct,
                    }
                    baseline_rows.append(row)
                    bf.write(json.dumps(row) + "\n")
                    bf.flush()
                    print(
                        f"   baseline Q{q_index+1}: {result['elapsed_ms']:.0f} ms "
                        f"correct={correct}"
                    )
            gc.collect()
    finally:
        if args.mode in ("session", "both"):
            sf.close()
        if args.mode in ("baseline", "both"):
            bf.close()

    total_wall_ms = (time.perf_counter_ns() - t_wall_start) / 1e6
    peak_rss_gb = _peak_rss_gb()

    # Summaries
    def _summarise(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
        if not rows:
            return {}
        elapsed = sorted(r["elapsed_ms"] for r in rows)
        median = elapsed[len(elapsed) // 2]
        n_correct = sum(1 for r in rows if r["correct"])
        return {
            "label": key,
            "n": len(rows),
            "n_correct": n_correct,
            "accuracy": n_correct / len(rows),
            "mean_elapsed_ms": sum(elapsed) / len(elapsed),
            "median_elapsed_ms": median,
            "p05_elapsed_ms": elapsed[int(0.05 * len(elapsed))],
            "p95_elapsed_ms": elapsed[int(0.95 * len(elapsed))],
        }

    session_summary = _summarise(session_rows, "session")
    baseline_summary = _summarise(baseline_rows, "baseline")

    session_first = [r for r in session_rows if r["q_index"] == 0]
    session_follow = [r for r in session_rows if r["q_index"] > 0]
    first_summary = _summarise(session_first, "session_first_query")
    follow_summary = _summarise(session_follow, "session_follow_up")

    speedup = None
    if first_summary and follow_summary and follow_summary["median_elapsed_ms"] > 0:
        speedup = first_summary["median_elapsed_ms"] / follow_summary["median_elapsed_ms"]

    prefix_coverages = [r["prefix_coverage"] for r in session_follow]
    mean_prefix_cov = (
        sum(prefix_coverages) / len(prefix_coverages) if prefix_coverages else 0.0
    )

    acc_delta = None
    if session_summary and baseline_summary:
        acc_delta = session_summary["accuracy"] - baseline_summary["accuracy"]

    # H1-H4 verdicts
    h1_median_follow_ms = follow_summary.get("median_elapsed_ms") if follow_summary else None
    h1_median_follow_s = h1_median_follow_ms / 1000 if h1_median_follow_ms else None
    h1_earn = (
        h1_median_follow_s is not None
        and speedup is not None
        and h1_median_follow_s <= 3.0
        and speedup >= 5.0
    )
    h1_reject = (
        h1_median_follow_s is not None
        and (h1_median_follow_s >= 5.0 or (speedup is not None and speedup <= 2.0))
    )
    h2_earn = acc_delta is not None and abs(acc_delta) <= 0.05
    h2_reject = acc_delta is not None and abs(acc_delta) > 0.10
    h3_earn = mean_prefix_cov >= 0.90
    h3_reject = mean_prefix_cov < 0.50
    h4_earn = peak_rss_gb <= 13.0
    h4_reject = peak_rss_gb > 14.0

    summary = {
        "phase": "1.55A",
        "model": args.model_path.name.lower(),
        "frame_count": args.frame_count,
        "n_clips": len(clips),
        "n_queries_per_mode": 3 * len(clips),
        "total_wall_ms": total_wall_ms,
        "peak_rss_gb": peak_rss_gb,
        "session": session_summary,
        "session_first_query": first_summary,
        "session_follow_up": follow_summary,
        "baseline": baseline_summary,
        "speedup_first_over_follow": speedup,
        "mean_follow_up_prefix_coverage": mean_prefix_cov,
        "accuracy_delta_session_minus_baseline": acc_delta,
        "verdicts": {
            "H1_follow_up_speedup": {
                "earn": h1_earn,
                "reject": h1_reject,
                "median_follow_up_s": h1_median_follow_s,
                "speedup": speedup,
            },
            "H2_accuracy_preservation": {
                "earn": h2_earn,
                "reject": h2_reject,
                "delta": acc_delta,
            },
            "H3_prefix_coverage": {
                "earn": h3_earn,
                "reject": h3_reject,
                "coverage": mean_prefix_cov,
            },
            "H4_peak_rss": {
                "earn": h4_earn,
                "reject": h4_reject,
                "peak_rss_gb": peak_rss_gb,
            },
        },
    }

    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(
        f"[1.55A] done. session follow-up median "
        f"{follow_summary.get('median_elapsed_ms'):.0f} ms, "
        f"speedup {speedup:.2f}×, "
        f"prefix coverage {mean_prefix_cov:.2%}, "
        f"Δacc {acc_delta}"
    )
    print(f"[1.55A] wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
