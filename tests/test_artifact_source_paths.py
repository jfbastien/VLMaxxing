from __future__ import annotations

from scripts.audit_artifact_integrity import _iter_source_paths as iter_audit_source_paths
from scripts.audit_artifact_integrity import _source_path_problem


def test_artifact_audit_source_paths_include_suffixed_lists() -> None:
    payload = {
        "source": "research/experiments/2026/example.json",
        "uniform_dense_source_paths": [
            "research/experiments/2026/artifacts/dense/frame_4_summary.json",
            "research/experiments/2026/artifacts/dense/frame_8_summary.json",
        ],
        "nested": {"summary_source": "paper/figures/example_data.json"},
    }

    expected = {
        "research/experiments/2026/example.json",
        "research/experiments/2026/artifacts/dense/frame_4_summary.json",
        "research/experiments/2026/artifacts/dense/frame_8_summary.json",
        "paper/figures/example_data.json",
    }
    assert set(iter_audit_source_paths(payload)) == expected


def test_artifact_audit_rejects_non_release_source_roots() -> None:
    assert _source_path_problem("results/local_only.json") is not None
    assert _source_path_problem("/tmp/local_only.json") is not None
    assert _source_path_problem("~/local_only.json") is not None
    assert _source_path_problem("notes/private.md") is not None
    assert _source_path_problem("research/experiments/2026/artifacts/example.json") is None
