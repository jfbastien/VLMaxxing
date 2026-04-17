# Publishability Status — 2026-04-17

One-file answer to "what can we actually claim, in what venue, with what
numbers, today." Kept in sync with [claim-matrix.md](claim-matrix.md) but
scoped narrower: reviewer-facing readiness and runtime-cost evidence.

## HN-style headline (honest version)

> **Training-free temporal routing on Qwen 2.5-VL-7B-4bit (MLX): matches
> 8-frame uniform-dense accuracy on MVBench motion holdout while using
> 56% of the fresh-frame budget (4.49 vs 8.0 effective fresh frames) —
> no training, no architecture change, one percentile pass + a bounded
> staleness counter.**

What we CANNOT yet honestly say in HN-headline form:

- "**N%** faster" — Track B sparse execution path is not written; only
  the dense wall-clock baseline has been captured (60.1 s/item median
  end-to-end at 8 frames). The projected ceiling on a vision-cache-only
  Track B speedup is **22% end-to-end** at this geometry (phase 1.50).
- "**N%** less energy" — no energy instrumentation. Projected proportional
  to wall-clock at fixed memory.
- "**N%** as accurate" — accuracy is equal (0.633=0.633 on MVBench
  dense-8 vs sticky4, clean tree) or marginally lower (0.333=0.333 on
  TOMATO dense-8 vs base, clean tree). No accuracy trade on the clean
  tree; the win is on the x-axis, not the y-axis.

**Honest one-liner for reviewers:** "matched-accuracy Pareto win at
reduced fresh-frame budget on two temporal-reasoning benchmarks at
N=30 holdout, clean-tree provenance; projected compute-savings ceiling
+22% end-to-end pending sparse-execution implementation."

## Publishable claim inventory (with concrete numbers)

### What is earned RIGHT NOW (can appear in paper body, not just discussion)

| # | Claim | Numbers (cite) | Evidence path |
|---|---|---|---|
| A | **Pareto win on MVBench motion holdout N=30 at matched accuracy.** | Planner 2.0 base `max_abs(8,32) static+shifted age=4` → 0.600 cached_accuracy @ 4.06 effective fresh frames, vs uniform dense-6 at 0.567 @ 6.0 (strict dominance: better accuracy at fewer fresh frames). | `phase1_21_mvbench_motion_holdout_v2_cached_nosticky/*_summary.json`; `paper/figures/pareto_holdout_n30.png` |
| B | **Pareto tie on TOMATO motion holdout N=30 at 44% of the fresh-frame budget.** | Planner 2.0 base → 0.333 cached_accuracy @ 3.55 effective fresh frames, equal to uniform dense-8 at 0.333 @ 8.0. | `phase1_20_tomato_motion_holdout_v2_cached_clean/*_summary.json` |
| C | **Sticky4 refinement matches dense-8 accuracy at 56% of budget on MVBench.** | Planner 2.0 + sticky_window=4 → 0.633 @ 4.49 vs uniform dense-8 at 0.633 @ 8.0. Strict Pareto equivalence at reduced fresh frames. | `phase1_21_mvbench_motion_holdout_v2_cached/*-sticky4_summary.json` |
| D | **Beats novelty-ranked dense on both benchmarks at matched fresh-frame count.** | Novelty-ranked dense N=8 on TOMATO: 0.233 (hurts uniform by 0.100). On MVBench: 0.567 (loses to uniform by 0.067, saturates at 0.567). Planner 2.0 cached DOMINATES every novelty cell at equal-or-lower fresh budget. | `results/novelty_ranked_dense/*_holdout_n{4,6,8}.json`; phase 1.34 note |
| E | **Bounded staleness is the mechanism on TOMATO; removing age=4 causes catastrophic novelty collapse.** | TOMATO Planner 2.0 no-age: novel_blocks→0, identical-feature reuse. With age=4: recovers proxy signal. Content-conditional finding. | phase 1.20 ablation cells (canonical note + registry) |
| F | **Pixel-diff proxy → ViT feature-change correlation is non-trivial but content-conditional.** | Phase 1.36 feature-change oracle: best pixel stat Pearson r=0.233 (TOMATO MEAN) to r=0.504 (MVBench CPF). Ranking is content-dependent; the best routing stat (MAX_ABS) is NOT the best point predictor. | `phase1_36_feature_change_oracle/*.json`; phase 1.36 note |
| G | **Dense wall-clock baseline captured on M3 Air 16GB.** | TOMATO n=10 mc_scoring at 8 frames, 560×560: 60.1 s/item median; prefill 72% of wall time, vision encode 22%, decode 6%; peak 6.87 GB. | `results/track_b/tomato_mc_n10.json`; phase 1.50 note |
| H | **Hard ceiling for vision-cache-only Track B: 22% end-to-end speedup at this geometry.** | Arithmetic: vision encode is 22% of per-item wall time, so any method that only skips vision work caps at 22% end-to-end before prefill savings. | Derived from G; explicit in phase 1.50 §Paper implications |

### What remains BLOCKED before venue submission

| # | Claim | Blocker | Runtime estimate |
|---|---|---|---|
| I | "Method delivers measured N% speedup" | Sparse-execution path does not exist. Track B measures dense; a sparse path must be written to measure the delta. | Implementation ≈ 1-2 weeks; per-run wall time ≈ 1 h for N=30 on each benchmark. |
| J | "Validated on VideoMME (de facto benchmark)" | Phase 1.41 loader written; N=30 run not launched. | ≈ 2 h GPU wall time for N=30 at 32 frames, assuming no OOM at 32 frames on M3 Air 16 GB (prefill O(F²) grows fast; predicted fit with careful activation streaming). |
| K | "Cross-architecture generalization (Qwen windowed ↔ Gemma/InternVL3 all-global)" | Second architecture has not been run locally. | ≈ 4-6 h GPU wall time for matched N=30 on a second 4-bit-quantized checkpoint, assuming it fits on M3 Air 16 GB. Not guaranteed: Gemma 4 SigLIP + LLM has a larger vision tower. |
| L | "Placement ablation (phase 1.38)" | Not run. | ≈ 30 min GPU wall time on a subset. |

## Evidence table with RUNTIME (not implementation) time

Runtime = GPU wall time to reproduce the cited number from a warm cache.
Implementation time is out of scope for this table.

| # | Claim | Cold-cache runtime | Warm-cache runtime | Hardware |
|---|---|---|---|---|
| A | MVBench motion holdout N=30 base | ≈ 90 min (includes feature extraction) | ≈ 25-30 min | M3 Air 16 GB, Qwen 2.5-VL-7B-4bit |
| B | TOMATO motion holdout N=30 base | ≈ 120 min (larger videos, longer decode) | ≈ 30-40 min | same |
| C | MVBench motion holdout N=30 sticky4 | ≈ 90 min | ≈ 25-30 min | same |
| D | Novelty-ranked dense 2×3 grid (TOMATO+MVBench, N={4,6,8}) | ≈ 120 min total | ≈ 45-60 min | same |
| E | TOMATO ablation cells (6 cells × 2 benchmarks × N=30) | ≈ 6-8 h | ≈ 3-4 h | same |
| F | Phase 1.36 oracle (per-block Pearson, partial cache coverage) | ≈ 60 min | ≈ 20 min | same |
| G | Phase 1.50 dense wall-clock baseline (TOMATO n=10) | ≈ 15 min | ≈ 12 min | same |
| H | Derived from G, zero runtime | — | — | — |

### Runtime cost summary

- **One full reviewer-response cycle (re-run A through F on clean tree):** warm-cache ≈ 5-7 h; cold-cache ≈ 10-14 h.
- **N=30 motion holdout pair on a new policy:** warm-cache ≈ 60 min; cold-cache ≈ 3.5 h.
- **Phase 1.50 Track B N=30 pair (currently running TOMATO, MVBench next):** cold-cache ≈ 2 h per benchmark.

## Venue targeting (current honest read)

| Venue | Fit today | What would need to land |
|---|---|---|
| **arXiv preprint** | **Ready now as positional submission.** Two clean-tree Pareto results + oracle + dense wall-clock. Framing must say "projected ceiling" for speedup. | Optional: close Codex round-13/14 cleanups (this session). |
| **NeurIPS / ICLR / CVPR efficiency workshop** | **Within reach.** Needs one of: Track B sparse delta OR VideoMME lane OR second-architecture result. | One of {I, J, K} landed. |
| **Main track (NeurIPS/ICML/CVPR)** | **NOT ready.** Single-architecture, two benchmarks, no measured speedup. Reviewers will flag all three. | At least two of {I, J, K} + placement ablation L. |
| **Systems conference (MLSys/OSDI)** | **NOT ready.** No sparse execution to characterize. | I landed at minimum; K strengthens. |

## What is safe to say in a one-paragraph abstract TODAY

> We study training-free temporal feature reuse for video VLMs on a
> Qwen 2.5-VL-7B-4bit MLX deployment, using a bounded-staleness,
> concentration-aware pixel-diff planner over spatial blocks. On the
> TOMATO motion holdout (N=30), our planner matches uniform-dense
> 8-frame accuracy (0.333) at 44% of the fresh-frame budget (3.55
> effective fresh frames). On the MVBench motion holdout (N=30), a
> sticky-window refinement matches uniform-dense 8-frame accuracy
> (0.633) at 56% of the fresh-frame budget (4.49 effective fresh
> frames), while the base policy strictly dominates uniform dense-6
> (0.600 > 0.567 at fewer fresh frames). A feature-change oracle
> (phase 1.36) establishes that pixel-diff statistics correlate with
> ViT feature change at Pearson r up to 0.504 on MVBench, and that
> the best routing statistic (MAX_ABS) is not the best point predictor
> — routing cares about ordering, not magnitude matching. We report
> a dense wall-clock baseline of 60.1 s/item on M3 Air 16 GB at
> 8 frames (prefill 72% of end-to-end), giving a 22% ceiling on any
> vision-cache-only Track B speedup before the prefill path is also
> compressed. Sparse-execution measurement is left as follow-up work.

## What is NOT safe to say today

- "SOTA" on any axis.
- "N% faster end-to-end" (no sparse path).
- "Generalizes across architectures" (single architecture).
- "Validated on VideoMME" (phase 1.41 not run).
- "Beats CodecSight / CoPE / FastV / VisionZip" (no head-to-head).
- "Training-free codec-guided" without qualifying "pixel-diff proxy
  for codec MV/CBF; phase 1.29 MV-only is the bridge."

## Immediate next actions to extend publishability (ranked)

1. **Phase 1.41 VideoMME N=30** — ≈ 2 h GPU wall time, unlocks claim J.
2. **Phase 1.38 placement ablation** — ≈ 30 min GPU wall time, strengthens mechanism claim.
3. **Phase 1.37 child-veto dev grid** — ≈ 2 h GPU wall time, unlocks claim 3 from claim-matrix.
4. **Phase 1.50 Track B N=30 pair (currently running)** — cold-cache ≈ 4 h, tightens variance bands on G.
5. **Track B sparse path** — weeks of engineering, the biggest single claim unlock.

Maintained by: research automation. Source of truth for numbers:
[`claim-matrix.md`](claim-matrix.md) and the artifact JSONs it cites.
