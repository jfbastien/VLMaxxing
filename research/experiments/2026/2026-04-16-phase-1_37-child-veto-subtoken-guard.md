# Phase 1.37: Child-Veto / Subtoken Guard

## Preregistration

Objective:

- add a 2×2 child-level guard inside each 28×28 merged-token block.
  Divide each block into four 14×14 children. Compute a
  **non-max-aggregation statistic** (MEAN or CPF) per child. **Veto
  reuse of the entire merged token if ANY child exceeds a threshold.**

**RESCOPED 2026-04-16 per codex audit**: the original prereg said
"MAX_ABS or CPF per child." Codex correctly identified that
`ANY(child_max_abs > t) ≡ block_max_abs > t` — child-level MAX_ABS
is mathematically identical to block-level MAX_ABS, so it adds
nothing. The mechanism only works with a statistic where the
child-level aggregation differs from the block-level aggregation:

- **Child MEAN**: block-mean can be low even if one child has high
  mean (diluted by the other 3 static children). Child-mean catches
  this: if one child's mean > t, veto. This IS different from
  block-mean because block-mean averages over 4× more pixels.
- **Child CPF**: similarly, block CPF counts changed pixels over the
  entire block, diluting spatially concentrated changes. Child CPF
  catches a 14×14 region where many pixels changed even if the
  block-wide fraction is low.

So the operative statistic for child-veto is `{MEAN, CPF}`, NOT
`{MAX_ABS, TOP_K_MEAN}` (which are already spatially sensitive at
the block level).

- this directly targets the failure mode identified across phases
  1.10–1.26: small, spatially sparse, semantically critical evidence
  inside a mostly-static 28×28 block.
- per ChatGPT 2026-04-16 review: child-veto is "the highest-value
  overlooked near-term unlock."

Claim register targets:

- Paper claim 2 (naive mean-diff is too blunt): child-veto is a
  strictly more sensitive routing oracle.
- Paper claim 3 (concentration-aware routing repairs hard temporal
  failures).

Reproduction mode:

- method-development; new mechanism. Training-free.

Track: A

Gating: runs after phase 1.36 feature-change oracle clarifies
whether signal quality or schedule quality is the bottleneck. If
signal quality is good (oracle confirms MAX_ABS r ≥ 0.7), child-veto
may not add much and schedule improvements (sticky, age) are more
leveraged. If signal quality is the bottleneck (r < 0.5), child-veto
is the most immediate fix.

Hypotheses:

- **H1 (TOMATO direction recovery)**: child-veto with `max_abs`
  per-child at threshold ~16 (half of block-level 32) recovers the
  TOMATO direction item that vanilla `max_abs(8,32) age=4` misses
  on dev, because the direction cue is spatially concentrated in 1
  of the 4 children.
- **H2 (MVBench improvement)**: child-veto on MVBench motion holdout
  at N=15 reaches cached ≥ 0.733 (matching sticky4's result) at
  lower budget than sticky4 (fresh < 5.10).
- **H3 (budget cost bounded)**: child-veto adds ≤ 0.5 effective
  fresh frames compared to block-level-only routing, because only
  blocks with spatially heterogeneous content trigger the veto.

Acceptance band:

- H1: TOMATO dev cached_accuracy increases from 0.400 to ≥ 0.467
  (at least 1 extra correct item).
- H2: MVBench holdout cached_accuracy ≥ 0.667 at fresh ≤ 5.10.
- H3: extra budget ≤ 0.5 fresh frames.

Rejection band:

- H1: no accuracy change or regression.
- H2: child-veto gives same or worse accuracy than sticky4.
- H3: budget explodes (> 1 full extra fresh frame) — child-veto
  is too aggressive and needs thresholding.

## Code change

In `scripts/run_benchmark_track_a.py::_mix_qwen_features`, after
computing `reuse_mask` from `flattened_reuse_mask(classification)`:

1. Reshape the frame pair's pixel diff to (H_blocks, W_blocks,
   block_size, block_size) = (20, 20, 28, 28).
2. Reshape each block to (2, 14, 2, 14) children.
3. Compute per-child MAX_ABS (or CPF).
4. If any child exceeds threshold, set `reuse_mask[block] = False`.
5. Proceed with existing age-gate and sticky logic.

Add `--child-veto-threshold` CLI flag (default None = off).
Add `child_veto_threshold` to `PolicyCandidate` and `_planner_payload`.

~30 lines of code change in the mask construction path.

Also update `planner_grid_search.py` calibration to optionally
include child-veto in the calibrated reuse estimate.

## Execution

Pending phase 1.36 oracle outcome (clarifies priority). If oracle
says signal quality is the bottleneck (r < 0.5), child-veto jumps
to #1. If oracle says signal is good (r ≥ 0.7), child-veto is
useful but lower-priority than schedule improvements.

## Result

Pending.

## Interpretation

Pending.

## Links

- ChatGPT 2026-04-16 review: "child-veto / subtoken guard"
- [phase 1.36 feature-change oracle](2026-04-16-phase-1_36-feature-change-oracle.md)
- [docs/methodology/temporal-coverage-metrics.md](../../../docs/methodology/temporal-coverage-metrics.md)
