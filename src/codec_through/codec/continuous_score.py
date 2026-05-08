"""Continuous codec-score helpers for the Phase 1.29 planner probe."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np
import numpy.typing as npt
from PIL import Image

from codec_through.codec.onevision_patchification import FuseMode, fuse_motion_residual
from codec_through.temporal import BlockClass


class CodecScoreSource(StrEnum):
    """Codec-derived score planes available to planner probes."""

    NOVEL_CODED = "novel_coded"
    MOTION = "motion"
    RESIDUAL = "residual"
    FUSED = "fused"


CODEC_SCORE_UNITS: dict[CodecScoreSource, str] = {
    CodecScoreSource.NOVEL_CODED: "fraction_intra_or_coded_block_flag",
    CodecScoreSource.MOTION: "macroblock_motion_vector_magnitude_pixels",
    CodecScoreSource.RESIDUAL: "repo_local_reconstructed_y_residual_proxy",
    CodecScoreSource.FUSED: "onevision_style_motion_residual_fused_score",
}


@dataclass(frozen=True, slots=True)
class ScoreThresholds:
    """Thresholds that map continuous codec scores to planner classes."""

    static_threshold: float
    shifted_threshold: float


def sparse_sample_indices(total_frames: int, frame_count: int) -> list[int]:
    """Return the exact linspace-style indices used by benchmark sampling."""

    if total_frames <= 0:
        raise ValueError("total_frames must be positive")
    if frame_count <= 0:
        raise ValueError("frame_count must be positive")
    if total_frames < frame_count:
        raise ValueError("total_frames must be >= frame_count")
    return [int(index) for index in np.linspace(0, total_frames - 1, frame_count, dtype=int)]


def sparse_pair_spans(indices: list[int]) -> list[tuple[int, int]]:
    """Return inclusive native-frame spans between adjacent sampled frames."""

    if len(indices) < 2:
        raise ValueError("need at least two sampled indices")
    spans: list[tuple[int, int]] = []
    for previous, current in zip(indices[:-1], indices[1:], strict=True):
        if current < previous:
            raise ValueError("sample indices must be non-decreasing")
        lo = previous + 1
        hi = current
        if lo > hi:
            lo = hi
        spans.append((lo, hi))
    return spans


def mean_pool_blocks(
    values: npt.NDArray[np.float32],
    *,
    block_size: int,
) -> npt.NDArray[np.float32]:
    """Pool a pixel-aligned score plane into block-wise means."""

    if values.ndim != 2:
        raise ValueError("values must be 2D")
    if block_size <= 0:
        raise ValueError("block_size must be positive")
    height, width = values.shape
    if height % block_size != 0 or width % block_size != 0:
        raise ValueError(
            "values shape must be divisible by block_size, "
            f"got {(height, width)} with block_size={block_size}"
        )
    rows = height // block_size
    cols = width // block_size
    reshaped = values.reshape(rows, block_size, cols, block_size)
    return np.asarray(reshaped.transpose(0, 2, 1, 3).mean(axis=(2, 3)), dtype=np.float32)


def project_macroblock_scores_to_token_grid(
    macroblock_scores: npt.NDArray[np.float32],
    *,
    macroblock_size: int,
    frame_width: int,
    frame_height: int,
    canvas_size: int,
    active_box: tuple[int, int, int, int],
    token_block: int,
) -> npt.NDArray[np.float32]:
    """Project native-frame macroblock scores into the padded Qwen token grid."""

    if macroblock_scores.ndim != 2:
        raise ValueError("macroblock_scores must be 2D")
    if macroblock_size <= 0 or token_block <= 0 or canvas_size <= 0:
        raise ValueError("macroblock_size, token_block, and canvas_size must be positive")
    if canvas_size % token_block != 0:
        raise ValueError("canvas_size must be divisible by token_block")
    if frame_width <= 0 or frame_height <= 0:
        raise ValueError("frame dimensions must be positive")

    left, top, right, bottom = active_box
    if not (0 <= left <= right <= canvas_size and 0 <= top <= bottom <= canvas_size):
        raise ValueError("active_box must lie within the padded canvas")
    active_width = right - left
    active_height = bottom - top
    if active_width <= 0 or active_height <= 0:
        raise ValueError("active_box must have positive area")

    expanded = np.repeat(
        np.repeat(macroblock_scores.astype(np.float32), macroblock_size, axis=0),
        macroblock_size,
        axis=1,
    )
    expected_height = macroblock_scores.shape[0] * macroblock_size
    expected_width = macroblock_scores.shape[1] * macroblock_size
    if expected_height < frame_height or expected_height - frame_height >= macroblock_size:
        raise ValueError(
            "macroblock_scores height does not match frame geometry: "
            f"{macroblock_scores.shape[0]} rows at macroblock_size={macroblock_size} "
            f"for frame_height={frame_height}"
        )
    if expected_width < frame_width or expected_width - frame_width >= macroblock_size:
        raise ValueError(
            "macroblock_scores width does not match frame geometry: "
            f"{macroblock_scores.shape[1]} cols at macroblock_size={macroblock_size} "
            f"for frame_width={frame_width}"
        )
    expanded = expanded[:frame_height, :frame_width]
    if expanded.shape != (frame_height, frame_width):
        raise ValueError(
            "expanded macroblock plane does not match frame geometry, "
            f"got {expanded.shape} vs {(frame_height, frame_width)}"
        )

    resized = Image.fromarray(expanded, mode="F").resize(
        (active_width, active_height),
        Image.Resampling.BICUBIC,
    )
    canvas = np.zeros((canvas_size, canvas_size), dtype=np.float32)
    projected = np.asarray(resized, dtype=np.float32)
    min_score = float(np.nanmin(macroblock_scores))
    max_score = float(np.nanmax(macroblock_scores))
    canvas[top:bottom, left:right] = np.clip(projected, min_score, max_score)
    return mean_pool_blocks(canvas, block_size=token_block)


def project_fused_motion_residual_to_token_grid(
    macroblock_motion: npt.NDArray[np.float32],
    macroblock_residual: npt.NDArray[np.float32],
    *,
    macroblock_size: int,
    frame_width: int,
    frame_height: int,
    canvas_size: int,
    active_box: tuple[int, int, int, int],
    token_block: int,
    mode: FuseMode = "weighted",
    motion_weight: float = 1.0,
    residual_weight: float = 1.0,
    normalize_inputs: bool = True,
) -> npt.NDArray[np.float32]:
    """Fuse MB motion/residual scores and project them into the model token grid."""

    if macroblock_motion.shape != macroblock_residual.shape:
        raise ValueError(
            "macroblock_motion and macroblock_residual must have the same shape, "
            f"got {macroblock_motion.shape} and {macroblock_residual.shape}"
        )
    if macroblock_motion.ndim != 2:
        raise ValueError("macroblock_motion and macroblock_residual must be 2D")
    fused = fuse_motion_residual(
        macroblock_motion,
        macroblock_residual,
        mode=mode,
        motion_weight=motion_weight,
        residual_weight=residual_weight,
        normalize_inputs=normalize_inputs,
    )
    return project_macroblock_scores_to_token_grid(
        fused,
        macroblock_size=macroblock_size,
        frame_width=frame_width,
        frame_height=frame_height,
        canvas_size=canvas_size,
        active_box=active_box,
        token_block=token_block,
    )


def macroblock_motion_magnitude(macroblocks: np.ndarray) -> npt.NDArray[np.float32]:
    """Return the larger available forward/backward MV magnitude per macroblock."""

    _validate_macroblock_fields(
        macroblocks,
        required=("mv_magnitude", "mv_magnitude_back"),
    )
    forward = np.asarray(macroblocks["mv_magnitude"], dtype=np.float32)
    backward = np.asarray(macroblocks["mv_magnitude_back"], dtype=np.float32)
    forward = np.nan_to_num(forward, nan=0.0, posinf=0.0, neginf=0.0)
    backward = np.nan_to_num(backward, nan=0.0, posinf=0.0, neginf=0.0)
    return np.maximum(forward, backward).astype(np.float32)


def macroblock_residual_energy(macroblocks: np.ndarray) -> npt.NDArray[np.float32]:
    """Return the repo-local residual-energy proxy per macroblock."""

    _validate_macroblock_fields(macroblocks, required=("residual_energy",))
    return np.asarray(macroblocks["residual_energy"], dtype=np.float32)


def macroblock_score_plane(
    macroblocks: np.ndarray,
    *,
    source: CodecScoreSource | str,
    mode: FuseMode = "weighted",
    motion_weight: float = 1.0,
    residual_weight: float = 1.0,
    normalize_inputs: bool = True,
) -> npt.NDArray[np.float32]:
    """Build a continuous score plane from H264MetadataExtractor macroblocks."""

    score_source = CodecScoreSource(source)
    if score_source is CodecScoreSource.NOVEL_CODED:
        _validate_macroblock_fields(macroblocks, required=("intra_flag", "cbf"))
        return np.asarray(
            macroblocks["intra_flag"] | macroblocks["cbf"],
            dtype=np.float32,
        )
    motion = macroblock_motion_magnitude(macroblocks)
    if score_source is CodecScoreSource.MOTION:
        return motion
    residual = macroblock_residual_energy(macroblocks)
    if score_source is CodecScoreSource.RESIDUAL:
        return residual
    if score_source is CodecScoreSource.FUSED:
        return fuse_motion_residual(
            motion,
            residual,
            mode=mode,
            motion_weight=motion_weight,
            residual_weight=residual_weight,
            normalize_inputs=normalize_inputs,
        )
    raise ValueError(f"unsupported codec score source: {source}")


def project_macroblock_metadata_to_token_grid(
    macroblocks: np.ndarray,
    *,
    source: CodecScoreSource | str,
    macroblock_size: int,
    frame_width: int,
    frame_height: int,
    canvas_size: int,
    active_box: tuple[int, int, int, int],
    token_block: int,
    mode: FuseMode = "weighted",
    motion_weight: float = 1.0,
    residual_weight: float = 1.0,
    normalize_inputs: bool = True,
) -> npt.NDArray[np.float32]:
    """Build and project a macroblock score plane into the model token grid."""

    score_plane = macroblock_score_plane(
        macroblocks,
        source=source,
        mode=mode,
        motion_weight=motion_weight,
        residual_weight=residual_weight,
        normalize_inputs=normalize_inputs,
    )
    return project_macroblock_scores_to_token_grid(
        score_plane,
        macroblock_size=macroblock_size,
        frame_width=frame_width,
        frame_height=frame_height,
        canvas_size=canvas_size,
        active_box=active_box,
        token_block=token_block,
    )


def codec_score_units(
    source: CodecScoreSource | str,
    *,
    fusion_mode: FuseMode = "weighted",
    motion_weight: float = 1.0,
    residual_weight: float = 1.0,
    normalize_inputs: bool = True,
) -> str:
    """Return the physical/proxy units for a codec score source."""

    score_source = CodecScoreSource(source)
    if score_source is not CodecScoreSource.FUSED:
        return CODEC_SCORE_UNITS[score_source]
    normalization = "percentile_normalized_inputs" if normalize_inputs else "raw_inputs"
    return (
        f"{CODEC_SCORE_UNITS[score_source]}:"
        f"mode={fusion_mode},motion_weight={motion_weight},"
        f"residual_weight={residual_weight},{normalization}"
    )


def _validate_macroblock_fields(macroblocks: np.ndarray, *, required: tuple[str, ...]) -> None:
    if macroblocks.ndim != 2:
        raise ValueError("macroblocks must be a 2D structured array")
    if macroblocks.dtype.fields is None:
        raise ValueError("macroblocks must be a structured array")
    missing = [field for field in required if field not in macroblocks.dtype.fields]
    if missing:
        raise ValueError(f"macroblocks missing required fields: {missing}")


def calibrate_score_thresholds(
    scores: npt.NDArray[np.float32],
    *,
    static_share: float,
    shifted_share: float,
) -> ScoreThresholds:
    """Choose score thresholds that match the requested static/shifted shares."""

    if scores.ndim != 1:
        raise ValueError("scores must be 1D")
    if scores.size == 0:
        raise ValueError("scores must not be empty")
    if not (0.0 <= static_share <= 1.0):
        raise ValueError("static_share must lie in [0, 1]")
    if not (0.0 <= shifted_share <= 1.0):
        raise ValueError("shifted_share must lie in [0, 1]")
    if static_share + shifted_share > 1.0:
        raise ValueError("static_share + shifted_share must be <= 1.0")
    static_threshold = float(np.quantile(scores, static_share))
    shifted_threshold = float(np.quantile(scores, static_share + shifted_share))
    if shifted_threshold < static_threshold:
        raise ValueError("shifted threshold must be >= static threshold")
    return ScoreThresholds(
        static_threshold=static_threshold,
        shifted_threshold=shifted_threshold,
    )


def classify_score_grid(
    score_grid: npt.NDArray[np.float32],
    *,
    thresholds: ScoreThresholds,
) -> npt.NDArray[np.int32]:
    """Map a continuous score grid into STATIC / SHIFTED / NOVEL classes."""

    if score_grid.ndim != 2:
        raise ValueError("score_grid must be 2D")
    classes = np.full(score_grid.shape, BlockClass.NOVEL, dtype=np.int32)
    classes[score_grid < thresholds.static_threshold] = BlockClass.STATIC
    classes[
        (score_grid >= thresholds.static_threshold) & (score_grid < thresholds.shifted_threshold)
    ] = BlockClass.SHIFTED
    return classes


def class_share_vector(
    classifications: list[npt.NDArray[np.int32]],
) -> npt.NDArray[np.float64]:
    """Return STATIC / SHIFTED / NOVEL shares over a list of class grids."""

    if not classifications:
        raise ValueError("classifications must not be empty")
    counts = np.zeros(3, dtype=np.int64)
    for classification in classifications:
        if classification.ndim != 2:
            raise ValueError("classification grids must be 2D")
        counts += np.bincount(classification.reshape(-1), minlength=3)
    total = int(counts.sum())
    if total <= 0:
        raise ValueError("classification grids contained no blocks")
    return counts.astype(np.float64) / float(total)
