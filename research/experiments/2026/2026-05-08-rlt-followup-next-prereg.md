# 2026-05-08 RLT/VLMaxxing Follow-Up Queue Preregistration

Status: round-17 queue executed; follow-up controls preregistered below.

## Context

The 2026-05-08 RLT follow-up run produced three reproduced-here facts:

- RLT-as-C-VISION at `keep_rate=0.5` is E2E-positive on Gemma 4 E4B / MLX-VLM
  across VideoMME, TOMATO, and MVBench.
- RLT's raw-frame motion scorer matches the expensive max-min diversity scorer
  on E2E speedup within a few percent while costing 81-122x less per item.
- RLT prompt admission is substrate-sensitive: default `prefill_step_size=2048`
  regresses, while lower prefill thresholds can recover positive prefill
  reduction by keeping both arms on the chunked path.

The round-17 queue then added three reproduced-here facts:

- The old magnitude scorer is not a clean control: it budgets K over the padded
  encoder row, while RLT and max-min budget K over valid encoder positions.
- Incremental composition is positive on all three benchmarks, but it is not a
  full dense-vs-composed measurement because both branches share RLT C-VISION.
- TOMATO keep-rate sweep supports `keep_rate=0.5` as the current Pareto knee;
  `0.3` is faster but visibly quality-stressed at n=30.

The next queue closes those two remaining paper gaps without changing the paper
source before the results exist.

## Local M3/M4-Class Queue

Command shape:

```bash
uv run python scripts/run_rlt_followup_queue.py \
  --run-cvision-rlt \
  --run-cvision-expansion \
  --run-max-min-triangulation \
  --run-magnitude-head-to-head \
  --run-magnitude-valid-head-to-head \
  --run-composition-incremental \
  --run-composition-direct \
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

### H1b: Valid-Position Magnitude Control

Hypothesis: valid-position magnitude should recover a meaningful fraction of
the old magnitude scorer's lost speed, because it no longer spends K on padded
encoder slots. If it matches RLT on speed and quality, the paper should frame
RLT primarily as a cheaper/pre-vision scorer. If it still loses, the stronger
claim is that pixel-domain temporal motion is a better saliency signal for
these video-QA workloads.

Gate: same C-VISION core gates as H1. This control reuses dense baselines and
therefore runs only after the RLT VideoMME gate.

Expected result: VideoMME improves from the old magnitude `0.97x` regression;
TOMATO/MVBench move closer to RLT but may still lag if hidden-state magnitude
is a worse task-relevance signal.

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

### H2b: Direct Full Composition

Hypothesis: dense baseline versus full RLT stack (`RLT-as-C-VISION + RLT prompt
admission`, both at `prefill_step_size=1024`) should exceed the multiplicative
estimate's lower bound but may not exactly equal the product because decode,
generation length, and MLX chunking interact with the branch timings.

Scope: this is the paper-facing full-stack measurement. It uses a dense
reference artifact with no sparse vision and no placeholder admission, paired
against a composed artifact with RLT sparse vision and RLT placeholder
admission. It does not reuse the incremental-composition dense branch.

Expected result: full dense-to-composed speedups in the neighborhood of the
round-17 estimates: roughly VideoMME `1.08-1.12x`, TOMATO `1.35-1.45x`, MVBench
`1.55-1.75x`. A miss falsifies the multiplicative-composition framing and
should replace estimates with measured direct values.

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
  --mlx-memory-limit-gb 60 \
  --artifact-dir research/experiments/2026/artifacts/rlt_followup_queue_m5_gemma4_26b \
  --run-cvision-rlt \
  --run-cvision-expansion \
  --run-max-min-triangulation \
  --run-magnitude-valid-head-to-head \
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
   valid-position magnitude, composition, and keep-rate sweep.
3. If composition quality fails, do not claim composition; keep C-VISION-only
   claims intact.
4. Direct full composition supersedes multiplicative estimates wherever it
   completes; estimates remain hypotheses only.
5. Keep-rate sweep runs only after the base RLT VideoMME gate because it is a
   Pareto refinement, not a rescue path for a failed base method.
