"""codec-through research package."""

from codec_through.answers import extract_choice
from codec_through.feature_cache import (
    CACHE_KEY_SCHEMA_VERSION,
    DEFAULT_FEATURE_CACHE_DIR,
    CacheKey,
    frame_sequence_sha256,
    get_feature_cache,
    model_content_sha256,
    preprocessing_hash,
    put_feature_cache,
)
from codec_through.ffmpeg import (
    ExtractedFrame,
    FramePacketInfo,
    extract_frames,
    extract_frames_single_pass,
    frame_level_early_exit,
    mean_i_frame_size,
    probe_frame_count,
    probe_frame_packets,
    uniform_frame_indices,
)
from codec_through.qtable import (
    CANDIDATE,
    COMPLEX,
    FLAT,
    aggregate_to_token_grid,
    classify_tokens,
    extract_block_complexity,
)
from codec_through.temporal import (
    BlockClass,
    BlockThresholds,
    ClassificationSummary,
    block_size_from_vision_config,
    classify_blocks,
    summarize_classification,
)

__all__ = [
    "__version__",
    "BlockClass",
    "BlockThresholds",
    "ClassificationSummary",
    "COMPLEX",
    "CANDIDATE",
    "CacheKey",
    "CACHE_KEY_SCHEMA_VERSION",
    "block_size_from_vision_config",
    "DEFAULT_FEATURE_CACHE_DIR",
    "ExtractedFrame",
    "FLAT",
    "FramePacketInfo",
    "aggregate_to_token_grid",
    "classify_blocks",
    "classify_tokens",
    "extract_block_complexity",
    "extract_choice",
    "extract_frames",
    "extract_frames_single_pass",
    "frame_sequence_sha256",
    "frame_level_early_exit",
    "get_feature_cache",
    "mean_i_frame_size",
    "model_content_sha256",
    "preprocessing_hash",
    "probe_frame_count",
    "probe_frame_packets",
    "put_feature_cache",
    "summarize_classification",
    "uniform_frame_indices",
]

__version__ = "0.1.0"
