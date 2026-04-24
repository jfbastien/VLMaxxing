#!/usr/bin/env python3
"""Phase 1.30 single-arm session / streaming bridge harness.

This intentionally runs one stack per invocation so cold-vs-streaming comparisons
can be thermally paired as separate processes:

- ``cold``: no prompt-cache reuse; decode and prefill are paid on every query
- ``streaming``: decode once per clip session, prompt-cache reuse across the
  clip's question sequence, optional Qwen vision-tower pruning
"""

from __future__ import annotations

import argparse
import gc
import importlib.util
import json
import sys
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import mlx.core as mx
from mlx_vlm import load
from mlx_vlm.generate import PromptCacheState
from mlx_vlm.utils import prepare_inputs

from codec_through.memory_guard import check_rss_guard
from codec_through.qwen_pruned_vision_tower import (
    QwenVisionPruneConfig,
    set_qwen_vision_tower_config,
)
from codec_through.session_bucketing import is_degenerate_response
from codec_through.session_prune_policy import keep_rate_for_query

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO_ROOT / "scripts" / "run_benchmark_track_a.py"
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_kv_cache_session import (  # noqa: E402
    DEFAULT_MODEL_PATH,
    _peak_rss_gb,
    _questions_for_video_id,
    _run_query,
    _score_answer,
)


@dataclass(frozen=True, slots=True)
class SessionSeed:
    seed_item_id: str
    video_id: str
    duration: str
    split: str
    source_manifests: tuple[str, ...]
    questions: list[Any]


def _load_runner_module() -> Any:
    name = "_phase1_30_streaming_runner"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot build spec for {RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def _load_manifest_items(manifest_path: Path) -> list[str]:
    payload = tomllib.loads(manifest_path.read_text())
    benchmark = str(payload["benchmark"])
    if benchmark != "videomme":
        raise ValueError(f"Phase 1.30 supports videomme manifests only, got {benchmark!r}")
    return [str(item_id) for item_id in payload["item_ids"]]


def _video_id_from_item_id(item_id: str) -> str:
    parts = item_id.split(":")
    if len(parts) != 3:
        raise ValueError(f"unexpected VideoMME item_id format: {item_id!r}")
    return parts[2].split("-")[0]


def _build_session_seeds(
    *,
    rows: list[dict[str, Any]],
    manifest_paths: list[Path],
    keep_duplicate_seeds: bool,
) -> list[SessionSeed]:
    by_video: dict[str, list[str]] = {}
    ordered_pairs: list[tuple[str, str]] = []
    for manifest_path in manifest_paths:
        for item_id in _load_manifest_items(manifest_path):
            video_id = _video_id_from_item_id(item_id)
            by_video.setdefault(video_id, []).append(manifest_path.as_posix())
            ordered_pairs.append((item_id, video_id))

    seeds: list[SessionSeed] = []
    seen_video_ids: set[str] = set()
    for seed_item_id, video_id in ordered_pairs:
        if not keep_duplicate_seeds and video_id in seen_video_ids:
            continue
        questions = _questions_for_video_id(video_id, rows)
        source_manifests = tuple(sorted(set(by_video[video_id])))
        split = (
            "dev"
            if all("dev" in path for path in source_manifests)
            else "holdout"
            if all("holdout" in path for path in source_manifests)
            else "mixed"
        )
        seeds.append(
            SessionSeed(
                seed_item_id=seed_item_id,
                video_id=video_id,
                duration=questions[0].group,
                split=split,
                source_manifests=source_manifests,
                questions=questions,
            )
        )
        seen_video_ids.add(video_id)
    return seeds


def _prepare_sample_timed(
    *,
    runner: Any,
    processor: Any,
    item: Any,
    frame_count: int,
    frame_cache: dict[str, Any],
) -> tuple[Any, float, float]:
    if hasattr(processor, "image_processor"):
        if hasattr(processor.image_processor, "do_resize"):
            processor.image_processor.do_resize = False
        if hasattr(processor.image_processor, "do_image_splitting"):
            processor.image_processor.do_image_splitting = False

    video_key = str(item.video_path)
    t0 = time.perf_counter_ns()
    if video_key not in frame_cache:
        frames, active_boxes = runner._decode_uniform_frames(
            item.video_path,
            frame_count=frame_count,
            start_seconds=item.start_seconds,
            end_seconds=item.end_seconds,
        )
        frame_cache[video_key] = (frames, active_boxes)
    frames, active_boxes = frame_cache[video_key]
    decode_ms = (time.perf_counter_ns() - t0) / 1_000_000

    messages = [
        {
            "role": "user",
            "content": [
                *({"type": "image"} for _ in frames),
                {"type": "text", "text": item.question},
            ],
        }
    ]
    t1 = time.perf_counter_ns()
    rendered_prompt = processor.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    raw_inputs = prepare_inputs(processor, images=frames, prompts=rendered_prompt)
    processor_ms = (time.perf_counter_ns() - t1) / 1_000_000
    input_ids = mx.array(raw_inputs["input_ids"])
    pixel_values = mx.array(raw_inputs["pixel_values"])
    mask = mx.array(raw_inputs["attention_mask"])
    extra_kwargs = {
        key: mx.array(value)
        for key, value in raw_inputs.items()
        if key not in {"input_ids", "pixel_values", "attention_mask"}
    }
    return (
        runner.PreparedSample(
            item=item,
            frames=frames,
            active_boxes=active_boxes,
            input_ids=input_ids,
            pixel_values=pixel_values,
            mask=mask,
            extra_kwargs=extra_kwargs,
        ),
        decode_ms,
        processor_ms,
    )


def _summarize(rows: list[dict[str, Any]], label: str) -> dict[str, Any]:
    if not rows:
        return {"label": label, "n": 0}
    elapsed = sorted(float(row["end_to_end_ms"]) for row in rows)
    decode = [float(row["decode_ms"]) for row in rows]
    processor = [float(row["processor_ms"]) for row in rows]
    query = [float(row["query_ms"]) for row in rows]
    prefix_coverages = [float(row["prefix_coverage"]) for row in rows if row["q_index"] > 0]
    n_correct = sum(1 for row in rows if row["correct"])
    n_parse_fail = sum(1 for row in rows if row["parse_failure"])
    return {
        "label": label,
        "n": len(rows),
        "n_correct": n_correct,
        "accuracy": n_correct / len(rows),
        "n_parse_failures": n_parse_fail,
        "mean_end_to_end_ms": sum(elapsed) / len(elapsed),
        "median_end_to_end_ms": elapsed[len(elapsed) // 2],
        "p05_end_to_end_ms": elapsed[int(0.05 * (len(elapsed) - 1))],
        "p95_end_to_end_ms": elapsed[int(0.95 * (len(elapsed) - 1))],
        "mean_decode_ms": sum(decode) / len(decode),
        "mean_processor_ms": sum(processor) / len(processor),
        "mean_query_ms": sum(query) / len(query),
        "mean_prefix_coverage_follow_up": (
            sum(prefix_coverages) / len(prefix_coverages) if prefix_coverages else 0.0
        ),
    }


def _should_refresh(*, drift_refresh_policy: str, q_index: int) -> bool:
    if q_index == 0:
        return False
    if drift_refresh_policy == "off":
        return False
    if drift_refresh_policy == "hard-reset":
        return True
    raise ValueError(f"unsupported drift_refresh_policy: {drift_refresh_policy!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stack",
        choices=("cold", "streaming"),
        required=True,
        help="cold = no cache reuse; streaming = session cache reuse per clip",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        action="append",
        required=True,
        help="VideoMME manifest(s); pass twice for dev+holdout union",
    )
    parser.add_argument(
        "--keep-duplicate-seeds",
        action="store_true",
        help="Repeat sessions for duplicate manifest seeds instead of defaulting to unique clips.",
    )
    parser.add_argument("--n-seeds", type=int, default=0, help="0 = all seeds")
    parser.add_argument("--frame-count", type=int, default=8)
    parser.add_argument("--max-tokens", type=int, default=32)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--rss-guard-mb", type=int, default=0)
    parser.add_argument("--vision-tower-layer", type=int, default=2)
    parser.add_argument("--vision-tower-keep-rate", type=float, default=1.0)
    parser.add_argument(
        "--vision-tower-keep-rate-first-query",
        type=float,
        default=None,
        help="Optional Q0 override for position-conditioned pruning policies.",
    )
    parser.add_argument(
        "--vision-tower-keep-rate-follow-ups",
        type=float,
        default=None,
        help="Optional Q1/Q2 override for position-conditioned pruning policies.",
    )
    parser.add_argument(
        "--drift-refresh-policy",
        choices=("off", "hard-reset", "threshold"),
        default="off",
        help="Streaming-only refresh policy. threshold is reserved and hard-fails today.",
    )
    parser.add_argument("--drift-refresh-threshold", type=float, default=0.0)
    args = parser.parse_args()

    runner = _load_runner_module()
    runner._ensure_clean_git_tree(allow_dirty=args.allow_dirty)

    if args.stack == "cold" and args.drift_refresh_policy != "off":
        raise SystemExit("cold stack does not support refresh policies")
    if args.drift_refresh_policy == "threshold":
        raise SystemExit(
            "thresholded drift refresh is not implemented yet; use --drift-refresh-policy off "
            "or hard-reset"
        )

    rows = runner._load_videomme_rows()
    seeds = _build_session_seeds(
        rows=rows,
        manifest_paths=args.manifest,
        keep_duplicate_seeds=args.keep_duplicate_seeds,
    )
    if args.n_seeds > 0:
        seeds = seeds[: args.n_seeds]
    if not seeds:
        raise SystemExit("no session seeds loaded")

    model, processor = load(str(args.model_path))
    if getattr(model.config, "model_type", None) != "qwen2_5_vl":
        raise SystemExit(
            f"Phase 1.30 harness currently supports qwen2_5_vl only; got "
            f"{getattr(model.config, 'model_type', None)!r}"
        )
    candidate_keep_rates = [
        args.vision_tower_keep_rate,
        args.vision_tower_keep_rate_first_query,
        args.vision_tower_keep_rate_follow_ups,
    ]
    use_positioned_policy = any(rate is not None for rate in candidate_keep_rates[1:])
    vt_patched_any = any((rate is not None and rate < 1.0) for rate in candidate_keep_rates)
    if vt_patched_any or use_positioned_policy:
        initial_keep_rate = keep_rate_for_query(
            q_index=0,
            default_keep_rate=args.vision_tower_keep_rate,
            first_query_keep_rate=args.vision_tower_keep_rate_first_query,
            follow_up_keep_rate=args.vision_tower_keep_rate_follow_ups,
        )
        set_qwen_vision_tower_config(
            model,
            QwenVisionPruneConfig(
                layer_idx=args.vision_tower_layer,
                keep_rate=initial_keep_rate,
            ),
        )

    if args.rss_guard_mb > 0:
        check_rss_guard(args.rss_guard_mb, stage="post_model_load")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    refresh_trace: list[dict[str, Any]] = []
    session_start_ns = time.perf_counter_ns()
    frame_cache: dict[str, Any] = {}
    unique_video_ids = sorted({seed.video_id for seed in seeds})

    with args.output.open("w") as handle:
        for seed in seeds:
            print(
                f"[1.30 {args.stack}] seed={seed.seed_item_id} video={seed.video_id} "
                f"duration={seed.duration} split={seed.split}"
            )
            state = PromptCacheState() if args.stack == "streaming" else None
            if args.stack == "streaming":
                frame_cache.clear()

            for q_index, item in enumerate(seed.questions):
                query_keep_rate = keep_rate_for_query(
                    q_index=q_index,
                    default_keep_rate=args.vision_tower_keep_rate,
                    first_query_keep_rate=args.vision_tower_keep_rate_first_query,
                    follow_up_keep_rate=args.vision_tower_keep_rate_follow_ups,
                )
                if vt_patched_any or use_positioned_policy:
                    set_qwen_vision_tower_config(
                        model,
                        QwenVisionPruneConfig(
                            layer_idx=args.vision_tower_layer,
                            keep_rate=query_keep_rate,
                        ),
                    )
                refresh_before_query = False
                refresh_reason = None
                if args.stack == "streaming" and _should_refresh(
                    drift_refresh_policy=args.drift_refresh_policy,
                    q_index=q_index,
                ):
                    state = PromptCacheState()
                    frame_cache.clear()
                    refresh_before_query = True
                    refresh_reason = args.drift_refresh_policy
                    refresh_trace.append(
                        {
                            "seed_item_id": seed.seed_item_id,
                            "video_id": seed.video_id,
                            "item_id": item.item_id,
                            "q_index": q_index,
                            "reason": refresh_reason,
                            "threshold": args.drift_refresh_threshold,
                        }
                    )

                local_frame_cache = frame_cache if args.stack == "streaming" else {}
                sample, decode_ms, processor_ms = _prepare_sample_timed(
                    runner=runner,
                    processor=processor,
                    item=item,
                    frame_count=args.frame_count,
                    frame_cache=local_frame_cache,
                )

                result = _run_query(
                    model,
                    processor,
                    sample,
                    max_tokens=args.max_tokens,
                    prompt_cache_state=state,
                )
                choice, correct = _score_answer(result["text"], item)
                parse_failure = choice is None
                degenerate = is_degenerate_response(
                    text=result["text"],
                    parse_failure=parse_failure,
                )
                end_to_end_ms = decode_ms + processor_ms + float(result["elapsed_ms"])
                row = {
                    "phase": "1.30",
                    "stack": args.stack,
                    "session_id": seed.seed_item_id,
                    "seed_item_id": seed.seed_item_id,
                    "video_id": seed.video_id,
                    "duration": seed.duration,
                    "split": seed.split,
                    "source_manifests": list(seed.source_manifests),
                    "item_id": item.item_id,
                    "q_index": q_index,
                    "frame_count": args.frame_count,
                    "timing_ms": {
                        "decode": decode_ms,
                        "processor": processor_ms,
                        "vision": None,
                        "generate": float(result["elapsed_ms"]),
                        "end_to_end": end_to_end_ms,
                    },
                    "decode_ms": decode_ms,
                    "processor_ms": processor_ms,
                    "query_ms": float(result["elapsed_ms"]),
                    "end_to_end_ms": end_to_end_ms,
                    "prompt_tokens": int(result["prompt_tokens"]),
                    "generation_tokens": int(result["generation_tokens"]),
                    "peak_memory_gb": float(result["peak_memory_gb"]),
                    "prefix_hit": int(result["prefix_hit"]),
                    "input_len": int(result["input_len"]),
                    "prefix_coverage": float(result["prefix_coverage"]),
                    "response": result["text"].strip()[:400],
                    "choice": choice,
                    "correct": correct,
                    "parse_failure": parse_failure,
                    "degenerate": degenerate,
                    "refresh_fired": refresh_before_query,
                    "refresh_policy": args.drift_refresh_policy,
                    "refresh_reason": refresh_reason,
                    "refresh_threshold": args.drift_refresh_threshold,
                    "vision_tower_patched": query_keep_rate < 1.0,
                    "vision_tower_keep_rate": query_keep_rate,
                    "vision_tower_keep_rate_default": args.vision_tower_keep_rate,
                    "vision_tower_keep_rate_first_query": args.vision_tower_keep_rate_first_query,
                    "vision_tower_keep_rate_follow_ups": args.vision_tower_keep_rate_follow_ups,
                    "vision_tower_layer": args.vision_tower_layer,
                }
                records.append(row)
                handle.write(json.dumps(row) + "\n")
                handle.flush()
                print(
                    f"   Q{q_index + 1}: {end_to_end_ms:.0f} ms "
                    f"prefix={row['prefix_coverage']:.2%} correct={correct} "
                    f"degenerate={degenerate}"
                )
                gc.collect()

                if args.rss_guard_mb > 0:
                    check_rss_guard(args.rss_guard_mb, stage=f"{args.stack}:{item.item_id}")

            del state
            gc.collect()

    total_wall_ms = (time.perf_counter_ns() - session_start_ns) / 1_000_000
    summary = {
        "phase": "1.30",
        "stack": args.stack,
        "model": args.model_path.name,
        "frame_count": args.frame_count,
        "n_seed_items": len(seeds),
        "n_session_seeds": len(seeds),
        "n_unique_video_ids": len(unique_video_ids),
        "n_queries": len(records),
        "source_manifests": [path.as_posix() for path in args.manifest],
        "vision_tower_keep_rate": args.vision_tower_keep_rate,
        "vision_tower_keep_rate_first_query": args.vision_tower_keep_rate_first_query,
        "vision_tower_keep_rate_follow_ups": args.vision_tower_keep_rate_follow_ups,
        "vision_tower_layer": args.vision_tower_layer,
        "drift_refresh_policy": args.drift_refresh_policy,
        "drift_refresh_threshold": args.drift_refresh_threshold,
        "total_wall_ms": total_wall_ms,
        "peak_rss_gb": _peak_rss_gb(),
        "all_queries": _summarize(records, "all_queries"),
        "first_queries": _summarize(
            [row for row in records if row["q_index"] == 0], "first_queries"
        ),
        "follow_ups": _summarize([row for row in records if row["q_index"] > 0], "follow_ups"),
        "degenerate_queries": sum(1 for row in records if row["degenerate"]),
        "parse_failures": sum(1 for row in records if row["parse_failure"]),
        "refresh_events": len(refresh_trace),
        "refresh_trace_path": args.summary.with_name(
            args.summary.stem + "_refresh_trace.json"
        ).as_posix(),
    }
    args.summary.write_text(json.dumps(summary, indent=2) + "\n")
    refresh_trace_path = Path(summary["refresh_trace_path"])
    refresh_trace_path.write_text(json.dumps(refresh_trace, indent=2) + "\n")
    print(f"[1.30 {args.stack}] wrote {args.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
