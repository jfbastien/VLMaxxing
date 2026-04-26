from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_phase1_30ac_smoke_validator_accepts_active_followups(tmp_path: Path) -> None:
    jsonl = tmp_path / "smoke.jsonl"
    _write_jsonl(
        jsonl,
        [
            {
                "item_id": "videomme:short:001-1",
                "q_index": 0,
                "prefix_hit": 0,
                "image_token_count": 8,
                "image_tokens_recomputed": 8,
                "vision_pruning_active": False,
                "vision_tower_keep_rate": 1.0,
            },
            {
                "item_id": "videomme:short:001-2",
                "q_index": 1,
                "prefix_hit": 0,
                "image_token_count": 8,
                "image_tokens_recomputed": 8,
                "vision_pruning_active": True,
                "vision_tower_keep_rate": 0.5,
                "reset_cache_between_queries": True,
                "refresh_reason": "per_query_reset",
            },
            {
                "item_id": "videomme:short:001-3",
                "q_index": 2,
                "prefix_hit": 0,
                "image_token_count": 8,
                "image_tokens_recomputed": 8,
                "vision_pruning_active": True,
                "vision_tower_keep_rate": 0.5,
                "reset_cache_between_queries": True,
                "refresh_reason": "per_query_reset",
            },
        ],
    )

    subprocess.run(
        [
            sys.executable,
            "scripts/validate_phase1_30ac_smoke.py",
            "--jsonl",
            str(jsonl),
        ],
        check=True,
    )


def test_phase1_30ac_smoke_validator_rejects_cached_followups(tmp_path: Path) -> None:
    jsonl = tmp_path / "smoke.jsonl"
    _write_jsonl(
        jsonl,
        [
            {"item_id": "videomme:short:001-1", "q_index": 0},
            {
                "item_id": "videomme:short:001-2",
                "q_index": 1,
                "prefix_hit": 8,
                "image_token_count": 8,
                "image_tokens_recomputed": 0,
                "vision_pruning_active": False,
                "vision_tower_keep_rate": 0.5,
                "reset_cache_between_queries": True,
                "refresh_reason": "per_query_reset",
            },
            {
                "item_id": "videomme:short:001-3",
                "q_index": 2,
                "prefix_hit": 8,
                "image_token_count": 8,
                "image_tokens_recomputed": 0,
                "vision_pruning_active": False,
                "vision_tower_keep_rate": 0.5,
                "reset_cache_between_queries": True,
                "refresh_reason": "per_query_reset",
            },
        ],
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_phase1_30ac_smoke.py",
            "--jsonl",
            str(jsonl),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "prefix_hit=8, expected 0" in result.stderr


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ({"reset_cache_between_queries": False}, "reset_cache_between_queries is not true"),
        ({"refresh_reason": "cache_hit"}, "refresh_reason='cache_hit'"),
        ({"image_token_count": 0}, "image_token_count=0, expected >0"),
        ({"image_tokens_recomputed": 4}, "recomputed 4/8 image tokens"),
        ({"vision_tower_keep_rate": 1.0}, "follow-up keep_rate=1.0, expected <1.0"),
        ({"vision_pruning_active": False}, "vision_pruning_active is not true"),
    ],
)
def test_phase1_30ac_smoke_validator_rejects_each_followup_invariant(
    tmp_path: Path,
    mutation: dict[str, Any],
    expected: str,
) -> None:
    row = {
        "item_id": "videomme:short:001-2",
        "q_index": 1,
        "prefix_hit": 0,
        "image_token_count": 8,
        "image_tokens_recomputed": 8,
        "vision_pruning_active": True,
        "vision_tower_keep_rate": 0.5,
        "reset_cache_between_queries": True,
        "refresh_reason": "per_query_reset",
    }
    row.update(mutation)
    jsonl = tmp_path / "smoke.jsonl"
    _write_jsonl(
        jsonl,
        [
            {"item_id": "videomme:short:001-1", "q_index": 0},
            row,
            {
                "item_id": "videomme:short:001-3",
                "q_index": 2,
                "prefix_hit": 0,
                "image_token_count": 8,
                "image_tokens_recomputed": 8,
                "vision_pruning_active": True,
                "vision_tower_keep_rate": 0.5,
                "reset_cache_between_queries": True,
                "refresh_reason": "per_query_reset",
            },
        ],
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_phase1_30ac_smoke.py",
            "--jsonl",
            str(jsonl),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert expected in result.stderr
