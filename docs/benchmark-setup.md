# Benchmark Setup

This document covers the benchmark-native asset path for pre-release source
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
├── mvbench/
│   ├── downloads/
│   ├── hf/
│   └── video/
└── videomme/
    ├── downloads/
    ├── hf/
    └── videos/
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

If the official Drive bundle is quota-blocked or the transfer is corrupted, the
fetch script falls back to the public `ellisbrown/TOMATO` Hugging Face mirror,
which hosts `video_shard_000.tar.zst` through `video_shard_005.tar.zst`. The
selected asset source is recorded in `data/benchmarks/tomato/SOURCE.json`.

If the Drive path is already known-bad on the current machine, skip straight to
the mirror:

```bash
uv run python scripts/fetch_benchmarks.py --dataset tomato --mode assets --tomato-video-source mirror
```

Fetch MVBench task JSON and NTU reference list from Hugging Face:

```bash
uv run python scripts/fetch_benchmarks.py --dataset mvbench --mode metadata
```

Fetch the MVBench hosted video bundles from Hugging Face:

```bash
uv run python scripts/fetch_benchmarks.py --dataset mvbench --mode assets
```

The default MVBench asset profile is `predecessor18`, which matches the
predecessor-style `18`-task slice and avoids downloading hosted bundles that
are not needed for the first generalized reproduction pass.

In practice that hosted predecessor-style slice still needs `perception.zip`
for several of the saved `18` tasks. The default profile therefore includes it
even though the earliest draft of this repo's fetch list did not.

To fetch every Hugging Face-hosted MVBench archive instead:

```bash
uv run python scripts/fetch_benchmarks.py --dataset mvbench --mode assets --mvbench-profile all
```

Fetch the TOMATO and MVBench stacks (`both` means TOMATO + MVBench):

```bash
uv run python scripts/fetch_benchmarks.py --dataset both --mode all
```

Fetch VideoMME metadata:

```bash
uv run python scripts/fetch_benchmarks.py --dataset videomme --mode metadata
```

VideoMME videos are intentionally fetched by checked manifest subset rather than
by the full 101 GB corpus. Use:

```bash
uv run python scripts/fetch_videomme_subset.py \
  --manifest research/benchmark_manifests/videomme_dev_v1.toml \
  --manifest research/benchmark_manifests/videomme_holdout_v1.toml \
  --cache-dir data/benchmarks/videomme/downloads/hf_cache
```

See [docs/videomme-download-handoff.md](videomme-download-handoff.md) for the
complete VideoMME acquisition and verification flow.

Dry-run without downloading anything:

```bash
uv run python scripts/fetch_benchmarks.py --dataset both --mode all --dry-run
```

## Benchmark Runner

The benchmark-native Track A runner is:

```bash
uv run python scripts/run_benchmark_track_a.py run --benchmark tomato
```

Useful control modes:

- `--cache-mode default`:
  run the normal same-position cached-feature substitution path
- `--cache-mode identity`:
  route unchanged dense features back through the benchmark runner to verify
  cache-path transparency on the exact benchmark code path

Useful diagnosis option:

- `--refresh-interval <k>`:
  force a dense refresh every `k` frames while keeping the cached-feature path
  active between refreshes
- `--manifest <path>`:
  run an explicit frozen slice instead of the historical `first N per group`
  selection path
- `--feature-cache-dir <path>`:
  store or reuse dense vision features for repeated Track A planner sweeps
- `--no-feature-replay`:
  disable dense feature replay and force dense recomputation
- `--allow-dirty`:
  bypass the default clean-tree guard for debugging only; reportable benchmark
  artifacts should come from clean commits

Current reuse-accounting rule on the benchmark runner:

- `reuse_ratio_mean` is the pad-masked active-region reuse ratio
- `reuse_ratio_mean_raw` is also recorded for descriptive comparison
- identity-mode controls report reuse as `null` because the planner is bypassed

Current replay rule on the benchmark runner:

- replay is a Track A experiment accelerator only
- cache hits are recorded per item as `feature_cache_hit`
- replay does not justify speedup or compression language

Recommended first TOMATO smoke on this machine:

```bash
uv run python scripts/run_benchmark_track_a.py run \
  --benchmark tomato \
  --per-group 1 \
  --chunk-size 1 \
  --frame-count 8 \
  --max-tokens 32 \
  --output-path results/tomato_smoke.jsonl \
  --summary-path results/tomato_smoke_summary.json
```

Recommended first generalized TOMATO subset after the smoke passes:

```bash
uv run python scripts/run_benchmark_track_a.py run \
  --benchmark tomato \
  --manifest research/benchmark_manifests/tomato_dev_v1.toml \
  --chunk-size 1 \
  --frame-count 8 \
  --max-tokens 32 \
  --output-path results/tomato_subset.jsonl \
  --summary-path results/tomato_subset_summary.json
```

For long semantic runs, the runner also supports cooperative stop and summary
checkpointing:

```bash
uv run python scripts/run_benchmark_track_a.py run \
  --benchmark tomato \
  --manifest research/benchmark_manifests/tomato_dev_v1.toml \
  --chunk-size 1 \
  --stop-file /tmp/vlmaxxing-stop \
  --summary-path results/tomato_subset_summary.json
```

Then request clean termination with:

```bash
touch /tmp/vlmaxxing-stop
```

The runner stops at the next chunk boundary and rewrites the summary JSON.

Benchmark slice policy now lives under
[research/benchmark_manifests/](../research/benchmark_manifests/README.md).
Use `*_dev_v1.toml` during planner search and keep `*_holdout_v1.toml` frozen
until the next policy choice is ready for evaluation.

Replay methodology and invalidation rules live in
[docs/methodology/feature-replay.md](methodology/feature-replay.md).

## TOMATO Notes

- official code repo: `yale-nlp/TOMATO`
- official QA tables: `yale-nlp/TOMATO` on Hugging Face
- official video bundle: Google Drive file linked from the TOMATO repo README
- QA table license from the dataset card: `CC BY-SA 4.0`

This repo uses the official Hugging Face tables plus the official Google Drive
video bundle when available. If the Drive bundle is unavailable, it falls back
to the public `ellisbrown/TOMATO` shard mirror and records that choice in the
local source record so the acquisition path remains auditable.

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
- the default fetch profile mirrors that predecessor-style hosted subset:
  `FunQA_test`, `Moments_in_Time_Raw`, `clevrer`, `data0613`, `perception`,
  `scene_qa`, `ssv2_video`, `sta`, `star`, and `vlnqa`

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
- that the pre-release source frame count or model precision can be matched

Those caveats belong in the experiment note and
[docs/reproduction-status.md](reproduction-status.md).
