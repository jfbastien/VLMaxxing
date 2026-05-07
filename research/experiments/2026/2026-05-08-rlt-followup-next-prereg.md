# 2026-05-08 RLT/VLMaxxing Follow-Up Queue Preregistration

Status: preregistered, not yet executed in this note.

## Context

The 2026-05-08 RLT follow-up run produced three reproduced-here facts:

- RLT-as-C-VISION at `keep_rate=0.5` is E2E-positive on Gemma 4 E4B / MLX-VLM
  across VideoMME, TOMATO, and MVBench.
- RLT's raw-frame motion scorer matches the expensive max-min diversity scorer
  on E2E speedup within a few percent while costing 81-122x less per item.
- RLT prompt admission is substrate-sensitive: default `prefill_step_size=2048`
  regresses, while lower prefill thresholds can recover positive prefill
  reduction by keeping both arms on the chunked path.

The next queue is designed to close comparison and composition gaps without
changing the paper source before the results exist.

## Local M3/M4-Class Queue

Command shape:

```bash
uv run python scripts/run_rlt_followup_queue.py \
  --run-cvision-rlt \
  --run-cvision-expansion \
  --run-max-min-triangulation \
  --run-magnitude-head-to-head \
  --run-composition-incremental \
  --run-keep-rate-sweep
```

### H1: Magnitude Head-To-Head

Hypothesis: MLX-native magnitude scoring will be E2E-similar to RLT because
scorer cost is small relative to item latency, but may differ in quality.

Gate: run only after RLT VideoMME passes the core C-VISION gates: complete
pairing, fidelity, sparse-vision reduction, positive E2E, powered bucket E2E,
and sparse-induced parse-failure delta. Absolute parse rate and the Amdahl
ceiling diagnostic are reported but not hard gates.

Expected result: E2E within 1-3% of RLT on TOMATO/MVBench; quality is the
unknown axis.

### H2: Incremental Composition

Hypothesis: RLT prompt admission adds a small positive gain on top of
RLT-as-C-VISION when both arms use `prefill_step_size=1024`, but the gain is
limited because C-VISION does not change prompt geometry. The lower threshold is
intentional: it keeps typical RLT-pruned prompts on the chunked prefill path and
avoids repeating the known MLX-VLM single-shot substrate trap near 1500 tokens.

Scope: this is incremental composition, not full dense-vs-composed. Both paired
branches share RLT C-VISION sparse vision features; the difference is dense
placeholders versus RLT-pruned placeholders.

Expected result: VideoMME near 1.00-1.02x incremental E2E. Quality failure kills
the composition claim, but still supports the current C-VISION-only claim.

### H3: Keep-Rate Pareto Sweep

Hypothesis: the Pareto knee for RLT-as-C-VISION is around `keep_rate=0.4-0.5`
on TOMATO/MVBench. Lower keep rates should improve E2E and risk quality;
higher keep rates should preserve quality and shrink E2E gains.

Default sweep: TOMATO at keep rates `0.3, 0.5, 0.7, 0.85`, reusing the same
dense JSONL when present.

Expected result: `0.3` is the likely quality-stress point; `0.5` remains the
balanced point; `0.7/0.85` should approach dense quality with smaller speedups.

### Ceiling Diagnostic Note

The predicted-from-vision Amdahl ceiling is a diagnostic, not a hard result
ceiling. The completed TOMATO/MVBench n=30 cells showed that decode and
generation-token-count covariance can move actual E2E speedup by several
percentage points relative to a vision-share-only prediction. The follow-up
queue therefore reports the ceiling diagnostic but gates on measured paired
E2E, sparse-vision reduction, fidelity, bucket support, and sparse-induced
parse failures.

## M5 128GB Queue

Use the same Gemma family as the paper-scale target, not Gemma 3:

```bash
uv run python scripts/run_rlt_followup_queue.py \
  --gemma-model-path "$HOME/models/gemma-4-26b-a4b-it-4bit" \
  --rss-guard-mb 60000 \
  --artifact-dir research/experiments/2026/artifacts/rlt_followup_queue_m5_gemma4_26b \
  --run-cvision-rlt \
  --run-cvision-expansion \
  --run-max-min-triangulation \
  --run-magnitude-head-to-head \
  --run-keep-rate-sweep
```

Hypothesis: absolute E2E speedup may shrink as language/decode share grows, but
the scorer-cost ratio should widen because max-min scales with feature dimension
while RLT scoring stays raw-pixel-domain.

First gate on M5: n=1 smoke must pass shape, schema, scorer-timing, and memory
guards before any n=30 cells continue.

## Cancellation Tree

1. If RLT C-VISION smoke fails pairing or schema, stop all model cells.
2. If RLT VideoMME fails core C-VISION gates, skip expansion, max-min, magnitude,
   composition, and keep-rate sweep.
3. If composition quality fails, do not claim composition; keep C-VISION-only
   claims intact.
4. Keep-rate sweep runs only after the base RLT VideoMME gate because it is a
   Pareto refinement, not a rescue path for a failed base method.
