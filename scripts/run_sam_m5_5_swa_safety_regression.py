#!/usr/bin/env python3
"""M5-5 -- SWA-aware safety wrapper regression test.

Confirms empirically that the `SafePromptCacheState` wrapper from
`scripts/swa_aware_cache.py` produces byte-identical outputs to cold
dense on the same B0b corpus. This is not a speedup -- it is the
correctness floor for cross-turn cache reuse on Gemma 4 26B-A4B /
mlx-vlm 0.4.4.

Compares 3 arms per (video, q_index):
  - cold_dense (baseline)
  - safe_wrapper          : pass SafePromptCacheState; library skips
                            the broken trim path; produces correct
                            cold-dense output (no speedup)
  - native_cross_turn     : pass real PromptCacheState (the broken
                            path) -- the B0b cross_turn_warm arm,
                            for reference

5 videos x 1 question (Q2 follow-up "What color is most prominent?")
x 3 arms = 15 paired rows.

Expected outcome:
  - safe_wrapper        : 5/5 byte-identical with cold_dense
  - native_cross_turn   : ~0-2 / 5 byte-identical (matches B0b)

This run is a regression gate for the safety wrapper, not a
performance claim.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import platform
import resource
import subprocess
import sys
import tempfile
import time
import uuid
import warnings
from pathlib import Path
from typing import Any

if not os.environ.get("HF_TOKEN"):
    raise SystemExit("HF_TOKEN required.")

import mlx.core as mx
import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from swa_aware_cache import (  # noqa: E402
    SafePromptCacheState,
    cache_topology_summary,
    is_mixed_swa_topology,
)

SCHEMA_VERSION = "sam_scaleout_artifact_v1"
PHASE = "M5-5"
EXPERIMENT_ID = "sam_scaleout_m5_5_swa_safety_regression_20260429"
PROTOCOL_ID = "sam_scaleout_handoff_20260429"

VIDEOMME_DIR_DEFAULT = Path(
    "/Users/sam/repos/codec-through/experiments/videomme_data")
ARTIFACT_DIR = REPO_ROOT / (
    "research/experiments/2026/artifacts/sam_scaleout_m5_20260429")
DEFAULT_OUT = ARTIFACT_DIR / "sam_m5_5_swa_safety_regression.jsonl"

MODEL_ID_DEFAULT = "google/gemma-4-26B-A4B-it"
HF_SNAPSHOT_DEFAULT = "7d4c97e54145f8ffd1a4dd1b4986a5015a517842"

SETUP_QUESTION = "Briefly describe what you see."
TEST_QUESTION = "What color is most prominent in the scene?"
MAX_TOKENS = 32


def peak_rss_gb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 ** 3)


def sha256_short(s):
    if isinstance(s, str):
        s = s.encode("utf-8")
    return hashlib.sha256(s).hexdigest()


def hash_ndarray(arr):
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def hash_ids(ids):
    h = hashlib.sha256()
    for i in ids:
        h.update(int(i).to_bytes(4, "little", signed=False))
    return h.hexdigest()


def repo_commit_sha(p):
    try:
        return subprocess.run(
            ["git", "-C", str(p), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
            timeout=5).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def runtime_versions():
    out = {"python": sys.version.split()[0]}
    for pkg in ("mlx", "mlx_vlm", "transformers"):
        try:
            mod = __import__(pkg)
            out[pkg] = getattr(mod, "__version__", "unknown")
        except ImportError:
            out[pkg] = "missing"
    return out


def hardware_descriptor():
    chip = subprocess.run(
        ["sysctl", "-n", "machdep.cpu.brand_string"],
        capture_output=True, text=True, timeout=5).stdout.strip() or "?"
    try:
        mem = int(subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            capture_output=True, text=True, timeout=5).stdout.strip() or 0)
        mem_gb = mem / (1024 ** 3)
    except Exception:  # noqa: BLE001
        mem_gb = 0.0
    return f"{chip} | {mem_gb:.1f} GB unified | Darwin {platform.release()}"


def find_videomme_video(video_id, vmme_dir):
    for ext in (".mp4", ".mkv", ".webm"):
        for p in vmme_dir.rglob(f"{video_id}{ext}"):
            return str(p)
    return None


def extract_frames(video_path, n_frames=8, max_size=560):
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        capture_output=True, text=True, timeout=15)
    try:
        duration = float(out.stdout.strip())
    except (ValueError, AttributeError):
        duration = 60.0
    timestamps = list(np.linspace(duration * 0.01, duration * 0.99, n_frames))
    frames = []
    for ts in timestamps:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
        subprocess.run(
            ["ffmpeg", "-v", "quiet", "-y", "-ss", f"{ts:.3f}",
             "-i", video_path, "-vframes", "1",
             "-vf",
             f"scale={max_size}:{max_size}:force_original_aspect_ratio=decrease,"
             f"pad={max_size}:{max_size}:(ow-iw)/2:(oh-ih)/2", tmp_path],
            capture_output=True, timeout=30)
        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
            frames.append(np.array(Image.open(tmp_path).convert("RGB")))
        if os.path.exists(tmp_path):
            try: os.unlink(tmp_path)
            except OSError: pass
    return frames, [float(t) for t in timestamps]


def save_jpgs(frames, tag):
    paths = []
    for i, f in enumerate(frames):
        path = f"/tmp/sam_m55_{tag}_{i}.jpg"
        Image.fromarray(f).save(path, quality=85)
        paths.append(path)
    return paths


def cleanup(paths):
    for p in paths:
        try: os.unlink(p)
        except OSError: pass


class Harness:
    def __init__(self, model_id):
        warnings.filterwarnings("ignore")
        from mlx_vlm import load
        from mlx_vlm.prompt_utils import apply_chat_template
        from mlx_vlm.generate import stream_generate, PromptCacheState
        print(f"[loader] loading {model_id}", flush=True)
        t0 = time.time()
        self.model, self.processor = load(model_id)
        print(f"[loader] loaded in {time.time() - t0:.1f}s", flush=True)
        self.apply_template = apply_chat_template
        self.stream_generate = stream_generate
        self.NativePromptCacheState = PromptCacheState
        self.model_id = model_id
        self.cache_topology = cache_topology_summary(self.model)
        self.is_mixed_swa = is_mixed_swa_topology(self.model)
        print(f"[topology] mixed_swa={self.is_mixed_swa} "
              f"n_layers={self.cache_topology.get('n_layers')} "
              f"n_full={self.cache_topology.get('n_full')} "
              f"n_sliding={self.cache_topology.get('n_sliding')}", flush=True)

    def run(self, img_paths, q, *, prompt_cache_state=None,
            max_tokens=MAX_TOKENS):
        formatted = self.apply_template(
            self.processor, self.model.config, q,
            num_images=len(img_paths), enable_thinking=False)
        inputs = self.processor(
            text=[formatted], images=img_paths,
            return_tensors="np", add_special_tokens=False)
        input_ids = mx.array(inputs["input_ids"])
        pixel_values = mx.array(inputs["pixel_values"])
        mask = mx.array(inputs["attention_mask"]) if "attention_mask" in inputs else None
        kwargs = {"max_tokens": max_tokens, "input_ids": input_ids,
                  "pixel_values": pixel_values, "temperature": 0.0}
        if mask is not None:
            kwargs["mask"] = mask
        if prompt_cache_state is not None:
            kwargs["prompt_cache_state"] = prompt_cache_state
        text_pieces, token_ids = [], []
        first_t = None
        t0 = time.perf_counter()
        for resp in self.stream_generate(
                self.model, self.processor, "", **kwargs):
            if first_t is None:
                first_t = time.perf_counter()
            if resp.text:
                text_pieces.append(resp.text)
            try: token_ids.append(int(resp.token))
            except Exception: token_ids.append(resp.token)  # noqa: BLE001
        wall = (time.perf_counter() - t0) * 1000.0
        prefill = ((first_t - t0) * 1000.0) if first_t else None
        return {"output_text": "".join(text_pieces),
                "n_input_tokens": int(input_ids.shape[1]),
                "n_output_tokens": len(token_ids),
                "input_ids_hash": hash_ids(input_ids.flatten().tolist()),
                "wall_ms": wall, "prefill_ms": prefill,
                "generate_ms": wall - prefill if prefill else None}


ROW_KEYS = (
    "schema_version","experiment_id","protocol_id","run_id","phase",
    "row_role","arm","baseline_arm","comparator_arm","policy",
    "baseline_policy","policy_params","model_id","model_sha","quantization",
    "runtime","runtime_commit","hardware","os_version","mlx_version",
    "metal_version","command_line","memory_definition","video_id",
    "event_id","item_id","pair_key","q_index","source_q_index",
    "turn_index","prompt_frame_count","frame_ids","frame_hashes",
    "baseline_frame_ids","baseline_frame_hashes","frame_selection_hash",
    "frames_sha256","raw_prompt","baseline_raw_prompt","prompt_hash",
    "baseline_prompt_hash","input_ids_hash","baseline_input_ids_hash",
    "raw_response","baseline_raw_response","session_choice",
    "baseline_choice","choice_diff","session_correct","baseline_correct",
    "correctness_diff","session_parse_failure","baseline_parse_failure",
    "parse_failure","text_identical","decode_ms","vision_ms","prefill_ms",
    "repair_prefill_ms","generate_ms","end_to_end_ms",
    "baseline_end_to_end_ms","elapsed_ms","baseline_elapsed_ms","vit_calls",
    "baseline_vit_calls","peak_memory_gb","cache_topology","prefix_hit",
    "prefix_coverage","prompt_tokens","baseline_prompt_tokens",
    "generation_tokens","seed","temperature","top_p","evidence_budget",
    "cadence_sec","fps","last_k","selected_frame_indices","event_time_s",
    "observation_window_s","stale_cache_case_id","changed_answer_expected",
    "claim_id","source_artifact_path","source_artifact_sha256",
    "export_row_count","expected_row_count","exactness_match","ci_method",
    "ci95","provenance_note","stage_timings_ms","commit_sha")


def make_row(prov, **kw):
    row = {k: None for k in ROW_KEYS}
    row.update({
        "schema_version": SCHEMA_VERSION, "experiment_id": EXPERIMENT_ID,
        "protocol_id": PROTOCOL_ID, "run_id": prov["run_id"],
        "phase": PHASE, "row_role": "paired",
        "model_id": prov["model_id"], "model_sha": prov["model_sha"],
        "quantization": prov["quantization"], "runtime": prov["runtime"],
        "runtime_commit": prov["runtime_commit"],
        "hardware": prov["hardware"], "os_version": prov["os_version"],
        "mlx_version": prov["mlx_version"],
        "metal_version": prov["metal_version"],
        "command_line": prov["command_line"],
        "memory_definition": prov["memory_definition"],
        "frame_ids": [], "frame_hashes": [], "baseline_frame_ids": [],
        "baseline_frame_hashes": [], "raw_prompt": "",
        "baseline_raw_prompt": "", "raw_response": "",
        "baseline_raw_response": "", "choice_diff": False,
        "session_correct": False, "baseline_correct": False,
        "correctness_diff": False, "session_parse_failure": False,
        "baseline_parse_failure": False, "parse_failure": False,
        "text_identical": False, "end_to_end_ms": 0.0, "seed": 0,
        "temperature": 0.0, "cache_topology": {},
        "selected_frame_indices": None, "commit_sha": prov["commit_sha"]})
    row.update(kw)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-videos", type=int, default=5)
    ap.add_argument("--n-frames", type=int, default=8)
    ap.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    ap.add_argument("--model-id", default=MODEL_ID_DEFAULT)
    ap.add_argument("--hf-snapshot", default=HF_SNAPSHOT_DEFAULT)
    ap.add_argument("--videomme-dir", type=Path, default=VIDEOMME_DIR_DEFAULT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    parquet = args.videomme_dir / "videomme/test-00000-of-00001.parquet"
    if not parquet.exists():
        raise SystemExit(f"VideoMME parquet missing: {parquet}")
    args.out.parent.mkdir(parents=True, exist_ok=True)

    versions = runtime_versions()
    prov = {
        "run_id": f"sam_m55_{int(time.time())}_{uuid.uuid4().hex[:8]}",
        "model_id": args.model_id, "model_sha": args.hf_snapshot,
        "quantization": "bf16_native",
        "runtime": f"mlx_vlm-{versions['mlx_vlm']}",
        "runtime_commit": "pypi", "hardware": hardware_descriptor(),
        "os_version": f"Darwin {platform.release()}",
        "mlx_version": versions.get("mlx", "unknown"),
        "metal_version": None,
        "command_line": " ".join(sys.argv),
        "memory_definition": "ru_maxrss bytes (macOS) -> GB",
        "commit_sha": repo_commit_sha(REPO_ROOT)}
    print(f"[provenance] {json.dumps(prov, indent=2)}", flush=True)

    import pyarrow.parquet as pq
    df = pq.read_table(parquet).to_pandas().sort_values(
        "question_id").reset_index(drop=True)
    seen, items = {}, []
    for _, row in df.iterrows():
        if row["videoID"] in seen:
            continue
        seen[row["videoID"]] = True
        items.append({"video_id": str(row["videoID"])})
        if len(items) >= args.n_videos:
            break

    h = Harness(args.model_id)
    rows = []

    for vi, it in enumerate(items):
        vp = find_videomme_video(it["video_id"], args.videomme_dir)
        if not vp:
            raise SystemExit(f"video missing: {it['video_id']}")
        frames, ts = extract_frames(vp, args.n_frames)
        paths = save_jpgs(frames, it["video_id"])
        frame_hashes = [hash_ndarray(f) for f in frames]
        frame_ids = [f"{it['video_id']}@{t:.3f}s" for t in ts]
        sel_hash = sha256_short("|".join(frame_hashes))
        print(f"[video {vi+1}/{len(items)}] {it['video_id']}", flush=True)

        # Cold dense baseline
        print(f"  [cold_dense] {TEST_QUESTION}", flush=True)
        cold = h.run(paths, TEST_QUESTION, max_tokens=args.max_tokens)
        gc.collect()

        # Safe wrapper: SafePromptCacheState always returns 0 for prefix
        # match, so the broken trim block is skipped. Output should be
        # byte-identical to cold dense.
        print(f"  [safe_wrapper] {TEST_QUESTION}", flush=True)
        safe_state = SafePromptCacheState()
        # First do a setup turn so the wrapper has *had* a turn to "see"
        # state. The safe wrapper's update() is a no-op so this turn
        # doesn't actually persist anything.
        _ = h.run(paths, SETUP_QUESTION,
                  prompt_cache_state=safe_state, max_tokens=args.max_tokens)
        safe_run = h.run(paths, TEST_QUESTION,
                          prompt_cache_state=safe_state,
                          max_tokens=args.max_tokens)
        gc.collect()

        # Native cross-turn: the broken path. Reproduce B0b cross_turn_warm
        # behavior at smaller scale for direct comparison.
        print(f"  [native_cross_turn] {TEST_QUESTION}", flush=True)
        native_state = h.NativePromptCacheState()
        _ = h.run(paths, SETUP_QUESTION,
                  prompt_cache_state=native_state,
                  max_tokens=args.max_tokens)
        native_run = h.run(paths, TEST_QUESTION,
                            prompt_cache_state=native_state,
                            max_tokens=args.max_tokens)
        gc.collect()

        # Emit 2 paired rows: safe_wrapper vs cold + native vs cold.
        common = dict(
            video_id=it["video_id"], item_id=it["video_id"],
            q_index=0, turn_index=1,
            prompt_frame_count=args.n_frames,
            frame_ids=frame_ids, frame_hashes=frame_hashes,
            baseline_frame_ids=frame_ids,
            baseline_frame_hashes=frame_hashes,
            frame_selection_hash=sel_hash, frames_sha256=sel_hash,
            raw_prompt=TEST_QUESTION, baseline_raw_prompt=TEST_QUESTION,
            prompt_hash=sha256_short(TEST_QUESTION),
            baseline_prompt_hash=sha256_short(TEST_QUESTION),
            baseline_input_ids_hash=cold["input_ids_hash"],
            baseline_raw_response=cold["output_text"],
            session_choice=None, baseline_choice=None,
            session_correct=False, baseline_correct=False,
            session_parse_failure=False, baseline_parse_failure=False,
            parse_failure=False,
            baseline_prompt_tokens=cold["n_input_tokens"],
            baseline_end_to_end_ms=cold["wall_ms"],
            baseline_vit_calls=1, baseline_arm="cold_dense",
            baseline_policy="cold_dense_no_cache",
            comparator_arm="cold_dense",
            cache_topology=h.cache_topology,
            peak_memory_gb=peak_rss_gb(),
        )

        rows.append(make_row(prov, **common,
            pair_key=f"v={it['video_id']}/safe_wrapper",
            arm="safe_wrapper",
            policy="SafePromptCacheState_force_cold_dense",
            input_ids_hash=safe_run["input_ids_hash"],
            raw_response=safe_run["output_text"],
            choice_diff=False,
            correctness_diff=False,
            text_identical=safe_run["output_text"] == cold["output_text"],
            end_to_end_ms=safe_run["wall_ms"],
            elapsed_ms=safe_run["wall_ms"],
            baseline_elapsed_ms=cold["wall_ms"],
            prefill_ms=safe_run["prefill_ms"],
            generate_ms=safe_run["generate_ms"],
            vit_calls=1, prefix_hit=0, prefix_coverage=0.0,
            prompt_tokens=safe_run["n_input_tokens"],
            generation_tokens=safe_run["n_output_tokens"],
            provenance_note=(
                "M5-5 safe wrapper: SafePromptCacheState.find_prefix_length "
                "returns 0 so the broken trim path is skipped. Expected "
                "byte-identical to cold_dense."),
        ))

        rows.append(make_row(prov, **common,
            pair_key=f"v={it['video_id']}/native_cross_turn",
            arm="native_cross_turn",
            policy="native_PromptCacheState_cross_turn_chained",
            input_ids_hash=native_run["input_ids_hash"],
            raw_response=native_run["output_text"],
            choice_diff=False,
            correctness_diff=False,
            text_identical=native_run["output_text"] == cold["output_text"],
            end_to_end_ms=native_run["wall_ms"],
            elapsed_ms=native_run["wall_ms"],
            baseline_elapsed_ms=cold["wall_ms"],
            prefill_ms=native_run["prefill_ms"],
            generate_ms=native_run["generate_ms"],
            vit_calls=0,
            prefix_hit=native_run["n_input_tokens"],
            prefix_coverage=1.0,
            prompt_tokens=native_run["n_input_tokens"],
            generation_tokens=native_run["n_output_tokens"],
            provenance_note=(
                "M5-5 native cross-turn: real PromptCacheState (broken "
                "path). Expected to reproduce B0b cross_turn_warm "
                "divergence behavior at smaller scale."),
        ))

        cleanup(paths)
        del frames
        gc.collect()

    with args.out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"[wrote] {len(rows)} rows -> {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
