#!/usr/bin/env python3
"""B4-adjacent -- Track B (hard-prune) on Gemma 4 26B-A4B.

Phase contract: research/experiments/2026/2026-04-29-sam-scaleout-handoff.md

NON-CONFORMANCE NOTICE: the strict B4 contract requires "real
compact/sparse vision-tower execution" -- i.e., the ViT does less work
on pruned input. This stack does NOT have a sparse-ViT execution path
on Gemma 4 26B-A4B (mlx-vlm 0.4.4 runs the vision tower densely on all
patches). The closest deployment-relevant Track B mechanism on this
stack is **post-ViT hard spatial pruning**: the ViT runs fully, then
the lowest-importance visual tokens are *physically removed* from the
LLM input ids before the LM prefill. This reduces LLM prefill cost
(real work skipped in prefill, per the AGENTS.md Track A/B definition)
but does NOT reduce vision-tower cost.

We run the protocol against this hard-prune mechanism with explicit
non-conformance disclosure on every row's `provenance_note` field.
The findings doc explains the disclosure.

Imports the existing post-ViT pruning pipeline from sdamico/codec-
through (`experiments/run_gemma4_validation.py::Gemma4VLM.run_comparison_pruned`)
via sys.path. The cascade is `experiments/spatial_cascade.py`.

Frame counts: 8f and 32f. Keep rate: 0.50.

Estimated runtime: ~30-45 min on M5 Max for 5 videos x {8f, 32f} x
{dense, pruned} = 20 forward passes.
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
import time
import uuid
import warnings
from pathlib import Path
from typing import Any

if not os.environ.get("HF_TOKEN"):
    raise SystemExit("HF_TOKEN required.")

REPO_ROOT = Path(__file__).resolve().parents[1]
SDAMICO_EXPERIMENTS = Path(
    os.environ.get("CODEC_THROUGH_SDAMICO_EXPERIMENTS", "external/codec-through/experiments")
)
if str(SDAMICO_EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(SDAMICO_EXPERIMENTS))

import contextlib  # noqa: E402

import numpy as np  # noqa: E402

SCHEMA_VERSION = "sam_scaleout_artifact_v1"
PHASE = "B4"
EXPERIMENT_ID = "sam_scaleout_b4_track_b_hard_prune_20260429"
PROTOCOL_ID = "sam_scaleout_handoff_20260429"

VIDEOMME_DIR_DEFAULT = SDAMICO_EXPERIMENTS / "videomme_data"
ARTIFACT_DIR = REPO_ROOT / ("research/experiments/2026/artifacts/sam_scaleout_m5_20260429")
DEFAULT_OUT = ARTIFACT_DIR / "sam_b4_sparse_vit_ceiling.jsonl"

MODEL_ID_DEFAULT = "google/gemma-4-26B-A4B-it"
HF_SNAPSHOT_DEFAULT = "7d4c97e54145f8ffd1a4dd1b4986a5015a517842"

QUESTION = "Describe the most prominent visual content. Keep it concise."
KEEP_RATIO = 0.50
MAX_TOKENS = 32


# Provenance helpers (shared shape with B0b/B3/B5)


def peak_rss_gb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024**3)


def sha256_short(s: str | bytes) -> str:
    if isinstance(s, str):
        s = s.encode("utf-8")
    return hashlib.sha256(s).hexdigest()


def hash_ndarray(arr: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


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


# Frame extraction


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
    import tempfile

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
    from PIL import Image

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


# Schema row

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
            "row_role": "paired_dense_vs_pruned",
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
    ap.add_argument("--n-videos", type=int, default=5)
    ap.add_argument("--frame-counts", type=int, nargs="+", default=[8, 32])
    ap.add_argument("--keep-ratio", type=float, default=KEEP_RATIO)
    ap.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    ap.add_argument("--model-id", default=MODEL_ID_DEFAULT)
    ap.add_argument("--hf-snapshot", default=HF_SNAPSHOT_DEFAULT)
    ap.add_argument("--videomme-dir", type=Path, default=VIDEOMME_DIR_DEFAULT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    if args.smoke:
        args.n_videos = 1
        args.frame_counts = [8]

    parquet = find_videomme_parquet(args.videomme_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)

    versions = runtime_versions()
    prov = {
        "run_id": f"sam_b4_{int(time.time())}_{uuid.uuid4().hex[:8]}",
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

    # Load VideoMME items.
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

    # Load model via sdamico's wrapper.
    warnings.filterwarnings("ignore")
    from run_gemma4_validation import Gemma4VLM

    print(f"[loader] loading {args.model_id} via Gemma4VLM", flush=True)
    t0 = time.time()
    vlm = Gemma4VLM(model_name=args.model_id, thinking=False)
    print(f"[loader] loaded in {time.time() - t0:.1f}s", flush=True)
    cache_topology = {}  # not relevant for B4
    try:
        text_cfg = getattr(vlm.model.config, "text_config", vlm.model.config)
        layer_types = getattr(text_cfg, "layer_types", None)
        sliding = getattr(text_cfg, "sliding_window", None)
        if layer_types is None:
            cache_topology = {
                "n_layers": getattr(text_cfg, "num_hidden_layers", 0),
                "sliding_window": sliding,
                "layer_types": "uniform",
            }
        else:
            cache_topology = {
                "n_layers": len(layer_types),
                "sliding_window": sliding,
                "layer_types": list(layer_types),
                "n_swa": sum(1 for t in layer_types if "sliding" in str(t)),
                "n_full": sum(1 for t in layer_types if "full" in str(t)),
            }
    except Exception:  # noqa: BLE001
        pass

    rows: list[dict[str, Any]] = []

    for vi, it in enumerate(items):
        vp = find_videomme_video(it["video_id"], args.videomme_dir)
        if not vp:
            raise SystemExit(f"video missing: {it['video_id']}")
        for fc in args.frame_counts:
            print(f"[video {vi + 1}/{len(items)} {it['video_id']}] frames={fc}", flush=True)
            frames, ts = extract_frames(vp, fc)
            if len(frames) != fc:
                raise SystemExit(f"frame count mismatch for {it['video_id']}")
            frame_hashes = [hash_ndarray(f) for f in frames]
            frame_ids = [f"{it['video_id']}@{t:.3f}s" for t in ts]
            sel_hash = sha256_short("|".join(frame_hashes))

            # Run both arms via sdamico's helper.
            print(f"  [run] dense vs hard-prune kr={args.keep_ratio}", flush=True)
            t_total = time.perf_counter()
            comparison = vlm.run_comparison_pruned(
                frames, QUESTION, keep_ratio=args.keep_ratio, max_tokens=args.max_tokens
            )
            wall_total = (time.perf_counter() - t_total) * 1000.0

            baseline_text = comparison["baseline"]
            pruned_text = comparison["pruned"]
            baseline_ms = comparison["baseline_ms"]
            pm = comparison["prune_metrics"]
            # Compose pruned E2E from stage timings.
            pruned_ms = (
                pm.get("vit_ms", 0.0)
                + pm.get("spatial_ms", 0.0)
                + pm.get("novelty_ms", 0.0)
                + pm.get("prefill_ms", 0.0)
                + pm.get("gen_ms", 0.0)
            )

            # C-CEILING (modified for hard-prune which reduces prefill, not
            # vision): we report observed prefill reduction and the E2E
            # speedup ratio.
            e2e_speedup = baseline_ms / max(pruned_ms, 1.0) if baseline_ms > 0 else float("nan")

            # Vision share is a constant: ViT runs fully both times. We
            # record vit_ms in stage_timings_ms and note that vision_ms
            # in the schema is the vit_ms (pruning post-ViT does not
            # reduce it).
            stage_timings = {
                "dense_total_ms": baseline_ms,
                "pruned_vit_ms": pm.get("vit_ms"),
                "pruned_spatial_cascade_ms": pm.get("spatial_ms"),
                "pruned_novelty_ms": pm.get("novelty_ms"),
                "pruned_prefill_ms": pm.get("prefill_ms"),
                "pruned_gen_ms": pm.get("gen_ms"),
                "pruned_total_ms": pruned_ms,
                "wall_outer_ms": wall_total,
                "tokens_before": pm.get("tokens_before"),
                "tokens_after": pm.get("tokens_after"),
                "keep_ratio_actual": pm.get("keep_ratio_actual"),
                "e2e_speedup_observed": e2e_speedup,
            }

            text_id = baseline_text == pruned_text

            rows.append(
                make_row(
                    prov,
                    arm="hard_prune_post_vit_kr050",
                    baseline_arm="dense_no_prune",
                    comparator_arm="dense_no_prune",
                    policy=f"hard_prune_keep_ratio_{args.keep_ratio}",
                    baseline_policy="dense_no_prune",
                    policy_params={"keep_ratio": args.keep_ratio, "frame_count": fc},
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
                    input_ids_hash=sha256_short(
                        f"pruned|kr{args.keep_ratio}|f{fc}|{it['video_id']}"
                    ),
                    baseline_input_ids_hash=sha256_short(f"dense|f{fc}|{it['video_id']}"),
                    raw_response=pruned_text,
                    baseline_raw_response=baseline_text,
                    session_choice=None,
                    baseline_choice=None,
                    choice_diff=False,
                    session_correct=False,
                    baseline_correct=False,
                    correctness_diff=False,
                    session_parse_failure=False,
                    baseline_parse_failure=False,
                    parse_failure=False,
                    text_identical=text_id,
                    vision_ms=pm.get("vit_ms"),
                    prefill_ms=pm.get("prefill_ms"),
                    generate_ms=pm.get("gen_ms"),
                    end_to_end_ms=pruned_ms,
                    baseline_end_to_end_ms=baseline_ms,
                    elapsed_ms=pruned_ms,
                    baseline_elapsed_ms=baseline_ms,
                    vit_calls=1,
                    baseline_vit_calls=1,
                    peak_memory_gb=peak_rss_gb(),
                    cache_topology=cache_topology,
                    prompt_tokens=pm.get("tokens_after"),
                    baseline_prompt_tokens=pm.get("tokens_before"),
                    generation_tokens=None,
                    evidence_budget=f"hard_prune_kr{args.keep_ratio}_f{fc}",
                    cadence_sec=None,
                    fps=None,
                    last_k=None,
                    selected_frame_indices=list(range(fc)),
                    stage_timings_ms=stage_timings,
                    claim_id="C_CEILING_e2e_observed_vs_predicted",
                    provenance_note=(
                        f"NON-CONFORMANT B4: this stack has no sparse-ViT "
                        f"execution path on Gemma 4 26B-A4B. ViT runs FULLY "
                        f"on both arms. The 'session' arm applies post-ViT "
                        f"hard spatial pruning (keep_ratio={args.keep_ratio}, "
                        f"actual={pm.get('keep_ratio_actual'):.3f}) which "
                        f"reduces LLM prefill cost but not vision cost. "
                        f"Reported as B4-adjacent diagnostic; do not import "
                        f"as strict B4 evidence."
                    ),
                )
            )
            print(
                f"  [done] dense {baseline_ms:.0f}ms vs pruned {pruned_ms:.0f}ms"
                f" -> {e2e_speedup:.3f}x",
                flush=True,
            )
            del frames
            gc.collect()

    with args.out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"[wrote] {len(rows)} rows -> {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
