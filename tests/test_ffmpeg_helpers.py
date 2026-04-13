import pytest

from codec_through.ffmpeg import (
    FramePacketInfo,
    frame_level_early_exit,
    mean_i_frame_size,
    uniform_frame_indices,
)


def test_uniform_frame_indices_matches_prototype_spacing() -> None:
    assert uniform_frame_indices(10, 4) == [0, 3, 6, 9]


def test_uniform_frame_indices_rejects_invalid_sampling() -> None:
    with pytest.raises(ValueError):
        uniform_frame_indices(1, 4)
    with pytest.raises(ValueError):
        uniform_frame_indices(0, 4)
    with pytest.raises(ValueError):
        uniform_frame_indices(4, 0)


def test_mean_i_frame_size_uses_only_i_frames() -> None:
    packets = [
        FramePacketInfo(index=0, pict_type="I", key_frame=True, pkt_size=100),
        FramePacketInfo(index=1, pict_type="P", key_frame=False, pkt_size=10),
        FramePacketInfo(index=2, pict_type="I", key_frame=False, pkt_size=140),
    ]
    assert mean_i_frame_size(packets) == 120.0


def test_frame_level_early_exit_only_for_tiny_non_i_frames() -> None:
    avg_i_frame_size = 1000.0
    tiny_p = FramePacketInfo(index=1, pict_type="P", key_frame=False, pkt_size=10)
    normal_p = FramePacketInfo(index=2, pict_type="P", key_frame=False, pkt_size=100)
    i_frame = FramePacketInfo(index=0, pict_type="I", key_frame=True, pkt_size=1000)

    assert frame_level_early_exit(tiny_p, avg_i_frame_size, threshold=0.02) == "ALL_STATIC"
    assert frame_level_early_exit(normal_p, avg_i_frame_size, threshold=0.02) is None
    assert frame_level_early_exit(i_frame, avg_i_frame_size, threshold=0.02) is None
