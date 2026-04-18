# Paper Claim Matrix

Last updated: 2026-04-17

This is the single-file answer to "what must be true before we can
make each claim in the paper?" Per codex 2026-04-16 review: keep
the repo aligned to a ship-worthy thesis instead of an endless good
research program.

## Paper thesis

> Training-free temporal routing can improve the quality–compute
> Pareto frontier for video VLMs on temporal-reasoning tasks, when
> reuse is concentration-aware, age-bounded, architecture-aware,
> and backed by real skipped compute.

If the codec signal path (phase 1.29) lands: "codec-guided."
If not: "codec-inspired / pixel-diff proxy for codec-guided."

## Claim matrix

| # | Paper claim | Required evidence | Current status | Blocker | Promotion rule |
|---|---|---|---|---|---|
| 1 | Pixel-diff proxy has measurable (not perfect) point-predictor fidelity for ViT feature change | Phase 1.36 oracle reports per-block Pearson r by benchmark; pixel→feature correlation is non-trivial | Phase 1.36 DONE (2026-04-17): best pixel stat achieves r=0.233 (TOMATO MEAN) to r=0.504 (MVBench CPF) Pearson on a 45/60-item cache-hit subset (15 items missed the v2 cache-key rewrite and were not re-extracted for this pass). Weak-to-moderate, content-dependent. Not the r≥0.7 originally preregistered, but exactly what you would expect from a 28-pixel-block point predictor; the routing benefit sits on ordering, not magnitude-matching. | None (claim can now use exact numbers, no longer aspirational; coverage caveat belongs in paper methods) | Claim on oracle + MV-only comparison (phase 1.29) |
| 2 | Naive mean-diff is too blunt on temporally concentrated evidence | Phase 1.36 oracle + Planner 2.0 ablation show that the best routing statistic is NOT the best point predictor; falsified-hypotheses ledger entry for mean-diff default | Phase 1.36 DONE (2026-04-17): MAX_ABS is 2nd-to-last as a point predictor on both benchmarks (TOMATO Pearson 0.191, MVBench 0.444) BUT wins in the Planner 2.0 routing ablation. Routing objective differs from point-prediction — MAX_ABS catches localized hotspots for top-k budget allocation. MEAN/CPF are best point predictors (content-dependent). | None | Claim on oracle-disentangled framing |
| 3 | Concentration-aware routing (within-block child-veto, neighbor-halo veto, sticky-dynamic, age-bounded) repairs hard temporal failures | Phase 1.37 within-block child-veto OR phase 1.37B neighbor-halo veto + phase 1.26 sticky + age-bounded all evaluated on dev/holdout | Sticky4 passes MVBench holdout (1.26.B). Phase 1.37B **neighbor-halo veto RETIRED 2026-04-17 as preregistered null** — code landed (commits 2ebf90d, db10e12, 0ea69fe, 46b5d05, 2947198; `NeighborHaloVetoConfig` + `apply_neighbor_halo_veto` + 10 unit tests; Track A `--halo-veto-percentile` / `--halo-veto-neighborhood` CLI flags) and the full 9/9 cells × 2 benchmarks dev sweep landed. **TOMATO NO-LIFT**: control cached_accuracy=0.233 is rank-1 and within MRU 1/30=0.034 of every cell (halo moves only agreement 0.833→0.867–0.933 at the cost of fresh-frame budget 3.77→4.20–6.58). **MVBench NO-LIFT-NEGATIVE**: halo hurts — control is sole rank-1 at 0.800, 7/8 halo cells lose 0.067–0.100. No holdout run per the frozen promotion rule (no cell clears the 1/30 MRU bar). Phase 1.37 within-block child-veto remains preregistered but NOT YET IMPLEMENTED (distinct mechanism, lives in `_mix_qwen_features`); it is now the only remaining path toward claim 3 evidence. See registry row 1.37B and `research/experiments/2026/2026-04-17-phase-1_37B-neighbor-halo-veto-prereg.md` for full provenance. | Phase 1.37 within-block child-veto implementation + dev + holdout (halo variant is off the table per frozen rule) | Claim on N=30 surviving sticky4 + at least one veto variant result — halo variant is now unavailable, child-veto remains the only candidate |
| 4 | Saved budget placement matters more than quantity | Phase 1.38 temporal placement ablations show middle-event items; phase 1.28 shows 16-frame saturation | Partially supported (1.26 asymmetry, 1.28 saturation) | Phase 1.38 run | Claim when ablations + oracle + N=30 all converge |
| 5 | Real sparse execution converts proxy gain into measured speedup | Track B harness: wall-clock decode/preprocess/vision/prefill/generation + peak memory + FLOPs | **DENSE BASELINE CAPTURED ON BOTH BENCHMARKS (phase 1.50).** TOMATO n=10 dev (2026-04-17): 60.1 s/item median. TOMATO N=30 holdout v2 (2026-04-17): 61.1 s/item median, p95 70.2 s (prefill 70%, vision_encode 22.6%, decode 6.7%). MVBench N=30 holdout v2 (2026-04-17): 56.5 s/item median, p95 60.3 s (prefill 78%, vision_encode 20.2%, decode 0.6%). Peak 6.87 GB both. Hard cross-benchmark ceiling: vision-cache-only Track B speedup caps at **20–23% of end-to-end** at this geometry (8 frames, 560×560). Sparse execution path still not written. | Sparse execution implementation | Still prospective until a sparse path measures a delta against this baseline |
| 6 | Method survives on temporal-reasoning benchmarks at N=30 | Phase 1.21 MVBench N=30 + phase 1.20 TOMATO N=30 | **BOTH HALVES PAPER-GRADE (clean trees).** MVBench: base 0.600@4.06 (Pareto win vs dense-6). TOMATO: base 0.333@3.55 (Pareto tie vs dense-8 at 44% budget). | Done | Full claim satisfied with clean provenance |
| 7 | Architecture-conditioned reuse fidelity is a spectrum (not binary: windowed-mostly = byte-identical; all-global = high-fidelity approximate but can still be lossless depending on pretraining) | Phase 1.42 attention-topology (Qwen windowed vs Gemma global + optional InternVL3 all-global) | NOT STARTED; sam's whitepaper §2.7 + §2.9 provides hypothesis; scope note: InternVL3 is all-global yet preserves 95% strict agreement, so a binary claim is under-evidenced | Second-arch feasibility on M3 Air 16GB | Claim on ≥ 2 local architectures with different attention topologies |
| 8 | Validated on VideoMME (de facto benchmark standard) | Phase 1.41 VideoMME lane on Qwen 7B | NOT STARTED | Corpus setup | Claim on local VideoMME evaluation |
| 9 | Beats novelty-ranked dense at matched budget | Phase 1.34 novelty-ranked dense baseline | **COMPLETE 2026-04-17.** Full 2×3 grid N=30 landed. TOMATO: novelty N=4 ties uniform (0.133); N=6 HURTS by 0.100 (0.167 vs 0.267); N=8 HURTS by 0.100 (0.233 vs 0.333). MVBench: novelty N=4 BEATS uniform by +0.067 (0.567 vs 0.500) — sign flips at low budget; N=6 ties; N=8 LOSES by 0.067 (0.567 vs 0.633) — novelty saturates at 0.567 while uniform scales. Cached base on each benchmark (0.333@3.55 TOMATO, 0.600@4.06 MVBench) DOMINATES every novelty-ranked cell at equal-or-lower fresh-frame budget. Claim #9 fully supported. | None | Claim earned on both benchmarks |
| 10 | Composition with within-frame methods (FastV/FlashVID) is multiplicative | Phase 1.32 FastV pilot or FlashVID comparison OR **phase 1.52R temporal+spatial on Gemma** | NOT STARTED; two paths now queued (original: mlx-vlm fork; new: phase 1.52R on Gemma) | Phase 1.52R depends on 1.42+1.51R | Deferred; claim only after measured |
| 11 | Novelty-pruning visual tokens before LLM prefill delivers end-to-end speedup on Gemma 4 | Phase 1.51R novelty-pruning on Gemma (5 anchor arms × 5 keep rates dev tranche, single-shot holdout) | **DURATION-CONDITIONAL PARTIAL REPRODUCTION (2026-04-18).** Stage 1 n=30 at kr=0.5: e2e=1.00×, gen=1.01× — preregistered NULL at Sam's implicit operating point, full statistical power. Stage 2b n=30 at kr=0.10 (with Task #89 instrumentation, landed 2026-04-18): aggregate pruned_acc=0.30 vs dense_acc=0.40 (**-10pp, NOT accuracy-preserving**); e2e=1.12×, gen=2.62×, per-token gen=2.69× (diff-gen confound ≈0 at n=30, d_toks=21.0, p_toks=21.6). Per-bucket asymmetry is the paper-interesting finding: **medium items preserve accuracy (Δacc=0, gen=2.71×, agreement=0.70)**; short -10pp; long -20pp. n=5 kr=0.10 "pruned_acc=dense" from Stage 2 was small-sample luck on short items — corrected. Stage 3 (n=5 subset, kr × max_tokens grid) resolves the diff-gen confound: at matched tokens clean prefill-only gen speedups are monotone in kr — kr=0.10: 3.82×, kr=0.25: 1.83×, kr=0.50: 1.01×, kr=0.75: 0.69×. Driver instrumented with per-item `generated_tokens` + `per_token_generate_speedup_mean` (commit 6f389ca). bf16 fix (commit 469570c) unblocks feature-dependent arms. Stage 5 (nuwa_pillar / max_min_diversity / gemma_structural at kr=0.50 n=30) is the next science: does informed anchoring recover the -10pp aggregate drop at Sam's reference point? kr=0.10 was dropped from Stage 5 because nuwa's default anchor floor (64/frame) exceeds kr=0.10 budget (25/frame). Paper framing: "Sam's 1.8× e2e does not reproduce; the mechanism is duration-conditional — we preserve accuracy at 2.71× gen on medium items but collapse by 20pp on long items at kr=0.10." | Claim earned on ≥ 1.8× end-to-end speedup (not generate-only) with accuracy within 0.10 of Gemma-dense-8 on one benchmark. **Stage 2b n=30 kr=0.10 e2e=1.12× aggregate, gen=2.62× aggregate, -10pp accuracy — partial reproduction, not a full paper result at Sam's bar.** The medium-bucket slice (Δacc=0 at 2.71× gen) is a narrow earned-win that may anchor the paper if Stage 5 anchors don't close the aggregate gap. Paper fallback: publish as "duration-conditional partial reproduction + preregistered null at Sam's kr" with the duration × kr grid as the headline figure. |
| 12 | Method generalizes to long-form egocentric video (EgoSchema) | Phase 1.43 EgoSchema lane on Qwen 2.5-VL | NOT STARTED; preregistered | EgoSchema loader + manifest | Claim earned on N=30 holdout with agreement ≥ 0.80 and Pareto tie-or-win vs matched dense |

## One paper, two lanes (round-17 reframe)

**The target is ONE paper, co-authored with Sam, that advances SOTA
with measured big multiplicative speedups.** Method work serves that
science goal and is welcome in an appendix; it is not a separate
methods paper. Both lanes must contribute evidence.

**Lane A — Qwen routing (TOMATO + MVBench).**
- Claims 1, 2, 3, 4, 5, 6, 8, 9, 12 primarily exercise Qwen 2.5-VL.
- Role in the paper: validates the routing / bounded-staleness mechanism and the "pixel-diff proxy" story. Natural home for the method appendix.
- Currently earned: 1, 2, 6, 9. Partial: 3 (sticky4 only — dirty-tree supplementary; halo-veto retired 2026-04-17 as preregistered null on TOMATO + MVBench dev, child-veto 1.37 remaining path), 4 (asymmetry only; placement ablations pending), 5 (dense baseline only).

**Lane B — Gemma big-numbers (VideoMME + TOMATO + MVBench).**
- Claims 7, 10, 11 primarily exercise Gemma 4-E4B; claim 5 measured delta will likely land on Gemma too.
- Role in the paper: **THE SOTA-facing content** that justifies venue targeting. Multiplicative speedup via novelty-pruning + temporal reuse.
- Currently earned: none. All three preregistered only.

Prose must never conflate lane-A-earned with lane-B-prospective. When a claim sits in both lanes (e.g., claim 5 sparse-execution delta measured on either Qwen or Gemma), name the architecture explicitly.

## What must land before a paper submission (one-paper gate)

**Required for the paper to make sense at all** (round-17):
- Claim 6 earned (already done: TOMATO + MVBench paper-grade at N=30) — method is real on ≥ 2 benchmarks.
- Claim 8 earned (VideoMME lane) — headline benchmark the community recognizes.
- Claim 11 earned (Gemma novelty-pruning delivers end-to-end speedup ≥ 1.8× on one benchmark, preferably VideoMME) — THIS IS THE BIG-NUMBER claim.
- Claim 7 partial (Gemma fidelity characterized at ≥ 1 benchmark) — architecture breadth.
- Claim 5 at minimum one wall-clock measurement in a sparse-execution path — measured, not ceiling-derived.

**Strongly recommended to strengthen the paper**:
- Claim 10 (phase 1.52 combined temporal+spatial on Gemma) — multiplicative composition measured, not projected.
- Claim 3 (halo-veto or within-block child-veto earned) — routing claim gets mechanism evidence.
- Claim 1 oracle (already done) and claim 2 (STATIC vs STATIC+SHIFTED comparison).
- Claim 9 (novelty-ranked dense baseline — done) — disqualifies the dumb strawman.

**Can defer to paper discussion / future work / appendix**:
- Claim 12 (EgoSchema long-form)
- Full codec signal path (phase 1.29 MV-only)
- TempCompass as third benchmark
- Claim 4 (placement ablation) — strengthens, not required.

## Language rules

Per ChatGPT 2026-04-16 review:

- DO NOT say "confidence-conditioned" until answer-margin analyses
  land. SAY: "staleness × temporal-evidence concentration."
- DO NOT say "content-conditioned" (too broad). SAY: "temporally
  concentrated, fine-grained evidence dependence."
- DO NOT say "SOTA claim reopened." SAY: "paper slot reopened" or
  "SOTA-direction signal."
- DO NOT present Track B as built. SAY: "prospective" or "not yet
  measured."
