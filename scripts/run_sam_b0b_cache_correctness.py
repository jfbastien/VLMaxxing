#!/usr/bin/env python3
"""B0b — Sam scale-out cache-correctness gate (Gemma 4 26B-A4B / mlx-vlm).

Phase contract: research/experiments/2026/2026-04-29-sam-scaleout-handoff.md
Schema:        research/schemas/sam_scaleout_artifact_v1.schema.json
Operator:      research/experiments/2026/2026-04-29-sam-scaleout-operator-prompt.md

Protocol:
  - 7 videos x 3 evaluation questions = 21 paired pair_keys
  - For each (video, q_index) pair, run three arms:
      * cold_dense              (baseline_arm; full prefill+generate, no cache)
      * within_turn_cache_replay (build PromptCacheState during prefill, then
                                  generate; same turn -- the path that PASSED
                                  in S0 10/10)
      * cross_turn_warm         (build cache from prior Q0+answer turn, ask
                                 the next Q reusing the cache -- the path that
                                 FAILED in S0 3/5)
  - Emit one paired row per (video, q_index, arm) where arm in
    {within_turn_cache_replay, cross_turn_warm} and baseline_arm = cold_dense.
    -> 21 within-turn rows + 21 cross-turn rows = 42 rows total.

Greedy decoding (temp=0). Same frames, identical prompts, identical
input_ids_hash between paired arms.

Runs in ~10-30 min on M5 Max / 128 GB / Gemma 4 26B-A4B.

Note: Gemma 4 26B-A4B has 25 sliding-window layers + 5 full-attention
layers. mlx-vlm 0.4.4's prompt-cache trim path doesn't honor SWA semantics
(see S0 findings). We expect cross_turn_warm to fail this gate.
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
    raise SystemExit(
        "HF_TOKEN environment variable is required (gated Gemma 4 weights). "
        "Aborting per B0b spec -- do not attempt to download."
    )

import contextlib

# --- BEGIN B0b r2 correctness-control guard ---
# Background: mlx_vlm/generate.py:671-697 (mlx-vlm 0.4.4) flat-slices
# c.keys[:, :, :prefix_len, :] for every prompt-cache entry. That is
# correct for KVCache (Qwen, full-attention everywhere) but corrupts
# RotatingKVCache (Gemma 4 SWA layers -- slot 0 of a rotated buffer is
# not the oldest temporal token). Combined with the input_ids trim on
# the same path, partial-cache reuse on Gemma 4 26B-A4B is unsafe.
#
# Until a topology-aware vendor patch lands, this guard refuses to
# reuse the cache cross-turn whenever any RotatingKVCache is present.
# The result: B0b's correctness gate can pass; the C-PERSIST speedup
# claim on Gemma 26B remains BLOCKED until the upstream fix.
import importlib  # noqa: E402

import mlx.core as mx
import numpy as np  # noqa: E402
from mlx_lm.models.cache import RotatingKVCache  # noqa: E402
from PIL import Image

# Note: `mlx_vlm.generate` is shadowed by the top-level `generate`
# function exported in mlx_vlm/__init__.py, so `import mlx_vlm.generate`
# returns the function, not the module. Use importlib to fetch the
# actual submodule.
_gen = importlib.import_module("mlx_vlm.generate")
_orig_stream_generate = _gen.stream_generate

# Sticky module-level flag. The runner reads this AFTER every
# stream_generate call to decide whether to emit "cache-reuse" or
# "guarded full-refill" metadata for that row. Reset by the runner
# before the next call.
B0B_GUARD_TRIGGERED = False


def _correctness_guard_stream_generate(*args, **kwargs):
    global B0B_GUARD_TRIGGERED
    B0B_GUARD_TRIGGERED = False
    cache_state = kwargs.get("prompt_cache_state")
    if (
        cache_state is not None
        and getattr(cache_state, "cache", None)
        and any(isinstance(c, RotatingKVCache) for c in cache_state.cache)
    ):
        # Refuse cross-turn cache reuse on mixed-topology models.
        # Force full re-prefill. mlx-vlm sees no cache, takes the
        # cold path, and produces a correctness-clean output.
        kwargs["prompt_cache_state"] = None
        B0B_GUARD_TRIGGERED = True
    return _orig_stream_generate(*args, **kwargs)


_gen.stream_generate = _correctness_guard_stream_generate
# --- END B0b r2 correctness-control guard ---

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "sam_scaleout_artifact_v1"
PHASE = "B0b"
EXPERIMENT_ID = "sam_scaleout_b0b_cache_correctness_20260429"
PROTOCOL_ID = "sam_scaleout_handoff_20260429"

# Default external VideoMME data location (sdamico repo). The 26B/M5 stack
# inherits this dataset; the JF mirror does not duplicate it.
VIDEOMME_DIR_DEFAULT = Path("/Users/sam/repos/codec-through/experiments/videomme_data")
ARTIFACT_DIR = REPO_ROOT / "research/experiments/2026/artifacts/sam_scaleout_m5_20260429"
DEFAULT_OUT = ARTIFACT_DIR / "sam_b0b_cache_correctness.jsonl"

MODEL_ID_DEFAULT = "google/gemma-4-26B-A4B-it"
HF_SNAPSHOT_DEFAULT = "7d4c97e54145f8ffd1a4dd1b4986a5015a517842"

# B0b: 3 evaluation questions per video. We use the parquet's question as Q1
# plus two stable follow-ups so all 7 videos answer the same Q2/Q3 (gives a
# clean cross-turn cache-bug signal -- if cross_turn_warm leaks Q1 context
# into Q2/Q3, the same Q2/Q3 across all videos makes the leak conspicuous).
FOLLOWUPS = (
    "What color is most prominent in the scene?",
    "Are there any people visible? Answer YES or NO and one short phrase.",
)

# Q0 is the setup turn for cross_turn_warm -- we need *some* turn to build
# the conversational cache that subsequent Qs reuse.
SETUP_QUESTION = "Briefly describe what you see."

MAX_TOKENS = 32  # short -- we just need correctness comparison.


# ---------------------------------------------------------------------------
# Provenance + hashing helpers
# ---------------------------------------------------------------------------


def peak_rss_gb() -> float:
    # ru_maxrss on macOS is in BYTES (Linux = KB); we are macOS-only here.
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024**3)


def sha256_short(s: str | bytes) -> str:
    if isinstance(s, str):
        s = s.encode("utf-8")
    return hashlib.sha256(s).hexdigest()


def hash_ids(ids: list[int]) -> str:
    h = hashlib.sha256()
    for i in ids:
        h.update(int(i).to_bytes(4, "little", signed=False))
    return h.hexdigest()


def hash_ndarray(arr: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def repo_commit_sha(path: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        return out.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return "unknown"


def runtime_versions() -> dict[str, str]:
    out: dict[str, str] = {"python": sys.version.split()[0]}
    for pkg in ("mlx", "mlx_vlm", "transformers"):
        try:
            mod = __import__(pkg)
            out[pkg] = getattr(mod, "__version__", "unknown")
        except ImportError:
            out[pkg] = "missing"
    try:
        import mlx_lm

        out["mlx_lm"] = getattr(mlx_lm, "__version__", "unknown")
    except ImportError:
        out["mlx_lm"] = "missing"
    return out


def hardware_descriptor() -> str:
    try:
        chip = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True, timeout=5
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        chip = "unknown"
    try:
        mem_bytes = int(
            subprocess.run(
                ["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=5
            ).stdout.strip()
            or 0
        )
        mem_gb = mem_bytes / (1024**3)
    except Exception:  # noqa: BLE001
        mem_gb = 0.0
    return f"{chip} | {mem_gb:.1f} GB unified | Darwin {platform.release()}"


def metal_version() -> str | None:
    try:
        out = subprocess.run(
            ["system_profiler", "SPDisplaysDataType"], capture_output=True, text=True, timeout=10
        ).stdout
        for line in out.splitlines():
            if "Metal Support" in line:
                return line.split(":", 1)[1].strip()
    except Exception:  # noqa: BLE001
        pass
    return None


# ---------------------------------------------------------------------------
# Frame extraction (deterministic timestamps + per-frame hash)
# ---------------------------------------------------------------------------


def find_videomme_video(video_id: str, videomme_dir: Path) -> str | None:
    for ext in (".mp4", ".mkv", ".webm", ".avi"):
        for p in videomme_dir.rglob(f"{video_id}{ext}"):
            return str(p)
    return None


def extract_frames(
    video_path: str, n_frames: int = 8, max_size: int = 560
) -> tuple[list[np.ndarray], list[float]]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            video_path,
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )
    try:
        duration = float(result.stdout.strip())
    except (ValueError, AttributeError):
        duration = 60.0
    timestamps = list(np.linspace(duration * 0.01, duration * 0.99, n_frames))
    frames: list[np.ndarray] = []
    for ts in timestamps:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "quiet",
                "-y",
                "-ss",
                f"{float(ts):.3f}",
                "-i",
                video_path,
                "-vframes",
                "1",
                "-vf",
                f"scale={max_size}:{max_size}:force_original_aspect_ratio=decrease,"
                f"pad={max_size}:{max_size}:(ow-iw)/2:(oh-ih)/2",
                tmp_path,
            ],
            capture_output=True,
            timeout=30,
        )
        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
            frames.append(np.array(Image.open(tmp_path).convert("RGB")))
        if os.path.exists(tmp_path):
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
    return frames, [float(ts) for ts in timestamps]


def save_frame_jpgs(frames: list[np.ndarray], tag: str) -> list[str]:
    out_paths = []
    for i, f in enumerate(frames):
        path = f"/tmp/sam_b0b_{tag}_{i}.jpg"
        Image.fromarray(f).save(path, quality=85)
        out_paths.append(path)
    return out_paths


def cleanup_paths(paths: list[str]) -> None:
    for p in paths:
        with contextlib.suppress(OSError):
            os.unlink(p)


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


class Harness:
    def __init__(self, model_id: str) -> None:
        warnings.filterwarnings("ignore")
        from mlx_vlm import load
        from mlx_vlm.generate import PromptCacheState, stream_generate
        from mlx_vlm.prompt_utils import apply_chat_template

        print(f"[loader] loading {model_id} ...", flush=True)
        t0 = time.time()
        self.model, self.processor = load(model_id)
        print(f"[loader] loaded in {time.time() - t0:.1f}s", flush=True)
        self.apply_template = apply_chat_template
        self.stream_generate = stream_generate
        self.PromptCacheState = PromptCacheState
        self.model_id = model_id
        # Cache topology -- inspect for sliding-window layers.
        cfg = self.model.config
        text_cfg = getattr(cfg, "text_config", cfg)
        sliding = getattr(text_cfg, "sliding_window", None)
        layer_types = getattr(text_cfg, "layer_types", None)
        if layer_types is None:
            n_layers = getattr(text_cfg, "num_hidden_layers", 0)
            self.cache_topology = {
                "n_layers": n_layers,
                "sliding_window": sliding,
                "layer_types": "uniform",
            }
        else:
            self.cache_topology = {
                "n_layers": len(layer_types),
                "sliding_window": sliding,
                "layer_types": list(layer_types),
                "n_swa": sum(1 for t in layer_types if "sliding" in str(t)),
                "n_full": sum(1 for t in layer_types if "full" in str(t)),
            }

    def format_inputs(
        self, img_paths: list[str], question_text: str
    ) -> tuple[mx.array, mx.array, mx.array | None, str]:
        formatted = self.apply_template(
            self.processor,
            self.model.config,
            question_text,
            num_images=len(img_paths),
            enable_thinking=False,
        )
        inputs = self.processor(
            text=[formatted], images=img_paths, return_tensors="np", add_special_tokens=False
        )
        input_ids = mx.array(inputs["input_ids"])
        pixel_values = mx.array(inputs["pixel_values"])
        mask = mx.array(inputs["attention_mask"]) if "attention_mask" in inputs else None
        return input_ids, pixel_values, mask, formatted

    def run(
        self,
        img_paths: list[str],
        question_text: str,
        *,
        prompt_cache_state: Any = None,
        max_tokens: int = MAX_TOKENS,
    ) -> dict[str, Any]:
        input_ids, pixel_values, mask, formatted_prompt = self.format_inputs(
            img_paths, question_text
        )
        n_input = int(input_ids.shape[1])
        kwargs = {
            "max_tokens": max_tokens,
            "input_ids": input_ids,
            "pixel_values": pixel_values,
            "temperature": 0.0,
        }
        if mask is not None:
            kwargs["mask"] = mask
        if prompt_cache_state is not None:
            kwargs["prompt_cache_state"] = prompt_cache_state

        text_pieces: list[str] = []
        token_ids: list[int] = []
        first_token_id: int | None = None
        prefill_ms = None
        decode_pieces_ms = []
        t_start = time.perf_counter()
        t_first = None
        for resp in self.stream_generate(self.model, self.processor, "", **kwargs):
            if t_first is None:
                t_first = time.perf_counter()
                prefill_ms = (t_first - t_start) * 1000.0
            if resp.text:
                text_pieces.append(resp.text)
            tok = resp.token
            try:
                tok_int = int(tok)
            except Exception:  # noqa: BLE001
                tok_int = tok
            if first_token_id is None:
                first_token_id = tok_int
            token_ids.append(tok_int)
            decode_pieces_ms.append(time.perf_counter())
        wall = time.perf_counter() - t_start
        generate_ms = (
            (decode_pieces_ms[-1] - t_first) * 1000.0 if decode_pieces_ms and t_first else None
        )
        return {
            "output_text": "".join(text_pieces),
            "formatted_prompt": formatted_prompt,
            "token_ids": token_ids,
            "first_token_id": first_token_id,
            "n_input_tokens": n_input,
            "n_output_tokens": len(token_ids),
            "input_ids_hash": hash_ids(input_ids.flatten().tolist()),
            "wall_time_ms": wall * 1000.0,
            "prefill_ms": prefill_ms,
            "generate_ms": generate_ms,
            "peak_rss_gb": peak_rss_gb(),
        }


# ---------------------------------------------------------------------------
# B0b orchestration
# ---------------------------------------------------------------------------


def load_first_n_videomme(parquet_path: Path, n: int) -> list[dict[str, Any]]:
    import pyarrow.parquet as pq

    df = pq.read_table(parquet_path).to_pandas()
    df = df.sort_values("question_id").reset_index(drop=True)
    seen: dict[str, bool] = {}
    items: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        if row["videoID"] in seen:
            continue
        seen[row["videoID"]] = True
        items.append(
            {
                "video_id": str(row["videoID"]),
                "duration": str(row["duration"]),
                "q1_text": str(row["question"]),
                "options": list(row["options"]),
                "answer_letter": str(row["answer"]),
                "question_id": str(row["question_id"]),
            }
        )
        if len(items) >= n:
            break
    return items


def parse_letter(text: str, n_options: int = 4) -> str | None:
    t = text.strip().upper()
    if not t:
        return None
    for letter in [chr(ord("A") + i) for i in range(n_options)]:
        if t.startswith(letter):
            return letter
    return None


def parsed_correct(text: str, options: list[str], answer_letter: str) -> bool:
    parsed = parse_letter(text, len(options))
    return parsed == answer_letter.strip().upper()


def make_row(
    *,
    base_provenance: dict[str, Any],
    video_id: str,
    item_id: str,
    q_index: int,
    turn_index: int,
    pair_key: str,
    arm: str,
    baseline_arm: str,
    policy: str,
    baseline_policy: str,
    policy_params: dict[str, Any] | None = None,
    comparator_arm: str | None,
    frame_ids: list[str],
    frame_hashes: list[str],
    baseline_frame_ids: list[str],
    baseline_frame_hashes: list[str],
    frame_selection_hash: str,
    raw_prompt: str,
    baseline_raw_prompt: str,
    input_ids_hash: str,
    baseline_input_ids_hash: str,
    raw_response: str,
    baseline_raw_response: str,
    session_choice: str | None,
    baseline_choice: str | None,
    session_correct: bool,
    baseline_correct: bool,
    session_parse_failure: bool,
    baseline_parse_failure: bool,
    prompt_tokens: int,
    baseline_prompt_tokens: int,
    generation_tokens: int,
    prefill_ms: float | None,
    generate_ms: float | None,
    repair_prefill_ms: float | None,
    end_to_end_ms: float,
    baseline_end_to_end_ms: float | None,
    vit_calls: int | None,
    baseline_vit_calls: int | None,
    peak_memory_gb: float | None,
    cache_topology: dict[str, Any],
    prefix_hit: int | None,
    prefix_coverage: float | None,
    stage_timings_ms: dict[str, Any] | None,
    provenance_note: str | None,
) -> dict[str, Any]:
    """Construct a fully schema-compliant row."""
    derived_choice_diff = session_choice != baseline_choice
    derived_correctness_diff = bool(session_correct) != bool(baseline_correct)
    derived_text_identical = raw_response == baseline_raw_response
    derived_parse_failure = bool(session_parse_failure) or bool(baseline_parse_failure)
    row = {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "protocol_id": PROTOCOL_ID,
        "run_id": base_provenance["run_id"],
        "phase": PHASE,
        "row_role": "paired",
        "arm": arm,
        "baseline_arm": baseline_arm,
        "comparator_arm": comparator_arm,
        "policy": policy,
        "baseline_policy": baseline_policy,
        "policy_params": policy_params,
        "model_id": base_provenance["model_id"],
        "model_sha": base_provenance["model_sha"],
        "quantization": base_provenance["quantization"],
        "runtime": base_provenance["runtime"],
        "runtime_commit": base_provenance["runtime_commit"],
        "hardware": base_provenance["hardware"],
        "os_version": base_provenance["os_version"],
        "mlx_version": base_provenance["mlx_version"],
        "metal_version": base_provenance["metal_version"],
        "command_line": base_provenance["command_line"],
        "memory_definition": base_provenance["memory_definition"],
        "video_id": video_id,
        "event_id": None,
        "item_id": item_id,
        "pair_key": pair_key,
        "q_index": q_index,
        "source_q_index": None,
        "turn_index": turn_index,
        "prompt_frame_count": len(frame_ids),
        "frame_ids": frame_ids,
        "frame_hashes": frame_hashes,
        "baseline_frame_ids": baseline_frame_ids,
        "baseline_frame_hashes": baseline_frame_hashes,
        "frame_selection_hash": frame_selection_hash,
        "frames_sha256": frame_selection_hash,
        "raw_prompt": raw_prompt,
        "baseline_raw_prompt": baseline_raw_prompt,
        "prompt_hash": sha256_short(raw_prompt),
        "baseline_prompt_hash": sha256_short(baseline_raw_prompt),
        "input_ids_hash": input_ids_hash,
        "baseline_input_ids_hash": baseline_input_ids_hash,
        "raw_response": raw_response,
        "baseline_raw_response": baseline_raw_response,
        "session_choice": session_choice,
        "baseline_choice": baseline_choice,
        "choice_diff": derived_choice_diff,
        "session_correct": bool(session_correct),
        "baseline_correct": bool(baseline_correct),
        "correctness_diff": derived_correctness_diff,
        "session_parse_failure": bool(session_parse_failure),
        "baseline_parse_failure": bool(baseline_parse_failure),
        "parse_failure": derived_parse_failure,
        "text_identical": derived_text_identical,
        "decode_ms": None,
        "vision_ms": None,
        "prefill_ms": prefill_ms,
        "repair_prefill_ms": repair_prefill_ms,
        "generate_ms": generate_ms,
        "end_to_end_ms": end_to_end_ms,
        "baseline_end_to_end_ms": baseline_end_to_end_ms,
        "elapsed_ms": end_to_end_ms,
        "baseline_elapsed_ms": baseline_end_to_end_ms,
        "vit_calls": vit_calls,
        "baseline_vit_calls": baseline_vit_calls,
        "peak_memory_gb": peak_memory_gb,
        "cache_topology": cache_topology,
        "prefix_hit": prefix_hit,
        "prefix_coverage": prefix_coverage,
        "prompt_tokens": prompt_tokens,
        "baseline_prompt_tokens": baseline_prompt_tokens,
        "generation_tokens": generation_tokens,
        "seed": 0,
        "temperature": 0.0,
        "top_p": None,
        "evidence_budget": None,
        "cadence_sec": None,
        "fps": None,
        "last_k": None,
        "selected_frame_indices": list(range(len(frame_ids))),
        "event_time_s": None,
        "observation_window_s": None,
        "stale_cache_case_id": None,
        "changed_answer_expected": None,
        "claim_id": None,
        "source_artifact_path": None,
        "source_artifact_sha256": None,
        "export_row_count": None,
        "expected_row_count": None,
        "exactness_match": None,
        "ci_method": None,
        "ci95": None,
        "provenance_note": provenance_note,
        "stage_timings_ms": stage_timings_ms,
        "commit_sha": base_provenance["commit_sha"],
    }
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-videos", type=int, default=7)
    ap.add_argument("--n-frames", type=int, default=8)
    ap.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    ap.add_argument("--model-id", default=MODEL_ID_DEFAULT)
    ap.add_argument("--hf-snapshot", default=HF_SNAPSHOT_DEFAULT)
    ap.add_argument("--videomme-dir", type=Path, default=VIDEOMME_DIR_DEFAULT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--smoke", action="store_true", help="1 video × 1 question for harness validation"
    )
    args = ap.parse_args()

    if args.smoke:
        args.n_videos = 1

    parquet = args.videomme_dir / "videomme/test-00000-of-00001.parquet"
    if not parquet.exists():
        raise SystemExit(f"VideoMME parquet missing: {parquet}")

    args.out.parent.mkdir(parents=True, exist_ok=True)

    # Provenance.
    versions = runtime_versions()
    base_provenance = {
        "run_id": f"sam_b0b_{int(time.time())}_{uuid.uuid4().hex[:8]}",
        "model_id": args.model_id,
        "model_sha": args.hf_snapshot,
        "quantization": "bf16_native",
        "runtime": f"mlx_vlm-{versions['mlx_vlm']}",
        "runtime_commit": "pypi",
        "hardware": hardware_descriptor(),
        "os_version": f"Darwin {platform.release()}",
        "mlx_version": versions.get("mlx", "unknown"),
        "metal_version": metal_version(),
        "command_line": " ".join(sys.argv),
        "memory_definition": "ru_maxrss bytes (macOS) -> GB",
        "commit_sha": repo_commit_sha(REPO_ROOT),
    }
    print(f"[provenance] {json.dumps(base_provenance, indent=2)}", flush=True)

    items = load_first_n_videomme(parquet, args.n_videos)
    if len(items) < args.n_videos:
        raise SystemExit(f"Only found {len(items)} unique videos; need {args.n_videos}")

    # Resolve videos and pre-extract frames.
    print(f"[setup] resolving {len(items)} videos + extracting frames", flush=True)
    for it in items:
        video_path = find_videomme_video(it["video_id"], args.videomme_dir)
        if not video_path:
            raise SystemExit(f"Video missing: {it['video_id']}")
        frames, timestamps = extract_frames(video_path, n_frames=args.n_frames)
        if len(frames) != args.n_frames:
            raise SystemExit(
                f"Expected {args.n_frames} frames for {it['video_id']}, got {len(frames)}"
            )
        it["video_path"] = video_path
        it["frames"] = frames
        it["timestamps"] = timestamps
        it["frame_paths"] = save_frame_jpgs(frames, it["video_id"])
        it["frame_hashes"] = [hash_ndarray(f) for f in frames]
        it["frame_ids"] = [f"{it['video_id']}@{ts:.3f}s" for ts in timestamps]
        it["frame_selection_hash"] = sha256_short("|".join(it["frame_hashes"]))

    # Load model once.
    h = Harness(args.model_id)

    # Build the question pool: Q1 = parquet question (with MC choices), Q2/Q3
    # are fixed follow-ups. Q1 stays MC; Q2/Q3 are open. Parse-failure logic
    # is per arm.
    if args.smoke:
        [items[0]["q1_text"]]
    else:
        # We use 3 questions per video. Q1 is MC; Q2/Q3 are the two FOLLOWUPS.
        pass  # constructed below per video

    rows: list[dict[str, Any]] = []

    for vi, it in enumerate(items):
        print(f"[video {vi + 1}/{len(items)}] {it['video_id']}", flush=True)
        # Build question list.
        q1_with_options = (
            f"{it['q1_text']}\n"
            + "\n".join(f"{chr(ord('A') + i)}. {o}" for i, o in enumerate(it["options"]))
            + "\nAnswer with a single letter (A/B/C/D)."
        )
        if args.smoke:
            qs: list[tuple[str, str]] = [
                ("q1_mc", q1_with_options),
            ]
        else:
            qs = [
                ("q1_mc", q1_with_options),
                ("q2_followup_color", FOLLOWUPS[0]),
                ("q3_followup_people", FOLLOWUPS[1]),
            ]

        # Run cold_dense baseline for each Q (no cache).
        cold_results: dict[str, dict[str, Any]] = {}
        for q_label, q_text in qs:
            print(f"  [cold_dense] {q_label}", flush=True)
            r = h.run(it["frame_paths"], q_text, max_tokens=args.max_tokens)
            cold_results[q_label] = r
            gc.collect()

        # Run within_turn_cache_replay for each Q. Build PromptCacheState
        # during prefill; generate from it. Each Q is independent (a fresh
        # cache built within that turn).
        within_results: dict[str, dict[str, Any]] = {}
        for q_label, q_text in qs:
            print(f"  [within_turn_cache_replay] {q_label}", flush=True)
            cache_state = h.PromptCacheState()
            r = h.run(
                it["frame_paths"],
                q_text,
                prompt_cache_state=cache_state,
                max_tokens=args.max_tokens,
            )
            within_results[q_label] = r
            del cache_state
            gc.collect()

        # Run cross_turn_warm. Build cache from Q0 setup turn, then run Q1,
        # Q2, Q3 with the persisted cache (each subsequent Q reusing the
        # cache from the previous turn).
        cross_results: dict[str, dict[str, Any]] = {}
        cross_cache = h.PromptCacheState()
        print("  [cross_turn_warm] q0_setup (cache primer)", flush=True)
        _setup = h.run(
            it["frame_paths"],
            SETUP_QUESTION,
            prompt_cache_state=cross_cache,
            max_tokens=args.max_tokens,
        )
        for ti, (q_label, q_text) in enumerate(qs):
            print(f"  [cross_turn_warm] {q_label} (turn {ti + 1})", flush=True)
            r = h.run(
                it["frame_paths"],
                q_text,
                prompt_cache_state=cross_cache,
                max_tokens=args.max_tokens,
            )
            cross_results[q_label] = r
            gc.collect()
        del cross_cache
        gc.collect()

        # Emit rows. For each question, pair within and cross arm rows
        # against the cold_dense baseline.
        for q_idx, (q_label, q_text) in enumerate(qs):
            cold = cold_results[q_label]
            within = within_results[q_label]
            cross = cross_results[q_label]

            n_options = len(it["options"]) if q_label == "q1_mc" else 4
            cold_choice = parse_letter(cold["output_text"], n_options)
            within_choice = parse_letter(within["output_text"], n_options)
            cross_choice = parse_letter(cross["output_text"], n_options)

            cold_correct = q_label == "q1_mc" and cold_choice == it["answer_letter"].strip().upper()
            within_correct = (
                q_label == "q1_mc" and within_choice == it["answer_letter"].strip().upper()
            )
            cross_correct = (
                q_label == "q1_mc" and cross_choice == it["answer_letter"].strip().upper()
            )

            # parse_failure is "did the arm produce a parseable choice when
            # the question expected a letter?". For non-MC follow-ups, parse
            # failure is False (text is the answer).
            cold_pf = q_label == "q1_mc" and cold_choice is None
            within_pf = q_label == "q1_mc" and within_choice is None
            cross_pf = q_label == "q1_mc" and cross_choice is None

            base_kw = dict(
                base_provenance=base_provenance,
                video_id=it["video_id"],
                item_id=it["video_id"],
                q_index=q_idx,
                turn_index=q_idx,
                frame_ids=it["frame_ids"],
                frame_hashes=it["frame_hashes"],
                baseline_frame_ids=it["frame_ids"],
                baseline_frame_hashes=it["frame_hashes"],
                frame_selection_hash=it["frame_selection_hash"],
                raw_prompt=q_text,
                baseline_raw_prompt=q_text,
                baseline_input_ids_hash=cold["input_ids_hash"],
                baseline_raw_response=cold["output_text"],
                baseline_choice=cold_choice,
                baseline_correct=cold_correct,
                baseline_parse_failure=cold_pf,
                baseline_prompt_tokens=cold["n_input_tokens"],
                baseline_end_to_end_ms=cold["wall_time_ms"],
                baseline_vit_calls=1,
                cache_topology=h.cache_topology,
                peak_memory_gb=peak_rss_gb(),
                stage_timings_ms=None,
                provenance_note=(
                    f"q_label={q_label}; cold_dense baseline run alongside "
                    f"within_turn_cache_replay and cross_turn_warm arms."
                ),
            )

            # Within-turn row.
            rows.append(
                make_row(
                    **base_kw,
                    pair_key=f"v={it['video_id']}/q={q_idx}/within",
                    arm="within_turn_cache_replay",
                    baseline_arm="cold_dense",
                    policy="prompt_cache_state_within_turn",
                    baseline_policy="cold_dense_no_cache",
                    comparator_arm="cold_dense",
                    input_ids_hash=within["input_ids_hash"],
                    raw_response=within["output_text"],
                    session_choice=within_choice,
                    session_correct=within_correct,
                    session_parse_failure=within_pf,
                    prompt_tokens=within["n_input_tokens"],
                    generation_tokens=within["n_output_tokens"],
                    prefill_ms=within["prefill_ms"],
                    generate_ms=within["generate_ms"],
                    repair_prefill_ms=None,
                    end_to_end_ms=within["wall_time_ms"],
                    vit_calls=1,
                    prefix_hit=0,
                    prefix_coverage=0.0,
                )
            )

            # Cross-turn row. Read the guard flag set by
            # _correctness_guard_stream_generate during the cross-turn
            # call -- if it fired, encode "guarded full re-prefill" via
            # policy / policy_params / vit_calls / prefix_hit /
            # prefix_coverage / provenance_note. Otherwise emit the
            # original cache-reuse metadata.
            guard_fired = bool(B0B_GUARD_TRIGGERED)
            cross_kw = {**base_kw}
            if guard_fired:
                cross_kw["provenance_note"] = (
                    "[B0b r2 guard fired: cross-turn cache reuse "
                    "disabled because RotatingKVCache present in prompt "
                    "cache; effective path is full re-prefill] "
                    + (base_kw.get("provenance_note") or "")
                )
            rows.append(
                make_row(
                    **cross_kw,
                    pair_key=f"v={it['video_id']}/q={q_idx}/cross",
                    arm="cross_turn_warm",
                    baseline_arm="cold_dense",
                    policy=(
                        "full_refill_guard_rotating_kv"
                        if guard_fired
                        else "prompt_cache_state_cross_turn_chained"
                    ),
                    policy_params=(
                        {
                            "cache_guard_triggered": True,
                            "guard_reason": "rotating_kv_present",
                            "cache_reuse_disabled": True,
                        }
                        if guard_fired
                        else None
                    ),
                    baseline_policy="cold_dense_no_cache",
                    comparator_arm="cold_dense",
                    input_ids_hash=cross["input_ids_hash"],
                    raw_response=cross["output_text"],
                    session_choice=cross_choice,
                    session_correct=cross_correct,
                    session_parse_failure=cross_pf,
                    prompt_tokens=cross["n_input_tokens"],
                    generation_tokens=cross["n_output_tokens"],
                    prefill_ms=cross["prefill_ms"],
                    generate_ms=cross["generate_ms"],
                    repair_prefill_ms=None,
                    end_to_end_ms=cross["wall_time_ms"],
                    vit_calls=1 if guard_fired else 0,
                    prefix_hit=0 if guard_fired else cross["n_input_tokens"],
                    prefix_coverage=0.0 if guard_fired else 1.0,
                )
            )

        # Frame jpgs are large; release after each video.
        cleanup_paths(it["frame_paths"])
        del it["frames"]
        del it["frame_paths"]
        gc.collect()

    # Write JSONL.
    with args.out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    print(f"[wrote] {len(rows)} rows -> {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
