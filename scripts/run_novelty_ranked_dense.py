#!/usr/bin/env python3
"""Phase 1.34 novelty-ranked dense baseline.

Regenerates the raw artifacts needed to promote paper/claim-matrix.md claim #9
from local diagnostic to release claim-bearing evidence. The open question is
whether a cached policy's gain comes from **smart budget placement** (the
theory) or just from **smart frame selection**. A novelty-ranked dense-N
baseline picks the N most informative frames up front, then runs dense compute
on them — no caching, no reuse.

Method:
- Decode a dense grid (``--reference-frames``, default 32) of uniformly
  sampled frames.
- For each adjacent pair compute the chosen novelty statistic
  (default: MAX_ABS — the Planner 2.0 winner).
- Each frame's novelty score is the max adjacent-pair diff it
  participates in; frame 0 gets the second-pair score.
- Rank frames by score, keep the top ``--frame-count``, always
  including frame 0.
- Re-sample and re-sort by original temporal index so the selection
  fed to the VLM stays time-ordered.
- Run Qwen 2.5-VL generation on those N frames, compare to ground
  truth via the runner's ``extract_choice``.

This harness does its own end-to-end inference (no cache replay) so
the output is a direct accuracy measurement.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import av  # type: ignore[import-untyped]
import mlx.core as mx
import numpy as np
from mlx_vlm import generate, load  # type: ignore[import-untyped]
from mlx_vlm.utils import prepare_inputs  # type: ignore[import-untyped]
from PIL import Image

from codec_through.answers import extract_choice
from codec_through.temporal import BlockStatistic, PlannerConfig, block_statistic_values

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO_ROOT / "scripts" / "run_benchmark_track_a.py"

DEFAULT_MODEL_PATH = Path.home() / "models" / "Qwen2.5-VL-7B-Instruct-4bit"

QWEN_BLOCK_SIZE = 28
BENCHMARK_FRAME_SIZE = 560


def _load_runner_module() -> Any:
    name = "_novelty_runner"
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


@dataclass(frozen=True, slots=True)
class NoveltyRecord:
    item_id: str
    benchmark: str
    group: str
    reference_frames: int
    selected_frames: int
    selected_indices: list[int]
    frame_novelty: list[float]
    model_text: str
    choice_index: int | None
    answer_index: int
    correct: bool
    parse_failure: bool
    elapsed_ms: float


def _decode_reference_frames(
    runner: Any, video_path: Path, *, reference_frames: int, start: float | None, end: float | None
) -> tuple[list[Image.Image], list[int]]:
    """Decode all frames then uniformly sample ``reference_frames`` of them.

    Returns the sampled, letterboxed frames plus their original indices
    within the decoded stream so the caller can surface which frames
    were ranked and which survived.
    """

    all_frames: list[Image.Image] = []
    with av.open(str(video_path)) as container:
        for frame in container.decode(video=0):
            timestamp = float(frame.time) if frame.time is not None else None
            if start is not None and timestamp is not None and timestamp < start:
                continue
            if end is not None and timestamp is not None and timestamp > end:
                break
            all_frames.append(frame.to_image().convert("RGB"))
    if len(all_frames) < reference_frames:
        raise ValueError(
            f"expected >= {reference_frames} frames from {video_path}, got {len(all_frames)}"
        )
    indices = np.linspace(0, len(all_frames) - 1, reference_frames, dtype=int).tolist()
    sampled: list[Image.Image] = []
    for index in indices:
        padded, _ = runner._square_pad_frame(all_frames[index], size=BENCHMARK_FRAME_SIZE)
        sampled.append(padded)
    return sampled, indices


def _per_frame_novelty(frames: list[Image.Image], *, statistic: BlockStatistic) -> np.ndarray:
    """Score each frame by its max adjacent-pair diff.

    Pair (t, t+1) contributes its summary statistic to both frames t
    and t+1. Frame 0's only pair is (0, 1); the last frame's only pair
    is (N-2, N-1). This keeps the budget of frames to choose balanced
    with the number of pairs.
    """

    arrays = [np.asarray(f, dtype=np.uint8) for f in frames]
    n = len(arrays)
    cfg = PlannerConfig(statistic=statistic)
    pair_scores = np.zeros(n - 1, dtype=np.float32)
    for i in range(n - 1):
        stats = block_statistic_values(
            arrays[i], arrays[i + 1], block_size=QWEN_BLOCK_SIZE, config=cfg
        )
        pair_scores[i] = float(stats.mean())
    per_frame = np.zeros(n, dtype=np.float32)
    for i in range(n):
        neighbors = []
        if i > 0:
            neighbors.append(pair_scores[i - 1])
        if i < n - 1:
            neighbors.append(pair_scores[i])
        per_frame[i] = max(neighbors) if neighbors else 0.0
    return per_frame


def _select_top_novel(
    scores: np.ndarray, *, frame_count: int, force_first: bool = True
) -> list[int]:
    if frame_count <= 0 or frame_count > len(scores):
        raise ValueError(f"invalid frame_count={frame_count} for reference N={len(scores)}")
    # descending argsort
    order = np.argsort(-scores, kind="mergesort").tolist()
    chosen: list[int] = []
    if force_first and 0 not in chosen:
        chosen.append(0)
    for idx in order:
        if len(chosen) >= frame_count:
            break
        if idx in chosen:
            continue
        chosen.append(idx)
    # time-ordered output
    chosen.sort()
    return chosen


def _run_inference(
    model: Any,
    processor: Any,
    frames: list[Image.Image],
    question: str,
    *,
    max_tokens: int,
) -> tuple[str, float]:
    if hasattr(processor, "image_processor"):
        if hasattr(processor.image_processor, "do_resize"):
            processor.image_processor.do_resize = False
        if hasattr(processor.image_processor, "do_image_splitting"):
            processor.image_processor.do_image_splitting = False
    messages = [
        {
            "role": "user",
            "content": [*({"type": "image"} for _ in frames), {"type": "text", "text": question}],
        }
    ]
    rendered = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    raw = prepare_inputs(processor, images=frames, prompts=rendered)
    input_ids = mx.array(raw["input_ids"])
    pixel_values = mx.array(raw["pixel_values"])
    mask = mx.array(raw["attention_mask"])
    extra = {
        k: mx.array(v)
        for k, v in raw.items()
        if k not in {"input_ids", "pixel_values", "attention_mask"}
    }
    t0 = time.perf_counter_ns()
    mx.random.seed(42)
    response = generate(
        model,
        processor,
        "",
        input_ids=input_ids,
        pixel_values=pixel_values,
        mask=mask,
        max_tokens=max_tokens,
        temperature=0.0,
        **extra,
    )
    elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000
    return str(response.text), elapsed_ms


def _load_manifest_items(runner: Any, manifest_path: Path) -> list[Any]:
    payload = tomllib.loads(manifest_path.read_text())
    benchmark = payload["benchmark"]
    item_ids = payload["item_ids"]
    return runner._load_items_by_id(benchmark, item_ids)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--n-items", type=int, default=0, help="Cap items (0 = all)")
    parser.add_argument("--reference-frames", type=int, default=32, help="Dense grid to rank from")
    parser.add_argument("--frame-count", type=int, default=8, help="Novelty-ranked frames to keep")
    parser.add_argument(
        "--statistic",
        choices=[s.value for s in BlockStatistic],
        default=BlockStatistic.MAX_ABS.value,
        help="Pixel statistic to rank frames by",
    )
    parser.add_argument("--max-tokens", type=int, default=32)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    if not args.model_path.exists():
        raise SystemExit(f"model path missing: {args.model_path}")
    runner = _load_runner_module()
    items = _load_manifest_items(runner, args.manifest)
    if not items:
        raise SystemExit("no items loaded from manifest")
    if args.n_items > 0:
        items = items[: args.n_items]
    stat = BlockStatistic(args.statistic)

    print(f"loading model: {args.model_path}")
    model, processor = load(str(args.model_path))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    records: list[NoveltyRecord] = []
    with args.output.open("w") as out_f:
        for idx, item in enumerate(items):
            frames, orig_indices = _decode_reference_frames(
                runner,
                item.video_path,
                reference_frames=args.reference_frames,
                start=item.start_seconds,
                end=item.end_seconds,
            )
            scores = _per_frame_novelty(frames, statistic=stat)
            selected = _select_top_novel(scores, frame_count=args.frame_count, force_first=True)
            chosen_frames = [frames[i] for i in selected]
            chosen_indices = [orig_indices[i] for i in selected]
            prompt = runner._multiple_choice_prompt(item.question, item.candidates)
            text, elapsed_ms = _run_inference(
                model, processor, chosen_frames, prompt, max_tokens=args.max_tokens
            )
            choice = extract_choice(text, item.candidates)
            record = NoveltyRecord(
                item_id=item.item_id,
                benchmark=item.benchmark,
                group=item.group,
                reference_frames=args.reference_frames,
                selected_frames=args.frame_count,
                selected_indices=chosen_indices,
                frame_novelty=[float(scores[i]) for i in selected],
                model_text=text,
                choice_index=choice,
                answer_index=item.answer_index,
                correct=(choice is not None and choice == item.answer_index),
                parse_failure=choice is None,
                elapsed_ms=elapsed_ms,
            )
            records.append(record)
            out_f.write(
                json.dumps(
                    {
                        "item_id": record.item_id,
                        "benchmark": record.benchmark,
                        "group": record.group,
                        "reference_frames": record.reference_frames,
                        "selected_frames": record.selected_frames,
                        "selected_indices": record.selected_indices,
                        "frame_novelty": record.frame_novelty,
                        "model_text": record.model_text,
                        "choice_index": record.choice_index,
                        "answer_index": record.answer_index,
                        "correct": record.correct,
                        "parse_failure": record.parse_failure,
                        "elapsed_ms": record.elapsed_ms,
                    }
                )
                + "\n"
            )
            out_f.flush()
            print(
                f"[{idx + 1:3d}/{len(items)}] {item.item_id:<40s} "
                f"correct={record.correct} parse_failure={record.parse_failure} "
                f"elapsed={record.elapsed_ms:.0f}ms"
            )

    total = len(records)
    correct = sum(1 for r in records if r.correct)
    parse_failures = sum(1 for r in records if r.parse_failure)
    summary = {
        "manifest": str(args.manifest),
        "model_path": str(args.model_path),
        "reference_frames": args.reference_frames,
        "frame_count": args.frame_count,
        "statistic": args.statistic,
        "max_tokens": args.max_tokens,
        "n_items": total,
        "correct": correct,
        "accuracy": correct / total if total else 0.0,
        "parse_failures": parse_failures,
        "mean_elapsed_ms": float(np.mean([r.elapsed_ms for r in records])) if records else 0.0,
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    print(
        f"\n=== novelty-ranked dense: accuracy={summary['accuracy']:.3f} "
        f"({correct}/{total}, {parse_failures} parse failures) "
        f"mean_elapsed={summary['mean_elapsed_ms']:.0f}ms"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
