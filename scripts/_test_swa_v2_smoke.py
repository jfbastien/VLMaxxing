#!/usr/bin/env python3
"""Quick smoke test: does the prefix-snapshot approach produce
byte-identical output to cold dense on N=1 video?

Imports the existing B0b harness (just for the format_inputs / harness
plumbing) and then runs:
  - cold_dense (full prefill)
  - prefix_snapshot path (warm prefix + per-turn prefill of just the
    question tokens)

Compares output text + measures wall-clock.
"""

from __future__ import annotations

import os
import sys
import time
import warnings
from pathlib import Path

if not os.environ.get("HF_TOKEN"):
    raise SystemExit("HF_TOKEN required.")

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# Reuse harness from the B0b runner.
sys.path.insert(0, str(SCRIPTS))
from run_sam_b0b_cache_correctness import (  # noqa: E402
    MODEL_ID_DEFAULT,
    VIDEOMME_DIR_DEFAULT,
    Harness,
    cleanup_paths,
    extract_frames,
    find_videomme_video,
    save_frame_jpgs,
)
from swa_aware_cache_v2 import (  # noqa: E402
    make_prefix_snapshot,
    run_turn_with_snapshot,
)

QUESTION = "What color is most prominent in the scene?"
SETUP_QUESTION = "Briefly describe what you see."


def main() -> int:
    warnings.filterwarnings("ignore")

    # Pick first VideoMME video.
    import pyarrow.parquet as pq

    parquet = VIDEOMME_DIR_DEFAULT / "videomme/test-00000-of-00001.parquet"
    df = pq.read_table(parquet).to_pandas().sort_values("question_id").reset_index(drop=True)
    video_id = str(df.iloc[0]["videoID"])
    video_path = find_videomme_video(video_id, VIDEOMME_DIR_DEFAULT)
    if not video_path:
        raise SystemExit(f"video missing: {video_id}")
    print(f"[setup] video={video_id}")
    frames, ts = extract_frames(video_path, n_frames=8)
    paths = save_frame_jpgs(frames, video_id)

    h = Harness(MODEL_ID_DEFAULT)
    print(f"[topology] {h.cache_topology}")

    # Arm 1: cold dense
    print("\n[cold_dense]")
    t0 = time.perf_counter()
    cold = h.run(paths, QUESTION, max_tokens=32)
    cold_ms = (time.perf_counter() - t0) * 1000.0
    print(f"  output: {cold['output_text']!r}")
    print(f"  wall: {cold_ms:.0f} ms ({cold['n_input_tokens']} input tokens)")

    # Arm 2: prefix snapshot
    print("\n[prefix_snapshot] building snapshot...")
    snapshot = make_prefix_snapshot(h, paths)
    print(f"  n_prefix_tokens={snapshot['n_prefix_tokens']} warm_ms={snapshot['warm_ms']:.0f}")

    print("\n[prefix_snapshot] running turn 1 (Q1) ...")
    snap_run = run_turn_with_snapshot(snapshot, h, paths, QUESTION, max_tokens=32)
    print(f"  output: {snap_run['output_text']!r}")
    print(
        f"  wall: {snap_run['wall_ms']:.0f} ms "
        f"({snap_run['n_new_tokens_prefilled']} new tokens prefilled, "
        f"prefill_ms={snap_run['prefill_ms']:.0f})"
    )

    print("\n[prefix_snapshot] running turn 2 (same Q again, fresh restore) ...")
    snap_run2 = run_turn_with_snapshot(snapshot, h, paths, QUESTION, max_tokens=32)
    print(f"  output: {snap_run2['output_text']!r}")
    print(
        f"  wall: {snap_run2['wall_ms']:.0f} ms "
        f"({snap_run2['n_new_tokens_prefilled']} new tokens prefilled)"
    )

    # Comparisons
    byte_id_t1 = cold["output_text"] == snap_run["output_text"]
    byte_id_t2 = cold["output_text"] == snap_run2["output_text"]
    snap_t1_speedup = cold_ms / max(snap_run["wall_ms"], 1)
    snap_t2_speedup = cold_ms / max(snap_run2["wall_ms"], 1)
    print("\n=== summary ===")
    print(f"  cold       : {cold['output_text']!r} ({cold_ms:.0f} ms)")
    print(f"  snapshot t1: byte-id={byte_id_t1} speedup={snap_t1_speedup:.2f}x")
    print(f"  snapshot t2: byte-id={byte_id_t2} speedup={snap_t2_speedup:.2f}x")

    cleanup_paths(paths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
