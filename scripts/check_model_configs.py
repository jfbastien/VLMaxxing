"""Check local model configs for geometry-sensitive experiments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from codec_through.temporal import block_size_from_vision_config

DEFAULT_MODEL_DIR = Path.home() / "models"
DEFAULT_MODELS = [
    "Qwen2.5-VL-3B-Instruct-4bit",
    "gemma-4-e4b-it-4bit",
    "Qwen2.5-VL-7B-Instruct-4bit",
]


def _load_config(model_root: Path) -> dict[str, Any]:
    config_path = model_root / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"missing config: {config_path}")
    return cast(dict[str, Any], json.loads(config_path.read_text()))


def _vision_config(config: dict[str, Any]) -> dict[str, Any]:
    vision_config = config.get("vision_config")
    if not isinstance(vision_config, dict):
        raise ValueError("config.json does not contain a dict vision_config")
    return vision_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--models-root",
        type=Path,
        default=DEFAULT_MODEL_DIR,
        help="directory containing local model subdirectories",
    )
    parser.add_argument(
        "models",
        nargs="*",
        default=DEFAULT_MODELS,
        help="model subdirectories to inspect",
    )
    args = parser.parse_args()

    for model_name in args.models:
        model_root = args.models_root / model_name
        config = _load_config(model_root)
        vision_config = _vision_config(config)
        block_size = block_size_from_vision_config(vision_config)
        print(model_name)
        print(f"  block_size_px: {block_size}")
        if "fullatt_block_indexes" in vision_config:
            print(f"  fullatt_block_indexes: {vision_config['fullatt_block_indexes']}")
        print(f"  patch_size: {vision_config.get('patch_size')}")
        print(f"  spatial_merge_size: {vision_config.get('spatial_merge_size', 1)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
