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

The round-18 queue then added two reproduced-here facts:

- Direct dense-vs-full-composition is strongly E2E-positive but not uniformly
  quality-clean: VideoMME `1.070x` with Δacc `-0.033`, TOMATO `1.275x` with
  Δacc `0.000`, and MVBench `1.899x` with Δacc `-0.167`. The failures are
  bucket-local rather than global.
- Valid-position magnitude does not close the gap to RLT. Fixing K accounting
  helps the control, but it still trails RLT on this stack; the saliency signal
  matters, not just the budget denominator.

The round-19 queue then added three reproduced-here facts:

- Bucket-specific rescue is not a universal quality fix. VideoMME rescue remains
  essentially unchanged, TOMATO rescue weakens quality, and MVBench rescue trades
  the `1.899x` speed frontier for `1.403x` while recovering
  `object_interaction`.
- MVBench `moving_attribute` remains the hard counterexample: raising both
  admission and vision keep-rate to `0.85` does not recover the bucket. The
  result points away from "just keep more motion tokens" and toward a later
  query-aware/static-detail policy.
- The direct-composition speed frontier is real, but the quality story must be
  phrased gate-first. The clean local claim today is "RLT C-VISION is robustly
  positive; full composition is high-upside and benchmark/bucket conditional,"
  not "MVBench rescue is paper-clean."

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
  --run-composition-rescue \
  --run-composition-holdout \
  --run-composition-rescue-holdout \
  --run-moving-attribute-bracket \
  --run-composition-combined-analysis \
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

### H2c: Bucket-Specific Composition Rescue

Hypothesis: the direct-composition quality loss is group-local and recoverable
by raising K only in the failed groups. This follows the RLT literature's core
assumption that temporal redundancy is not uniformly distributed, and matches
the observed round-18 failures:

- VideoMME failed `long` and `medium`; rescue uses keep-rate `0.7` for those
  two groups and keeps `short` at `0.5`.
- TOMATO failed `direction`; rescue uses keep-rate `0.85` for `direction` and
  keeps `rotation` / `shape_trend` at `0.5`.
- MVBench failed `moving_attribute` and `object_interaction`; rescue uses
  keep-rate `0.85` for those groups and keeps the other motion groups at `0.5`.

Gate: run only after RLT VideoMME core C-VISION gates pass. If the base direct
composition already passes all direct gates for a benchmark, skip that
benchmark's rescue cell. A rescue pass requires aggregate fidelity, positive
E2E, sparse-induced parse-failure parity, and bucket-level quality+E2E.

Expected result: VideoMME should trade a small amount of speed for cleaner
quality (`~1.03-1.06x`). TOMATO should remain meaningfully positive
(`~1.15-1.25x`) if `direction` was the only sensitive group. MVBench is the
decisive cell: success would turn the `1.90x` speed frontier into a safer
class-conditional policy around `1.45-1.70x`; failure would say fine-grained
attribute/interaction questions need query-aware or static-detail protection,
not just more tokens in the same RLT policy.

### H2d: MVBench Moving-Attribute Dense-Bracket

Hypothesis: if `moving_attribute` is merely token-budget-bound, then setting
that bucket to `keep_rate=1.0` while preserving the known `object_interaction`
rescue at `0.85` should recover the bucket. If it does not recover, the failure
is structural: RLT's motion prior is dropping static appearance evidence that
must be protected by query-aware/static-detail routing rather than more of the
same motion-ranked tokens.

Scope: `--run-moving-attribute-bracket` runs one MVBench full-composition cell:
`moving_attribute=1.0`, `object_interaction=0.85`, all other groups at the base
`0.5` keep-rate. It is not a new headline policy unless it recovers quality
with measured E2E still above `1.0`; its primary role is diagnosis.

Expected result: if `moving_attribute` remains near the dev-slice `Delta acc =
-0.50`, query-aware/static-detail routing becomes the right next branch. If it
recovers, the current paper should frame the failure as budget-bound and use a
per-bucket dense fallback or higher-K policy for that class.

### H3: Keep-Rate Pareto Sweep

Hypothesis: the Pareto knee for RLT-as-C-VISION is around `keep_rate=0.4-0.5`
on TOMATO/MVBench. Lower keep rates should improve E2E and risk quality;
higher keep rates should preserve quality and shrink E2E gains.

Default sweep: TOMATO at keep rates `0.3, 0.5, 0.7, 0.85`, reusing the same
dense JSONL when present.

Expected result: `0.3` is the likely quality-stress point; `0.5` remains the
balanced point; `0.7/0.85` should approach dense quality with smaller speedups.

### H4: Disjoint Holdout Composition Replication

Hypothesis: direct full composition should replicate as an E2E-positive result
on disjoint VideoMME, TOMATO, and MVBench holdout manifests, but the quality
gate may remain bucket-conditional. This is the replication gate for any
paper-facing full-composition headline.

Scope: `--run-composition-holdout` uses the existing holdout manifests:

- `videomme_holdout_v1.toml` (`30` items)
- `tomato_motion_holdout_v2.toml` (`30` items)
- `mvbench_motion_holdout_v2.toml` (`30` items, `6` per group)

Footgun: `videomme_combined_v1_n60.toml` is the dev+holdout superset. Dev-only
and holdout-only replication must use `videomme_dev_v1.toml` and
`videomme_holdout_v1.toml` explicitly when the boundary matters.

Gate: run only after the RLT VideoMME core C-VISION gate passes. Each benchmark
must independently clear aggregate fidelity, positive measured E2E,
sparse-induced parse-failure parity, and bucket-level quality+E2E. If a direct
holdout cell fails, `--run-composition-rescue-holdout` applies the same
pre-registered group keep-rate override for that benchmark and supersedes the
base row only if it clears the same gates.

Expected result: VideoMME should remain modestly positive and decode-limited;
TOMATO should remain positive if the dev result was not slice-specific; MVBench
is the decisive replication. If holdout MVBench again shows large speed with a
`moving_attribute` failure, the paper should promote the failure as the
query-aware motivation rather than tune another global RLT keep-rate.

### H4b: Pooled Dev+Holdout Analysis

Hypothesis: pooling dev and holdout rows after both have been measured should
tighten confidence intervals without changing the qualitative result. This is
an analyzer-only pass; it is not a new measurement.

Scope: `--run-composition-combined-analysis` runs n=60 analyzer passes for
direct full composition and rescue composition by concatenating the paired dev
and holdout JSONLs. It requires both source artifacts to exist and hard-fails
on duplicate item IDs.

Expected result: the n=60 direct and rescue summaries should either confirm the
dev narrative with tighter CIs, or reveal that the dev slice was too optimistic.
If dev and holdout disagree materially, the paper should report replication
variance instead of a single pooled headline.

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
export GEMMA_MODEL_PATH=/path/to/sams/gemma-4-26b-or-paper-target-mlx-model
uv run python scripts/run_rlt_followup_queue.py \
  --gemma-model-path "$GEMMA_MODEL_PATH" \
  --frame-count 8 \
  --rss-guard-mb 60000 \
  --mlx-memory-limit-gb 60 \
  --artifact-dir research/experiments/2026/artifacts/rlt_followup_queue_m5_gemma4_26b \
  --run-cvision-rlt \
  --run-cvision-expansion \
  --run-max-min-triangulation \
  --run-magnitude-valid-head-to-head \
  --run-magnitude-head-to-head \
  --run-composition-direct \
  --run-composition-rescue \
  --run-composition-holdout \
  --run-composition-rescue-holdout \
  --run-moving-attribute-bracket \
  --run-composition-combined-analysis \
  --run-keep-rate-sweep
```

Hypothesis: absolute E2E speedup may shrink as language/decode share grows, but
the scorer-cost ratio should widen because max-min scales with feature dimension
while RLT scoring stays raw-pixel-domain. Composition and rescue cells now pass
the same `--mlx-memory-limit-gb` cap as Track-B C-VISION cells so high-memory
runs fail inside MLX rather than through whole-system memory pressure.

Operational blocker before M5 launch: verify the exact model directory and
`model.config.model_type` on Sam's machine with an n=1 smoke. Do not assume a
username or the illustrative path above; `$GEMMA_MODEL_PATH` must point to the
actual MLX model used by this paper's Gemma-family scale check.

First gate on M5: n=1 smoke must pass shape, schema, scorer-timing, and memory
guards before any n=30 cells continue.

The M5 block intentionally skips `--run-composition-incremental`: direct
dense-vs-full-composition supersedes the incremental cell for the paper-facing
scale check. It also keeps `--frame-count 8` explicit to avoid mixing in the
known non-monotonic frame-count effects from earlier scale studies.

## Cancellation Tree

1. If RLT C-VISION smoke fails pairing or schema, stop all model cells.
2. If RLT VideoMME fails core C-VISION gates, skip expansion, max-min, magnitude,
   valid-position magnitude, composition, and keep-rate sweep.
3. If composition quality fails, do not claim composition; keep C-VISION-only
   claims intact.
4. Bucket-specific rescue supersedes failed direct-composition rows only if it
   clears the direct full-composition gate with measured E2E still above 1.0.
5. Direct full composition supersedes multiplicative estimates wherever it
   completes; estimates remain hypotheses only.
6. Holdout composition is the replication gate. Dev-slice full composition
   should not become the headline unless the corresponding holdout cell supports
   it or the paper explicitly labels the dev result as exploratory.
7. The moving-attribute bracket runs only after the base RLT VideoMME gate and
   answers a diagnostic question: budget-bound failure versus structural
   query-aware/static-detail need.
8. Pooled dev+holdout analysis runs only after source artifacts exist. It
   increases analysis power but does not replace reporting dev/holdout
   replication separately when they disagree.
9. Keep-rate sweep runs only after the base RLT VideoMME gate because it is a
   Pareto refinement, not a rescue path for a failed base method.
