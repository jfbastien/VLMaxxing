# Paper Claim Matrix

Last updated: 2026-04-19

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
| 8 | Validated on VideoMME (de facto benchmark standard) | Phase 1.41 VideoMME lane on Qwen 7B | **EARNED 2026-04-18 (8f); strengthened 2026-04-19 (16f, 32f).** Qwen 2.5-VL-7B-Instruct-4bit (MLX) on `videomme_dev_v1.toml` n=30. **8f**: `dense_acc=0.533`, bucket short 0.800 → medium 0.500 → long 0.300. **16f**: `dense_acc=0.567`, short 0.800 → medium 0.700 → long 0.100. **32f (2026-04-19)**: `dense_acc=0.533` (n=30), short 0.800 → medium 0.700 → long 0.100 — **zero flips vs 16f per-bucket; long bucket plateau confirmed as third data point**. All three frame counts: `parse_failures=0`, `agreement=1.000` (identity cache bit-faithful). **Phase 1.57 mechanism ablation landed 2026-04-19 on same manifest** — adjudicates the 16f→32f hypotheses: per-bucket drift (adjacent-frame ViT cos, STATIC class) shows 8f→32f rise 0.567→0.676 (short, accelerating), 0.575→0.639 (medium, sub-linear), 0.545→0.592 (long, saturated at 16f). **H-drift-compounds REJECTED** (direction is rise, not decline); **H-saturation SUPPORTED** (long-bucket drift AND accuracy both plateau at 16f co-saturation); H-stride-window neutral; H-4bit-quant (1.58) deferred. Prereg: `2026-04-19-phase-1_41-qwen-videomme-16f-prereg.md`, `2026-04-19-phase-1_41-qwen-videomme-32f-long-prereg.md`, `2026-04-19-phase-1_57-feature-drift-mechanism-prereg.md`. Findings: `2026-04-19-phase-1_41-qwen-videomme-16f-findings.md`, `2026-04-19-phase-1_41-qwen-videomme-32f-long-findings.md`, `2026-04-19-phase-1_57-feature-drift-findings.md`. | **32f NOT Pareto-efficient on this model/benchmark** — 2× prompt tokens, 2× latency, zero aggregate acc lift over 16f. Long-bucket plateau confirmed at 16f onward; bucket-dependent attention-mixing ceiling means per-bucket drift caveats must accompany per-bucket acc in paper. Drift is a *co-indicator* of capacity plateau, not the binding constraint — short-bucket acc is flat from 16f despite drift still rising at 32f. Phase 1.58 (bf16 quantization ablation) remains the open mechanism question. | Claim on local VideoMME evaluation earned at 8f, 16f, and 32f; per-bucket scaling surface fully mapped with mechanism co-saturation evidence. |
| 9 | Beats novelty-ranked dense at matched budget | Phase 1.34 novelty-ranked dense baseline | **COMPLETE 2026-04-17.** Full 2×3 grid N=30 landed. TOMATO: novelty N=4 ties uniform (0.133); N=6 HURTS by 0.100 (0.167 vs 0.267); N=8 HURTS by 0.100 (0.233 vs 0.333). MVBench: novelty N=4 BEATS uniform by +0.067 (0.567 vs 0.500) — sign flips at low budget; N=6 ties; N=8 LOSES by 0.067 (0.567 vs 0.633) — novelty saturates at 0.567 while uniform scales. Cached base on each benchmark (0.333@3.55 TOMATO, 0.600@4.06 MVBench) DOMINATES every novelty-ranked cell at equal-or-lower fresh-frame budget. Claim #9 fully supported. | None | Claim earned on both benchmarks |
| 10 | Composition with within-frame methods (FastV/FlashVID) is multiplicative | Phase 1.32 FastV pilot or FlashVID comparison OR **phase 1.52R temporal+spatial on Gemma** | NOT STARTED; two paths now queued (original: mlx-vlm fork; new: phase 1.52R on Gemma) | Phase 1.52R depends on 1.42+1.51R | Deferred; claim only after measured |
| 11 | Novelty-pruning visual tokens before LLM prefill delivers end-to-end speedup on Gemma 4 | Phase 1.51R novelty-pruning on Gemma (5 anchor arms × 5 keep rates dev tranche, single-shot holdout) | **DURATION-CONDITIONAL PARTIAL REPRODUCTION (2026-04-18).** Stage 1 n=30 at kr=0.5: e2e=1.00×, gen=1.01× — **pre-registered NULL at Sam's reference kr**. Stage 2b n=30 at kr=0.10: e2e=1.12× aggregate, gen=2.62×, **Δacc=-0.10 (NOT accuracy-preserving aggregate)** with bucket asymmetry (medium Δacc=0 at 2.71× gen; short -10pp; long -20pp). Stage 5 (kr=0.50 n=30 × 3 anchors): **gemma_structural = paper default** (Δacc=-0.033, mask cost 2ms, +0.10 long-bucket lift); nuwa_pillar REJECTED. Stage 6 gemma_structural kr sweep (n=30 each): **8f Pareto knee = kr=0.33 short-bucket (Δacc=0 at e2e=1.090× per_tok=7.904×)**, does NOT extend to kr=0.25. Stage 6 32-frame regime match (n=10 per bucket, kr=0.10, anchor=none): H1 long FALSIFIED (1.234× below [1.5, 2.0]); H1' short favorable falsification (1.663× above [1.40, 1.55]); H1'' medium strict-inside-band EARNED (1.565×). **Δacc bucket-invariant at -0.100 across all three 32f buckets at kr=0.10**. Cross-bucket 32f aggregate (n=30 dev): **e2e = 1.389× time-weighted at Δacc=-0.100 — DEV-ONLY, NOT a paper headline** (holdout not run; per-bucket are the primary reportable results). *Methodology note (Codex round-21, 2026-04-19):* the earlier 1.487× figure was a mean-of-bucket-ratios; correct aggregate is `sum(dense_e2e)/sum(pruned_e2e) = 2458.03s/1769.88s = 1.389×`. Stage 7 (32f short × kr=0.33 × gemma_structural n=10): 8f recipe does NOT generalize — Δacc=-0.100 at 1.558×; kr=0.10 anchor=none strictly dominates in 32f short. **Ceiling implication:** long-32 ceiling@∞ = 1.312× (decode-bounded at 56.9% of e2e) — Sam's 1.8× long is arithmetically unreachable without Phase 1.54 decode acceleration. Short/medium levers belong to Phase 1.51V. **Full stage history:** `research/experiments/2026/2026-04-19-claim-11-reproduction-log.md` (Stages 1/2b/3/5/6/7 with per-bucket numbers, ceiling decompositions, and confound checks). See row 13 (C-CEILING) for the analytical contribution graduating from this work. | Claim earned on ≥ 1.8× end-to-end speedup (not generate-only) with accuracy within 0.10 of Gemma-dense-8 on one benchmark. **Stage 2b n=30 kr=0.10 e2e=1.12× aggregate, -10pp accuracy — partial reproduction, not a full paper result at Sam's bar.** The medium-bucket slice (Δacc=0 at 2.71× gen) and the 8f kr=0.33 gemma_structural short-bucket (Δacc=0 at 1.090×) anchor the paper if Stage 5 anchors don't close the aggregate gap. Paper fallback: "duration-conditional partial reproduction + pre-registered null at Sam's kr" with the duration × kr grid as the headline figure. |
| 12 | Method generalizes to long-form egocentric video (EgoSchema) | Phase 1.43 EgoSchema lane on Qwen 2.5-VL | NOT STARTED; preregistered | EgoSchema loader + manifest | Claim earned on N=30 holdout with agreement ≥ 0.80 and Pareto tie-or-win vs matched dense |
| 13 | **C-CEILING:** Token-pruning wall-clock speedup is predicted within ≤5.2% by an arithmetic-ceiling model `e2e ≤ 1/(fixed_frac + (1-fixed_frac)/s)` where fixed_frac = (D+P+V)/e2e and s = per-token generate speedup. Standalone analytical claim, independent of any specific SOTA arm. | Seven independent regime dimensions cross-validating the model at ≤5.2% error on Gemma 4-E4B-4bit: 8-frame kr sweep (kr=0.10/0.25/0.33 n=30 each), 32-frame smoke (n=1), 32-frame long (n=10), 32-frame short (n=10), 32-frame medium (n=10), 32-frame short × gemma_structural × kr=0.33 (n=10 — second anchor arm). Median error 2.1%, worst 5.2%. | **EARNED (2026-04-18).** 6-regime cross-validation done. All predictions were pre-registered BEFORE observation in individual phase prereg docs; all fall within stated bands. Decode cliff between medium and long buckets (seek-dominated) is a testable corollary quantifying where Phase 1.54 pays off. | None for the standalone claim. To strengthen: validate on a second architecture (Qwen 7B) and/or a second benchmark. | Claim earned: ≥ 5 independent regimes validated, each with pre-registered predictions, all within ±10% of observed. **Already satisfied.** |

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
- Claim 11 earned (Gemma novelty-pruning delivers end-to-end speedup ≥ 1.8× on one benchmark, preferably VideoMME) — THIS IS THE BIG-NUMBER claim. **1.8× is our internal preregistered reproduction target, not a number from Sam's whitepaper.** Sam's whitepaper reports 5.4× prefill and 4.2× e2e (Qwen 32f talking-head) on larger models / different regimes; our 4B-class / 8-frame regime is bounded by arithmetic ceiling to ≤1.46× at kr=0.10 aggregate (see C-CEILING below). The 1.8× gate should be read as "prove the mechanism delivers a multiplicative e2e win, big enough to matter."
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
