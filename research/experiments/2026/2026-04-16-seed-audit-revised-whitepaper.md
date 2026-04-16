# Seed Audit: Revised Whitepaper (2026-04-16)

## Provenance

Source: `~/s/codec-through-sam/whitepaper.md` (imported as
`seed/whitepaper/whitepaper-revised-2026-04-16.md`).

The revised whitepaper adds three major claim families beyond the
original we've been targeting:

1. **VideoMME** as a primary benchmark (300 questions, 100 videos,
   32 frames, 100% byte-identical on Qwen, 90%/−3.3% on Gemma 4)
2. **Cross-architecture generalization** on Gemma 4 26B with the
   architectural hypothesis: windowed attention (Qwen) → exact
   reuse, global attention (Gemma 4 SigLIP) → approximate reuse
3. **Wall-clock throughput** on Apple M5 Max: 6.0× ViT, 4.2× E2E,
   130 fps on 32-frame conferencing
4. **Strict-parse audit** methodology: 413 Qwen items with raw
   response logging, 0 parse failures
5. **New competitors**: FlashVID (ICLR 2026 Oral, 6.3× prefill,
   99.1% accuracy), STC-Cacher (CVPR 2026, in-ViT caching),
   DyCoke, EVS, NVILA
6. **Thinking-amplification finding**: Gemma 4 thinking-on drops
   strict agreement from 82% → 58%, byte-identical from 82% → 12%

## What we import as provenance, NOT as trusted claims

All of the above are imported as seed material with the same
epistemics we apply to the original whitepaper: useful hypotheses
and comparison targets, NOT claims we inherit without local
reproduction.

Specific trust boundaries:

| Claim | Our status | Required to trust |
|---|---|---|
| Qwen2.5-VL 100% agreement on TOMATO (1,484 items) | Local partial (0.833 on 30 items) — not yet at sam's level | Full TOMATO run with our strict parser |
| Qwen 100% on VideoMME (300 items) | Not attempted | Local VideoMME lane (phase 1.41) |
| Qwen 100% on MVBench (160 items) | Local partial (0.870 on 54 items) | Full hosted + NTU run |
| Gemma 4 90% on VideoMME | Not attempted | Local Gemma 4 setup (may not fit M3 Air 16GB) |
| Windowed-attention → exact, global → approximate | Not tested | Local Qwen vs Gemma comparison |
| Thinking amplification | Not tested | Gemma 4 thinking-on/off comparison |
| Wall-clock 6.0× / 4.2× / 130 fps | Not attempted (M5 Max, not our M3 Air) | Local Track B harness |
| Strict-parse 0/413 failures on Qwen | Plausible — our parser also gets 0 failures locally | Already confirmed on our smaller slices |
| FlashVID 6.3× prefill, 99.1% | Not verified locally | External reference |
| STC-Cacher CVPR 2026 | Not verified locally | External reference |

## What changes in our plan

### New claims to register

- `WP-2.7`: VideoMME evaluation (Qwen + Gemma 4)
- `WP-2.8`: Strict-parse audit methodology (413+ items, 0 failures)
- `WP-2.9`: Cross-architecture generalization (windowed vs global
  attention topology)
- `WP-2.10`: Thinking-amplification finding
- `WP-4.1`: Wall-clock throughput (ViT speedup, E2E speedup, FPS)
- `WP-5.1`: Composition projection with TurboQuant (~175×)

### New phases to preregister

- **Phase 1.41 VideoMME lane**: stand up local VideoMME on Qwen 7B
  MLX. This is the de facto standard for video VLM efficiency papers.
  Matches sam's setup at 32 frames. Priority: high, after N=30.
- **Phase 1.42 Attention-topology experiment**: test the hypothesis
  that windowed attention gives exact reuse while global attention
  gives approximate. If we can run Gemma 4 4B (edge variant) on
  M3 Air, that would be the second architecture. Priority: medium.

### New competitors to track

Add to `docs/related-work-table.md`:
- **FlashVID** (ICLR 2026 Oral): post-ViT tree-based token merge,
  6.3× prefill, 99.1% accuracy. Qwen2.5-VL tested. **Composable
  with us** (multiplicatively: we skip ViT, FlashVID merges
  remaining tokens).
- **STC-Cacher** (CVPR 2026): in-ViT activation caching via Key
  projection cosine similarity, 24.5% ViT reduction. Partially
  composable.
- **DyCoke** (CVPR 2025): LLM-side token merge + KV pruning.
- **EVS** (Oct 2025): post-ViT prune by pixel L1 diff. Closest to
  our signal (both use pixel diff!) but operates at per-token
  granularity within frames rather than per-frame binary.

### What this does NOT change

- Our planner-2.0 direction (child-veto, feature-change oracle,
  placement ablations) is still the correct next method step.
- Track B is still unbuilt and mandatory for SOTA comparison.
- The MVBench holdout sticky4 result (phase 1.26.B) is still our
  strongest local signal.
- Phase 1.21 N=30 is still the hardening gate.

## What sam does better that we should learn from

1. **Scope of benchmarking**: 1,837 items across 3 benchmarks vs
   our ~150 items across 2 benchmarks. We need VideoMME.
2. **Cross-architecture testing**: two architecturally distinct VLMs.
   We have only Qwen.
3. **Strict-parse audit at scale**: sam has 413 items with raw
   response logging and 0 parse failures. Our exact strict-parse
   coverage: 30 TOMATO benchmark-native items (0 parse failures,
   `docs/reproduction-status.md` row WP-2.5) + 54 MVBench hosted
   items (0 parse failures, row WP-2.6) = **84 saved benchmark
   items**, all with 0 parse failures. Additionally, ~60 items across
   motion dev/holdout slices evaluated in phases 1.10–1.12 with
   0 parse failures. Exact total: ~144 items (not "~150"). Scaling
   to 413+ is the remaining step.
4. **Honest weakness section**: per-frame binary can't prune within
   novel frames. We already know this from our planner work.

## What we do better than sam

1. **Dev/holdout discipline**: sam runs on everything once. We split
   dev vs holdout and preregister.
2. **Matched dense frame-budget baselines**: sam compares cached vs
   dense-same-frames. We compare at matched effective fresh frames.
3. **Content-conditioned planner search**: sam uses default
   thresholds (STATIC < 3, SHIFTED < 8). We ran 30-policy grid
   sweeps across 4 statistics × thresholds × reuse classes × max_age
   (phases 1.10–1.11) and SEPARATELY tested sticky-dynamic (phase
   1.26) — these are distinct experimental families, not one sweep.
4. **Pareto analysis**: we compute real Pareto frontiers; sam reports
   binary agreement.
5. **Falsified-hypotheses ledger**: we track what doesn't work.
6. **Post-CodecSight positioning**: we've already absorbed
   CodecSight, CoPE, FrameFusion, STTM, T3S. Sam's comparison table
   is broader but our methodology context is deeper.
