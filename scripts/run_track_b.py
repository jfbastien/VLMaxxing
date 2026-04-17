#!/usr/bin/env python3
"""Phase 1.30 / claim #5 Track B wall-clock harness.

Times the dense Qwen 2.5-VL path with phase-level granularity. Two modes:

  --mode mc_scoring   (default)   decode | preprocess | vision | prefill
  --mode full_generation          decode | preprocess | vision | generation

Reports peak GPU memory on MLX (Apple Silicon). The output is a JSONL
with one record per timed item plus a summary JSON. This is NOT sparse
execution — it is the dense-baseline measurement discipline required
to stop reporting Track B numbers as "prospective" in
paper/claim-matrix.md claim #5.

Why two modes? Our Track A MC-scoring path terminates after one
prefill forward pass (read logits at the last position over the answer
letters). That is the inference cost the Track A caching claim speeds
up. In contrast, a full generative query ends with an autoregressive
decode loop. mlx-vlm's ``generate()`` re-runs prefill internally, so
timing prefill and generation separately would double-count; the modes
are exclusive to avoid that.

Design notes:
- Reuses the runner's item loaders and frame decoders via importlib so
  Track A and Track B preprocessing stay in lockstep.
- A warmup item is run once and excluded from records to absorb
  first-compile JIT and mlx-vlm graph capture.
- Timing is ``time.perf_counter_ns``; peak memory is the MLX value
  returned by ``mx.get_peak_memory()`` after ``mx.eval``.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
import sys
import time
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import mlx.core as mx
from mlx_vlm import generate, load  # type: ignore[import-untyped]
from mlx_vlm.utils import prepare_inputs  # type: ignore[import-untyped]

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO_ROOT / "scripts" / "run_benchmark_track_a.py"

DEFAULT_MODEL_PATH = Path.home() / "models" / "Qwen2.5-VL-7B-Instruct-4bit"


def _load_runner_module() -> Any:
    """Load the Track A runner as a module."""

    name = "_track_b_runner"
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
class PhaseRecord:
    item_id: str
    benchmark: str
    group: str
    frame_count: int
    mode: str
    decode_ms: float
    preprocess_ms: float
    vision_encode_ms: float
    # Exactly one of the two below is populated depending on --mode.
    # The other is 0.0 and should be ignored.
    prefill_ms: float
    generation_ms: float
    generation_tokens: int
    total_ms: float
    # Peak memory per GPU phase (GB).
    peak_memory_after_vision_gb: float
    peak_memory_after_inference_gb: float


def _bytes_to_gb(b: int) -> float:
    return b / (1024**3)


def _now_ms(start_ns: int) -> float:
    return (time.perf_counter_ns() - start_ns) / 1_000_000


def _warmup(model: Any, processor: Any, runner: Any, warm_item: Any, frame_count: int) -> None:
    sample = runner._prepare_sample(model, processor, warm_item, frame_count=frame_count)
    dtype = model.vision_tower.patch_embed.proj.weight.dtype
    features = model.vision_tower(
        sample.pixel_values.astype(dtype),
        sample.extra_kwargs["image_grid_thw"],
        output_hidden_states=False,
    )
    mx.eval(features)
    # Dry-run prefill so the mlx-vlm generate path hits a compiled code
    # path on the first measured item.
    _ = model(sample.input_ids, sample.pixel_values, mask=sample.mask, **sample.extra_kwargs)
    mx.eval(_)


def _time_one_item(
    model: Any,
    processor: Any,
    runner: Any,
    item: Any,
    *,
    mode: str,
    frame_count: int,
    max_tokens: int,
) -> PhaseRecord:
    total_start = time.perf_counter_ns()

    # --- Decode -------------------------------------------------------
    t0 = time.perf_counter_ns()
    frames, active_boxes = runner._decode_uniform_frames(
        item.video_path,
        frame_count=frame_count,
        start_seconds=item.start_seconds,
        end_seconds=item.end_seconds,
    )
    decode_ms = _now_ms(t0)

    # --- Preprocess (tokenize + pixel prep) ---------------------------
    t0 = time.perf_counter_ns()
    # Disable processor-side resizing exactly as the runner does so the
    # measured preprocess path stays in sync.
    if hasattr(processor, "image_processor"):
        if hasattr(processor.image_processor, "do_resize"):
            processor.image_processor.do_resize = False
        if hasattr(processor.image_processor, "do_image_splitting"):
            processor.image_processor.do_image_splitting = False
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
    mx.eval(input_ids, pixel_values, mask)
    preprocess_ms = _now_ms(t0)

    # --- Vision encode ------------------------------------------------
    mx.reset_peak_memory()
    t0 = time.perf_counter_ns()
    dtype = model.vision_tower.patch_embed.proj.weight.dtype
    features = model.vision_tower(
        pixel_values.astype(dtype),
        extra_kwargs["image_grid_thw"],
        output_hidden_states=False,
    )
    mx.eval(features)
    vision_encode_ms = _now_ms(t0)
    peak_after_vision = _bytes_to_gb(mx.get_peak_memory())

    # --- Inference (exactly one of prefill / generation) -------------
    prefill_ms = 0.0
    generation_ms = 0.0
    generation_tokens = 0
    mx.reset_peak_memory()
    if mode == "mc_scoring":
        t0 = time.perf_counter_ns()
        outputs = model(input_ids, pixel_values, mask=mask, **extra_kwargs)
        logits = outputs.logits[0, -1, :]
        _logprobs = logits - mx.logsumexp(logits, keepdims=True)
        mx.eval(_logprobs)
        prefill_ms = _now_ms(t0)
        del outputs
    elif mode == "full_generation":
        t0 = time.perf_counter_ns()
        response = generate(
            model,
            processor,
            "",
            input_ids=input_ids,
            pixel_values=pixel_values,
            mask=mask,
            max_tokens=max_tokens,
            temperature=0.0,
            **extra_kwargs,
        )
        generation_ms = _now_ms(t0)
        generation_tokens = int(response.generation_tokens)
    else:
        raise ValueError(f"unknown mode: {mode!r}")
    peak_after_inference = _bytes_to_gb(mx.get_peak_memory())

    total_ms = _now_ms(total_start)
    del features, active_boxes

    return PhaseRecord(
        item_id=item.item_id,
        benchmark=item.benchmark,
        group=item.group,
        frame_count=frame_count,
        mode=mode,
        decode_ms=decode_ms,
        preprocess_ms=preprocess_ms,
        vision_encode_ms=vision_encode_ms,
        prefill_ms=prefill_ms,
        generation_ms=generation_ms,
        generation_tokens=generation_tokens,
        total_ms=total_ms,
        peak_memory_after_vision_gb=peak_after_vision,
        peak_memory_after_inference_gb=peak_after_inference,
    )


def _summarize(records: list[PhaseRecord]) -> dict[str, Any]:
    def stats(values: list[float]) -> dict[str, float]:
        values_sorted = sorted(values)
        if not values_sorted:
            return {"n": 0}
        return {
            "n": len(values_sorted),
            "mean": statistics.fmean(values_sorted),
            "median": statistics.median(values_sorted),
            "min": values_sorted[0],
            "max": values_sorted[-1],
            "p95": values_sorted[int(0.95 * (len(values_sorted) - 1))],
        }

    phases = [
        "decode_ms",
        "preprocess_ms",
        "vision_encode_ms",
        "prefill_ms",
        "generation_ms",
        "total_ms",
        "generation_tokens",
        "peak_memory_after_vision_gb",
        "peak_memory_after_inference_gb",
    ]
    summary: dict[str, Any] = {"n_items": len(records)}
    for phase in phases:
        summary[phase] = stats([getattr(r, phase) for r in records])
    return summary


def _load_manifest_items(runner: Any, manifest_path: Path) -> list[Any]:
    payload = tomllib.loads(manifest_path.read_text())
    benchmark = payload["benchmark"]
    item_ids = payload["item_ids"]
    return runner._load_items_by_id(benchmark, item_ids)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--n-items", type=int, default=0, help="Cap items (0 = all)")
    parser.add_argument("--frame-count", type=int, default=8)
    parser.add_argument(
        "--mode",
        choices=["mc_scoring", "full_generation"],
        default="mc_scoring",
        help="mc_scoring = one prefill forward pass; full_generation = autoregressive decode",
    )
    parser.add_argument("--max-tokens", type=int, default=8)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--output", type=Path, required=True, help="Per-item JSONL")
    parser.add_argument("--summary", type=Path, required=True, help="Aggregate summary JSON")
    args = parser.parse_args()

    if not args.model_path.exists():
        raise SystemExit(f"model path missing: {args.model_path}")

    runner = _load_runner_module()
    items = _load_manifest_items(runner, args.manifest)
    if not items:
        raise SystemExit("no items loaded from manifest")
    if args.n_items > 0:
        items = items[: args.n_items]

    print(f"loading model: {args.model_path}")
    model, processor = load(str(args.model_path))

    # One warmup pass on the first item (excluded from records) so
    # reported numbers are steady-state.
    print(f"warmup on {items[0].item_id}")
    _warmup(model, processor, runner, items[0], frame_count=args.frame_count)
    mx.reset_peak_memory()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    records: list[PhaseRecord] = []
    with args.output.open("w") as out_f:
        for idx, item in enumerate(items):
            t = time.perf_counter_ns()
            record = _time_one_item(
                model,
                processor,
                runner,
                item,
                mode=args.mode,
                frame_count=args.frame_count,
                max_tokens=args.max_tokens,
            )
            records.append(record)
            out_f.write(json.dumps(asdict(record)) + "\n")
            out_f.flush()
            item_wall = (time.perf_counter_ns() - t) / 1000.0
            print(
                f"[{idx + 1:3d}/{len(items)}] {item.item_id:<40s} "
                f"decode={record.decode_ms:6.1f} "
                f"prep={record.preprocess_ms:6.1f} "
                f"vit={record.vision_encode_ms:6.1f} "
                f"prefill={record.prefill_ms:6.1f} "
                f"gen={record.generation_ms:6.1f} "
                f"total={record.total_ms:7.1f} ms "
                f"(wall {item_wall / 1000:.0f}ms)"
            )

    summary = _summarize(records)
    summary["manifest"] = str(args.manifest)
    summary["model_path"] = str(args.model_path)
    summary["mode"] = args.mode
    summary["frame_count"] = args.frame_count
    summary["max_tokens"] = args.max_tokens
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    print("\n=== Track B summary ===")
    for phase in [
        "decode_ms",
        "preprocess_ms",
        "vision_encode_ms",
        "prefill_ms",
        "generation_ms",
        "total_ms",
    ]:
        s = summary[phase]
        print(
            f"  {phase:<22s} mean={s['mean']:8.2f} median={s['median']:8.2f} "
            f"p95={s['p95']:8.2f} min={s['min']:8.2f} max={s['max']:8.2f}"
        )
    mem = summary["peak_memory_after_inference_gb"]
    print(
        f"  peak_mem_gb (post-inference)  mean={mem['mean']:.2f} "
        f"p95={mem['p95']:.2f} max={mem['max']:.2f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
