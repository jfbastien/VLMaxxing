from __future__ import annotations

import numpy as np
import pytest

from tests._mlx_probe import mlx_is_usable

if not mlx_is_usable():
    pytest.skip(
        "mlx.core not usable on this host (import or Metal-init fails); see tests/_mlx_probe.py",
        allow_module_level=True,
    )

import mlx.core as mx

pytest.importorskip("mlx_vlm")

import scripts.run_novelty_pruning_gemma as runner


def test_prune_placeholders_none_is_strict_bypass(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_prune(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("none mode must not call prune_image_placeholders")

    monkeypatch.setattr(runner, "prune_image_placeholders", fail_prune)

    input_ids_np = np.array([101, 7, 7, 102, 7, 7, 103], dtype=np.int64)
    dense_input_ids = mx.array(input_ids_np[None, :])
    vision_features = mx.array(np.ones((1, 4, 2), dtype=np.float32))
    keep_mask = np.ones((2, 2), dtype=bool)

    result = runner._apply_placeholder_prune_for_generation(
        prune_placeholders="none",
        input_ids_np=input_ids_np,
        dense_input_ids=dense_input_ids,
        vision_features=vision_features,
        keep_mask=keep_mask,
        image_token_id=7,
    )

    assert result.input_ids is dense_input_ids
    assert result.image_features is vision_features
    assert result.kept_per_frame == [2, 2]
    assert result.elapsed_ms == 0.0
    assert result.bypassed is True
