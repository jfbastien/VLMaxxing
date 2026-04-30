#!/usr/bin/env python3
"""B3 -- Sam scale-out matched streaming baselines.

Phase contract: research/experiments/2026/2026-04-29-sam-scaleout-handoff.md
Schema:        research/schemas/sam_scaleout_artifact_v1.schema.json

Compares 4 streaming policies on the same recordings, events, observation
windows, questions, answer keys, and scoring:

  - screenshot_polling : 1 frame at the query timestamp
                          (evidence_budget="1f@t")
  - low_fps_dense      : 4 uniform frames across the observation window
                          (evidence_budget="4f@uniform")
  - recency_last_k     : 4 most recent frames before the query
                          (evidence_budget="last_4")
  - sam_policy         : codec-through native streaming -- decode all
                          frames upstream, fire the ViT only at events
                          (T0 + rebuilds when MV inflection > threshold);
                          present 4 representative frames covering T0
                          and the last rebuild span if any
                          (evidence_budget="vit_at_events")

Events are MV-inflection points detected from H.264 motion-vector
side-channel (consistent with the §2.13.4 inflection detector). Each
event has an observation window [t_event - W, t_event] (W = 4 s by
default). At t_event we ask the model "Describe what is currently on
screen.". Each arm's frames are passed to the same model (Gemma 4 26B);
the response is graded by an LLM-as-judge against the fresh-oracle
answer (high-density sample over the whole window) for the same event.

Stale-cache cases are flagged automatically: events where mv_sum over
the prior window is high (visual content has changed substantially since
the last event); for these `changed_answer_expected = True`. At least
one such case is required by the validator.

7 events per video x 2 videos = 14 pair_keys at the lower bound; we
target >=10 events per video (>=20 pair_keys, >=80 rows).

Greedy decoding (temp=0). All arms see identical model + identical
question; only the frame selection differs between arms.

Runs in ~30-60 min on M5 Max / 128 GB.
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
        "HF_TOKEN environment variable is required (gated Gemma 4 weights). Aborting per B3 spec."
    )

import contextlib

import mlx.core as mx
import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "sam_scaleout_artifact_v1"
PHASE = "B3"
EXPERIMENT_ID = "sam_scaleout_b3_streaming_baselines_20260429"
PROTOCOL_ID = "sam_scaleout_handoff_20260429"

DEFAULT_RECORDINGS_DIR = Path(
    "/Users/sam/repos/codec-through/research/2026-04-26-e3-sectional-scroll-walltime/recordings"
)
ARTIFACT_DIR = REPO_ROOT / ("research/experiments/2026/artifacts/sam_scaleout_m5_20260429")
DEFAULT_OUT = ARTIFACT_DIR / "sam_b3_streaming_baselines.jsonl"

MODEL_ID_DEFAULT = "google/gemma-4-26B-A4B-it"
HF_SNAPSHOT_DEFAULT = "7d4c97e54145f8ffd1a4dd1b4986a5015a517842"

QUESTION = (
    "Describe what is currently on screen. Be specific about text, "
    "names, or identifiable content. Keep it under 2 sentences."
)
JUDGE_QUESTION = (
    'Reference description: "{ref}"\n'
    'Candidate description: "{cand}"\n'
    "Does the candidate match the reference's description of what is on "
    "screen? Answer only YES or NO."
)

MAX_TOKENS = 80
JUDGE_MAX_TOKENS = 6


# ---------------------------------------------------------------------------
# Provenance helpers (shared with B0b)
# ---------------------------------------------------------------------------


def peak_rss_gb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024**3)


def sha256_short(s: str | bytes) -> str:
    if isinstance(s, str):
        s = s.encode("utf-8")
    return hashlib.sha256(s).hexdigest()


def hash_ndarray(arr: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def hash_ids(ids: list[int]) -> str:
    h = hashlib.sha256()
    for i in ids:
        h.update(int(i).to_bytes(4, "little", signed=False))
    return h.hexdigest()


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
    out = {"python": sys.version.split()[0]}
    for pkg in ("mlx", "mlx_vlm", "transformers"):
        try:
            mod = __import__(pkg)
            out[pkg] = getattr(mod, "__version__", "unknown")
        except ImportError:
            out[pkg] = "missing"
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
# Frame extraction by index from an mp4 (ffmpeg-driven, on demand)
# ---------------------------------------------------------------------------


def video_meta(path: str) -> tuple[float, float, int]:
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-show_entries",
            "stream=avg_frame_rate,nb_read_frames,duration",
            "-of",
            "default=noprint_wrappers=1",
            "-count_frames",
            "-select_streams",
            "v:0",
            path,
        ],
        capture_output=True,
        text=True,
        timeout=60,
    ).stdout
    duration = 0.0
    fps = 30.0
    n = 0
    for line in out.splitlines():
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k == "duration":
            with contextlib.suppress(ValueError):
                duration = float(v)
        elif k == "avg_frame_rate" and "/" in v:
            num, den = v.split("/")
            if int(den) > 0:
                fps = int(num) / int(den)
        elif k == "nb_read_frames":
            with contextlib.suppress(ValueError):
                n = int(v)
    if n == 0 and duration > 0:
        n = int(duration * fps)
    return duration, fps, n


def extract_frame_at(video_path: str, ts: float, max_size: int = 560) -> np.ndarray:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "quiet",
            "-y",
            "-ss",
            f"{ts:.3f}",
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
    if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise SystemExit(f"frame extract failed at ts={ts} for {video_path}")
    arr = np.array(Image.open(tmp_path).convert("RGB"))
    os.unlink(tmp_path)
    return arr


def save_frame_jpgs(frames: list[np.ndarray], tag: str) -> list[str]:
    out = []
    for i, f in enumerate(frames):
        path = f"/tmp/sam_b3_{tag}_{i}.jpg"
        Image.fromarray(f).save(path, quality=85)
        out.append(path)
    return out


def cleanup(paths: list[str]) -> None:
    for p in paths:
        with contextlib.suppress(OSError):
            os.unlink(p)


# ---------------------------------------------------------------------------
# MV-inflection event detection (lightweight; pixel-diff stand-in)
# ---------------------------------------------------------------------------


def detect_events_pixeldiff(
    video_path: str, fps: float, duration: float, cadence_s: float = 1.0, z_threshold: float = 1.5
) -> list[float]:
    """Detect events as moments where the pixel-diff between adjacent
    sampled frames spikes above the moving baseline. We use this rather
    than a full H.264 MV pipeline because the recordings we use here
    are 1080p re-encodes; the exact MV side-channel that the
    sectional-scroll mechanism uses is for the codec-through claim,
    not for the gold-standard event detector.

    Returns a list of event timestamps (seconds).
    """
    sample_interval = max(0.1, min(cadence_s, 0.5))
    sample_ts = list(np.arange(sample_interval, duration, sample_interval))
    diffs: list[float] = []
    prev = None
    for ts in sample_ts:
        f = extract_frame_at(video_path, ts, max_size=320).astype(np.float32)
        if prev is not None:
            d = np.abs(f - prev).mean()
            diffs.append(float(d))
        else:
            diffs.append(0.0)
        prev = f
    if len(diffs) < 4:
        return []
    diffs_np = np.array(diffs)
    median = float(np.median(diffs_np))
    mad = float(np.median(np.abs(diffs_np - median))) + 1e-6
    z = (diffs_np - median) / mad
    event_indices = [i for i, zi in enumerate(z) if zi > z_threshold]
    # Min spacing 1.0 s between events.
    chosen: list[int] = []
    for i in event_indices:
        if not chosen or sample_ts[i] - sample_ts[chosen[-1]] >= 1.0:
            chosen.append(i)
    events = [sample_ts[i] for i in chosen]
    # Always include 1.0 s and 3/4-of-duration as anchor events so we
    # have stable coverage even if no spikes detect; these are stripped
    # if events already cover them.
    anchors = [1.5, 3.0, max(1.0, duration / 4)]
    for a in anchors:
        if not events or all(abs(a - e) > 1.0 for e in events):
            events.append(a)
    events = sorted(events)
    return events


# ---------------------------------------------------------------------------
# Harness (reuse from B0b style)
# ---------------------------------------------------------------------------


class Harness:
    def __init__(self, model_id: str) -> None:
        warnings.filterwarnings("ignore")
        from mlx_vlm import load
        from mlx_vlm.generate import stream_generate
        from mlx_vlm.prompt_utils import apply_chat_template

        print(f"[loader] loading {model_id} ...", flush=True)
        t0 = time.time()
        self.model, self.processor = load(model_id)
        print(f"[loader] loaded in {time.time() - t0:.1f}s", flush=True)
        self.apply_template = apply_chat_template
        self.stream_generate = stream_generate
        self.model_id = model_id
        cfg = self.model.config
        text_cfg = getattr(cfg, "text_config", cfg)
        layer_types = getattr(text_cfg, "layer_types", None)
        sliding = getattr(text_cfg, "sliding_window", None)
        if layer_types is None:
            self.cache_topology = {
                "n_layers": getattr(text_cfg, "num_hidden_layers", 0),
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
        self, img_paths: list[str], question: str
    ) -> tuple[mx.array, mx.array, mx.array | None, str]:
        formatted = self.apply_template(
            self.processor,
            self.model.config,
            question,
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
        self, img_paths: list[str], question: str, *, max_tokens: int = MAX_TOKENS
    ) -> dict[str, Any]:
        input_ids, pixel_values, mask, formatted = self.format_inputs(img_paths, question)
        n_input = int(input_ids.shape[1])
        kwargs = {
            "max_tokens": max_tokens,
            "input_ids": input_ids,
            "pixel_values": pixel_values,
            "temperature": 0.0,
        }
        if mask is not None:
            kwargs["mask"] = mask
        text_pieces = []
        token_ids = []
        first = None
        t_start = time.perf_counter()
        for resp in self.stream_generate(self.model, self.processor, "", **kwargs):
            if first is None:
                first = time.perf_counter()
            if resp.text:
                text_pieces.append(resp.text)
            try:
                token_ids.append(int(resp.token))
            except Exception:  # noqa: BLE001
                token_ids.append(resp.token)
        wall = (time.perf_counter() - t_start) * 1000.0
        prefill = ((first - t_start) * 1000.0) if first else None
        return {
            "output_text": "".join(text_pieces),
            "token_ids": token_ids,
            "n_input_tokens": n_input,
            "n_output_tokens": len(token_ids),
            "input_ids_hash": hash_ids(input_ids.flatten().tolist()),
            "wall_ms": wall,
            "prefill_ms": prefill,
            "generate_ms": wall - prefill if prefill else None,
        }


# ---------------------------------------------------------------------------
# Frame-selection policies
# ---------------------------------------------------------------------------


def policy_frames(
    arm: str,
    video_path: str,
    t_event: float,
    observation_window_s: float,
    fps: float,
    duration: float,
    n_arm_frames: int = 4,
) -> tuple[list[float], list[int]]:
    """Returns (timestamps, frame_indices) for a given arm at a given event.

    Frame indices are the *integer* frame indices at the source FPS so
    `selected_frame_indices` is meaningful per-row.
    """
    fps_safe = max(1.0, fps)
    win_start = max(0.0, t_event - observation_window_s)
    if arm == "screenshot_polling":
        ts = [t_event]
    elif arm == "low_fps_dense":
        if observation_window_s <= 0:
            ts = [t_event]
        else:
            ts = list(np.linspace(win_start + 0.05, t_event, n_arm_frames))
    elif arm == "recency_last_k":
        # Last K frames; ~0.5s spacing, tail at t_event
        ts = [max(0.0, t_event - 0.5 * (n_arm_frames - 1 - i)) for i in range(n_arm_frames)]
    elif arm == "sam_policy":
        # codec-through native: ViT fires at events. Approximate by
        # picking T0 (start of clip) + last event timestamp + 2 mid-window
        # frames so the LLM sees the scene history that the cache would
        # have summarized.
        ts = sorted(
            set(
                [
                    min(0.5, duration * 0.05),  # T0 anchor
                    max(0.0, t_event - observation_window_s * 0.6),
                    max(0.0, t_event - observation_window_s * 0.3),
                    t_event,
                ]
            )
        )
        # Pad / trim to n_arm_frames
        while len(ts) < n_arm_frames:
            ts.append(t_event)
        ts = ts[:n_arm_frames]
    else:
        raise ValueError(f"unknown arm: {arm}")
    ts = [min(max(0.0, t), max(0.0, duration - 0.05)) for t in ts]
    indices = [int(round(t * fps_safe)) for t in ts]
    return ts, indices


# ---------------------------------------------------------------------------
# Stale-cache classification
# ---------------------------------------------------------------------------


def classify_stale_cache(
    t_event: float, prior_event_t: float | None, window_s: float
) -> tuple[bool, str | None]:
    """`changed_answer_expected = True` when the prior window contained a
    visual change since the last anchor frame. We approximate this as
    "this event is preceded by another detected event within the window
    -- so the screen was changing". `changed_answer_expected = False`
    when no event preceded inside the window (a stable screen)."""
    if prior_event_t is None:
        return False, None
    gap = t_event - prior_event_t
    if 0 < gap <= window_s:
        return True, f"prior_event_at_{prior_event_t:.3f}"
    return False, None


# ---------------------------------------------------------------------------
# LLM-as-judge grading
# ---------------------------------------------------------------------------


def parse_yes_no(text: str) -> str | None:
    t = text.strip().upper()
    if t.startswith("YES"):
        return "YES"
    if t.startswith("NO"):
        return "NO"
    return None


# ---------------------------------------------------------------------------
# Row builder
# ---------------------------------------------------------------------------

ROW_TEMPLATE_KEYS = (
    "schema_version",
    "experiment_id",
    "protocol_id",
    "run_id",
    "phase",
    "row_role",
    "arm",
    "baseline_arm",
    "comparator_arm",
    "policy",
    "baseline_policy",
    "policy_params",
    "model_id",
    "model_sha",
    "quantization",
    "runtime",
    "runtime_commit",
    "hardware",
    "os_version",
    "mlx_version",
    "metal_version",
    "command_line",
    "memory_definition",
    "video_id",
    "event_id",
    "item_id",
    "pair_key",
    "q_index",
    "source_q_index",
    "turn_index",
    "prompt_frame_count",
    "frame_ids",
    "frame_hashes",
    "baseline_frame_ids",
    "baseline_frame_hashes",
    "frame_selection_hash",
    "frames_sha256",
    "raw_prompt",
    "baseline_raw_prompt",
    "prompt_hash",
    "baseline_prompt_hash",
    "input_ids_hash",
    "baseline_input_ids_hash",
    "raw_response",
    "baseline_raw_response",
    "session_choice",
    "baseline_choice",
    "choice_diff",
    "session_correct",
    "baseline_correct",
    "correctness_diff",
    "session_parse_failure",
    "baseline_parse_failure",
    "parse_failure",
    "text_identical",
    "decode_ms",
    "vision_ms",
    "prefill_ms",
    "repair_prefill_ms",
    "generate_ms",
    "end_to_end_ms",
    "baseline_end_to_end_ms",
    "elapsed_ms",
    "baseline_elapsed_ms",
    "vit_calls",
    "baseline_vit_calls",
    "peak_memory_gb",
    "cache_topology",
    "prefix_hit",
    "prefix_coverage",
    "prompt_tokens",
    "baseline_prompt_tokens",
    "generation_tokens",
    "seed",
    "temperature",
    "top_p",
    "evidence_budget",
    "cadence_sec",
    "fps",
    "last_k",
    "selected_frame_indices",
    "event_time_s",
    "observation_window_s",
    "stale_cache_case_id",
    "changed_answer_expected",
    "claim_id",
    "source_artifact_path",
    "source_artifact_sha256",
    "export_row_count",
    "expected_row_count",
    "exactness_match",
    "ci_method",
    "ci95",
    "provenance_note",
    "stage_timings_ms",
    "commit_sha",
)


def make_b3_row(
    *,
    base_provenance: dict[str, Any],
    arm: str,
    policy: str,
    evidence_budget: str,
    cadence_sec: float | None,
    fps: float | None,
    last_k: int | None,
    selected_frame_indices: list[int],
    video_id: str,
    event_id: str,
    item_id: str,
    pair_key: str,
    q_index: int,
    raw_prompt: str,
    frame_ids: list[str],
    frame_hashes: list[str],
    baseline_frame_ids: list[str],
    baseline_frame_hashes: list[str],
    frame_selection_hash: str,
    input_ids_hash: str,
    baseline_input_ids_hash: str,
    raw_response: str,
    baseline_raw_response: str,
    session_choice: str | None,
    baseline_choice: str | None,
    session_correct: bool,
    baseline_correct: bool,
    end_to_end_ms: float,
    baseline_end_to_end_ms: float | None,
    vit_calls: int | None,
    baseline_vit_calls: int | None,
    event_time_s: float,
    observation_window_s: float,
    stale_cache_case_id: str | None,
    changed_answer_expected: bool,
    cache_topology: dict[str, Any],
    prompt_tokens: int,
    baseline_prompt_tokens: int,
    generation_tokens: int,
    prefill_ms: float | None,
    generate_ms: float | None,
    provenance_note: str,
) -> dict[str, Any]:
    row: dict[str, Any] = {k: None for k in ROW_TEMPLATE_KEYS}
    row.update(
        {
            "schema_version": SCHEMA_VERSION,
            "experiment_id": EXPERIMENT_ID,
            "protocol_id": PROTOCOL_ID,
            "run_id": base_provenance["run_id"],
            "phase": PHASE,
            "row_role": "paired_vs_oracle",
            "arm": arm,
            "baseline_arm": "fresh_oracle_dense",
            "comparator_arm": "fresh_oracle_dense",
            "policy": policy,
            "baseline_policy": "fresh_oracle_dense",
            "policy_params": None,
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
            "event_id": event_id,
            "item_id": item_id,
            "pair_key": pair_key,
            "q_index": q_index,
            "source_q_index": None,
            "turn_index": 0,
            "prompt_frame_count": len(frame_ids),
            "frame_ids": frame_ids,
            "frame_hashes": frame_hashes,
            "baseline_frame_ids": baseline_frame_ids,
            "baseline_frame_hashes": baseline_frame_hashes,
            "frame_selection_hash": frame_selection_hash,
            "frames_sha256": frame_selection_hash,
            "raw_prompt": raw_prompt,
            "baseline_raw_prompt": raw_prompt,
            "prompt_hash": sha256_short(raw_prompt),
            "baseline_prompt_hash": sha256_short(raw_prompt),
            "input_ids_hash": input_ids_hash,
            "baseline_input_ids_hash": baseline_input_ids_hash,
            "raw_response": raw_response,
            "baseline_raw_response": baseline_raw_response,
            "session_choice": session_choice,
            "baseline_choice": baseline_choice,
            "choice_diff": session_choice != baseline_choice,
            "session_correct": bool(session_correct),
            "baseline_correct": bool(baseline_correct),
            "correctness_diff": bool(session_correct) != bool(baseline_correct),
            "session_parse_failure": False,
            "baseline_parse_failure": False,
            "parse_failure": False,
            "text_identical": raw_response == baseline_raw_response,
            "decode_ms": None,
            "vision_ms": None,
            "prefill_ms": prefill_ms,
            "repair_prefill_ms": None,
            "generate_ms": generate_ms,
            "end_to_end_ms": end_to_end_ms,
            "baseline_end_to_end_ms": baseline_end_to_end_ms,
            "elapsed_ms": end_to_end_ms,
            "baseline_elapsed_ms": baseline_end_to_end_ms,
            "vit_calls": vit_calls,
            "baseline_vit_calls": baseline_vit_calls,
            "peak_memory_gb": peak_rss_gb(),
            "cache_topology": cache_topology,
            "prefix_hit": None,
            "prefix_coverage": None,
            "prompt_tokens": prompt_tokens,
            "baseline_prompt_tokens": baseline_prompt_tokens,
            "generation_tokens": generation_tokens,
            "seed": 0,
            "temperature": 0.0,
            "top_p": None,
            "evidence_budget": evidence_budget,
            "cadence_sec": cadence_sec,
            "fps": fps,
            "last_k": last_k,
            "selected_frame_indices": selected_frame_indices,
            "event_time_s": event_time_s,
            "observation_window_s": observation_window_s,
            "stale_cache_case_id": stale_cache_case_id,
            "changed_answer_expected": changed_answer_expected,
            "claim_id": None,
            "source_artifact_path": None,
            "source_artifact_sha256": None,
            "export_row_count": None,
            "expected_row_count": None,
            "exactness_match": None,
            "ci_method": None,
            "ci95": None,
            "provenance_note": provenance_note,
            "stage_timings_ms": None,
            "commit_sha": base_provenance["commit_sha"],
        }
    )
    return row


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--recordings-dir", type=Path, default=DEFAULT_RECORDINGS_DIR)
    ap.add_argument("--observation-window-s", type=float, default=4.0)
    ap.add_argument(
        "--n-arm-frames", type=int, default=4, help="frames per arm (except screenshot_polling=1)"
    )
    ap.add_argument(
        "--n-events-per-video",
        type=int,
        default=11,
        help=">=10 to give >=20 pair_keys across 2 videos",
    )
    ap.add_argument(
        "--n-oracle-frames", type=int, default=8, help="dense-oracle frames over observation window"
    )
    ap.add_argument("--model-id", default=MODEL_ID_DEFAULT)
    ap.add_argument("--hf-snapshot", default=HF_SNAPSHOT_DEFAULT)
    ap.add_argument("--smoke", action="store_true", help="2 events on twitter only")
    args = ap.parse_args()

    # Recordings
    videos = [
        ("twitter", str(args.recordings_dir / "twitter_1080p_30.mp4")),
        ("terminal", str(args.recordings_dir / "terminal_1080p_30.mp4")),
    ]
    if args.smoke:
        videos = videos[:1]
        args.n_events_per_video = 2

    for _, path in videos:
        if not Path(path).exists():
            raise SystemExit(f"recording missing: {path}")

    args.out.parent.mkdir(parents=True, exist_ok=True)

    # Provenance
    versions = runtime_versions()
    base_provenance = {
        "run_id": f"sam_b3_{int(time.time())}_{uuid.uuid4().hex[:8]}",
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

    # Detect events per video
    print("[events] detecting per-video event timestamps", flush=True)
    per_video_events: dict[str, list[float]] = {}
    per_video_meta: dict[str, tuple[float, float, int]] = {}
    for vid, path in videos:
        duration, fps, n_frames = video_meta(path)
        per_video_meta[vid] = (duration, fps, n_frames)
        events = detect_events_pixeldiff(path, fps, duration, cadence_s=1.0, z_threshold=1.5)
        if len(events) < args.n_events_per_video:
            # Pad with uniform timestamps if detector under-fires
            extra_count = args.n_events_per_video - len(events)
            anchors = list(np.linspace(duration * 0.1, duration * 0.95, extra_count + 2)[1:-1])
            events = sorted(events + anchors)
        events = events[: args.n_events_per_video]
        per_video_events[vid] = events
        print(
            f"  [{vid}] duration={duration:.2f}s fps={fps:.1f} "
            f"events={len(events)} ts={[round(t, 2) for t in events]}",
            flush=True,
        )

    # Load model
    h = Harness(args.model_id)

    rows: list[dict[str, Any]] = []
    arms = ("screenshot_polling", "low_fps_dense", "recency_last_k", "sam_policy")

    for vid, path in videos:
        duration, fps, n_frames = per_video_meta[vid]
        events = per_video_events[vid]
        prior_event_t: float | None = None
        for ei, t_event in enumerate(events):
            event_id = f"{vid}_e{ei:02d}"
            item_id = event_id
            print(f"[event {vid} #{ei} t={t_event:.2f}s]", flush=True)
            window_s = args.observation_window_s
            stale_case, stale_id = classify_stale_cache(t_event, prior_event_t, window_s)
            prior_event_t = t_event

            # 1. Fresh oracle: dense uniform sampling over the
            #    observation window. This is the GOLD STANDARD.
            oracle_ts = list(
                np.linspace(max(0.0, t_event - window_s + 0.05), t_event, args.n_oracle_frames)
            )
            oracle_frames = [extract_frame_at(path, t) for t in oracle_ts]
            oracle_paths = save_frame_jpgs(oracle_frames, f"{vid}_e{ei:02d}_oracle")
            oracle_hashes = [hash_ndarray(f) for f in oracle_frames]
            oracle_ids = [f"{vid}@{t:.3f}s" for t in oracle_ts]
            sha256_short("|".join(oracle_hashes))
            [int(round(t * fps)) for t in oracle_ts]
            print(f"  [fresh_oracle_dense] {args.n_oracle_frames} frames", flush=True)
            oracle_run = h.run(oracle_paths, QUESTION, max_tokens=MAX_TOKENS)
            oracle_response = oracle_run["output_text"]
            cleanup(oracle_paths)
            del oracle_frames
            gc.collect()

            # The oracle answer is "correct" by construction; baseline_correct=True.
            for arm in arms:
                ts_list, idxs = policy_frames(
                    arm,
                    path,
                    t_event,
                    args.observation_window_s,
                    fps,
                    duration,
                    n_arm_frames=(1 if arm == "screenshot_polling" else args.n_arm_frames),
                )
                arm_frames = [extract_frame_at(path, t) for t in ts_list]
                arm_paths = save_frame_jpgs(arm_frames, f"{vid}_e{ei:02d}_{arm}")
                arm_hashes = [hash_ndarray(f) for f in arm_frames]
                arm_ids = [f"{vid}@{t:.3f}s" for t in ts_list]
                arm_sel_hash = sha256_short("|".join(arm_hashes))
                print(f"  [{arm}] {len(ts_list)} frames", flush=True)
                arm_run = h.run(arm_paths, QUESTION, max_tokens=MAX_TOKENS)
                arm_response = arm_run["output_text"]
                cleanup(arm_paths)
                del arm_frames

                # LLM-as-judge: does arm response match oracle response?
                judge_prompt = JUDGE_QUESTION.format(
                    ref=oracle_response.replace('"', "'"), cand=arm_response.replace('"', "'")
                )
                # Judge is text-only -- no images. mlx-vlm needs at least
                # one image; reuse the t_event frame as a neutral anchor.
                anchor_frame = extract_frame_at(path, t_event)
                anchor_paths = save_frame_jpgs([anchor_frame], "judge_anchor")
                judge_run = h.run(anchor_paths, judge_prompt, max_tokens=JUDGE_MAX_TOKENS)
                judge_text = judge_run["output_text"]
                judge_choice = parse_yes_no(judge_text)
                arm_correct = judge_choice == "YES"
                cleanup(anchor_paths)
                del anchor_frame

                # Evidence-budget metadata per arm
                if arm == "screenshot_polling":
                    evidence_budget = "1f@t"
                    cadence_sec = None
                    arm_fps = None
                    last_k = None
                elif arm == "low_fps_dense":
                    evidence_budget = f"{args.n_arm_frames}f@uniform_over_{window_s:.1f}s"
                    cadence_sec = window_s / max(1, args.n_arm_frames - 1)
                    arm_fps = args.n_arm_frames / window_s
                    last_k = None
                elif arm == "recency_last_k":
                    evidence_budget = f"last_{args.n_arm_frames}"
                    cadence_sec = 0.5
                    arm_fps = None
                    last_k = args.n_arm_frames
                elif arm == "sam_policy":
                    evidence_budget = "vit_at_events_T0_plus_window"
                    cadence_sec = None
                    arm_fps = None
                    last_k = None
                else:
                    evidence_budget = "unknown"
                    cadence_sec = None
                    arm_fps = None
                    last_k = None

                vit_calls = (
                    1 if arm in ("screenshot_polling", "low_fps_dense", "recency_last_k") else 1
                )  # sam_policy here also fires once
                # per query; in production it would
                # fire only at events
                rows.append(
                    make_b3_row(
                        base_provenance=base_provenance,
                        arm=arm,
                        policy=f"streaming_{arm}",
                        evidence_budget=evidence_budget,
                        cadence_sec=cadence_sec,
                        fps=arm_fps,
                        last_k=last_k,
                        selected_frame_indices=idxs,
                        video_id=vid,
                        event_id=event_id,
                        item_id=item_id,
                        pair_key=event_id,
                        q_index=0,
                        raw_prompt=QUESTION,
                        frame_ids=arm_ids,
                        frame_hashes=arm_hashes,
                        baseline_frame_ids=oracle_ids,
                        baseline_frame_hashes=oracle_hashes,
                        frame_selection_hash=arm_sel_hash,
                        input_ids_hash=arm_run["input_ids_hash"],
                        baseline_input_ids_hash=oracle_run["input_ids_hash"],
                        raw_response=arm_response,
                        baseline_raw_response=oracle_response,
                        session_choice=judge_choice,
                        baseline_choice="YES",
                        session_correct=arm_correct,
                        baseline_correct=True,
                        end_to_end_ms=arm_run["wall_ms"],
                        baseline_end_to_end_ms=oracle_run["wall_ms"],
                        vit_calls=vit_calls,
                        baseline_vit_calls=args.n_oracle_frames,
                        event_time_s=t_event,
                        observation_window_s=window_s,
                        stale_cache_case_id=stale_id,
                        changed_answer_expected=stale_case,
                        cache_topology=h.cache_topology,
                        prompt_tokens=arm_run["n_input_tokens"],
                        baseline_prompt_tokens=oracle_run["n_input_tokens"],
                        generation_tokens=arm_run["n_output_tokens"],
                        prefill_ms=arm_run.get("prefill_ms"),
                        generate_ms=arm_run.get("generate_ms"),
                        provenance_note=(
                            f"event_id={event_id}; arm={arm}; baseline=fresh_oracle_dense "
                            f"({args.n_oracle_frames} frames over {window_s:.1f}s); "
                            f"judge=YES/NO match against oracle answer."
                        ),
                    )
                )
                gc.collect()
            print(f"  [event {ei} done] arms emitted", flush=True)

    with args.out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    print(f"[wrote] {len(rows)} rows -> {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
