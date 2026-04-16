# Planner Sweep Methodology

Last updated: 2026-04-16. Prior version preserved in git history;
this rewrite reflects the post-CodecSight methodology tranche
(phases 1.10–1.12.B, 1.19, 1.26, and the 2026-04-16 audit).

## Goal

Search routing policies without silently changing the evaluation
slice, without overcounting via grid holes, and without mixing
semantic validation with Track B performance claims.

## Current policy axes

The benchmark runner exposes six first-class policy knobs:

| knob | values |
|---|---|
| planner statistic | `mean`, `max_abs`, `changed_pixel_fraction`, `top_k_mean` |
| thresholds | `(static, shifted)` per statistic; plus `pixel_change_threshold` and `top_k` for CPF / TOP_K_MEAN |
| reuse classes | `static`, `static+shifted` |
| bounded token age | `max_age ∈ {None, 2, 4, 8}` |
| sticky window (new, phase 1.26) | `sticky_window ∈ {None, 4, 8}` |
| frame refresh interval | `0` (off) or positive k |

Not-first-class yet (future phases):

- projector-group completion (phase 1.27 preregistered)
- motion-vector signal source instead of pixel diff (phase 1.29)

## Reporting contract

Every sweep note should state:

1. The exact manifest used.
2. Whether the manifest is `dev` or `holdout`.
3. The policy grid searched, **including which combinations were
   SKIPPED** (e.g., per-bin=1 will skip some age × threshold
   combinations; document this).
4. The default baseline(s) used for comparison — specifically, the
   matched dense frame-budget curve at the same `frame_count`
   range.
5. The chosen selection rule for advancing a policy to holdout.
6. If any cross-benchmark transfer winner is being tested, state
   which benchmark discovered it and which phase produced the
   discovery.

Sweep artifacts record, at minimum:

- dense_accuracy / cached_accuracy / agreement (all per item AND
  aggregated)
- active reuse ratio + raw reuse ratio (per-frame-pair AND mean)
- planner config
- refresh interval
- sticky_window
- manifest path + benchmark

## Selection rule (UPDATED per 2026-04-16 audit)

Previous rule said "promote exactly one policy to the corresponding
holdout." This is tightened and made consistent with the Pareto
reporting doc.

### Rule 1: dev-only search

Search on `*_dev_v1.toml` only. Do not inspect holdout during the
search.

### Rule 2: candidate set, not single winner

Promote either:

- **one** policy if a single policy strictly dominates on the
  inter-cached 2D skyline `(cached_accuracy, effective_fresh_frames)`
- **up to five** tied policies if the top cached_accuracy tier is
  tied, with explicit rationale recorded per
  `docs/methodology/pareto-reporting.md#top-k-allowance`

### Rule 3: non-tied extras are separated

If the promotion list includes both "top tier" and "lower-tier
diagnostic" points (as phase 1.12 did with 3 × 0.733 + 2 × 0.667),
separate them in the launch spec as `primary` and
`diagnostic_extras`. Diagnostic extras still get evaluated, but
they contribute to a different conclusion (content-class
coverage) than the primary tied set (Pareto survival).

### Rule 4: dedupe non-binding age variants BEFORE selection

On frame_count=N clips, `max_age >= N-1` never binds. Two policies
that differ only in a non-binding age are empirically identical.
Dedupe before passing to the holdout launch list. See
`scripts/select_holdout_winners.py::_dedupe_equivalents`.

### Rule 5: cross-benchmark transfer is a separate category

If a policy was discovered on benchmark A's dev and we test it on
benchmark B's holdout, that's a **transfer-discovered follow-up
test**, preregistered as a distinct phase (e.g., 1.12.B). The
holdout number is still one-shot but the selection provenance is
different. Frame accordingly (see pareto-reporting.md).

## Search strategy (NEW: factorized, 2026-04-16)

Previous search style (calibrate-then-per-bin sampling) missed the
cross-benchmark-winning `max_abs(8,32) age=4` because per-bin=1 on
the (8,32) threshold set picked noage + age=8 and skipped age=4.
Factorized search avoids that failure mode:

### Stage A (coarse): statistic × reuse_classes

Fix `max_age=None` and a median threshold pair per statistic.
Evaluate all combinations. Identify promising statistic + reuse_class
regions.

### Stage B (threshold refinement): grid over thresholds in promising regions

For each (statistic, reuse_classes) winner from Stage A, sweep
threshold pairs at `max_age=None` only.

### Stage C (age sweep): per surviving threshold, sweep max_age

For the top-3 (statistic, thresholds, reuse_classes) regions, sweep
`max_age ∈ {None, 2, 4, 8}` explicitly. This avoids the per-bin
sampling that hid age=4.

### Stage D (sticky + projector): apply mechanism refinements

Apply sticky_window and projector-group-completion to the top surviving
policies. See phases 1.26 and 1.27.

## Search discipline

- Search on `*_dev_v1.toml` only.
- Promote per Rule 2/3 above.
- If the holdout misses materially, record the miss and do not
  overwrite it.
- Do not cite dev-sweep best numbers as final evidence.
- Do not call a single threshold point per statistic a "sweep" —
  that is only a probe.
- Use dense feature replay to accelerate repeated Track A policy
  runs, but do not treat replay as systems evidence.
- When comparing statistics, use calibrated threshold grids (v2
  calibration since phase 1.19) before interpreting quality
  differences.
- Keep matched dense frame-budget baselines alongside planner
  sweeps so policy wins are not mistaken for wins over equally
  expensive dense alternatives.

## Current working hypothesis (updated 2026-04-16)

The default `mean` planner under-reports small-area, temporally
concentrated changes inside a 28×28 merged-token block. `max_abs` is
more sensitive to brief semantic events.

Refined hypothesis after phase 1.11 + 1.12.B:

- The strongest current policy family is `max_abs(8,32)
  static+shifted age=4` (cross-benchmark-validated).
- The next scientific question is NOT "what threshold" but "what
  temporal placement": see
  [temporal-coverage-metrics.md](temporal-coverage-metrics.md).
- Sticky-dynamic (phase 1.26) and projector-group completion (phase
  1.27) are the highest-leverage next mechanism tests.

## Related

- [pareto-reporting.md](pareto-reporting.md)
- [temporal-coverage-metrics.md](temporal-coverage-metrics.md)
- [feature-replay.md](feature-replay.md)
