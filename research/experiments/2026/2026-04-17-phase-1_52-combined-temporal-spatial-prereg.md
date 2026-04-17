# Phase 1.52 — Combined temporal+spatial pipeline (multiplicative-or-additive test)

Date: 2026-04-17
State: blocked (preregistered; depends on phase 1.42 Gemma integration AND phase 1.51 novelty-pruning winner cell)
Parent: `paper/claim-matrix.md` claim #10 (composition with within-
frame methods is multiplicative)
Depends on: phase 1.42 (Gemma integration), phase 1.51 (novelty-
pruning winner cell); both must pass their preregistered gates
first.

## Motivation

Phase 1.50 measured the vision-cache-only (temporal reuse) ceiling
at **20-23 % end-to-end** on M3 Air at 8-frame × 560 × 560
geometry because **prefill is 70-78 % of per-item wall time**.
Phase 1.51 is hypothesized to deliver 50-80 % end-to-end speedup
on Gemma via visual-token pruning before LLM prefill.

The paper's SOTA story requires both axes to stack meaningfully.
This phase is the **direct empirical test** of whether they do.

Three possible outcomes:

1. **Multiplicative** (claim #10 accepted): combined speedup ≈
   (1 + temporal) × (1 + pruning) − 1. E.g., 0.22 temporal × 0.70
   pruning → 1.22 × 1.70 − 1 = 1.07 → **107 % end-to-end
   speedup** (≈ 2× wall-clock). This is the "big numbers" story.
2. **Additive** (claim #10 narrowed): combined speedup ≈ temporal
   + pruning. 0.22 + 0.70 = 0.92 → **92 % speedup**. Still
   meaningful but not a composition win.
3. **Sub-additive** (claim #10 rejected): the two mechanisms
   interfere. Most common reason would be: novelty-pruning removes
   the visual-token positions that temporal reuse would otherwise
   cache-hit on, so the temporal cache hit-rate collapses under
   pruning and the claimed ~22 % temporal contribution vanishes.

Which outcome holds depends on whether temporal reuse and novelty-
pruning operate on **independent** vs **overlapping** axes. Our
prior is weakly multiplicative because:

- Temporal reuse acts on the *time* axis (inter-frame redundancy).
- Novelty-pruning acts on the *space* axis (intra-frame redundancy).
- The orthogonality is tempered by the observation that novel
  regions are also the regions the temporal planner tends NOT to
  reuse; there may be positive correlation between "what pruning
  drops" and "what temporal keeps fresh," which could reduce the
  combined benefit.

## Hypothesis

H1 (multiplicative): On Gemma 4 at the winning keep-rate cell from
phase 1.51, combined pipeline end-to-end speedup ≥ 0.8 ×
(temporal_speedup × pruning_speedup) on TOMATO motion holdout N=30
and MVBench motion holdout N=30. The 0.8× slack acknowledges
non-perfect compositionality (some overhead from running both
mechanisms).

H2 (accuracy preservation): Combined cached accuracy is within
0.15 of Gemma-dense-8 at 8 frames. This is looser than the
individual 0.10 thresholds because two lossy mechanisms stack.

H3 (independent mechanisms): Removing either mechanism from the
combined pipeline returns accuracy to approximately the single-
mechanism accuracy (± 0.03). Falsification means the two
mechanisms interact: e.g., pruning masks the accuracy drop from
temporal staleness, so removing pruning exposes a larger drop.

## Method

**Phase A — composition harness:**

1. Extend `_mix_gemma_features` (from phase 1.42) to also apply
   the phase-1.51 novelty-pruning anchor strategy before the LLM
   receives its visual prefix. Order matters: apply temporal reuse
   first (producing mixed features with some stale entries), then
   apply novelty-pruning to the resulting visual sequence.
2. Record per-stage timings: vision-encode, temporal-mix, novelty-
   prune, LLM-prefill, LLM-decode. This is necessary to decompose
   the combined speedup factor.

**Phase B — single-shot paper-grade test:**

Run 4 cells on both TOMATO and MVBench motion holdout N=30:

| Cell | Temporal reuse | Novelty-pruning | Purpose |
|---|---|---|---|
| `dense` | off | off | baseline (dense-8 Gemma) |
| `temporal` | on (Planner 2.0 MAX_ABS age=4) | off | temporal-only reference |
| `prune` | off | on (phase 1.51 winner) | pruning-only reference |
| `combined` | on | on | the composition test |

Metrics per cell: cached_accuracy, effective_fresh_frames,
end-to-end wall-clock, prefill seconds, vision-encode seconds,
peak memory, prefill token count.

**Phase C — interaction probe:**

If H1 is rejected (sub-additive), run a 2×2 ablation:

- Temporal with / without novelty-pruning
- Novelty-pruning with anchor / without anchor

And measure which interaction dominates. This decomposes whether
the interference is at the routing layer (temporal decides what
to reuse) or at the pruning layer (pruning decides what to keep).

## Accept / reject gates (preregistered)

- **Multiplicative composition (accept):** combined speedup on at
  least one benchmark ≥ 0.8 × (temporal × pruning speedup product)
  AND combined accuracy within 0.15 of dense-8. This earns claim
  #10 a measured entry. **Paper-table headline number** comes
  from this cell.
- **Additive composition (narrow claim):** combined speedup ≥
  (temporal + pruning) − 0.10 AND within-accuracy. The paper
  reports additive composition, not multiplicative, and drops the
  strong form of claim #10.
- **Interference (reject):** combined speedup < max(temporal,
  pruning). The paper reports this as a limitation; the two
  mechanisms do not stack. Claim #10 is replaced by a negative
  result table entry.

## Runtime estimate

Wall-clock only, excluding Phase A implementation:

| Stage | Duration estimate |
|---|---|
| Phase A smoke run (single-item 4-cell fwd) | 10 min |
| Phase B TOMATO 4 cells × N=30 × ~15 s/item (Gemma + pruning) | ~30 min |
| Phase B MVBench 4 cells × N=30 × ~15 s/item | ~30 min |
| Track B wall-clock decomposition (10 items, per-stage breakdown) | ~20 min |
| Phase C interaction probe (conditional on H1 rejection) | +1 hr |
| **Total if H1 accepted** | **~90 min** |
| **Total with Phase C** | **~150 min** |

## Paper-grade artifacts (expected)

- `research/experiments/2026/artifacts/phase1_52_gemma_tomato_combined_v2/*.json`
  (4 cells × N=30)
- `research/experiments/2026/artifacts/phase1_52_gemma_mvbench_combined_v2/*.json`
  (4 cells × N=30)
- `results/track_b/gemma_combined_tomato_n30.json` (per-stage breakdown)
- `results/track_b/gemma_combined_mvbench_n30.json`

## Status

- 2026-04-17: preregistered. Blocked on phase 1.42 pass and phase
  1.51 pass. This is the terminal phase of the "big numbers" arc.

## Why this phase exists

If phase 1.51 delivers its hypothesized 1.8× pruning speedup in
isolation but phase 1.52 shows combined ≤ 1.0× (interference),
the paper's "big numbers" story collapses — isolated improvements
don't stack. Preregistering the multiplicative vs additive vs
interference gates here forces us to publish an honest composition
number rather than cherry-picking the best single-mechanism cell.

## Composable axes beyond this phase (future work)

- **PoRe** (arxiv 2508.17807): position-reweighting as a third
  composable axis. Orthogonal to both temporal reuse and token-
  drop. Reserved for phase 1.53 if 1.52 passes.
- **FastV-style layer-2 threshold**: composes cleanly with phase
  1.51's input-layer pruning; would need a separate prereg.
- **Iso-budget comparison**: all combined-pipeline cells must
  also be compared at equal effective_fresh_frames or equal
  kept_token_count, per phase 1.28 protocol.
