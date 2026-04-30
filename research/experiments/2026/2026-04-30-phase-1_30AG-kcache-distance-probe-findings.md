---
date: 2026-04-30 (initial); updated 2026-05-01 (rerun showed bug is not in the analyzer)
phase: 1.30AG (K/V cache-distance mechanism probe)
status: capture-earned (H1+H2+H3 PASS); H4 saturation gate FAILS because the captured K cache contains non-finite elements at every layer — bug is upstream of the analyzer reduction, not in it. **Distance numbers remain NOT release-claim-bearing.**
related:
  - 2026-04-23-phase-1_30-mechanism-decomposition-prereg.md
---

# Phase 1.30AG — K/V cache-distance probe (cache itself is NaN-poisoned; analyzer is faithful)

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

So the reduction style is not the root cause. The mean-form fix +
its CPU-side regression test were **reverted**.

The actual root cause is upstream: the captured K (and most V) cache
tensors contain non-finite elements before any reduction. The
decisive evidence is the reuse arm:

- `reuse_vs_dense.keys_mean_abs = 0.0` on every row — confirms the
  reuse-arm cache and the dense reference are bit-identical buffers.
- `reuse_vs_dense.keys_cosine = NaN` on every row — bit-identical
  finite buffers cannot produce NaN cosine.

The combination is only consistent with `l - r` short-circuiting to
zero (same-buffer subtraction in IEEE; works even when the buffer
contains NaN), while `l * l` and `l * r` do propagate NaN through
multiplication. The pruned arm's `keys_mean_abs = +inf` confirms at
least one element of the diff is non-finite — `mean(...inf...) / N
= inf` only if the sum sees an `inf` element directly.

Cross-layer pattern: in both runs, K-side cosine is NaN at every
layer, V-side cosine is finite at layer 1 only. That points at a
specific structural source of NaN in the K cache and to a lesser
extent the V cache, layer 0 specifically. Plausible candidates that
still need verification:

- pre-allocated K-cache buffer padding beyond `valid_tokens` is
  uninitialized (or sentinel-NaN), and the slice
  `value[..., 0:valid_tokens, :]` is not actually narrowing the tensor
  view in the reduction path (lazy view + stride math).
- Qwen 2.5-VL 4-bit MLX cache stores layer-0 K with NaN sentinels in
  unused positions (mask, padding, or fp16 underflow from the 4-bit
  dequant path).
- the rotary-embedding / RoPE pre-multiplied K values overflow
  bf16 specifically at layer 0 of this model.

Without instrumented reads of the live cache (e.g. a small probe
patch that prints `mx.any(mx.isnan(l_flat)).item()` and
`mx.max(mx.abs(l_flat)).item()` for one layer × one row before
reduction) we cannot pick between these. That diagnostic patch is
the next step if the user wants this probe revived.

## What the rerun establishes

- The bug is reproducible end-to-end and not flaky.
- It is not in the cosine reduction style.
- It is in the captured cache tensors themselves at the point the
  probe reduces them.
- The earlier "fp32 cast crashed with NSException" was sandbox-side
  (Metal init blocked); the actual rerun under sandbox-off completed
  in 30 minutes and reproduced the same NaN pattern. The crash was
  not informative about memory pressure.

## Path forward

1. Add a read-only NaN-audit print to the probe for one row at one
   layer before each reduction; confirm whether the non-finite
   elements live inside `[0:valid_tokens]` or only in the buffer tail.
2. If they live in the valid window, the cache itself is the bug —
   inspect the mlx-vlm cache write path or the rotary embedding for
   NaN-producing ops.
3. If they live only in the buffer tail and the slice is not
   narrowing the view, fix the narrowing (e.g. force materialize via
   `mx.contiguous` or copy before reduction) and rerun.

The probe code is checked in unmodified after the revert.

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
