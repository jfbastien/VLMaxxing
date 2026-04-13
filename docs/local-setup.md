# Local Setup

This file is intentionally concrete. It answers two questions:

1. What is already present on this machine?
2. What do we still need before meaningful local video/VLM work can start?

## Current Local State

Checked locally on 2026-04-13:

- `uv`: installed
- `ffmpeg`: installed
- `llama-server`: installed
- `git-lfs`: installed
- `yt-dlp`: missing
- `mlx-vlm`: missing
- Python packages such as `torch`, `av`, and `mlx_vlm`: not installed in the current environment

## Current Models

Present under `~/models`:

- `Qwen3-0.6B-Q8_0.gguf`
- `Qwen3-1.7B-Q8_0.gguf`
- `Qwen3-8B-Q4_K_M.gguf`

These are useful for text experiments and harness work, but they do not unblock the video/VLM track because they are text-only GGUF models.

## Recommended Next Downloads

Download in this order:

1. `mlx-community/Qwen2.5-VL-3B-Instruct-4bit`
2. `mlx-community/gemma-4-e4b-it-4bit`
3. `mlx-community/Qwen2.5-VL-7B-Instruct-4bit`

## Why These Three

### `mlx-community/Qwen2.5-VL-3B-Instruct-4bit`

Source:

- <https://huggingface.co/mlx-community/Qwen2.5-VL-3B-Instruct-4bit>

Why first:

- small enough for fast local iteration
- directly aligned with the seed whitepaper's model family
- good baseline for mechanism work

Published size on Hugging Face:

- about 3.07 GB

### `mlx-community/gemma-4-e4b-it-4bit`

Source:

- <https://huggingface.co/mlx-community/gemma-4-e4b-it-4bit>
- <https://ai.google.dev/gemma/docs/get_started>

Why second:

- official Google guidance places Gemma 4 E4B in the "mobile devices and laptops" tier
- good small multimodal comparison against Qwen
- useful if we want a Gemma-side check without jumping to large-server models

Published size on Hugging Face:

- about 5.22 GB

### `mlx-community/Qwen2.5-VL-7B-Instruct-4bit`

Source:

- <https://huggingface.co/mlx-community/Qwen2.5-VL-7B-Instruct-4bit>

Why third:

- use for confirmation runs on smaller subsets once the harness is stable
- too expensive for every iteration on a 16 GB Air, but still useful for spot checks

Published size on Hugging Face:

- about 5.64 GB

## Optional Model

### `mlx-community/gemma-4-e2b-it-4bit`

Source:

- <https://huggingface.co/mlx-community/gemma-4-e2b-it-4bit>

Why optional:

- attractive if we want an even lighter Gemma experiment
- likely valuable for responsiveness testing and harness bring-up

Published size on Hugging Face:

- about 3.58 GB

## What Not To Download First

- Gemma 4 31B: wrong scale for routine local iteration on this machine
- more text-only GGUFs: they do not help with the video/VLM bottleneck
- too many model variants before the harness exists: that just increases download cost and choice confusion

## Recommended Tool Additions

### Must-have

- `mlx-vlm`

Reason:

- this is the most practical way to run open VLMs locally on Apple Silicon

Source:

- <https://github.com/Blaizzy/mlx-vlm>

### Strongly Recommended

- `yt-dlp`

Reason:

- useful for fetching reproducible public clips for the real-video bucket set
- easier than manually sourcing clip files

### Likely Needed Soon

- `av` / PyAV

Reason:

- useful Python path for video decode and side-data inspection

## Is `llama.cpp` Enough?

No, not for the main research path.

`llama.cpp` is still useful:

- for text-only helpers
- for small harness experiments
- for OpenAI-compatible local serving

But the main local VLM/video path should start with MLX-VLM, not with GGUF-first multimodal plumbing.

The reason is practical:

- MLX is Apple-first
- MLX-VLM already supports selected video-chat models
- the current question is about video VLM behavior, not generic text inference
