# Phase 1.30AF — Cache-Boundary Attribution (PREREG)

## Naming Note

Claude suggested the name `1.30AE` for a K-cache distance probe, but `1.30AE`
already exists in this repo as the duration-conditioned union candidate that was
correctly skipped after 1.30AB failed. This phase uses the next free identifier:
`1.30AF`.

## Question

1.30AC (cache invalidation with active follow-up V-pruning) and 1.30AD
(instrumented cache reuse) landed at essentially the same net aggregate accuracy
drop. Is that row-identical behavior, or do different row-level failures happen
to land at the same aggregate boundary?

## Inputs

- `phase1_30AD_instrumented_w_rerun/paired_queries.jsonl`
- `phase1_30AD_instrumented_w_rerun/streaming_q0_dense_cache_reuse_followups.jsonl`
- `phase1_30AC_cache_invalidated_followups/paired_queries.jsonl`
- `phase1_30AC_cache_invalidated_followups/streaming_cache_invalidated_followups.jsonl`

## Gates

- H1-complete-overlap: common paired row count >= 171.
- H2-same-net: absolute aggregate accuracy-delta gap <= 0.005.
- H3-mechanism-contrast: cache-reuse follow-up active fraction < 0.10 and
  cache-invalidated follow-up active fraction > 0.90.
- H4-row-nonidentity: any-drift row sets are not identical.

## Interpretation

If H2/H4 both hold, the paper should say "same aggregate boundary loss,
different row-level flip sets," not "byte-equivalent." This phase is a post-hoc
attribution over existing artifacts, not direct KV tensor-distance measurement.
A true tensor-distance probe remains future work if the row-level attribution is
insufficient for reviewers.
