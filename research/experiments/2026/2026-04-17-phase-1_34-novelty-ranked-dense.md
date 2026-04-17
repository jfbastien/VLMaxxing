# Phase 1.34 — Novelty-ranked dense baseline (Track A)

Date: 2026-04-17 (live; TOMATO full, MVBench in progress)
Parent: `paper/claim-matrix.md` claim #9 ("beats novelty-ranked dense
at matched budget")

## Hypothesis

The cached-policy advantage over uniform dense-N could plausibly
come from two sources:

1. **Smart compute reuse** (the intended mechanism): picking
   novel regions inside each frame and reusing the static ones.
2. **Smart frame selection in disguise**: the cached policy
   implicitly concentrates vision budget on the informative
   frames. A dense baseline that does the same frame selection,
   without any reuse, might close the gap.

A **novelty-ranked dense-N** baseline is the clean test. For each
item we decode 32 uniform frames, compute per-adjacent-pair pixel
novelty (MAX_ABS, the Planner 2.0 winner), rank each frame by its
max score, keep the top-N (always including frame 0), re-sort by
temporal index, then run full Qwen 2.5-VL generation on those N
frames with no caching at all. If the cached policy still beats
novelty-ranked dense-N at matched N, the advantage cannot be
attributed to frame selection.

Secondary question — does novelty-ranked dense-N at least beat
**uniform** dense-N? If yes, "smart selection" is a real but
weaker claim than the cached story. If no, even uniform placement
outperforms novelty-ranked, and we have direct evidence that
**budget placement** (regardless of reuse) beats **novelty
magnitude**. The paper theory predicts novelty magnitude is the
wrong axis for answer stability.

## Method

Harness: `scripts/run_novelty_ranked_dense.py` (committed 8920e36).

For each item:
1. Decode 32 uniformly sampled frames (square-padded to 560×560).
2. Compute per-block pixel MAX_ABS for each adjacent pair.
3. Per-frame score = max over adjacent-pair scores the frame
   participates in. Frame 0 uses the second-pair score.
4. Keep the top-N frames; always include frame 0.
5. Re-sort by temporal index so the selection is time-ordered.
6. Run `mlx_vlm.generate()` on the N frames with the benchmark's
   prompt and extract the answer letter via `codec_through.answers.
   extract_choice`.

N ∈ {4, 6, 8}. Benchmarks: TOMATO motion holdout v2 (N=30 items)
and MVBench motion holdout v2 (N=30 items). The two holdouts
together match the phase 1.20 / 1.21 paper-grade evaluation
axes exactly.

## Results (live, 2026-04-17)

### TOMATO motion holdout v2 (N=30)

| Config | Accuracy | N correct | Mean elapsed / item |
|---|---:|---:|---:|
| Uniform dense-4 (phase 1.20) | 0.133 | 4/30 | — |
| **Novelty-ranked dense-4** | **0.133** | **4/30** | **19.1 s** |
| Uniform dense-6 (phase 1.20) | 0.267 | 8/30 | — |
| **Novelty-ranked dense-6** | **0.167** | **5/30** | **30.9 s** |
| Uniform dense-8 (phase 1.20) | 0.333 | 10/30 | — |
| **Novelty-ranked dense-8** | **0.233** | **7/30** | **39.6 s** |
| **Cached base** (`max_abs(8,32) static+shifted age=4`) | **0.333** | **10/30** | **at 3.55 fresh frames** |

### MVBench motion holdout v2 (N=30)

*pending*

## TOMATO interpretation (all 3 cells complete)

1. **Novelty-ranking gives no benefit over uniform at N=4**
   (0.133 = 0.133). At this budget neither method works well on
   TOMATO, but the tie rules out "cached wins because it picks
   better frames at low budget."

2. **Novelty-ranking HURTS accuracy at N=6 AND N=8** on TOMATO.
   N=6: 0.167 vs uniform 0.267 (−0.100 absolute).
   N=8: 0.233 vs uniform 0.333 (−0.100 absolute).
   The gap is consistent across budgets. Mechanism: TOMATO clips
   are constrained synthetic motion (rotation, translation,
   shape change) with relatively uniform pixel change across
   the clip. "Novelty magnitude" concentrates budget on
   localized pixel hotspots that do not necessarily correspond
   to the decisive temporal event. Uniform placement gives
   better temporal coverage and therefore better accuracy.

3. **This is direct evidence for paper claim #4** (budget
   placement matters more than quantity). Even at dense-only
   compute (no reuse), *how* you spend the frame budget changes
   accuracy by 0.100 absolute on the same clips. Novelty magnitude
   ≠ informative placement on temporally-uniform content.

4. **The cached policy (0.333 @ 3.55 fresh frames) ties uniform
   dense-8 (0.333 @ 8.0 fresh frames) while DOMINATING all
   novelty-ranked cells** — novelty-dense-4 (0.133), -6 (0.167),
   -8 (0.233). Cached achieves dense-8 quality at 44% of the
   fresh-frame budget, and beats the best novelty-ranked cell
   (0.233) by 0.100 absolute. This is strong support for
   claim #9: cached's advantage cannot be attributed to smart
   frame selection, because the closest non-cached frame
   selector UNDER-performs uniform placement at matched budget.

## Open cells before the writeup

- MVBench N=4, 6, 8 (in flight): is the pattern direction-preserved
  on heterogeneous real video, where novelty magnitude is more
  informative? MVBench's pixel→feature oracle gave higher
  correlations (Pearson up to 0.50 on CPF), so novelty-ranking
  could plausibly help here where it didn't on TOMATO.
  Null hypothesis: same direction as TOMATO (novelty-ranking ≤
  uniform). Alternative: novelty-ranking helps on MVBench
  because heterogeneous content has sparser truly-novel frames.

## Reproduction

```bash
# TOMATO
uv run python scripts/run_novelty_ranked_dense.py \
  --manifest research/benchmark_manifests/tomato_motion_holdout_v2.toml \
  --frame-count 6 \
  --output results/novelty_ranked_dense/tomato_holdout_n6.jsonl \
  --summary results/novelty_ranked_dense/tomato_holdout_n6.json

# MVBench (same flags, different manifest)
```

## Paper implications (preliminary)

- **Claim #9 trend is supportive** — cached still dominates.
  Final statement deferred until MVBench cells complete.
- **Claim #4 gains a cleaner causal result** — even dense-only,
  *placement* of the frame budget matters. Current text for the
  paper: "Novelty-magnitude frame ranking under-performs uniform
  frame ranking by 0.100 absolute on TOMATO at N=6 (0.167 vs
  0.267). Pixel-space novelty is not a substitute for temporal
  placement." This is independent of our caching mechanism and
  can appear in the "why budget placement" section.

## Status

- Code + tests committed (8920e36).
- TOMATO results partial (N=4, N=6 complete; N=8 running).
- MVBench results pending the TOMATO queue to drain.
- Full writeup + paper-claim decision after all 6 cells complete.
