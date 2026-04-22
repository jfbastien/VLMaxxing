"""1.29 follow-up pilot: continuous codec-score + planner-style rethresholding.

Follows the hard falsification in 2026-04-22-phase-1_29-codec-native-short-bucket-pilot-findings.md.
Tests redesign option (2): replace MAX-over-span of labels with a continuous
codec-score aggregated over the native-rate span, then rethreshold to classes
using quantile-calibrated planner thresholds.

Continuous codec-score per MB position per sparse-pair-span:
    f_novel_coded = (# native frames at that MB with intra_flag OR cbf) / span_len

Resample MB-grid → 28px token grid by MEAN (keeping signal continuous).
Calibrate global thresholds (static_t, shifted_t) to match the 1.57 8f
dev30 aggregate class distribution (STATIC 0.436 / SHIFTED 0.026 / NOVEL 0.538).
Apply thresholds per token block per pair; measure per-item class shares and
per-item |Δ| vs 1.57 pixel-diff reference.

Gate: same as the hard-falsification pilot — max |Δ| < 0.10 per class on
mean across n=5.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from codec_through.codec.h264_metadata import H264MetadataExtractor  # noqa: E402
from codec_through.video_decode import _count_frames  # noqa: E402

QWEN_TOKEN_BLOCK = 28
PILOT_ITEMS = [
    "videomme:short:037-2",
    "videomme:short:210-2",
    "videomme:short:282-2",
    "videomme:short:120-2",
    "videomme:short:158-3",
]

# 1.57 pixel-diff 8f dev30 aggregate class distribution (sum over 30 items)
PIX_AGG_STATIC = 0.436
PIX_AGG_SHIFTED = 0.026
PIX_AGG_NOVEL = 0.538


def pick_video(item_id: str, df: pd.DataFrame) -> str | None:
    _, _grp, suffix = item_id.split(":")
    row = df[df["question_id"].astype(str) == suffix]
    if len(row) == 0:
        return None
    return row.iloc[0]["videoID"]


def resample_mean(
    src: np.ndarray,
    src_px: int,
    dst_px: int,
    height: int,
    width: int,
) -> np.ndarray:
    """Resample continuous src-grid (srcH × srcW) to dst-grid by area-mean.

    Counterpart to `_resample_majority_conservative` but for continuous signals.
    """
    dst_h = height // dst_px
    dst_w = width // dst_px
    out = np.zeros((dst_h, dst_w), dtype=np.float32)
    for di in range(dst_h):
        for dj in range(dst_w):
            y0 = di * dst_px
            y1 = (di + 1) * dst_px
            x0 = dj * dst_px
            x1 = (dj + 1) * dst_px
            si0 = y0 // src_px
            si1 = min((y1 + src_px - 1) // src_px, src.shape[0])
            sj0 = x0 // src_px
            sj1 = min((x1 + src_px - 1) // src_px, src.shape[1])
            if si1 > si0 and sj1 > sj0:
                out[di, dj] = src[si0:si1, sj0:sj1].mean()
    return out


def main() -> None:
    with open("research/experiments/2026/artifacts/phase1_57/qwen_8f_dev30.json") as f:
        ref = {it["item_id"]: it for it in json.load(f)["per_item"]}
    df = pd.read_parquet("data/benchmarks/videomme/hf/videomme/test-00000-of-00001.parquet")

    # Pass 1: compute continuous codec scores per pair per token block
    # for all pilot items. Accumulate pooled scores to calibrate thresholds.
    all_scores: list[np.ndarray] = []
    per_item_scores: dict[str, list[np.ndarray]] = {}
    per_item_meta: list[dict] = []

    for iid in PILOT_ITEMS:
        if iid not in ref:
            continue
        vid = pick_video(iid, df)
        if vid is None:
            continue
        cand = list(Path("data/benchmarks/videomme/videos").glob(f"{vid}.*"))
        if not cand:
            continue
        vpath = cand[0]

        total = _count_frames(vpath, start_seconds=None, end_seconds=None)
        idxs = np.linspace(0, total - 1, 8, dtype=int).tolist()

        t0 = time.time()
        ext = H264MetadataExtractor(str(vpath), max_frames=idxs[-1] + 1)
        per_frame_novel_flag = []  # list of (MB_H, MB_W) bool arrays
        for fm in ext.iter_frames():
            mbs = fm.macroblocks
            novel = mbs["intra_flag"] | mbs["cbf"]
            per_frame_novel_flag.append(novel)
        extract_s = time.time() - t0

        scores_per_pair: list[np.ndarray] = []
        for k in range(1, len(idxs)):
            lo, hi = idxs[k - 1] + 1, idxs[k]
            if lo > hi:
                lo = hi
            stk = np.stack(per_frame_novel_flag[lo : hi + 1], axis=0).astype(np.float32)
            f_novel = stk.mean(axis=0)  # (MB_H, MB_W) in [0, 1]
            tok = resample_mean(
                f_novel,
                src_px=ext.mb_size,
                dst_px=QWEN_TOKEN_BLOCK,
                height=ext.height,
                width=ext.width,
            )
            scores_per_pair.append(tok)
            all_scores.append(tok.ravel())
        per_item_scores[iid] = scores_per_pair
        per_item_meta.append(
            {"item_id": iid, "total_frames": int(total), "extract_s": round(extract_s, 2)}
        )

    if not all_scores:
        print("No items completed — exit")
        return

    # Calibrate thresholds to match pixel-diff aggregate on pooled scores.
    # static_t: codec score below = STATIC. shifted_t: codec score between
    # static_t and shifted_t = SHIFTED, codec score above = NOVEL.
    pooled = np.concatenate(all_scores)
    static_t = float(np.quantile(pooled, PIX_AGG_STATIC))
    shifted_t = float(np.quantile(pooled, PIX_AGG_STATIC + PIX_AGG_SHIFTED))
    print(
        f"pooled score stats: min={pooled.min():.3f} p10={np.quantile(pooled, 0.10):.3f} "
        f"p43.6={static_t:.3f} p46.2={shifted_t:.3f} "
        f"p90={np.quantile(pooled, 0.90):.3f} max={pooled.max():.3f}"
    )
    print(
        f"calibrated thresholds (to match pixel-diff aggregate dist "
        f"S/X/N={PIX_AGG_STATIC:.3f}/{PIX_AGG_SHIFTED:.3f}/{PIX_AGG_NOVEL:.3f}): "
        f"static_t={static_t:.3f} shifted_t={shifted_t:.3f}"
    )
    print()

    # Pass 2: apply thresholds, compute per-item class shares, compare to 1.57.
    out = {
        "pilot_items": PILOT_ITEMS,
        "static_t": static_t,
        "shifted_t": shifted_t,
        "per_item": [],
    }
    rows = []
    for iid, scores_per_pair in per_item_scores.items():
        ref_it = ref[iid]
        meta = next(m for m in per_item_meta if m["item_id"] == iid)

        codec_total = np.zeros(3, dtype=np.int64)  # [STATIC, SHIFTED, NOVEL]
        for tok in scores_per_pair:
            s = tok.ravel()
            codec_total[0] += int((s < static_t).sum())
            codec_total[1] += int(((s >= static_t) & (s < shifted_t)).sum())
            codec_total[2] += int((s >= shifted_t).sum())
        codec_share = codec_total / codec_total.sum()

        cc = ref_it["class_counts"]
        pix_total = np.array([cc["static"], cc["shifted"], cc["novel"]])
        pix_share = pix_total / pix_total.sum()

        delta = codec_share - pix_share
        out["per_item"].append(
            {
                "item_id": iid,
                "total_frames": meta["total_frames"],
                "extract_s": meta["extract_s"],
                "pix_share": {
                    "STATIC": float(pix_share[0]),
                    "SHIFTED": float(pix_share[1]),
                    "NOVEL": float(pix_share[2]),
                },
                "codec_share": {
                    "STATIC": float(codec_share[0]),
                    "SHIFTED": float(codec_share[1]),
                    "NOVEL": float(codec_share[2]),
                },
                "delta": {
                    "STATIC": float(delta[0]),
                    "SHIFTED": float(delta[1]),
                    "NOVEL": float(delta[2]),
                },
            }
        )
        rows.append({"pix": pix_share, "codec": codec_share})
        print(
            f"{iid:24s} pix S/X/N={pix_share[0]:.3f}/{pix_share[1]:.3f}/{pix_share[2]:.3f}  "
            f"codec S/X/N={codec_share[0]:.3f}/{codec_share[1]:.3f}/{codec_share[2]:.3f}  "
            f"Δ={delta[0]:+.3f}/{delta[1]:+.3f}/{delta[2]:+.3f}"
        )

    if rows:
        pix_mean = np.mean([r["pix"] for r in rows], axis=0)
        codec_mean = np.mean([r["codec"] for r in rows], axis=0)
        agg_delta = codec_mean - pix_mean
        out["aggregate"] = {
            "n_items": len(rows),
            "pix_mean": {
                "STATIC": float(pix_mean[0]),
                "SHIFTED": float(pix_mean[1]),
                "NOVEL": float(pix_mean[2]),
            },
            "codec_mean": {
                "STATIC": float(codec_mean[0]),
                "SHIFTED": float(codec_mean[1]),
                "NOVEL": float(codec_mean[2]),
            },
            "delta_mean": {
                "STATIC": float(agg_delta[0]),
                "SHIFTED": float(agg_delta[1]),
                "NOVEL": float(agg_delta[2]),
            },
            "max_abs_delta": float(np.abs(agg_delta).max()),
        }

        # Rank correlation across items (STATIC share — the most semantically
        # loaded class). If the codec signal preserves item-level ordering
        # of how-static-the-clip-is, it is usable as a continuous signal.
        # Spearman via numpy rankdata (avoid scipy dep)
        pix_static = np.array([r["pix"][0] for r in rows])
        codec_static = np.array([r["codec"][0] for r in rows])
        pix_ranks = np.argsort(np.argsort(pix_static)).astype(np.float64)
        codec_ranks = np.argsort(np.argsort(codec_static)).astype(np.float64)
        if pix_ranks.std() > 0 and codec_ranks.std() > 0:
            rho = float(np.corrcoef(pix_ranks, codec_ranks)[0, 1])
        else:
            rho = float("nan")
        out["aggregate"]["spearman_static"] = {"rho": rho, "n": len(rows)}

        print(
            f"\nAGGREGATE (n={len(rows)}): "
            f"pix mean S/X/N={pix_mean[0]:.3f}/{pix_mean[1]:.3f}/{pix_mean[2]:.3f}  "
            f"codec mean S/X/N={codec_mean[0]:.3f}/{codec_mean[1]:.3f}/{codec_mean[2]:.3f}  "
            f"Δ={agg_delta[0]:+.3f}/{agg_delta[1]:+.3f}/{agg_delta[2]:+.3f}  "
            f"max|Δ|={np.abs(agg_delta).max():.3f}"
        )
        print(f"Spearman(pix_STATIC_share, codec_STATIC_share) ρ={rho:+.3f} (n={len(rows)})")
        print(
            "GATE (10pp max|Δ|): "
            + ("PROCEED" if np.abs(agg_delta).max() < 0.10 else "STILL FAILS")
        )

    out_path = Path("research/experiments/2026/artifacts/phase1_29_continuous_codec_score_pilot")
    out_path.mkdir(parents=True, exist_ok=True)
    (out_path / "summary.json").write_text(json.dumps(out, indent=2))
    print(f"\nWrote: {out_path / 'summary.json'}")


if __name__ == "__main__":
    main()
