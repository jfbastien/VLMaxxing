---
phase: 1.41
date: 2026-04-21
parent: research/experiments/2026/2026-04-19-phase-1_41-qwen-videomme-16f-findings.md
prior:
  - research/experiments/2026/2026-04-19-phase-1_41-qwen-videomme-16f-findings.md
  - research/experiments/2026/2026-04-18-phase-1_41-qwen-videomme-baseline-findings.md
status: prereg (Qwen 7B 16f VideoMME holdout n=30 — dev-to-holdout frame-scaling cross-check)
tracking: autonomous session 2026-04-21 should-do #7
---

# 1.41 Qwen 16f VideoMME holdout — prereg (strengthener, not a gate)

## Motivation

Claim 8 (VideoMME earned on Qwen 7B) is currently **dev-only** across
8f/16f/32f (per `claim-matrix.md:32`). The 16f dev run (2026-04-19)
produced the most surprising finding on the frame-scaling surface:
aggregate +3.3pp, medium +30pp, **long −20pp** — a non-monotonic
shape that is the paper's cleanest example of bucket-conditional
frame-scaling non-linearity. If this shape replicates on the disjoint
holdout, the "long bucket regresses at 16f" framing becomes
paper-grade evidence on both splits; if it does not replicate, the
claim is dev-only and the paper must soften it.

This run is an **incremental strengthener**, not a gate. No headline
cell flips on the outcome.

## Pre-registered predictions (same structure as 16f dev prereg)

Two hypotheses — the interesting one is replication of the
non-monotonic shape.

**H1 (aggregate replication)**: holdout 16f `dense_acc ∈ [0.50, 0.70]`.
Rationale: dev 16f landed 0.567; the holdout is smaller-sample and
disjoint, so ±0.10 window is calibrated to small-n noise. **Falsification:**
aggregate < 0.45 (holdout is materially harder than dev) OR > 0.75
(sampling artifact).

**H2 (long-bucket regression replicates)**: holdout 16f `long_acc ≤
long_acc(holdout 8f)`, with best-guess long drops by ≥ 5pp. Rationale:
dev 16f long −20pp vs 8f was the cleanest non-monotone signature
observed on Gemma/Qwen at any frame count — if mechanism is real
(attention-mixing saturation on long-form items), it should replicate
across an independent item draw. **Falsification:** long_acc(16f) >
long_acc(8f) + 5pp.

**H3 (short/medium buckets flat or lift)**: holdout 16f
`short_acc ∈ [0.60, 0.95]` AND `medium_acc ∈ [0.40, 0.90]`.
Wide-band — just asking for "not broken". **Falsification:** either
bucket < 0.30 (catastrophic regression).

**H4 (agreement to identity cache bit-faithful)**: `agreement = 1.000`.
Rationale: bit-identity has held at 8f and 16f dev; expected to hold
unconditionally at 16f holdout too. **Falsification:** agreement <
1.000 on any item.

**H5 (RSS headroom)**: peak RSS ≤ 10 GB (4 GB margin vs 14 GB
ceiling). Rationale: dev 16f was 7.227 GB / item stable. **Falsification:**
> 13 GB on any item.

## Decision matrix

| H1 | H2 | Interpretation |
|----|----|----------------|
| pass | pass | **non-monotone shape earned on holdout** — paper can cite both splits |
| pass | fail | "long −20pp" framing is dev-only — paper must soften |
| fail (low) | any | VideoMME holdout is harder than dev — note sampling, acc banner changes |
| fail (high) | any | small-n artifact — no claim flip |

## Configuration

Mirrors 16f dev invocation (`2026-04-19-phase-1_41-qwen-videomme-16f-prereg.md:94-102`):

```
model-path        /Users/jfb/models/Qwen2.5-VL-7B-Instruct-4bit (script default)
benchmark         videomme
manifest          research/benchmark_manifests/videomme_holdout_v1.toml
frame-count       16
cache-mode        identity
max-tokens        32
output            research/experiments/2026/artifacts/phase1_41_qwen_videomme_16f_holdout/dense_n30.jsonl
summary           research/experiments/2026/artifacts/phase1_41_qwen_videomme_16f_holdout/dense_n30_summary.json
```

## Runtime

Dev 16f took ~75 s / item (n=30) ≈ 37 min wall-clock. Holdout is n=30
disjoint items with similar per-bucket composition; expected 30-45 min
total. Well within autonomous-session bucket.

## Non-goals

- No pruning arm (C-VISION is Gemma-only until Qwen vision-tower
  pruning lands, see `priority.md` should-do #3).
- No 32f holdout (deferred; 32f dev already landed and long-bucket
  plateaued there at 0.10).
- No thermal pairing (this is dense-only; no paired arm to compare
  against in-run).
