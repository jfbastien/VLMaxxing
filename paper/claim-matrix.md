# Paper Claim Matrix

Last updated: 2026-04-16

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
| 1 | Codec-derived proxies are valid training-free routing signals | Phase 1.36 oracle shows r ≥ 0.7 for at least one pixel signal; phase 1.29 MV-only path matches | Oracle preregistered; MV-only proposed | None (oracle CPU-only) | Claim on oracle + MV-only results |
| 2 | Naive mean-diff is too blunt on temporally concentrated evidence | Phase 1.36 oracle shows MAX_ABS or CPF > MEAN by ≥ 0.1 Spearman gap; falsified-hypotheses ledger entry for mean-diff default | Partially supported by phases 1.6/1.7/1.10 | None | Claim when oracle confirms + STATIC-only comparison |
| 3 | Concentration-aware routing (child-veto, sticky-dynamic, age-bounded) repairs hard temporal failures | Phase 1.37 child-veto + phase 1.26 sticky + age-bounded all evaluated on dev/holdout | Sticky4 passes MVBench holdout (1.26.B); child-veto preregistered | Phase 1.37 code + run | Claim on N=30 surviving sticky4 + child-veto result |
| 4 | Saved budget placement matters more than quantity | Phase 1.38 temporal placement ablations show middle-event items; phase 1.28 shows 16-frame saturation | Partially supported (1.26 asymmetry, 1.28 saturation) | Phase 1.38 run | Claim when ablations + oracle + N=30 all converge |
| 5 | Real sparse execution converts proxy gain into measured speedup | Track B harness: wall-clock decode/preprocess/vision/prefill/generation + peak memory + FLOPs | **NOT STARTED** | Track B design + implementation | Cannot claim until measured; prospective until then |
| 6 | Method survives on temporal-reasoning benchmarks at N=30 | Phase 1.21 MVBench N=30 + phase 1.20 TOMATO N=30 | 1.21 in-flight (dense baselines); 1.20 proposed | 1.21 completion | Claim on first N=30 Pareto survivor |
| 7 | Architecture-dependent exact vs approximate reuse | Phase 1.42 attention-topology (Qwen windowed vs Gemma global) | NOT STARTED; sam's whitepaper provides hypothesis | Gemma 4 on M3 Air feasibility | Claim on local second-arch result |
| 8 | Validated on VideoMME (de facto benchmark standard) | Phase 1.41 VideoMME lane on Qwen 7B | NOT STARTED | Corpus setup | Claim on local VideoMME evaluation |
| 9 | Beats novelty-ranked dense at matched budget | Phase 1.34 novelty-ranked dense baseline | Proposed | Code + run | Claim on comparison result |
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
