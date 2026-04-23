---
phase: 1.29B
date: 2026-04-23
parent: research/experiments/2026/2026-04-23-phase-1_29-planner-accuracy-probe-findings.md
status: findings appended; H_short_bundle PASS-boundary; H_duration_breadth PASS
tracking: codex AFK continuation 2026-04-23
---

# Phase 1.29B — codec-native planner replication and breadth prereg

## Motivation

Phase 1.29 reopened the codec-native planner path after the continuous-score
redesign matched dense answers on VideoMME short-dev n=10:

- codec-dense agreement: 1.00
- codec accuracy = dense accuracy = 0.80
- codec-minus-pixel accuracy: +0.10
- codec active-reuse ratio within 1pp of pixel

That is a first point, not paper-grade evidence. The earlier queue described
"n=30 short", but the repository's fixed VideoMME manifests contain only
10 short items in `videomme_dev_v1.toml` and 10 disjoint short items in
`videomme_holdout_v1.toml`. This prereg corrects that scope before any new run:

1. **Replication slice:** disjoint short holdout n=10.
2. **Short evidence bundle:** dev+holdout short n=20, analyzed from the two
   short runs.
3. **Duration-breadth slice:** all-duration dev n=30, run only if short
   replication is not clearly falsifying.

## Hypotheses

### H_short_replicates

On `videomme_holdout_v1_short_only.toml` at Qwen 2.5-VL-7B-Instruct-4bit,
8 frames, per-item live-pixel calibration:

- codec-dense choice agreement >= 0.90
- codec accuracy loss relative to dense >= -0.05
- codec-pixel choice agreement >= 0.80
- absolute active-reuse-ratio gap between codec and pixel <= 0.05
- parse failures = 0 for dense, pixel, and codec arms

This is a strict n=10 replication gate. If it fails by one item only on
accuracy but passes choice-agreement and parse gates, interpret as MIXED and
use the combined n=20 short bundle rather than promoting or killing the claim.

### H_short_bundle

Pooling the existing dev-short n=10 with the holdout-short n=10:

- codec-dense choice agreement >= 0.90
- codec accuracy loss relative to dense >= -0.05
- codec-pixel choice agreement >= 0.80
- absolute active-reuse-ratio gap between codec and pixel <= 0.05

This is the minimum evidence needed to keep C-CODEC in the paper-body
candidate list. It is still short-bucket-only and must be labeled as such.

### H_duration_breadth

On `videomme_dev_v1.toml` all durations n=30:

- codec-dense choice agreement >= 0.85
- codec accuracy loss relative to dense >= -0.10
- codec-pixel choice agreement >= 0.75
- absolute active-reuse-ratio gap between codec and pixel <= 0.10

The breadth gate is intentionally looser because long clips make native-rate
H.264 extraction expensive and because the n=10 result is short-only. Passing
this gate would upgrade C-CODEC from short-only first point to a broader local
codec-native benchmark slice. Failing it localizes C-CODEC to short/static-ish
clips and keeps it out of the main headline.

## Method

Use the existing runner without code changes:

```bash
PHASE1_29_MANIFEST=research/benchmark_manifests/videomme_holdout_v1_short_only.toml \
PHASE1_29_OUT_DIR=research/experiments/2026/artifacts/phase1_29B_short_holdout_20260423 \
bash scripts/run_phase1_29_planner_accuracy_probe.sh
```

If H_short_replicates is not clearly falsified, run duration breadth:

```bash
PHASE1_29_MANIFEST=research/benchmark_manifests/videomme_dev_v1.toml \
PHASE1_29_OUT_DIR=research/experiments/2026/artifacts/phase1_29B_dev30_duration_20260423 \
bash scripts/run_phase1_29_planner_accuracy_probe.sh
```

Do not overwrite the existing first-point artifacts under
`phase1_29_planner_accuracy_probe/`.

## Interpretation rules

- Treat codec-native as a **planner-substitution** claim, not a latency claim.
  This runner pays native-rate H.264 extraction cost that a streaming decoder
  would already have; measured wall-clock here is a diagnostic, not a systems
  speedup.
- Do not promote C-CODEC to a headline on short-only evidence.
- If short holdout fails, root-cause before running long-duration breadth:
  inspect per-item dense correctness, parse failures, reuse-ratio drift, and
  codec-vs-pixel selection Jaccard.
- If duration breadth fails while short passes, frame C-CODEC as a boundary:
  codec-native planner substitution works on short clips but does not yet
  survive long-span sparse-sampling without a better native-rate aggregation or
  calibration policy.

## Artifacts

Planned:

- `research/benchmark_manifests/videomme_holdout_v1_short_only.toml`
- `research/benchmark_manifests/videomme_short_dev_holdout_v1_n20.toml`
- `research/experiments/2026/artifacts/phase1_29B_short_holdout_20260423/results.jsonl`
- `research/experiments/2026/artifacts/phase1_29B_short_holdout_20260423/summary.json`
- `research/experiments/2026/artifacts/phase1_29B_dev30_duration_20260423/results.jsonl`
- `research/experiments/2026/artifacts/phase1_29B_dev30_duration_20260423/summary.json`

## Execution — short holdout

Run command:

```bash
uv run python scripts/run_phase1_29_planner_accuracy_probe.py \
  --manifest research/benchmark_manifests/videomme_holdout_v1_short_only.toml \
  --output-path research/experiments/2026/artifacts/phase1_29B_short_holdout_20260423/results.jsonl \
  --summary-path research/experiments/2026/artifacts/phase1_29B_short_holdout_20260423/summary.json
```

Environment record: clean tree at git SHA
`21d3721a5dcaadda9a842c653796e4c131480965`.

Artifacts:

- `research/experiments/2026/artifacts/phase1_29B_short_holdout_20260423/results.jsonl`
- `research/experiments/2026/artifacts/phase1_29B_short_holdout_20260423/summary.json`

## Results — short holdout

| Metric | Value | Gate | Verdict |
|--------|-------|------|---------|
| n items | 10 | 10 | PASS |
| Dense accuracy | 0.800 (8/10) | reference | — |
| Pixel accuracy | 0.700 (7/10) | reference | — |
| Codec accuracy | 0.700 (7/10) | dense loss >= -0.05 | MIXED |
| Codec minus dense accuracy | -0.100 | >= -0.05 | FAIL by one item |
| Codec-dense agreement | 0.900 (9/10) | >= 0.90 | PASS |
| Codec-pixel agreement | 1.000 (10/10) | >= 0.80 | PASS |
| Pixel-dense agreement | 0.900 (9/10) | reference | — |
| Pixel active reuse | 0.080 | reference | — |
| Codec active reuse | 0.074 | abs gap <= 0.05 | PASS |
| Pair-selection Jaccard | 0.506 | diagnostic | — |
| Parse failures | 0 dense / 0 pixel / 0 codec | 0 | PASS |

Per-item result:

| item | dense | pixel | codec | codec/pixel choice | Jaccard |
|------|-------|-------|-------|--------------------|---------|
| `videomme:short:062-3` | correct | correct | correct | 2 / 2 | 0.857 |
| `videomme:short:066-3` | correct | wrong | wrong | 3 / 3 | 0.294 |
| `videomme:short:070-3` | correct | correct | correct | 2 / 2 | 0.712 |
| `videomme:short:074-3` | correct | correct | correct | 1 / 1 | 0.215 |
| `videomme:short:126-1` | correct | correct | correct | 3 / 3 | 0.571 |
| `videomme:short:126-2` | correct | correct | correct | 1 / 1 | 0.571 |
| `videomme:short:136-3` | wrong | wrong | wrong | 1 / 1 | 0.479 |
| `videomme:short:267-2` | correct | correct | correct | 3 / 3 | 0.714 |
| `videomme:short:280-3` | correct | correct | correct | 3 / 3 | 0.499 |
| `videomme:short:293-1` | wrong | wrong | wrong | 3 / 3 | 0.143 |

## Combined short-bucket evidence

Pooling the original dev-short first point with the disjoint short-holdout run:

| Metric | Value | Gate | Verdict |
|--------|-------|------|---------|
| n items | 20 | 20 | PASS |
| Dense accuracy | 0.800 (16/20) | reference | — |
| Pixel accuracy | 0.700 (14/20) | reference | — |
| Codec accuracy | 0.750 (15/20) | dense loss >= -0.05 | PASS on boundary |
| Codec minus dense accuracy | -0.050 | >= -0.05 | PASS on boundary |
| Codec-dense agreement | 0.950 (19/20) | >= 0.90 | PASS |
| Codec-pixel agreement | 0.950 (19/20) | >= 0.80 | PASS |
| Pixel-dense agreement | 0.900 (18/20) | reference | — |
| Pixel active reuse | 0.103 | reference | — |
| Codec active reuse | 0.096 | abs gap <= 0.05 | PASS |

## Interpretation after short replication

`H_short_replicates` is **MIXED-positive**: codec loses exactly one dense-correct
item (`videomme:short:066-3`) but matches pixel on all 10 items and preserves
the reuse-ratio geometry. This is not a clean standalone holdout pass because
the accuracy-loss gate misses by one item.

`H_short_bundle` is **PASS on the preregistered boundary**. The combined short
n=20 evidence keeps C-CODEC alive as a planner-substitution candidate, but the
margin is thin: the paper cannot claim codec-native is better than pixel, only
that continuous codec scores with per-item live-pixel calibration reproduce
pixel/dense planner behavior on short VideoMME within the preregistered band.

Per the preregistration, this result is not clearly falsifying, so the next
step is the all-duration dev n=30 breadth run. If that breadth run fails, the
claim should be scoped to short/static-ish clips and kept out of the headline.

## Execution — all-duration dev breadth

Run command:

```bash
uv run python scripts/run_phase1_29_planner_accuracy_probe.py \
  --manifest research/benchmark_manifests/videomme_dev_v1.toml \
  --output-path research/experiments/2026/artifacts/phase1_29B_dev30_duration_20260423/results.jsonl \
  --summary-path research/experiments/2026/artifacts/phase1_29B_dev30_duration_20260423/summary.json
```

Environment record: clean tree at git SHA
`f9e4653d0914240b926d4d46c790d61cfc27ee52`.

Artifacts:

- `research/experiments/2026/artifacts/phase1_29B_dev30_duration_20260423/results.jsonl`
- `research/experiments/2026/artifacts/phase1_29B_dev30_duration_20260423/summary.json`

## Results — all-duration dev n=30

| Metric | Value | Gate | Verdict |
|--------|-------|------|---------|
| n items | 30 | 30 | PASS |
| Dense accuracy | 0.533 (16/30) | reference | — |
| Pixel accuracy | 0.533 (16/30) | reference | — |
| Codec accuracy | 0.533 (16/30) | dense loss >= -0.10 | PASS |
| Codec minus dense accuracy | 0.000 | >= -0.10 | PASS |
| Codec-dense agreement | 1.000 (30/30) | >= 0.85 | PASS |
| Codec-pixel agreement | 0.933 (28/30) | >= 0.75 | PASS |
| Pixel-dense agreement | 0.933 (28/30) | reference | — |
| Pixel active reuse | 0.105 | reference | — |
| Codec active reuse | 0.089 | abs gap <= 0.10 | PASS |
| Pair-selection Jaccard | 0.525 | diagnostic | — |
| Parse failures | 0 dense / 0 pixel / 0 codec | 0 | PASS |

Per-duration breakdown:

| Duration | Dense acc | Pixel acc | Codec acc | Codec-dense | Codec-pixel | Reuse gap | Jaccard | Mean codec extract |
|----------|-----------|-----------|-----------|-------------|-------------|-----------|---------|--------------------|
| long | 0.300 | 0.300 | 0.300 | 1.000 | 1.000 | 0.017 | 0.667 | 615.2 s |
| medium | 0.500 | 0.600 | 0.500 | 1.000 | 0.900 | 0.023 | 0.293 | 92.6 s |
| short | 0.800 | 0.700 | 0.800 | 1.000 | 0.900 | 0.008 | 0.614 | 21.3 s |

Only two items differ between pixel and codec; codec equals dense on both:

| item | dense | pixel | codec | interpretation |
|------|-------|-------|-------|----------------|
| `videomme:medium:531-1` | choice 1, wrong | choice 2, correct | choice 1, wrong | pixel diverges from dense; codec preserves dense |
| `videomme:short:037-2` | choice 2, correct | choice 0, wrong | choice 2, correct | codec preserves dense and gold; pixel loses |

Offline extraction cost:

| Bucket | Sum codec extract | Mean | Min | Max |
|--------|-------------------|------|-----|-----|
| long | 6151.6 s | 615.2 s | 353.1 s | 904.0 s |
| medium | 925.7 s | 92.6 s | 25.4 s | 175.1 s |
| short | 213.0 s | 21.3 s | 10.5 s | 29.6 s |
| total | 7290.3 s | 243.0 s | — | — |

The run remained silent for roughly the native-rate extraction phase before
entering Qwen prefill. This is a methodology and tooling finding: future
medium/long codec-native sweeps need progress logging and per-item
checkpointing. It is also a paper-positioning constraint: this offline
sparse-sampling harness validates codec scores as a **semantic planner
substitution**, but it is not a systems speedup path. A speed claim still
requires codec metadata to be available from a streaming decoder path.

## Verdict

`H_duration_breadth` **PASSES**. Continuous H.264-derived codec scores with
per-item live-pixel calibration exactly preserve dense choices on VideoMME
dev all-duration n=30, with zero accuracy loss, zero parse failures, and
codec-pixel agreement 28/30.

C-CODEC can now move from "short first point" to "local codec-native
planner-substitution evidence", with two strict caveats:

1. The calibration is still per-item live-pixel calibrated. This is not a
   codec-only deployment recipe yet; calibration ablations remain the next
   scientific gate.
2. Offline native-rate extraction is too slow for a systems headline. The
   systems path must be streaming/decoder-integrated or cached, not this
   after-the-fact sparse-sampling retrofit.
