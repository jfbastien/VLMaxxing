# Phase 1.13: Logprob Stratification — Confidence vs Staleness

## Preregistration

Objective:

- run the dev-selected Pareto-winning policies once more on dev + holdout
  with `--log-option-logprobs` enabled, then bin items via
  `scripts/stratify_logprobs.py` into confidence-limited /
  staleness-agnostic / staleness-limited / ambiguous, and report
  cached-vs-dense agreement and accuracy conditional on each bin

Claim register targets:

- `WP-2.5`
- `WP-2.6`
- `WP-3.1`

Reproduction mode:

- generalized benchmark stratification

Track:

- A (quality conditioned on dense path's confidence)

Hypotheses:

- H1: items in the "confidence_limited" bin contribute most of the
  cached-vs-dense disagreement on motion holdout, dragging down the
  aggregate agreement rate
- H2: items in the "staleness_agnostic" bin show very high cached-vs-dense
  agreement (>= 0.95), supporting the framing that caching is safe when
  the dense path is itself confident
- H3: items in the "staleness_limited" bin (dense confident, cached
  uncertain) are concentrated on motion-heavy buckets like TOMATO
  `direction` — i.e. caching breaks dense's confidence specifically when
  the temporal evidence is critical

Acceptance band:

- the four bins partition the items without "missing_logprobs" exceeding
  ~10% (parsing failures stay rare)
- within at least one bin, the conditional cached vs dense agreement
  differs from the unconditional aggregate by >= 0.10 (i.e. the
  stratification is informative)

Rejection band:

- the partition is degenerate (single bin contains > 90% of items) — the
  default `CONF_LOW` and `CONF_HIGH` thresholds need re-calibration
- conditional agreement differs from unconditional by < 0.05 in every bin
  — the stratification adds no signal

Inconclusive:

- logprob extraction fails on > 30% of items (tokenizer issues with
  candidate letters)

Notes:

- thresholds (`CONF_LOW=0.5`, `CONF_HIGH=1.0`) are nominal; the first run
  will inform whether they need calibration on observed margin
  distributions
- this phase is opt-in for cost reasons (`--log-option-logprobs` runs an
  extra prefill per cached / dense path), so we run it on the small set
  of phase 1.12 winners only

## Execution

Pending phases 1.10, 1.11, 1.12 completion.

Planned commands:

```
# for each dev winner from phase 1.10/1.11:
uv run python scripts/run_benchmark_track_a.py run \
  --benchmark <benchmark> \
  --manifest <dev_manifest> \
  --chunk-size 1 \
  --frame-count 8 \
  --statistic <s> --static-threshold <st> --shifted-threshold <sh> \
  --reuse-classes <rc> --max-age <ma> \
  --log-option-logprobs \
  --output-path <jsonl> --summary-path <summary> \
  --allow-dirty

uv run python scripts/stratify_logprobs.py stratify \
  --jsonl <jsonl> \
  --conf-low 0.5 --conf-high 1.0 \
  --out <stratification.json>
```

## Result

Pending.

## Interpretation

Pending.

Expected interpretation template:

> Aggregate agreement on this slice: X
> Conditional on dense top_margin >= CONF_HIGH: agreement Y (the "real"
> caching quality on items where dense was confident)
> Conditional on staleness_limited: cached predicts answer letter Z% of
> the time vs dense's argmax (where the dense argmax is the correct
> letter and cached has switched away from it)

This conditional view is what the paper should report alongside the
aggregate, since aggregate agreement on confidence-limited items is
mostly a measure of dense baseline weakness, not caching policy quality.

## Links

- [phase 1.12 holdout evaluation](2026-04-14-phase-1_12-grid-winners-holdout.md)
- [scripts/stratify_logprobs.py](../../../scripts/stratify_logprobs.py)
- [experiment registry](../registry.md)
