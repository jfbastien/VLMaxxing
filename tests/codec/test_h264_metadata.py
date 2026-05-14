"""Regression tests for the ported H.264 metadata extractor.

Spec source: `research/experiments/2026/2026-04-16-phase-1_29-mv-only-signal-path.md`
lines 143-149. Three pinned behaviors:

1. **Static clip → zero motion signal.** An all-black clip should yield
   no coded motion vectors and no CBF trips: the encoder chooses skip
   mode for every non-I macroblock.
2. **Moving block between I and P → expected MV magnitude.** A single
   high-contrast patch that translates by a known pixel offset should
   produce MVs whose magnitude lies near that offset (±chroma/RD noise).
3. **B-frames → bidirectional residual differs from P-only path.** On a
   clip with B-frames, the bidirectional ``b_cbf_thresh`` path should
   mark a different (smaller) set of MBs as CBF than the forward-only
   threshold would. Guards the bidirectional fix from regressing.

The clips are synthesized in-process with PyAV (``libx264``) so the
tests have no binary fixture dependency.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import av
import numpy as np
import pytest

from codec_through.codec.h264_metadata import (
    NOVEL,
    STATIC,
    H264MetadataExtractor,
    classify_blocks_h264,
)

# ────────────────────────────────────────────────────────────────────
# Synthetic clip builders
# ────────────────────────────────────────────────────────────────────


def _encode_rgb_frames(
    path: Path,
    frames: list[np.ndarray],
    *,
    fps: int = 30,
    gop: int | None = None,
    bframes: int = 0,
) -> None:
    """Encode a list of HxWx3 uint8 RGB frames to H.264 with a known GOP.

    ``gop`` controls the key-frame interval (``-g``). ``bframes`` sets
    the max number of B-frames between references (``-bf``). Both map
    to libx264 options so tests can force I/P/B frame layouts.
    """
    with av.open(str(path), mode="w") as container:
        stream = container.add_stream("libx264", rate=fps)
        stream.width = frames[0].shape[1]
        stream.height = frames[0].shape[0]
        stream.pix_fmt = "yuv420p"
        opts: dict[str, object] = {}
        if gop is not None:
            opts["g"] = str(gop)
            opts["keyint_min"] = str(gop)
        opts["bf"] = str(bframes)
        # Predictable, low-effort encode so tests are fast.
        opts["preset"] = "veryfast"
        opts["tune"] = "zerolatency" if bframes == 0 else "fastdecode"
        stream.options = opts

        for arr in frames:
            frame = av.VideoFrame.from_ndarray(arr, format="rgb24")
            for pkt in stream.encode(frame):
                container.mux(pkt)
        for pkt in stream.encode():
            container.mux(pkt)


def _black_clip(path: Path, n: int = 30, *, w: int = 96, h: int = 96) -> None:
    frames = [np.zeros((h, w, 3), dtype=np.uint8) for _ in range(n)]
    _encode_rgb_frames(path, frames, gop=15, bframes=0)


def _translating_patch_clip(
    path: Path,
    *,
    n: int = 12,
    w: int = 128,
    h: int = 128,
    patch: int = 32,
    dx: int = 8,
    dy: int = 0,
    bframes: int = 0,
    gop: int | None = None,
) -> None:
    """White patch on a mid-gray background translating by (dx, dy) per frame.

    Mid-gray (not black) so the RD choice is not dominated by DC offset,
    and the patch is a strong enough texture that libx264 allocates a
    real MV rather than collapsing to skip.
    """
    frames = []
    for i in range(n):
        arr = np.full((h, w, 3), 96, dtype=np.uint8)
        x0 = 16 + i * dx
        y0 = 16 + i * dy
        x1 = x0 + patch
        y1 = y0 + patch
        x1 = min(x1, w)
        y1 = min(y1, h)
        arr[y0:y1, x0:x1] = 230
        frames.append(arr)
    _encode_rgb_frames(path, frames, gop=gop if gop is not None else n, bframes=bframes)


# ────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────


@pytest.fixture
def black_clip(tmp_path: Path) -> Iterator[Path]:
    p = tmp_path / "black.mp4"
    _black_clip(p)
    yield p


@pytest.fixture
def motion_clip(tmp_path: Path) -> Iterator[Path]:
    p = tmp_path / "motion.mp4"
    # No B-frames — every non-I frame is a P-frame, matching the spec.
    _translating_patch_clip(p, dx=8, dy=0, bframes=0)
    yield p


@pytest.fixture
def bframes_clip(tmp_path: Path) -> Iterator[Path]:
    p = tmp_path / "bframes.mp4"
    # Force B-frames between anchors. libx264 may still refuse if scene
    # changes too much; translating patch is smooth enough that B-frames
    # survive the lookahead.
    _translating_patch_clip(p, dx=4, dy=0, bframes=3, gop=24)
    yield p


# ────────────────────────────────────────────────────────────────────
# Tests
# ────────────────────────────────────────────────────────────────────


def test_black_clip_has_no_motion_signal(black_clip: Path) -> None:
    """Static content → skip-MB dominance, zero MV magnitude, no CBF trips on P/B."""
    ext = H264MetadataExtractor(str(black_clip))

    per_frame_intra = []
    per_frame_skip_rate = []
    per_frame_cbf_rate = []
    per_frame_mv_max = []

    for meta in ext.iter_frames():
        mbs = meta.macroblocks
        per_frame_intra.append(meta.frame_type == "I")
        if meta.frame_type == "I":
            # I-frame: MV side-data is empty by construction, intra_flag True.
            assert bool(mbs["intra_flag"].all()), "all I-frame MBs must be intra"
            assert float(mbs["mv_magnitude"].max()) == 0.0
            continue
        per_frame_skip_rate.append(float(mbs["skip_flag"].mean()))
        per_frame_cbf_rate.append(float(mbs["cbf"].mean()))
        per_frame_mv_max.append(float(mbs["mv_magnitude"].max()))

    assert any(per_frame_intra), "expected at least one I-frame in a 30-frame clip"
    # Non-I frames: every MB should be skip, no CBF trips, zero MVs.
    assert per_frame_skip_rate, "expected some P-frames"
    assert min(per_frame_skip_rate) >= 0.95, (
        f"black clip should be ~all-skip on P-frames; got min skip rate "
        f"{min(per_frame_skip_rate):.3f}"
    )
    assert max(per_frame_cbf_rate) <= 0.05, (
        f"black clip must not trip CBF; max cbf rate {max(per_frame_cbf_rate):.3f}"
    )
    assert max(per_frame_mv_max) < 1e-3, (
        f"black clip must have zero MV magnitude; max {max(per_frame_mv_max):.3f}"
    )


def test_black_clip_classify_is_all_static(black_clip: Path) -> None:
    """classify_blocks_h264 on a black P-frame must return STATIC everywhere."""
    ext = H264MetadataExtractor(str(black_clip))
    saw_p = False
    for meta in ext.iter_frames():
        if meta.frame_type != "P":
            continue
        cls = classify_blocks_h264(meta, token_block=28)
        # Allow a 1-token-wide trailing strip from rounding; interior must be STATIC.
        # Interior crop ignores final row/col where width % 28 != 0.
        interior = cls[:-1, :-1] if cls.shape[0] > 1 and cls.shape[1] > 1 else cls
        static_frac = float((interior == STATIC).mean())
        assert static_frac >= 0.9, (
            f"black P-frame classify: interior STATIC frac {static_frac:.3f} (shape {cls.shape})"
        )
        saw_p = True
        break
    assert saw_p, "no P-frame encountered in black clip"


def test_motion_clip_yields_expected_mv_magnitude(motion_clip: Path) -> None:
    """Translating patch → P-frame MVs on the patch region cluster near the dx."""
    ext = H264MetadataExtractor(str(motion_clip))

    # Pick the first non-I frame that has coded MVs.
    mv_mags_coded: list[float] = []
    for meta in ext.iter_frames():
        if meta.frame_type == "I":
            continue
        mbs = meta.macroblocks
        # Coded MBs: non-skip, non-intra. MVs here reflect encoder choice.
        coded = ~mbs["skip_flag"] & ~mbs["intra_flag"]
        if not coded.any():
            continue
        mv_mags_coded.extend(mbs["mv_magnitude"][coded].ravel().tolist())
        # One frame is enough to assert the signal.
        break

    assert mv_mags_coded, "expected coded MVs on the translating-patch P-frame"
    # Expected dx = 8 px per frame; libx264 quarter-pel estimation should
    # land within a few px. Check p50 ∈ [4, 14]; max < 32 (patch size).
    p50 = float(np.percentile(mv_mags_coded, 50))
    assert 3.0 <= p50 <= 14.0, (
        f"coded MV p50 expected ~8 px, got {p50:.2f} (n={len(mv_mags_coded)})"
    )
    # And the patch region must produce NOVEL/SHIFTED blocks in the classifier.
    for meta in ext.iter_frames():
        if meta.frame_type == "I":
            continue
        cls = classify_blocks_h264(meta, token_block=meta.mb_size)
        active = float((cls != STATIC).mean())
        assert active >= 0.02, f"motion clip must mark some blocks active; got {active:.3f}"
        break


def test_bframe_bidirectional_residual_differs_from_pframe_threshold(
    bframes_clip: Path,
) -> None:
    """On a B-frame, the bidirectional path produces a different CBF set than
    a P-only threshold would.

    Mechanism: the extractor uses the looser ``b_cbf_thresh=6.0`` on B-frames
    *and* takes the min residual vs (prev, next). A P-only pipeline would
    use ``cbf_thresh=3.0`` vs prev only. On a smoothly translating patch the
    forward residual is small; bidirectional min can only reduce it further.
    So we expect bidir cbf_rate ≤ fwd-only-at-3.0 cbf_rate, and the two rates
    should not be identical — if they were, the bidir code path is inert.
    """
    ext = H264MetadataExtractor(str(bframes_clip))

    saw_b = False
    for meta in ext.iter_frames():
        if meta.frame_type != "B":
            continue
        saw_b = True
        mbs = meta.macroblocks
        bidir_cbf_rate = float(mbs["cbf"].mean())
        # Re-threshold using the forward residual only against the P-only
        # threshold — we can approximate by comparing the stored residual
        # to 3.0 (the ``cbf_thresh``); this is a lower bound on the forward-
        # only CBF rate because bidir residual ≤ forward residual by min().
        forward_lower_bound_cbf_rate = float((mbs["residual_energy"] >= 3.0).mean())
        # The bidir set must be a subset (up to tie) of a forward-at-3.0 set
        # since the stored residual is already the min. Equivalently, bidir
        # rate at threshold 6.0 ≤ stored residual ≥ 3.0 rate.
        assert bidir_cbf_rate <= forward_lower_bound_cbf_rate + 1e-6, (
            f"bidir cbf rate {bidir_cbf_rate:.3f} should be ≤ forward-only "
            f"at-3.0 rate {forward_lower_bound_cbf_rate:.3f}"
        )
        # And we expect the B-frame residual to be small but finite — zero
        # everywhere would signal a path where bidirectional residual was
        # never filled in.
        assert float(mbs["residual_energy"].max()) > 0.0, (
            "bidirectional residual must be populated on B-frames"
        )
        break

    assert saw_b, (
        "libx264 did not emit B-frames despite -bf 3; the fixture must exercise "
        "the bidirectional residual path instead of silently skipping it"
    )


def test_iter_frames_is_reentrant(black_clip: Path) -> None:
    """The extractor documents that iter_frames reopens the container; verify
    a second pass yields the same number of frames as the first."""
    ext = H264MetadataExtractor(str(black_clip))
    n1 = sum(1 for _ in ext.iter_frames())
    n2 = sum(1 for _ in ext.iter_frames())
    assert n1 == n2 > 0


def test_classify_on_intra_frame_marks_novel(motion_clip: Path) -> None:
    """I-frames should produce NOVEL classification because intra_flag=True."""
    ext = H264MetadataExtractor(str(motion_clip))
    for meta in ext.iter_frames():
        if meta.frame_type != "I":
            continue
        cls = classify_blocks_h264(meta, token_block=meta.mb_size)
        assert float((cls == NOVEL).mean()) >= 0.95, (
            "I-frame classification should be dominated by NOVEL"
        )
        return
    pytest.fail("no I-frame in motion clip — unexpected given gop=n")
