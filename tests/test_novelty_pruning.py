"""Tests for phase 1.51R novelty-pruning anchor-arm policy.

The module under test (`codec_through.novelty_pruning`) is pure-numpy and
CPU-only; these tests do not require MLX or a GPU. Each anchor arm from the
preregistration (`research/experiments/2026/2026-04-17-phase-1_51-novelty-pruning-gemma-prereg.md`)
is covered with synthetic inputs whose expected masks are derivable by hand.
"""

from __future__ import annotations

import numpy as np
import pytest

from codec_through.novelty_pruning import (
    ANCHOR_ARMS,
    NoveltyPruneConfig,
    compute_keep_mask,
    compute_pixel_novelty,
    prune_image_placeholders,
    reduce_features,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _novelty_ramp(f_count: int, t_count: int) -> np.ndarray:
    """Per-frame novelty where token i has score i (highest at last token)."""
    row = np.arange(t_count, dtype=np.float32)
    return np.broadcast_to(row, (f_count, t_count)).copy()


def _random_features(f_count: int, t_count: int, d: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.standard_normal((f_count, t_count, d)).astype(np.float32)


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------


def test_anchor_arms_constant_matches_literal() -> None:
    assert set(ANCHOR_ARMS) == {
        "none",
        "cls_attention_proxy",
        "nuwa_pillar",
        "max_min_diversity",
        "gemma_structural",
    }


def test_promotable_arms_excludes_proxy() -> None:
    from codec_through.novelty_pruning import PROMOTABLE_ARMS

    # The cls_attention_proxy arm is gated off winner promotion until real
    # Gemma vision-tower attention instrumentation lands.
    assert "cls_attention_proxy" not in PROMOTABLE_ARMS
    assert set(PROMOTABLE_ARMS) == {
        "none",
        "nuwa_pillar",
        "max_min_diversity",
        "gemma_structural",
    }


def test_resolved_grid_shape_square_default() -> None:
    cfg = NoveltyPruneConfig(anchor_arm="gemma_structural", keep_rate=0.5)
    assert cfg.resolved_grid_shape(16) == (4, 4)


def test_resolved_grid_shape_explicit_side() -> None:
    cfg = NoveltyPruneConfig(anchor_arm="gemma_structural", keep_rate=0.5, grid_side=8)
    assert cfg.resolved_grid_shape(64) == (8, 8)


def test_resolved_grid_shape_rectangular_override() -> None:
    cfg = NoveltyPruneConfig(anchor_arm="gemma_structural", keep_rate=0.5, grid_shape=(14, 20))
    assert cfg.resolved_grid_shape(280) == (14, 20)


def test_resolved_grid_shape_rejects_non_square_without_override() -> None:
    cfg = NoveltyPruneConfig(anchor_arm="gemma_structural", keep_rate=0.5)
    with pytest.raises(ValueError, match="not square"):
        cfg.resolved_grid_shape(280)


def test_resolved_grid_shape_rejects_mismatched_override() -> None:
    cfg = NoveltyPruneConfig(anchor_arm="gemma_structural", keep_rate=0.5, grid_shape=(4, 5))
    with pytest.raises(ValueError, match="does not multiply"):
        cfg.resolved_grid_shape(25)


def test_compute_keep_mask_rejects_1d_novelty() -> None:
    cfg = NoveltyPruneConfig(anchor_arm="none", keep_rate=0.5)
    with pytest.raises(ValueError, match="2D"):
        compute_keep_mask(np.arange(10, dtype=np.float32), config=cfg)


def test_compute_keep_mask_rejects_bad_keep_rate() -> None:
    cfg = NoveltyPruneConfig(anchor_arm="none", keep_rate=1.5)
    with pytest.raises(ValueError, match="keep_rate"):
        compute_keep_mask(_novelty_ramp(2, 4), config=cfg)


def test_compute_keep_mask_requires_features_for_nuwa() -> None:
    cfg = NoveltyPruneConfig(anchor_arm="nuwa_pillar", keep_rate=0.5, grid_side=4, nuwa_cell_side=2)
    with pytest.raises(ValueError, match="features"):
        compute_keep_mask(_novelty_ramp(1, 16), config=cfg)


def test_compute_keep_mask_requires_features_for_diversity() -> None:
    cfg = NoveltyPruneConfig(anchor_arm="max_min_diversity", keep_rate=0.5)
    with pytest.raises(ValueError, match="features"):
        compute_keep_mask(_novelty_ramp(1, 9), config=cfg)


def test_compute_keep_mask_requires_cls_attention_when_selected() -> None:
    cfg = NoveltyPruneConfig(anchor_arm="cls_attention_proxy", keep_rate=0.5)
    with pytest.raises(ValueError, match="cls_attention_proxy"):
        compute_keep_mask(_novelty_ramp(1, 9), config=cfg)


def test_compute_keep_mask_rejects_feature_shape_mismatch() -> None:
    cfg = NoveltyPruneConfig(anchor_arm="max_min_diversity", keep_rate=0.5)
    with pytest.raises(ValueError, match="features must have shape"):
        compute_keep_mask(
            _novelty_ramp(2, 4),
            config=cfg,
            features=np.zeros((3, 4, 5), dtype=np.float32),
        )


def test_compute_keep_mask_rejects_cls_shape_mismatch() -> None:
    cfg = NoveltyPruneConfig(anchor_arm="cls_attention_proxy", keep_rate=0.5)
    with pytest.raises(ValueError, match="cls_attention must match"):
        compute_keep_mask(
            _novelty_ramp(2, 4),
            config=cfg,
            cls_attention=np.zeros((2, 5), dtype=np.float32),
        )


# ---------------------------------------------------------------------------
# Arm: none (pure top-K novelty)
# ---------------------------------------------------------------------------


def test_none_arm_keeps_top_k_by_novelty() -> None:
    novelty = _novelty_ramp(2, 8)  # token 7 highest on each frame
    cfg = NoveltyPruneConfig(anchor_arm="none", keep_rate=0.5)  # k = 4
    mask = compute_keep_mask(novelty, config=cfg)
    assert mask.shape == (2, 8)
    for f in range(2):
        # Top-4 highest-novelty tokens are 4, 5, 6, 7.
        assert mask[f].tolist() == [False] * 4 + [True] * 4


def test_none_arm_keep_rate_1_keeps_all() -> None:
    novelty = _novelty_ramp(1, 5)
    cfg = NoveltyPruneConfig(anchor_arm="none", keep_rate=1.0)
    mask = compute_keep_mask(novelty, config=cfg)
    assert mask.all()


def test_none_arm_keep_rate_0_keeps_minimum_one() -> None:
    novelty = _novelty_ramp(1, 5)
    cfg = NoveltyPruneConfig(anchor_arm="none", keep_rate=0.0)
    mask = compute_keep_mask(novelty, config=cfg)
    # floor(0 * 5) = 0 but the module clamps to 1 to avoid degeneracy.
    assert mask.sum() == 1
    # Highest-novelty token (index 4) wins the single slot.
    assert mask[0, 4]


def test_none_arm_ties_break_by_lower_index() -> None:
    # All novelties equal → top-k selects lowest-index tokens first.
    novelty = np.full((1, 6), 3.14, dtype=np.float32)
    cfg = NoveltyPruneConfig(anchor_arm="none", keep_rate=0.5)  # k = 3
    mask = compute_keep_mask(novelty, config=cfg)
    assert mask[0].tolist() == [True, True, True, False, False, False]


# ---------------------------------------------------------------------------
# Arm: cls_attention
# ---------------------------------------------------------------------------


def test_cls_attention_keeps_top_k_by_attention() -> None:
    # Novelty ramps up, attention ramps *down* — make sure we pick by attention.
    novelty = _novelty_ramp(1, 6)
    attention = np.array([[6.0, 5.0, 4.0, 3.0, 2.0, 1.0]], dtype=np.float32)
    cfg = NoveltyPruneConfig(anchor_arm="cls_attention_proxy", keep_rate=0.5)  # k = 3
    mask = compute_keep_mask(novelty, config=cfg, cls_attention=attention)
    assert mask[0].tolist() == [True, True, True, False, False, False]


def test_cls_attention_ignores_novelty() -> None:
    # A sanity check: no matter what novelty looks like, result depends only on attention.
    novelty_a = np.array([[1.0, 2.0, 3.0, 4.0]], dtype=np.float32)
    novelty_b = np.array([[4.0, 3.0, 2.0, 1.0]], dtype=np.float32)
    attention = np.array([[10.0, 0.0, 0.0, 10.0]], dtype=np.float32)
    cfg = NoveltyPruneConfig(anchor_arm="cls_attention_proxy", keep_rate=0.5)  # k = 2
    mask_a = compute_keep_mask(novelty_a, config=cfg, cls_attention=attention)
    mask_b = compute_keep_mask(novelty_b, config=cfg, cls_attention=attention)
    assert np.array_equal(mask_a, mask_b)
    assert mask_a[0].tolist() == [True, False, False, True]


# ---------------------------------------------------------------------------
# Arm: nuwa_pillar
# ---------------------------------------------------------------------------


def test_nuwa_pillar_preserves_top_norm_per_cell() -> None:
    # 4x4 grid split into 2x2 cells → 4 cells of 4 tokens each.
    # pillar_frac = 0.25 → 1 pillar per cell (highest L2-norm).
    # keep_rate 0.25 → k = 4 → anchors fully occupy budget; novelty fill = 0.
    grid = 4
    t = grid * grid
    cfg = NoveltyPruneConfig(
        anchor_arm="nuwa_pillar",
        keep_rate=0.25,
        grid_side=grid,
        nuwa_cell_side=2,
        nuwa_pillar_frac=0.25,
    )
    # Craft features so the pillar per cell is predictable: one token per cell
    # has unit norm, the rest are zero.
    features = np.zeros((1, t, 3), dtype=np.float32)
    pillar_positions = [
        (0, 0),
        (0, 2),
        (2, 0),
        (2, 2),
    ]
    for r, c in pillar_positions:
        features[0, r * grid + c, 0] = 1.0
    novelty = np.zeros((1, t), dtype=np.float32)
    mask = compute_keep_mask(novelty, config=cfg, features=features)
    expected_indices = [r * grid + c for r, c in pillar_positions]
    kept = np.nonzero(mask[0])[0].tolist()
    assert sorted(kept) == sorted(expected_indices)


def test_nuwa_pillar_fills_remainder_with_novelty() -> None:
    grid = 4
    t = grid * grid
    cfg = NoveltyPruneConfig(
        anchor_arm="nuwa_pillar",
        keep_rate=0.5,  # k = 8, anchors = 4 → 4 novelty fills
        grid_side=grid,
        nuwa_cell_side=2,
        nuwa_pillar_frac=0.25,
    )
    features = np.zeros((1, t, 3), dtype=np.float32)
    pillar_positions = [(0, 0), (0, 2), (2, 0), (2, 2)]
    for r, c in pillar_positions:
        features[0, r * grid + c, 0] = 1.0
    # Rank novelty so the top-4 non-pillar fills are deterministic.
    novelty = np.arange(t, dtype=np.float32)[None, :]
    mask = compute_keep_mask(novelty, config=cfg, features=features)
    assert mask.sum() == 8
    anchors = {r * grid + c for r, c in pillar_positions}
    kept = set(np.nonzero(mask[0])[0].tolist())
    # Anchors are always preserved.
    assert anchors.issubset(kept)
    # The 4 highest-novelty non-anchors fill the remainder: 12, 13, 14, 15
    # minus any that are also anchors (none), plus preferring lower indices on ties.
    novelty_candidates = [i for i in range(t) if i not in anchors]
    expected_fill = sorted(novelty_candidates, key=lambda i: -novelty[0, i])[:4]
    assert kept - anchors == set(expected_fill)


def test_nuwa_pillar_rejects_grid_not_divisible_by_cell() -> None:
    cfg = NoveltyPruneConfig(
        anchor_arm="nuwa_pillar",
        keep_rate=0.5,
        grid_side=5,
        nuwa_cell_side=2,
    )
    features = np.zeros((1, 25, 3), dtype=np.float32)
    novelty = np.zeros((1, 25), dtype=np.float32)
    with pytest.raises(ValueError, match="must divide"):
        compute_keep_mask(novelty, config=cfg, features=features)


# ---------------------------------------------------------------------------
# Arm: max_min_diversity
# ---------------------------------------------------------------------------


def test_max_min_diversity_picks_distant_tokens() -> None:
    # Craft features so two tokens are far apart and three others are clustered.
    # max-min should pick the two far-apart tokens first.
    features = np.array(
        [
            [
                [10.0, 0.0],  # 0
                [0.0, 0.0],  # 1
                [0.0, 0.1],  # 2 (near 1)
                [0.1, 0.0],  # 3 (near 1)
                [-10.0, 0.0],  # 4
            ]
        ],
        dtype=np.float32,
    )
    novelty = np.zeros((1, 5), dtype=np.float32)
    cfg = NoveltyPruneConfig(anchor_arm="max_min_diversity", keep_rate=0.4)  # k = 2
    mask = compute_keep_mask(novelty, config=cfg, features=features)
    kept = set(np.nonzero(mask[0])[0].tolist())
    # Seed by L1-norm: token 0 and token 4 both have L1 10 (tied); argmax picks 0.
    # Next token maximizes min-distance from {0} → token 4 (L2 distance 20).
    assert kept == {0, 4}


def test_max_min_diversity_keeps_everything_when_budget_exceeds_tokens() -> None:
    features = _random_features(1, 4, d=3, seed=7)
    novelty = np.zeros((1, 4), dtype=np.float32)
    cfg = NoveltyPruneConfig(anchor_arm="max_min_diversity", keep_rate=1.0)
    mask = compute_keep_mask(novelty, config=cfg, features=features)
    assert mask.all()


def test_max_min_diversity_respects_k_from_keep_rate() -> None:
    features = _random_features(2, 16, d=8, seed=11)
    novelty = np.zeros((2, 16), dtype=np.float32)
    cfg = NoveltyPruneConfig(anchor_arm="max_min_diversity", keep_rate=0.25)  # k = 4
    mask = compute_keep_mask(novelty, config=cfg, features=features)
    for f in range(2):
        assert mask[f].sum() == 4


# ---------------------------------------------------------------------------
# Arm: gemma_structural
# ---------------------------------------------------------------------------


def test_gemma_structural_preserves_corners_and_center() -> None:
    # 5x5 grid → corners at (0,0), (0,4), (4,0), (4,4); center at (2,2).
    # keep_rate small enough that anchors fully occupy budget (k=5).
    grid = 5
    t = grid * grid
    cfg = NoveltyPruneConfig(anchor_arm="gemma_structural", keep_rate=5 / t, grid_side=grid)
    novelty = np.zeros((1, t), dtype=np.float32)
    mask = compute_keep_mask(novelty, config=cfg)
    kept = set(np.nonzero(mask[0])[0].tolist())
    expected = {
        0 * grid + 0,
        0 * grid + 4,
        4 * grid + 0,
        4 * grid + 4,
        2 * grid + 2,
    }
    assert kept == expected


def test_gemma_structural_fills_remainder_with_novelty() -> None:
    grid = 4
    t = grid * grid
    cfg = NoveltyPruneConfig(
        anchor_arm="gemma_structural",
        keep_rate=0.5,
        grid_side=grid,  # k = 8
    )
    novelty = np.arange(t, dtype=np.float32)[None, :]
    mask = compute_keep_mask(novelty, config=cfg)
    assert mask.sum() == 8
    # Anchors: corners (0, 3, 12, 15) + center (4//2 * 4 + 4//2 = 10).
    anchors = {0, 3, 12, 15, 10}
    kept = set(np.nonzero(mask[0])[0].tolist())
    assert anchors.issubset(kept)
    # Fill with top-3 highest-novelty non-anchors: 14, 13, 11.
    non_anchor_top = [i for i in (15, 14, 13, 12, 11) if i not in anchors][:3]
    assert kept - anchors == set(non_anchor_top)


def test_gemma_structural_rejects_non_square_without_override() -> None:
    cfg = NoveltyPruneConfig(anchor_arm="gemma_structural", keep_rate=0.5)
    novelty = np.zeros((1, 280), dtype=np.float32)
    with pytest.raises(ValueError, match="not square"):
        compute_keep_mask(novelty, config=cfg)


def test_gemma_structural_accepts_rectangular_grid_shape() -> None:
    # Gemma's 280 soft tokens live on a 14x20 grid (vision flattened post-pool).
    cfg = NoveltyPruneConfig(
        anchor_arm="gemma_structural",
        keep_rate=0.1,  # k = 28, anchors (5) + 23 novelty fill
        grid_shape=(14, 20),
    )
    novelty = np.arange(280, dtype=np.float32)[None, :]
    mask = compute_keep_mask(novelty, config=cfg)
    assert mask.sum() == 28
    # Corners for (14, 20): (0,0), (0,19), (13,0), (13,19) + center (7, 10).
    anchors = {
        0 * 20 + 0,
        0 * 20 + 19,
        13 * 20 + 0,
        13 * 20 + 19,
        7 * 20 + 10,
    }
    kept = set(np.nonzero(mask[0])[0].tolist())
    assert anchors.issubset(kept)


# ---------------------------------------------------------------------------
# reduce_features
# ---------------------------------------------------------------------------


def test_reduce_features_matches_mask() -> None:
    features = _random_features(3, 4, d=5, seed=3)
    mask = np.zeros((3, 4), dtype=bool)
    # Keep tokens (0,1), (1,3), (2,0), (2,2)
    mask[0, 1] = True
    mask[1, 3] = True
    mask[2, 0] = True
    mask[2, 2] = True
    kept, positions = reduce_features(features, mask)
    assert kept.shape == (4, 5)
    expected_positions = np.array([0 * 4 + 1, 1 * 4 + 3, 2 * 4 + 0, 2 * 4 + 2], dtype=np.int64)
    assert np.array_equal(positions, expected_positions)
    # Row order matches frame-major / token-major traversal.
    for idx, pos in enumerate(expected_positions):
        f = pos // 4
        tok = pos % 4
        assert np.array_equal(kept[idx], features[f, tok])


def test_reduce_features_rejects_shape_mismatch() -> None:
    features = _random_features(2, 3, d=4, seed=1)
    mask = np.zeros((2, 5), dtype=bool)
    with pytest.raises(ValueError, match="does not match"):
        reduce_features(features, mask)


def test_reduce_features_handles_empty_mask() -> None:
    features = _random_features(2, 3, d=4, seed=1)
    mask = np.zeros((2, 3), dtype=bool)
    kept, positions = reduce_features(features, mask)
    assert kept.shape == (0, 4)
    assert positions.shape == (0,)


# ---------------------------------------------------------------------------
# compute_pixel_novelty
# ---------------------------------------------------------------------------


def test_compute_pixel_novelty_basic_shape_and_values() -> None:
    # Two 4x4 grayscale frames; bottom-left 2x2 block changes by 10, rest static.
    frames = np.zeros((2, 4, 4), dtype=np.float32)
    frames[1, 2:4, 0:2] = 10.0
    novelty = compute_pixel_novelty(frames, grid_shape=(2, 2))
    assert novelty.shape == (2, 4)
    # Grid cells of size 2x2 → bottom-left cell is token index 2 (row 1, col 0).
    assert novelty[1, 2] == pytest.approx(10.0)
    # Other cells see no change.
    for idx in (0, 1, 3):
        assert novelty[1, idx] == 0.0
    # Default first_frame="mirror" → frame-0 equals frame-1.
    assert np.allclose(novelty[0], novelty[1])


def test_compute_pixel_novelty_first_frame_zero() -> None:
    frames = np.zeros((3, 4, 4), dtype=np.float32)
    frames[1, 2:4, 0:2] = 10.0
    frames[2, 0:2, 2:4] = 5.0
    novelty = compute_pixel_novelty(frames, grid_shape=(2, 2), first_frame="zero")
    assert novelty[0].tolist() == [0.0, 0.0, 0.0, 0.0]
    assert novelty[1, 2] == pytest.approx(10.0)
    # Frame 2 diff vs frame 1 hits BOTH regions (top-right gains 5, bottom-left loses 10).
    assert novelty[2, 1] == pytest.approx(5.0)
    assert novelty[2, 2] == pytest.approx(10.0)


def test_compute_pixel_novelty_first_frame_max() -> None:
    frames = np.zeros((3, 4, 4), dtype=np.float32)
    frames[1, 2:4, 0:2] = 10.0
    frames[2, 0:2, 2:4] = 5.0
    novelty = compute_pixel_novelty(frames, grid_shape=(2, 2), first_frame="max")
    # max across frames 1..F-1 per token.
    assert novelty[0, 1] == pytest.approx(5.0)
    assert novelty[0, 2] == pytest.approx(10.0)


def test_compute_pixel_novelty_color_frames() -> None:
    # 3-channel: per-pixel novelty is the mean over channels, matching
    # `codec_through.temporal._diff_plane`.
    frames = np.zeros((2, 2, 2, 3), dtype=np.float32)
    frames[1, 0, 0] = np.array([6.0, 0.0, 0.0], dtype=np.float32)  # mean diff = 2.0
    novelty = compute_pixel_novelty(frames, grid_shape=(2, 2))
    # grid matches pixel dims → each token sees exactly one pixel's diff.
    assert novelty[1, 0] == pytest.approx(2.0)
    assert novelty[1, 1] == 0.0


def test_compute_pixel_novelty_rejects_bad_shape() -> None:
    with pytest.raises(ValueError, match="F, H, W"):
        compute_pixel_novelty(np.zeros((4, 4), dtype=np.float32), grid_shape=(2, 2))


def test_compute_pixel_novelty_rejects_indivisible_grid() -> None:
    frames = np.zeros((2, 5, 5), dtype=np.float32)
    with pytest.raises(ValueError, match="must be divisible"):
        compute_pixel_novelty(frames, grid_shape=(2, 2))


def test_compute_pixel_novelty_handles_empty_and_single_frame() -> None:
    empty = compute_pixel_novelty(np.zeros((0, 4, 4), dtype=np.float32), grid_shape=(2, 2))
    assert empty.shape == (0, 4)
    single = compute_pixel_novelty(np.ones((1, 4, 4), dtype=np.float32), grid_shape=(2, 2))
    assert single.shape == (1, 4)
    # No diff available → all zero.
    assert np.all(single == 0.0)


def test_compute_pixel_novelty_matches_14x20_gemma_grid() -> None:
    # Sanity: the 560x560 → 14x20 Gemma case. 560/14 = 40, 560/20 = 28.
    rng = np.random.default_rng(42)
    frames = rng.standard_normal((3, 560, 560)).astype(np.float32)
    novelty = compute_pixel_novelty(frames, grid_shape=(14, 20))
    assert novelty.shape == (3, 280)
    # Every cell should see some non-zero diff (random data).
    assert (novelty[1] > 0).all()
    assert (novelty[2] > 0).all()


# ---------------------------------------------------------------------------
# Prefill-shortening bridge (prune_image_placeholders)
# ---------------------------------------------------------------------------


def _simple_prompt(image_token_id: int, frames: int, tokens_per_frame: int) -> np.ndarray:
    """Minimal text+image prompt: BOS + F × (IMG×T + SEP) + text_tail.

    Matches the Gemma 4 / Qwen 2.5-VL chat-template pattern where the
    tokenizer emits one run of ``T`` image-token placeholders per frame
    with non-image tokens (newline / end-of-image markers) separating
    consecutive frames. A 2026-04-18 runtime probe on
    ``mlx-community/gemma-4-e4b-it-4bit`` confirmed two frames produced
    two separate runs of 256 placeholders each (not one contiguous run
    of 512), so this helper must exercise the multi-run layout.
    """
    bos, text_a, sep, text_b = np.int64(1), np.int64(2), np.int64(99), np.int64(3)
    parts: list[np.ndarray] = [np.array([bos, text_a], dtype=np.int64)]
    for _ in range(frames):
        parts.append(np.full(tokens_per_frame, image_token_id, dtype=np.int64))
        parts.append(np.array([sep], dtype=np.int64))
    parts.append(np.array([text_b], dtype=np.int64))
    return np.concatenate(parts)


def test_prune_image_placeholders_keep_all_is_identity() -> None:
    input_ids = _simple_prompt(image_token_id=7, frames=2, tokens_per_frame=3)
    keep_mask = np.ones((2, 3), dtype=bool)
    result = prune_image_placeholders(input_ids, keep_mask, image_token_id=7)
    np.testing.assert_array_equal(result.input_ids, input_ids)
    np.testing.assert_array_equal(result.feature_indices, np.arange(6, dtype=np.int64))
    np.testing.assert_array_equal(result.kept_per_frame, np.array([3, 3], dtype=np.int64))


def test_prune_image_placeholders_keep_none_strips_all_images() -> None:
    input_ids = _simple_prompt(image_token_id=7, frames=2, tokens_per_frame=3)
    keep_mask = np.zeros((2, 3), dtype=bool)
    result = prune_image_placeholders(input_ids, keep_mask, image_token_id=7)
    # _simple_prompt layout (multi-run): [1, 2, 7, 7, 7, 99, 7, 7, 7, 99, 3].
    # Keeping none → image runs drop but separators (sep=99) stay:
    #                                    [1, 2,         99,          99, 3].
    expected = np.array([1, 2, 99, 99, 3], dtype=np.int64)
    np.testing.assert_array_equal(result.input_ids, expected)
    assert result.feature_indices.shape == (0,)
    np.testing.assert_array_equal(result.kept_per_frame, np.array([0, 0], dtype=np.int64))


def test_prune_image_placeholders_mixed_mask_preserves_frame_major_order() -> None:
    # Frames=2, tokens_per_frame=3. Keep tokens: frame 0 -> {0, 2}, frame 1 -> {1}.
    # Expected feature indices (flat, row-major): [0, 2, 4].
    input_ids = _simple_prompt(image_token_id=7, frames=2, tokens_per_frame=3)
    keep_mask = np.array([[True, False, True], [False, True, False]])
    result = prune_image_placeholders(input_ids, keep_mask, image_token_id=7)
    # _simple_prompt layout: [1, 2, 7, 7, 7, 99, 7, 7, 7, 99, 3].
    #                        bos ta  f0 f0 f0 sep f1 f1 f1 sep tb
    # After pruning: keep f0[0], f0[2], f1[1] → [1, 2, 7, 7, 99, 7, 99, 3].
    expected = np.array([1, 2, 7, 7, 99, 7, 99, 3], dtype=np.int64)
    np.testing.assert_array_equal(result.input_ids, expected)
    np.testing.assert_array_equal(result.feature_indices, np.array([0, 2, 4], dtype=np.int64))
    np.testing.assert_array_equal(result.kept_per_frame, np.array([2, 1], dtype=np.int64))


def test_prune_image_placeholders_rejects_non_1d_input_ids() -> None:
    input_ids = np.zeros((2, 3), dtype=np.int64)
    keep_mask = np.ones((2, 3), dtype=bool)
    with pytest.raises(ValueError, match="input_ids must be 1-D"):
        prune_image_placeholders(input_ids, keep_mask, image_token_id=7)


def test_prune_image_placeholders_rejects_non_2d_keep_mask() -> None:
    input_ids = _simple_prompt(image_token_id=7, frames=2, tokens_per_frame=3)
    keep_mask = np.ones(6, dtype=bool)
    with pytest.raises(ValueError, match="keep_mask must be 2-D"):
        prune_image_placeholders(input_ids, keep_mask, image_token_id=7)


def test_prune_image_placeholders_rejects_placeholder_count_mismatch() -> None:
    # Prompt has 2*3=6 placeholders but mask covers 3*3=9.
    input_ids = _simple_prompt(image_token_id=7, frames=2, tokens_per_frame=3)
    keep_mask = np.ones((3, 3), dtype=bool)
    with pytest.raises(ValueError, match="placeholders but keep_mask"):
        prune_image_placeholders(input_ids, keep_mask, image_token_id=7)


def test_prune_image_placeholders_handles_uint_input_dtype() -> None:
    input_ids = _simple_prompt(image_token_id=7, frames=1, tokens_per_frame=2).astype(np.uint32)
    keep_mask = np.array([[True, False]])
    result = prune_image_placeholders(input_ids, keep_mask, image_token_id=7)
    assert result.input_ids.dtype == np.uint32
    # _simple_prompt(F=1, T=2) → [1, 2, 7, 7, 99, 3]; keep f0[0] → [1, 2, 7, 99, 3].
    np.testing.assert_array_equal(result.input_ids, np.array([1, 2, 7, 99, 3], dtype=np.uint32))


def test_prune_image_placeholders_feature_indices_match_keep_mask_count() -> None:
    # Random mask; verify feature_indices length equals mask.sum() and only
    # hits positions that are True in keep_mask.
    rng = np.random.default_rng(0)
    f_count, t_count = 4, 8
    keep_mask = rng.random((f_count, t_count)) > 0.5
    input_ids = _simple_prompt(image_token_id=7, frames=f_count, tokens_per_frame=t_count)
    result = prune_image_placeholders(input_ids, keep_mask, image_token_id=7)
    assert result.feature_indices.size == int(keep_mask.sum())
    flat_mask = keep_mask.reshape(-1)
    assert bool(flat_mask[result.feature_indices].all())
    # Placeholder count in new input_ids must equal number of kept tokens.
    assert int((result.input_ids == 7).sum()) == int(keep_mask.sum())


def test_prune_image_placeholders_rejects_wrong_run_length() -> None:
    """Total placeholder count can match while per-frame layout is wrong.

    Regression for the validation gap a sub-agent flagged during the
    2026-04-18 OOM audit: if the processor emits T-1 placeholders for
    frame 0 and T+1 for frame 1, the total still equals F*T but the
    placeholder_cursor → (frame, token) binding is off-by-one, silently
    feeding frame-0 features into frame-1 slots. The function must
    reject this layout.
    """
    # Build a prompt with 3 + 5 image tokens (total 8 == 2*4) but wrong runs.
    seq = [np.int64(1), np.int64(2)]
    seq.extend([np.int64(7)] * 3)
    seq.append(np.int64(99))
    seq.extend([np.int64(7)] * 5)
    seq.append(np.int64(100))
    input_ids = np.asarray(seq, dtype=np.int64)
    keep_mask = np.ones((2, 4), dtype=bool)
    with pytest.raises(ValueError, match="image-token run 0 has length 3, expected 4"):
        prune_image_placeholders(input_ids, keep_mask, image_token_id=7)


def test_prune_image_placeholders_rejects_wrong_run_count() -> None:
    """Too few image-token runs: F*T placeholders live in fewer than F runs."""
    # 8 placeholders in a single run — total matches 2*4, but only 1 frame present.
    seq = [np.int64(1), np.int64(2)]
    seq.extend([np.int64(7)] * 8)
    seq.append(np.int64(100))
    input_ids = np.asarray(seq, dtype=np.int64)
    keep_mask = np.ones((2, 4), dtype=bool)
    with pytest.raises(ValueError, match="image-token run 0 has length 8, expected 4"):
        prune_image_placeholders(input_ids, keep_mask, image_token_id=7)


def test_prune_image_placeholders_accepts_trailing_image_tokens() -> None:
    """An input_ids that ends with image tokens (no trailing non-image) is valid."""
    # Layout: [text, img, img, text, img, img]  — 2 runs of length 2, T=2, F=2.
    seq = [np.int64(1)]
    seq.extend([np.int64(7)] * 2)
    seq.append(np.int64(2))
    seq.extend([np.int64(7)] * 2)
    input_ids = np.asarray(seq, dtype=np.int64)
    keep_mask = np.ones((2, 2), dtype=bool)
    result = prune_image_placeholders(input_ids, keep_mask, image_token_id=7)
    # Keep-all → identity-shaped output.
    np.testing.assert_array_equal(result.input_ids, input_ids)
