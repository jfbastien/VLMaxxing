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


def _scalar_offset(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, np.integer):
        return int(value)
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return int(item())
        except (TypeError, ValueError):
            pass
    array = np.asarray(value)
    if array.size != 1:
        raise ValueError(
            "batched/vector cache offsets are unsupported in 1.30AG; "
            f"got offset shape {array.shape}"
        )
    return int(array.reshape(-1)[0])


def _cache_window(entry: Any, name: str) -> dict[str, Any] | None:
    value = getattr(entry, name, None)
    if value is None:
        return None
    if len(value.shape) < 3:
        raise ValueError(f"expected cache tensor with >=3 dims, got {value.shape}")
    buffer_tokens = int(value.shape[-2])
    raw_offset = getattr(entry, "offset", buffer_tokens)
    valid_tokens = _scalar_offset(raw_offset)
    if valid_tokens < 0 or valid_tokens > buffer_tokens:
        raise ValueError(
            f"invalid cache offset for {name}: offset={valid_tokens}, buffer_tokens={buffer_tokens}"
        )
    slices = [slice(None)] * len(value.shape)
    slices[-2] = slice(0, valid_tokens)
    return {
        "array": value[tuple(slices)],
        "raw_array": value,
        "valid_tokens": valid_tokens,
        "buffer_tokens": buffer_tokens,
        "dtype": str(value.dtype),
    }


def _token_prefix(array: mx.array, common_tokens: int) -> mx.array:
    slices = [slice(None)] * len(array.shape)
    slices[-2] = slice(0, common_tokens)
    return array[tuple(slices)]


def _finite_or_none(value: float) -> float | None:
    """Replace NaN/Inf with None so allow_nan=False JSON dumps cleanly."""
    import math

    if math.isnan(value) or math.isinf(value):
        return None
    return float(value)


def _audit_flat(flat: mx.array) -> dict[str, Any]:
    """Read-only NaN/Inf/max-abs telemetry on a flattened cache window."""
    has_nan = mx.any(mx.isnan(flat))
    has_inf = mx.any(mx.isinf(flat))
    max_abs = mx.max(mx.abs(flat))
    mx.eval(has_nan, has_inf, max_abs)
    return {
        "has_nan": bool(has_nan.item()),
        "has_inf": bool(has_inf.item()),
        "max_abs": _finite_or_none(float(max_abs.item())),
    }


def _distance_for_windows(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_array = left["array"]
    right_array = right["array"]
    if len(left_array.shape) < 3 or len(right_array.shape) < 3:
        raise ValueError(
            f"expected cache tensors with >=3 dims, got {left_array.shape}, {right_array.shape}"
        )
    if tuple(left_array.shape[:-2]) != tuple(right_array.shape[:-2]) or int(
        left_array.shape[-1]
    ) != int(right_array.shape[-1]):
        raise ValueError(
            "cache non-token shape mismatch in K/V distance probe: "
            f"{left_array.shape} != {right_array.shape}"
        )
    left_tokens = int(left["valid_tokens"])
    right_tokens = int(right["valid_tokens"])
    common_len = min(left_tokens, right_tokens)
    if common_len <= 0:
        raise ValueError(
            "cache distance probe cannot compare empty valid cache windows: "
            f"{left_tokens} vs {right_tokens}"
        )
    left_common = _token_prefix(left_array, common_len)
    right_common = _token_prefix(right_array, common_len)
    l_flat = left_common.reshape(-1)
    r_flat = right_common.reshape(-1)

    # Pre-reduction finite-audit telemetry on the *valid* window plus a
    # buffer-tail audit past valid_tokens, to discriminate "cache contains
    # NaN/Inf" from "bf16 cosine reduction overflows."
    l_audit = _audit_flat(l_flat)
    r_audit = _audit_flat(r_flat)
    left_raw = left.get("raw_array")
    right_raw = right.get("raw_array")
    left_buffer = int(left["buffer_tokens"])
    right_buffer = int(right["buffer_tokens"])
    if left_raw is not None and left_buffer > left_tokens:
        slices = [slice(None)] * len(left_raw.shape)
        slices[-2] = slice(left_tokens, left_buffer)
        l_tail = left_raw[tuple(slices)].reshape(-1)
        l_tail_audit = _audit_flat(l_tail)
    else:
        l_tail_audit = {"has_nan": False, "has_inf": False, "max_abs": None}
    if right_raw is not None and right_buffer > right_tokens:
        slices = [slice(None)] * len(right_raw.shape)
        slices[-2] = slice(right_tokens, right_buffer)
        r_tail = right_raw[tuple(slices)].reshape(-1)
        r_tail_audit = _audit_flat(r_tail)
    else:
        r_tail_audit = {"has_nan": False, "has_inf": False, "max_abs": None}

    # Native-dtype reductions (the hypothesis-(b) overflow surface).
    dot = mx.sum(l_flat * r_flat)
    denom = mx.sqrt(mx.sum(l_flat * l_flat)) * mx.sqrt(mx.sum(r_flat * r_flat))
    cosine = dot / mx.maximum(denom, mx.array(1e-12))
    mean_abs = mx.mean(mx.abs(l_flat - r_flat))
    rms = mx.sqrt(mx.mean((l_flat - r_flat) * (l_flat - r_flat)))
    mx.eval(cosine, mean_abs, rms)

    # fp32 control cosine: the discriminator. If valid-window inputs are finite
    # and cosine_native is NaN while cosine_fp32 is finite, hypothesis (b)
    # (overflow) is confirmed.
    l_fp32 = l_flat.astype(mx.float32)
    r_fp32 = r_flat.astype(mx.float32)
    dot_fp32 = mx.sum(l_fp32 * r_fp32)
    denom_fp32 = mx.sqrt(mx.sum(l_fp32 * l_fp32)) * mx.sqrt(mx.sum(r_fp32 * r_fp32))
    cosine_fp32 = dot_fp32 / mx.maximum(denom_fp32, mx.array(1e-12))
    mx.eval(cosine_fp32)

    cosine_value = _finite_or_none(float(cosine.item()))
    cosine_fp32_value = _finite_or_none(float(cosine_fp32.item()))
    mean_abs_value = _finite_or_none(float(mean_abs.item()))
    rms_value = _finite_or_none(float(rms.item()))
    nonfinite_count = sum(
        1 for v in (cosine_value, cosine_fp32_value, mean_abs_value, rms_value) if v is None
    )

    return {
        "cosine": cosine_value,
        "cosine_distance": (None if cosine_value is None else float(1.0 - cosine_value)),
        "cosine_fp32": cosine_fp32_value,
        "cosine_fp32_distance": (
            None if cosine_fp32_value is None else float(1.0 - cosine_fp32_value)
        ),
        "mean_abs": mean_abs_value,
        "rms": rms_value,
        "nonfinite_count": nonfinite_count,
        "common_tokens": common_len,
        "left_tokens": left_tokens,
        "right_tokens": right_tokens,
        "left_buffer_tokens": left_buffer,
        "right_buffer_tokens": right_buffer,
        "left_dtype": str(left.get("dtype", "?")),
        "right_dtype": str(right.get("dtype", "?")),
        "left_audit": l_audit,
        "right_audit": r_audit,
        "left_tail_audit": l_tail_audit,
        "right_tail_audit": r_tail_audit,
        "same_valid_token_length": left_tokens == right_tokens,
    }


def _cache_distance(left: list[Any], right: list[Any]) -> dict[str, Any]:
    layer_rows: list[dict[str, Any]] = []
    for layer_idx, (left_entry, right_entry) in enumerate(zip(left, right, strict=True)):
        row: dict[str, Any] = {"layer": layer_idx}
        for name in ("keys", "values"):
            left_window = _cache_window(left_entry, name)
            right_window = _cache_window(right_entry, name)
            if left_window is None or right_window is None:
                row[f"{name}_available"] = False
                continue
            row[f"{name}_available"] = True
            metric = _distance_for_windows(left_window, right_window)
            for metric_name, metric_value in metric.items():
                row[f"{name}_{metric_name}"] = metric_value
        layer_rows.append(row)
    aggregate: dict[str, Any] = {"layers": layer_rows}
    for name in ("keys", "values"):

        def _finite_values(field: str, _name: str = name) -> list[float]:
            out: list[float] = []
            for row in layer_rows:
                if not row.get(f"{_name}_available"):
                    continue
                value = row.get(f"{_name}_{field}")
                if value is None:
                    continue
                out.append(float(value))
            return out

        cosines = _finite_values("cosine")
        cosines_fp32 = _finite_values("cosine_fp32")
        mean_abs = _finite_values("mean_abs")
        rms = _finite_values("rms")
        cosine_distances = _finite_values("cosine_distance")
        cosine_fp32_distances = _finite_values("cosine_fp32_distance")
        token_mismatches = [
            row
            for row in layer_rows
            if row.get(f"{name}_available") and not row.get(f"{name}_same_valid_token_length")
        ]
        n_available = sum(1 for row in layer_rows if row.get(f"{name}_available"))
        nonfinite_layers = sum(
            int(row.get(f"{name}_nonfinite_count") or 0)
            for row in layer_rows
            if row.get(f"{name}_available")
        )
        valid_has_nan_layers = sum(
            1
            for row in layer_rows
            if row.get(f"{name}_available")
            and (
                (row.get(f"{name}_left_audit") or {}).get("has_nan")
                or (row.get(f"{name}_right_audit") or {}).get("has_nan")
            )
        )
        valid_has_inf_layers = sum(
            1
            for row in layer_rows
            if row.get(f"{name}_available")
            and (
                (row.get(f"{name}_left_audit") or {}).get("has_inf")
                or (row.get(f"{name}_right_audit") or {}).get("has_inf")
            )
        )
        tail_has_nan_layers = sum(
            1
            for row in layer_rows
            if row.get(f"{name}_available")
            and (
                (row.get(f"{name}_left_tail_audit") or {}).get("has_nan")
                or (row.get(f"{name}_right_tail_audit") or {}).get("has_nan")
            )
        )
        aggregate[f"{name}_mean_cosine"] = float(np.mean(cosines)) if cosines else None
        aggregate[f"{name}_mean_cosine_fp32"] = (
            float(np.mean(cosines_fp32)) if cosines_fp32 else None
        )
        aggregate[f"{name}_mean_cosine_distance"] = (
            float(np.mean(cosine_distances)) if cosine_distances else None
        )
        aggregate[f"{name}_mean_cosine_fp32_distance"] = (
            float(np.mean(cosine_fp32_distances)) if cosine_fp32_distances else None
        )
        aggregate[f"{name}_mean_abs"] = float(np.mean(mean_abs)) if mean_abs else None
        aggregate[f"{name}_mean_rms"] = float(np.mean(rms)) if rms else None
        aggregate[f"{name}_n_token_length_mismatch_layers"] = len(token_mismatches)
        aggregate[f"{name}_all_same_valid_token_length"] = len(token_mismatches) == 0
        aggregate[f"{name}_n_available_layers"] = n_available
        aggregate[f"{name}_n_finite_cosine_layers"] = len(cosines)
        aggregate[f"{name}_n_finite_cosine_fp32_layers"] = len(cosines_fp32)
        aggregate[f"{name}_total_nonfinite_metric_count"] = nonfinite_layers
        aggregate[f"{name}_valid_window_nan_layers"] = valid_has_nan_layers
        aggregate[f"{name}_valid_window_inf_layers"] = valid_has_inf_layers
        aggregate[f"{name}_buffer_tail_nan_layers"] = tail_has_nan_layers
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


def _clamped_cosine(value: float | None) -> float | None:
    """Clamp cosine to [-1, 1] for paper display; raw fp32 values can overshoot
    by ~1 fp32 ULP on bit-identical fp16 inputs because the dot-product and
    norms are computed independently and round differently."""
    if value is None:
        return None
    if value > 1.0:
        return 1.0
    if value < -1.0:
        return -1.0
    return float(value)


def _path_mean(rows: list[dict[str, Any]], path: str) -> float | None:
    values: list[float] = []
    for row in rows:
        cursor: Any = row
        try:
            for part in path.split("."):
                cursor = cursor[part]
        except (KeyError, TypeError):
            cursor = None
        if cursor is None:
            continue
        try:
            values.append(float(cursor))
        except (TypeError, ValueError):
            continue
    if not values:
        return None
    return float(np.mean(values))


def _relative_gap(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    denom = max(abs(left), abs(right), 1e-12)
    return abs(left - right) / denom


def _emit_summary(
    *,
    args: argparse.Namespace,
    output_rows: list[dict[str, Any]],
    row_path: Path,
    selection_metadata: dict[str, Any],
    t0: int,
) -> int:
    """Write kcache_distance_summary.json from output_rows.

    The headline metrics use ``cosine_fp32`` because the native bf16/fp16
    cosine reduction overflows on ~3M-element flattened cache windows and
    returns NaN at every K layer; the per-layer ``cosine_fp32`` control was
    added by the finite-audit telemetry patch and is the actual saturation
    answer. The bf16/fp16 ``mean_cosine`` columns are kept for traceability
    but are not the basis for any gate.
    """

    def _class_summary(class_name: str) -> dict[str, Any]:
        class_rows = [row for row in output_rows if row["drift_class"] == class_name]
        if not class_rows:
            return {"drift_class": class_name, "n": 0}
        return {
            "drift_class": class_name,
            "n": len(class_rows),
            # native-dtype (fp16/bf16) reductions kept for traceability
            "mean_reuse_keys_cosine": _path_mean(class_rows, "reuse_vs_dense.keys_mean_cosine"),
            "mean_pruned_keys_cosine": _path_mean(class_rows, "pruned_vs_dense.keys_mean_cosine"),
            "mean_reuse_values_cosine": _path_mean(class_rows, "reuse_vs_dense.values_mean_cosine"),
            "mean_pruned_values_cosine": _path_mean(
                class_rows, "pruned_vs_dense.values_mean_cosine"
            ),
            "mean_reuse_keys_cosine_distance": _path_mean(
                class_rows, "reuse_vs_dense.keys_mean_cosine_distance"
            ),
            "mean_pruned_keys_cosine_distance": _path_mean(
                class_rows, "pruned_vs_dense.keys_mean_cosine_distance"
            ),
            "mean_reuse_values_cosine_distance": _path_mean(
                class_rows, "reuse_vs_dense.values_mean_cosine_distance"
            ),
            "mean_pruned_values_cosine_distance": _path_mean(
                class_rows, "pruned_vs_dense.values_mean_cosine_distance"
            ),
            # fp32 control reductions (the trustworthy column)
            "mean_reuse_keys_cosine_fp32": _clamped_cosine(
                _path_mean(class_rows, "reuse_vs_dense.keys_mean_cosine_fp32")
            ),
            "mean_pruned_keys_cosine_fp32": _clamped_cosine(
                _path_mean(class_rows, "pruned_vs_dense.keys_mean_cosine_fp32")
            ),
            "mean_reuse_values_cosine_fp32": _clamped_cosine(
                _path_mean(class_rows, "reuse_vs_dense.values_mean_cosine_fp32")
            ),
            "mean_pruned_values_cosine_fp32": _clamped_cosine(
                _path_mean(class_rows, "pruned_vs_dense.values_mean_cosine_fp32")
            ),
            "mean_reuse_keys_cosine_fp32_distance": _path_mean(
                class_rows, "reuse_vs_dense.keys_mean_cosine_fp32_distance"
            ),
            "mean_pruned_keys_cosine_fp32_distance": _path_mean(
                class_rows, "pruned_vs_dense.keys_mean_cosine_fp32_distance"
            ),
            "mean_reuse_values_cosine_fp32_distance": _path_mean(
                class_rows, "reuse_vs_dense.values_mean_cosine_fp32_distance"
            ),
            "mean_pruned_values_cosine_fp32_distance": _path_mean(
                class_rows, "pruned_vs_dense.values_mean_cosine_fp32_distance"
            ),
            "mean_reuse_keys_mean_abs": _path_mean(class_rows, "reuse_vs_dense.keys_mean_abs"),
            "mean_pruned_keys_mean_abs": _path_mean(class_rows, "pruned_vs_dense.keys_mean_abs"),
        }

    by_drift_class = {
        name: _class_summary(name)
        for name in ("shared_drift", "reuse_only_drift", "invalidated_only_drift", "stable")
    }

    keys_mean_abs_gap = _relative_gap(
        _path_mean(output_rows, "reuse_vs_dense.keys_mean_abs"),
        _path_mean(output_rows, "pruned_vs_dense.keys_mean_abs"),
    )
    values_mean_abs_gap = _relative_gap(
        _path_mean(output_rows, "reuse_vs_dense.values_mean_abs"),
        _path_mean(output_rows, "pruned_vs_dense.values_mean_abs"),
    )
    # native-dtype gaps (kept for traceability only)
    keys_cosine_distance_gap = _relative_gap(
        _path_mean(output_rows, "reuse_vs_dense.keys_mean_cosine_distance"),
        _path_mean(output_rows, "pruned_vs_dense.keys_mean_cosine_distance"),
    )
    values_cosine_distance_gap = _relative_gap(
        _path_mean(output_rows, "reuse_vs_dense.values_mean_cosine_distance"),
        _path_mean(output_rows, "pruned_vs_dense.values_mean_cosine_distance"),
    )
    # fp32 gaps (the H4 gate basis)
    keys_cosine_fp32_distance_gap = _relative_gap(
        _path_mean(output_rows, "reuse_vs_dense.keys_mean_cosine_fp32_distance"),
        _path_mean(output_rows, "pruned_vs_dense.keys_mean_cosine_fp32_distance"),
    )
    values_cosine_fp32_distance_gap = _relative_gap(
        _path_mean(output_rows, "reuse_vs_dense.values_mean_cosine_fp32_distance"),
        _path_mean(output_rows, "pruned_vs_dense.values_mean_cosine_fp32_distance"),
    )

    same_valid_lengths = bool(
        output_rows
        and all(row["reuse_vs_dense"]["keys_all_same_valid_token_length"] for row in output_rows)
        and all(row["reuse_vs_dense"]["values_all_same_valid_token_length"] for row in output_rows)
        and all(row["pruned_vs_dense"]["keys_all_same_valid_token_length"] for row in output_rows)
        and all(row["pruned_vs_dense"]["values_all_same_valid_token_length"] for row in output_rows)
    )
    n_token_length_mismatch_rows = sum(
        1
        for row in output_rows
        if not (
            row["reuse_vs_dense"]["keys_all_same_valid_token_length"]
            and row["reuse_vs_dense"]["values_all_same_valid_token_length"]
            and row["pruned_vs_dense"]["keys_all_same_valid_token_length"]
            and row["pruned_vs_dense"]["values_all_same_valid_token_length"]
        )
    )
    n_unique_followup_rows = len(
        {(str(row["video_id"]), int(row["q_index"])) for row in output_rows}
    )
    capture_row_floor = 20
    pass_h1_row_count = (
        len(output_rows) >= capture_row_floor and n_unique_followup_rows >= capture_row_floor
    )
    # Cache states are "captured" if the fp32 control cosine is finite at every
    # row × arm × kv. The native bf16/fp16 cosine column overflows by design at
    # this scale and is intentionally allowed to be NaN.
    pass_h1_cache_states_captured = bool(
        output_rows
        and all(
            row["reuse_vs_dense"].get("keys_mean_cosine_fp32") is not None for row in output_rows
        )
        and all(
            row["reuse_vs_dense"].get("values_mean_cosine_fp32") is not None for row in output_rows
        )
        and all(
            row["pruned_vs_dense"].get("keys_mean_cosine_fp32") is not None for row in output_rows
        )
        and all(
            row["pruned_vs_dense"].get("values_mean_cosine_fp32") is not None for row in output_rows
        )
    )
    pass_h1_capture = pass_h1_row_count and pass_h1_cache_states_captured and same_valid_lengths
    pass_h2_distance_report = all(
        int(selection_metadata["selected_by_drift_class"].get(name, 0)) > 0
        for name in ("shared_drift", "reuse_only_drift", "invalidated_only_drift", "stable")
    )
    pass_h3_outcome_link = pass_h2_distance_report and all(
        by_drift_class[name].get("mean_reuse_keys_mean_abs") is not None
        for name in ("shared_drift", "reuse_only_drift", "invalidated_only_drift", "stable")
    )
    pass_h1_same_valid_lengths = same_valid_lengths
    # H4 saturation: pruned arm should diverge from dense substantially MORE
    # than reuse arm. Gate: relative gap on cosine_fp32_distance >= 0.5 for
    # both K and V (i.e., pruned distance is at least 2x the reuse distance,
    # equivalent to the structured saturation interpretation). Earlier draft
    # used <= 0.10 which encoded the OPPOSITE story (gate passes when arms
    # AGREE) and was load-bearing on a bf16 column that NaN-overflowed.
    pass_h4_saturation_test = (
        pass_h1_same_valid_lengths
        and keys_cosine_fp32_distance_gap is not None
        and values_cosine_fp32_distance_gap is not None
        and keys_cosine_fp32_distance_gap >= 0.5
        and values_cosine_fp32_distance_gap >= 0.5
    )

    summary = {
        "phase": "1.30AG",
        "n_rows": len(output_rows),
        "n_unique_followup_rows": n_unique_followup_rows,
        "capture_row_floor": capture_row_floor,
        "max_pairs_requested": args.max_pairs,
        "selection": selection_metadata,
        "vision_tower_layer": args.vision_tower_layer,
        "vision_tower_keep_rate": args.vision_tower_keep_rate,
        "cache_dtype_observed": output_rows[0]["reuse_vs_dense"]["layers"][0].get(
            "keys_left_dtype", "?"
        )
        if output_rows
        else "?",
        # native-dtype mean (kept for traceability; expect None on K side)
        "mean_reuse_keys_cosine": _path_mean(output_rows, "reuse_vs_dense.keys_mean_cosine"),
        "mean_pruned_keys_cosine": _path_mean(output_rows, "pruned_vs_dense.keys_mean_cosine"),
        "mean_reuse_values_cosine": _path_mean(output_rows, "reuse_vs_dense.values_mean_cosine"),
        "mean_pruned_values_cosine": _path_mean(output_rows, "pruned_vs_dense.values_mean_cosine"),
        "mean_reuse_keys_cosine_distance": _path_mean(
            output_rows, "reuse_vs_dense.keys_mean_cosine_distance"
        ),
        "mean_pruned_keys_cosine_distance": _path_mean(
            output_rows, "pruned_vs_dense.keys_mean_cosine_distance"
        ),
        "mean_reuse_values_cosine_distance": _path_mean(
            output_rows, "reuse_vs_dense.values_mean_cosine_distance"
        ),
        "mean_pruned_values_cosine_distance": _path_mean(
            output_rows, "pruned_vs_dense.values_mean_cosine_distance"
        ),
        # fp32 control means (the trustworthy column)
        "mean_reuse_keys_cosine_fp32": _clamped_cosine(
            _path_mean(output_rows, "reuse_vs_dense.keys_mean_cosine_fp32")
        ),
        "mean_pruned_keys_cosine_fp32": _clamped_cosine(
            _path_mean(output_rows, "pruned_vs_dense.keys_mean_cosine_fp32")
        ),
        "mean_reuse_values_cosine_fp32": _clamped_cosine(
            _path_mean(output_rows, "reuse_vs_dense.values_mean_cosine_fp32")
        ),
        "mean_pruned_values_cosine_fp32": _clamped_cosine(
            _path_mean(output_rows, "pruned_vs_dense.values_mean_cosine_fp32")
        ),
        "mean_reuse_keys_cosine_fp32_distance": _path_mean(
            output_rows, "reuse_vs_dense.keys_mean_cosine_fp32_distance"
        ),
        "mean_pruned_keys_cosine_fp32_distance": _path_mean(
            output_rows, "pruned_vs_dense.keys_mean_cosine_fp32_distance"
        ),
        "mean_reuse_values_cosine_fp32_distance": _path_mean(
            output_rows, "reuse_vs_dense.values_mean_cosine_fp32_distance"
        ),
        "mean_pruned_values_cosine_fp32_distance": _path_mean(
            output_rows, "pruned_vs_dense.values_mean_cosine_fp32_distance"
        ),
        "mean_reuse_keys_mean_abs": _path_mean(output_rows, "reuse_vs_dense.keys_mean_abs"),
        "mean_pruned_keys_mean_abs": _path_mean(output_rows, "pruned_vs_dense.keys_mean_abs"),
        "mean_reuse_values_mean_abs": _path_mean(output_rows, "reuse_vs_dense.values_mean_abs"),
        "mean_pruned_values_mean_abs": _path_mean(output_rows, "pruned_vs_dense.values_mean_abs"),
        "keys_cosine_distance_relative_gap": keys_cosine_distance_gap,
        "values_cosine_distance_relative_gap": values_cosine_distance_gap,
        "keys_cosine_fp32_distance_relative_gap": keys_cosine_fp32_distance_gap,
        "values_cosine_fp32_distance_relative_gap": values_cosine_fp32_distance_gap,
        "keys_mean_abs_relative_gap": keys_mean_abs_gap,
        "values_mean_abs_relative_gap": values_mean_abs_gap,
        "all_same_valid_token_lengths": same_valid_lengths,
        "n_token_length_mismatch_rows": n_token_length_mismatch_rows,
        "by_drift_class": by_drift_class,
        "pass_H1_row_count": pass_h1_row_count,
        "pass_H1_cache_states_captured": pass_h1_cache_states_captured,
        "pass_H1_capture": pass_h1_capture,
        "pass_H1_same_valid_lengths": pass_h1_same_valid_lengths,
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
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"[1.30AG] wrote {summary_path}")
    return 0


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
    parser.add_argument(
        "--reaggregate-only",
        action="store_true",
        help=(
            "Skip model load + capture; re-read kcache_distance_rows.jsonl from "
            "--output-dir and re-emit kcache_distance_summary.json with the "
            "current aggregator + gate logic. Used to refresh the summary after "
            "an analyzer fix without paying the 30 min capture cost."
        ),
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.reaggregate_only:
        row_path = args.output_dir / "kcache_distance_rows.jsonl"
        if not row_path.exists():
            raise SystemExit(
                f"--reaggregate-only requires existing rows at {row_path}; run a capture first."
            )
        output_rows = _read_jsonl(row_path)
        if not output_rows:
            raise SystemExit(f"--reaggregate-only loaded zero rows from {row_path}")
        # Reconstruct selection metadata from the rows themselves so the gate
        # logic still works without re-reading the upstream attribution file.
        class_counts: dict[str, int] = {
            "shared_drift": 0,
            "reuse_only_drift": 0,
            "invalidated_only_drift": 0,
            "stable": 0,
        }
        for row in output_rows:
            class_counts[str(row["drift_class"])] = class_counts.get(str(row["drift_class"]), 0) + 1
        selection_metadata = {
            "available_by_drift_class": dict(class_counts),
            "selected_by_drift_class": dict(class_counts),
            "target_per_class": max(1, args.max_pairs // 4),
        }
        t0 = time.perf_counter_ns()
        return _emit_summary(
            args=args,
            output_rows=output_rows,
            row_path=row_path,
            selection_metadata=selection_metadata,
            t0=t0,
        )

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
            try:
                pruned_cache, pruned_ms = _full_prompt_cache(model=model, sample=current_sample)
            finally:
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
            handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
            handle.flush()
            reuse_cos = row["reuse_vs_dense"].get("keys_mean_cosine")
            pruned_cos = row["pruned_vs_dense"].get("keys_mean_cosine")
            reuse_cos_str = f"{reuse_cos:.4f}" if isinstance(reuse_cos, float) else "n/a"
            pruned_cos_str = f"{pruned_cos:.4f}" if isinstance(pruned_cos, float) else "n/a"
            print(
                f"[1.30AG] {video_id} q={q_index}: "
                f"reuse K cos={reuse_cos_str}, "
                f"pruned K cos={pruned_cos_str}"
            )
            del dense_cache, reuse_cache, pruned_cache
            gc.collect()
            mx.clear_cache()

    return _emit_summary(
        args=args,
        output_rows=output_rows,
        row_path=row_path,
        selection_metadata=selection_metadata,
        t0=t0,
    )


if __name__ == "__main__":
    raise SystemExit(main())
