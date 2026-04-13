# Local Setup

This file describes the repo contract for local development.

It intentionally avoids treating one machine's current global state as the
source of truth. The source of truth is:

- `pyproject.toml`
- `uv.lock`
- this setup document for external tools and model assets

## External Tools

Required outside Python:

- `uv`
- `ffmpeg`
- `git-lfs`

Useful but optional:

- `yt-dlp` for reproducible public clip acquisition

## Python Environments

Base repo checks:

```bash
uv sync --group dev
```

Research helpers such as PyAV:

```bash
uv sync --group dev --group research
```

Local MLX / MLX-VLM work:

```bash
uv sync --group dev --group research --group vlm
```

The repo assumes you run commands through `uv run ...`, not through an unrelated
system Python environment.

## Verification Commands

Base verification:

```bash
uv run ruff check .
uv run mypy src tests
uv run pytest
```

Optional research/VLM verification:

```bash
uv run python -c "import av; print(av.__version__)"
uv run python -c "import mlx, mlx_vlm; print(mlx_vlm.__file__)"
ffmpeg -version
git-lfs --version
```

## Recommended Models

The repo's current model order is:

1. `Qwen2.5-VL-3B-Instruct-4bit`
2. `Qwen2.5-VL-7B-Instruct-4bit`
3. `gemma-4-e4b-it-4bit`

Why this order:

- `Qwen2.5-VL-3B` is the fastest local bring-up path for Track A work
- `Qwen2.5-VL-7B` is the closest confirmation path to the imported whitepaper
- `gemma-4-e4b-it-4bit` is the cross-family check once geometry-specific helpers are explicit

This repo does not require a specific model directory layout, but the current
local convention is `~/models/<model-name>/`.

## What This Repo Does Not Assume

- your shell's global Python packages
- text-only GGUF models for the video/VLM path
- that every machine can reproduce 7B full-benchmark runs

For reproducibility notes and machine limits, keep the durable record in the
experiment note and [PLAN.md](../PLAN.md), not in this setup file.
