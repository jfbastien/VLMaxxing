"""Short-bucket pilot for 1.29 codec-native vs pixel-diff agreement.

Runs native-rate H.264 metadata extract on 5 short-bucket VideoMME items,
OR-aggregates MB labels across the native-rate span between each pair of
sparse-sampled 8 frames, resamples to Qwen token geometry (28px), then
compares the resulting STATIC/SHIFTED/NOVEL class shares against the
1.57 artifact pixel-diff reference for the same items.

Gate: if max |Δ| per class < 10pp on mean (averaged over 5 items, weighted
by pair-count), proceed with 1.29 Stages A/B/C integration.
Otherwise: redesign the codec-vs-pixel mapping (or change from label-pass
to continuous-score-then-rethreshold).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from codec_through.codec.h264_metadata import (  # noqa: E402
    NOVEL,
    SHIFTED,
    STATIC,
    H264MetadataExtractor,
    _resample_majority_conservative,
    classify_blocks_h264,
)
from codec_through.video_decode import _count_frames  # noqa: E402

QWEN_TOKEN_BLOCK = 28
PILOT_ITEMS = [
    "videomme:short:037-2",
    "videomme:short:210-2",
    "videomme:short:282-2",
    "videomme:short:120-2",
    "videomme:short:158-3",
]


def pick_video(item_id: str, df: pd.DataFrame) -> str | None:
    _, _grp, suffix = item_id.split(":")
    row = df[df["question_id"].astype(str) == suffix]
    if len(row) == 0:
        return None
    return row.iloc[0]["videoID"]


def main() -> None:
    ref = {
        it["item_id"]: it
        for it in json.load(
            open("research/experiments/2026/artifacts/phase1_57/qwen_8f_dev30.json")
        )["per_item"]
    }
    df = pd.read_parquet("data/benchmarks/videomme/hf/videomme/test-00000-of-00001.parquet")

    rows: list[dict[str, object]] = []
    out = {"pilot_items": PILOT_ITEMS, "per_item": [], "aggregate": None}
    for iid in PILOT_ITEMS:
        if iid not in ref:
            print(f"{iid}: NOT IN REFERENCE (skip)")
            continue
        ref_it = ref[iid]
        vid = pick_video(iid, df)
        if vid is None:
            print(f"{iid}: no videoID match in parquet (skip)")
            continue
        cand = list(Path("data/benchmarks/videomme/videos").glob(f"{vid}.*"))
        if not cand:
            print(f"{iid}: video file missing for {vid} (skip)")
            continue
        vpath = cand[0]
        t0 = time.time()
        total = _count_frames(vpath, start_seconds=None, end_seconds=None)
        count_s = time.time() - t0
        idxs = np.linspace(0, total - 1, 8, dtype=int).tolist()

        t0 = time.time()
        ext = H264MetadataExtractor(str(vpath), max_frames=idxs[-1] + 1)
        labels_per_frame = []
        for fm in ext.iter_frames():
            labels_per_frame.append(classify_blocks_h264(fm, token_block=ext.mb_size))
        extract_s = time.time() - t0

        # OR-aggregate across each sparse-pair span: pair k covers frames
        # idxs[k-1]+1 .. idxs[k] inclusive. MAX over that range with
        # NOVEL(2) > SHIFTED(1) > STATIC(0).
        pair_counts = []
        for k in range(1, len(idxs)):
            lo, hi = idxs[k - 1] + 1, idxs[k]
            if lo > hi:
                lo = hi
            stk = np.stack(labels_per_frame[lo : hi + 1], axis=0)
            agg_mb = stk.max(axis=0)
            tok = _resample_majority_conservative(
                agg_mb,
                src_px=ext.mb_size,
                dst_px=QWEN_TOKEN_BLOCK,
                height=ext.height,
                width=ext.width,
            )
            c = np.bincount(tok.ravel(), minlength=3)
            pair_counts.append(c)

        codec_total = np.sum(pair_counts, axis=0)
        codec_share = codec_total / codec_total.sum()
        cc = ref_it["class_counts"]
        pix_total = np.array([cc["static"], cc["shifted"], cc["novel"]])
        pix_share = pix_total / pix_total.sum()

        delta = codec_share - pix_share
        out["per_item"].append(
            {
                "item_id": iid,
                "total_frames": int(total),
                "count_frames_s": round(count_s, 2),
                "extract_s": round(extract_s, 2),
                "pix_share": {"STATIC": float(pix_share[STATIC]), "SHIFTED": float(pix_share[SHIFTED]), "NOVEL": float(pix_share[NOVEL])},
                "codec_share": {"STATIC": float(codec_share[STATIC]), "SHIFTED": float(codec_share[SHIFTED]), "NOVEL": float(codec_share[NOVEL])},
                "delta": {"STATIC": float(delta[STATIC]), "SHIFTED": float(delta[SHIFTED]), "NOVEL": float(delta[NOVEL])},
            }
        )
        rows.append({"pix": pix_share, "codec": codec_share})
        print(
            f"{iid:24s} fr={total:5d} count={count_s:5.1f}s ext={extract_s:5.1f}s  "
            f"pix S/X/N={pix_share[STATIC]:.3f}/{pix_share[SHIFTED]:.3f}/{pix_share[NOVEL]:.3f}  "
            f"codec S/X/N={codec_share[STATIC]:.3f}/{codec_share[SHIFTED]:.3f}/{codec_share[NOVEL]:.3f}  "
            f"Δ={delta[STATIC]:+.3f}/{delta[SHIFTED]:+.3f}/{delta[NOVEL]:+.3f}"
        )

    if rows:
        pix_mean = np.mean([r["pix"] for r in rows], axis=0)
        codec_mean = np.mean([r["codec"] for r in rows], axis=0)
        agg_delta = codec_mean - pix_mean
        out["aggregate"] = {
            "n_items": len(rows),
            "pix_mean": {"STATIC": float(pix_mean[STATIC]), "SHIFTED": float(pix_mean[SHIFTED]), "NOVEL": float(pix_mean[NOVEL])},
            "codec_mean": {"STATIC": float(codec_mean[STATIC]), "SHIFTED": float(codec_mean[SHIFTED]), "NOVEL": float(codec_mean[NOVEL])},
            "delta_mean": {"STATIC": float(agg_delta[STATIC]), "SHIFTED": float(agg_delta[SHIFTED]), "NOVEL": float(agg_delta[NOVEL])},
            "max_abs_delta": float(np.abs(agg_delta).max()),
        }
        print(
            "\nAGGREGATE (n={}): pix mean S/X/N={:.3f}/{:.3f}/{:.3f}  codec mean S/X/N={:.3f}/{:.3f}/{:.3f}  Δ={:+.3f}/{:+.3f}/{:+.3f}  max|Δ|={:.3f}".format(
                len(rows),
                pix_mean[STATIC], pix_mean[SHIFTED], pix_mean[NOVEL],
                codec_mean[STATIC], codec_mean[SHIFTED], codec_mean[NOVEL],
                agg_delta[STATIC], agg_delta[SHIFTED], agg_delta[NOVEL],
                np.abs(agg_delta).max(),
            )
        )
        print(
            "GATE: 10pp max|Δ| threshold → "
            + ("PROCEED with 1.29 Stages A/B/C" if np.abs(agg_delta).max() < 0.10 else "REDESIGN codec→class mapping")
        )

    out_path = Path("research/experiments/2026/artifacts/phase1_29_short_bucket_pilot")
    out_path.mkdir(parents=True, exist_ok=True)
    (out_path / "summary.json").write_text(json.dumps(out, indent=2))
    print(f"\nWrote: {out_path / 'summary.json'}")


if __name__ == "__main__":
    main()
