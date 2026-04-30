---
date: 2026-04-30 (initial); 2026-05-01 (rerun + math retraction); 2026-05-01 (CLOSED-EARNED after finite-audit telemetry)
phase: 1.30AG (K/V cache-distance mechanism probe)
status: CLOSED-EARNED. All four gates PASS using the fp32 control cosine column. Cache is finite at every layer; the original NaN cosine was fp16 sum-of-squares overflow in the cosine reduction, not upstream pathology. H4 saturation HOLDS: reuse-arm cache cosine vs dense ≈ 1.0 (bit-identical), pruned-arm cosine 0.724 K / 0.296 V (substantial divergence).
related:
  - 2026-04-23-phase-1_30-mechanism-decomposition-prereg.md
---

# Phase 1.30AG — K/V cache-distance probe (CLOSED-EARNED via fp32 cosine column)

## Question

After Phase A's six-arm scout, the open mechanism question for the
1.30 composition Δacc=−0.193 was: does the K-side cache distance
between dense and reuse vs. dense and pruned actually saturate (i.e.,
small for reuse, large for pruned), or are both arms producing
similar K traces? Phase 1.30AG probes per-layer K/V distance under
fixed `vision_tower_layer=2`, `vision_tower_keep_rate=0.50`,
`max_pairs=20`.

## Method

- driver: `scripts/run_phase1_30AG_kcache_distance_probe.{sh,py}`
  (chain-runner step A5).
- selection: 5 rows per drift class across `{shared_drift,
  reuse_only_drift, invalidated_only_drift, stable}` (20 total).
- per-row, per-layer cache-tensor capture: `keys` and `values`
  windows from `mlx-vlm` cache state at follow-up (Q2 or later).
- distance metrics: per-layer cosine, cosine-distance, mean-abs,
  RMS over the common valid-token prefix.
- aggregation: per-row mean over layers, then per-class mean,
  then headline relative-gap for `reuse_vs_dense` vs.
  `pruned_vs_dense` on K and V.

## Results

20 rows captured, 5 per class as planned. Wall time 39.9 min.

`kcache_distance_summary.json` headline gate: **`headline_pass: false`**.
Detail:

- `pass_H1_row_count: true`
- `pass_H1_cache_states_captured: true`
- `pass_H1_same_valid_lengths: true` (no token-length mismatches)
- `pass_H1_capture: true`
- `pass_H2_distance_report: true`
- `pass_H3_outcome_link: true`
- **`pass_H4_saturation_test: false`**

The H4 fail is **caused by the cosine reduction returning `NaN` on
every row at every layer** (and `mean_abs = inf` on the `pruned_vs_dense`
side), not by the saturation hypothesis being scientifically false.
This is an analyzer numerical-stability bug, not an experiment failure.

### Concrete row-level evidence (row 0, layer 0)

`reuse_vs_dense` (per-layer):

| field | value |
|---|---|
| `keys_common_tokens` | 3295 |
| `keys_mean_abs` | 0.0 |
| `keys_rms` | 0.0 |
| `keys_cosine` | **NaN** |
| `keys_cosine_distance` | NaN |
| `keys_same_valid_token_length` | true |

`pruned_vs_dense` (per-layer):

| field | value |
|---|---|
| `keys_common_tokens` | 3295 |
| `keys_mean_abs` | **+inf** |
| `keys_rms` | +inf |
| `keys_cosine` | **NaN** |
| `keys_same_valid_token_length` | true |
| `values_cosine` | 0.0 |
| `values_rms` | 0.194 |

The `reuse_vs_dense` side has bit-identical tensors
(`mean_abs = 0`, `rms = 0`) yet returns `NaN` cosine. The
`pruned_vs_dense` side has finite RMS for V (0.194) but
`mean_abs = +inf` for K. Both are inconsistent with a clean
finite-arithmetic reduction, so the per-layer cosine column is
unreliable.

## Diagnosis (revised 2026-05-01 after rerun)

The initial diagnosis blamed an `mx.sum(x*x)` overflow in
`scripts/run_phase1_30AG_kcache_distance_probe.py:_distance_for_windows`.
A mean-form variant (`mx.sum` → `mx.mean`, mathematically equivalent
for cosine because the N factor cancels in the ratio) was landed and
the probe was re-run with sandbox off. The rerun's per-layer cosine
counts and aggregate means were **bit-identical** to the original
sum-form run:

| field | sum-form | mean-form |
|---|---|---|
| reuse_keys cosine finite | 0/560 | 0/560 |
| reuse_values cosine finite | 19/560 | 19/560 |
| pruned_keys cosine finite | 0/560 | 0/560 |
| pruned_values cosine finite | 58/560 | 58/560 |
| `mean_reuse_keys_mean_abs` | 1.7352934e-05 | 1.7352934e-05 |
| `pass_H4_saturation_test` | False | False |

The mean-form fix + its CPU-side regression test were **reverted**
because the rerun showed bit-identical NaN counts.

**Two hypotheses remain live and the artifact does not yet
discriminate.** This is a correction to the earlier 2026-05-01 draft
that asserted the upstream-cache-NaN hypothesis as confirmed.

(a) **Upstream cache contains non-finite elements** — what the
earlier draft claimed.

(b) **`mx.sum(x*x)` overflows in bf16** in the cosine denominator —
identical finite vectors of shape ~3300×7×128 = ~3M bf16 elements
can produce `dot = sum(l*r) → +inf`, `denom = sqrt(sum(l*l)) *
sqrt(sum(r*r)) = inf * inf → +inf`, and therefore `cosine = inf/inf
→ NaN`. `mean_abs = mean(|l - r|)` correctly returns 0 because the
two vectors are bit-identical so `l - r = 0` everywhere. `rms = 0`
agrees.

Why the earlier "same-buffer subtraction shortcut" inference was
**wrong as stated**: under IEEE 754, `NaN - NaN = NaN` (not zero).
MLX does not enable fast-math reassociation by default, so even if
`l` and `r` reference the same memory, the elementwise subtraction
produces NaN at any NaN positions; `mean(abs(NaN))` would be NaN, not
0. The observed `reuse_keys_mean_abs = 0.0 on 533/560 layers exactly`
is therefore strong evidence that the underlying buffers are finite,
not NaN-poisoned — pointing at hypothesis (b), not (a).

Why the mean-form rerun **does not discriminate**: MLX's
`mx.mean(a)` is implemented as `sum(a) * (1/N)` and the `sum` for
fp16/bf16 inputs does not upcast its accumulator. Verified against
`ml-explore/mlx@main mlx/ops.cpp`: the `out_type` switch in
`array sum(...)` only promotes integer/bool dtypes; floats keep their
input dtype. So `mean(x*x)` overflows on the same input where
`sum(x*x)` overflows. Bit-identical post-fix output is fully
consistent with overflow.

Cross-layer pattern: K-side cosine NaN at every layer (0/560 finite),
V-side cosine finite at layer 1 only (~10% finite). The pruned arm's
`keys_mean_abs = +inf` on every layer is consistent with the diff
`(l - r)` containing at least one bf16-overflow-magnitude element
when one side is the dense cache and the other is the pruned cache,
because the pruned vision-tower path can plausibly produce
larger-magnitude K values at the cut layers. Both observations are
also consistent with hypothesis (a). The artifact does not separate.

## What the rerun establishes

- The bug is reproducible end-to-end and not flaky.
- It is not the sum-vs-mean reduction-style choice.
- The bit-identical mean-form output is **not** a discriminator
  between hypothesis (a) and (b) given how MLX implements `mean`.
- The earlier "fp32 cast crashed with NSException" was sandbox-side
  (Metal init blocked), not memory pressure. Disregard that clue.

## Closure (2026-05-01) — finite-audit rerun discriminates decisively

The finite-audit telemetry patch shipped in commit `6cc5d32` and the
sandbox-off rerun completed in 30 min. The fp32 control cosine column is
finite at every layer × row × arm; the per-window NaN/Inf/max-abs audit
shows zero non-finite elements anywhere in the valid window OR in the
buffer tail past `valid_tokens`. The native fp16 cosine column remains
NaN at every K layer (and most V layers) — the discriminator is
unambiguous.

**Hypothesis (b) confirmed: fp16 sum-of-squares overflow in the cosine
reduction.** The captured cache is **fp16** (verified via
`cache_dtype_observed = mlx.core.float16`, not bf16 as the earlier
draft assumed); fp16 max is 65504 and a single squared element at
|x| ≥ 256 saturates. Observed max-abs across all K layers ranges
11.2 → 420.75 with mean 43.76, so several layers carry single
elements that saturate `x*x` in fp16, polluting `sum(x*x)` to `+inf`
and then `dot/denom = inf/inf = NaN`. The fp32 control upcasts only
the cosine inputs and is bit-stable across the same windows.

Hypothesis (a) (upstream cache NaN poisoning) is **falsified**:
`valid_window_nan_layers = 0` and `valid_window_inf_layers = 0` for
every (row × kv × arm). The buffer tail past `valid_tokens` also has
`max_abs = 0` and zero non-finite elements, so the slice in
`_token_prefix` really does narrow the view in the reduction path.

The earlier draft's "same-buffer subtraction shortcuts NaN" inference
was IEEE-incorrect. `NaN - NaN = NaN` always under IEEE 754 and MLX
does not enable fast-math reassociation by default; the actual reason
`reuse_keys_mean_abs = 0` co-occurs with `cosine = NaN` is that the
buffers are finite and bit-identical (so subtraction produces zero)
but `sum(x*x)` overflows in fp16. The earlier draft has been retracted
in `ef7b7da`.

## Headline numbers (the saturation answer)

Computed from `kcache_distance_summary.json` after re-aggregation
sourcing the headline metrics from the fp32 cosine column. Native fp16
columns are kept for traceability but are mostly NaN-overflowed.

| arm | mean cosine_fp32 | mean cosine_fp32 distance |
|---|---|---|
| reuse_vs_dense (K) | 1.000 | ~0 |
| reuse_vs_dense (V) | 1.000 | ~0 |
| pruned_vs_dense (K) | 0.724 | 0.276 |
| pruned_vs_dense (V) | 0.296 | 0.704 |

**Saturation relative gap** = `|reuse_distance - pruned_distance| /
max(...)`:

| axis | gap |
|---|---|
| keys | 0.9999993 |
| values | 0.9999989 |

Both essentially 1.0 (pruned distance is ~∞× the reuse distance under
relative-gap normalization). The H4 gate is `gap >= 0.5` for both K
and V, so saturation HOLDS by a wide margin.

## Mechanism interpretation for 1.30

Pruning at vision-tower layer L=2 with kr=0.5 produces:

- **Substantial K-cache divergence vs dense**: cos 0.724
  (cosine-distance 0.276). The K projection at later language-model
  layers sees a meaningfully different attention key space when
  upstream visual tokens are pruned.
- **Dominant V-cache divergence vs dense**: cos 0.296
  (cosine-distance 0.704). The V projection diverges much more than
  K, consistent with V values being downstream of attention-weighted
  visual content.
- **Reuse-arm cache is essentially identical to dense**: cos ≈ 1.0
  for both K and V. Same-prefix Q0 cache reuse preserves the cache
  state to fp16 precision.

This is the saturation pattern the probe was designed to detect. The
1.30 mechanism question — "does pruning at vision layer L=2 produce
different K cache state from dense?" — is now answered "yes,
substantially different K and dominantly different V, while the
no-prune Q0-reuse arm preserves the cache exactly."

**Caveat**: the `reuse_only_drift` class shows non-zero
`mean_reuse_keys_mean_abs = 6.94e-5` driven by a single row (Q index
7); all other reuse rows are bit-identical (mean_abs = 0.0). That row
shows layer-systematic ~1e-4 drift on the reuse arm. Worth a footnote
in any paper-side use, not a closure blocker.

## What the artifact looks like now

- `kcache_distance_rows.jsonl` — 20 rows × 28 layers × 2 arms × 2
  (k/v) with finite-audit telemetry, fp32 control cosine, native
  fp16 cosine (NaN where the reduction overflows), and explicit
  `nonfinite_count` per layer.
- `kcache_distance_summary.json` — re-aggregated via
  `scripts/reaggregate_phase1_30AG.py` (MLX-free) so future analyzer
  changes can be applied without re-running the 30-min capture.
- `cache_dtype_observed = mlx.core.float16` is recorded in the
  summary so consumers know the native-cosine column is fp16-overflow,
  not bf16-overflow.

## Interpretation (what we can and cannot say)

- **Captured**: cache states captured for 20 paired rows balanced
  across 4 drift classes; per-row valid-token alignment confirmed
  (no length mismatches).
- **Cannot interpret**: per-layer K/V cosine, the
  reuse-vs-pruned saturation gap, and any K-distance ordering
  across drift classes. All those readings are NaN-poisoned.
- **Faintly interpretable**: `reuse_vs_dense.keys_mean_abs = 0.0`
  on every row indicates that the K cache for the reuse arm is
  bit-identical to the dense reference within the captured prefix.
  The pruned arm's `mean_abs = +inf` is an artifact, not a
  measurement.

## Falsified hypotheses

None — no scientific hypothesis is yet adjudicated, only the
analyzer's numerical path.

## Open questions

- Does the saturation gate H4 hold once the cosine reduction is
  numerically clean? Without that, the 1.30 mechanism story
  cannot use this probe.

## Next steps

1. Patch `_distance_for_windows` to do reductions in a
   numerically stable form (`sqrt(mean)` route preferred over
   the fp32 cast given the OOM hint).
2. Add a CPU-side regression test on a small synthetic tensor pair
   (identical / orthogonal / scaled) to lock the reduction.
3. Re-run A5 (`bash scripts/run_phase1_30AG_kcache_distance_probe.sh`,
   ~40 min).
4. If H4 still fails after the fix, that is a real null and should
   feed back into the 1.30 root-cause Phase B/C plan rather than
   blocking the chain.

## Cross-references

- Phase 1.30 root-cause Phase A: 2026-04-23-phase-1_30-mechanism-decomposition-prereg.md
- Composition safety memory: `project_composition_safety_2026-04-23.md`
  (Δacc=−0.193 on 1.30 K+V composition).
- Artifacts: `research/experiments/2026/artifacts/phase1_30AG_kcache_distance_probe/`.

## Caveats

- The 20 paired rows are stratified, not random. Generalization beyond
  the four drift classes is not claimed.
- Single sampler seed (42), single keep-rate (0.50), single
  vision-tower-layer (2). The probe is mechanism instrumentation, not
  a sweep.
- **Distance numbers are not release-claim-bearing in this run.**
