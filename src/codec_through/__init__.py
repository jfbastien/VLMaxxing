"""codec-through research package."""

from codec_through.answers import extract_choice
from codec_through.ffmpeg import (
    ExtractedFrame,
    FramePacketInfo,
    extract_frames,
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
    "ExtractedFrame",
    "FLAT",
    "FramePacketInfo",
    "aggregate_to_token_grid",
    "classify_blocks",
    "classify_tokens",
    "extract_block_complexity",
    "extract_choice",
    "extract_frames",
    "frame_level_early_exit",
    "mean_i_frame_size",
    "probe_frame_count",
    "probe_frame_packets",
    "summarize_classification",
    "uniform_frame_indices",
]

__version__ = "0.1.0"
