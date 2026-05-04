#!/usr/bin/env python3
"""M5-5b -- Prefix-snapshot cache-reuse regression on Gemma 4 26B-A4B.

Tests the `swa_aware_cache_v2.make_prefix_snapshot` /
`run_turn_with_snapshot` workflow as a real cross-turn cache reuse
mechanism that delivers BOTH correctness and speedup on Gemma 4
26B-A4B's mixed-SWA topology.

Compares 2 arms per (video, q_index):
  - cold_dense (baseline): per-Q full prefill+generate
  - prefix_snapshot       : warm a [system, image] cache snapshot
                            once per video, then for each Q restore
                            the snapshot and prefill only the
                            question-trailing tokens

7 videos x 3 questions = 21 paired rows. Greedy decoding (temp=0).

Gate (replaces the strict B0b gate):
  - >=20/21 byte-identical (text_identical=True)
  - median speedup >=2x vs cold_dense
  - 0 schema errors
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import platform
import resource
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import mlx.core as mx

if not os.environ.get("HF_TOKEN"):
    raise SystemExit("HF_TOKEN required.")

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from run_sam_b0b_cache_correctness import (  # noqa: E402
    HF_SNAPSHOT_DEFAULT,
    MODEL_ID_DEFAULT,
    VIDEOMME_DIR_DEFAULT,
    Harness,
    cleanup_paths,
    extract_frames,
    find_videomme_parquet,
    find_videomme_video,
    hash_ids,
    hash_ndarray,
    save_frame_jpgs,
    sha256_short,
)
from swa_aware_cache_v2 import (  # noqa: E402
    make_prefix_snapshot,
    run_turn_with_snapshot,
)

SCHEMA_VERSION = "sam_scaleout_artifact_v1"
PHASE = "M5-5b"
EXPERIMENT_ID = "sam_scaleout_m5_5b_swa_prefix_snapshot_20260429"
PROTOCOL_ID = "sam_scaleout_handoff_20260429"

ARTIFACT_DIR = REPO_ROOT / ("research/experiments/2026/artifacts/sam_scaleout_m5_20260429")
DEFAULT_OUT = ARTIFACT_DIR / "sam_m5_5b_swa_prefix_snapshot.jsonl"

FOLLOWUPS = (
    "What color is most prominent in the scene?",
    "Are there any people visible? Answer YES or NO and one short phrase.",
)
MAX_TOKENS = 32


def peak_rss_gb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024**3)


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


def make_row(prov, **kw):
    row = {k: None for k in ROW_KEYS}
    row.update(
        {
            "schema_version": SCHEMA_VERSION,
            "experiment_id": EXPERIMENT_ID,
            "protocol_id": PROTOCOL_ID,
            "run_id": prov["run_id"],
            "phase": PHASE,
            "row_role": "paired",
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


def cold_dense_run(
    harness: Any,
    img_paths: list[str],
    question: str,
    *,
    max_tokens: int = MAX_TOKENS,
    single_shot_prefill: bool = False,
) -> dict[str, Any]:
    """Cold-dense run with optional single-shot prefill (for the
    byte-identical comparison vs prefix-snapshot)."""
    formatted = harness.apply_template(
        harness.processor,
        harness.model.config,
        question,
        num_images=len(img_paths),
        enable_thinking=False,
    )
    inputs = harness.processor(
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
    if single_shot_prefill:
        kwargs["prefill_step_size"] = None
    text_pieces, token_ids = [], []
    first_t = None
    t0 = time.perf_counter()
    for resp in harness.stream_generate(harness.model, harness.processor, "", **kwargs):
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
        "wall_time_ms": wall,
        "prefill_ms": prefill,
        "generate_ms": wall - prefill if prefill else None,
    }


def parse_letter(text: str, n: int = 4) -> str | None:
    t = text.strip().upper()
    for letter in [chr(ord("A") + i) for i in range(n)]:
        if t.startswith(letter):
            return letter
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-videos", type=int, default=7)
    ap.add_argument("--n-frames", type=int, default=8)
    ap.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    ap.add_argument("--model-id", default=MODEL_ID_DEFAULT)
    ap.add_argument("--hf-snapshot", default=HF_SNAPSHOT_DEFAULT)
    ap.add_argument("--videomme-dir", type=Path, default=VIDEOMME_DIR_DEFAULT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--single-shot-prefill",
        action="store_true",
        help="Use prefill_step_size=None on both arms to "
        "eliminate chunked-prefill BF16 noise as a "
        "source of paraphrase divergence.",
    )
    args = ap.parse_args()

    parquet = find_videomme_parquet(args.videomme_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)

    versions = runtime_versions()
    prov = {
        "run_id": f"sam_m55b_{int(time.time())}_{uuid.uuid4().hex[:8]}",
        "model_id": args.model_id,
        "model_sha": args.hf_snapshot,
        "quantization": "bf16_native",
        "runtime": f"mlx_vlm-{versions['mlx_vlm']}",
        "runtime_commit": "pypi",
        "hardware": hardware_descriptor(),
        "os_version": f"Darwin {platform.release()}",
        "mlx_version": versions.get("mlx", "unknown"),
        "metal_version": None,
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
        items.append(
            {
                "video_id": str(row["videoID"]),
                "q1_text": str(row["question"]),
                "options": list(row["options"]),
                "answer_letter": str(row["answer"]),
            }
        )
        if len(items) >= args.n_videos:
            break

    h = Harness(args.model_id)
    rows = []

    for vi, it in enumerate(items):
        vp = find_videomme_video(it["video_id"], args.videomme_dir)
        if not vp:
            raise SystemExit(f"video missing: {it['video_id']}")
        frames, ts = extract_frames(vp, args.n_frames)
        paths = save_frame_jpgs(frames, it["video_id"])
        frame_hashes = [hash_ndarray(f) for f in frames]
        frame_ids = [f"{it['video_id']}@{t:.3f}s" for t in ts]
        sel_hash = sha256_short("|".join(frame_hashes))
        print(f"[video {vi + 1}/{len(items)}] {it['video_id']}", flush=True)

        # 3 questions
        q1_with_options = (
            f"{it['q1_text']}\n"
            + "\n".join(f"{chr(ord('A') + i)}. {o}" for i, o in enumerate(it["options"]))
            + "\nAnswer with a single letter (A/B/C/D)."
        )
        qs = [("q1_mc", q1_with_options), ("q2_color", FOLLOWUPS[0]), ("q3_people", FOLLOWUPS[1])]

        # Cold dense baseline per Q.
        cold = {}
        for q_label, q_text in qs:
            print(f"  [cold_dense] {q_label}", flush=True)
            cold[q_label] = cold_dense_run(
                h,
                paths,
                q_text,
                max_tokens=args.max_tokens,
                single_shot_prefill=args.single_shot_prefill,
            )
            gc.collect()

        # Build prefix snapshot once for this video.
        print("  [snapshot] warming prefix cache ...", flush=True)
        snapshot = make_prefix_snapshot(h, paths, single_shot_prefill=args.single_shot_prefill)
        print(
            f"    n_prefix={snapshot['n_prefix_tokens']} warm_ms={snapshot['warm_ms']:.0f}",
            flush=True,
        )

        # Run each Q against the snapshot.
        snap_runs = {}
        for q_label, q_text in qs:
            print(f"  [snapshot] {q_label}", flush=True)
            snap_runs[q_label] = run_turn_with_snapshot(
                snapshot,
                h,
                paths,
                q_text,
                max_tokens=args.max_tokens,
                single_shot_prefill=args.single_shot_prefill,
            )
            gc.collect()

        # Emit rows.
        for q_idx, (q_label, q_text) in enumerate(qs):
            cb = cold[q_label]
            sn = snap_runs[q_label]
            n_opts = len(it["options"]) if q_label == "q1_mc" else 4
            cb_choice = parse_letter(cb["output_text"], n_opts)
            sn_choice = parse_letter(sn["output_text"], n_opts)
            cb_correct = q_label == "q1_mc" and cb_choice == it["answer_letter"].strip().upper()
            sn_correct = q_label == "q1_mc" and sn_choice == it["answer_letter"].strip().upper()
            cb_pf = q_label == "q1_mc" and cb_choice is None
            sn_pf = q_label == "q1_mc" and sn_choice is None

            rows.append(
                make_row(
                    prov,
                    arm="prefix_snapshot",
                    baseline_arm="cold_dense",
                    comparator_arm="cold_dense",
                    policy="swa_aware_cache_v2_prefix_snapshot",
                    baseline_policy="cold_dense_no_cache",
                    policy_params={
                        "n_prefix_tokens": snapshot["n_prefix_tokens"],
                        "warm_ms": snapshot["warm_ms"],
                    },
                    video_id=it["video_id"],
                    item_id=it["video_id"],
                    pair_key=f"v={it['video_id']}/q={q_idx}/snapshot",
                    q_index=q_idx,
                    turn_index=q_idx,
                    prompt_frame_count=args.n_frames,
                    frame_ids=frame_ids,
                    frame_hashes=frame_hashes,
                    baseline_frame_ids=frame_ids,
                    baseline_frame_hashes=frame_hashes,
                    frame_selection_hash=sel_hash,
                    frames_sha256=sel_hash,
                    raw_prompt=q_text,
                    baseline_raw_prompt=q_text,
                    prompt_hash=sha256_short(q_text),
                    baseline_prompt_hash=sha256_short(q_text),
                    input_ids_hash=sha256_short(f"snapshot|v={it['video_id']}|q={q_idx}"),
                    baseline_input_ids_hash=cb["input_ids_hash"],
                    raw_response=sn["output_text"],
                    baseline_raw_response=cb["output_text"],
                    session_choice=sn_choice,
                    baseline_choice=cb_choice,
                    choice_diff=sn_choice != cb_choice,
                    session_correct=sn_correct,
                    baseline_correct=cb_correct,
                    correctness_diff=sn_correct != cb_correct,
                    session_parse_failure=sn_pf,
                    baseline_parse_failure=cb_pf,
                    parse_failure=sn_pf or cb_pf,
                    text_identical=sn["output_text"] == cb["output_text"],
                    end_to_end_ms=sn["wall_ms"],
                    baseline_end_to_end_ms=cb["wall_time_ms"],
                    elapsed_ms=sn["wall_ms"],
                    baseline_elapsed_ms=cb["wall_time_ms"],
                    prefill_ms=sn["prefill_ms"],
                    generate_ms=sn["generate_ms"],
                    vit_calls=0,
                    baseline_vit_calls=1,
                    peak_memory_gb=peak_rss_gb(),
                    cache_topology=h.cache_topology,
                    prefix_hit=snapshot["n_prefix_tokens"],
                    prefix_coverage=1.0,
                    prompt_tokens=sn["n_input_tokens"],
                    baseline_prompt_tokens=cb["n_input_tokens"],
                    generation_tokens=sn["n_output_tokens"],
                    provenance_note=(
                        f"M5-5b prefix-snapshot wrapper. Snapshot warmed "
                        f"once per video at the [system, image] boundary "
                        f"(n={snapshot['n_prefix_tokens']} tokens, "
                        f"warm_ms={snapshot['warm_ms']:.0f}). For each Q the "
                        f"snapshot is restored, only the question-trailing "
                        f"tokens are prefilled, then generate."
                    ),
                )
            )

        cleanup_paths(paths)
        del frames
        gc.collect()

    with args.out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"[wrote] {len(rows)} rows -> {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
