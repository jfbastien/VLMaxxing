# Phase 1.25: TempCompass Benchmark Ingest

## Preregistration

Objective:

- add TempCompass (arXiv 2403.00476) as a third temporal-reasoning
  benchmark alongside TOMATO and MVBench motion. TempCompass
  specifically isolates *speed*, *direction*, *order*, and
  *attribute-change* aspects via controlled probes.
- produce dev and holdout manifests with the same preregistration
  discipline as our TOMATO / MVBench slices.

Claim register targets:

- Paper claim 2, 3: validates against a controlled-probe benchmark
  that our TOMATO work has been hinting at structurally.
- `WP-3.3`

Reproduction mode:

- corpus setup + baseline evaluation; not a method change.

Track: A (additional benchmark, same methodology)

Gating: runs when corpus download budget allows. NOT top priority —
phases 1.26/1.27/1.28 are more leveraged because they test paper
claims 3 and 4 on benchmarks we already have.

Hypotheses:

- **H1 (structure confirms)**: TempCompass reveals a per-aspect
  pattern where our cached policies match dense on "attribute-change"
  (static-evidence items) and fail on "speed" and "direction"
  (motion-critical items).
- **H2 (sticky-dynamic helps order/direction)**: once phase 1.26
  lands, sticky-dynamic improves TempCompass "order" and "direction"
  accuracy vs vanilla but not "speed" (which needs sub-frame
  timing, not just change detection).
- **H3 (TempCompass is harder than our current slices)**: cached
  accuracy on TempCompass < cached accuracy on TOMATO at matched
  operating point. TempCompass was designed for explicit
  temporal-aspect isolation.

Acceptance band:

- manifests built, dev/holdout disjoint, per-aspect 15 items each
  (15 × 4 aspects = 60 dev items; 60 holdout items).
- baseline dense-N frame-budget curve for N ∈ {2, 4, 6, 8} on dev
  evaluated cleanly.

Rejection band:

- TempCompass corpus isn't available in a form we can ingest within
  a day (corpus-build failure).

Inconclusive:

- item format incompatibility with our current runner — TempCompass
  uses open-ended VQA in some subtasks; we'd need a parser
  extension for those.

## Corpus work

1. Pull TempCompass from HF
   (https://huggingface.co/datasets/lmms-lab/TempCompass)
2. Extract the 4 aspect subsets: speed, direction, event_order,
   attribute_change
3. Pick 60 items per slice (dev vs holdout) stratified by aspect
   seed=42
4. Write
   `research/benchmark_manifests/tempcompass_motion_dev_v1.toml` and
   `research/benchmark_manifests/tempcompass_motion_holdout_v1.toml`
5. Extend `scripts/run_benchmark_track_a.py` with a TempCompass
   loader parallel to the TOMATO/MVBench loaders.

## Execution

Pending. Lower priority than 1.26 / 1.27 / 1.28.

## Result

Pending.

## Interpretation

Pending.

## Links

- TempCompass paper: https://arxiv.org/abs/2403.00476
- Pre-release CodecSight strategy notes are preserved in git history; current
  release-facing positioning is in [paper/framing.md](../../../paper/framing.md)
  and [docs/related-work-table.md](../../../docs/related-work-table.md).
