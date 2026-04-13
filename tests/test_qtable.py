import numpy as np

from codec_through.qtable import CANDIDATE, COMPLEX, FLAT, aggregate_to_token_grid


def test_aggregate_to_token_grid_preserves_uniform_scores() -> None:
    blocks = np.full((7, 7), 5, dtype=np.int32)
    aggregated = aggregate_to_token_grid(blocks, token_h=2, token_w=2, patch_px=28)
    assert aggregated.shape == (2, 2)
    assert np.allclose(aggregated, 5.0)


def test_aggregate_to_token_grid_respects_spatial_bias() -> None:
    blocks = np.zeros((7, 7), dtype=np.int32)
    blocks[:4, :4] = 12
    aggregated = aggregate_to_token_grid(blocks, token_h=2, token_w=2, patch_px=28)
    assert aggregated[0, 0] > aggregated[1, 1]


def test_qtable_class_labels_are_stable() -> None:
    scores = np.array([[0.0, 5.0, 30.0]])
    classification = np.full(scores.shape, CANDIDATE, dtype=np.int32)
    classification[scores <= 3] = FLAT
    classification[scores > 20] = COMPLEX
    assert int(classification[0, 0]) == FLAT
    assert int(classification[0, 1]) == CANDIDATE
    assert int(classification[0, 2]) == COMPLEX
