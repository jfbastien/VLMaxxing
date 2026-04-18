# Sam-reproduction lane — preregistered (2026-04-17)

**State**: **pilot n=1 landed 2026-04-18 as preregistered null** (1.51R
end-to-end 1.01× vs 1.8× target on `videomme:long:669-1`). Scale-up
(Stage 1 n=30) running. See
`research/experiments/2026/2026-04-18-phase-1_51R-pilot-findings.md`
for the arithmetic ceiling derivation and stage-level share
breakdown.
**Parent**: `paper/claim-matrix.md` claims #7, #10, #11 (Gemma
architecture fidelity, composition, and novelty-pruning speedup)
**Depends on**: `docs/videomme-download-handoff.md` (user must unpack
VideoMME videos first)
**Motivation**: Codex round-17 flagged that phase 1.51 as written is
a TOMATO/MVBench-centric novelty-pruning expansion, NOT a faithful
local reproduction of Sam's main headline path. This note adds the
faithful-reproduction lane so the paper can claim "we reproduced Sam's
Gemma + VideoMME novelty-pruning result locally" in addition to
"we extended it to TOMATO/MVBench."

## What Sam measured (from whitepaper §2.11)

Sam's whitepaper reports:

- **Model**: Gemma 4 26B on M5 Max hardware.
- **Benchmark**: VideoMME test split.
- **Mechanism**: hard spatial pruning (per-frame novelty score;
  preserve static-anchor tokens; drop the rest before LLM prefill).
- **Result**: 4-5× end-to-end speedup at accuracy within some band
  of Gemma-dense. Exact accuracy delta is measured in Sam's table,
  which should be cited in the paper.

## What we will measure locally (reproduction)

**Model**: Gemma 4-E4B-4bit (smaller model than Sam's 26B; the one
that fits on M3 Air 16 GB).
**Benchmark**: VideoMME test split N=30 (matched manifest to what
phase 1.41 uses for Qwen).
**Mechanism**: same as Sam's — anchor-selection + novelty-ranked
prune, keep top-K tokens per frame.
**Target claim**: reproduce the SIGN and ORDER-OF-MAGNITUDE of Sam's
result on the smaller model at M3 Air scale. Exact multiples may
differ (smaller model → larger prefill fraction → potentially larger
speedup; or smaller model → tighter accuracy floor → smaller usable
keep-rate region).

## Phase structure (ordered)

### Phase 1.42 — Gemma smoke (claim 7 partial)

Already designed in
`research/experiments/2026/2026-04-17-phase-1_42-gemma-integration-design.md`.
Option A (whole-frame-or-nothing temporal reuse). NOT required for
the reproduction lane but establishes that Gemma runs correctly
through the harness and supports `cached_image_features`.

Scope: 1 item smoke + N=30 on one benchmark (TOMATO).
Runtime: ≈ 1.5 h GPU after integration code lands.

### Phase 1.51R — Sam novelty-pruning reproduction on Gemma + VideoMME (NEW)

**Primary reproduction phase.** Runs independently of 1.42 temporal
reuse integration (novelty-pruning is a fresh code path at the LLM
prefill input, not a `_mix_gemma_features` consumer).

Scope:

- VideoMME test split, N=30 per duration band (short/medium/long/very-long).
- Gemma 4-E4B-4bit dense baseline: no prune, uniform 8-frame sample.
- Novelty-pruning cells: 5 anchor arms × 5 keep rates, same grid as
  phase 1.51 on TOMATO/MVBench. Anchor arms (matching
  `src/codec_through/novelty_pruning.py::ANCHOR_ARMS`):
  {`none`, `cls_attention_proxy`, `nuwa_pillar`,
  `max_min_diversity`, `gemma_structural`}. `cls_attention_proxy`
  is excluded from winner promotion (see `PROMOTABLE_ARMS`) since
  Gemma's post-pool stream has no true CLS-attention signal —
  the arm ranks by a caller-supplied proxy and runs for literature
  comparison only. Keep rates: {0.3, 0.4, 0.5, 0.6, 0.7}.
- Per-cell N=30 dev pass, single-shot holdout on the rank-1 cell.

Runtime budget: ≈ 6-8 h GPU wall time cold-cache (Gemma features
not in the current feature cache, each dev cell does dense feature
extraction once).

**Success criterion for "Sam reproduction":**

1. At least one (anchor-arm × keep-rate) cell on VideoMME achieves
   end-to-end speedup ≥ 1.8× over Gemma-dense-8 at accuracy within
   0.10 of dense-8.
2. The speedup scales monotonically with (1 − keep_rate) at high
   keep rates (keep ≥ 0.5) — qualitative agreement with Sam's
   measurement that dropping more tokens → more speedup until
   accuracy falls off.
3. The sign of the accuracy-vs-speedup Pareto matches Sam's report
   (monotonically decreasing accuracy at monotonically increasing
   speedup, rather than e.g. a noisy scatter).

If all three hold → **claim: the Sam novelty-pruning result
reproduces on Gemma 4-E4B-4bit at M3 Air scale.**
If (1) holds but (2) or (3) fails → partial reproduction; paper
cites it as "sign matches, mechanism has a different scaling
regime at this model size."
If (1) fails → NO-REPRODUCTION. Paper cites it as a preregistered
null and explains what's different (model size, quantization,
hardware, Gemma E4B pretraining vs 26B).

### Phase 1.52R — Combined temporal + novelty reproduction (NEW)

Depends on phase 1.42 (temporal reuse on Gemma works) AND phase
1.51R (novelty-pruning reproduces on Gemma + VideoMME).

Scope: winning cells from 1.51R + whole-frame temporal reuse (Option
A from the 1.42 design note). Run N=30 on VideoMME, compare combined
speedup to the product of individual speedups.

Success criterion: combined speedup is at least the MAX of the two
individual speedups (i.e., stacking does not hurt). "Multiplicative"
claim requires combined ≥ (1 + temporal) × (1 + novelty) − 1 within a
noise band; "additive" is combined ≈ temporal + novelty; "sub-additive"
is combined < max(temporal, novelty).

Runtime: ≈ 2-3 h GPU wall time after 1.51R holdout lands.

### Phase 1.51E — Novelty-pruning extension on TOMATO/MVBench (the existing 1.51)

The already-registered phase 1.51 stays; it's an expansion lane
(does Sam's mechanism port to temporal-reasoning benchmarks on the
smaller Gemma?). Rename-in-place: phase 1.51 → phase 1.51E
("extension") to distinguish from 1.51R ("reproduction"). Both
run; both contribute to the paper. Reproduction is prioritized.

### Phase 1.41 — Qwen + VideoMME baseline

Required anchor so the paper has a within-architecture dense
baseline for VideoMME; unlocks claim 8.

Runtime: ≈ 2 h GPU wall time, cold-cache.

## What the paper says from this lane

- §Results will have a VideoMME table with: Qwen-dense-8, Qwen +
  Planner 2.0, Gemma-dense-8, Gemma + novelty-pruning (Sam's
  reproduction), Gemma + combined (phase 1.52R if applicable).
- §Discussion will cite Sam's 4-5× number on Gemma 4 26B with M5 Max
  and compare to our measured speedup on Gemma 4-E4B with M3 Air,
  explaining the deviation as a model-size / hardware-class shift.
- If reproduction fails: §Discussion cites the null as evidence
  that Sam's mechanism is either model-size-sensitive or
  hardware-specific; paper does NOT claim reproduction, but the
  negative result is still publishable.

## Ordering justification for user's "big numbers ASAP"

1. User unpacks VideoMME videos (blocks everything below).
2. Phase 1.41 Qwen + VideoMME N=30 (claim 8, ≈ 2 h) — first VideoMME
   number in the paper.
3. Phase 1.42 v0 Gemma smoke (claim 7 partial, ≈ 1.5 h) — establishes
   Gemma works on the harness. Can actually run in parallel with
   1.41 if we're careful about MLX queue.
4. **Phase 1.51R Sam reproduction on Gemma + VideoMME** (claim 11,
   ≈ 6-8 h) — the BIG NUMBERS result. If this lands as preregistered,
   the paper has its headline.
5. Phase 1.52R combined (claim 10, ≈ 2-3 h) — multiplicative
   composition measurement.
6. Phase 1.51E extension on TOMATO/MVBench (≈ 4-6 h) — breadth.
7. Phase 1.38 placement ablation (Lane A, ≈ 30 min).
8. Phase 1.37 within-block child-veto implementation + run (Lane A,
   ≈ 2 h + code time).
9. Phase 1.43 EgoSchema on Qwen (Lane A, ≈ 2-3 h).

Total runtime budget: **~22-30 hours of MLX wall time** from user
unpack to full reproduction + expansion + Lane-A completeness.

## Open questions (need user/Sam input)

1. **Anchor selection details**: Sam's whitepaper §2.11 describes
   the anchor concept (preserve static tokens; drop novel ones) but
   the exact anchor extraction procedure is a few possible
   implementations. We should either (a) pick the simplest
   well-specified option and report what we did, or (b) pull the
   canonical anchor extraction from Sam's reference code if available.
   **Request**: access to Sam's reference implementation if possible,
   or explicit confirmation that we're free to choose our own anchor.
2. **Keep-rate range**: Sam's paper reports a single operating point
   (some keep rate that gives 4-5×). We should sweep 5 rates. Does
   Sam have guidance on the well-behaved rate region or the typical
   accuracy knee location?
3. **Reproduction credit**: the paper should credit Sam's concept
   even where our measured speedup differs from Sam's reported
   4-5×. **Proposed language**: "novelty-pruning of visual tokens
   pre-prefill, following Sam's whitepaper §2.11; our Gemma 4-E4B-4bit
   measurement at M3 Air is [X.Y]× vs Sam's 4-5× on Gemma 4 26B at
   M5 Max." (Sam co-authors the paper, so this is primarily a
   methods-section tone choice.)

## Related docs

- `docs/videomme-download-handoff.md` — external blocker.
- `research/experiments/2026/2026-04-17-phase-1_42-gemma-integration-design.md` — Gemma temporal reuse design.
- `research/experiments/2026/2026-04-17-phase-1_51-novelty-pruning-gemma-prereg.md` — original (now extension) prereg.
- `research/experiments/2026/2026-04-17-phase-1_52-combined-temporal-spatial-prereg.md` — combined pipeline.
- `paper/publishability-status.md`, `paper/claim-matrix.md` — one-paper framing and claim status.
