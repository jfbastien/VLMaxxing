#!/usr/bin/env python3
"""Benchmark mlx-vlm language-prefill chunk thresholds without video work.

This diagnostic intentionally bypasses decode, processor, and vision stages. It
feeds synthetic embeddings through the same Gemma language model prefill paths
that ``mlx_vlm.generate`` uses above and below ``prefill_step_size``. The goal is
to explain substrate behavior, not to claim model quality.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, cast

import mlx.core as mx
import numpy as np
from mlx_vlm import load
from mlx_vlm.generate import cache

DEFAULT_MODEL_PATH = Path.home() / "models" / "gemma-4-e4b-it-4bit"
DEFAULT_SEQ_LENS = [1024, 1500, 1573, 2048, 2188, 2560, 3072]
DEFAULT_PREFILL_STEPS = [1024, 1500, 2048, 4096]
SCHEMA_VERSION = "mlx_vlm_prefill_kernel_bench_v1"


def _parse_int_list(value: str) -> list[int]:
    parsed = [int(part.strip()) for part in value.split(",") if part.strip()]
    if not parsed:
        raise argparse.ArgumentTypeError("list must not be empty")
    if any(item <= 0 for item in parsed):
        raise argparse.ArgumentTypeError("all values must be positive")
    return parsed


def _hidden_size(model: Any) -> int:
    for config in (
        getattr(getattr(model, "language_model", model), "config", None),
        getattr(getattr(model, "config", None), "text_config", None),
        getattr(model, "config", None),
    ):
        for attr in ("hidden_size", "model_dim", "dim"):
            value = getattr(config, attr, None)
            if value is not None:
                return int(value)
    for path in (
        ("language_model", "model", "embed_tokens", "weight"),
        ("language_model", "embed_tokens", "weight"),
        ("model", "embed_tokens", "weight"),
    ):
        value = model
        for attr in path:
            value = getattr(value, attr, None)
            if value is None:
                break
        if value is not None and hasattr(value, "shape") and len(value.shape) >= 2:
            return int(value.shape[-1])
    raise ValueError("could not infer language-model hidden size")


def _cache_states(prompt_cache: list[Any]) -> list[Any]:
    return [entry.state for entry in prompt_cache]


def _run_prefill_once(
    model: Any,
    *,
    seq_len: int,
    prefill_step_size: int,
    hidden_size: int,
) -> dict[str, Any]:
    input_ids = mx.zeros((1, seq_len), dtype=mx.int32)
    inputs_embeds = mx.random.normal((1, seq_len, hidden_size))
    prompt_cache = cache.make_prompt_cache(model.language_model)
    language_model_calls = 0
    t0 = time.perf_counter_ns()
    if seq_len > prefill_step_size:
        while inputs_embeds.shape[1] > 1:
            n_to_process = min(prefill_step_size, inputs_embeds.shape[1] - 1)
            model.language_model(
                inputs=input_ids[:, :n_to_process],
                inputs_embeds=inputs_embeds[:, :n_to_process],
                cache=prompt_cache,
                n_to_process=n_to_process,
            )
            language_model_calls += 1
            mx.eval(_cache_states(prompt_cache))
            inputs_embeds = inputs_embeds[:, n_to_process:]
            input_ids = input_ids[:, n_to_process:]
            mx.clear_cache()
        input_ids = input_ids[:, -1:]
    outputs = model.language_model(
        input_ids,
        inputs_embeds=inputs_embeds,
        cache=prompt_cache,
    )
    language_model_calls += 1
    mx.eval(outputs.logits, _cache_states(prompt_cache))
    elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000
    return {
        "seq_len": seq_len,
        "prefill_step_size": prefill_step_size,
        "chunked": seq_len > prefill_step_size,
        "language_model_calls": language_model_calls,
        "elapsed_ms": elapsed_ms,
        "tokens_per_second": float(seq_len / (elapsed_ms / 1000.0)) if elapsed_ms > 0 else 0.0,
    }


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[float]] = {}
    for row in rows:
        key = f"{row['seq_len']}@{row['prefill_step_size']}"
        groups.setdefault(key, []).append(float(row["elapsed_ms"]))
    return {
        key: {
            "mean_ms": float(np.mean(values)),
            "min_ms": float(np.min(values)),
            "max_ms": float(np.max(values)),
            "n": len(values),
        }
        for key, values in sorted(groups.items())
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--seq-lens", type=_parse_int_list, default=DEFAULT_SEQ_LENS)
    parser.add_argument("--prefill-step-sizes", type=_parse_int_list, default=DEFAULT_PREFILL_STEPS)
    parser.add_argument("--warmup-repeats", type=int, default=1)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.warmup_repeats < 0:
        raise SystemExit("--warmup-repeats must be nonnegative")
    if args.repeats <= 0:
        raise SystemExit("--repeats must be positive")

    model, _processor = load(args.model_path)
    hidden_size = _hidden_size(model)
    rows: list[dict[str, Any]] = []
    max_seq_len = max(cast(list[int], args.seq_lens))
    first_step = cast(list[int], args.prefill_step_sizes)[0]
    for _ in range(args.warmup_repeats):
        _run_prefill_once(
            model,
            seq_len=max_seq_len,
            prefill_step_size=first_step,
            hidden_size=hidden_size,
        )
        mx.clear_cache()

    for seq_len in cast(list[int], args.seq_lens):
        for prefill_step_size in cast(list[int], args.prefill_step_sizes):
            for repeat_idx in range(args.repeats):
                mx.random.seed(42 + repeat_idx)
                row = _run_prefill_once(
                    model,
                    seq_len=seq_len,
                    prefill_step_size=prefill_step_size,
                    hidden_size=hidden_size,
                )
                row["repeat_idx"] = repeat_idx
                rows.append(row)
                mx.clear_cache()

    payload = {
        "schema_version": SCHEMA_VERSION,
        "model_path": str(args.model_path),
        "seq_lens": args.seq_lens,
        "prefill_step_sizes": args.prefill_step_sizes,
        "warmup_repeats": args.warmup_repeats,
        "repeats": args.repeats,
        "hidden_size": hidden_size,
        "rows": rows,
        "summary": _summarize(rows),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(args.output), "rows": len(rows)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
