from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
import tomllib
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, cast

import av
import mlx.core as mx
import numpy as np
from mlx_vlm import generate, load  # type: ignore[import-untyped]
from mlx_vlm.utils import prepare_inputs  # type: ignore[import-untyped]
from PIL import Image

from codec_through.answers import extract_choice
from codec_through.temporal import (
    BlockClass,
    BlockThresholds,
    classify_blocks,
    summarize_classification,
)
from codec_through.track_a import (
    flattened_reuse_mask,
    qwen_merged_token_counts,
    resized_dimensions_for_block_multiple,
)

ARTIFACT_DIR = Path("research/experiments/2026/artifacts")
MANIFEST_PATH = Path("data/corpus/manifest.toml")
PROMPT_BANK_PATH = Path("research/prompt_bank/local_suite_v1.toml")
QWEN_TARGET_HEIGHT = 252
PRIMARY_CLIP_IDS = [
    "xiph_akiyo_cif",
    "xiph_news_cif",
    "xiph_coastguard_cif",
    "xiph_mobile_cif",
]
SYNTHETIC_CLIP_IDS = [
    "synthetic_affine_pan",
    "synthetic_scene_cut",
    "synthetic_fullframe_flicker",
    "synthetic_color_swap",
    "synthetic_small_object",
    "synthetic_screen_ocr",
]
DEFAULT_THRESHOLDS = BlockThresholds(static_threshold=3.0, shifted_threshold=8.0)
PHASE_OPEN_PROMPTS = [
    "Describe the scene in one sentence.",
    "What changes over time in this clip?",
]


@dataclass(frozen=True, slots=True)
class ModelSpec:
    model_id: str
    family: Literal["qwen", "gemma"]
    block_size: int
    target_height: int | None
    gemma_visual_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class ClipRecord:
    clip_id: str
    content_class: str
    tier: str
    local_path: Path


@dataclass(frozen=True, slots=True)
class PreparedSample:
    clip_id: str
    question: str
    frames: list[Image.Image]
    input_ids: mx.array
    pixel_values: mx.array
    mask: mx.array
    extra_kwargs: dict[str, mx.array]


def _run(command: list[str]) -> str:
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def _environment_record() -> dict[str, Any]:
    import mlx_vlm

    ffmpeg_version = _run(["ffmpeg", "-version"]).splitlines()[0]
    git_sha = _run(["git", "rev-parse", "HEAD"])
    git_dirty = bool(_run(["git", "status", "--short"]))
    return {
        "git_dirty": git_dirty,
        "git_sha": git_sha,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "ffmpeg": ffmpeg_version,
        "mlx_vlm_module": str(Path(mlx_vlm.__file__).resolve()),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_manifest() -> tuple[dict[str, ClipRecord], str]:
    payload = tomllib.loads(MANIFEST_PATH.read_text())
    derived_id = payload["derived_encode"][0]["id"]
    clips: dict[str, ClipRecord] = {}
    for clip in payload["clip"]:
        clip_id = clip["id"]
        local_path = Path(clip["local_path"])
        if clip["tier"] == "primary":
            candidate = Path("data/corpus/derived") / f"{local_path.stem}_{derived_id}.mp4"
            resolved = candidate if candidate.exists() else local_path
        else:
            resolved = local_path
        clips[clip_id] = ClipRecord(
            clip_id=clip_id,
            content_class=clip["content_class"],
            tier=clip["tier"],
            local_path=resolved,
        )
    return clips, derived_id


def _decode_contiguous_frames(
    video_path: Path,
    *,
    start_frame: int,
    frame_count: int,
) -> list[Image.Image]:
    if start_frame < 0:
        raise ValueError("start_frame must be non-negative")
    if frame_count <= 0:
        raise ValueError("frame_count must be positive")

    frames: list[Image.Image] = []
    with av.open(str(video_path)) as container:
        for index, frame in enumerate(container.decode(video=0)):
            if index < start_frame:
                continue
            frames.append(cast(Image.Image, frame.to_image()).convert("RGB"))  # type: ignore[no-untyped-call]
            if len(frames) == frame_count:
                break
    if len(frames) != frame_count:
        raise ValueError(
            f"expected {frame_count} decoded frames from {video_path}, got {len(frames)}"
        )
    return frames


def _preprocess_frames(frames: list[Image.Image], spec: ModelSpec) -> list[Image.Image]:
    processed: list[Image.Image] = []
    for frame in frames:
        width, height = frame.size
        target_width, target_height = resized_dimensions_for_block_multiple(
            width,
            height,
            block_size=spec.block_size,
            target_height=spec.target_height,
        )
        if (target_width, target_height) != (width, height):
            frame = frame.resize((target_width, target_height), Image.Resampling.BICUBIC)
        processed.append(frame)
    return processed


def _build_messages(frame_count: int, question: str) -> list[dict[str, Any]]:
    return [
        {
            "role": "user",
            "content": [
                *({"type": "image"} for _ in range(frame_count)),
                {"type": "text", "text": question},
            ],
        }
    ]


def _prepare_sample(
    model: Any,
    processor: Any,
    spec: ModelSpec,
    *,
    clip_id: str,
    frames: list[Image.Image],
    question: str,
) -> PreparedSample:
    del model  # Only needed for interface symmetry with later extensions.
    if spec.gemma_visual_tokens is not None:
        processor.image_processor.max_soft_tokens = spec.gemma_visual_tokens
    if hasattr(processor, "image_processor"):
        if hasattr(processor.image_processor, "do_resize"):
            processor.image_processor.do_resize = False
        if hasattr(processor.image_processor, "do_image_splitting"):
            processor.image_processor.do_image_splitting = False

    messages = _build_messages(len(frames), question)
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
        clip_id=clip_id,
        question=question,
        frames=frames,
        input_ids=input_ids,
        pixel_values=pixel_values,
        mask=mask,
        extra_kwargs=extra_kwargs,
    )


def _generate_text(
    model: Any,
    processor: Any,
    sample: PreparedSample,
    *,
    cached_features: mx.array | None = None,
    max_tokens: int,
) -> dict[str, Any]:
    mx.random.seed(42)
    kwargs = dict(sample.extra_kwargs)
    if cached_features is not None:
        kwargs["cached_image_features"] = cached_features
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
    elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000
    return {
        "text": response.text,
        "elapsed_ms": elapsed_ms,
        "prompt_tokens": response.prompt_tokens,
        "generation_tokens": response.generation_tokens,
        "peak_memory_gb": response.peak_memory,
    }


def _compute_cached_features(model: Any, spec: ModelSpec, sample: PreparedSample) -> mx.array:
    if spec.family == "gemma":
        features = model.encode_image(sample.pixel_values)
        mx.eval(features)
        return cast(mx.array, features)
    image_grid_thw = sample.extra_kwargs["image_grid_thw"]
    dtype = model.vision_tower.patch_embed.proj.weight.dtype
    features = model.vision_tower(
        sample.pixel_values.astype(dtype),
        image_grid_thw,
        output_hidden_states=False,
    )
    mx.eval(features)
    return cast(mx.array, features)


def _prefill_logits(
    model: Any,
    sample: PreparedSample,
    *,
    cached_features: mx.array | None = None,
) -> mx.array:
    kwargs = dict(sample.extra_kwargs)
    if cached_features is not None:
        kwargs["cached_image_features"] = cached_features
    outputs = model(sample.input_ids, sample.pixel_values, mask=sample.mask, **kwargs)
    logits = outputs.logits
    mx.eval(logits)
    return cast(mx.array, logits)


def _max_abs_diff(lhs: mx.array, rhs: mx.array) -> float:
    diff = mx.max(mx.abs(lhs - rhs))
    mx.eval(diff)
    return float(diff.item())


def _build_liveness_probe_question() -> str:
    return "\n".join(
        [
            "Which event happens in this clip?",
            "A. The large center square changes from red to green.",
            "B. The whole scene pans sideways.",
            "C. A hard cut changes the room.",
            "D. Nothing changes.",
            "Answer with one letter only.",
        ]
    )


def _qwen_segmented_perturbation(
    sample: PreparedSample,
    features: mx.array,
    *,
    zero_segment_index: int,
) -> mx.array:
    image_grid_thw = np.array(sample.extra_kwargs["image_grid_thw"].tolist(), dtype=np.int64)
    spatial_merge_size = int(getattr(sample.extra_kwargs["image_grid_thw"], "shape", (0,))[0])
    del spatial_merge_size  # avoid confusion with runtime array shape
    merge_size = 2
    counts = qwen_merged_token_counts(image_grid_thw, spatial_merge_size=merge_size)
    segments: list[mx.array] = []
    offset = 0
    for count in counts:
        segments.append(features[offset : offset + count])
        offset += count
    if not (0 <= zero_segment_index < len(segments)):
        raise ValueError("zero_segment_index out of range")
    segments[zero_segment_index] = mx.zeros_like(segments[zero_segment_index])
    perturbed = mx.concatenate(segments, axis=0)
    mx.eval(perturbed)
    return perturbed


def _perturb_features_for_liveness(
    spec: ModelSpec,
    sample: PreparedSample,
    features: mx.array,
) -> mx.array:
    if spec.family == "qwen":
        return _qwen_segmented_perturbation(sample, features, zero_segment_index=1)
    perturbed = mx.zeros_like(features)
    mx.eval(perturbed)
    return perturbed


def _cohens_kappa(
    reference: list[int | None], prediction: list[int | None], *, category_count: int
) -> float:
    if len(reference) != len(prediction):
        raise ValueError("reference and prediction lengths must match")
    if not reference:
        return 0.0
    none_bucket = category_count
    ref_labels = [value if value is not None else none_bucket for value in reference]
    pred_labels = [value if value is not None else none_bucket for value in prediction]
    categories = category_count + 1
    observed = sum(int(lhs == rhs) for lhs, rhs in zip(ref_labels, pred_labels, strict=True)) / len(
        ref_labels
    )
    ref_counts = Counter(ref_labels)
    pred_counts = Counter(pred_labels)
    expected = sum(
        (ref_counts[index] / len(ref_labels)) * (pred_counts[index] / len(pred_labels))
        for index in range(categories)
    )
    if expected == 1.0:
        return 1.0
    return (observed - expected) / (1.0 - expected)


def _multiple_choice_question(item: dict[str, Any]) -> str:
    lines = [item["question"]]
    for index, choice in enumerate(item["choices"]):
        letter = chr(ord("A") + index)
        lines.append(f"{letter}. {choice}")
    lines.append("Answer with one letter only.")
    return "\n".join(lines)


def _mix_qwen_features(
    sample: PreparedSample,
    features: mx.array,
    *,
    thresholds: BlockThresholds,
    reuse_classes: tuple[BlockClass, ...],
) -> tuple[mx.array, list[float]]:
    image_grid_thw = np.array(sample.extra_kwargs["image_grid_thw"].tolist(), dtype=np.int64)
    counts = qwen_merged_token_counts(image_grid_thw, spatial_merge_size=2)
    if len(counts) != len(sample.frames):
        raise ValueError("frame count and Qwen image grid count mismatch")

    dense_segments: list[mx.array] = []
    offset = 0
    for count in counts:
        dense_segments.append(features[offset : offset + count])
        offset += count

    mixed_segments = [dense_segments[0]]
    reused_ratios: list[float] = []
    for frame_index in range(1, len(sample.frames)):
        previous = np.array(sample.frames[frame_index - 1], dtype=np.uint8)
        current = np.array(sample.frames[frame_index], dtype=np.uint8)
        classification = classify_blocks(
            previous,
            current,
            block_size=28,
            thresholds=thresholds,
        )
        reuse_mask = flattened_reuse_mask(classification, reuse_classes=reuse_classes)
        if reuse_mask.size != dense_segments[frame_index].shape[0]:
            raise ValueError(
                "classification/token mismatch: "
                f"mask={reuse_mask.size}, tokens={dense_segments[frame_index].shape[0]}"
            )
        mask = mx.array(reuse_mask[:, None])
        mixed_segments.append(mx.where(mask, mixed_segments[-1], dense_segments[frame_index]))
        reused_ratios.append(float(reuse_mask.mean()))
    mixed = mx.concatenate(mixed_segments, axis=0)
    mx.eval(mixed)
    return mixed, reused_ratios


def _load_prompt_bank() -> list[dict[str, Any]]:
    payload = tomllib.loads(PROMPT_BANK_PATH.read_text())
    return list(payload["item"])


def _load_model(spec: ModelSpec) -> tuple[Any, Any]:
    return cast(tuple[Any, Any], load(str(Path.home() / "models" / spec.model_id)))


def _model_specs() -> list[ModelSpec]:
    return [
        ModelSpec(
            model_id="Qwen2.5-VL-3B-Instruct-4bit",
            family="qwen",
            block_size=28,
            target_height=QWEN_TARGET_HEIGHT,
        ),
        ModelSpec(
            model_id="gemma-4-e4b-it-4bit",
            family="gemma",
            block_size=16,
            target_height=None,
            gemma_visual_tokens=280,
        ),
    ]


def run_phase_0_5() -> dict[str, Any]:
    manifest, _ = _load_manifest()
    result: dict[str, Any] = {
        "phase": "0.5",
        "environment": _environment_record(),
        "models": {},
    }

    probe_clip = manifest["synthetic_color_swap"]
    probe_frames = _preprocess_frames(
        _decode_contiguous_frames(probe_clip.local_path, start_frame=18, frame_count=12),
        _model_specs()[0],
    )
    probe_question = _build_liveness_probe_question()

    for spec in _model_specs():
        model, processor = _load_model(spec)
        model_result: dict[str, Any] = {
            "api_dag": {
                "step_1_import_load": True,
                "step_2_model_load": True,
                "step_3_dense_generation": True,
                "step_4_dense_determinism": False,
                "step_5_cache_liveness": False,
            },
            "dense_examples": [],
        }

        for clip_id in ("xiph_akiyo_cif", "xiph_news_cif"):
            clip = manifest[clip_id]
            raw_frames = _decode_contiguous_frames(clip.local_path, start_frame=0, frame_count=8)
            frames = _preprocess_frames(raw_frames, spec)
            for prompt in PHASE_OPEN_PROMPTS:
                sample = _prepare_sample(
                    model,
                    processor,
                    spec,
                    clip_id=clip_id,
                    frames=frames,
                    question=prompt,
                )
                response = _generate_text(model, processor, sample, max_tokens=24)
                model_result["dense_examples"].append(
                    {
                        "clip_id": clip_id,
                        "clip_sha256": _sha256(clip.local_path),
                        "question": prompt,
                        "response": response["text"],
                        "elapsed_ms": response["elapsed_ms"],
                    }
                )

        determinism_sample = _prepare_sample(
            model,
            processor,
            spec,
            clip_id="xiph_akiyo_cif",
            frames=_preprocess_frames(
                _decode_contiguous_frames(
                    manifest["xiph_akiyo_cif"].local_path, start_frame=0, frame_count=8
                ),
                spec,
            ),
            question=PHASE_OPEN_PROMPTS[0],
        )
        dense_outputs: list[str] = []
        dense_latencies_ms: list[float] = []
        for _ in range(50):
            response = _generate_text(model, processor, determinism_sample, max_tokens=24)
            dense_outputs.append(response["text"])
            dense_latencies_ms.append(response["elapsed_ms"])
        unique_outputs = sorted(set(dense_outputs))
        model_result["determinism"] = {
            "clip_id": "xiph_akiyo_cif",
            "question": PHASE_OPEN_PROMPTS[0],
            "repetitions": 50,
            "unique_output_count": len(unique_outputs),
            "unique_outputs": unique_outputs,
            "bit_identical": len(unique_outputs) == 1,
            "latency_ms": {
                "p50": float(np.median(dense_latencies_ms)),
                "p95": float(np.percentile(dense_latencies_ms, 95)),
            },
        }
        model_result["api_dag"]["step_4_dense_determinism"] = len(unique_outputs) == 1

        probe_frames_for_model = (
            probe_frames
            if spec.family == "qwen"
            else _preprocess_frames(
                _decode_contiguous_frames(probe_clip.local_path, start_frame=18, frame_count=12),
                spec,
            )
        )
        probe_sample = _prepare_sample(
            model,
            processor,
            spec,
            clip_id=probe_clip.clip_id,
            frames=probe_frames_for_model,
            question=probe_question,
        )
        probe_features = _compute_cached_features(model, spec, probe_sample)
        probe_perturbed = _perturb_features_for_liveness(spec, probe_sample, probe_features)
        dense_probe = _generate_text(model, processor, probe_sample, max_tokens=4)
        perturbed_probe = _generate_text(
            model, processor, probe_sample, cached_features=probe_perturbed, max_tokens=4
        )
        dense_logits = _prefill_logits(model, probe_sample)
        perturbed_logits = _prefill_logits(model, probe_sample, cached_features=probe_perturbed)
        logits_diff = _max_abs_diff(dense_logits, perturbed_logits)
        liveness = dense_probe["text"] != perturbed_probe["text"] or logits_diff > 0.0
        model_result["api_dag"]["step_5_cache_liveness"] = liveness
        model_result["liveness_probe"] = {
            "clip_id": probe_clip.clip_id,
            "question": probe_question,
            "dense_text": dense_probe["text"],
            "perturbed_text": perturbed_probe["text"],
            "prefill_logits_max_abs_diff": logits_diff,
            "path_live": liveness,
        }

        result["models"][spec.model_id] = model_result
    return result


def run_phase_0_75() -> dict[str, Any]:
    manifest, _ = _load_manifest()
    result: dict[str, Any] = {
        "phase": "0.75",
        "environment": _environment_record(),
        "models": {},
    }

    for spec in _model_specs():
        model, processor = _load_model(spec)
        model_result: dict[str, Any] = {"samples": []}
        for clip_id in ("xiph_akiyo_cif", "xiph_news_cif"):
            clip = manifest[clip_id]
            frames = _preprocess_frames(
                _decode_contiguous_frames(clip.local_path, start_frame=0, frame_count=8),
                spec,
            )
            for prompt in PHASE_OPEN_PROMPTS:
                sample = _prepare_sample(
                    model,
                    processor,
                    spec,
                    clip_id=clip_id,
                    frames=frames,
                    question=prompt,
                )
                features = _compute_cached_features(model, spec, sample)
                perturbed = _perturb_features_for_liveness(spec, sample, features)

                dense_logits = _prefill_logits(model, sample)
                cached_logits = _prefill_logits(model, sample, cached_features=features)
                perturbed_logits = _prefill_logits(model, sample, cached_features=perturbed)

                outputs: dict[str, list[str]] = defaultdict(list)
                latencies: dict[str, list[float]] = defaultdict(list)
                for condition_name, cached in (
                    ("A0_dense", None),
                    ("A1_cached_same", features),
                    ("A2_cached_perturbed", perturbed),
                ):
                    for _ in range(10):
                        response = _generate_text(
                            model,
                            processor,
                            sample,
                            cached_features=cached,
                            max_tokens=24,
                        )
                        outputs[condition_name].append(response["text"])
                        latencies[condition_name].append(response["elapsed_ms"])

                dense_unique = sorted(set(outputs["A0_dense"]))
                cached_unique = sorted(set(outputs["A1_cached_same"]))
                perturbed_unique = sorted(set(outputs["A2_cached_perturbed"]))
                sample_result = {
                    "clip_id": clip_id,
                    "clip_sha256": _sha256(clip.local_path),
                    "question": prompt,
                    "repetitions_per_condition": 10,
                    "a0_unique_outputs": dense_unique,
                    "a1_unique_outputs": cached_unique,
                    "a2_unique_outputs": perturbed_unique,
                    "a0_equals_a1_exactly": outputs["A0_dense"] == outputs["A1_cached_same"],
                    "prefill_logits_max_abs_diff_a0_vs_a1": _max_abs_diff(
                        dense_logits, cached_logits
                    ),
                    "prefill_logits_max_abs_diff_a0_vs_a2": _max_abs_diff(
                        dense_logits, perturbed_logits
                    ),
                    "latency_ms": {
                        name: {
                            "p50": float(np.median(values)),
                            "p95": float(np.percentile(values, 95)),
                        }
                        for name, values in latencies.items()
                    },
                }
                model_result["samples"].append(sample_result)
        result["models"][spec.model_id] = model_result
    return result


def run_phase_1_0() -> dict[str, Any]:
    manifest, _ = _load_manifest()
    result: dict[str, Any] = {
        "phase": "1.0",
        "environment": _environment_record(),
        "thresholds": asdict(DEFAULT_THRESHOLDS),
        "clips": [],
    }
    qwen_spec = _model_specs()[0]
    for clip_id in PRIMARY_CLIP_IDS + SYNTHETIC_CLIP_IDS:
        clip = manifest[clip_id]
        start_frame = 0 if clip.tier == "primary" else 18
        raw_frames = _decode_contiguous_frames(
            clip.local_path, start_frame=start_frame, frame_count=12
        )
        frames = _preprocess_frames(raw_frames, qwen_spec)

        pair_summaries: list[dict[str, float]] = []
        for index in range(1, len(frames)):
            previous = np.array(frames[index - 1], dtype=np.uint8)
            current = np.array(frames[index], dtype=np.uint8)
            classification = classify_blocks(
                previous,
                current,
                block_size=qwen_spec.block_size,
                thresholds=DEFAULT_THRESHOLDS,
            )
            summary = summarize_classification(classification)
            pair_summaries.append(
                {
                    "static_ratio": summary.static_blocks / summary.total_blocks,
                    "shifted_ratio": summary.shifted_blocks / summary.total_blocks,
                    "novel_ratio": summary.novel_blocks / summary.total_blocks,
                    "reused_ratio": summary.reused_ratio,
                }
            )

        aggregates = {
            key: float(np.mean([pair[key] for pair in pair_summaries]))
            for key in ("static_ratio", "shifted_ratio", "novel_ratio", "reused_ratio")
        }
        result["clips"].append(
            {
                "clip_id": clip_id,
                "clip_sha256": _sha256(clip.local_path),
                "content_class": clip.content_class,
                "window_start": start_frame,
                "window_frames": 12,
                **aggregates,
            }
        )

    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for clip in result["clips"]:
        by_class[clip["content_class"]].append(clip)
    result["content_class_summary"] = {
        content_class: {
            key: float(np.mean([entry[key] for entry in entries]))
            for key in ("static_ratio", "shifted_ratio", "novel_ratio", "reused_ratio")
        }
        for content_class, entries in by_class.items()
    }
    return result


def run_track_a_pilot() -> dict[str, Any]:
    items = _load_prompt_bank()
    spec = _model_specs()[0]
    result: dict[str, Any] = {
        "phase": "track_a_pilot",
        "environment": _environment_record(),
        "model": spec.model_id,
        "thresholds": asdict(DEFAULT_THRESHOLDS),
        "item_execution_mode": "chunked-subprocesses",
        "chunk_size": 2,
        "items": [],
    }

    dense_choices: list[int | None] = []
    static_choices: list[int | None] = []
    shifted_choices: list[int | None] = []

    chunk_size = 2
    for chunk_start in range(0, len(items), chunk_size):
        chunk = items[chunk_start : chunk_start + chunk_size]
        completed = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "track_a_chunk",
                *[argument for item in chunk for argument in ("--item-id", item["id"])],
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or "unknown failure"
            chunk_ids = ",".join(item["id"] for item in chunk)
            raise RuntimeError(f"track_a_chunk failed for {chunk_ids}: {message}")
        chunk_results = json.loads(completed.stdout)
        for item_result in chunk_results:
            result["items"].append(item_result)
            dense_choices.append(item_result["dense_choice"])
            static_choices.append(item_result["static_choice"])
            shifted_choices.append(item_result["shifted_choice"])

    dense_accuracy = sum(int(item["dense_correct"]) for item in result["items"]) / len(
        result["items"]
    )
    static_accuracy = sum(int(item["static_correct"]) for item in result["items"]) / len(
        result["items"]
    )
    shifted_accuracy = sum(int(item["shifted_correct"]) for item in result["items"]) / len(
        result["items"]
    )
    dense_static_agreement = sum(
        int(lhs == rhs) for lhs, rhs in zip(dense_choices, static_choices, strict=True)
    ) / len(dense_choices)
    dense_shifted_agreement = sum(
        int(lhs == rhs) for lhs, rhs in zip(dense_choices, shifted_choices, strict=True)
    ) / len(dense_choices)
    result["summary"] = {
        "item_count": len(result["items"]),
        "dense_accuracy": dense_accuracy,
        "static_accuracy": static_accuracy,
        "shifted_accuracy": shifted_accuracy,
        "dense_static_agreement": dense_static_agreement,
        "dense_shifted_agreement": dense_shifted_agreement,
        "dense_static_kappa": _cohens_kappa(dense_choices, static_choices, category_count=4),
        "dense_shifted_kappa": _cohens_kappa(dense_choices, shifted_choices, category_count=4),
        "dense_parse_failures": sum(choice is None for choice in dense_choices),
        "static_parse_failures": sum(choice is None for choice in static_choices),
        "shifted_parse_failures": sum(choice is None for choice in shifted_choices),
    }
    return result


def run_track_a_chunk(item_ids: list[str]) -> list[dict[str, Any]]:
    manifest, _ = _load_manifest()
    spec = _model_specs()[0]
    model, processor = _load_model(spec)
    items = {item["id"]: item for item in _load_prompt_bank()}
    results: list[dict[str, Any]] = []
    for item_id in item_ids:
        item = items[item_id]
        clip = manifest[item["clip_id"]]
        raw_frames = _decode_contiguous_frames(
            clip.local_path,
            start_frame=int(item["window_start"]),
            frame_count=int(item["window_frames"]),
        )
        frames = _preprocess_frames(raw_frames, spec)
        question = _multiple_choice_question(item)
        sample = _prepare_sample(
            model,
            processor,
            spec,
            clip_id=item["clip_id"],
            frames=frames,
            question=question,
        )
        dense_features = _compute_cached_features(model, spec, sample)
        static_features, static_reuse_ratios = _mix_qwen_features(
            sample,
            dense_features,
            thresholds=DEFAULT_THRESHOLDS,
            reuse_classes=(BlockClass.STATIC,),
        )
        shifted_features, shifted_reuse_ratios = _mix_qwen_features(
            sample,
            dense_features,
            thresholds=DEFAULT_THRESHOLDS,
            reuse_classes=(BlockClass.STATIC, BlockClass.SHIFTED),
        )

        dense = _generate_text(model, processor, sample, max_tokens=4)
        static = _generate_text(
            model, processor, sample, cached_features=static_features, max_tokens=4
        )
        shifted = _generate_text(
            model, processor, sample, cached_features=shifted_features, max_tokens=4
        )

        dense_choice = extract_choice(dense["text"], item["choices"])
        static_choice = extract_choice(static["text"], item["choices"])
        shifted_choice = extract_choice(shifted["text"], item["choices"])

        results.append(
            {
                "id": item["id"],
                "clip_id": item["clip_id"],
                "bucket": item["bucket"],
                "window_start": item["window_start"],
                "window_frames": item["window_frames"],
                "answer_index": item["answer_index"],
                "dense_text": dense["text"],
                "dense_choice": dense_choice,
                "static_text": static["text"],
                "static_choice": static_choice,
                "shifted_text": shifted["text"],
                "shifted_choice": shifted_choice,
                "dense_correct": dense_choice == item["answer_index"],
                "static_correct": static_choice == item["answer_index"],
                "shifted_correct": shifted_choice == item["answer_index"],
                "dense_equals_static": dense["text"] == static["text"],
                "dense_equals_shifted": dense["text"] == shifted["text"],
                "static_reuse_ratio_mean": float(np.mean(static_reuse_ratios)),
                "shifted_reuse_ratio_mean": float(np.mean(shifted_reuse_ratios)),
            }
        )
    return results


def run_track_a_item(item_id: str) -> dict[str, Any]:
    return run_track_a_chunk([item_id])[0]


def _write_artifact(name: str, payload: dict[str, Any]) -> Path:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = ARTIFACT_DIR / name
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local Track A bring-up experiments.")
    parser.add_argument(
        "phase",
        choices=(
            "phase0_5",
            "phase0_75",
            "phase1_0",
            "track_a_pilot",
            "track_a_chunk",
            "track_a_item",
            "all",
        ),
    )
    parser.add_argument("--item-id", action="append", default=[])
    args = parser.parse_args()

    phases = (
        ("phase0_5", run_phase_0_5),
        ("phase0_75", run_phase_0_75),
        ("phase1_0", run_phase_1_0),
        ("track_a_pilot", run_track_a_pilot),
    )
    if args.phase == "track_a_chunk":
        if not args.item_id:
            raise SystemExit("--item-id is required for track_a_chunk")
        print(json.dumps(run_track_a_chunk(args.item_id), sort_keys=True))
        return
    if args.phase == "track_a_item":
        if len(args.item_id) != 1:
            raise SystemExit("--item-id is required for track_a_item")
        print(json.dumps(run_track_a_item(args.item_id[0]), sort_keys=True))
        return
    selected = (
        phases if args.phase == "all" else [phase for phase in phases if phase[0] == args.phase]
    )
    for phase_name, runner in selected:
        payload = runner()
        output_path = _write_artifact(f"{phase_name}.json", payload)
        print(output_path)


if __name__ == "__main__":
    main()
