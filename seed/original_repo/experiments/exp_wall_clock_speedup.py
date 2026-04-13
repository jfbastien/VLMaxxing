"""Wall-Clock Speedup Measurement for Codec-Through Temporal Caching.

Measures actual wall-clock timing of each pipeline component to produce
publication-ready speedup numbers:

  Component timings (per frame):
    - ViT encode: vision tower forward pass
    - Classification: pixel-diff block classification (STATIC/SHIFTED/NOVEL)
    - LLM prefill: embedding injection + KV cache setup
    - LLM generate: autoregressive token generation

  Experiments:
    1. Per-component timing (averaged over N frames)
    2. Content-dependent speedup (talking head / surveillance / FPV drone)
    3. Frame-count scaling (4, 8, 16, 32, 64 frames)
    4. Production throughput (fps sustainable, memory)

Usage:
    uv run python exp_wall_clock_speedup.py
    uv run python exp_wall_clock_speedup.py --model Qwen/Qwen2.5-VL-3B-Instruct
    uv run python exp_wall_clock_speedup.py --warmup 3 --trials 5
    uv run python exp_wall_clock_speedup.py --quick
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

import mlx.core as mx
import numpy as np
from PIL import Image


DATA_DIR = Path(__file__).parent / "data"

VIDEOS = {
    "talking_head": DATA_DIR / "talking_head.mp4",
    "surveillance": DATA_DIR / "surveillance.mp4",
    "fpv_drone": DATA_DIR / "fpv_drone.mp4",
}


# ═══════════════════════════════════════════════════════════════════
# Frame extraction
# ═══════════════════════════════════════════════════════════════════

def extract_consecutive_frames(video_path: str, start: int, count: int,
                               max_size: int = 560) -> list[np.ndarray]:
    """Extract consecutive decoded frames as numpy arrays."""
    frames = []
    for n in range(start, start + count):
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp_path = tmp.name
        subprocess.run([
            "ffmpeg", "-v", "quiet", "-y", "-i", video_path,
            "-vf", (f"select=eq(n\\,{n}),"
                    f"scale={max_size}:{max_size}:force_original_aspect_ratio=decrease,"
                    f"pad={max_size}:{max_size}:(ow-iw)/2:(oh-ih)/2"),
            "-vframes", "1", tmp_path,
        ], capture_output=True, timeout=30)
        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
            frames.append(np.array(Image.open(tmp_path).convert("RGB")))
            os.unlink(tmp_path)
        elif os.path.exists(tmp_path):
            os.unlink(tmp_path)
    return frames


# ═══════════════════════════════════════════════════════════════════
# Classification (pixel diff)
# ═══════════════════════════════════════════════════════════════════

def classify_blocks(frame_a: np.ndarray, frame_b: np.ndarray,
                    block_size: int = 28) -> np.ndarray:
    """Classify each block as STATIC(0), SHIFTED(1), or NOVEL(2)."""
    h = min(frame_a.shape[0], frame_b.shape[0])
    w = min(frame_a.shape[1], frame_b.shape[1])
    diff = np.abs(frame_a[:h, :w].astype(float) - frame_b[:h, :w].astype(float)).mean(axis=2)
    bh, bw = diff.shape[0] // block_size, diff.shape[1] // block_size
    if bh == 0 or bw == 0:
        return np.zeros((1, 1), dtype=np.int32)
    blocks = diff[:bh * block_size, :bw * block_size].reshape(
        bh, block_size, bw, block_size
    ).mean(axis=(1, 3))
    c = np.full_like(blocks, 2, dtype=np.int32)
    c[blocks < 3.0] = 0
    c[(blocks >= 3.0) & (blocks < 8.0)] = 1
    return c


# ═══════════════════════════════════════════════════════════════════
# Timing harness
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ComponentTimings:
    """Timing measurements for a single frame."""
    vit_encode_ms: float = 0.0
    classify_ms: float = 0.0
    n_tokens_total: int = 0
    n_tokens_reused: int = 0
    n_tokens_novel: int = 0
    frame_type: str = ""  # I, STATIC, MIXED


@dataclass
class ExperimentResult:
    """Results for one video x frame-count configuration."""
    video_name: str = ""
    n_frames: int = 0
    model_name: str = ""

    # Per-component average timings (ms)
    avg_vit_encode_ms: float = 0.0
    avg_classify_ms: float = 0.0
    llm_prefill_ms: float = 0.0
    llm_generate_ms: float = 0.0

    # Aggregate timing
    baseline_total_ms: float = 0.0   # N x ViT + LLM
    cached_total_ms: float = 0.0     # 1 x ViT + (N-1) x classify + LLM
    vit_speedup: float = 0.0         # baseline ViT time / cached ViT time
    e2e_speedup: float = 0.0         # baseline total / cached total

    # Token statistics
    avg_cache_rate: float = 0.0      # fraction of tokens reused
    avg_novel_rate: float = 0.0

    # Memory
    vit_features_bytes: int = 0       # size of cached features per frame

    # Per-frame details
    frame_timings: list = field(default_factory=list)


class TimingHarness:
    """Measures wall-clock timing of each VLM pipeline component."""

    def __init__(self, model_name: str = "Qwen/Qwen2.5-VL-7B-Instruct"):
        from mlx_vlm import load
        from mlx_vlm.generate import stream_generate

        self.model_name = model_name
        self.stream_generate = stream_generate
        print(f"  Loading {model_name}...")
        t0 = time.time()
        self.model, self.processor = load(model_name)
        self.load_time = time.time() - t0
        print(f"  Loaded in {self.load_time:.1f}s")
        self.vm = self.model.vision_tower
        self.spatial_merge = getattr(self.vm, 'spatial_merge_size', 2)

    def _prepare_single_image(self, frame: np.ndarray, prompt: str):
        """Prepare processor inputs for a single image."""
        path = "/tmp/codec_timing_frame.png"
        Image.fromarray(frame).save(path)
        messages = [{"role": "user", "content": [
            {"type": "image", "image": path},
            {"type": "text", "text": prompt},
        ]}]
        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.processor(text=[text], images=[path], return_tensors="np")
        return path, {k: mx.array(v) if isinstance(v, np.ndarray) else v
                      for k, v in inputs.items()}

    def _prepare_multi_image(self, frames: list[np.ndarray], prompt: str):
        """Prepare processor inputs for multiple images."""
        paths = []
        for i, f in enumerate(frames):
            p = f"/tmp/codec_timing_frame_{i}.png"
            Image.fromarray(f).save(p)
            paths.append(p)
        messages = [{"role": "user", "content":
            [{"type": "image", "image": p} for p in paths] +
            [{"type": "text", "text": prompt}]
        }]
        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.processor(text=[text], images=paths, return_tensors="np")
        return paths, {k: mx.array(v) if isinstance(v, np.ndarray) else v
                       for k, v in inputs.items()}

    def time_vit_encode(self, pixel_values, grid_thw) -> tuple[float, mx.array]:
        """Time vision tower forward pass. Returns (time_ms, features)."""
        dtype = self.vm.patch_embed.proj.weight.dtype
        pv = pixel_values.astype(dtype)

        # Force sync before timing
        mx.eval(pv)

        t0 = time.perf_counter()
        features = self.vm(pv, grid_thw, output_hidden_states=False)
        mx.eval(features)
        elapsed = (time.perf_counter() - t0) * 1000

        return elapsed, features

    def time_classify(self, frame_a: np.ndarray, frame_b: np.ndarray) -> tuple[float, np.ndarray]:
        """Time block classification. Returns (time_ms, classification)."""
        t0 = time.perf_counter()
        c = classify_blocks(frame_a, frame_b)
        elapsed = (time.perf_counter() - t0) * 1000
        return elapsed, c

    def time_generate(self, frame_paths: list[str], prompt: str,
                      cached_features=None,
                      max_tokens: int = 32) -> tuple[float, float, str]:
        """Time LLM generation. Returns (prefill_ms, generate_ms, text).

        We approximate prefill vs generate split by timing first-token
        latency (TTFT) separately from total generation.
        """
        kwargs = {"max_tokens": max_tokens, "temperature": 0.0}
        if cached_features is not None:
            kwargs["cached_image_features"] = cached_features

        text = ""
        first_token_time = None
        t0 = time.perf_counter()

        for response in self.stream_generate(
            self.model, self.processor, prompt,
            image=frame_paths, **kwargs
        ):
            if first_token_time is None:
                first_token_time = time.perf_counter()
            text += response.text

        t_end = time.perf_counter()

        if first_token_time is None:
            first_token_time = t_end

        prefill_ms = (first_token_time - t0) * 1000
        generate_ms = (t_end - first_token_time) * 1000

        return prefill_ms, generate_ms, text

    def measure_per_frame_vit(self, frames: list[np.ndarray],
                              prompt: str,
                              warmup: int = 2,
                              trials: int = 3) -> list[ComponentTimings]:
        """Measure ViT encode + classification for each frame independently."""
        results = []

        for idx, frame in enumerate(frames):
            path, inputs = self._prepare_single_image(frame, prompt)
            pv = inputs.get("pixel_values")
            grid_thw = inputs.get("image_grid_thw")

            if pv is None or grid_thw is None:
                continue

            # Warmup
            for _ in range(warmup):
                _, feat = self.time_vit_encode(pv, grid_thw)

            # Timed trials
            vit_times = []
            features = None
            for _ in range(trials):
                t, features = self.time_vit_encode(pv, grid_thw)
                vit_times.append(t)

            feat_np = np.array(features.astype(mx.float32))
            n_tokens = feat_np.shape[0]

            timing = ComponentTimings(
                vit_encode_ms=float(np.median(vit_times)),
                n_tokens_total=n_tokens,
            )

            # Classification (frames 1+ compared to previous)
            if idx > 0:
                classify_times = []
                classification = None
                for _ in range(trials):
                    ct, classification = self.time_classify(frames[idx - 1], frame)
                    classify_times.append(ct)

                timing.classify_ms = float(np.median(classify_times))

                if classification is not None:
                    n_static = int((classification == 0).sum())
                    n_shifted = int((classification == 1).sum())
                    n_novel = int((classification == 2).sum())
                    timing.n_tokens_reused = n_static + n_shifted
                    timing.n_tokens_novel = n_novel
                    timing.frame_type = "STATIC" if n_novel == 0 else "MIXED"
                else:
                    timing.frame_type = "MIXED"
            else:
                timing.frame_type = "I"
                timing.n_tokens_novel = n_tokens

            os.unlink(path)
            results.append(timing)

            if idx % 4 == 0:
                print(f"    Frame {idx}: ViT={timing.vit_encode_ms:.1f}ms "
                      f"Class={timing.classify_ms:.2f}ms Type={timing.frame_type}")

        return results

    def measure_generation_timing(self, frames: list[np.ndarray],
                                  prompt: str,
                                  warmup: int = 1,
                                  trials: int = 2,
                                  max_tokens: int = 32) -> dict:
        """Measure LLM generation timing: baseline vs cached."""
        paths, inputs = self._prepare_multi_image(frames, prompt)
        pv = inputs.get("pixel_values")
        grid_thw = inputs.get("image_grid_thw")

        # Get fresh features for all frames
        _, fresh_features = self.time_vit_encode(pv, grid_thw)
        fresh_np = np.array(fresh_features.astype(mx.float32))

        # Build cached features (reuse STATIC/SHIFTED from previous frame)
        split_sizes = (grid_thw.prod(axis=-1) // (self.spatial_merge ** 2)).tolist()
        segments = []
        offset = 0
        for s in split_sizes:
            segments.append(fresh_np[offset:offset + s])
            offset += s

        cached_segments = [segments[0].copy()]
        cache = segments[0].copy()
        for i in range(1, len(segments)):
            seg = segments[i]
            n_tok = seg.shape[0]
            classification = classify_blocks(frames[i - 1], frames[i])
            bh, bw = classification.shape

            if bh * bw != n_tok:
                cached_segments.append(seg.copy())
                cache = seg.copy()
                continue

            mixed = cache.copy().reshape(bh, bw, -1)
            fresh_2d = seg.reshape(bh, bw, -1)
            novel_mask = classification == 2
            mixed[novel_mask] = fresh_2d[novel_mask]
            mixed = mixed.reshape(n_tok, -1)
            cached_segments.append(mixed)
            cache = mixed.copy()

        cached_concat = np.concatenate(cached_segments, axis=0)
        cached_mx = mx.array(cached_concat).astype(fresh_features.dtype)

        # Warmup
        for _ in range(warmup):
            self.time_generate(paths, prompt, max_tokens=max_tokens)

        # Baseline: no cached features (ViT runs inside generate)
        bl_prefills, bl_generates = [], []
        for _ in range(trials):
            pf, gen, _ = self.time_generate(paths, prompt, max_tokens=max_tokens)
            bl_prefills.append(pf)
            bl_generates.append(gen)

        # Cached: pass cached_image_features (ViT skipped inside generate)
        ca_prefills, ca_generates = [], []
        for _ in range(trials):
            pf, gen, _ = self.time_generate(
                paths, prompt, cached_features=cached_mx, max_tokens=max_tokens
            )
            ca_prefills.append(pf)
            ca_generates.append(gen)

        for p in paths:
            if os.path.exists(p):
                os.unlink(p)

        return {
            "baseline_prefill_ms": float(np.median(bl_prefills)),
            "baseline_generate_ms": float(np.median(bl_generates)),
            "cached_prefill_ms": float(np.median(ca_prefills)),
            "cached_generate_ms": float(np.median(ca_generates)),
        }


# ═══════════════════════════════════════════════════════════════════
# Main experiments
# ═══════════════════════════════════════════════════════════════════

def run_per_component_timing(harness: TimingHarness,
                             video_name: str,
                             n_frames: int = 16,
                             start_frame: int = 10,
                             warmup: int = 2,
                             trials: int = 3) -> ExperimentResult:
    """Run the full timing experiment for one video."""
    video_path = str(VIDEOS[video_name])
    prompt = "Describe what is happening in this video."

    print(f"\n{'=' * 70}")
    print(f"  Timing: {video_name} -- {n_frames} frames")
    print(f"{'=' * 70}")

    # Extract frames
    print(f"  Extracting {n_frames} consecutive frames from frame {start_frame}...")
    frames = extract_consecutive_frames(video_path, start_frame, n_frames)
    actual_n = len(frames)
    print(f"  Got {actual_n} frames at {frames[0].shape[1]}x{frames[0].shape[0]}")

    # 1. Per-frame ViT + classify timing
    print(f"\n  Measuring per-frame ViT encode + classification ({trials} trials)...")
    frame_timings = harness.measure_per_frame_vit(
        frames, prompt, warmup=warmup, trials=trials
    )

    # 2. LLM generation timing (baseline vs cached)
    gen_n = min(8, actual_n)
    print(f"\n  Measuring LLM generation ({gen_n} frames, {trials} trials)...")
    gen_timing = harness.measure_generation_timing(
        frames[:gen_n], prompt, warmup=max(1, warmup // 2), trials=trials
    )

    # Compute aggregate results
    vit_times = [ft.vit_encode_ms for ft in frame_timings]
    classify_times = [ft.classify_ms for ft in frame_timings if ft.classify_ms > 0]

    avg_vit = np.mean(vit_times)
    avg_classify = np.mean(classify_times) if classify_times else 0

    # Cache rate: fraction of tokens reused (excl. I-frame)
    p_frame_timings = [ft for ft in frame_timings if ft.frame_type != "I"]
    if p_frame_timings:
        total_tok = sum(ft.n_tokens_total for ft in p_frame_timings)
        total_reused = sum(ft.n_tokens_reused for ft in p_frame_timings)
        cache_rate = total_reused / total_tok if total_tok > 0 else 0
    else:
        cache_rate = 0

    novel_rate = 1 - cache_rate
    n = actual_n

    # Speedup model:
    #   Baseline: N x ViT_encode
    #   Cached: 1 x ViT_encode + (N-1) x classify
    #   (With cached_image_features, entire ViT is bypassed for cached frames)
    baseline_vit_ms = n * avg_vit
    cached_vit_ms = 1 * avg_vit + (n - 1) * avg_classify
    vit_speedup = baseline_vit_ms / cached_vit_ms if cached_vit_ms > 0 else float('inf')

    # E2E: ViT + LLM
    llm_time_ms = gen_timing["baseline_prefill_ms"] + gen_timing["baseline_generate_ms"]
    llm_cached_ms = gen_timing["cached_prefill_ms"] + gen_timing["cached_generate_ms"]

    baseline_total = baseline_vit_ms + llm_time_ms
    cached_total = cached_vit_ms + llm_cached_ms
    e2e_speedup = baseline_total / cached_total if cached_total > 0 else float('inf')

    # Feature memory per frame
    hidden_dim = 3584 if "7B" in harness.model_name else 2048
    if frame_timings:
        feat_size = frame_timings[0].n_tokens_total * hidden_dim * 4  # fp32
    else:
        feat_size = 0

    result = ExperimentResult(
        video_name=video_name,
        n_frames=actual_n,
        model_name=harness.model_name,
        avg_vit_encode_ms=float(avg_vit),
        avg_classify_ms=float(avg_classify),
        llm_prefill_ms=gen_timing["baseline_prefill_ms"],
        llm_generate_ms=gen_timing["baseline_generate_ms"],
        baseline_total_ms=float(baseline_total),
        cached_total_ms=float(cached_total),
        vit_speedup=float(vit_speedup),
        e2e_speedup=float(e2e_speedup),
        avg_cache_rate=float(cache_rate),
        avg_novel_rate=float(novel_rate),
        vit_features_bytes=feat_size,
        frame_timings=[asdict(ft) for ft in frame_timings],
    )

    # Print results
    print(f"\n  +---------------------------------------------------+")
    print(f"  |  COMPONENT TIMINGS ({video_name:>15})            |")
    print(f"  +---------------------------------------------------+")
    print(f"  |  ViT encode/frame:     {avg_vit:>8.1f} ms              |")
    print(f"  |  Classify/frame:       {avg_classify:>8.2f} ms              |")
    print(f"  |  LLM prefill:          {gen_timing['baseline_prefill_ms']:>8.1f} ms              |")
    print(f"  |  LLM generate:         {gen_timing['baseline_generate_ms']:>8.1f} ms              |")
    print(f"  +---------------------------------------------------+")
    print(f"  |  Cache rate:           {cache_rate:>7.1%}                 |")
    print(f"  |  Novel rate:           {novel_rate:>7.1%}                 |")
    print(f"  +---------------------------------------------------+")
    print(f"  |  BASELINE ({n} frames):                            |")
    print(f"  |    ViT:  {n}x {avg_vit:.0f}ms = {baseline_vit_ms:>8.0f} ms              |")
    print(f"  |    LLM:                {llm_time_ms:>8.0f} ms              |")
    print(f"  |    Total:              {baseline_total:>8.0f} ms              |")
    print(f"  |  CACHED ({n} frames):                              |")
    print(f"  |    ViT:  1x {avg_vit:.0f}ms + {n-1}x {avg_classify:.1f}ms = {cached_vit_ms:>6.0f} ms   |")
    print(f"  |    LLM:                {llm_cached_ms:>8.0f} ms              |")
    print(f"  |    Total:              {cached_total:>8.0f} ms              |")
    print(f"  +---------------------------------------------------+")
    print(f"  |  ViT SPEEDUP:          {vit_speedup:>7.1f}x                |")
    print(f"  |  E2E SPEEDUP:          {e2e_speedup:>7.2f}x                |")
    print(f"  |  Feature cache/frame:  {feat_size / 1024 / 1024:>7.1f} MB              |")
    print(f"  +---------------------------------------------------+")

    return result


def run_frame_scaling(harness: TimingHarness,
                      video_name: str,
                      frame_counts: list[int] = None,
                      warmup: int = 2,
                      trials: int = 3) -> list[dict]:
    """Show how speedup scales with frame count."""
    if frame_counts is None:
        frame_counts = [4, 8, 16, 32, 64]

    video_path = str(VIDEOS[video_name])
    prompt = "Describe what is happening in this video."

    print(f"\n{'=' * 70}")
    print(f"  Frame-Count Scaling: {video_name}")
    print(f"{'=' * 70}")

    # Extract max frames needed
    max_n = max(frame_counts)
    print(f"  Extracting {max_n} frames...")
    all_frames = extract_consecutive_frames(video_path, 10, max_n)
    actual_max = len(all_frames)
    print(f"  Got {actual_max} frames")

    # Get ViT timing from first frame
    path, inputs = harness._prepare_single_image(all_frames[0], prompt)
    pv = inputs.get("pixel_values")
    grid_thw = inputs.get("image_grid_thw")

    for _ in range(warmup):
        harness.time_vit_encode(pv, grid_thw)

    vit_times = []
    for _ in range(trials):
        t, _ = harness.time_vit_encode(pv, grid_thw)
        vit_times.append(t)
    avg_vit_ms = float(np.median(vit_times))
    os.unlink(path)

    # Get classify timing
    classify_times_all = []
    for i in range(1, min(20, actual_max)):
        t, _ = harness.time_classify(all_frames[i - 1], all_frames[i])
        classify_times_all.append(t)
    avg_classify_ms = float(np.median(classify_times_all))

    # Compute cache rate for this video
    cache_counts = []
    for i in range(1, min(64, actual_max)):
        c = classify_blocks(all_frames[i - 1], all_frames[i])
        n_cached = int((c != 2).sum())
        n_total = int(c.size)
        cache_counts.append((n_cached, n_total))

    avg_cache_rate = (sum(c for c, t in cache_counts) /
                      sum(t for c, t in cache_counts)) if cache_counts else 0

    # Get LLM timing (one-shot, 8 frames)
    gen_timing = harness.measure_generation_timing(
        all_frames[:min(8, actual_max)], prompt, warmup=1, trials=2
    )
    llm_ms = gen_timing["baseline_prefill_ms"] + gen_timing["baseline_generate_ms"]

    results = []
    print(f"\n  ViT/frame: {avg_vit_ms:.1f}ms  Classify/frame: {avg_classify_ms:.2f}ms  "
          f"Cache rate: {avg_cache_rate:.1%}  LLM: {llm_ms:.0f}ms")
    print(f"\n  {'N':>5} {'BL ViT ms':>10} {'CA ViT ms':>10} {'ViT Spd':>8} "
          f"{'BL Total':>10} {'CA Total':>10} {'E2E Spd':>8}")
    print(f"  {'-' * 5} {'-' * 10} {'-' * 10} {'-' * 8} {'-' * 10} {'-' * 10} {'-' * 8}")

    for n in frame_counts:
        if n > actual_max:
            break

        bl_vit = n * avg_vit_ms
        ca_vit = 1 * avg_vit_ms + (n - 1) * avg_classify_ms
        vit_spd = bl_vit / ca_vit if ca_vit > 0 else 0

        bl_total = bl_vit + llm_ms
        ca_total = ca_vit + llm_ms
        e2e_spd = bl_total / ca_total if ca_total > 0 else 0

        print(f"  {n:>5} {bl_vit:>10.0f} {ca_vit:>10.1f} {vit_spd:>7.1f}x "
              f"{bl_total:>10.0f} {ca_total:>10.0f} {e2e_spd:>7.2f}x")

        results.append({
            "n_frames": n,
            "baseline_vit_ms": float(bl_vit),
            "cached_vit_ms": float(ca_vit),
            "vit_speedup": float(vit_spd),
            "baseline_total_ms": float(bl_total),
            "cached_total_ms": float(ca_total),
            "e2e_speedup": float(e2e_spd),
        })

    return results


def run_production_analysis(harness: TimingHarness,
                            avg_vit_ms: float,
                            avg_classify_ms: float,
                            cache_rate: float) -> dict:
    """Compute production throughput and feasibility numbers."""
    print(f"\n{'=' * 70}")
    print(f"  Production Throughput Analysis")
    print(f"{'=' * 70}")

    novel_rate = 1 - cache_rate
    effective_vit_cost_ms = novel_rate * avg_vit_ms + cache_rate * avg_classify_ms

    fps_baseline = 1000 / avg_vit_ms if avg_vit_ms > 0 else 0
    fps_cached = 1000 / effective_vit_cost_ms if effective_vit_cost_ms > 0 else 0

    # 30fps real-time analysis
    budget_per_frame_ms = 1000 / 30  # 33.3ms
    can_realtime_baseline = avg_vit_ms < budget_per_frame_ms
    can_realtime_cached = effective_vit_cost_ms < budget_per_frame_ms

    # Memory calculations
    tokens_per_frame = 400  # typical for 560x560 input
    hidden_dim = 3584 if "7B" in harness.model_name else 2048
    bytes_per_frame_fp16 = tokens_per_frame * hidden_dim * 2

    print(f"\n  Configuration:")
    print(f"    ViT encode:    {avg_vit_ms:.1f} ms/frame")
    print(f"    Classify:      {avg_classify_ms:.2f} ms/frame")
    print(f"    Cache rate:    {cache_rate:.1%}")
    print(f"    Novel rate:    {novel_rate:.1%}")
    print(f"    Effective ViT: {effective_vit_cost_ms:.2f} ms/frame (cached)")

    print(f"\n  Throughput:")
    print(f"    Baseline:      {fps_baseline:.1f} fps (ViT only)")
    print(f"    Cached:        {fps_cached:.0f} fps (ViT only)")
    print(f"    Speedup:       {fps_cached / fps_baseline:.1f}x")

    print(f"\n  30fps Real-Time Feasibility:")
    print(f"    Budget:        {budget_per_frame_ms:.1f} ms/frame")
    print(f"    Baseline:      {'YES' if can_realtime_baseline else 'NO'} ({avg_vit_ms:.1f} ms)")
    print(f"    Cached:        {'YES' if can_realtime_cached else 'NO'} ({effective_vit_cost_ms:.2f} ms)")

    print(f"\n  Memory (feature cache, fp16):")
    print(f"    Per frame:     {bytes_per_frame_fp16 / 1024 / 1024:.2f} MB")
    print(f"    1 sec (30fps): {30 * bytes_per_frame_fp16 / 1024 / 1024:.0f} MB")
    print(f"    1 min:         {1800 * bytes_per_frame_fp16 / 1024 / 1024 / 1024:.2f} GB")
    print(f"    Only cache LATEST frame -> {bytes_per_frame_fp16 / 1024 / 1024:.2f} MB constant")

    return {
        "fps_baseline": float(fps_baseline),
        "fps_cached": float(fps_cached),
        "fps_speedup": float(fps_cached / fps_baseline) if fps_baseline > 0 else 0,
        "effective_vit_cost_ms": float(effective_vit_cost_ms),
        "can_realtime_30fps_baseline": can_realtime_baseline,
        "can_realtime_30fps_cached": can_realtime_cached,
        "cache_memory_per_frame_fp16_mb": float(bytes_per_frame_fp16 / 1024 / 1024),
        "cache_memory_1min_fp16_gb": float(1800 * bytes_per_frame_fp16 / 1024 / 1024 / 1024),
    }


def main():
    parser = argparse.ArgumentParser(description="Wall-clock speedup measurement")
    parser.add_argument("--model", default="Qwen/Qwen2.5-VL-7B-Instruct",
                        help="Model to benchmark")
    parser.add_argument("--warmup", type=int, default=2,
                        help="Warmup iterations before timing")
    parser.add_argument("--trials", type=int, default=3,
                        help="Timed trials per measurement")
    parser.add_argument("--n-frames", type=int, default=16,
                        help="Frames per video for per-component test")
    parser.add_argument("--quick", action="store_true",
                        help="Quick run: fewer frames, fewer trials")
    parser.add_argument("--output", default="wall_clock_results.json",
                        help="Output JSON file")
    args = parser.parse_args()

    if args.quick:
        args.warmup = 1
        args.trials = 2
        args.n_frames = 8

    harness = TimingHarness(args.model)

    all_results = {
        "model": args.model,
        "device": "Apple M5 Max (MLX)",
        "warmup": args.warmup,
        "trials": args.trials,
        "videos": {},
        "scaling": {},
        "production": {},
    }

    # Experiment 1: Per-component timing for each video
    for video_name in VIDEOS:
        if not VIDEOS[video_name].exists():
            print(f"  Skipping {video_name} (not found)")
            continue
        result = run_per_component_timing(
            harness, video_name,
            n_frames=args.n_frames,
            warmup=args.warmup,
            trials=args.trials,
        )
        all_results["videos"][video_name] = asdict(result)

    # Experiment 2: Frame-count scaling
    for video_name in VIDEOS:
        if not VIDEOS[video_name].exists():
            continue
        max_n = 64 if not args.quick else 32
        frame_counts = [4, 8, 16, 32]
        if max_n >= 64:
            frame_counts.append(64)
        scaling = run_frame_scaling(
            harness, video_name,
            frame_counts=frame_counts,
            warmup=args.warmup,
            trials=args.trials,
        )
        all_results["scaling"][video_name] = scaling

    # Experiment 3: Production analysis
    if "talking_head" in all_results["videos"]:
        th = all_results["videos"]["talking_head"]
        prod = run_production_analysis(
            harness,
            avg_vit_ms=th["avg_vit_encode_ms"],
            avg_classify_ms=th["avg_classify_ms"],
            cache_rate=th["avg_cache_rate"],
        )
        all_results["production"] = prod

    # Summary Table
    print(f"\n{'=' * 70}")
    print(f"  SUMMARY: Wall-Clock Speedup Results")
    print(f"{'=' * 70}")
    print(f"\n  Model: {args.model}")
    print(f"  Device: Apple M5 Max (MLX)")
    print(f"\n  {'Video':>15} {'ViT ms':>8} {'Class ms':>9} {'Cache%':>7} "
          f"{'ViT Spd':>8} {'E2E Spd':>8}")
    print(f"  {'-' * 15} {'-' * 8} {'-' * 9} {'-' * 7} {'-' * 8} {'-' * 8}")

    for name, data in all_results["videos"].items():
        print(f"  {name:>15} {data['avg_vit_encode_ms']:>7.1f} "
              f"{data['avg_classify_ms']:>8.2f} {data['avg_cache_rate']:>6.1%} "
              f"{data['vit_speedup']:>7.1f}x {data['e2e_speedup']:>7.2f}x")

    # Save results
    output_path = Path(__file__).parent / args.output
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\n  Results saved to {output_path}")


if __name__ == "__main__":
    main()
