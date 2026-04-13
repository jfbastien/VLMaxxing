"""Codec-Through Pipeline: MV + Pixel Diff + Q-Table Integration

Combined pipeline using codec metadata and pixel differencing together:

  Stage 0: IDR scene cut detection (force cache invalidation)
  Stage 1: MV header scan (frame-level early exit for >95% skip frames)
  Stage 2: Pixel diff classification (STATIC/SHIFTED/NOVEL cache decisions)
  Stage 3: Q-table spatial pre-filter (classify FLAT/CANDIDATE/COMPLEX for merge)

This module provides the building blocks. The benchmark runners import from here.
"""

import subprocess
import tempfile
import os
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image


# ═══════════════════════════════════════════════════════════════════
# Stage 0: IDR Scene Cut Detection
# ═══════════════════════════════════════════════════════════════════

def detect_keyframes(video_path: str, max_frames: int = 500) -> list[int]:
    """Detect I-frame / IDR positions in a video.

    Returns list of frame indices that are keyframes (scene cuts / I-frames).
    These should trigger full cache invalidation.
    """
    result = subprocess.run([
        "ffprobe", "-v", "quiet", "-select_streams", "v:0",
        "-show_frames", "-show_entries", "frame=pict_type,key_frame",
        "-of", "csv=p=0", video_path
    ], capture_output=True, text=True, timeout=60)

    keyframes = []
    for i, line in enumerate(result.stdout.strip().split('\n')):
        if i >= max_frames:
            break
        parts = line.strip().split(',')
        if len(parts) >= 2:
            is_key = parts[1].strip() == '1'
            pict_type = parts[0].strip()
            if is_key or pict_type == 'I':
                keyframes.append(i)

    return keyframes


def is_scene_cut(keyframes: list[int], frame_idx: int) -> bool:
    """Check if a frame is a scene cut (keyframe/IDR)."""
    return frame_idx in keyframes


# ═══════════════════════════════════════════════════════════════════
# Stage 1: MV Header Scan (Frame-Level Early Exit)
# ═══════════════════════════════════════════════════════════════════

def get_frame_sizes(video_path: str, max_frames: int = 500) -> list[dict]:
    """Get frame type and packet sizes for MV-based early exit.

    A P-frame with pkt_size << I-frame size is almost entirely skip blocks.
    This enables frame-level early exit: if the frame is tiny, ALL tokens are STATIC.
    """
    result = subprocess.run([
        "ffprobe", "-v", "quiet", "-select_streams", "v:0",
        "-show_frames",
        "-show_entries", "frame=pict_type,pkt_size,key_frame",
        "-of", "csv=p=0", video_path
    ], capture_output=True, text=True, timeout=60)

    frames = []
    for line in result.stdout.strip().split('\n')[:max_frames]:
        parts = line.strip().split(',')
        if len(parts) >= 3:
            frames.append({
                "pict_type": parts[0].strip(),
                "pkt_size": int(parts[1].strip()) if parts[1].strip().isdigit() else 0,
                "key_frame": parts[2].strip() == '1',
            })
    return frames


def frame_level_early_exit(frame_info: dict, avg_i_frame_size: float,
                           threshold: float = 0.02) -> Optional[str]:
    """Determine if a frame can skip pixel diff entirely.

    If P/B frame size < threshold × I-frame size, it's almost entirely
    skip blocks → classify ALL tokens as STATIC without decoding.

    Returns: 'ALL_STATIC' if early exit, None if pixel diff needed.
    """
    if frame_info["key_frame"] or frame_info["pict_type"] == "I":
        return None  # I-frames always need full encode

    if avg_i_frame_size <= 0:
        return None

    ratio = frame_info["pkt_size"] / avg_i_frame_size
    if ratio < threshold:
        return "ALL_STATIC"

    return None  # Need pixel diff to classify


# ═══════════════════════════════════════════════════════════════════
# Stage 2: Pixel Diff Classification (unchanged from experiments)
# ═══════════════════════════════════════════════════════════════════

def classify_blocks(frame_a: np.ndarray, frame_b: np.ndarray,
                    block_size: int = 28,
                    static_thresh: float = 3.0,
                    shift_thresh: float = 8.0) -> np.ndarray:
    """Classify each block as STATIC(0), SHIFTED(1), or NOVEL(2)."""
    h = min(frame_a.shape[0], frame_b.shape[0])
    w = min(frame_a.shape[1], frame_b.shape[1])
    diff = np.abs(frame_a[:h, :w].astype(float) - frame_b[:h, :w].astype(float)).mean(axis=2)
    bh = diff.shape[0] // block_size
    bw = diff.shape[1] // block_size
    if bh == 0 or bw == 0:
        return np.zeros((1, 1), dtype=np.int32)
    diff_crop = diff[:bh * block_size, :bw * block_size]
    blocks = diff_crop.reshape(bh, block_size, bw, block_size).mean(axis=(1, 3))
    c = np.full_like(blocks, 2, dtype=np.int32)
    c[blocks < static_thresh] = 0
    c[(blocks >= static_thresh) & (blocks < shift_thresh)] = 1
    return c


# ═══════════════════════════════════════════════════════════════════
# Stage 3: Q-Table Spatial Pre-Filter
# ═══════════════════════════════════════════════════════════════════

def extract_qtable_complexity(jpeg_path: str, token_block_size: int = 28) -> Optional[np.ndarray]:
    """Extract per-token complexity from JPEG Q-table.

    Returns 2D array of surviving AC coefficient counts per token-sized block.
    Returns None if not a JPEG or Q-table unavailable.
    """
    try:
        import jpegio
        jpg = jpegio.read(jpeg_path)
        dct = jpg.coef_arrays[0]  # Y channel
        h_blocks = dct.shape[0] // 8
        w_blocks = dct.shape[1] // 8

        # Count surviving AC coefficients per 8×8 block
        blocks = dct[:h_blocks * 8, :w_blocks * 8].reshape(h_blocks, 8, w_blocks, 8)
        blocks = blocks.transpose(0, 2, 1, 3)
        ac = blocks.copy()
        ac[:, :, 0, 0] = 0
        surviving = np.count_nonzero(ac.reshape(h_blocks, w_blocks, 64), axis=2)

        # Aggregate to token-sized blocks
        # Each token covers token_block_size pixels = token_block_size/8 JPEG blocks
        jpeg_per_token = token_block_size // 8  # e.g., 28/8 ≈ 3
        if jpeg_per_token < 1:
            jpeg_per_token = 1

        th = h_blocks // jpeg_per_token
        tw = w_blocks // jpeg_per_token
        if th == 0 or tw == 0:
            return None

        # Average surviving count per token region
        cropped = surviving[:th * jpeg_per_token, :tw * jpeg_per_token]
        token_complexity = cropped.reshape(
            th, jpeg_per_token, tw, jpeg_per_token
        ).mean(axis=(1, 3))

        return token_complexity

    except Exception:
        return None


def qtable_classify_tokens(complexity: np.ndarray,
                           flat_thresh: float = 3.0,
                           complex_thresh: float = 20.0) -> np.ndarray:
    """Classify tokens as FLAT(0), CANDIDATE(1), COMPLEX(2) from Q-table complexity.

    FLAT → merge aggressively (free decision)
    CANDIDATE → run learned scoring to decide
    COMPLEX → protect (free decision)
    """
    c = np.ones_like(complexity, dtype=np.int32)  # default CANDIDATE
    c[complexity <= flat_thresh] = 0   # FLAT
    c[complexity >= complex_thresh] = 2  # COMPLEX
    return c


def merge_flat_tokens(embeddings: np.ndarray, classification: np.ndarray) -> tuple[np.ndarray, int]:
    """Merge FLAT tokens by averaging neighbors.

    Simple approach: for each pair of adjacent FLAT tokens in the same row,
    average their embeddings and output one token instead of two.

    Returns (merged_embeddings, original_count) for computing reduction.
    """
    bh, bw = classification.shape
    embed_dim = embeddings.shape[-1]
    emb_2d = embeddings.reshape(bh, bw, embed_dim)

    merged = []
    for h in range(bh):
        w = 0
        while w < bw:
            if (classification[h, w] == 0 and w + 1 < bw and classification[h, w + 1] == 0):
                # Merge pair
                avg = (emb_2d[h, w] + emb_2d[h, w + 1]) / 2.0
                merged.append(avg)
                w += 2
            else:
                merged.append(emb_2d[h, w])
                w += 1

    return np.stack(merged, axis=0), bh * bw


# ═══════════════════════════════════════════════════════════════════
# Frame Extraction (JPEG for Q-table, PNG fallback)
# ═══════════════════════════════════════════════════════════════════

def extract_frames_jpeg(video_path: str, n_frames: int = 8,
                        start: float = 0, end: float = 0,
                        max_size: int = 560, jpeg_quality: int = 2) -> list[tuple[str, np.ndarray]]:
    """Extract frames as JPEG (for Q-table) and return (path, array) pairs.

    Returns list of (jpeg_path, numpy_array) tuples. Caller must clean up paths.
    """
    ss = ["-ss", str(start)] if start > 0 else []
    t = ["-t", str(end - start)] if end > start > 0 else []

    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0"]
        + ss + t + [video_path],
        capture_output=True, text=True, timeout=30)
    try:
        total = int(result.stdout.strip())
    except ValueError:
        total = 200

    indices = np.linspace(0, max(total - 1, 0), n_frames, dtype=int)
    results = []
    for idx in indices:
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = tmp.name
        subprocess.run(
            ["ffmpeg", "-v", "quiet", "-y"] + ss + t + [
                "-i", video_path,
                "-vf", f"select=eq(n\\,{idx}),scale={max_size}:{max_size}:force_original_aspect_ratio=decrease,pad={max_size}:{max_size}:(ow-iw)/2:(oh-ih)/2",
                "-q:v", str(jpeg_quality),
                "-vframes", "1", tmp_path],
            capture_output=True, timeout=30)
        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
            arr = np.array(Image.open(tmp_path).convert("RGB"))
            results.append((tmp_path, arr))
        elif os.path.exists(tmp_path):
            os.unlink(tmp_path)
    return results


# ═══════════════════════════════════════════════════════════════════
# Combined Pipeline
# ═══════════════════════════════════════════════════════════════════

class CodecThroughPipeline:
    """Full Codec-Through pipeline combining all stages.

    Usage:
        pipeline = CodecThroughPipeline(video_path)
        for frame_idx, frame_data in pipeline.process_frames(n_frames=8):
            # frame_data.classification: STATIC/SHIFTED/NOVEL per token
            # frame_data.qtable_class: FLAT/CANDIDATE/COMPLEX per token
            # frame_data.is_scene_cut: True if IDR/keyframe
            # frame_data.early_exit: True if frame-level skip (all STATIC)
    """

    def __init__(self, video_path: str):
        self.video_path = video_path
        self.keyframes = detect_keyframes(video_path)
        self.frame_info = get_frame_sizes(video_path)

        # Compute average I-frame size for early exit threshold
        i_sizes = [f["pkt_size"] for f in self.frame_info if f["pict_type"] == "I"]
        self.avg_i_size = np.mean(i_sizes) if i_sizes else 0

    def classify_frame(self, frame_idx: int, prev_frame: Optional[np.ndarray],
                       curr_frame: np.ndarray) -> dict:
        """Full classification pipeline for one frame."""
        result = {
            "is_scene_cut": is_scene_cut(self.keyframes, frame_idx),
            "early_exit": False,
            "classification": None,
            "pict_type": self.frame_info[frame_idx]["pict_type"] if frame_idx < len(self.frame_info) else "?",
        }

        # Stage 0: Scene cut → force full re-encode
        if result["is_scene_cut"]:
            return result

        # Stage 1: Frame-level early exit
        if frame_idx < len(self.frame_info):
            exit_type = frame_level_early_exit(self.frame_info[frame_idx], self.avg_i_size)
            if exit_type == "ALL_STATIC":
                result["early_exit"] = True
                # All tokens STATIC — no pixel diff needed
                if prev_frame is not None:
                    bh = curr_frame.shape[0] // 28
                    bw = curr_frame.shape[1] // 28
                    result["classification"] = np.zeros((bh, bw), dtype=np.int32)
                return result

        # Stage 2: Pixel diff classification
        if prev_frame is not None:
            result["classification"] = classify_blocks(prev_frame, curr_frame)

        return result
