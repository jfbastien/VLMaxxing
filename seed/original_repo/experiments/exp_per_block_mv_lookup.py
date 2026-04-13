"""Experiment: Per-block MV-compensated embedding cache lookup on real video.

Tasks:
1. Extract real per-macroblock MVs from H.264 via PyAV flags2 export
2. Classify blocks as STATIC/SHIFTED/NOVEL using MVs + residual energy proxy
3. MV magnitude analysis (distribution, token-boundary crossings)
4. Per-block lookup index computation (source token mapping)
5. Residual energy as CBF proxy (motion-compensated prediction error)
"""

import json
from pathlib import Path
from collections import defaultdict

import av
import numpy as np


PTYPE_MAP = {1: 'I', 2: 'P', 3: 'B'}


# ── 1. MV Extraction ────────────────────────────────────────────────────

def extract_mvs_and_frames(video_path: str, max_frames: int = 150):
    """Extract per-macroblock MVs and decoded frames from H.264 video.

    Returns:
        mv_by_frame: dict[int, np.ndarray] — structured MV arrays keyed by frame index
        frames_y: list[np.ndarray] — Y-plane for each frame (H, W)
        frame_types: list[str] — 'I', 'P', 'B' per frame
        width, height: int — frame dimensions
    """
    container = av.open(video_path)
    stream = container.streams.video[0]

    # Enable MV export: flags2 |= (1 << 28)  — AV_CODEC_FLAG2_EXPORT_MVS
    stream.codec_context.flags2 |= (1 << 28)

    mv_by_frame = {}
    frames_y = []
    frame_types = []
    frame_idx = 0

    for frame in container.decode(stream):
        if frame_idx >= max_frames:
            break

        # Extract Y-plane
        y_plane = frame.to_ndarray(format='gray')
        frames_y.append(y_plane)

        # Frame type (pict_type is an int in PyAV 17: 1=I, 2=P, 3=B)
        ft = PTYPE_MAP.get(frame.pict_type, '?')
        frame_types.append(ft)

        # Extract MVs from side_data — iterate to find MotionVectors
        mv_array = None
        if frame.side_data:
            for sd_item in frame.side_data:
                if hasattr(sd_item, 'to_ndarray'):
                    mv_array = sd_item.to_ndarray()
                    break

        mv_by_frame[frame_idx] = mv_array  # None for I-frames
        frame_idx += 1

    container.close()
    h, w = frames_y[0].shape if frames_y else (0, 0)
    return mv_by_frame, frames_y, frame_types, w, h


# ── 2. MV Statistics ────────────────────────────────────────────────────

def compute_mv_statistics(mv_by_frame, frame_types, width, height, mb_size=16):
    """Compute MV magnitude statistics across all P/B-frames."""
    all_magnitudes = []
    per_frame_stats = []

    for fidx, mv_arr in mv_by_frame.items():
        ft = frame_types[fidx]
        if ft == 'I' or mv_arr is None or len(mv_arr) == 0:
            continue

        # Forward MVs only (source == -1)
        fwd_mask = mv_arr['source'] == -1
        fwd = mv_arr[fwd_mask] if fwd_mask.any() else mv_arr

        scale = fwd['motion_scale'].astype(np.float64)
        scale[scale == 0] = 1
        dx = fwd['motion_x'].astype(np.float64) / scale
        dy = fwd['motion_y'].astype(np.float64) / scale
        mags = np.sqrt(dx**2 + dy**2)

        all_magnitudes.append(mags)
        n = len(fwd)
        per_frame_stats.append({
            'frame': fidx,
            'type': ft,
            'n_mvs': n,
            'zero_pct': float((mags < 0.5).sum() / n),
            'cross14_pct': float((mags > 14).sum() / n),
            'cross28_pct': float((mags > 28).sum() / n),
            'median_mag': float(np.median(mags)),
            'mean_mag': float(np.mean(mags)),
            'p95_mag': float(np.percentile(mags, 95)),
            'max_mag': float(np.max(mags)),
        })

    if all_magnitudes:
        all_mags = np.concatenate(all_magnitudes)
    else:
        all_mags = np.array([0.0])

    total = len(all_mags)
    return {
        'total_mvs': total,
        'zero_mv_pct': float((all_mags < 0.5).sum() / total),
        'cross14_pct': float((all_mags > 14).sum() / total),
        'cross28_pct': float((all_mags > 28).sum() / total),
        'magnitude_median': float(np.median(all_mags)),
        'magnitude_mean': float(np.mean(all_mags)),
        'magnitude_p95': float(np.percentile(all_mags, 95)),
        'magnitude_max': float(np.max(all_mags)),
        'per_frame': per_frame_stats,
    }


# ── Helper: Build per-MB MV map ────────────────────────────────────────

def build_mb_mv_map(mv_arr, mb_size, mb_h, mb_w):
    """Build per-macroblock MV map from forward MVs.

    Returns dict: (mb_row, mb_col) -> (avg_dx_px, avg_dy_px, mv_magnitude)
    """
    if mv_arr is None or len(mv_arr) == 0:
        return {}

    fwd_mask = mv_arr['source'] == -1
    fwd = mv_arr[fwd_mask] if fwd_mask.any() else mv_arr

    scale = fwd['motion_scale'].astype(np.float64)
    scale[scale == 0] = 1
    dx = fwd['motion_x'].astype(np.float64) / scale
    dy = fwd['motion_y'].astype(np.float64) / scale

    mb_cols = fwd['dst_x'].astype(np.int32) // mb_size
    mb_rows = fwd['dst_y'].astype(np.int32) // mb_size

    # Aggregate per-MB (average sub-block MVs)
    accum = defaultdict(lambda: [[], []])
    for i in range(len(fwd)):
        r, c = int(mb_rows[i]), int(mb_cols[i])
        if 0 <= r < mb_h and 0 <= c < mb_w:
            accum[(r, c)][0].append(dx[i])
            accum[(r, c)][1].append(dy[i])

    mv_map = {}
    for key, (dxs, dys) in accum.items():
        adx = np.mean(dxs)
        ady = np.mean(dys)
        mv_map[key] = (adx, ady, np.sqrt(adx**2 + ady**2))
    return mv_map


# ── 3. Residual Energy as CBF Proxy + Classification ───────────────────

def compute_residual_classification(mv_by_frame, frames_y, frame_types,
                                    width, height, mb_size=16, threshold=3.0):
    """Classify MBs using MV + motion-compensated residual energy.

    STATIC: |MV| < 0.5 AND residual < threshold
    SHIFTED: |MV| >= 0.5 AND residual < threshold
    NOVEL: residual >= threshold OR intra-coded
    """
    mb_w = width // mb_size
    mb_h = height // mb_size
    per_frame = []

    for fidx, mv_arr in mv_by_frame.items():
        ft = frame_types[fidx]
        if ft == 'I' or fidx == 0:
            continue

        current = frames_y[fidx].astype(np.float32)
        prev = frames_y[fidx - 1].astype(np.float32)

        mv_map = build_mb_mv_map(mv_arr, mb_size, mb_h, mb_w)

        n_static = 0
        n_shifted = 0
        n_novel = 0
        n_intra = 0

        for mr in range(mb_h):
            for mc in range(mb_w):
                y0, x0 = mr * mb_size, mc * mb_size
                current_block = current[y0:y0+mb_size, x0:x0+mb_size]

                if (mr, mc) not in mv_map:
                    n_intra += 1
                    n_novel += 1
                    continue

                adx, ady, mag = mv_map[(mr, mc)]
                src_x = max(0, min(x0 + round(adx), width - mb_size))
                src_y = max(0, min(y0 + round(ady), height - mb_size))
                pred_block = prev[src_y:src_y+mb_size, src_x:src_x+mb_size]
                residual = np.mean(np.abs(current_block - pred_block))

                if residual < threshold:
                    if mag < 0.5:
                        n_static += 1
                    else:
                        n_shifted += 1
                else:
                    n_novel += 1

        total = mb_h * mb_w
        per_frame.append({
            'frame': fidx, 'type': ft, 'total_mbs': total,
            'static': n_static, 'shifted': n_shifted,
            'novel': n_novel, 'intra': n_intra,
            'static_pct': n_static / total,
            'shifted_pct': n_shifted / total,
            'novel_pct': n_novel / total,
        })

    return per_frame


# ── 4. Compare MV-based vs pixel-diff classification ───────────────────

def compare_mv_vs_pixeldiff(mv_by_frame, frames_y, frame_types, width, height,
                            mb_size=16, static_thresh=3.0, shift_thresh=8.0,
                            residual_thresh=3.0):
    """Compare MV+residual classification against naive pixel-diff."""
    mb_w = width // mb_size
    mb_h = height // mb_size

    agree = 0
    disagree = 0
    total = 0
    confusion = defaultdict(int)

    for fidx, mv_arr in mv_by_frame.items():
        ft = frame_types[fidx]
        if ft == 'I' or fidx == 0:
            continue

        current = frames_y[fidx].astype(np.float32)
        prev = frames_y[fidx - 1].astype(np.float32)
        mv_map = build_mb_mv_map(mv_arr, mb_size, mb_h, mb_w)

        for mr in range(mb_h):
            for mc in range(mb_w):
                y0, x0 = mr * mb_size, mc * mb_size
                current_block = current[y0:y0+mb_size, x0:x0+mb_size]
                prev_block = prev[y0:y0+mb_size, x0:x0+mb_size]

                # Pixel-diff classification
                pd_diff = np.mean(np.abs(current_block - prev_block))
                if pd_diff < static_thresh:
                    pd_class = 'STATIC'
                elif pd_diff < shift_thresh:
                    pd_class = 'SHIFTED'
                else:
                    pd_class = 'NOVEL'

                # MV-based classification
                if (mr, mc) not in mv_map:
                    mv_class = 'NOVEL'
                else:
                    adx, ady, mag = mv_map[(mr, mc)]
                    src_x = max(0, min(x0 + round(adx), width - mb_size))
                    src_y = max(0, min(y0 + round(ady), height - mb_size))
                    pred_block = prev[src_y:src_y+mb_size, src_x:src_x+mb_size]
                    mc_res = np.mean(np.abs(current_block - pred_block))

                    if mc_res < residual_thresh:
                        mv_class = 'STATIC' if mag < 0.5 else 'SHIFTED'
                    else:
                        mv_class = 'NOVEL'

                total += 1
                if mv_class == pd_class:
                    agree += 1
                else:
                    disagree += 1
                confusion[(mv_class, pd_class)] += 1

    return {
        'total_mbs': total,
        'agree': agree, 'disagree': disagree,
        'agree_pct': agree / total if total > 0 else 0,
        'confusion': {f'{k[0]}_vs_{k[1]}': v for k, v in sorted(confusion.items())},
    }


# ── 5. Per-block Lookup Index Computation ───────────────────────────────

def compute_lookup_indices(mv_by_frame, frames_y, frame_types, width, height,
                           mb_size=16, token_size=28, residual_threshold=3.0):
    """Compute source token index for each MB via its MV."""
    token_h = height // token_size
    token_w = width // token_size
    mb_w = width // mb_size
    mb_h = height // mb_size

    total_lookups = 0
    in_bounds = 0
    out_bounds = 0
    zero_offset = 0
    nonzero_offset = 0
    per_frame = []

    for fidx, mv_arr in mv_by_frame.items():
        ft = frame_types[fidx]
        if ft == 'I' or fidx == 0:
            continue

        mv_map = build_mb_mv_map(mv_arr, mb_size, mb_h, mb_w)
        current = frames_y[fidx].astype(np.float32)
        prev = frames_y[fidx - 1].astype(np.float32)

        f_in = f_out = f_same = f_diff = f_cache = 0

        for mr in range(mb_h):
            for mc in range(mb_w):
                if (mr, mc) not in mv_map:
                    continue

                adx, ady, mag = mv_map[(mr, mc)]
                cur_tok_h = (mr * mb_size) // token_size
                cur_tok_w = (mc * mb_size) // token_size
                src_tok_w = cur_tok_w - round(adx / token_size)
                src_tok_h = cur_tok_h - round(ady / token_size)

                total_lookups += 1
                if 0 <= src_tok_h < token_h and 0 <= src_tok_w < token_w:
                    in_bounds += 1
                    f_in += 1
                    if src_tok_h == cur_tok_h and src_tok_w == cur_tok_w:
                        zero_offset += 1
                        f_same += 1
                    else:
                        nonzero_offset += 1
                        f_diff += 1

                    # Check cacheability
                    y0, x0 = mr * mb_size, mc * mb_size
                    cb = current[y0:y0+mb_size, x0:x0+mb_size]
                    sx = max(0, min(x0 + round(adx), width - mb_size))
                    sy = max(0, min(y0 + round(ady), height - mb_size))
                    pb = prev[sy:sy+mb_size, sx:sx+mb_size]
                    if np.mean(np.abs(cb - pb)) < residual_threshold:
                        f_cache += 1
                else:
                    out_bounds += 1
                    f_out += 1

        per_frame.append({
            'frame': fidx,
            'in_bounds': f_in, 'out_bounds': f_out,
            'same_token': f_same, 'diff_token': f_diff,
            'cacheable': f_cache, 'total_mbs': mb_h * mb_w,
        })

    return {
        'total_lookups': total_lookups,
        'in_bounds_pct': in_bounds / total_lookups if total_lookups > 0 else 0,
        'out_bounds_pct': out_bounds / total_lookups if total_lookups > 0 else 0,
        'same_token_pct': zero_offset / total_lookups if total_lookups > 0 else 0,
        'diff_token_pct': nonzero_offset / total_lookups if total_lookups > 0 else 0,
        'per_frame': per_frame,
    }


# ── 6. Residual threshold sweep ────────────────────────────────────────

def sweep_residual_thresholds(mv_by_frame, frames_y, frame_types, width, height,
                              mb_size=16,
                              thresholds=(1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0)):
    """Sweep residual thresholds for CBF=0 proxy calibration."""
    mb_w = width // mb_size
    mb_h = height // mb_size

    # Pre-compute all residuals once
    all_residuals = []
    for fidx, mv_arr in mv_by_frame.items():
        ft = frame_types[fidx]
        if ft == 'I' or fidx == 0:
            continue
        current = frames_y[fidx].astype(np.float32)
        prev = frames_y[fidx - 1].astype(np.float32)
        mv_map = build_mb_mv_map(mv_arr, mb_size, mb_h, mb_w)

        for mr in range(mb_h):
            for mc in range(mb_w):
                if (mr, mc) not in mv_map:
                    continue
                adx, ady, _ = mv_map[(mr, mc)]
                y0, x0 = mr * mb_size, mc * mb_size
                cb = current[y0:y0+mb_size, x0:x0+mb_size]
                sx = max(0, min(x0 + round(adx), width - mb_size))
                sy = max(0, min(y0 + round(ady), height - mb_size))
                pb = prev[sy:sy+mb_size, sx:sx+mb_size]
                all_residuals.append(np.mean(np.abs(cb - pb)))

    residuals = np.array(all_residuals)
    total = len(residuals)

    results = []
    for thresh in thresholds:
        cbf0 = int((residuals < thresh).sum())
        results.append({
            'threshold': thresh,
            'cbf0_pct': cbf0 / total if total > 0 else 0,
            'cbf0_count': cbf0,
            'total_inter': total,
        })

    # Also report residual distribution
    if total > 0:
        res_stats = {
            'median': float(np.median(residuals)),
            'mean': float(np.mean(residuals)),
            'p25': float(np.percentile(residuals, 25)),
            'p75': float(np.percentile(residuals, 75)),
            'p90': float(np.percentile(residuals, 90)),
            'p95': float(np.percentile(residuals, 95)),
        }
    else:
        res_stats = {}

    return results, res_stats


# ── Main Analysis ───────────────────────────────────────────────────────

def analyze_video(video_path: str, max_frames: int = 150):
    """Full per-block MV analysis pipeline."""
    path = Path(video_path)
    print(f"\n{'='*70}")
    print(f"  Analyzing: {path.name}")
    print(f"{'='*70}")

    # 1. Extract
    print("  [1/6] Extracting MVs and frames...")
    mv_by_frame, frames_y, frame_types, width, height = extract_mvs_and_frames(
        str(path), max_frames)

    n_frames = len(frames_y)
    n_i = sum(1 for ft in frame_types if ft == 'I')
    n_p = sum(1 for ft in frame_types if ft == 'P')
    n_b = sum(1 for ft in frame_types if ft == 'B')
    total_mvs = sum(len(a) for a in mv_by_frame.values() if a is not None)
    frames_with_mvs = sum(1 for a in mv_by_frame.values() if a is not None and len(a) > 0)

    print(f"  Decoded {n_frames} frames ({n_i}I, {n_p}P, {n_b}B), {width}x{height}")
    print(f"  Total MVs extracted: {total_mvs:,} across {frames_with_mvs} frames")

    # 2. MV statistics
    print("  [2/6] Computing MV statistics...")
    mv_stats = compute_mv_statistics(mv_by_frame, frame_types, width, height)
    print(f"  MV magnitude: median={mv_stats['magnitude_median']:.2f}, "
          f"mean={mv_stats['magnitude_mean']:.2f}, "
          f"p95={mv_stats['magnitude_p95']:.2f}, "
          f"max={mv_stats['magnitude_max']:.2f}")
    print(f"  Zero MV (<0.5px): {mv_stats['zero_mv_pct']:.1%}")
    print(f"  Cross 14px boundary: {mv_stats['cross14_pct']:.1%}")
    print(f"  Cross 28px boundary: {mv_stats['cross28_pct']:.1%}")

    # 3. MV+residual classification
    print("  [3/6] MV+residual classification...")
    mv_class = compute_residual_classification(
        mv_by_frame, frames_y, frame_types, width, height, threshold=3.0)

    if mv_class:
        total_mbs = sum(r['total_mbs'] for r in mv_class)
        agg_s = sum(r['static'] for r in mv_class)
        agg_sh = sum(r['shifted'] for r in mv_class)
        agg_n = sum(r['novel'] for r in mv_class)
        agg_i = sum(r['intra'] for r in mv_class)
        print(f"  ┌──────────────────────────────────────────────────────┐")
        print(f"  │  MV+RESIDUAL CLASSIFICATION (threshold=3.0)         │")
        print(f"  ├──────────────────────────────────────────────────────┤")
        print(f"  │  STATIC  (|MV|<0.5, res<3): {agg_s/total_mbs:>6.1%}  ({agg_s:>8,})   │")
        print(f"  │  SHIFTED (|MV|≥0.5, res<3): {agg_sh/total_mbs:>6.1%}  ({agg_sh:>8,})   │")
        print(f"  │  NOVEL   (res≥3 or intra) : {agg_n/total_mbs:>6.1%}  ({agg_n:>8,})   │")
        print(f"  │  (of which intra)          : {agg_i/total_mbs:>6.1%}  ({agg_i:>8,})   │")
        print(f"  └──────────────────────────────────────────────────────┘")
        class_rates = {
            'static_pct': round(agg_s / total_mbs, 4),
            'shifted_pct': round(agg_sh / total_mbs, 4),
            'novel_pct': round(agg_n / total_mbs, 4),
            'intra_pct': round(agg_i / total_mbs, 4),
        }
    else:
        class_rates = {'static_pct': 0, 'shifted_pct': 0, 'novel_pct': 0, 'intra_pct': 0}

    # 4. Compare vs pixel-diff
    print("  [4/6] Comparing MV-based vs pixel-diff...")
    comparison = compare_mv_vs_pixeldiff(
        mv_by_frame, frames_y, frame_types, width, height)
    print(f"  Agreement: {comparison['agree_pct']:.1%} ({comparison['agree']:,}/{comparison['total_mbs']:,})")
    print(f"  Confusion (MV_vs_PixelDiff):")
    for k, v in sorted(comparison['confusion'].items()):
        pct = v / comparison['total_mbs'] * 100 if comparison['total_mbs'] > 0 else 0
        print(f"    {k}: {v:,} ({pct:.1f}%)")

    # 5. Lookup indices
    print("  [5/6] Computing lookup indices (token_size=28)...")
    lookup = compute_lookup_indices(
        mv_by_frame, frames_y, frame_types, width, height, token_size=28)
    print(f"  Total lookups: {lookup['total_lookups']:,}")
    print(f"  In-bounds: {lookup['in_bounds_pct']:.1%}")
    print(f"  Out-of-bounds (NOVEL): {lookup['out_bounds_pct']:.1%}")
    print(f"  Same token (STATIC): {lookup['same_token_pct']:.1%}")
    print(f"  Different token (SHIFTED): {lookup['diff_token_pct']:.1%}")

    # 6. Threshold sweep
    print("  [6/6] Sweeping residual thresholds...")
    threshold_sweep, res_dist = sweep_residual_thresholds(
        mv_by_frame, frames_y, frame_types, width, height)
    print(f"  Residual distribution: median={res_dist.get('median',0):.2f}, "
          f"mean={res_dist.get('mean',0):.2f}, "
          f"p90={res_dist.get('p90',0):.2f}")
    print(f"  Threshold → CBF=0 proxy rate:")
    for ts in threshold_sweep:
        print(f"    {ts['threshold']:>5.1f} → {ts['cbf0_pct']:.1%}")

    return {
        'video': path.name,
        'n_frames': n_frames,
        'frame_types': {'I': n_i, 'P': n_p, 'B': n_b},
        'dimensions': {'width': width, 'height': height},
        'total_mvs_extracted': total_mvs,
        'mv_stats': {
            'total_mvs': mv_stats['total_mvs'],
            'zero_mv_pct': round(mv_stats['zero_mv_pct'], 4),
            'cross14_pct': round(mv_stats['cross14_pct'], 4),
            'cross28_pct': round(mv_stats['cross28_pct'], 4),
            'magnitude_median': round(mv_stats['magnitude_median'], 3),
            'magnitude_mean': round(mv_stats['magnitude_mean'], 3),
            'magnitude_p95': round(mv_stats['magnitude_p95'], 3),
            'magnitude_max': round(mv_stats['magnitude_max'], 3),
        },
        'classification': class_rates,
        'comparison_vs_pixeldiff': {
            'agreement_pct': round(comparison['agree_pct'], 4),
            'confusion': comparison['confusion'],
        },
        'lookup_indices': {
            'total_lookups': lookup['total_lookups'],
            'in_bounds_pct': round(lookup['in_bounds_pct'], 4),
            'out_bounds_pct': round(lookup['out_bounds_pct'], 4),
            'same_token_pct': round(lookup['same_token_pct'], 4),
            'diff_token_pct': round(lookup['diff_token_pct'], 4),
        },
        'threshold_sweep': [
            {'threshold': ts['threshold'], 'cbf0_pct': round(ts['cbf0_pct'], 4)}
            for ts in threshold_sweep
        ],
        'residual_distribution': res_dist,
        'mv_per_frame_stats': mv_stats['per_frame'][:30],
    }


def main():
    data_dir = Path(__file__).parent / "data"

    videos = [
        data_dir / "surveillance.mp4",
        data_dir / "talking_head_h264.mp4",
        data_dir / "fpv_drone_h264.mp4",
    ]

    print("=" * 70)
    print("  Per-Block MV-Compensated Cache Lookup Analysis")
    print("  Using PyAV flags2 MV export + residual energy proxy")
    print("=" * 70)

    all_results = {}
    for v in videos:
        if not v.exists():
            print(f"\n  SKIP: {v.name} not found")
            continue
        try:
            result = analyze_video(str(v), max_frames=150)
            all_results[v.name] = result
        except Exception as e:
            print(f"\n  ERROR on {v.name}: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    print(f"\n{'='*70}")
    print(f"  SUMMARY ACROSS VIDEOS")
    print(f"{'='*70}")
    print(f"\n  {'Video':<25} {'Zero MV':>8} {'>14px':>8} {'>28px':>8} {'STATIC':>8} {'SHIFTED':>8} {'NOVEL':>8}")
    print(f"  {'─'*25} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")
    for name, r in all_results.items():
        mv = r['mv_stats']
        cl = r['classification']
        print(f"  {name:<25} {mv['zero_mv_pct']:>7.1%} {mv['cross14_pct']:>7.1%} "
              f"{mv['cross28_pct']:>7.1%} {cl['static_pct']:>7.1%} {cl['shifted_pct']:>7.1%} "
              f"{cl['novel_pct']:>7.1%}")

    print(f"\n  {'Video':<25} {'InBnd':>8} {'SameTok':>8} {'DiffTok':>8} {'OOB':>8} {'Agree%':>8}")
    print(f"  {'─'*25} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")
    for name, r in all_results.items():
        lu = r['lookup_indices']
        cmp = r['comparison_vs_pixeldiff']
        print(f"  {name:<25} {lu['in_bounds_pct']:>7.1%} {lu['same_token_pct']:>7.1%} "
              f"{lu['diff_token_pct']:>7.1%} {lu['out_bounds_pct']:>7.1%} {cmp['agreement_pct']:>7.1%}")

    out_path = Path(__file__).parent / "mv_lookup_results.json"
    with open(out_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\n  Results saved to {out_path}")

    return all_results


if __name__ == "__main__":
    main()
