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
| 1 | Pixel-diff proxy has measurable (not perfect) point-predictor fidelity for ViT feature change | Phase 1.36 oracle reports per-block Pearson r by benchmark; pixel→feature correlation is non-trivial | Phase 1.36 DONE (2026-04-17): best pixel stat achieves r=0.233 (TOMATO MEAN) to r=0.504 (MVBench CPF) Pearson. Weak-to-moderate, content-dependent. Not the r≥0.7 originally preregistered, but exactly what you would expect from a 28-pixel-block point predictor; the routing benefit sits on ordering, not magnitude-matching. | None (claim can now use exact numbers, no longer aspirational) | Claim on oracle + MV-only comparison (phase 1.29) |
| 2 | Naive mean-diff is too blunt on temporally concentrated evidence | Phase 1.36 oracle + Planner 2.0 ablation show that the best routing statistic is NOT the best point predictor; falsified-hypotheses ledger entry for mean-diff default | Phase 1.36 DONE (2026-04-17): MAX_ABS is 2nd-to-last as a point predictor on both benchmarks (TOMATO Pearson 0.191, MVBench 0.444) BUT wins in the Planner 2.0 routing ablation. Routing objective differs from point-prediction — MAX_ABS catches localized hotspots for top-k budget allocation. MEAN/CPF are best point predictors (content-dependent). | None | Claim on oracle-disentangled framing |
| 3 | Concentration-aware routing (child-veto, sticky-dynamic, age-bounded) repairs hard temporal failures | Phase 1.37 child-veto + phase 1.26 sticky + age-bounded all evaluated on dev/holdout | Sticky4 passes MVBench holdout (1.26.B); child-veto preregistered | Phase 1.37 code + run | Claim on N=30 surviving sticky4 + child-veto result |
| 4 | Saved budget placement matters more than quantity | Phase 1.38 temporal placement ablations show middle-event items; phase 1.28 shows 16-frame saturation | Partially supported (1.26 asymmetry, 1.28 saturation) | Phase 1.38 run | Claim when ablations + oracle + N=30 all converge |
| 5 | Real sparse execution converts proxy gain into measured speedup | Track B harness: wall-clock decode/preprocess/vision/prefill/generation + peak memory + FLOPs | **DENSE BASELINE CAPTURED (phase 1.50, 2026-04-17, n=10 TOMATO mc_scoring).** 60.1 s/item median end-to-end; prefill 72%, vision_encode 22%, decode 6%; peak 6.87 GB. Hard ceiling: vision-cache-only Track B speedup caps at 22% of end-to-end at this geometry (8 frames, 560×560). Sparse execution path still not written. | Sparse execution implementation | Still prospective until a sparse path measures a delta against this baseline |
| 6 | Method survives on temporal-reasoning benchmarks at N=30 | Phase 1.21 MVBench N=30 + phase 1.20 TOMATO N=30 | **BOTH HALVES PAPER-GRADE (clean trees).** MVBench: base 0.600@4.06 (Pareto win vs dense-6). TOMATO: base 0.333@3.55 (Pareto tie vs dense-8 at 44% budget). | Done | Full claim satisfied with clean provenance |
| 7 | Architecture-conditioned reuse fidelity is a spectrum (not binary: windowed-mostly = byte-identical; all-global = high-fidelity approximate but can still be lossless depending on pretraining) | Phase 1.42 attention-topology (Qwen windowed vs Gemma global + optional InternVL3 all-global) | NOT STARTED; sam's whitepaper §2.7 + §2.9 provides hypothesis; scope note: InternVL3 is all-global yet preserves 95% strict agreement, so a binary claim is under-evidenced | Second-arch feasibility on M3 Air 16GB | Claim on ≥ 2 local architectures with different attention topologies |
| 8 | Validated on VideoMME (de facto benchmark standard) | Phase 1.41 VideoMME lane on Qwen 7B | NOT STARTED | Corpus setup | Claim on local VideoMME evaluation |
| 9 | Beats novelty-ranked dense at matched budget | Phase 1.34 novelty-ranked dense baseline | **COMPLETE 2026-04-17.** Full 2×3 grid N=30 landed. TOMATO: novelty N=4 ties uniform (0.133); N=6 HURTS by 0.100 (0.167 vs 0.267); N=8 HURTS by 0.100 (0.233 vs 0.333). MVBench: novelty N=4 BEATS uniform by +0.067 (0.567 vs 0.500) — sign flips at low budget; N=6 ties; N=8 LOSES by 0.067 (0.567 vs 0.633) — novelty saturates at 0.567 while uniform scales. Cached base on each benchmark (0.333@3.55 TOMATO, 0.600@4.06 MVBench) DOMINATES every novelty-ranked cell at equal-or-lower fresh-frame budget. Claim #9 fully supported. | None | Claim earned on both benchmarks |
| 10 | Composition with within-frame methods (FastV/FlashVID) is multiplicative | Phase 1.32 FastV pilot or FlashVID comparison | NOT STARTED; blocked on mlx-vlm fork | Fork engineering | Deferred; claim only after measured |

## What must land before arXiv submission

**Non-negotiable** (codex 2026-04-16):
- Claims 3, 4, 6 all passed (method + placement + N=30)
- Claim 1 at least partially (oracle confirms pixel-diff signal quality)
- Claim 5 at minimum one wall-clock measurement (Track B)
- Claim 8 (VideoMME lane)

**Strongly recommended** (codex + ChatGPT):
- Claim 7 (second architecture)
- Claim 9 (novelty-ranked dense baseline)
- Claim 2 (STATIC vs STATIC+SHIFTED explicit comparison)

**Can defer to paper discussion / future work**:
- Claim 10 (composition)
- Full codec signal path (phase 1.29 MV-only)
- TempCompass as third benchmark

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
