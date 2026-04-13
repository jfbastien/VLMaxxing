"""TOMATO + MVBench on Qwen2.5-VL-7B via mlx-vlm.

Uses mlx-vlm's native cached_image_features to bypass the vision tower
for cached tokens. Runs on M5 Max at ~36 tok/s.

Usage:
    uv run python run_tomato_mlx.py --benchmark tomato --n 20
    uv run python run_tomato_mlx.py --benchmark mvbench --n 10
    uv run python run_tomato_mlx.py --benchmark both --n 15
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import mlx.core as mx
import numpy as np
from PIL import Image
from tqdm import tqdm


TOMATO_DIR = Path(__file__).parent / "tomato-bench"
MVBENCH_VIDEO_DIR = Path(__file__).parent / "mvbench_data" / "video"


def extract_frames(video_path: str, n_frames: int = 8,
                   start: float = 0, end: float = 0,
                   max_size: int = 560) -> list[np.ndarray]:
    """Extract uniformly sampled frames."""
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
    frames = []
    for idx in indices:
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp_path = tmp.name
        subprocess.run(
            ["ffmpeg", "-v", "quiet", "-y"] + ss + t + [
                "-i", video_path,
                "-vf", f"select=eq(n\\,{idx}),scale={max_size}:{max_size}:force_original_aspect_ratio=decrease,pad={max_size}:{max_size}:(ow-iw)/2:(oh-ih)/2",
                "-vframes", "1", tmp_path],
            capture_output=True, timeout=30)
        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
            frames.append(np.array(Image.open(tmp_path).convert("RGB")))
            os.unlink(tmp_path)
        elif os.path.exists(tmp_path):
            os.unlink(tmp_path)
    return frames


def classify_blocks(frame_a: np.ndarray, frame_b: np.ndarray, block_size: int = 28) -> np.ndarray:
    h = min(frame_a.shape[0], frame_b.shape[0])
    w = min(frame_a.shape[1], frame_b.shape[1])
    diff = np.abs(frame_a[:h, :w].astype(float) - frame_b[:h, :w].astype(float)).mean(axis=2)
    bh, bw = diff.shape[0] // block_size, diff.shape[1] // block_size
    if bh == 0 or bw == 0:
        return np.zeros((1, 1), dtype=np.int32)
    blocks = diff[:bh*block_size, :bw*block_size].reshape(bh, block_size, bw, block_size).mean(axis=(1, 3))
    c = np.full_like(blocks, 2, dtype=np.int32)
    c[blocks < 3.0] = 0
    c[(blocks >= 3.0) & (blocks < 8.0)] = 1
    return c


def extract_choice(response: str, candidates: list[str]) -> int:
    response = response.strip().upper()
    for i in range(len(candidates)):
        letter = chr(65 + i)
        if response.startswith(letter):
            return i
    for i, c in enumerate(candidates):
        if c.lower() in response.lower():
            return i
    return 0


class CachedVLM:
    """Qwen2.5-VL-7B with temporal embedding caching via mlx-vlm."""

    def __init__(self, model_name: str = "Qwen/Qwen2.5-VL-7B-Instruct"):
        from mlx_vlm import load
        print(f"  Loading {model_name}...")
        t0 = time.time()
        self.model, self.processor = load(model_name)
        print(f"  Loaded in {time.time()-t0:.1f}s")
        self.vm = self.model.vision_tower

    def _prepare_inputs(self, frame_paths: list[str], prompt: str):
        """Prepare processor inputs for multi-image."""
        messages = [{"role": "user", "content":
            [{"type": "image", "image": p} for p in frame_paths] +
            [{"type": "text", "text": prompt}]
        }]
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.processor(text=[text], images=frame_paths, return_tensors="np")
        return {k: mx.array(v) if isinstance(v, np.ndarray) else v for k, v in inputs.items()}

    def encode_vision(self, pixel_values, grid_thw):
        """Run vision tower, return features."""
        dtype = self.vm.patch_embed.proj.weight.dtype
        pv = pixel_values.astype(dtype)
        features = self.vm(pv, grid_thw, output_hidden_states=False)
        mx.eval(features)
        return features

    def generate(self, frame_paths: list[str], prompt: str,
                 cached_features=None, max_tokens: int = 64) -> str:
        """Generate text, optionally with cached vision features."""
        from mlx_vlm.generate import stream_generate

        kwargs = {"max_tokens": max_tokens, "temperature": 0.0}
        if cached_features is not None:
            kwargs["cached_image_features"] = cached_features

        text = ""
        for response in stream_generate(
            self.model, self.processor, prompt,
            image=frame_paths, **kwargs
        ):
            text += response.text
        return text

    def run_comparison(self, frames: list[np.ndarray], prompt: str,
                       max_tokens: int = 64) -> dict:
        """Run baseline vs cached comparison on a set of frames."""
        # Save frames to temp files
        frame_paths = []
        for i, f in enumerate(frames):
            path = f"/tmp/codec_frame_{i}.png"
            Image.fromarray(f).save(path)
            frame_paths.append(path)

        # Prepare inputs to get pixel_values and grid_thw
        inputs = self._prepare_inputs(frame_paths, prompt)
        pixel_values = inputs.get("pixel_values")
        grid_thw = inputs.get("image_grid_thw")

        # Get fresh vision features
        if pixel_values is not None and grid_thw is not None:
            fresh_features = self.encode_vision(pixel_values, grid_thw)

            # Build cached features: first frame fresh, rest mixed
            spatial_merge = getattr(self.vm, 'spatial_merge_size', 2)
            split_sizes = (grid_thw.prod(axis=-1) // (spatial_merge ** 2)).tolist()
            # Convert to numpy for slicing
            fresh_np = np.array(fresh_features.astype(mx.float32))
            segments = []
            offset = 0
            for s in split_sizes:
                segments.append(fresh_np[offset:offset+s])
                offset += s

            # Cache: first frame is I-frame, rest use cached for STATIC/SHIFTED
            cached_segments = [segments[0].copy()]
            cache = segments[0].copy()
            total_reused = 0
            total_tokens = 0

            for i in range(1, len(segments)):
                seg = segments[i]
                n_tok = seg.shape[0]
                classification = classify_blocks(frames[i-1], frames[i])
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

                total_reused += int((classification != 2).sum())
                total_tokens += int(classification.size)
                cached_segments.append(mixed)
                cache = mixed.copy()

            cached_concat = np.concatenate(cached_segments, axis=0)
            cached_features_mx = mx.array(cached_concat).astype(fresh_features.dtype)
            reuse_pct = total_reused / total_tokens if total_tokens > 0 else 0
        else:
            cached_features_mx = None
            reuse_pct = 0

        # Baseline: fresh encode (no cached features)
        baseline = self.generate(frame_paths, prompt, max_tokens=max_tokens)

        # Cached: skip vision tower
        cached = self.generate(frame_paths, prompt,
                               cached_features=cached_features_mx,
                               max_tokens=max_tokens)

        # Cleanup
        for p in frame_paths:
            os.unlink(p)

        return {
            "baseline": baseline,
            "cached": cached,
            "reuse_pct": reuse_pct,
        }


def load_tomato(split: str, n: int) -> list[dict]:
    if split == "ALL":
        qs = []
        for f in sorted(TOMATO_DIR.glob("data/*.json")):
            with open(f) as fh:
                data = json.load(fh)
            for k, v in list(data.items())[:n]:
                v["id"] = k; v["split"] = f.stem; qs.append(v)
        return qs
    with open(TOMATO_DIR / "data" / f"{split}.json") as f:
        data = json.load(f)
    return [dict(v, id=k, split=split) for k, v in list(data.items())[:n]]


def run_tomato(vlm: CachedVLM, split: str, n: int, n_frames: int):
    questions = load_tomato(split, n)
    print(f"\n  TOMATO: {len(questions)} questions, {n_frames} frames")

    results = []
    for q in tqdm(questions, desc="TOMATO"):
        vpath = str(TOMATO_DIR / "videos" / q["demonstration_type"] / f"{q['key']}.mp4")
        if not os.path.exists(vpath):
            continue

        options = q["options"]
        choices = [chr(65+i) for i in range(len(options))]
        gt_idx = q["answer"]
        index2ans = {choices[i]: options[i] for i in range(len(options))}

        prompt = f"Analyze the video frames. Question: {q['question']}\nOptions: {index2ans}\nAnswer with just the letter."

        frames = extract_frames(vpath, n_frames)
        if len(frames) < 2:
            continue

        r = vlm.run_comparison(frames, prompt)
        bl_idx = extract_choice(r["baseline"], choices)
        ca_idx = extract_choice(r["cached"], choices)

        results.append({
            "split": q["split"], "gt": gt_idx,
            "bl_correct": bl_idx == gt_idx, "ca_correct": ca_idx == gt_idx,
            "match": bl_idx == ca_idx, "reuse": r["reuse_pct"],
        })
        mark = "✓" if bl_idx == ca_idx else "✗"
        tqdm.write(f"  [{mark}] GT={choices[gt_idx]} BL={choices[bl_idx]} CA={choices[ca_idx]} "
                   f"reuse={r['reuse_pct']:.0%} | {q['question'][:50]}")

    return results


def print_summary(results: list[dict], name: str):
    n = len(results)
    if n == 0:
        return
    bl = sum(r["bl_correct"] for r in results) / n
    ca = sum(r["ca_correct"] for r in results) / n
    agree = sum(r["match"] for r in results) / n
    reuse = np.mean([r["reuse"] for r in results])

    print(f"\n  {'='*60}")
    print(f"  {name}: {n} questions")
    print(f"  Baseline: {bl:.1%}  Cached: {ca:.1%}  Δ: {ca-bl:+.1%}  Agree: {agree:.1%}  Reuse: {reuse:.1%}")

    splits = set(r.get("split", "?") for r in results)
    if len(splits) > 1:
        for s in sorted(splits):
            sr = [r for r in results if r.get("split") == s]
            s_bl = sum(r["bl_correct"] for r in sr) / len(sr)
            s_ca = sum(r["ca_correct"] for r in sr) / len(sr)
            print(f"    {s:<25} BL={s_bl:.0%} CA={s_ca:.0%} Δ={s_ca-s_bl:+.0%} (n={len(sr)})")

    if abs(ca - bl) <= 0.05:
        print(f"  VERDICT: PASS ✓ (Δ ≤ 5%)")
    elif ca >= bl:
        print(f"  VERDICT: PASS ✓ (cached ≥ baseline)")
    else:
        print(f"  VERDICT: {'MARGINAL' if abs(ca-bl) <= 0.1 else 'FAIL'} (Δ = {ca-bl:+.1%})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", default="tomato", choices=["tomato", "mvbench", "both"])
    parser.add_argument("--split", default="ALL")
    parser.add_argument("--n", type=int, default=15)
    parser.add_argument("--frames", type=int, default=8)
    parser.add_argument("--model", default="Qwen/Qwen2.5-VL-7B-Instruct")
    args = parser.parse_args()

    print("=" * 60)
    print(f"  Codec-Through Benchmark: {args.model}")
    print(f"  Backend: MLX (Apple Silicon unified memory)")
    print(f"  Frames: {args.frames}, N per split: {args.n}")
    print("=" * 60)

    vlm = CachedVLM(args.model)

    if args.benchmark in ("tomato", "both"):
        results = run_tomato(vlm, args.split, args.n, args.frames)
        print_summary(results, "TOMATO (7B)")
        with open(f"tomato_7b_{args.split}_{args.n}.json", "w") as f:
            json.dump(results, f, indent=2)

    if args.benchmark in ("mvbench", "both"):
        results = run_mvbench(vlm, args.n, args.frames)
        print_summary(results, "MVBench (7B)")
        with open(f"mvbench_7b_{args.n}.json", "w") as f:
            json.dump(results, f, indent=2)


MVBENCH_TASKS = [
    'action_sequence', 'moving_count', 'action_prediction', 'episodic_reasoning',
    'action_antonym', 'action_count', 'scene_transition', 'object_shuffle',
    'object_existence', 'fine_grained_pose', 'unexpected_action', 'moving_direction',
    'state_change', 'object_interaction', 'character_order', 'action_localization',
    'counterfactual_inference', 'fine_grained_action', 'moving_attribute', 'egocentric_navigation',
]

MVBENCH_SEARCH_DIRS = [
    MVBENCH_VIDEO_DIR / "clevrer" / "video_validation",
    MVBENCH_VIDEO_DIR / "ssv2_video",
    MVBENCH_VIDEO_DIR / "Moments_in_Time_Raw" / "validation",
    MVBENCH_VIDEO_DIR / "scene_qa" / "video",
    MVBENCH_VIDEO_DIR / "star",
    MVBENCH_VIDEO_DIR / "sta" / "sta_video",
    MVBENCH_VIDEO_DIR / "FunQA_test" / "test",
    MVBENCH_VIDEO_DIR / "data0613",
    MVBENCH_VIDEO_DIR / "vlnqa",
    MVBENCH_VIDEO_DIR,
]


def find_mvbench_video(video_name: str) -> str | None:
    for d in MVBENCH_SEARCH_DIRS:
        for ext in ['', '.mp4', '.avi', '.webm', '.mkv']:
            candidate = d / (Path(video_name).stem + ext) if ext else d / video_name
            if candidate.exists():
                return str(candidate)
    for p in MVBENCH_VIDEO_DIR.rglob(video_name):
        return str(p)
    return None


def run_mvbench(vlm: CachedVLM, n_per_task: int, n_frames: int):
    from datasets import load_dataset

    all_results = []
    for task in MVBENCH_TASKS:
        print(f"\n  ── {task} ──")
        ds = load_dataset('OpenGVLab/MVBench', task, split='train', streaming=True)
        skipped = 0

        for i, ex in enumerate(ds):
            if i >= n_per_task + skipped:
                break

            vpath = find_mvbench_video(ex['video'])
            if not vpath:
                skipped += 1
                continue

            candidates = ex['candidates']
            answer = ex['answer']
            gt_idx = candidates.index(answer) if answer in candidates else 0
            options_str = "\n".join(f"{chr(65+j)}. {c}" for j, c in enumerate(candidates))
            prompt = f"Question: {ex['question']}\nOptions:\n{options_str}\nAnswer with just the letter."

            start = ex.get('start', 0) or 0
            end = ex.get('end', 0) or 0
            frames = extract_frames(vpath, n_frames, start=start, end=end)
            if len(frames) < 2:
                skipped += 1
                continue

            r = vlm.run_comparison(frames, prompt)
            bl_idx = extract_choice(r["baseline"], candidates)
            ca_idx = extract_choice(r["cached"], candidates)

            all_results.append({
                "split": task, "gt": gt_idx,
                "bl_correct": bl_idx == gt_idx, "ca_correct": ca_idx == gt_idx,
                "match": bl_idx == ca_idx, "reuse": r["reuse_pct"],
            })

            mark = "✓" if bl_idx == ca_idx else "✗"
            tqdm.write(f"    [{mark}] GT={chr(65+gt_idx)} BL={chr(65+bl_idx)} CA={chr(65+ca_idx)} "
                       f"reuse={r['reuse_pct']:.0%} | {ex['question'][:50]}")

        task_r = [r for r in all_results if r["split"] == task]
        if task_r:
            bl = sum(r["bl_correct"] for r in task_r) / len(task_r)
            ca = sum(r["ca_correct"] for r in task_r) / len(task_r)
            print(f"    → BL={bl:.0%} CA={ca:.0%} Δ={ca-bl:+.0%} (n={len(task_r)})")

    return all_results


if __name__ == "__main__":
    main()
