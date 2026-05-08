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

Useful but optional:

- `yt-dlp` for reproducible public clip acquisition

## Python Environments

Base repo checks and CPU decode/codec helpers:

```bash
uv sync --locked --group dev --group research
```

Local MLX / MLX-VLM work:

```bash
uv sync --locked --group dev --group research --group vlm
```

Benchmark-native TOMATO / MVBench helpers:

```bash
uv sync --locked --group dev --group research --group vlm --group benchmark
```

The repo assumes you run commands through `uv run ...`, not through an unrelated
system Python environment.

Important current note:

- the Qwen2.5-VL video processor path requires `torch` and `torchvision` in the
  repo environment
- these are included in the `vlm` group so
  `uv sync --locked --group ... --group vlm`
  is the intended setup path

## Verification Commands

Base verification:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
uv run python scripts/audit_artifact_integrity.py
```

Optional research/VLM verification:

```bash
uv run python -c "import av; print(av.__version__)"
uv run python -c "import mlx, mlx_vlm; print(mlx_vlm.__file__)"
uv run python scripts/check_model_configs.py
ffmpeg -version
```

Scale-out streaming baseline recordings are not part of the normal checkout.
Scripts that consume them look under `data/recordings/` by default and can be
pointed elsewhere with `CODEC_THROUGH_RECORDINGS_DIR` or `--recordings-dir`.

## Recommended Models

The repo's current model order is:

1. `Qwen2.5-VL-3B-Instruct-4bit`
2. `gemma-4-e4b-it-4bit`
3. `Qwen2.5-VL-7B-Instruct-4bit`

Why this order:

- `Qwen2.5-VL-3B` is the fastest local bring-up path for Track A work
- `gemma-4-e4b-it-4bit` is the early cross-family check for geometry and quality-floor differences
- `Qwen2.5-VL-7B` is the closest confirmation path to the imported predecessor results

This repo does not require a specific model directory layout, but the current
local convention is `${MODEL_ROOT:-$HOME/models}/<model-name>/`.

Gemma note:

- Gemma 4 exposes configurable visual token budgets
- for this repo's initial pilot work, freeze Gemma E4B at `280` visual tokens
  unless an experiment note explicitly says otherwise

## Evaluation Data Setup

Benchmark assets are large and are ignored by git through `/data/`. If you
have a sibling checkout with populated benchmark assets, prefer a symlink over
duplicating the videos:

```bash
mv data/benchmarks /private/tmp/codec-through-2-benchmarks-backup
ln -s ~/s/codec-through/data/benchmarks data/benchmarks
uv run python scripts/preflight_onevision_vlmaxxing.py --scope all --no-write-json
```

The OneVision preflight also looks for a sibling `codec-through` checkout and
prints local restore commands when a symlink is not present. If that sibling
checkout is absent, use the fetch scripts below.

Bring up the local primary corpus and derived H.264 files:

```bash
uv run python scripts/fetch_corpus.py --tier primary --encode
```

Generate the scored synthetic local stress clips:

```bash
uv run python scripts/generate_synthetic_corpus.py
```

Optional predecessor cross-check clips:

```bash
uv run python scripts/fetch_corpus.py --tier crosscheck
```

TOMATO and MVBench benchmark-native assets:

```bash
uv run python scripts/fetch_benchmarks.py --dataset both --mode all
```

Here `--dataset both` means TOMATO + MVBench. VideoMME metadata is handled by
`scripts/fetch_benchmarks.py`, but the videos are intentionally fetched by
manifest subset. See
[docs/videomme-download-handoff.md](videomme-download-handoff.md) for the
`scripts/fetch_videomme_subset.py` flow.

The source of truth for clip ids and local paths is:

- [data/corpus/manifest.toml](../data/corpus/manifest.toml)

For the OneVision + VLMaxxing real-video visualization gate, the three
paper-facing benchmark clip windows are pinned in
`scripts/preflight_onevision_vlmaxxing.py` and
`scripts/render_onevision_vlmaxxing_explainer_videos.py`, because those are
benchmark-native source videos rather than primary local corpus clips.

The policy for what belongs in each corpus tier is:

- [docs/clip-policy.md](clip-policy.md)
- [docs/benchmark-setup.md](benchmark-setup.md)

## What This Repo Does Not Assume

- your shell's global Python packages
- text-only GGUF models for the video/VLM path
- that every machine can reproduce 7B full-benchmark runs

## Clips And Local Assets

This repo does not check fetched or source media into git. Generated paper
figures, thumbnails, and explicit review artifacts are handled by the scoped
policy in [docs/clip-policy.md](clip-policy.md).

For the local clip policy, primary corpus, and predecessor cross-check set, see
[docs/clip-policy.md](clip-policy.md) and
[data/corpus/manifest.toml](../data/corpus/manifest.toml).

For reproducibility notes and machine limits, keep the durable record in the
experiment note and [PLAN.md](../PLAN.md), not in this setup file.
