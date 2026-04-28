#!/usr/bin/env python3
"""Phase 1.30AG — K/V cache-distance probe for the 1.30 boundary.

The probe reruns a small set of 1.30AC/AD follow-up rows and captures the
language-model prompt cache after the current follow-up prompt under:

1. dense current-query prefill,
2. Q0 cache-reuse plus current text-tail prefill, and
3. cache-invalidated current-query prefill with follow-up vision pruning.

It then reports layerwise K/V cosine and mean-absolute distance to the dense
current-query cache. This is a mechanism probe, not a new accuracy cell.
"""

from __future__ import annotations

import argparse
import gc
import json
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

from run_kv_selective_reprefill_v2 import (  # noqa: E402
    DEFAULT_MODEL_PATH,
    QWEN_IMAGE_TOKEN_ID,
    _load_videomme_rows,
    _prepare_sample,
    _questions_for_video_id,
)

from codec_through.qwen_pruned_vision_tower import (  # noqa: E402
    QwenVisionPruneConfig,
    set_qwen_vision_tower_config,
)
from codec_through.qwen_selective_reprefill import (  # noqa: E402
    common_prefix_token_count,
    compute_qwen_position_ids,
    compute_qwen_token_cut_plan,
    generate_qwen_tail_with_explicit_positions,
    make_qwen_prefix_cache,
    rewind_qwen_prefix_cache,
    slice_qwen_prompt_for_reprefill,
)

DEFAULT_ATTRIBUTION = Path(
    "research/experiments/2026/artifacts/phase1_30AF_cache_boundary_attribution/"
    "attribution_summary.json"
)
DEFAULT_OUTPUT_DIR = Path("research/experiments/2026/artifacts/phase1_30AG_kcache_distance_probe")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


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


def _full_prompt_cache(*, model: Any, sample: Any) -> tuple[list[Any], float]:
    position_ids = compute_qwen_position_ids(
        model=model,
        input_ids=sample.input_ids,
        image_grid_thw=sample.extra_kwargs["image_grid_thw"],
        mask=sample.mask,
    )
    full_len = int(sample.input_ids.shape[1])
    full_grid = np.asarray(sample.extra_kwargs["image_grid_thw"].tolist(), dtype=np.int64)
    plan = compute_qwen_token_cut_plan(
        input_ids=np.asarray(sample.input_ids.tolist(), dtype=np.int64).reshape(-1),
        image_grid_thw=full_grid,
        trunc_token_idx=full_len,
        image_token_id=QWEN_IMAGE_TOKEN_ID,
        spatial_merge_size=_spatial_merge_size(model),
    )
    prefix, _tail = slice_qwen_prompt_for_reprefill(
        input_ids=sample.input_ids,
        mask=sample.mask,
        pixel_values=sample.pixel_values,
        image_grid_thw=sample.extra_kwargs["image_grid_thw"],
        position_ids=position_ids,
        plan=plan,
    )
    return make_qwen_prefix_cache(model=model, prefix=prefix)


def _reuse_q0_to_current_cache(
    *,
    model: Any,
    processor: Any,
    q0_sample: Any,
    current_sample: Any,
    max_tokens: int,
    seed: int,
) -> tuple[list[Any], dict[str, Any]]:
    q0_cache, q0_cache_ms = _full_prompt_cache(model=model, sample=q0_sample)
    q0_ids = np.asarray(q0_sample.input_ids.tolist(), dtype=np.int64).reshape(-1)
    current_ids = np.asarray(current_sample.input_ids.tolist(), dtype=np.int64).reshape(-1)
    shared_prefix = common_prefix_token_count(q0_ids, current_ids)
    if shared_prefix <= 0:
        raise RuntimeError("Q0 and current follow-up prompt share no token prefix")
    rewind_qwen_prefix_cache(
        prompt_cache=q0_cache,
        appended_prompt_tokens=int(q0_ids.size - shared_prefix),
        appended_generation_tokens=0,
    )
    position_ids = compute_qwen_position_ids(
        model=model,
        input_ids=current_sample.input_ids,
        image_grid_thw=current_sample.extra_kwargs["image_grid_thw"],
        mask=current_sample.mask,
    )
    plan = compute_qwen_token_cut_plan(
        input_ids=current_ids,
        image_grid_thw=np.asarray(
            current_sample.extra_kwargs["image_grid_thw"].tolist(), dtype=np.int64
        ),
        trunc_token_idx=shared_prefix,
        image_token_id=QWEN_IMAGE_TOKEN_ID,
        spatial_merge_size=_spatial_merge_size(model),
    )
    _prefix, tail = slice_qwen_prompt_for_reprefill(
        input_ids=current_sample.input_ids,
        mask=current_sample.mask,
        pixel_values=current_sample.pixel_values,
        image_grid_thw=current_sample.extra_kwargs["image_grid_thw"],
        position_ids=position_ids,
        plan=plan,
    )
    result = generate_qwen_tail_with_explicit_positions(
        model=model,
        processor=processor,
        prompt_cache=q0_cache,
        tail=tail,
        full_prompt_tokens=int(current_sample.input_ids.shape[1]),
        max_tokens=max_tokens,
        seed=seed,
    )
    metadata = {
        "q0_cache_ms": q0_cache_ms,
        "tail_prefill_ms": result["prefill_ms"],
        "shared_prefix_tokens": shared_prefix,
        "tail_prompt_tokens": result["tail_prompt_tokens"],
        "prefix_coverage": result["prefix_coverage"],
    }
    return q0_cache, metadata


def _cache_arrays(entry: Any, name: str) -> mx.array | None:
    value = getattr(entry, name, None)
    if value is None:
        return None
    return value


def _distance_for_arrays(left: mx.array, right: mx.array) -> dict[str, float]:
    if len(left.shape) < 3 or len(right.shape) < 3:
        raise ValueError(f"expected cache tensors with >=3 dims, got {left.shape}, {right.shape}")
    if int(left.shape[2]) != int(right.shape[2]):
        raise ValueError(
            "cache-token length mismatch in K/V distance probe: "
            f"{left.shape[2]} != {right.shape[2]}"
        )
    common_len = int(left.shape[2])
    left_common = left
    right_common = right
    l_flat = left_common.reshape(-1)
    r_flat = right_common.reshape(-1)
    dot = mx.sum(l_flat * r_flat)
    denom = mx.sqrt(mx.sum(l_flat * l_flat)) * mx.sqrt(mx.sum(r_flat * r_flat))
    cosine = dot / mx.maximum(denom, mx.array(1e-12))
    mean_abs = mx.mean(mx.abs(l_flat - r_flat))
    rms = mx.sqrt(mx.mean((l_flat - r_flat) * (l_flat - r_flat)))
    mx.eval(cosine, mean_abs, rms)
    return {
        "cosine": float(cosine.item()),
        "mean_abs": float(mean_abs.item()),
        "rms": float(rms.item()),
        "common_tokens": common_len,
        "left_tokens": int(left.shape[2]),
        "right_tokens": int(right.shape[2]),
    }


def _cache_distance(left: list[Any], right: list[Any]) -> dict[str, Any]:
    layer_rows: list[dict[str, Any]] = []
    for layer_idx, (left_entry, right_entry) in enumerate(zip(left, right, strict=True)):
        row: dict[str, Any] = {"layer": layer_idx}
        for name in ("keys", "values"):
            left_array = _cache_arrays(left_entry, name)
            right_array = _cache_arrays(right_entry, name)
            if left_array is None or right_array is None:
                row[f"{name}_available"] = False
                continue
            row[f"{name}_available"] = True
            metric = _distance_for_arrays(left_array, right_array)
            for metric_name, metric_value in metric.items():
                row[f"{name}_{metric_name}"] = metric_value
        layer_rows.append(row)
    aggregate: dict[str, Any] = {"layers": layer_rows}
    for name in ("keys", "values"):
        cosines = [
            float(row[f"{name}_cosine"]) for row in layer_rows if row.get(f"{name}_available")
        ]
        mean_abs = [
            float(row[f"{name}_mean_abs"]) for row in layer_rows if row.get(f"{name}_available")
        ]
        rms = [float(row[f"{name}_rms"]) for row in layer_rows if row.get(f"{name}_available")]
        aggregate[f"{name}_mean_cosine"] = float(np.mean(cosines)) if cosines else None
        aggregate[f"{name}_mean_abs"] = float(np.mean(mean_abs)) if mean_abs else None
        aggregate[f"{name}_mean_rms"] = float(np.mean(rms)) if rms else None
    return aggregate


def _drift_class(row: dict[str, Any]) -> str:
    reuse_drift = bool(row["reuse_any_drift"])
    invalidated_drift = bool(row["invalidated_any_drift"])
    if reuse_drift and invalidated_drift:
        return "shared_drift"
    if reuse_drift:
        return "reuse_only_drift"
    if invalidated_drift:
        return "invalidated_only_drift"
    return "stable"


def _select_rows(
    *,
    reuse_rows: list[dict[str, Any]],
    invalidated_rows: list[dict[str, Any]],
    max_pairs: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_key: dict[tuple[str, int], dict[str, Any]] = {}
    invalidated_by_key = {
        (str(row["video_id"]), int(row["q_index"])): row
        for row in invalidated_rows
        if int(row["q_index"]) > 0
    }
    for row in reuse_rows:
        if int(row["q_index"]) <= 0:
            continue
        key = (str(row["video_id"]), int(row["q_index"]))
        other = invalidated_by_key.get(key)
        if other is None:
            continue
        reuse_drift = bool(row["cold_choice"] != row["streaming_choice"])
        invalidated_drift = bool(other["cold_choice"] != other["streaming_choice"])
        reuse_correctness_drift = bool(row["cold_correct"] != row["streaming_correct"])
        invalidated_correctness_drift = bool(other["cold_correct"] != other["streaming_correct"])
        by_key[key] = {
            "video_id": key[0],
            "q_index": key[1],
            "duration": row["duration"],
            "reuse_choice_drift": reuse_drift,
            "invalidated_choice_drift": invalidated_drift,
            "reuse_correctness_drift": reuse_correctness_drift,
            "invalidated_correctness_drift": invalidated_correctness_drift,
            "reuse_any_drift": reuse_drift or reuse_correctness_drift,
            "invalidated_any_drift": invalidated_drift or invalidated_correctness_drift,
        }
    classes = {
        "shared_drift": [],
        "reuse_only_drift": [],
        "invalidated_only_drift": [],
        "stable": [],
    }
    for row in by_key.values():
        classes[_drift_class(row)].append(row)
    for rows in classes.values():
        rows.sort(key=lambda row: (str(row["video_id"]), int(row["q_index"])))

    target_per_class = max(1, max_pairs // len(classes))
    selected: list[dict[str, Any]] = []
    for class_name in ("shared_drift", "reuse_only_drift", "invalidated_only_drift", "stable"):
        selected.extend(classes[class_name][:target_per_class])
    if len(selected) < max_pairs:
        selected_keys = {(row["video_id"], row["q_index"]) for row in selected}
        remaining = sorted(
            [
                row
                for row in by_key.values()
                if (row["video_id"], row["q_index"]) not in selected_keys
            ],
            key=lambda row: (
                not (row["reuse_any_drift"] or row["invalidated_any_drift"]),
                str(row["video_id"]),
                int(row["q_index"]),
            ),
        )
        selected.extend(remaining[: max_pairs - len(selected)])
    selected = selected[:max_pairs]
    for row in selected:
        row["drift_class"] = _drift_class(row)
    metadata = {
        "available_by_drift_class": {name: len(rows) for name, rows in classes.items()},
        "selected_by_drift_class": {
            name: sum(1 for row in selected if row["drift_class"] == name) for name in classes
        },
        "target_per_class": target_per_class,
    }
    return selected, metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attribution-summary", type=Path, default=DEFAULT_ATTRIBUTION)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-pairs", type=int, default=20)
    parser.add_argument("--vision-tower-layer", type=int, default=2)
    parser.add_argument("--vision-tower-keep-rate", type=float, default=0.50)
    parser.add_argument("--max-tokens", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    payload = json.loads(args.attribution_summary.read_text())
    reuse_path = Path(payload["cache_reuse"]["pairs"])
    invalidated_path = Path(payload["cache_invalidated"]["pairs"])
    selected, selection_metadata = _select_rows(
        reuse_rows=_read_jsonl(reuse_path),
        invalidated_rows=_read_jsonl(invalidated_path),
        max_pairs=args.max_pairs,
    )
    if not selected:
        raise RuntimeError("no paired 1.30 follow-up rows selected for K/V probe")

    print(f"[1.30AG] loading model from {args.model_path}")
    model, processor = load(str(args.model_path))
    rows = _load_videomme_rows()
    frame_cache: dict[str, Any] = {}
    output_rows: list[dict[str, Any]] = []
    t0 = time.perf_counter_ns()
    row_path = args.output_dir / "kcache_distance_rows.jsonl"

    with row_path.open("w") as handle:
        for selected_row in selected:
            video_id = selected_row["video_id"]
            q_index = int(selected_row["q_index"])
            questions = _questions_for_video_id(video_id, rows)
            q0_sample = _prepare_sample(
                processor,
                questions[0],
                frame_count=8,
                frame_cache=frame_cache,
            )
            current_sample = _prepare_sample(
                processor,
                questions[q_index],
                frame_count=8,
                frame_cache=frame_cache,
            )

            set_qwen_vision_tower_config(
                model,
                QwenVisionPruneConfig(
                    layer_idx=args.vision_tower_layer,
                    keep_rate=1.0,
                ),
            )
            dense_cache, dense_ms = _full_prompt_cache(model=model, sample=current_sample)
            reuse_cache, reuse_meta = _reuse_q0_to_current_cache(
                model=model,
                processor=processor,
                q0_sample=q0_sample,
                current_sample=current_sample,
                max_tokens=args.max_tokens,
                seed=args.seed,
            )
            set_qwen_vision_tower_config(
                model,
                QwenVisionPruneConfig(
                    layer_idx=args.vision_tower_layer,
                    keep_rate=args.vision_tower_keep_rate,
                ),
            )
            pruned_cache, pruned_ms = _full_prompt_cache(model=model, sample=current_sample)
            set_qwen_vision_tower_config(
                model,
                QwenVisionPruneConfig(
                    layer_idx=args.vision_tower_layer,
                    keep_rate=1.0,
                ),
            )

            row = {
                **selected_row,
                "dense_cache_ms": dense_ms,
                "reuse_cache_metadata": reuse_meta,
                "pruned_cache_ms": pruned_ms,
                "reuse_vs_dense": _cache_distance(reuse_cache, dense_cache),
                "pruned_vs_dense": _cache_distance(pruned_cache, dense_cache),
            }
            output_rows.append(row)
            handle.write(json.dumps(row, sort_keys=True) + "\n")
            handle.flush()
            print(
                f"[1.30AG] {video_id} q={q_index}: "
                f"reuse K cos={row['reuse_vs_dense']['keys_mean_cosine']:.4f}, "
                f"pruned K cos={row['pruned_vs_dense']['keys_mean_cosine']:.4f}"
            )
            del dense_cache, reuse_cache, pruned_cache
            gc.collect()
            mx.clear_cache()

    def _mean(path: str) -> float | None:
        values = []
        for row in output_rows:
            cursor: Any = row
            for part in path.split("."):
                cursor = cursor[part]
            if cursor is not None:
                values.append(float(cursor))
        return float(np.mean(values)) if values else None

    def _class_summary(class_name: str) -> dict[str, Any]:
        class_rows = [row for row in output_rows if row["drift_class"] == class_name]
        if not class_rows:
            return {"drift_class": class_name, "n": 0}

        def _class_mean(path: str) -> float | None:
            values = []
            for row in class_rows:
                cursor: Any = row
                for part in path.split("."):
                    cursor = cursor[part]
                if cursor is not None:
                    values.append(float(cursor))
            return float(np.mean(values)) if values else None

        return {
            "drift_class": class_name,
            "n": len(class_rows),
            "mean_reuse_keys_cosine": _class_mean("reuse_vs_dense.keys_mean_cosine"),
            "mean_pruned_keys_cosine": _class_mean("pruned_vs_dense.keys_mean_cosine"),
            "mean_reuse_values_cosine": _class_mean("reuse_vs_dense.values_mean_cosine"),
            "mean_pruned_values_cosine": _class_mean("pruned_vs_dense.values_mean_cosine"),
            "mean_reuse_keys_mean_abs": _class_mean("reuse_vs_dense.keys_mean_abs"),
            "mean_pruned_keys_mean_abs": _class_mean("pruned_vs_dense.keys_mean_abs"),
        }

    by_drift_class = {
        name: _class_summary(name)
        for name in ("shared_drift", "reuse_only_drift", "invalidated_only_drift", "stable")
    }

    def _relative_gap(left: float | None, right: float | None) -> float | None:
        if left is None or right is None:
            return None
        denom = max(abs(left), abs(right), 1e-12)
        return abs(left - right) / denom

    keys_mean_abs_gap = _relative_gap(
        _mean("reuse_vs_dense.keys_mean_abs"),
        _mean("pruned_vs_dense.keys_mean_abs"),
    )
    values_mean_abs_gap = _relative_gap(
        _mean("reuse_vs_dense.values_mean_abs"),
        _mean("pruned_vs_dense.values_mean_abs"),
    )
    pass_h1_capture = bool(
        output_rows
        and all(row["reuse_vs_dense"]["keys_mean_cosine"] is not None for row in output_rows)
        and all(row["pruned_vs_dense"]["keys_mean_cosine"] is not None for row in output_rows)
    )
    pass_h2_distance_report = all(
        int(selection_metadata["selected_by_drift_class"].get(name, 0)) > 0
        for name in ("shared_drift", "reuse_only_drift", "invalidated_only_drift", "stable")
    )
    pass_h3_outcome_link = pass_h2_distance_report and all(
        by_drift_class[name].get("mean_reuse_keys_mean_abs") is not None
        for name in ("shared_drift", "reuse_only_drift", "invalidated_only_drift", "stable")
    )
    pass_h4_saturation_test = (
        keys_mean_abs_gap is not None
        and values_mean_abs_gap is not None
        and keys_mean_abs_gap <= 0.10
        and values_mean_abs_gap <= 0.10
    )

    summary = {
        "phase": "1.30AG",
        "n_rows": len(output_rows),
        "max_pairs_requested": args.max_pairs,
        "selection": selection_metadata,
        "vision_tower_layer": args.vision_tower_layer,
        "vision_tower_keep_rate": args.vision_tower_keep_rate,
        "mean_reuse_keys_cosine": _mean("reuse_vs_dense.keys_mean_cosine"),
        "mean_pruned_keys_cosine": _mean("pruned_vs_dense.keys_mean_cosine"),
        "mean_reuse_values_cosine": _mean("reuse_vs_dense.values_mean_cosine"),
        "mean_pruned_values_cosine": _mean("pruned_vs_dense.values_mean_cosine"),
        "mean_reuse_keys_mean_abs": _mean("reuse_vs_dense.keys_mean_abs"),
        "mean_pruned_keys_mean_abs": _mean("pruned_vs_dense.keys_mean_abs"),
        "mean_reuse_values_mean_abs": _mean("reuse_vs_dense.values_mean_abs"),
        "mean_pruned_values_mean_abs": _mean("pruned_vs_dense.values_mean_abs"),
        "keys_mean_abs_relative_gap": keys_mean_abs_gap,
        "values_mean_abs_relative_gap": values_mean_abs_gap,
        "by_drift_class": by_drift_class,
        "pass_H1_capture": pass_h1_capture,
        "pass_H2_distance_report": pass_h2_distance_report,
        "pass_H3_outcome_link": pass_h3_outcome_link,
        "pass_H4_saturation_test": pass_h4_saturation_test,
        "headline_pass": pass_h1_capture
        and pass_h2_distance_report
        and pass_h3_outcome_link
        and pass_h4_saturation_test,
        "row_jsonl": row_path.as_posix(),
        "wall_time_s": (time.perf_counter_ns() - t0) / 1e9,
    }
    summary_path = args.output_dir / "kcache_distance_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(f"[1.30AG] wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
