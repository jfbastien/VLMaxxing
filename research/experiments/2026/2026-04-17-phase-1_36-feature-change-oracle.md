# Phase 1.36 — Feature-change oracle (pixel-diff ↔ ViT cosine distance)

Date: 2026-04-17
Parent: `paper/claim-matrix.md` claim #2 (pixel-diff proxy fidelity)

## Framing note (2026-04-17 update)

This phase is a **ranking/diagnosis** study, not a "pick the
statistic with the highest Pearson r" study. The main take-aways
are structural, not leaderboard-shaped:

1. Pixel→feature correlation has a **weak-to-moderate ceiling**
   (Pearson r up to ~0.50), so pixel-space routing is an
   approximation even on the statistic that best predicts feature
   change. This is a lower bound, not a failure.
2. The best **routing** statistic (MAX_ABS, per the Planner 2.0
   ablation) is NOT the best **point predictor** on either
   benchmark. Routing cares about ordering under a top-k budget;
   point prediction cares about magnitude-matching. Different
   objectives have different winners.
3. The best point predictor is **content-dependent** (MEAN on
   TOMATO, CPF on MVBench), matching the Planner 2.0 finding that
   no single statistic is universal.

None of these conclusions require picking a statistic; they narrow
the paper's claim scope instead.

## Hypothesis

The pixel-diff planner routes blocks into STATIC / SHIFTED / NOVEL using
one of four pixel statistics (MEAN, MAX_ABS, CHANGED_PIXEL_FRACTION,
TOP_K_MEAN). Phase 1.47 and the Planner 2.0 ablation both treat these as
interchangeable signals and pick winners only by downstream benchmark
accuracy. This phase tests the upstream question: **how well does each
pixel statistic predict the actual per-block change in Qwen 2.5-VL ViT
features on the same frame pair?** A high correlation means the pixel
signal is a good point predictor of feature change; a low correlation
means the pixel→feature relationship is too noisy for that statistic to
matter as anything other than a rough ordering.

The result is not a routing policy. It quantifies how much of the
pixel→feature relationship each statistic captures.

## Method

- Reuse the existing dense-feature replay cache under
  `research/cache/dense_features/` — 495 `.npz` files, one per
  `(model, preprocessing, item, frame-hash)` tuple. Each cache stores
  `features [tokens_total, 3584]` and `image_grid_thw [num_frames, 3]`.
- For every item in a manifest:
  1. Decode 8 uniform frames with the benchmark runner's own
     `_decode_uniform_frames` helper (square pad to 560×560, matching
     the cached features' preprocessing contract).
  2. Convert frames to `[F, 560, 560, 3] uint8` and for each adjacent
     pair `(t, t+1)` compute MEAN / MAX_ABS / CPF / TOP_K_MEAN per
     28-pixel block via `block_statistic_values`. Block grid: 20×20.
  3. Load the cached features, split into per-frame `[20, 20, 3584]`
     (patch-grid 40×40 divided by `spatial_merge=2`), and compute
     per-block cosine distance between the two grids.
  4. Append per-block rows `(item_id, benchmark, group, block_row,
     block_col, mean, max_abs, cpf, top_k_mean, cosine_distance)` to
     a parquet dump.
- After all items, compute Pearson and Spearman correlation of each
  pixel statistic against cosine distance across every block × every
  adjacent pair × every item.

Implementation: `scripts/feature_change_oracle.py`.

**No ViT inference is run.** The whole study is CPU-only on cached
features, runtime roughly 30 s per 30-item manifest (decode + numpy).

## Datasets

- TOMATO: `tomato_motion_dev_v2.toml` + `tomato_motion_holdout_v2.toml`
  (N=30 target; 45 items discovered, 45 cache hits)
- MVBench: `mvbench_motion_dev_v2.toml` + `mvbench_motion_holdout_v2.toml`
  (N=30 target; 45 items discovered, 45 cache hits)

Each benchmark yielded 126,000 per-block (45 items × 7 pairs × 400
blocks) rows.

> Note: the cache hit count of 45 on each benchmark reflects all items
> whose cached features survived the v2 cache-key rewrite. We did not
> refresh the cache for this study.

## Results

All correlations are computed across every block in every pair in every
cached item for the benchmark.

| Benchmark | Statistic | Pearson r | Spearman r |
|---|---|---:|---:|
| TOMATO (N=45, 126k blocks) | **MEAN** | **+0.233** | **+0.177** |
| TOMATO | CPF | +0.224 | +0.101 |
| TOMATO | TOP_K_MEAN | +0.201 | +0.156 |
| TOMATO | MAX_ABS | +0.191 | +0.149 |
| MVBench (N=45, 126k blocks) | **CPF** | **+0.504** | +0.489 |
| MVBench | MEAN | +0.451 | **+0.491** |
| MVBench | TOP_K_MEAN | +0.452 | +0.475 |
| MVBench | MAX_ABS | +0.444 | +0.466 |

Cosine-distance distributions:

| Benchmark | mean | p95 |
|---|---:|---:|
| TOMATO | 0.194 | 0.640 |
| MVBench | 0.258 | 0.705 |

## What this means

1. **Pixel↔feature correlation is weak-to-moderate in absolute terms.**
   The best statistic on either benchmark caps at Pearson ≈ 0.50.
   A single 28-pixel block's ViT cosine distance is shaped by more
   than its own local diff — neighbor context, ViT receptive field
   effects, and attention all matter. A point-predictor framing of
   pixel stats was never going to be high-r.

2. **The ranking is content-dependent**, matching the Planner 2.0
   ablation's "MAX_ABS is not a universal default" scope.
   - TOMATO (constrained motion synthetic clips): **MEAN** is the
     strongest predictor on both Pearson and Spearman. CPF collapses
     on Spearman (+0.101), consistent with CPF being a near-binary
     trigger that loses information inside its "above threshold"
     range.
   - MVBench (heterogeneous real-video motion clips): **CPF** wins
     Pearson and **MEAN** wins Spearman by a hair. In practice MEAN
     and CPF behave as a tied pair here; MAX_ABS and TOP_K_MEAN sit
     clearly lower.

3. **MAX_ABS is never the best point predictor of feature change.**
   It is second-to-last on both benchmarks. This is a striking
   contrast with the Planner 2.0 ablation, where MAX_ABS was the best
   routing statistic on TOMATO and tied-best on MVBench at matched
   budget. The reconciliation:
   - Point-prediction ("what is this block's feature delta?") and
     routing ("which blocks should I mark novel at this budget?")
     are different objectives.
   - MAX_ABS is an outlier-sensitive signal: one high-diff pixel in a
     block drives its score up. That makes it good at *ordering*
     blocks for a top-k budget allocator, even when the per-block
     feature delta magnitude is elsewhere set by slower, more
     distributed change.
   - MEAN and CPF average across the block and so track the bulk
     pixel-change amplitude — which correlates better with the
     block's mean-pooled feature delta, but doesn't necessarily
     identify the motion hotspots a router cares about.

4. **The pixel→feature mapping is stronger on MVBench than TOMATO.**
   Correlations are roughly 2× higher on MVBench. TOMATO's
   constrained-motion synthetic clips have smaller global diffs
   (cos_mean 0.194 vs 0.258) and narrower dynamic range, so the
   pixel signal has less headroom to be informative.

## Paper implications

- **Claim #2 (pixel-diff proxy fidelity)** in `paper/claim-matrix.md`
  should not stay at "proxy fidelity validated by downstream quality
  alone." The direct per-block correlation is now the lower bound:
  **weak-to-moderate (r ≤ 0.50) and content-dependent.** That is a
  fact about pixel-space routing, not a concession.
- The Planner 2.0 statistic-choice paragraph can now say: the
  best-routing statistic (MAX_ABS) is NOT the best point predictor;
  the best point predictor is MEAN on TOMATO and CPF on MVBench. The
  routing objective is about ordering blocks under a budget, not about
  matching the feature delta magnitude.
- `paper/framing.md` "Proxy Chain" section benefits from the explicit
  lower bound: *"pixel-space RGB differencing correlates with ViT
  feature change at Pearson r ≈ 0.23 (TOMATO) to 0.50 (MVBench). Under
  real codec signals (phase 1.29 MV-only) this lower bound is a
  ceiling we need to surpass before claiming codec-grade signal."*

## Open questions

- What does this curve look like with real H.264/H.265 motion-vector
  metadata (phase 1.29 MV-only)? The hypothesis to test next is: MV
  magnitude correlates MORE strongly with feature change than any
  RGB stat, because MV represents block motion after the encoder has
  already done the hard work of aligning content.
- Does the TOMATO-vs-MVBench gap survive on a higher-resolution
  feature extraction? The cache is all at 560×560 — we have not
  tested whether MAX_ABS's relative weakness is a block-size artifact.
- Per-block cosine distance is pooled within a merged-token; a
  finer-grained pre-merge patch grid might shift the ranking.

## Reproduction

```bash
uv run python scripts/feature_change_oracle.py \
  --manifest research/benchmark_manifests/tomato_motion_dev_v2.toml \
  --manifest research/benchmark_manifests/tomato_motion_holdout_v2.toml \
  --output results/feature_change_oracle/tomato_n30.parquet \
  --summary results/feature_change_oracle/tomato_n30.json

uv run python scripts/feature_change_oracle.py \
  --manifest research/benchmark_manifests/mvbench_motion_dev_v2.toml \
  --manifest research/benchmark_manifests/mvbench_motion_holdout_v2.toml \
  --output results/feature_change_oracle/mvbench_n30.parquet \
  --summary results/feature_change_oracle/mvbench_n30.json
```

Parquet output columns: `item_id, benchmark, group, frame_a, frame_b,
block_row, block_col, mean, max_abs, cpf, top_k_mean, cosine_distance`.

## Artifacts

- `results/feature_change_oracle/tomato_n30.json` — summary (cache
  hits 45 / misses 15; 126k blocks aggregated)
- `results/feature_change_oracle/tomato_n30.parquet` — per-block rows
- `results/feature_change_oracle/mvbench_n30.json` — summary
- `results/feature_change_oracle/mvbench_n30.parquet` — per-block rows
- `scripts/feature_change_oracle.py` — driver (commit f1f34ca and
  subsequent refinements in 8920e36)

Coverage caveat: 45 cache hits / 15 cache misses on each benchmark.
The 15 misses are items whose cached features predate the v2
cache-key rewrite (phase 1.32 model-content hash fix) and were not
re-extracted for this study. Per-block correlations below are
computed on the 45-item intersection only.

## State

- Status: completed (2026-04-17)
- Clean tree: yes (commit 8920e36 at run time; note text updated in
  subsequent research commits without changing numbers)
- Paper-grade: yes for the lower-bound point-predictor framing;
  claim #2 cited in `paper/claim-matrix.md`
- Outstanding: none. Open questions are future-work seeds, not
  blockers for the current claim.
