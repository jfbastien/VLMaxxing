# Research Strategy After CodecSight & CoPE-VideoLM

Date: 2026-04-16
Parent: [PLAN.md](../PLAN.md), [execution-plan-round-7.md](execution-plan-round-7.md)
Positioning: [literature-map-2026-04-16.md](literature-map-2026-04-16.md)

## Candidate Thesis (target, not current claim)

After CodecSight (systems) and CoPE-VideoLM (model) landed, the
**candidate paper thesis** is:

> **A training-free, codec-guided temporal routing method that aims to
> improve the quality–compute Pareto frontier for video VLMs on
> temporal-reasoning benchmarks (TOMATO, TempCompass, MVBench motion)
> by combining concentration-aware change detection, bounded
> staleness, and projector-consistent sparse execution. Real measured
> skipped compute on Apple Silicon MLX remains a gating requirement,
> not a completed claim.**

Five **target claims** to test:

1. Codec-derived proxies are valid training-free routing signals.
2. Naive mean-diff + no-refresh is too blunt on TOMATO-style brief
   semantically-critical change patterns (confirmed by our phase 1.10
   negative and phase 1.11 null-on-MVBench-holdout results).
3. Sticky-dynamic + age-bounded + projector-group-complete planners
   repair hard temporal failures.
4. The saved budget can be spent on more frames, not just less
   latency. Iso-token-budget coverage beats dense frame subsampling.
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

## Ordering (ordered by value, fits ~30 hrs autonomous budget)

Priority = (probability-of-moving-paper-claim × magnitude) / (effort).

1. **Phase 1.26 sticky-dynamic planner** — ~3 hrs GPU + ~2 hrs code.
   Highest leverage. Directly attacks the current failure mode and
   is the single biggest delta per CodecSight's own ablation.
2. **Phase 1.27 projector-group completion** — ~1 hr code + ~1 hr
   GPU. Composes with 1.26; the two together are the strongest
   policy delta we can ship.
3. **Phase 1.20 TOMATO N=30** — ~3 hrs GPU. Required to harden any
   claim; without it the TOMATO tie is noise.
4. **Phase 1.28 iso-token-budget coverage** — ~2 hrs GPU.
   "What does the saved budget buy us?" answer — paper claim #4.
5. **Phase 1.29 MV-only signal path** — ~4 hrs code + ~2 hrs GPU.
   Deployability story. Option to defer behind phase 1.30 if
   Track B timing harness lands first.
6. **Phase 1.31 failure predictor** — ~2 hrs CPU. Mechanistic
   understanding that can be computed on existing artifacts.
7. **Phase 1.32 FastV composition pilot** — ~1-2 weeks (mlx-vlm
   fork for attention-score exposure). Defer until 1.26 + 1.27 +
   1.28 are stable.
8. **Phase 1.33 FastVID baseline** — ~1 week (torch port; run on
   same slices for comparison). Defer until first paper draft.
9. **Phase 1.30 streaming-window harness** — ~1 week infra + ~2 hrs
   eval. Needed for CodecSight-comparable operating point. Defer
   unless Track B ships first.
10. **Phase 1.25 TempCompass ingest** — ~1 day corpus work + ~2 hrs
    GPU. Additional benchmark to broaden coverage; defer until TOMATO
    / MVBench story is settled.

## What the operator needs to review before I proceed autonomously

- The demoted/retired list above. If the user wants phase 1.21 or
  phase 1.13 to still run, flag it.
- The priority order. If there's a strong preference for phase 1.32
  (FastV composition) as the showcase, I need to commit the ~1-2
  weeks to mlx-vlm forking.
- The thesis statement. If the user wants a different paper frame,
  the whole execution plan rearranges around that.
- The decision to absorb CodecSight's sticky-dynamic + projector-group
  as borrowed mechanisms (with proper attribution). If there's a
  concern about overlap in novelty, we need to add something
  CodecSight doesn't have — e.g., the concentration-aware change
  detection (our TOP_K_MEAN statistic, or a new "transient event
  detector" family).

## Concrete hypotheses per new phase

### Phase 1.26 — sticky-dynamic planner

H1: Adding sticky-dynamic (once marked dynamic within a reset window,
   stay dynamic until window end) recovers the 1 direction-item that
   `max_abs(8,32) static+shifted age=4` misses on TOMATO dev.

H2: On MVBench motion holdout, sticky-dynamic does NOT recover the 0.733
   dev result because the dev-to-holdout gap was items-level, not
   mechanism-level.

H3: Sticky-dynamic's main cost is extra fresh-token-equivalent budget
   (fewer blocks marked reusable) — the trade-off is 0.05–0.15 extra
   fresh frames on TOMATO motion dev vs the vanilla policy.

### Phase 1.27 — projector-group completion

H1: On Qwen 2.5-VL (2×2 spatial merge), snapping dynamic to tiles
   before ViT eliminates the small garbage-projector-input risk
   without a measurable Pareto shift.

H2: Combined with sticky-dynamic, projector-group completion gives
   a cleaner Pareto frontier at the same operating points (the
   mechanism matters for deployability, not for dev accuracy on the
   frozen manifest).

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
