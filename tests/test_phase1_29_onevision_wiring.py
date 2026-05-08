from __future__ import annotations

import importlib.util
import inspect
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from codec_through.codec.continuous_score import CodecScoreSource

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER_PATH = REPO_ROOT / "scripts" / "run_phase1_29_planner_accuracy_probe.py"


def _load_probe_module() -> Any:
    spec = importlib.util.spec_from_file_location("phase1_29_probe_for_test", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load module spec for {RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_probe_module_import_does_not_require_pyav() -> None:
    class BlockAvFinder:
        def find_spec(self, fullname: str, path: object = None, target: object = None) -> None:
            if fullname == "av":
                raise ImportError("blocked av import for --help/import boundary test")
            return None

    finder = BlockAvFinder()
    previous_av = sys.modules.pop("av", None)
    sys.meta_path.insert(0, finder)
    try:
        module = _load_probe_module()
    finally:
        sys.meta_path.remove(finder)
        if previous_av is not None:
            sys.modules["av"] = previous_av

    assert module.CODEC_SCORE_SOURCE_CHOICES == ("novel_coded", "motion", "residual", "fused")


def test_help_smoke_does_not_import_model_runtime() -> None:
    completed = subprocess.run(
        [sys.executable, str(RUNNER_PATH), "--help"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "--codec-score-source" in completed.stdout
    assert "--fusion-mode" in completed.stdout


def test_validate_codec_score_args_rejects_bad_weights() -> None:
    module = _load_probe_module()

    with pytest.raises(ValueError, match="motion-weight must be finite"):
        module._validate_codec_score_args(
            codec_score_source=CodecScoreSource.FUSED,
            motion_weight=float("nan"),
            residual_weight=1.0,
        )
    with pytest.raises(ValueError, match="residual-weight must be non-negative"):
        module._validate_codec_score_args(
            codec_score_source=CodecScoreSource.FUSED,
            motion_weight=1.0,
            residual_weight=-1.0,
        )
    with pytest.raises(ValueError, match="requires at least one positive fusion weight"):
        module._validate_codec_score_args(
            codec_score_source=CodecScoreSource.FUSED,
            motion_weight=0.0,
            residual_weight=0.0,
        )


def test_runtime_module_guard_fails_before_lazy_load() -> None:
    module = _load_probe_module()
    module.runner = None
    module.mx = None

    with pytest.raises(RuntimeError, match="call _load_runtime_modules"):
        module._require_runtime_modules()


def test_validate_no_windowed_items_rejects_before_cache_reuse() -> None:
    module = _load_probe_module()
    item = SimpleNamespace(item_id="videomme:short:267-2", start_seconds=0.0, end_seconds=None)

    with pytest.raises(ValueError, match="windowed clips is not implemented"):
        module._validate_no_windowed_items([item])


def test_precompute_cache_rejects_version_and_metadata_mismatch(tmp_path: Path) -> None:
    module = _load_probe_module()
    cache_path = tmp_path / "precompute.json"

    cache_path.write_text(json.dumps({"version": -1, "metadata": {}, "items": []}) + "\n")
    with pytest.raises(ValueError, match="has version"):
        module._load_precompute_cache(
            cache_path,
            expected_metadata={},
            item_by_id={},
        )

    cache_path.write_text(
        json.dumps(
            {
                "version": module.PRECOMPUTE_CACHE_VERSION,
                "metadata": {"codec_score_source": "motion"},
                "items": [],
            }
        )
        + "\n"
    )
    with pytest.raises(ValueError, match="metadata does not match"):
        module._load_precompute_cache(
            cache_path,
            expected_metadata={"codec_score_source": "residual"},
            item_by_id={},
        )


def test_precompute_cache_metadata_records_item_windows() -> None:
    module = _load_probe_module()
    item = SimpleNamespace(
        item_id="videomme:short:267-2",
        video_path=Path("data/benchmarks/videomme/videos/Atf_Af1q_5w.mp4"),
        start_seconds=None,
        end_seconds=None,
    )

    metadata = module._precompute_cache_metadata(
        manifest_path=Path("research/benchmark_manifests/videomme_dev_v1_short_only.toml"),
        items=[item],
        frame_count=8,
        planner_config=module.DEFAULT_PLANNER,
        calibration_source="live-pixel",
        reference_summary=None,
        codec_score_source=CodecScoreSource.FUSED,
        fusion_mode="weighted",
        motion_weight=1.0,
        residual_weight=1.0,
        normalize_fusion_inputs=True,
    )

    assert metadata["version"] == module.PRECOMPUTE_CACHE_VERSION
    assert metadata["item_windows"] == [
        {
            "item_id": item.item_id,
            "video_path": str(item.video_path),
            "start_seconds": None,
            "end_seconds": None,
        }
    ]
    assert metadata["codec_score_source"] == "fused"


def test_recorded_h264_extractor_defaults_match_constructor_signature() -> None:
    from codec_through.codec.h264_metadata import H264MetadataExtractor

    module = _load_probe_module()
    signature = inspect.signature(H264MetadataExtractor.__init__)
    defaults: dict[str, Any] = {
        name: parameter.default
        for name, parameter in signature.parameters.items()
        if name in module.H264_EXTRACTOR_DEFAULTS
    }

    assert defaults == module.H264_EXTRACTOR_DEFAULTS
