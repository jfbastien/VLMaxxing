#!/usr/bin/env python3
"""Phase 1.55D — selective re-prefill of last-K frames per follow-up.

Scientific question: does re-prefilling the last K frames per follow-up
query recover the cache-reuse Δacc ramp observed in 1.55A while
retaining ≥ 15× speedup?

Mechanism: for follow-up queries (q_index > 0) in a session, truncate
`PromptCacheState.token_ids` to the boundary between (system prompt +
first N−K frames) and (last K frames + question). On the next
generate() call mlx-vlm's prefix-reuse code finds a shorter common
prefix, truncates the KV cache to that boundary, and re-prefills the
last K frames + new question fresh under attention.

Scope: Qwen 2.5-VL-7B-Instruct-4bit only. Single N (default 20f),
single or swept K.
"""

from __future__ import annotations

import argparse
import gc
import json
import resource
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import mlx.core as mx
from mlx_vlm import generate, load
from mlx_vlm.generate import PromptCacheState
from mlx_vlm.utils import prepare_inputs
from PIL import Image

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

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

QWEN_IMAGE_TOKEN_ID = 151655  # <|image_pad|> in Qwen 2.5-VL-Instruct

DEFAULT_OUTPUT_DIR = Path("research/experiments/2026/artifacts/phase1_55D_selective_reprefill")


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
    frame_cache: dict[str, tuple[list[Image.Image], list[tuple[int, int, int, int]]]],
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
        messages, tokenize=False, add_generation_prompt=True
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
    if usage > 10**9:
        return usage / 1e9
    return usage / 1e6


def _compute_trunc_idx(
    input_ids: mx.array, n_frames: int, reprefill_k: int, image_token_id: int
) -> int:
    """Return the token index at which to truncate cache to re-prefill last K frames.

    We scan the Q1 input_ids for all image-content tokens (image_token_id),
    partition them uniformly into N frames, and return the absolute token
    position of the first image token of frame (N-K+1). The cached prefix
    after truncation contains: system prompt + first (N-K) frames' image
    tokens. The re-prefill on each follow-up covers: last K frames' image
    tokens + question + chat template tail.
    """
    if reprefill_k <= 0:
        raise ValueError("reprefill_k must be > 0")
    if reprefill_k >= n_frames:
        raise ValueError(f"reprefill_k={reprefill_k} must be < n_frames={n_frames}")
    ids_list = input_ids.flatten().tolist()
    image_positions = [i for i, t in enumerate(ids_list) if t == image_token_id]
    total_image_tokens = len(image_positions)
    if total_image_tokens == 0:
        raise ValueError("no image tokens found in input_ids")
    if total_image_tokens % n_frames != 0:
        raise ValueError(
            f"image tokens {total_image_tokens} not divisible by n_frames {n_frames} — "
            "uniform-per-frame assumption violated"
        )
    tokens_per_frame = total_image_tokens // n_frames
    boundary_image_idx = (n_frames - reprefill_k) * tokens_per_frame
    return image_positions[boundary_image_idx]


def _truncate_state_for_reprefill(state: PromptCacheState, trunc_idx: int) -> None:
    """Rewind state.token_ids to trunc_idx; mlx-vlm will truncate cache on next call."""
    if state.token_ids is None:
        return
    if trunc_idx >= len(state.token_ids):
        return
    state.token_ids = state.token_ids[:trunc_idx]
    if state.cache is not None:
        for c in state.cache:
            if hasattr(c, "keys") and c.keys is not None:
                cached_len = c.keys.shape[2]
                if cached_len > trunc_idx:
                    c.keys = c.keys[:, :, :trunc_idx, :]
                    c.values = c.values[:, :, :trunc_idx, :]
                    if hasattr(c, "offset"):
                        c.offset = trunc_idx


def _run_query(
    model: Any,
    processor: Any,
    sample: PreparedSample,
    *,
    max_tokens: int,
    prompt_cache_state: PromptCacheState | None,
    temperature: float = 0.0,
    top_p: float = 1.0,
    min_p: float = 0.0,
) -> dict[str, Any]:
    mx.random.seed(42)
    kwargs = dict(sample.extra_kwargs)
    prefix_hit_before = 0
    input_len = int(sample.input_ids.size)
    if prompt_cache_state is not None:
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
        temperature=temperature,
        top_p=top_p,
        min_p=min_p,
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
    parser = argparse.ArgumentParser(description="1.55D selective re-prefill session driver")
    parser.add_argument(
        "--video-ids",
        type=str,
        default=",".join(DEFAULT_SHORT_VIDEO_IDS),
    )
    parser.add_argument("--frame-count", type=int, default=20)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument(
        "--reprefill-k",
        type=int,
        required=True,
        help="Number of last frames to re-prefill per follow-up query (1..N-1)",
    )
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
    )
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--min-p", type=float, default=0.0)
    args = parser.parse_args()

    if args.reprefill_k <= 0:
        raise SystemExit("--reprefill-k must be > 0 (use 1.55A driver for K=0)")

    video_ids = [vid.strip() for vid in args.video_ids.split(",") if vid.strip()]
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1.55D] loading model from {args.model_path}")
    model, processor = load(str(args.model_path))
    print(
        f"[1.55D] loaded; video_ids={video_ids} "
        f"frames={args.frame_count} reprefill_k={args.reprefill_k}"
    )

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

    tag = f"k{args.reprefill_k}_n{len(clips)}"
    session_path = args.output_dir / f"session_{tag}.jsonl"
    baseline_path = args.output_dir / f"baseline_{tag}.jsonl"
    summary_path = args.output_dir / f"summary_{tag}.json"

    frame_cache: dict[str, Any] = {}
    session_rows: list[dict[str, Any]] = []
    baseline_rows: list[dict[str, Any]] = []
    t_wall_start = time.perf_counter_ns()

    # image_token_id lookup: prefer model.config, fall back to known Qwen constant
    image_token_id = getattr(model.config, "image_token_id", None)
    if image_token_id is None:
        image_token_id = QWEN_IMAGE_TOKEN_ID
    print(f"[1.55D] image_token_id={image_token_id}")

    try:
        if args.mode in ("session", "both"):
            sf = open(session_path, "w")  # noqa: SIM115
        if args.mode in ("baseline", "both"):
            bf = open(baseline_path, "w")  # noqa: SIM115

        for clip in clips:
            print(f"[1.55D] clip {clip.video_id} duration={clip.duration}")

            if args.mode in ("session", "both"):
                state = PromptCacheState()
                trunc_idx: int | None = None
                for q_index, item in enumerate(clip.questions):
                    sample = _prepare_sample(
                        processor,
                        item,
                        frame_count=args.frame_count,
                        frame_cache=frame_cache,
                    )
                    # Compute trunc_idx once on Q1 (image layout is identical
                    # across the 3 Qs for this clip; validated by shared video_id).
                    if q_index == 0:
                        trunc_idx = _compute_trunc_idx(
                            sample.input_ids,
                            n_frames=args.frame_count,
                            reprefill_k=args.reprefill_k,
                            image_token_id=image_token_id,
                        )
                        print(
                            f"   trunc_idx={trunc_idx} "
                            f"(input_len={int(sample.input_ids.size)}; "
                            f"reprefill tail = last {args.reprefill_k} frames "
                            f"+ question)"
                        )
                    else:
                        # Before Q2, Q3: rewind state to trunc_idx to force
                        # mlx-vlm to re-prefill from the last-K-frames boundary.
                        assert trunc_idx is not None
                        _truncate_state_for_reprefill(state, trunc_idx)

                    result = _run_query(
                        model,
                        processor,
                        sample,
                        max_tokens=args.max_tokens,
                        prompt_cache_state=state,
                        temperature=args.temperature,
                        top_p=args.top_p,
                        min_p=args.min_p,
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
                        "trunc_idx": trunc_idx,
                        "reprefill_k": args.reprefill_k,
                        "response": result["text"].strip()[:200],
                        "choice": choice,
                        "correct": correct,
                    }
                    session_rows.append(row)
                    sf.write(json.dumps(row) + "\n")
                    sf.flush()
                    print(
                        f"   session Q{q_index + 1}: {result['elapsed_ms']:.0f} ms "
                        f"prefix={result['prefix_hit']}/{result['input_len']} "
                        f"({result['prefix_coverage']:.2%}) correct={correct} "
                        f"resp={result['text'].strip()[:40]!r}"
                    )
                del state
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
                        top_p=args.top_p,
                        min_p=args.min_p,
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
                        f"   baseline Q{q_index + 1}: {result['elapsed_ms']:.0f} ms "
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

    def _summarise(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
        if not rows:
            return {}
        elapsed = sorted(r["elapsed_ms"] for r in rows)
        n_correct = sum(1 for r in rows if r["correct"])
        return {
            "label": key,
            "n": len(rows),
            "n_correct": n_correct,
            "accuracy": n_correct / len(rows),
            "mean_elapsed_ms": sum(elapsed) / len(elapsed),
            "median_elapsed_ms": float(statistics.median(elapsed)),
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
    mean_prefix_cov = sum(prefix_coverages) / len(prefix_coverages) if prefix_coverages else 0.0
    acc_delta = None
    if session_summary and baseline_summary:
        acc_delta = session_summary["accuracy"] - baseline_summary["accuracy"]

    # H verdicts per 1.55D prereg
    h1_target_15 = acc_delta is not None and acc_delta >= -0.15
    h1_target_25 = acc_delta is not None and acc_delta >= -0.25
    h2_follow_s = follow_summary["median_elapsed_ms"] / 1000 if follow_summary else None
    h2_speedup_10 = speedup is not None and speedup >= 10.0
    # Basin dispersal counted as follow-ups with known pathological attractor
    # strings: addCriterion variants or the literal 自动生成 ("auto-generated")
    # marker observed in the unrepaired basin.
    basin_hits = sum(
        1
        for r in session_follow
        if "addCriterion" in r.get("response", "") or "自动" in r.get("response", "")
    )
    h3_basin_drop = basin_hits <= 4
    h4_rss = peak_rss_gb <= 5.0

    summary = {
        "phase": "1.55D",
        "model": args.model_path.name.lower(),
        "frame_count": args.frame_count,
        "reprefill_k": args.reprefill_k,
        "n_clips": len(clips),
        "n_queries_per_mode": 3 * len(clips),
        "total_wall_ms": total_wall_ms,
        "peak_rss_gb": peak_rss_gb,
        "sampling": {
            "temperature": args.temperature,
            "top_p": args.top_p,
            "min_p": args.min_p,
            "seed": 42,
        },
        "session": session_summary,
        "session_first_query": first_summary,
        "session_follow_up": follow_summary,
        "baseline": baseline_summary,
        "speedup_first_over_follow": speedup,
        "mean_follow_up_prefix_coverage": mean_prefix_cov,
        "accuracy_delta_session_minus_baseline": acc_delta,
        "basin_follow_up_hits": basin_hits,
        "basin_follow_up_total": len(session_follow),
        "verdicts": {
            "H1_fidelity_target_minus_0_15": h1_target_15,
            "H1_fidelity_target_minus_0_25": h1_target_25,
            "H2_speedup_10x": h2_speedup_10,
            "H2_follow_up_median_s": h2_follow_s,
            "H3_basin_dispersal_le_4": h3_basin_drop,
            "H4_peak_rss_le_5gb": h4_rss,
        },
    }

    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(
        f"[1.55D] done. follow-up median "
        f"{(follow_summary or {}).get('median_elapsed_ms', 0):.0f} ms, "
        f"speedup {speedup}, "
        f"prefix coverage {mean_prefix_cov:.2%}, "
        f"Δacc {acc_delta}, "
        f"basin {basin_hits}/{len(session_follow)}"
    )
    print(f"[1.55D] wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
