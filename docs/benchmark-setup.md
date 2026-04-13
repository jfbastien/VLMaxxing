# Benchmark Setup

This document covers the benchmark-native asset path for whitepaper
reproduction.

It is separate from the local clip corpus because benchmark assets have
different licensing, larger size, and stricter comparability requirements.

## Reproduction Target

On this M3 Air, benchmark work defaults to **generalized reproduction**, not
strict rerun:

- same method family
- same benchmark structure
- local hardware-aware subset or chunking when needed
- explicit caveats about model precision, frame count, and subset size

Do not silently blur that into "full replication."

The frozen imported targets are in
[docs/claim-register.md](claim-register.md).

## Install The Benchmark Helpers

```bash
uv sync --group dev --group research --group vlm --group benchmark
```

## Local Layout

Benchmark assets live under ignored paths:

```text
data/benchmarks/
├── tomato/
│   ├── downloads/
│   ├── hf/
│   └── videos/
└── mvbench/
    ├── downloads/
    ├── hf/
    └── video/
```

Nothing under `data/benchmarks/` is committed to git.

## Fetch Commands

Fetch TOMATO QA tables from Hugging Face:

```bash
uv run python scripts/fetch_benchmarks.py --dataset tomato --mode metadata
```

Fetch the TOMATO video bundle from the official Google Drive file:

```bash
uv run python scripts/fetch_benchmarks.py --dataset tomato --mode assets
```

Fetch MVBench task JSON and NTU reference list from Hugging Face:

```bash
uv run python scripts/fetch_benchmarks.py --dataset mvbench --mode metadata
```

Fetch the MVBench hosted video bundles from Hugging Face:

```bash
uv run python scripts/fetch_benchmarks.py --dataset mvbench --mode assets
```

Fetch both benchmark stacks:

```bash
uv run python scripts/fetch_benchmarks.py --dataset both --mode all
```

Dry-run without downloading anything:

```bash
uv run python scripts/fetch_benchmarks.py --dataset both --mode all --dry-run
```

## TOMATO Notes

- official code repo: `yale-nlp/TOMATO`
- official QA tables: `yale-nlp/TOMATO` on Hugging Face
- official video bundle: Google Drive file linked from the TOMATO repo README
- QA table license from the dataset card: `CC BY-SA 4.0`

This repo uses the official Hugging Face tables plus the official Google Drive
video bundle. The fetch script hard-codes the public Drive file id from the
official TOMATO README so the acquisition path is auditable.

Expected final layout:

```text
data/benchmarks/tomato/
├── hf/
│   └── data/*.parquet
└── videos/
    ├── human/
    ├── object/
    └── simulated/
```

## MVBench Notes

- official dataset repo: `OpenGVLab/MVBench` on Hugging Face
- task JSON is hosted directly on Hugging Face
- most video bundles are hosted directly on Hugging Face as zip archives
- `320` NTU RGB+D videos remain manual because of upstream license restrictions

Current implication:

- this repo can automate the Hugging Face-hosted portion of MVBench
- full `20`-task coverage may still require the NTU manual download
- the imported predecessor run only saved an `18`-task local slice, so a local
  generalized reproduction can still be meaningful before NTU is complete

Expected final layout:

```text
data/benchmarks/mvbench/
├── hf/
│   ├── json/*.json
│   └── video/MVBench_videos_ntu.txt
└── video/
    ├── clevrer/
    ├── star/
    ├── ssv2_video/
    └── ...
```

## What The Fetch Script Guarantees

- fail-loud if the expected local layout is not created
- preserve downloaded archives under `downloads/`
- record the upstream repo or Drive source in a checked local JSON note
- keep benchmark data out of git

## What The Fetch Script Does Not Guarantee

- that the full benchmark is tractable on this machine
- that every MVBench task is complete without NTU
- that the imported whitepaper frame count or model precision can be matched

Those caveats belong in the experiment note and
[docs/reproduction-status.md](reproduction-status.md).
