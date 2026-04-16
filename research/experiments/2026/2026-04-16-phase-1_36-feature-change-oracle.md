# Phase 1.36: Feature-Change Oracle (Signal Quality Diagnostic)

## Preregistration

Objective:

- use the existing dense feature replay cache to measure the GROUND
  TRUTH of "did the ViT feature actually change between adjacent
  frames?" per merged-token block. Then correlate each pixel-space
  routing signal (MEAN, MAX_ABS, CHANGED_PIXEL_FRACTION, TOP_K_MEAN)
  against this oracle to determine which signal best predicts ViT
  feature change.
- this answers the critical question: **is the current bottleneck
  signal quality (choosing the wrong blocks) or schedule quality
  (refreshing at the wrong times)?** If one pixel signal correlates
  highly with feature change, signal quality is already good and
  the next lever is scheduling. If none correlates well, we need a
  better signal first.

Claim register targets:

- Informs paper claims 1 (codec-derived proxies are valid routing
  signals) and 2 (naive mean-diff is too blunt).

Reproduction mode:

- CPU-only diagnostic analysis of existing replay-cache artifacts.
  No new VLM runs.

Track: A methodology.

Gating: runs any time; CPU-only; does NOT contend with GPU-bound
experiments. Can run in parallel with phase 1.21.

Hypotheses:

- **H1 (MAX_ABS is the best predictor)**: Spearman correlation
  between MAX_ABS pixel diff and per-block ViT cosine distance ≥ 0.7
  across the TOMATO + MVBench dev items.
- **H2 (MEAN is the weakest)**: Spearman correlation for MEAN is
  measurably lower than MAX_ABS (> 0.1 gap).
- **H3 (signal is good enough)**: the best pixel-space signal
  achieves Spearman ≥ 0.7, meaning signal quality is adequate and
  the next improvement should target scheduling (age/sticky/placement)
  rather than a fundamentally different signal.
- **H4 (signal vs schedule)**: if the best pixel signal < 0.5
  correlation, signal quality is the bottleneck and we should
  invest in DCT_HF, attention-weighted diff, or other richer
  signals before further schedule tuning.

Acceptance band:

- H1 or H3 passes: current MAX_ABS signal is good enough;
  scheduling is the next lever. Confirm with per-content-class
  stratification.

Rejection band:

- All pixel signals < 0.5 correlation: current pixel-diff proxy
  chain is fundamentally limited; need richer signals.

Inconclusive:

- correlation is in the 0.5–0.7 range across all signals; both
  signal and schedule improvements matter.

## Implementation

New script `scripts/feature_change_oracle.py`:

1. For each item in TOMATO motion dev + MVBench motion dev:
   - Load per-frame dense features from the replay cache
   - For each adjacent-frame pair, compute per-block cosine
     distance: `1 - cos(features[t, block], features[t+1, block])`
   - Decode the same frames and compute per-block: MEAN, MAX_ABS,
     CHANGED_PIXEL_FRACTION, TOP_K_MEAN of the pixel diff
2. Across all (item, frame_pair, block) triples:
   - Compute Spearman correlation of each pixel signal vs ViT
     cosine distance
3. Stratify by content class (TOMATO group, MVBench group)
4. Output: `phase1_36_feature_change_oracle.json` with per-signal
   correlations, per-content-class breakdowns, scatter plots data.

Runtime: ~30 min CPU (feature loading from disk + numpy correlation).

## Execution

Pending scheduling. Can start immediately (CPU-only).

## Result

Pending.

## Interpretation

Pending.

## Links

- [docs/methodology/temporal-coverage-metrics.md](../../../docs/methodology/temporal-coverage-metrics.md)
- [phase 1.31 failure predictor](2026-04-16-phase-1_31-failure-predictor.md)
- ChatGPT 2026-04-16 review: "idea 13 — Late-Layer ViT Cosine
  Similarity as Oracle"
