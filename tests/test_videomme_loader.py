"""Unit tests for VideoMME loader helpers in scripts/run_benchmark_track_a.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from tests._mlx_probe import mlx_is_usable

if not mlx_is_usable():
    pytest.skip(
        "mlx.core not usable on this host (import or Metal-init fails); see tests/_mlx_probe.py",
        allow_module_level=True,
    )

RUNNER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_benchmark_track_a.py"
RUNNER_MODULE_NAME = "_videomme_runner_under_test"


def _load_runner_module() -> ModuleType:
    if RUNNER_MODULE_NAME in sys.modules:
        return sys.modules[RUNNER_MODULE_NAME]
    spec = importlib.util.spec_from_file_location(RUNNER_MODULE_NAME, RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot build spec for {RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[RUNNER_MODULE_NAME] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(RUNNER_MODULE_NAME, None)
        raise
    return module


RUNNER = _load_runner_module()


def test_choice_text_strips_letter_prefix() -> None:
    assert RUNNER._videomme_choice_text("A. Playing piano") == "Playing piano"
    assert RUNNER._videomme_choice_text("B. A dog barks") == "A dog barks"


def test_choice_text_passthrough_without_prefix() -> None:
    assert RUNNER._videomme_choice_text("Playing piano") == "Playing piano"
    assert RUNNER._videomme_choice_text("A dog barks") == "A dog barks"


def test_parse_videomme_item_id_roundtrip() -> None:
    duration, question_id = RUNNER._parse_videomme_item_id("videomme:short:q_42")
    assert duration == "short"
    assert question_id == "q_42"


def test_parse_videomme_item_id_rejects_wrong_prefix() -> None:
    with pytest.raises(ValueError):
        RUNNER._parse_videomme_item_id("tomato:short:q_42")


def test_parse_videomme_item_id_rejects_empty_fields() -> None:
    with pytest.raises(ValueError):
        RUNNER._parse_videomme_item_id("videomme::q_42")


def test_videomme_item_from_row_valid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    video_path = tmp_path / "videomme_videos" / "abc123.mp4"
    video_path.parent.mkdir(parents=True)
    video_path.write_bytes(b"fake")
    monkeypatch.setattr(RUNNER, "VIDEOMME_VIDEO_DIR", video_path.parent)
    row = {
        "videoID": "abc123",
        "duration": "short",
        "question_id": "q_42",
        "question": "What is in the video?",
        "options": ["A. Dog", "B. Cat", "C. Fish", "D. Bird"],
        "answer": "B",
    }
    item = RUNNER._videomme_item_from_row(row)
    assert item.benchmark == "videomme"
    assert item.item_id == "videomme:short:q_42"
    assert item.group == "short"
    assert item.candidates == ["Dog", "Cat", "Fish", "Bird"]
    assert item.answer_index == 1
    assert item.video_path == video_path


def test_videomme_item_from_row_rejects_bad_answer_letter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    video_path = tmp_path / "videomme_videos" / "abc123.mp4"
    video_path.parent.mkdir(parents=True)
    video_path.write_bytes(b"fake")
    monkeypatch.setattr(RUNNER, "VIDEOMME_VIDEO_DIR", video_path.parent)
    row = {
        "videoID": "abc123",
        "duration": "short",
        "question_id": "q_42",
        "question": "What is in the video?",
        "options": ["A. Dog", "B. Cat"],
        "answer": "Q",
    }
    with pytest.raises(ValueError):
        RUNNER._videomme_item_from_row(row)


def test_videomme_item_from_row_rejects_out_of_range_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    video_path = tmp_path / "videomme_videos" / "abc123.mp4"
    video_path.parent.mkdir(parents=True)
    video_path.write_bytes(b"fake")
    monkeypatch.setattr(RUNNER, "VIDEOMME_VIDEO_DIR", video_path.parent)
    row = {
        "videoID": "abc123",
        "duration": "short",
        "question_id": "q_42",
        "question": "What is in the video?",
        "options": ["A. Dog", "B. Cat"],
        "answer": "C",
    }
    with pytest.raises(ValueError):
        RUNNER._videomme_item_from_row(row)


def test_find_videomme_video_raises_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(RUNNER, "VIDEOMME_VIDEO_DIR", tmp_path / "nonexistent")
    with pytest.raises(FileNotFoundError):
        RUNNER._find_videomme_video("nope")


def test_find_videomme_video_locates_direct_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    video_dir = tmp_path / "vmme_videos"
    video_dir.mkdir()
    target = video_dir / "xyz.mp4"
    target.write_bytes(b"fake")
    monkeypatch.setattr(RUNNER, "VIDEOMME_VIDEO_DIR", video_dir)
    assert RUNNER._find_videomme_video("xyz") == target


def test_find_videomme_video_detects_ambiguous_matches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    video_dir = tmp_path / "vmme_videos"
    (video_dir / "sub1").mkdir(parents=True)
    (video_dir / "sub2").mkdir(parents=True)
    (video_dir / "sub1" / "xyz.mp4").write_bytes(b"fake")
    (video_dir / "sub2" / "xyz.mkv").write_bytes(b"fake")
    monkeypatch.setattr(RUNNER, "VIDEOMME_VIDEO_DIR", video_dir)
    with pytest.raises(RuntimeError):
        RUNNER._find_videomme_video("xyz")


def test_load_manifest_accepts_videomme(tmp_path: Path) -> None:
    manifest_path = tmp_path / "videomme_manifest.toml"
    manifest_path.write_text(
        'benchmark = "videomme"\n'
        'description = "smoke test manifest"\n'
        'item_ids = ["videomme:short:q_1", "videomme:short:q_2"]\n'
    )
    manifest = RUNNER._load_manifest(manifest_path)
    assert manifest.benchmark == "videomme"
    assert manifest.item_ids == ["videomme:short:q_1", "videomme:short:q_2"]
