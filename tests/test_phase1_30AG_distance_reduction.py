"""Math-equivalence regression test for the 1.30AG K/V cosine reduction.

Background
==========

The original `_distance_for_windows` math in
`scripts/run_phase1_30AG_kcache_distance_probe.py` used unbounded
sum-of-squares reductions::

    dot   = mx.sum(l_flat * r_flat)
    denom = mx.sqrt(mx.sum(l_flat * l_flat)) * mx.sqrt(mx.sum(r_flat * r_flat))
    cosine = dot / mx.maximum(denom, mx.array(1e-12))

When the live K/V cache contained a rare element near bf16 max,
`mx.sum(l_flat * l_flat)` overflowed to inf and cosine became NaN
even for bit-identical caches. The fix is to use mean-form, which
is mathematically identical for cosine (the N factor cancels in the
ratio) and lets the MLX runtime keep its higher-precision accumulator
contained::

    dot   = mx.mean(l_flat * r_flat)
    denom = mx.sqrt(mx.mean(l_flat * l_flat)) * mx.sqrt(mx.mean(r_flat * r_flat))
    cosine = dot / mx.maximum(denom, mx.array(1e-12))

This file pins the *math equivalence* on fp32, where both forms must
agree to high precision. The bf16/fp16 overflow regime that produced
the original NaN is a property of MLX's reduction-accumulator dtype on
Apple Metal and is verified by re-running the probe (~40 min, sandbox
off, GPU required), not by this CPU-side test.
"""

from __future__ import annotations

import numpy as np
import pytest


def _cosine_sum_form(left: np.ndarray, right: np.ndarray) -> float:
    """Original 1.30AG implementation, ported to numpy with same dtype path."""
    dot = (left * right).sum(dtype=left.dtype)
    denom = np.sqrt((left * left).sum(dtype=left.dtype)) * np.sqrt(
        (right * right).sum(dtype=left.dtype)
    )
    return float(dot / max(float(denom), 1e-12))


def _cosine_mean_form(left: np.ndarray, right: np.ndarray) -> float:
    """Proposed fix: mean-form. N cancels mathematically; intermediates bounded."""
    dot = (left * right).mean(dtype=left.dtype)
    denom = np.sqrt((left * left).mean(dtype=left.dtype)) * np.sqrt(
        (right * right).mean(dtype=left.dtype)
    )
    return float(dot / max(float(denom), 1e-12))


@pytest.mark.parametrize("form", [_cosine_sum_form, _cosine_mean_form])
def test_identical_vectors_cosine_one(form):
    rng = np.random.default_rng(0)
    v = rng.standard_normal(1024).astype(np.float32)
    assert form(v, v) == pytest.approx(1.0, abs=1e-5)


@pytest.mark.parametrize("form", [_cosine_sum_form, _cosine_mean_form])
def test_orthogonal_vectors_cosine_zero(form):
    left = np.array([1.0, 0.0, 1.0, 0.0] * 256, dtype=np.float32)
    right = np.array([0.0, 1.0, 0.0, 1.0] * 256, dtype=np.float32)
    assert form(left, right) == pytest.approx(0.0, abs=1e-6)


@pytest.mark.parametrize("form", [_cosine_sum_form, _cosine_mean_form])
def test_antiparallel_cosine_minus_one(form):
    rng = np.random.default_rng(1)
    v = rng.standard_normal(1024).astype(np.float32)
    assert form(v, -v) == pytest.approx(-1.0, abs=1e-5)


@pytest.mark.parametrize("form", [_cosine_sum_form, _cosine_mean_form])
def test_scaling_invariance(form):
    rng = np.random.default_rng(2)
    v = rng.standard_normal(1024).astype(np.float32)
    assert form(v, 2.0 * v) == pytest.approx(1.0, abs=1e-5)


def test_sum_and_mean_forms_agree_on_fp32():
    """Both reduction forms must produce numerically identical cosines on fp32
    inputs that do not overflow. The fix is a pure refactor at this precision."""
    rng = np.random.default_rng(3)
    left = rng.standard_normal(8192).astype(np.float32)
    right = rng.standard_normal(8192).astype(np.float32)
    assert _cosine_sum_form(left, right) == pytest.approx(_cosine_mean_form(left, right), abs=1e-6)
