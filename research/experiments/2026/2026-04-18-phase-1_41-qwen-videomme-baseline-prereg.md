# Phase 1.41 — Qwen 2.5-VL-7B VideoMME baseline (prereg)

**Status:** pre-registration 2026-04-18. Predictions committed
BEFORE running. Unblocks **claim #8** in the paper claim-matrix
(VideoMME as recognized benchmark).

## Motivation

Claim #8 ("Validated on VideoMME") is a hard requirement for the
paper's headline: VideoMME is the de facto temporal-reasoning
benchmark standard, so the paper cannot ship without a local
Qwen 2.5-VL-7B number on it. All infrastructure landed 2026-04-17
(loader, manifests, video assets). This run is a **runtime-only
gap** — the Qwen Track A driver already supports `--benchmark
videomme` and the 1-item smoke test passed 2026-04-18 at
commit 66113c09e with dense=T cached=T agreement=1.0.

## Pre-registered predictions

VideoMME is 4-option multiple choice across short (<60s),
medium (60–300s), long (15+ min) durations. Public reports put
Qwen 2.5-VL-7B ≈ 0.55 on the full benchmark (n=2700). We run
on **videomme_dev_v1 n=30** (10 short + 10 medium + 10 long from
the dev split, distinct from the pre-release source's or any public test draw).

Baseline priors (from known Qwen performance on similar benchmarks
at 8 frames × 560×560 × max_tokens=32):
- TOMATO motion holdout N=30: 0.333 dense accuracy
- MVBench motion holdout N=30: 0.567 dense accuracy
- Agreement dense-vs-cached: 1.000 (MVBench) / 1.000 (TOMATO)

### Hypotheses

- **H1 (dense accuracy)**: aggregate dense_accuracy ∈ [0.40, 0.60].
  Best-guess 0.50. VideoMME 4-option random baseline is 0.25; a
  4B-class frame-sampling VLM at 8 frames is in the 0.40-0.60 band
  on dev slices.
- **H2 (parse failure rate)**: ≤ 2/30 dense parse failures. Qwen
  is a stable MCQ responder on prior runs.
- **H3 (peak RSS)**: < 8 GB. MVBench peaked at 6.87 GB on
  comparable geometry.
- **H4 (per-item wall-clock)**: median dense e2e ∈ [40, 90] s
  (TOMATO was 61.1 s median, MVBench 56.5 s — VideoMME items may
  run longer on medium/long buckets because of video decode time).

### Bucket priors

- Short bucket (n=10, <60s videos): dense_acc ∈ [0.40, 0.70]
- Medium bucket (n=10): dense_acc ∈ [0.30, 0.60]
- Long bucket (n=10): dense_acc ∈ [0.20, 0.50] (frame budget is
  most under-resourced here at 8 frames uniform over 15+ min)

## Falsification criteria

- Dense accuracy < 0.33 (random + stratification margin): Qwen 7B is
  **not** a usable VideoMME baseline at this frame count — would
  force a decision to lift frame-count to 32 even for the baseline.
- Dense accuracy > 0.60: either sampling lucky or dev slice is
  easier than published dev/test. Note but do not reject — report
  the number and move on.
- Parse failures ≥ 5/30: would signal prompt/format drift. Halt,
  investigate the prompt template.
- Peak RSS > 12 GB: infrastructure concern, not science. Would
  warn but not block.

## Run plan

Step A — single-item smoke (DONE 2026-04-18):
- Cache mode identity, one item (videomme:short:100-2), agreement=1.0.

Step B — **this run, n=30 dense** (cache_mode=identity, no router):

```bash
uv run python scripts/run_benchmark_track_a.py run \
    --benchmark videomme \
    --manifest research/benchmark_manifests/videomme_dev_v1.toml \
    --frame-count 8 \
    --cache-mode identity \
    --max-tokens 32 \
    --output-path research/experiments/2026/artifacts/phase1_41_qwen_videomme/dense_n30.jsonl \
    --summary-path research/experiments/2026/artifacts/phase1_41_qwen_videomme/dense_n30_summary.json
```

Estimated wall-time: 30 items × ~60s/item ≈ **30–45 min**.

Step C (deferred to findings-decision): if dense lands ≥ 0.40 and we
have time, run a routed variant (Planner 2.0 base config) to exercise
the caching mechanism on VideoMME — satisfies Claim #7 partial.

## What this earns

1. **Claim #8 baseline landed on VideoMME dev** — the benchmark-
   recognition gate the paper requires. Unblocks primary framing.
2. Anchors the denominator for any future Qwen + routing arm on
   VideoMME (Planner 2.0 base, sticky4, halo-veto).
3. Confirms the Qwen → VideoMME loader path on n=30 after 1-item
   smoke.

## What this falsifies

- If dense accuracy is below random-threshold-adjusted 0.33, the
  8-frame frame budget is insufficient and we must lift to 16 or 32
  frames even for the baseline. That would change scope for both
  claim #8 and claim #5 (Track B ceiling analysis would need
  re-deriving at 16/32f).

## Cross-references

- `paper/claim-matrix.md` claim #8.
- `research/experiments/2026/artifacts/phase1_41_qwen_videomme/smoke_summary.json`
  (1-item smoke, dense=T, cached=T, agreement=1.0).
- `research/benchmark_manifests/videomme_dev_v1.toml` (30 items).
