# Research Strategy After CodecSight & CoPE-VideoLM

Date: 2026-04-16
Parent: [PLAN.md](../PLAN.md)
Sibling: [literature-map-2026-04-16.md](literature-map-2026-04-16.md)
Positioning: [literature-map-2026-04-16.md](literature-map-2026-04-16.md)

## Candidate Thesis (target, not current claim)

After CodecSight (systems) and CoPE-VideoLM (model) landed, the
**candidate paper thesis** is:

> **A training-free temporal routing method that aims to improve the
> quality–compute Pareto frontier for video VLMs on temporal-reasoning
> tasks, when reuse is concentration-aware, age-bounded,
> architecture-aware, and backed by real skipped compute.**

If phase 1.29 MV-only signal path lands: "codec-guided." If not:
"codec-inspired / pixel-diff proxy for codec-guided." See
`paper/claim-matrix.md` for per-claim evidence gates.

Five **target claims** to test:

1. Pixel-diff (and optionally codec-derived) proxies are valid
   training-free routing signals.
2. Naive mean-diff + no-refresh is too blunt on TOMATO-style brief
   semantically-critical change patterns.
3. Concentration-aware routing (child-veto, sticky-dynamic,
   age-bounded) repairs hard temporal failures. (Note:
   projector-group completion is a no-op on our current Qwen 2.5-VL
   stack where BLOCK_SIZE=28 already matches projector input
   granularity; removed from the claim.)
4. Budget placement over time matters more than scalar fresh budget.
5. Real sparse execution converts the proxy gain into measured
   wall-clock speedup on MLX.

## Why we're in a defensible slot

CodecSight validates the broader systems thesis that codec signals can
serve as low-cost runtime oracles, but in an anomaly-streaming setting
rather than temporal-reasoning QA. CoPE-VideoLM validates the "buy
more frames per compute" thesis with a trained codec-aligned
representation. Our current slot is training-free,
temporal-reasoning-focused, MLX-local, with real skipped compute still
pending.

**Single-line differentiators** (current evidence):

- vs CodecSight: different benchmark domain, training-free planner
  search, no NVDEC dependency (MLX-side MV extraction path — phase
  1.29 pending).
- vs CoPE-VideoLM: training-free, no Δ-encoder pretraining.
- vs FastV/FastVID/VisionZip/SparseVLM/VScan: different axis
  (encoder-side temporal; they are intra-frame or decoder-internal).
  Likely composes in principle; measured composition remains future
  work.

## What changes in the plan

### Still do

- Phase 1.19 calibration fix: already landed (MAE 0.20 → 0.0017).
  Confirmed as critical methodology hygiene.
- Phase 1.20 TOMATO N=30 enlargement remains important because the
  current N=15 result is too small for cross-paper quantitative
  comparison.
- Phase 1.23 FastV scouting: complete; next step is the MLX-vlm fork
  for attention-score exposure.
- Phase 1.24 TOMATO holdout dense backfill: already landed.

### Demote / retire

- Phases 1.14, 1.15, 1.17, 1.18: further refinement of dense-dominated
  or holdout-rejected policies has no paper value. Demote to
  exploratory unless a specific research question arises.
- Phase 1.13 logprob stratification: defer until at least one policy
  survives N=30 enlargement — otherwise we're stratifying noise.
- Phase 1.21 MVBench N=30: **RE-ACTIVATED 2026-04-16** after phase
  1.12.B surfaced a cross-benchmark-discovered MVBench holdout
  Pareto survivor (`max_abs(8,32) static+shifted age=4` at cached
  0.667 / fresh 4.59 / agreement 0.933). Previously demoted under
  the assumption that MVBench holdout was a clean null; the null
  was specific to the phase-1.11-grid-sampled winners, not the
  (transfer-discovered) policy. N=30 now required for cross-paper
  comparability.

### Add (phases 1.25–1.33, preregistered)

The new tranche targets the 5 paper claims directly.

| Phase | Purpose | Claim |
|---|---|---|
| 1.25 TempCompass ingest | Add third benchmark per chat guidance | 2, 3 |
| 1.26 Sticky-dynamic planner | CodecSight-borrowed "once dynamic, stay dynamic within-GOP" | 3 |
| 1.27 Projector-group mask completion | Snap dynamic to 2×2 tiles before ViT | 3 |
| 1.28 Iso-token-budget coverage | cached @ {8, 12, 16} vs dense @ matched fresh_frames | 4 |
| 1.29 MV-only signal path (PyAV) | Deployable codec signal without NVDEC | 1 |
| 1.30 Streaming-window harness | Overlapping-window eval on continuous video | 5 |
| 1.31 Failure predictor | Quantitative model of when cached fails dense | all |
| 1.32 FastV composition pilot | First orthogonal-axis composition measurement | 5 |
| 1.33 FastVID baseline (torch) | Within-frame video-specific SOTA comparison | 2 |

Each phase is gated (some require code work first, some require an
N=30 survivor, some are purely additive). Ordering in the execution
plan.

## 2026-04-17 Codex review — phase additions from sam's broader surface

Codex re-read sam's whitepaper and flagged four **phases we should add
to the plan** because sam has measured results in those areas and our
paper currently does not:

- **Phase 1.43 EgoSchema low-reuse robustness** (new, Tier B). Sam
  reports 100% byte-identical agreement on Qwen2.5-VL-7B at 29.9% mean
  token reuse (N=100). This is the strongest counterexample to "caching
  only helps high-reuse content" in the current literature. If our
  planner at a matched low-reuse slice retains its quality-vs-fresh-
  tokens Pareto, claim #4 (budget-placement, not just reuse quantity)
  is strengthened. Runtime estimate: 2 hrs GPU at N=30 on our stack
  after EgoSchema is standable locally.
- **Phase 1.44 VideoMME frame-count scaling** (new, Tier B,
  blocked-by 1.41). Sam reports reuse climbing 86.5→90.8→93.1% across
  32/64/128 frames on conferencing content, with E2E speedup sustained
  at 4–5×. Our paper currently has no frame-count scaling axis. Runtime
  estimate: ~6 hrs GPU for VideoMME 30-item × {32, 64, 128} frame sweep
  once 1.41 lands.
- **Phase 1.45 combined temporal+spatial pipeline** (new, Tier C,
  blocked-by 1.29). Sam's most distinctive contribution is a MEASURED
  4–5× E2E speedup with combined temporal + spatial pruning on Gemma 4
  26B. We don't know if the arithmetic composes on Qwen2.5-VL-7B 4-bit
  at M3 Air. Runtime estimate: ~4 hrs GPU once hard spatial pruning
  lands (it's Track B-adjacent).
- **Phase 1.42 InternVL3 third architecture** (already planned, now
  re-scoped). Sam's whitepaper is internally inconsistent on whether
  InternVL3 is windowed or all-global (§2.7 line 171 says all-global,
  §2.10 line 243 says windowed). If we land Gemma 4 and InternVL3 we
  get a three-cell view of the topology spectrum without inheriting
  sam's binary framing.

Codex also verified **what we should NOT import from sam**:

- "windowed = exact, global = approximate" as a theorem (sam's own
  data shows InternVL3 between Qwen and Gemma 4 at 95% strict — this
  is a spectrum, not a binary)
- "mean-diff is the best classifier" (the word "mean-diff" does not
  appear in sam's whitepaper; this was a codex-summary artifact)
- "composition is real 175×" (sam's §5 explicitly marks it as
  projected, not measured)

See `research/experiments/2026/2026-04-16-seed-audit-revised-whitepaper.md
§ 2026-04-17 addendum` for the full cross-check.

## Ordering (UPDATED 2026-04-16 after weird-tricks review + ChatGPT synthesis)

Priority = (probability-of-moving-paper-claim × magnitude) / (effort).

### Tier 0 — recently completed

1. ✅ **Phase 1.21 MVBench N=30** — **PASSED**. Both variants
   survive holdout v2 (N=30): base policy (0.600@4.06, Pareto win
   vs dense-6) and sticky4 (0.633@4.49, Pareto tie vs dense-8).
   MVBench paper claim is now paper-grade on this slice. Dev v2
   cells deferred to later tranche.

### Tier A — do next (highest expected value)

2. ✅ **Phase 1.20 TOMATO N=30** — **PASSED (clean tree, commit
   42b06eb)**. Base policy ties dense-8 at 44% budget (0.333@3.55).
   Claim #6 now paper-grade on both benchmarks.
3. **Phase 1.36 feature-change oracle** — ~30 min CPU. Can run in
   parallel with 1.20 GPU work. Answers "signal quality or schedule
   quality bottleneck?"
4. **Phase 1.34 novelty-ranked dense baseline** — the strongest
   immediate falsifier of the current Pareto story. If cached loses
   to smart-frame-selection dense at matched budget, the method
   claim weakens. Per codex: should run BEFORE 1.37.
5. **Phase 1.38 temporal placement ablations** — ~3 hrs GPU. Dense-
   only frame0/middle/last/first+last/uniform4/uniform8 on TOMATO
   dev. Sharpens the budget-placement theory with causal evidence.

### Also in Tier A: explicit reuse-class comparison

Between phases 1.36/1.37, add:

- **STATIC-only vs STATIC+SHIFTED** comparison on the current best
  policy family. Per ChatGPT 2026-04-16 review: this is cheap,
  scientifically clean, and directly relevant since the imported
  shift-locality strength is not fully settled on the local stack.
  The combined Planner 2.0 family should be: `{MAX_ABS, CPF} ×
  {STATIC, STATIC+SHIFTED} × {age=2, age=4} × {no-sticky, sticky4}
  × {no-child-veto, child-veto}`.

### Tier B — follow-up

7. **Phase 1.25 TempCompass ingest** — **PROMOTED** per ChatGPT
   2026-04-16 and codex reviews. TempCompass is better aligned with
   our failure mode than broader benchmarks because it isolates
   direction, speed, order, attribute change via conflicting-video
   design. Should run BEFORE broader generic expansion.
8. **Phase 1.35 event-window oracle** — upper-bound ceiling on
   method headroom.
9. **Phase 1.31 failure predictor** — ~2 hrs CPU. First consumer of
   temporal-coverage placement metrics.
10. **Phase 1.29 MV-only signal path** — deployability story.

### Tier C — deferred / blocked

11. Phase 1.39 DCT_HF energy (OCR/screen-content focus)
12. Phase 1.40 speculative verify / selective re-encode (after 1.13
    logprob instrumentation)
13. Phase 1.32 FastV composition (mlx-vlm fork, ~1-2 weeks)
14. Phase 1.33 FastVID baseline (torch-side, ~1 week)
15. Phase 1.30 streaming harness (Track B infrastructure)
16. Phase 1.28.B true iso-budget (calibrated 16-frame tighter
    thresholds)
17. Phase 1.27 projector-group — **SUPERSEDED**. On our Qwen 2.5-VL
    stack BLOCK_SIZE=28 is already projector-input granularity (no-op).
    Sam's Gemma hard-spatial-pruning result (WP-2.11) is the better
    spatial follow-on if needed, but it belongs off the main paper
    critical path until after 1.20, 1.41, and Track B.

### Explicitly deferred to Track B / streaming

- **Temporal RoPE key correction**: NOT applicable to current Track
  A (we re-inject image features, not LLM KV states; Qwen recomputes
  M-RoPE positions on each forward pass). Becomes relevant only for
  selective KV-cache reuse in a streaming path. Per ChatGPT
  2026-04-16 review.
- **Eventful Transformers architecture**: Track B north star.
- **STTM composition**: after standalone planner + Track B.

Completed or superseded (not in active queue):

- ✅ Phase 1.21 (MVBench N=30 holdout: PASSED — base 0.600@4.06, sticky4 0.633@4.49)
- ✅ Phase 1.26 (TOMATO dev: sticky rejected)
- ✅ Phase 1.26.B (MVBench holdout N=15: sticky4 PASSES)
- ✅ Phase 1.26.C (MVBench dev: diagnostic)
- ✅ Phase 1.28 (off-budget probe; protocol deviation documented)
- ✅ Phase 1.19 (calibration fix; MAE 0.20→0.0017)
- ✅ Phase 1.24 (dense backfill; completed)
- ✅ Phase 1.23 (FastV scouting; blocker identified)

## What the operator should review at review cadence

**Updated 2026-04-16** (state after phase 1.12.B + 1.26.B surfaced
a cross-benchmark-discovered MVBench holdout survivor that now PASSES
with sticky_window=4):

- Phase 1.21 and phase 1.13 are **re-activated**, not demoted.
  Phase 1.21 MVBench N=30 is the top hardening gate for the new
  primary cell (`max_abs(8,32) age=4 sticky_window=4`, cached=0.733
  / fresh=5.10 / agreement=1.0 on MVBench holdout N=15).
- Phase 1.32 FastV composition remains blocked on the ~1–2 week
  mlx-vlm fork. If the operator wants to prioritize composition,
  that fork must start before dev N=30 completes.
- Thesis statement: keep current framing until an N=30 outcome
  flips it. See `paper/framing.md` for the candidate paper slot.
- CodecSight's sticky-dynamic and projector-group are borrowed
  mechanisms, with attribution. Phase 1.26.B confirmed sticky is
  benchmark-conditional (helps MVBench, hurts TOMATO direction) —
  this is empirically our contribution on top of the borrowed
  mechanism.

## Concrete hypotheses per new phase

### Phase 1.26 — sticky-dynamic planner (COMPLETED)

**Outcome**: benchmark-conditional mechanism.

- H1 (TOMATO dev recovery): **REJECTED**. sticky_window ∈ {4, 8}
  lowers cached 0.400 → 0.333, raises budget. The classifier
  misses direction motion entirely → nothing to latch.
- H2 (MVBench holdout sticky fails): **OVERTURNED** by phase 1.26.B.
  sticky_window=4 lifts cached 0.667 → 0.733 with agreement=1.000,
  item-identical to dense-8 at 64% budget. The strongest current
  holdout signal.
- H3 (budget cost): sticky_window=4 adds ~0.3–0.5 fresh frames on
  both TOMATO and MVBench; sticky_window=8 adds ~0.7.

The asymmetry is the mechanism finding: sticky works when the
initial classifier catches motion at SOME frame (intermittent →
latched); fails when the classifier misses motion entirely.

### Phase 1.27 — projector-group completion (needs rescoping)

On our Qwen 2.5-VL stack, `BLOCK_SIZE=28` already equals the
projector-input granularity (ViT patch 14 × spatial-merge 2 = 28).
The CodecSight rule is a no-op at this block size. A 2×2 merged-
token coarsening experiment is a DIFFERENT question (spatial
smoothing at 56×56 regions) and needs a separate hypothesis.

### Phase 1.28 — iso-token-budget coverage

H1: At matched fresh-token-equivalent budget ≈ 3.4, cached policy
   on 16 frames gives HIGHER accuracy than cached policy on 8 frames,
   because the extra coverage buys temporal information.

H2: cached-16-frames at 3.4 budget does NOT exceed dense-6-frames
   at 6-frame budget (dense ceiling still dominates at low budget on
   TOMATO motion holdout).

### Phase 1.29 — MV-only signal path

H1: PyAV-extracted H.264 motion vectors can be computed for our
   existing TOMATO / MVBench corpus without re-encoding. Latency
   per frame < 50 ms (decode-anyway cost).

H2: MV-magnitude-based planner correlates with our pixel-diff
   planner at Pearson r > 0.7 across the 15 TOMATO motion dev items.
   Means MV-only is a viable drop-in signal.

## New benchmarks to stand up

- **TempCompass**: isolates speed, direction, order, and
  attribute-change aspects. Strong complement to TOMATO.
- **MVBench motion-heavy group variant**: expand dev/holdout to
  include more action_sequence and motion-dense groups (not the
  simple action_localization etc. that phase 1.21 was going to use).
- **Streaming surveillance slice (optional)**: for CodecSight-style
  overlapping-window eval, we'd need a small slice of continuous
  video. UCF-Crime adapts but is a different domain. Defer unless
  Track B ships first.

## New methodology rules

1. **Matched-budget Pareto requires matched-PROBE items**. If we
   compare cached vs dense at matched fresh_frames, the items must
   be identical. Phase 1.12 and phase 1.24 already do this.
2. **Per-group accuracy reporting** for any policy that passes on
   the overall slice. On TOMATO, report direction / rotation /
   shape_trend separately; on MVBench, per motion-group. At N=15
   per-group is too small, but at N=30 it becomes actionable.
3. **Claim attribution in paper**: sticky-dynamic and
   projector-group completion are explicitly CodecSight-borrowed.
   Our contribution is (a) training-free-planner-search of the
   CodecSight mechanism applied to temporal-reasoning benchmarks,
   (b) the concentration-aware statistic family (TOP_K_MEAN,
   MAX_ABS), (c) iso-token-budget coverage experiments.
4. **Holdout is truly single-shot**. No retuning, no post-hoc
   reruns with different flags, no "but we hadn't thought of this
   control." Phase 1.25 TempCompass will bring a fresh holdout we
   haven't touched yet.

## Preregistration discipline update

Every new phase note must include:

- **Acceptance band** (what number means "claim holds")
- **Rejection band** (what number means "claim dies")
- **Inconclusive band** (what observation means "try again")
- **Per-claim mapping** (which of the 5 paper claims this phase
  supports)

Older phase preregs 1.12–1.23 already do this. Phases 1.25–1.33 must.

## Reading packet for next operator review

Required reads before the next audit cycle:

1. `docs/literature-map-2026-04-16.md` — positioning map
2. `docs/research-strategy-post-codecsight.md` — this file
3. `docs/execution-plan-round-7.md` — phase ordering
4. `research/decision-log.md` — updated rows for post-CodecSight
   positioning
5. Phase 1.25 + 1.26 + 1.27 + 1.28 preregistration notes
6. CodecSight abstract + Eq. 1–4 + Table 4 (ablation)
7. CoPE-VideoLM Table 1 + Appendix H.4 (FPS coverage)
