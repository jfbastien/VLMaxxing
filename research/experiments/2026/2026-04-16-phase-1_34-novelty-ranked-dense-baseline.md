# Phase 1.34: Novelty-Ranked Dense Baseline

## Preregistration

Objective:

- Add a stronger matched-budget dense baseline per the 2026-04-16
  audit: instead of uniform dense-N subsampling, pick the N "best"
  full frames using the same novelty signal (block-level
  `max_abs`) that our cached planner uses, then evaluate dense
  over those frames. Compare our cached policy against this
  stronger baseline at matched fresh-token-equivalent budget.
- If cached partial-regional refresh still wins over
  novelty-ranked full-frame spending, the result is much stronger
  than beating uniform dense-N.

Claim register targets:

- Paper claim 2 (naive mean-diff is too blunt): a stronger dense
  baseline reveals whether the cached advantage is from regional
  refresh or just from better frame selection.
- Paper claim 5 (real skipped compute): this is part of the fairer
  Pareto comparison the paper requires.

Reproduction mode:

- Baseline construction + matched-budget comparison. No new
  planner mechanism.

Track: A

Gating: runs any time; GPU-only work but small in scope (2 cells
per slice). Not competing with other phases.

Hypotheses:

- **H1 (novelty-ranking beats uniform)**: on TOMATO motion dev,
  dense over novelty-ranked {3, 4, 5} frames achieves higher
  accuracy than uniform dense-N at matched N.
- **H2 (cached still wins)**: our current cached winner
  (`max_abs(8,32) static+shifted age=4`) on 8 frames at fresh~3.4
  still matches or beats novelty-ranked dense-3 or dense-4.
- **H3 (method story is not just frame selection)**: if H1 and H2
  both hold, the cached policy's advantage is regional refresh,
  not frame selection. This is the paper claim we need.

Acceptance band:

- H1 passes: novelty-ranked dense-N accuracy ≥ uniform dense-N
  accuracy + 1/15 (N=15 granularity) on TOMATO motion dev at
  matched N ∈ {3, 4}.
- H2 passes: cached at fresh~3.4 accuracy ≥ novelty-ranked dense-4
  accuracy.

Rejection band:

- Novelty-ranked dense ≥ cached at matched budget: cached has no
  advantage beyond smart frame selection. This would be a
  significant weakening of the paper claim.

Inconclusive: N=15 CIs overlap; retest at N=30 via phase 1.20/1.21.

## Implementation sketch

New script `scripts/frame_budget_novelty_ranked.py`:

- Load manifest items.
- For each item, decode all frames + compute per-pair `max_abs`.
- Rank frames by their max-abs novelty score to the previous
  frame; keep the top-K novelty frames plus frame 0 (always keep
  frame 0 as reference).
- Run `run_benchmark_track_a.py` at `frame_count=K` on those ranked
  indices (needs a new `--frame-indices` override flag or a
  manifest-level override).

Runtime: 2 slices × 3 frame counts × ~12 min ≈ 1.2 hrs GPU.

Alternate simpler implementation path: pre-compute ranked-index
lists, write them to a small `indices.json` per item, then have the
runner read them. This avoids touching the main runner CLI.

## Execution

Pending code work (est. ~3 hrs for the novelty-ranking + frame
override path).

## Result

Pending.

## Interpretation

Pending.

## Links

- Pre-release CodecSight strategy notes are preserved in git history; current
  release-facing positioning is in [paper/framing.md](../../../paper/framing.md)
  and [docs/related-work-table.md](../../../docs/related-work-table.md).
- [phase 1.12 holdout evaluation](2026-04-14-phase-1_12-grid-winners-holdout.md)
- ChatGPT 2026-04-16 audit recommendation.
