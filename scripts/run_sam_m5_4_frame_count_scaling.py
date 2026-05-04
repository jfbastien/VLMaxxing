#!/usr/bin/env python3
"""M5-4 -- Frame-count scaling at 26B on Gemma 4 26B-A4B.

Cross-architecture C-CEILING data point: how does per-stage compute
scale with frame count, and where does the per-frame cost flatten or
inflect? JF's local lane has C-CEILING measured at the 4B class; this
phase fills the 26B / scale-out cell for the same axis.

Frame counts: 8 / 16 / 32 / 64 / 128.
3 videos x 5 frame counts = 15 schema-compliant rows.
Each row records dense forward+generate timing decomposed into
ViT, prefill, generate, total. Per-frame compute is computed
post-hoc in analysis.

Greedy decoding (temp=0). Same VideoMME items as B0b/B1/B2.

Estimated runtime: ~30-45 min on M5 Max for 3x5 forward passes
(128f is the dominant cost -- ~30s/forward at 128 frames).
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

import contextlib

import mlx.core as mx
import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "sam_scaleout_artifact_v1"
PHASE = "M5-4"
EXPERIMENT_ID = "sam_scaleout_m5_4_frame_count_scaling_20260429"
PROTOCOL_ID = "sam_scaleout_handoff_20260429"

VIDEOMME_DIR_DEFAULT = Path(
    os.environ.get("CODEC_THROUGH_VIDEOMME_DIR", "data/benchmarks/videomme")
)
ARTIFACT_DIR = REPO_ROOT / ("research/experiments/2026/artifacts/sam_scaleout_m5_20260429")
DEFAULT_OUT = ARTIFACT_DIR / "sam_m5_4_frame_count_scaling.jsonl"

MODEL_ID_DEFAULT = "google/gemma-4-26B-A4B-it"
HF_SNAPSHOT_DEFAULT = "7d4c97e54145f8ffd1a4dd1b4986a5015a517842"

QUESTION = "Describe the most prominent visual content. Keep it concise."
MAX_TOKENS = 16
DEFAULT_FRAME_COUNTS = [8, 16, 32, 64, 128]


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


def repo_commit_sha(p: Path) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(p), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
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
    chip = (
        subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True, timeout=5
        ).stdout.strip()
        or "?"
    )
    try:
        mem = int(
            subprocess.run(
                ["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=5
            ).stdout.strip()
            or 0
        )
        mem_gb = mem / (1024**3)
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


def find_videomme_video(video_id: str, vmme_dir: Path) -> str | None:
    for ext in (".mp4", ".mkv", ".webm"):
        for p in vmme_dir.rglob(f"{video_id}{ext}"):
            return str(p)
    return None


def find_videomme_parquet(vmme_dir: Path) -> Path:
    for rel in (
        Path("hf/videomme/test-00000-of-00001.parquet"),
        Path("videomme/test-00000-of-00001.parquet"),
    ):
        path = vmme_dir / rel
        if path.exists():
            return path
    raise SystemExit(
        f"VideoMME parquet missing under {vmme_dir}. "
        "Run `uv run python scripts/fetch_benchmarks.py --dataset videomme --mode metadata`."
    )


def extract_frames(
    video_path: str, n_frames: int, max_size: int = 560
) -> tuple[list[np.ndarray], list[float]]:
    out = subprocess.run(
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
        duration = float(out.stdout.strip())
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
        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
            frames.append(np.array(Image.open(tmp_path).convert("RGB")))
        if os.path.exists(tmp_path):
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
    return frames, [float(t) for t in timestamps]


def save_jpgs(frames: list[np.ndarray], tag: str) -> list[str]:
    paths = []
    for i, f in enumerate(frames):
        path = f"/tmp/sam_m54_{tag}_{i}.jpg"
        Image.fromarray(f).save(path, quality=85)
        paths.append(path)
    return paths


def cleanup(paths: list[str]) -> None:
    for p in paths:
        with contextlib.suppress(OSError):
            os.unlink(p)


class Harness:
    def __init__(self, model_id: str) -> None:
        warnings.filterwarnings("ignore")
        from mlx_vlm import load
        from mlx_vlm.generate import stream_generate
        from mlx_vlm.prompt_utils import apply_chat_template

        print(f"[loader] loading {model_id}", flush=True)
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

    def run(self, img_paths: list[str], q: str, *, max_tokens: int = MAX_TOKENS) -> dict[str, Any]:
        formatted = self.apply_template(
            self.processor, self.model.config, q, num_images=len(img_paths), enable_thinking=False
        )
        inputs = self.processor(
            text=[formatted], images=img_paths, return_tensors="np", add_special_tokens=False
        )
        input_ids = mx.array(inputs["input_ids"])
        pixel_values = mx.array(inputs["pixel_values"])
        mask = mx.array(inputs["attention_mask"]) if "attention_mask" in inputs else None
        n_input = int(input_ids.shape[1])
        kwargs = {
            "max_tokens": max_tokens,
            "input_ids": input_ids,
            "pixel_values": pixel_values,
            "temperature": 0.0,
        }
        if mask is not None:
            kwargs["mask"] = mask
        text_pieces, token_ids = [], []
        first_t = None
        t0 = time.perf_counter()
        for resp in self.stream_generate(self.model, self.processor, "", **kwargs):
            if first_t is None:
                first_t = time.perf_counter()
            if resp.text:
                text_pieces.append(resp.text)
            try:
                token_ids.append(int(resp.token))
            except Exception:  # noqa: BLE001
                token_ids.append(resp.token)
        wall = (time.perf_counter() - t0) * 1000.0
        prefill = ((first_t - t0) * 1000.0) if first_t else None
        return {
            "output_text": "".join(text_pieces),
            "n_input_tokens": n_input,
            "n_output_tokens": len(token_ids),
            "input_ids_hash": hash_ids(input_ids.flatten().tolist()),
            "wall_ms": wall,
            "prefill_ms": prefill,
            "generate_ms": wall - prefill if prefill else None,
        }


ROW_KEYS = (
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


def make_row(prov: dict[str, Any], **kw: Any) -> dict[str, Any]:
    row = {k: None for k in ROW_KEYS}
    row.update(
        {
            "schema_version": SCHEMA_VERSION,
            "experiment_id": EXPERIMENT_ID,
            "protocol_id": PROTOCOL_ID,
            "run_id": prov["run_id"],
            "phase": PHASE,
            "row_role": "single_arm_timing",
            "model_id": prov["model_id"],
            "model_sha": prov["model_sha"],
            "quantization": prov["quantization"],
            "runtime": prov["runtime"],
            "runtime_commit": prov["runtime_commit"],
            "hardware": prov["hardware"],
            "os_version": prov["os_version"],
            "mlx_version": prov["mlx_version"],
            "metal_version": prov["metal_version"],
            "command_line": prov["command_line"],
            "memory_definition": prov["memory_definition"],
            "frame_ids": [],
            "frame_hashes": [],
            "baseline_frame_ids": [],
            "baseline_frame_hashes": [],
            "raw_prompt": "",
            "baseline_raw_prompt": "",
            "raw_response": "",
            "baseline_raw_response": "",
            "choice_diff": False,
            "session_correct": False,
            "baseline_correct": False,
            "correctness_diff": False,
            "session_parse_failure": False,
            "baseline_parse_failure": False,
            "parse_failure": False,
            "text_identical": False,
            "end_to_end_ms": 0.0,
            "seed": 0,
            "temperature": 0.0,
            "cache_topology": {},
            "selected_frame_indices": None,
            "commit_sha": prov["commit_sha"],
        }
    )
    row.update(kw)
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-videos", type=int, default=3)
    ap.add_argument("--frame-counts", type=int, nargs="+", default=DEFAULT_FRAME_COUNTS)
    ap.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    ap.add_argument("--model-id", default=MODEL_ID_DEFAULT)
    ap.add_argument("--hf-snapshot", default=HF_SNAPSHOT_DEFAULT)
    ap.add_argument("--videomme-dir", type=Path, default=VIDEOMME_DIR_DEFAULT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    if args.smoke:
        args.n_videos = 1
        args.frame_counts = [8, 16]

    parquet = find_videomme_parquet(args.videomme_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)

    versions = runtime_versions()
    prov = {
        "run_id": f"sam_m54_{int(time.time())}_{uuid.uuid4().hex[:8]}",
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
    print(f"[provenance] {json.dumps(prov, indent=2)}", flush=True)

    import pyarrow.parquet as pq

    df = pq.read_table(parquet).to_pandas().sort_values("question_id").reset_index(drop=True)
    seen, items = {}, []
    for _, row in df.iterrows():
        if row["videoID"] in seen:
            continue
        seen[row["videoID"]] = True
        items.append({"video_id": str(row["videoID"])})
        if len(items) >= args.n_videos:
            break

    h = Harness(args.model_id)
    rows: list[dict[str, Any]] = []

    for vi, it in enumerate(items):
        vp = find_videomme_video(it["video_id"], args.videomme_dir)
        if not vp:
            raise SystemExit(f"video missing: {it['video_id']}")
        for fc in args.frame_counts:
            print(f"[video {vi + 1}/{len(items)} {it['video_id']}] frames={fc}", flush=True)
            frames, ts = extract_frames(vp, fc)
            if len(frames) != fc:
                raise SystemExit("frame count mismatch")
            paths = save_jpgs(frames, f"{it['video_id']}_f{fc}")
            frame_hashes = [hash_ndarray(f) for f in frames]
            frame_ids = [f"{it['video_id']}@{t:.3f}s" for t in ts]
            sel_hash = sha256_short("|".join(frame_hashes))
            t0 = time.perf_counter()
            r = h.run(paths, QUESTION, max_tokens=args.max_tokens)
            wall_outer = (time.perf_counter() - t0) * 1000.0
            cleanup(paths)
            del frames
            gc.collect()

            stage_timings = {
                "wall_outer_ms": wall_outer,
                "prefill_ms": r["prefill_ms"],
                "generate_ms": r["generate_ms"],
                "n_input_tokens": r["n_input_tokens"],
                "n_output_tokens": r["n_output_tokens"],
                "ms_per_frame_total": wall_outer / max(fc, 1),
                "ms_per_input_token": r["prefill_ms"] / max(r["n_input_tokens"], 1)
                if r["prefill_ms"]
                else None,
            }

            rows.append(
                make_row(
                    prov,
                    arm="cold_dense",
                    baseline_arm="cold_dense",
                    comparator_arm=None,
                    policy="cold_dense_no_cache",
                    baseline_policy="cold_dense_no_cache",
                    policy_params={"frame_count": fc},
                    video_id=it["video_id"],
                    item_id=it["video_id"],
                    pair_key=f"v={it['video_id']}/f={fc}",
                    q_index=0,
                    turn_index=0,
                    prompt_frame_count=fc,
                    frame_ids=frame_ids,
                    frame_hashes=frame_hashes,
                    baseline_frame_ids=frame_ids,
                    baseline_frame_hashes=frame_hashes,
                    frame_selection_hash=sel_hash,
                    frames_sha256=sel_hash,
                    raw_prompt=QUESTION,
                    baseline_raw_prompt=QUESTION,
                    prompt_hash=sha256_short(QUESTION),
                    baseline_prompt_hash=sha256_short(QUESTION),
                    input_ids_hash=r["input_ids_hash"],
                    baseline_input_ids_hash=r["input_ids_hash"],
                    raw_response=r["output_text"],
                    baseline_raw_response=r["output_text"],
                    session_choice=None,
                    baseline_choice=None,
                    choice_diff=False,
                    session_correct=False,
                    baseline_correct=False,
                    correctness_diff=False,
                    session_parse_failure=False,
                    baseline_parse_failure=False,
                    parse_failure=False,
                    text_identical=True,
                    prefill_ms=r["prefill_ms"],
                    generate_ms=r["generate_ms"],
                    end_to_end_ms=wall_outer,
                    baseline_end_to_end_ms=wall_outer,
                    elapsed_ms=wall_outer,
                    baseline_elapsed_ms=wall_outer,
                    vit_calls=1,
                    baseline_vit_calls=1,
                    peak_memory_gb=peak_rss_gb(),
                    cache_topology=h.cache_topology,
                    prompt_tokens=r["n_input_tokens"],
                    baseline_prompt_tokens=r["n_input_tokens"],
                    generation_tokens=r["n_output_tokens"],
                    evidence_budget=f"dense_f{fc}",
                    cadence_sec=None,
                    fps=None,
                    last_k=None,
                    selected_frame_indices=list(range(fc)),
                    stage_timings_ms=stage_timings,
                    claim_id="C_CEILING_per_frame_compute_curve_26B",
                    provenance_note=(
                        f"M5-4 frame-count scaling on Gemma 4 26B-A4B at "
                        f"f={fc}. Single dense forward pass per (video, fc). "
                        f"Per-frame compute = wall_ms / fc. Cross-arch "
                        f"C-CEILING data point."
                    ),
                )
            )
            print(f"  done: {wall_outer:.0f}ms total ({wall_outer / fc:.0f}ms/frame)", flush=True)

    with args.out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"[wrote] {len(rows)} rows -> {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
