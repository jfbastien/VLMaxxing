---
date: 2026-04-27
status: staged; not yet run
---

# Paper Deep-Mechanism Queue Runbook

## Purpose

This queue is the post-review mechanism batch. It is not the broad deployment
baseline batch and it does not edit the paper. It runs six sequential
experiments:

1. **1.55F-stage-timing** — analysis-only attribution of adaptive-vs-fixed
   C-PERSIST speedup.
2. **1.63E** — Track B Qwen frame-budget scaling at 8f/16f/20f/32f.
3. **1.63G** — Gemma Track B sparse-ViT architecture check.
4. **1.55K** — adaptive C-PERSIST sampler-temperature sweep.
5. **1.65** — within-1.30 dense logit-margin predictor scout for paired
   stability.
6. **1.30AF** — post-hoc row-level attribution for the 1.30AC/AD boundary,
   including margin-stratified feature attribution if 1.65 lands.

The goal is to turn the paper's remaining mechanism claims from single-point
or descriptive evidence into cross-budget, cross-architecture, and predictive
evidence.

## Launch

Dry run:

```bash
./.venv/bin/python scripts/run_paper_deep_mechanism_queue.py --dry-run
```

Autonomous run with per-phase commits:

```bash
nohup ./.venv/bin/python scripts/run_paper_deep_mechanism_queue.py --auto-commit \
  > /tmp/claude/deep_mechanism_queue.log 2>&1 &
```

Optional overrides:

- `PHASE1_63E_FRAME_COUNTS="8 16 20 32"` is the default so every Qwen
  frame-budget cell is computed and gated inside one run. Override to
  `"16 20 32"` only when intentionally reusing the landed 8f cell as a
  non-veto reference.
- `PHASE1_55K_TEMPERATURES="0.5 0.7 1.0 1.5"` is the default adaptive
  sampler sweep. The landed greedy 1.55F cell is included as a `T=0.0`
  reference if present. The summary requires absolute cold-baseline accuracy
  >= 14/21 for every temperature before the sampler-robustness claim can pass,
  so mutual session/baseline collapse at high temperature is not accepted as a
  robustness result.
- `PHASE1_65_MAX_ROWS=0` is the default and scores the full 1.30AD/1.30AC
  source set. Nonzero values request a deterministic balanced debug subsample.

## Expected Runtime

- 1.55F-stage-timing: <1 min.
- 1.63E: ~7.5-9.5 h with 8f/16f/20f/32f.
- 1.63G: ~2.5-3.5 h.
- 1.55K: ~4-6 h.
- 1.65: ~5-8 h at default `PHASE1_65_MAX_ROWS=0`.
- 1.30AF: <1 min.
- Total: ~19-27 h default, sequential, no parallel MLX work.

## Interpretation Checklist

- If 1.55F-stage-timing passes, adaptive's speedup lead over fixed K=1 is
  attributable to Q3 re-prefill avoidance. The preregistered mechanism gate is
  intentionally modest (>=3x Q3 fixed/adaptive speedup); larger observed ratios
  should be reported as measured attribution, not assumed.
- If 1.63E passes across all frame counts, C-CEILING is predictive across
  frame budgets for Qwen Track B vision-only sparse execution.
- If 1.63G passes, Track B sparse-ViT evidence is not Qwen-only.
- If 1.55K passes, adaptive C-PERSIST is not just a greedy-decoding artifact
  over a sampler range whose cold baseline remains competent. If the paired
  drift gates pass but the absolute-baseline floor fails, report a sampler
  quality boundary instead.
- If 1.65 passes, dense margin becomes a held-out within-1.30 stability signal;
  report it as an oracle-feature predictor scout for the 1.30 boundary, not as
  an explanation of 1.55F adaptive stability and not as a deployed guard.
- If 1.30AF passes, write the 1.30AC/AD relationship as same aggregate loss
  via different row-level flip sets, not byte-equivalent behavior. Use the
  duration/q-index/cold-correctness/margin feature attribution to state whether
  the different flip sets concentrate in an interpretable subset; if they do
  not, say that direct tensor-distance probing remains the next mechanism test.
- If any Track B cell skips vision work but lacks end-to-end positivity, keep
  the result as a systems boundary: real ViT work was skipped, but non-ViT
  stages dominated the local wall-clock.
