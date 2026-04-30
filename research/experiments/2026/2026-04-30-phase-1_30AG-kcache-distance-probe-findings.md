---
date: 2026-04-30
phase: 1.30AG (K/V cache-distance mechanism probe)
status: capture-earned (H1+H2+H3 PASS); H4 saturation gate FAILED on analyzer-side numerical-stability bug; **distance numbers NOT release-claim-bearing pending analyzer fix + rerun**
related:
  - 2026-04-23-phase-1_30-mechanism-decomposition-prereg.md
---

# Phase 1.30AG — K/V cache-distance probe (cosine reduction broken; structure earned)

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

## Diagnosis (provisional)

`scripts/run_phase1_30AG_kcache_distance_probe.py:_distance_for_windows`
computes the cosine via:

```
dot   = mx.sum(l_flat * r_flat)
denom = mx.sqrt(mx.sum(l_flat * l_flat)) * mx.sqrt(mx.sum(r_flat * r_flat))
cosine = dot / mx.maximum(denom, mx.array(1e-12))
```

with `l_flat`, `r_flat` flattened from large bf16/fp16 cache windows.
On the order of `3295 * num_kv_heads * head_dim` elements per layer,
`sum(x * x)` can saturate the bf16/fp16 dynamic range and return
`+inf`. Then `inf / inf = NaN`, which propagates to `cosine_distance`
and the per-class summary. The same overflow path explains
`pruned_vs_dense.keys_mean_abs = +inf` (it uses `mx.mean(mx.abs(l - r))`
on the same flattened tensor).

Two candidate fixes:

1. **fp32 cast before reduction**: `l_flat = left_common.reshape(-1).astype(mx.float32)`
   then proceed. Tried in this session; produced an MLX-runtime abort
   (`libc++abi: terminating due to uncaught exception of type NSException`)
   on the first prefill, plausibly memory pressure from doubling the
   flattened tensor size on the same machine that was already at ~5.5 GB
   peak RSS for the rest of the chain.
2. **Normalize via `sqrt(mean(x*x))` instead of `sqrt(sum(x*x))`**:
   `l_unit = l_flat / max(sqrt(mean(l*l)), 1e-12)`, then
   `cosine = mean(l_unit * r_unit)`. Algebraically equivalent and keeps
   intermediate magnitudes bounded. Patch was drafted but **not
   verified end-to-end** in this session, so it is **not landed**.

The probe code is currently checked in unmodified; the row-level
distances are kept as-is in the artifact for traceability. Forward
work needs both: (a) fix the analyzer reduction, (b) re-run the probe.

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
