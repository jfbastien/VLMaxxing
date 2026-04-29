---
date: 2026-04-27
phase: 1.30AG
status: preregistered; conditional
aliases:
  - Claude-proposed 1.30AE K-cache distance probe
---

# Phase 1.30AG — K-Cache Distance Probe (CONDITIONAL PREREG)

## Naming Note

Claude suggested `1.30AE` for this probe, but `1.30AE` already denotes the
duration-conditioned union candidate that was correctly skipped after 1.30AB
failed. This prereg uses the next free identifier, `1.30AG`.

## Launch Condition

Run this only if 1.30AF feature attribution is diffuse: no clear concentration
by duration, q-index, cold correctness, or 1.65 dense-margin strata explains why
1.30AC and 1.30AD land at the same aggregate accuracy delta through different
row-level flip sets.

## Question

Do 1.30AC cache invalidation with active follow-up V-pruning and 1.30AD
cache-reuse follow-ups reach the same aggregate loss because both move the
effective follow-up K-cache a comparable distance away from the dense reference
cache?

## Hypothesis

The equal aggregate loss is a cache-state saturation effect. Different
mechanisms perturb different rows, but both policies push follow-up cache state
past a similar distance threshold from the dense reference, so aggregate
accuracy lands at the same boundary.

## Protocol

- Select a deterministic 20-follow-up-row subset from the 1.30AD/1.30AC
  paired artifacts, stratified by:
  - shared drift rows
  - cache-reuse-only drift rows
  - cache-invalidated-only drift rows
  - stable rows
- For each selected session, capture post-Q0 cache tensors for:
  - dense reference
  - 1.30AD cache-reuse path
  - 1.30AC cache-invalidated V-pruned path
- Compute layer-wise cosine distance to the dense reference cache for K and V
  tensors separately, using each cache entry's valid `offset` window rather than
  the padded backing buffer.
- Report cache-token length parity. If a policy changes the valid K/V cache
  length relative to the dense reference, the probe may still emit diagnostic
  common-prefix distances, but the saturation gate fails because full-cache
  cosine distances are no longer physically comparable.
- Join cache-distance summaries to row-level follow-up drift outcomes.

## Gates

- H1-capture: all three cache states captured for >=20 unique follow-up rows without
  non-token shape mismatch, and all valid K/V cache windows have the same token
  length as the dense reference.
- H2-distance-report: layer-wise K and V cosine distances reported for both
  policies.
- H3-outcome-link: report distance distributions for stable, shared-drift,
  reuse-only-drift, and invalidated-only-drift rows.
- H4-saturation-test: if both policies' aggregate cosine distances
  (`1 - cosine`) are within 10% of each other while their row drift sets remain
  non-identical, mark the saturation hypothesis as supported. If not, mark it
  as unresolved.

## Interpretation

If H4 supports saturation, the paper can explain the 1.30 boundary as a
cache-state distance threshold: different perturbations, similar distance from
dense, same aggregate loss. If H4 fails, the paper should not invent a stronger
mechanism; it should report the equal aggregate as an empirical boundary and
defer tensor-level causality.

## Runtime And Resources

Estimated runtime: ~2 h on the local 16 GB laptop if implemented against the
existing 1.30 runner/cache hooks. This is not in the default deep-mechanism queue
because it should only run if 1.30AF is diffuse.
