"""S0 cache-correctness smoke test for Gemma 4 26B-A4B on mlx-vlm.

Three smoke checks per (item, q_idx):
  1. DETERMINISM        : dense run twice, byte-identical text expected.
  2. CACHE-EQUIVALENCE  : dense vs cached-cold (build PromptCacheState during
                          prefill, generate from it). Byte-identical expected.
  3. FOLLOW-UP CORRECT  : warm-followup (re-use cache from Q1+answer) vs
                          cold-followup (independent dense). Byte-identical
                          expected — this is the test that would catch the
                          1.55D-style breakage.

Greedy decoding (temp=0). 5 VideoMME items × 2 questions each.

Outputs:
  research/2026-04-26-s0-cache-correctness/results.jsonl
  research/2026-04-26-s0-cache-correctness/summary.json
"""
import argparse
import gc
import hashlib
import json
import os
import resource
import subprocess
import sys
import tempfile
import time
import warnings
from pathlib import Path

if not os.environ.get("HF_TOKEN"):
    raise SystemExit(
        "HF_TOKEN environment variable is required (gated Gemma 4 weights). "
        "Aborting per S0 spec — do not attempt to download.")

import mlx.core as mx
import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
VIDEOMME_DIR = REPO_ROOT / "experiments" / "videomme_data"
VIDEOMME_PARQUET = VIDEOMME_DIR / "videomme" / "test-00000-of-00001.parquet"
OUT_DIR = REPO_ROOT / "research" / "2026-04-26-s0-cache-correctness"
OUT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_PATH = OUT_DIR / "results.jsonl"
SUMMARY_PATH = OUT_DIR / "summary.json"

MODEL_ID_DEFAULT = "google/gemma-4-26B-A4B-it"
FOLLOWUP_Q = "What color is most prominent in the scene?"
MAX_TOKENS = 32  # short — we just need correctness comparisons.


def peak_rss_mb():
    # ru_maxrss on macOS is in BYTES (not KB like Linux)
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r / (1024 * 1024)


def hash_str(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def hash_ids(ids):
    h = hashlib.sha256()
    for i in ids:
        h.update(int(i).to_bytes(4, "little", signed=False))
    return h.hexdigest()[:16]


def find_videomme_video(video_id):
    for ext in (".mp4", ".mkv", ".webm", ".avi"):
        for p in VIDEOMME_DIR.rglob(f"{video_id}{ext}"):
            return str(p)
    return None


def extract_frames(video_path, n_frames=8, max_size=560):
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        capture_output=True, text=True, timeout=15)
    try:
        duration = float(result.stdout.strip())
    except (ValueError, AttributeError):
        duration = 60.0
    timestamps = np.linspace(duration * 0.01, duration * 0.99, n_frames)
    frames = []
    for ts in timestamps:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
        subprocess.run(
            ["ffmpeg", "-v", "quiet", "-y",
             "-ss", f"{float(ts):.3f}", "-i", video_path,
             "-vframes", "1",
             "-vf", f"scale={max_size}:{max_size}:force_original_aspect_ratio=decrease,"
                    f"pad={max_size}:{max_size}:(ow-iw)/2:(oh-ih)/2",
             tmp_path],
            capture_output=True, timeout=30)
        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
            frames.append(np.array(Image.open(tmp_path).convert("RGB")))
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    return frames


def save_frame_jpgs(frames, tag):
    out_paths = []
    for i, f in enumerate(frames):
        path = f"/tmp/s0_{tag}_{i}.jpg"
        Image.fromarray(f).save(path, quality=85)
        out_paths.append(path)
    return out_paths


def cleanup_paths(paths):
    for p in paths:
        try:
            os.unlink(p)
        except OSError:
            pass


def load_first_n_videomme(n):
    import pyarrow.parquet as pq
    df = pq.read_table(VIDEOMME_PARQUET).to_pandas()
    df = df.sort_values("question_id").reset_index(drop=True)
    items = []
    seen_video = {}
    # First N unique videos, taking the first question per video (Q1) and
    # using a fixed shared Q2 for all of them.
    for _, row in df.iterrows():
        if row["videoID"] in seen_video:
            continue
        seen_video[row["videoID"]] = True
        items.append({
            "item_id": row["videoID"],
            "duration": row["duration"],
            "question": row["question"],
            "options": list(row["options"]),
            "answer": row["answer"],
            "question_id": row["question_id"],
        })
        if len(items) >= n:
            break
    return items


class Harness:
    def __init__(self, model_id):
        warnings.filterwarnings("ignore")
        from mlx_vlm import load
        from mlx_vlm.prompt_utils import apply_chat_template
        from mlx_vlm.generate import stream_generate, PromptCacheState
        print(f"[loader] loading {model_id} ...", flush=True)
        t0 = time.time()
        self.model, self.processor = load(model_id)
        print(f"[loader] loaded in {time.time() - t0:.1f}s", flush=True)
        self.apply_template = apply_chat_template
        self.stream_generate = stream_generate
        self.PromptCacheState = PromptCacheState
        self.model_id = model_id

    def _format_inputs(self, img_paths, question_text):
        formatted = self.apply_template(
            self.processor, self.model.config, question_text,
            num_images=len(img_paths),
            enable_thinking=False,
        )
        inputs = self.processor(
            text=[formatted], images=img_paths,
            return_tensors="np", add_special_tokens=False)
        input_ids = mx.array(inputs["input_ids"])
        pixel_values = mx.array(inputs["pixel_values"])
        mask = mx.array(inputs["attention_mask"]) if "attention_mask" in inputs else None
        return input_ids, pixel_values, mask

    def run(self, img_paths, question_text, *, prompt_cache_state=None,
            max_tokens=MAX_TOKENS):
        """Run a single forward+generate pass. Returns dict with output_text,
        token ids, first-token id, n_input_tokens, wall_time, peak_rss."""
        input_ids, pixel_values, mask = self._format_inputs(img_paths, question_text)
        n_input_tokens = int(input_ids.shape[1])
        full_input_ids_hash = hash_ids(input_ids.flatten().tolist())

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

        text_pieces = []
        token_ids = []
        first_token_id = None
        first_logprobs = None
        t0 = time.perf_counter()
        for resp in self.stream_generate(self.model, self.processor, "", **kwargs):
            if resp.text:
                text_pieces.append(resp.text)
            tok = resp.token
            try:
                tok_int = int(tok)
            except Exception:  # noqa: BLE001
                # tok may already be a python int
                tok_int = tok
            if first_token_id is None:
                first_token_id = tok_int
                # logprobs is mx.array (vocab,)
                try:
                    first_logprobs = np.array(resp.logprobs).astype(np.float32)
                except Exception:  # noqa: BLE001
                    first_logprobs = None
            token_ids.append(tok_int)
        wall = time.perf_counter() - t0
        text = "".join(text_pieces)
        out = {
            "output_text": text,
            "n_input_tokens": n_input_tokens,
            "n_output_tokens": len(token_ids),
            "first_token_id": first_token_id,
            "wall_time_s": wall,
            "peak_rss_mb": peak_rss_mb(),
            "input_ids_hash": full_input_ids_hash,
            "token_ids": token_ids,
        }
        out["_first_logprobs"] = first_logprobs  # not JSONified later, used for cosine
        return out


def cosine(a, b):
    if a is None or b is None:
        return None
    a = a.flatten().astype(np.float64)
    b = b.flatten().astype(np.float64)
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return None
    return float((a @ b) / (na * nb))


def jsonl_row(item_id, q_idx, arm, prompt_text, run_out):
    return {
        "item_id": item_id,
        "q_idx": q_idx,
        "arm": arm,
        "prompt_hash": hash_str(prompt_text),
        "input_ids_hash": run_out["input_ids_hash"],
        "output_text": run_out["output_text"],
        "n_input_tokens": run_out["n_input_tokens"],
        "n_output_tokens": run_out["n_output_tokens"],
        "first_token_id": run_out["first_token_id"],
        "wall_time_s": run_out["wall_time_s"],
        "peak_rss_mb": run_out["peak_rss_mb"],
        "token_ids": run_out["token_ids"],
        "model_id": None,  # filled by caller
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n_items", type=int, default=5)
    ap.add_argument("--n_frames", type=int, default=8)
    ap.add_argument("--smoke_one", action="store_true",
                    help="Run on n_items=1 first to validate harness")
    ap.add_argument("--model_id", default=MODEL_ID_DEFAULT)
    args = ap.parse_args()

    if args.smoke_one:
        args.n_items = 1

    items = load_first_n_videomme(args.n_items)
    print(f"[plan] {len(items)} items × 2 questions each, {args.n_frames} frames", flush=True)
    for it in items:
        print(f"  - {it['item_id']} ({it['duration']}) q1={it['question'][:60]!r}")

    # Pre-fetch frame paths for every item before loading the model so
    # ffmpeg failures surface early.
    item_frames = {}
    for it in items:
        vpath = find_videomme_video(it["item_id"])
        if not vpath:
            print(f"[warn] video missing for {it['item_id']}, skipping", flush=True)
            continue
        frames = extract_frames(vpath, n_frames=args.n_frames)
        if len(frames) < args.n_frames // 2:
            print(f"[warn] too few frames extracted for {it['item_id']}, skipping", flush=True)
            continue
        item_frames[it["item_id"]] = frames
        print(f"[frames] {it['item_id']}: extracted {len(frames)} frames")

    if not item_frames:
        raise SystemExit("No item frames extracted — aborting.")

    harness = Harness(args.model_id)

    # Stream rows to disk
    open(RESULTS_PATH, "w").close()  # truncate
    rows = []

    summary = {
        "model_id": args.model_id,
        "n_items_planned": len(items),
        "n_items_run": 0,
        "n_frames": args.n_frames,
        "max_tokens": MAX_TOKENS,
        "tests": {
            "determinism_pass": 0,
            "determinism_total": 0,
            "cache_equivalence_pass": 0,
            "cache_equivalence_total": 0,
            "followup_correctness_pass": 0,
            "followup_correctness_total": 0,
        },
        "failures": [],
        "first_token_logit_cosine": [],
    }

    def emit(arm_name, item_id, q_idx, prompt_text, run_out):
        row = jsonl_row(item_id, q_idx, arm_name, prompt_text, run_out)
        row["model_id"] = args.model_id
        rows.append(row)
        with open(RESULTS_PATH, "a") as f:
            f.write(json.dumps(row) + "\n")
        print(f"  [emit] {arm_name:<20s} item={item_id} q={q_idx} "
              f"out={run_out['output_text']!r} "
              f"n_in={run_out['n_input_tokens']} n_out={run_out['n_output_tokens']} "
              f"t={run_out['wall_time_s']:.2f}s")

    for it in items:
        item_id = it["item_id"]
        if item_id not in item_frames:
            continue
        frames = item_frames[item_id]
        frame_paths = save_frame_jpgs(frames, item_id.replace("/", "_"))
        try:
            opts_str = "\n".join(it["options"])
            q1_text = (f"Question: {it['question']}\nOptions:\n{opts_str}\n"
                       "Answer with just the letter.")
            q2_text = FOLLOWUP_Q

            for q_idx, q_text in enumerate([q1_text, q2_text]):
                # =====================
                # 1) DETERMINISM
                # =====================
                print(f"\n[item {item_id} q{q_idx}] DETERMINISM ===")
                out_a = harness.run(frame_paths, q_text)
                emit("dense_a", item_id, q_idx, q_text, out_a)
                out_a2 = harness.run(frame_paths, q_text)
                emit("dense_a_repeat", item_id, q_idx, q_text, out_a2)
                det_ok = (out_a["output_text"] == out_a2["output_text"]
                          and out_a["token_ids"] == out_a2["token_ids"])
                summary["tests"]["determinism_total"] += 1
                if det_ok:
                    summary["tests"]["determinism_pass"] += 1
                else:
                    summary["failures"].append({
                        "test": "determinism", "item": item_id, "q_idx": q_idx,
                        "a_text": out_a["output_text"], "a2_text": out_a2["output_text"],
                    })
                print(f"  determinism={'PASS' if det_ok else 'FAIL'}")

                # =====================
                # 2) CACHE-EQUIVALENCE: dense vs cached_cold
                # =====================
                print(f"[item {item_id} q{q_idx}] CACHE-EQUIVALENCE ===")
                fresh_state = harness.PromptCacheState()
                out_b = harness.run(frame_paths, q_text, prompt_cache_state=fresh_state)
                emit("cached_cold", item_id, q_idx, q_text, out_b)
                cache_eq_ok = (out_a["output_text"] == out_b["output_text"]
                               and out_a["token_ids"] == out_b["token_ids"])
                summary["tests"]["cache_equivalence_total"] += 1
                if cache_eq_ok:
                    summary["tests"]["cache_equivalence_pass"] += 1
                else:
                    summary["failures"].append({
                        "test": "cache_equivalence", "item": item_id, "q_idx": q_idx,
                        "dense_text": out_a["output_text"],
                        "cached_text": out_b["output_text"],
                        "dense_tokens": out_a["token_ids"],
                        "cached_tokens": out_b["token_ids"],
                    })
                if out_a.get("_first_logprobs") is not None and out_b.get("_first_logprobs") is not None:
                    cos = cosine(out_a["_first_logprobs"], out_b["_first_logprobs"])
                    summary["first_token_logit_cosine"].append({
                        "item": item_id, "q_idx": q_idx, "arm_pair": "dense_vs_cached_cold",
                        "cosine": cos,
                    })
                print(f"  cache_equivalence={'PASS' if cache_eq_ok else 'FAIL'}")

                # Save the post-Q1 cache for the follow-up test (only for q_idx==0)
                if q_idx == 0:
                    persist_state_after_q1 = fresh_state  # already updated by stream_generate
                    persist_q1_text = q_text

            # =====================
            # 3) FOLLOW-UP CORRECTNESS (uses Q1 cache built above)
            # =====================
            # Warm: feed persist_state_after_q1 → ask Q2 (cache should reuse Q1 prefix)
            print(f"\n[item {item_id}] FOLLOW-UP CORRECTNESS ===")
            warm_q2_text = FOLLOWUP_Q
            warm = harness.run(frame_paths, warm_q2_text,
                               prompt_cache_state=persist_state_after_q1)
            emit("warm_followup", item_id, "q2_warm", warm_q2_text, warm)

            # Cold: independent dense run of Q2 alone (no carryover cache)
            cold = harness.run(frame_paths, warm_q2_text)
            emit("cold_followup", item_id, "q2_cold", warm_q2_text, cold)

            fu_ok = (warm["output_text"] == cold["output_text"]
                     and warm["token_ids"] == cold["token_ids"])
            summary["tests"]["followup_correctness_total"] += 1
            if fu_ok:
                summary["tests"]["followup_correctness_pass"] += 1
            else:
                summary["failures"].append({
                    "test": "followup_correctness", "item": item_id,
                    "warm_text": warm["output_text"],
                    "cold_text": cold["output_text"],
                    "warm_tokens": warm["token_ids"],
                    "cold_tokens": cold["token_ids"],
                })
            print(f"  followup_correctness={'PASS' if fu_ok else 'FAIL'}")
            summary["n_items_run"] += 1
        finally:
            cleanup_paths(frame_paths)
            mx.clear_cache()
            gc.collect()

    # write summary
    with open(SUMMARY_PATH, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\n[done] results → {RESULTS_PATH}")
    print(f"[done] summary → {SUMMARY_PATH}")
    print(json.dumps(summary["tests"], indent=2))
    print(f"failures: {len(summary['failures'])}")


if __name__ == "__main__":
    main()
