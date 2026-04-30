# Paper Framing

This file tracks the paper story, contribution boundary, and anti-claims.

Canonical paper-facing manuscript sources (what a reviewer will actually read
once rendered):

- [`paper/arxiv/sections/01_abstract.tex`](arxiv/sections/01_abstract.tex) —
  canonical abstract
- [`paper/arxiv/sections/02_introduction.tex`](arxiv/sections/02_introduction.tex)
  — canonical introduction

It is NOT the place for raw experimental detail. Evidence lives in:

- [docs/reproduction-status.md](../docs/reproduction-status.md) — per-claim
  pre-release source reproduction state
- [docs/literature-map-2026-04-16.md](../docs/literature-map-2026-04-16.md) —
  positioning map against CodecSight / CoPE / FastV / FrameFusion / etc.
- [docs/related-work-table.md](../docs/related-work-table.md) — paper-facing
  method comparison table with verified numbers
- [claim-matrix.md](claim-matrix.md) and
  [publishability-status.md](publishability-status.md) — current paper-facing
  claim and readiness ledgers
- [research/experiments/2026/](../research/experiments/2026/) — phase-by-phase
  results
- [research/falsified-hypotheses.md](../research/falsified-hypotheses.md) —
  what the evidence has ruled out

Last material update: 2026-04-27 (adaptive C-PERSIST breadth landed across
20f short/medium/long plus 32f short at n=93 / 0 observed paired drift,
14.90×--35.92× same-class follow-up speedup, and a 15.28×--35.97×
cold-all-query ratio; stage-timing attribution shows adaptive Q3 avoids the fixed-K last-frame
re-prefill; 1.30AC/AD close the cache-reuse/composition boundary as same net
aggregate loss through different any-paired-drift sets).

## Current Manuscript Position (2026-04-27)

The manuscript should be centered on one anti-recomputation story: where a
frozen video VLM must buy fresh visual evidence over time, and where cached
state remains inside the appropriate quality--compute frontier. That story has
three explicit local regimes, plus one scale-out streaming lane:

- **First-pass vision pruning** (C-VISION) for measured first-query gains on
  fresh videos.
- **Persistent follow-up reuse** (C-PERSIST) for the much larger after-ingest
  follow-up-query wins.
- **Routing-frontier experiments** for mechanism and boundary evidence.
- **Scale-out streaming state reuse** for the 26B native-rate deployment lane
  once artifact-compatible protocols and matched baselines are available.

Those regimes matter for different reasons. C-VISION shows that frozen
first-pass pruning already buys real wall-clock savings, but only in proportion
to the vision share that the dense path actually owns. C-PERSIST is where the
largest local multipliers live, because once a video has already been ingested,
the next question can reuse the expensive prefix instead of rebuilding it.
Routing is the cleanest evidence for why any of this works: novelty
magnitude alone is not enough, temporal placement of fresh compute matters, and
semantic-substitution claims must stay separate from sparse-path speedup
claims.

When this file disagrees with [`paper/priority.md`](priority.md) on what the
paper should lead with, prefer `priority.md`.

## Candidate Paper Slot

> A training-free anti-recomputation paper for video VLMs that shows
> three linked facts: first-pass gains are bounded by the share of
> runtime that vision actually owns, same-video follow-up can collapse
> to sub-second latency once the expensive prefix has been paid, and
> temporal placement of fresh compute matters more than novelty
> magnitude alone.

The semantic codec-native bridge has now landed locally, but the fully
harmonized scale-out systems bridge has not. Keep the wording precise:
sparse-sampled QA is still pixel-diff by design, native-rate streaming is
codec-metadata by design, and any ``codec-guided'' wording should stay attached
to the protocol it actually describes.

The paper-grade story is training-free anti-recomputation with measured
first-pass Gemma/Qwen gains, large after-ingest Qwen follow-up wins, and routing
evidence that explains the mechanism boundary.
For the per-claim breakdown, see
[`paper/claim-matrix.md`](claim-matrix.md) and
[docs/literature-map-2026-04-16.md § Current evidence level (2026-04-16)](../docs/literature-map-2026-04-16.md).

## Three Major Contributions (2026-04-23 status)

Per Codex rounds 25–26 (2026-04-21), the paper spine is these three
first-class contributions — ordered ahead of the Qwen routing lane,
which is reframed as the mechanism-validation backbone + null ledger
(claims 1/2/6/9 earned + halo-veto 1.37B retired + 1.51R VideoMME
duration-conditional partial reproduction + 1.55D frontier-partial):

1. **C-CEILING (claim 13): Arithmetic ceiling model for token-pruning
   wall-clock speedup.** Predicts E2E speedup within ≤5.2% across 7
   regime dimensions on Gemma 4-E4B-4bit (8/32 frame counts × benchmark
   × keep-rate × anchor arm). Formula: `e2e ≤ 1/(fixed_frac + (1 −
   fixed_frac)/s)`. Standalone analytical contribution; validated in the
   1.51R reproduction lane and further extended by 1.51V to a
   vision-axis analog `1/(1 − V_share × V_red)`.

2. **C-PERSIST (claim 14): Persistent follow-up reuse with paired-drift
   tested deployment envelope.** All persistent-KV claims in this paper
   are **after-ingest / follow-up-query** numbers: the user pays the
   full first-query prefill once, subsequent questions on the *same
   video* reuse the KV and return in sub-second time. These are not
   "any-fresh-video" latencies. 7B Qwen 2.5-VL-4bit stays inside the
   tested envelope through ≤16f / ≤6.5k prefill tokens, with a clean 16f
   point (Δacc=0) and a slightly worse but still tolerated 8f point
   (Δacc=−0.048); 3B at ≤36f / ≤14.5k prefill sits on a tolerated
   Δacc=−0.19 plateau (not clean, bounded). Basin onset is bracketed rather
   than a clean parameter-count ratio; basin geometry (non-letter attractor emergence) is
   cross-architectural; sampler-side intervention is
   architecture-conditional (insufficient at 7B basin at 20f AND 40f;
   partial-only at 3B basin at 40f — disperses to pre-basin plateau,
   not to baseline). The repair story is now broad on Qwen: fixed K=1
   selective re-prefill gives 0/93 observed paired drift at 9.48×--20.37×
   same-class follow-up speedup, while adaptive post-Q2-state reuse gives
   0/93 observed paired drift at 14.90×--35.92× same-class follow-up speedup
   (15.28×--35.97× cold-all-query ratio). Stage timing explains the adaptive gain:
   Q3 reuses the post-Q2 cache and avoids the fixed-K last-frame re-prefill.
   Tested deployment-regime table in [`paper/claim-matrix.md`](claim-matrix.md)
   provides paper-grade practitioner guidance; paired-fidelity boundary result
   in its own right.

3. **C-VISION (claim 15): Vision-tower pruning transfers at `L=2`
   `kr_V=0.50` across Gemma 4-E4B-4bit and Qwen 2.5-VL-7B-4bit, with
   first-pass gains governed by the scatter-back ceiling
   `1/(1 − V_share × V_red)`.**
   Dev n=30 headlines are TOMATO **1.24×**, MVBench **1.21×**, and
   VideoMME **1.08×** (8f) / **1.12×** (16f). Holdout status is now
   differentiated rather than missing: VideoMME 8f is **clean** at
   **1.113×** with zero aggregate accuracy delta; MVBench 8f is
   **advisory** at **1.407×** with a scheduler-scale decode note; and
  TOMATO 8f is **earned-advisory** at **1.194×** from checked-in session-5
  artifacts. The matched Qwen VideoMME 8f cross-arch point lands
   at **1.044× observed vs 1.043× predicted**, with smaller absolute lift
   because Qwen's dense vision share is only ~10\%. The mechanism is
   stable; the exact magnitude remains regime-dependent because `V_share`
   and `V_red` are benchmark-, architecture-, and protocol-sensitive.

These three claims align on a common analytical frame: **share ×
reduction → `1/(1 − share × reduction)` ceiling**, with
architecture-specific and regime-specific bounds characterized. The
paper presents these as three independent instantiations of a unified
efficiency-ceiling theory: C-CEILING (LLM-generate axis), C-VISION
(vision-tower axis), and the LLM-side composition analog. C-PERSIST
adds the orthogonal fidelity-floor axis (where the ceiling falls apart
entirely under cache reuse).

**Venue targeting implication:** the combination of C-PERSIST (safety
boundary, cross-architectural) + C-VISION (three-benchmark Gemma
headline cells plus a matched Qwen transfer point) + C-CEILING
(analytical framework) is paper-grade for an efficiency-focused venue
(NeurIPS / ICML efficiency workshop or ICLR Tiny Papers). The systems
angle is real, but a systems venue like MLSys still wants more: a
broader sparse backend, a clean systems baseline such as screenshot
polling, and a broader streaming evaluation. Main-track readiness now
depends on broader asks: (a) sparse-backend coverage beyond the bounded
measured sparse-vision envelope, including sparse LM prefill if claimed,
(b) a cleaner local bridge into the streaming / deployment regime, (c) a
decoder-integrated codec-native / native-rate systems bridge, and (d) a
scroll/pan or egomotion regime-boundary probe on a corpus that actually
contains that motion regime.

## Protocol matters — non-interchangeable evaluation regimes

Every number in this paper lives inside one of these protocols, and the
protocols are not mutually substitutable. Conflating them is the easiest
way to overclaim.

1. **Sparse after-ingest QA.** The VideoMME / MVBench / TOMATO
   benchmarks as we run them: decode N frames once, ask a question,
   score. This is what C-VISION and the 1.51R partial reproduction
   measure. It is *not* streaming, and it is *not* live camera.
2. **Native-rate streaming.** Frames arrive at source rate; the model
   must keep up. Candidate C-STREAM lives here. A checked mixed bundle now
   exists, but it is still bounded evidence rather than a fourth headline:
   default cache reuse is unsafe, prefix-snapshot reuse is positive small-N,
   and simple fixed-evidence baselines are serious.
3. **After-ingest persistent-KV reuse.** Same video, follow-up
   question. The first query pays full prefill; subsequent queries reuse
   the KV and return in sub-second wall-clock. This is what C-PERSIST
   characterizes, and it is the regime with the largest single
   multipliers in this paper — but only for *same-video* reuse.

A sparse-after-ingest speedup is not a streaming speedup. A persistent-KV
latency is not a first-query latency. When the paper gives a number,
it names the protocol it was measured under, in the same sentence.

## What stacks and what doesn't

Multiplicative stacking requires axis-orthogonality in compute. In
practice our three contributions do *not* compose as a naive product of
their independent speedups:

- **C-CEILING bounds everything from above.** Pruning tokens that are
  outside the ceiling's fixed-fraction term can't push E2E past
  `1/fixed_frac`. 1.51V + 1.51R running together on short-bucket
  VideoMME 8 f cannot exceed the short-bucket ceiling of ~1.76 ×, no
  matter how aggressive the kr.
- **C-VISION × C-PERSIST do not multiply.** Vision-tower pruning
  changes *first-pass* latency; persistent-KV reuse changes
  *follow-up* latency. The first pays prefill, the second skips it.
  They stack across *queries*, not inside a single query.
- **C-CEILING × C-VISION shares the vision axis.** The V_share term
  in `1/(1 − V_share × V_red)` is the *same V* as the V in the general
  ceiling. Stacking re-uses the same budget — you can't spend it twice.
- **The EXP10 n=60 composition audit sits at the ceiling, not above it.**
  Composition of 1.51R prefill-pruning × 1.51V vision-pruning lands at
  1.042 × E2E, ceiling-matched to the predicted LLM-side composition bound — a
  preregistered NULL on "stacking beats the ceiling" and an
  EARNED on the ceiling law itself.

The honest framing: we have three contributions that each characterize a
*different* bound, and those bounds share terms. The product of their
best-case multipliers is not an achievable target; the ceiling that uses
their combined V_share / V_red / fixed-fraction terms *is*.

## Negative results and boundaries (visible, not buried)

A reviewer who believes only the positive claims has not read the paper.
These are the nulls and boundaries we have earned; they shape the claim
boundary as much as the positives:

- **1.51R own-axis null at the pre-release reference kr.** At `kr_R=0.50` on
  Gemma 4-E4B-4bit VideoMME 8 f dev n=30, prefill-pruning alone yields
  `e2e=1.00×`, `gen=1.01×`. The 1.51R speedup in the main body comes
  from `kr=0.10` with a different aggregate-accuracy story.
- **EXP10 n=60 composition audit: preregistered NULL** on "stacking
  beats the ceiling." The observed 1.042 × E2E is ceiling-matched, not
  super-ceiling. (This is a positive result on the *ceiling law*, and a
  null on stack-beats-ceiling.)
- **1.29 codec-native sparse retrofit: HARD-FALSIFIED (MAX-aggregation)
  → PLANNER-SUBSTITUTION LANDED (continuous-score + per-item calibration).** Sparse 8-frame
  after-ingest classification from native-rate H.264 metadata degenerates
  to 100 % NOVEL on every pair when aggregated by MAX (pilot
  2026-04-22, mean |Δ| = 53.8 pp vs pixel-diff proxy). The continuous-score
  redesign passes the 10 pp aggregate gate at 7.9 pp but fails the
  per-item gate at 16–25 pp. Reframed with per-item live-pixel
  calibration, the planner-accuracy probe matches dense on 30/30 VideoMME
  dev all-duration Qwen items with codec accuracy equal to dense accuracy
  (0.533) and zero parse failures; short dev+holdout n=20 also passes on the
  -5pp accuracy-loss boundary. This is local codec-native planner-substitution
  evidence, not a latency win: offline codec extraction totals 7290s.
- **1.30 Qwen session/streaming composition: CLOSED BOUNDARY RESULT
  2026-04-26.** The original bridge was a hard negative, but the
  dense-Q0 successor `1.30W` materially improves it: paired cold
  `0.561` / streaming `0.503` (`Δacc = −0.0585`) at `2.7869×`, with
  aggregate Q0 parity (`34/57` in both arms), `0` parse failures, and `0`
  degenerates. Wording discipline matters here: 1.30W is currently
  evidenced as **dense-Q0 admission plus the existing session-reuse
  follow-up path**, not yet as proven follow-up pruning, because prompt
  reuse may bypass most follow-up image work. The composition is still
  not promoted: every remaining loss is follow-up-only, and the
  `>=3.0×` rescue floor is structurally unreachable under the current
  3-query protocol because dense Q0 alone already exceeds the target
  wall-clock budget. Root-cause decomposition remains valid, and the
  oracle upper bound from `1.30X` proves the lane is not dead in
  principle, but `1.30Z` and `1.30AB` then falsify every tested long-Q0 keep
  rate from `0.67` through `0.90`. The new instrumentation makes the mechanism boundary quantitative:
  `streaming_follow_up_vision_pruning_active_fraction = 0.0` and
  `streaming_follow_up_all_image_tokens_reused_fraction = 1.0` on the
  long-bucket follow-ups. The current 1.30 family is therefore a
  **Q0 admission + K-cache reuse** story, not a follow-up-pruning story.
  High keep rates restore aggregate Q0 accuracy but still lose follow-up
  accuracy by ~19pp, so first-answer aggregate correctness is not sufficient
  to certify the reused state. The cache-invalidated `1.30AC` and instrumented
  `1.30AD` successors now close this as a negative composition boundary: both
  reach the same net aggregate loss through different any-paired-drift sets, and
  only cache reuse preserves the speed profile. The next meaningful
  continuation is direct cache-state instrumentation or optional `0.95`
  boundary cleanup, not a revival of `1.30AA` unchanged.
- **1.60 scroll/pan regime-boundary probe: closed as a VideoMME corpus
  limitation.** We re-audited the natural corpus on a 60-item VideoMME
  stratification across 8f/16f/32f and found 0/60 items above the relaxed
  `shifted_fraction >= 0.30` gate (max 0.125). The result does not certify
  C-VISION on scroll/pan; it says VideoMME does not contain that
  regime at measurable scale. A scroll/pan characterization now requires
  EgoSchema/EPIC-Kitchens/Ego4D or a labeled synthetic set.
- **Streaming axis #2b: regime-dependent negative evidence, not a vague caveat.**
  The paired affine-cache-warp ablation shows a short-regime positive, a
  medium-duration null, near-zero dose-response on VideoMME, and a clean
  reconciliation with local phase 1.60: VideoMME mostly lacks the sustained
  pan/scroll regime the mechanism was designed for.
- **Piecewise reuse: no matched wall-clock baseline.** The
  piecewise-reuse case study in the separate streaming work is a single-cell
  illustration, not a scale-out result. Appendix-bound; does not
  contribute to the headline multipliers.

## Streaming evidence: case-study vs scale-out lane (not interchangeable)

Candidate C-STREAM is now a checked mixed bundle, not pending and not a fourth
headline. Do not promote numeric streaming rows unless they are backed by raw
paired outputs, cache-correctness smokes, source paths, and matched baselines;
the current bundle is useful because it includes both positive prefix-snapshot
rows and negative/baseline-pressure rows.

**Sparse exactness** is a separate artifact-bundle row, not part of the
deployment-multiplier bucket. Historical audits supported zero accuracy delta
on 1,937 sparse-sampled Qwen items, but direct byte-identical raw-paired
verification covered 513 items. Do not write
"byte-identical on 1,937" unless the validated bundle re-exports or reruns the missing
raw paired rows.

**Case-study** (single-cell illustrations, no paired baseline, or no
matched wall-clock): piecewise reuse; individual streaming anecdotes
without the paired sparse-benchmark comparison. These are appendix-bound
and do not contribute to the headline — the paper does not present a
case-study multiplier as evidence for a scale-out claim.

## Current Narrow Claim Boundary

We claim, with current evidence:

- training-free temporal feature reuse is a real, benchmark-validatable
  mechanism on our local Qwen 2.5-VL MLX stack
- the base policy family `max_abs(8,32) static+shifted age=4`
  **passes N=30 MVBench motion holdout** (cached=0.600@4.06, Pareto
  win vs dense-6; clean tree). A sticky_window=4 refinement reaches
  0.633@4.49 (ties dense-8 at 56% budget; dirty-tree, supplementary)
- the same base policy ties dense-8 on **TOMATO motion holdout at
  N=30** (0.333@3.55 = dense-8 at 44% budget; clean tree, commit
  42b06eb). Low-accuracy regime but Pareto relationship holds.
- naive mean-diff + no-refresh is too blunt on temporally concentrated
  evidence; `max_abs` statistic + bounded staleness recovers ground
- sticky-dynamic helps on MVBench holdout (+1 item) but hurts TOMATO
  dev; the explanatory variable is "placement of refresh in time,"
  not quantity

We do NOT claim:

- real sparse execution wins from the current Track A path
- measured speedup, FLOP reduction, or memory savings against FastV,
  CoPE-VideoLM, CodecSight, FrameFusion, or any adjacent method
- state-of-the-art benchmark accuracy or efficiency
- end-to-end gains from stacked compression arithmetic
- robotics inner-loop safety or real-time guarantees
- AI-native codecs as a near-term deliverable
- codec or pixel signals as semantic saliency or task-importance oracles

## Candidate C-STREAM (not applications / support)

Treat native-rate streaming as the scale-out lane for anti-recomputation, not
as decorative applications support. The local mechanism stack and future
streaming bundle occupy disjoint regimes by design:

| Axis                  | local mechanism stack                 | candidate streaming bundle                                          |
|-----------------------|--------------------------------------------|------------------------------------------------------------|
| Model size            | 4 B-class / 7B local, mostly quantized     | 26B-class scale-out rows plus local artifacts |
| Protocol              | sparse-sampled benchmark QA                | native-rate streaming / live deployment |
| Eval regime           | N = 30 / 60 holdout, paired, thermally controlled | checked raw paired rows and matched fixed-evidence baselines, still mixed |
| Classifier            | pixel-diff proxy on sampled decoded frames | MV/residual side-channels, event windows, prefix snapshots |
| Focus                 | mechanism isolation, prereg falsification  | full stack and deployment-style state reuse |
| Strongest numbers     | 1.113× VideoMME 8 f holdout; Gemma 32f short 1.316×; adaptive C-PERSIST 0/93 + many-turn stress | prefix-snapshot 8f/32f positive small-N; exactness export bounded to 1,937 zero-delta / 513 byte-identical |

The shared frame is **C-CEILING** (`1/(fixed + (1−fixed)/s)` on any
stage-bounded acceleration, including the vision-axis analog
`1/(1 − V_share × V_red)`) and a shared definition of
**attention-propagation drift** as the fidelity mechanism — NOT
positional-encoding drift. The local stack proves the mechanism at
small scale under strict prereg/falsification discipline; the separate
scale-out lane now reports checked mixed evidence only with its cache,
baseline, and source-manifest caveats attached. The paper reports the
**labeled evidence union** under a single analytical theory, with honest
accounting of where each number came from.

Weak streaming case-study claims without matched baselines (e.g.
single-cell streaming anecdotes) are **appendix-bound** — they do not
appear in the main body unless the paired baseline is also reported.

Bridge experiments we explicitly do NOT claim as landed in
codec-through locally:

- streaming-protocol fidelity reproduction of the pre-release N = 60 line: phase
  1.30 speedup landed locally on Qwen, but fidelity falsified the
  preregistered gate; root-cause decomposition now localizes the
  short-scout loss primarily to the V-only Q0 pruning leg, so the bridge
  depends on a better-certified/adaptive V admission policy rather than another
  blind stack run
- codec-native streaming-decoder integration for 1.29; the local
  planner-substitution bridge now survives both calibration-mode and
  calibration-source ablations, but the offline extraction path is still not a
  systems win
- broad sparse-backend coverage beyond the bounded measured sparse-vision
  envelope
- broader cross-architecture C-VISION coverage beyond the matched Qwen
  VideoMME point

These are the largest outstanding bridges between local mechanism evidence and
future scale-out claims; the three contributions above stand *without* them.

## Reviewer-Facing Limitations (shared fidelity vocabulary)

These are the caveats a reviewer will check. Per the pre-release source's
revised pre-release source §8 and codex 2026-04-16 review, the paper must state:

1. **Architecture-conditioned reuse fidelity is a spectrum**: on
   windowed-attention-heavy ViTs (Qwen 2.5-VL: 28 of 32 layers
   windowed), cached features are byte-identical to fresh on the
   local identity controls and high-stability on the transferred
   Planner 2.0 cells. On Gemma 4 SigLIP (all-global), the local
   second-architecture holdout is now **benchmark-conditional**:
   TOMATO motion N=30 lands at `0.933` strict agreement with no
   accuracy gap, while MVBench motion N=30 lands at only `0.733`
   strict agreement with the same `0.200` dense/cached accuracy.
   However, per the pre-release source §2.7, InternVL3 (also all-global) still yields
   95% strict agreement and +3.3% accuracy delta — so the claim is
   NOT a clean binary. Output stability is conditioned by attention
   topology, benchmark/query manifold, and pretraining. We must NOT
   say "exact" beyond Qwen-family models, and we also should not say
   "all-global universally implies quality loss."
2. **Thinking amplifies divergence**: on models with chain-of-thought
   (Gemma 4 thinking-on), small embedding differences cascade through
   reasoning chains, dropping strict agreement. This interaction is
   documented, not solved.
3. **VideoMME at 32 frames vs competitors' 64-256**: our evaluation
   budget is lower than some adjacent work. Frame-count scaling study
   is noted as future work.
4. **Pixel diff is still the default proxy, but codec-native evidence now
   exists without a calibration caveat on the local slices we ran**: the
   latest 1.29 results show why the bridge is hard. MAX-over-span sparse
   sampling degenerates to all-NOVEL, but continuous codec scores match dense
   choices on VideoMME dev all-duration \(n=30\), and that row is unchanged
   under both pooled/per-item threshold fitting and live-pixel/artifact
   target-share calibration ablations. This supports a codec-native
   planner-substitution row; it still does **not** support a latency claim
   because the current extraction path is offline and too slow.
5. **Composition remains projected**: temporal × KV-compression
   composition ratios are projected from independent-layer
   assumptions, not measured end-to-end.
6. **Per-frame binary decision**: our mechanism cannot prune WITHIN
   novel frames. On all-dynamic content, temporal caching provides
   near-zero benefit. This is a fundamental limitation, not a
   policy gap.
7. **Drift language discipline — attention-propagation drift, not
   PE drift.** The pre-release source attributes the refresh requirement
   to *attention-context* drift (attention weights at a given key
   position evolve ~0.01/frame as the query set shifts), NOT
   positional-encoding drift. Our phase 1.49 refresh sweep shows that
   periodic re-encode *recovers* agreement but does not *isolate* which
   drift mechanism is load-bearing. Phase 1.57 (adjacent-frame ViT
   cosine) is a **lower-bound proxy** on the cache-substitute error via
   fresh-vs-fresh cosine — NOT a direct cache-substitute measurement;
   the 1.45/1.46 identity controls are the direct path. The new Gemma
   1.57 lane lands the **same directional result** on VideoMME long dev,
   but at much higher absolute STATIC cosine than Qwen
   (`0.769 → 0.807` vs Qwen long `0.545 → 0.592` at 8f → 32f). The
   paper must therefore frame drift as **architecture-conditioned**
   rather than as a universal collapse law, and must still say
   "attention-propagation drift" (or "attention-context drift") when
   citing the pre-release source and must NOT assert a positional-encoding mechanism absent
   a local PE-ablation. Re-encode at I-frames (what we do) addresses
   attention-propagation drift; temporal-RoPE key correction would
   address PE drift — they require different mitigations. See
   [`publishability-status.md`](publishability-status.md) §Attention-
   context-drift-vs-PE-drift for the Codex round-21 reconciliation.

## Broader Sparse-Backend Reporting Template

The local paper now has bounded measured sparse-vision evidence. When broader
sparse-backend or scale-out reporting lands, report:

| Metric | Content types | Unit |
|---|---|---|
| ViT encode time | per frame, per content type | ms/frame |
| Classifier time | per frame | ms/frame |
| E2E pipeline time | per content type × frame count | seconds |
| ViT-only speedup | per content type × frame count | × |
| E2E speedup | per content type × frame count | × |
| FPS | per content type × frame count | frames/sec |
| Peak memory | per model size | GB |

Content types: talking-head, surveillance, FPV/egomotion (matching
the source table structure). Report ViT-only AND E2E separately; do NOT
use feature-replay timing as the main sparse-execution claim.

## Emerging Mechanistic Theory (2026-04-16)

The best current explanatory variable for cached-vs-dense behavior is
**budget placement over time**. Two policies with similar effective
fresh budget can behave very differently if one spends fresh tokens
around the decisive event and the other spends them in the wrong part
of the clip. Evidence pointers:

- phase 1.26 (sticky-dynamic adds refresh quantity but not helpful
  placement) strictly hurt TOMATO motion dev
- phase 1.28 (same policy at 16 frames vs 8) saturated at 0.667 on
  MVBench holdout — extra frames without smarter placement didn't help
- phase 1.16 cross-benchmark transfer was asymmetric, suggesting
  content-class-dependent placement mattered

See [docs/methodology/temporal-coverage-metrics.md](../docs/methodology/temporal-coverage-metrics.md)
for the formal placement metrics that phase 1.31 (failure predictor)
will exercise first.

## Why This Project Matters

Candidate line worth keeping:

> The codec already knows what changed. Stop re-encoding what didn't.

First-page paper language should keep the line's energy while qualifying it:
today's sparse-QA planner mostly uses pixel diff; phase 1.29 is local
codec-native planner-substitution evidence; decoder-integrated codec-speed
evidence remains future work. The stronger claim is not "we already built the
machine codec." It is "we measured which cross-layer temporal signals a frozen
VLM runtime can use, and the failures define requirements for future media."

The systems-engineering thesis:

- modern codecs already expose cheap signals about novelty, motion, and
  reference structure
- current VLM pipelines often ignore those signals and pay dense compute
  anyway
- part of the opportunity is not inventing new model internals first,
  but recovering cross-layer wins that existing systems left on the
  table
- denominator discipline is part of the contribution: the paper should be fun
  because the waste is visible, not because the speedups are multiplied past
  their measured regime

Framing to keep distinct from adjacent work:

- classical codecs are hand-designed predictive programs shaped by
  hardware constraints and perceptual objectives
- machine-consumption pipelines may want to reuse some of those ideas,
  but not inherit the human-vision objective blindly
- unchanged content is only the first case; predictably changed content
  motivates motion-conditioned, pose-aware, object/state, and multi-reference
  routing, all still future evidence here

## Comparison Boundary

What adjacent work already shows (see
[docs/literature-map-2026-04-16.md](../docs/literature-map-2026-04-16.md)
and [docs/related-work-table.md](../docs/related-work-table.md)):

- **CodecSight** owns the generic "codec metadata accelerates streaming
  VLM inference" systems thesis.
- **CoPE-VideoLM** owns the trained codec-native representation thesis,
  including "buy more frames per compute."
- **FastV / VisionZip / SparseVLM / VScan / FastVID / FrameFusion** own
  intra-frame or decoder-internal token reduction.
- **StreamingVLM / StreamMem / LiveVLM** own long-horizon KV memory.
- **TurboQuant / PolarQuant** own bits-per-cache-entry quantization.

What this repo is trying to show:

- how far a training-free reuse path can go before architecture changes
- how to separate answer-stability evidence from true skipped compute
- which cheap routing signals are useful before we pay for deeper model
  changes
- that agreement alone is not enough: the method needs a
  quality-versus-reuse story that stays honest when dense itself is weak
  on a slice

The paper slot is the intersection: training-free × temporal axis ×
temporal-reasoning benchmarks × MLX-local × (future) real measured
skipped compute.

## Likely Contribution Stack

Near-term paper path:

- honest reproduction of the pre-release source controls and benchmark lane on
  Apple Silicon (mostly done; see `docs/reproduction-status.md`)
- benchmark-native diagnosis of where same-position reuse fails and why
- a stronger training-free planner: phase 1.21 MVBench N=30 **PASSED**
  (base policy 0.600@4.06 Pareto-wins dense-6; clean tree). Phase
  1.20 TOMATO N=30 also **PASSED** (0.333@3.55 ties dense-8 at 44%
  budget; clean tree, commit 42b06eb).
- budget-placement instrumentation + failure predictor (phase 1.31 +
  temporal-coverage-metrics doc)
- matched dense frame-budget baselines, plus novelty-ranked dense as a local
  diagnostic until phase 1.34 raw outputs are checked in, and event-window oracle
  (phase 1.35)
- measured sparse-vision timing with broader sparse-backend and sparse LM
  prefill coverage still open

Follow-on systems work (belongs in the one-paper discussion, NOT
a separate systems paper per the round-17 reframe):

- changed-window sparse execution
- task-aware media policies
- screen-content specialization

## Future Horizons To Track Carefully

These are worth discussing, but should stay clearly labeled as future
work until local evidence exists:

Closest to current evidence:

- compute-denial or novelty-amplification robustness evaluation
- multi-reference and IMU-assisted stabilization
- changed-query attention after changed-window execution
- **training / fine-tuning acceleration via pre-LLM pruning and
  pre-encoder temporal redundancy compression.** Our current inference-
  time findings suggest two plausible training-time opportunities:
  (1) pre-LLM visual token pruning, which should reduce forward,
  backward, and activation-memory costs during multimodal fine-tuning;
  and (2) temporal redundancy compression before the expensive
  transformer stack. By contrast, **post-ViT feature caching does not
  directly transfer to end-to-end training when the vision encoder is
  trainable** because reused cached features break or approximate the
  gradient path. A gradient-faithful training formulation for
  temporal reuse remains open future work. Adjacent precedents:
  Run-Length Tokenization (arxiv id=b1ggjW00NI, 30% faster fine-tuning,
  >100% at 30 FPS in some settings), ToMe (arXiv:2210.09461,
  training-throughput gains including video), DynamicViT
  (arxiv id=jB0Nlbwlybm), EViT (arxiv id=BjyvwnXXVn_).
- **calibrated selective recompute / risk-triggered retry ladder.**
  Instead of spending dense compute on every item, the system would
  run a cheap cached or pruned pass first, estimate instance-level
  risk from answer margin, parse-instability, cheap-vs-visual
  disagreement, and temporal-coverage signals, and only escalate to
  denser visual processing when predicted failure risk is high.
  Because multimodal confidence is often miscalibrated, this must be
  treated as a calibration-and-policy problem rather than a raw
  logit-threshold trick. Prerequisites: phase 1.31 failure-predictor
  analysis lands, answer-margin features are calibrated, and a
  selective-risk-vs-compute evaluation is defined. References:
  CALM (openreview id=uLYc4L3C81A) for early-exit language models,
  ReCoVERR (ACL 2024.findings-acl.767) for VLM low-confidence
  evidence-gathering, CAP (openreview id=DA1ELJTudh) for per-instance
  abstention policy, and calibration warnings for MLLMs
  (ACL 2025.coling-main.208, openreview id=d8WMoi571f). **Do not say
  "confidence-conditioned" in paper claims until this evidence
  lands — see the explicit wording guardrail in claim-matrix.md.**

Medium-distance:

- machine-oriented codec sidecars
- **machine-oriented object / state delta sidecars** (phase 1.53
  deferred prereg, below). A natural extension is a sidecar that
  carries object/state deltas instead of dense repeated visual
  evidence: a full I-frame establishes entities and layout, while
  subsequent frames contribute only query-relevant changes such as
  movement, interaction, or state transitions. Could improve both
  efficiency and interpretability on temporal-reasoning tasks, but
  remains unvalidated locally. Likely helpful on object-interaction,
  moving-attribute, moving-direction, and state-change questions;
  likely harmful or insufficient on OCR, fine texture, small-object
  detail, or subtle appearance changes. Prompt growth can erase
  compute gains if the sidecar is not bounded and query-aware. This
  is a *new representation*, not a routing variant, and should not
  be silently folded into 1.29 (which should become the real
  codec-native classifier path instead — see below). Adjacent lines:
  VidCtx (openreview id=KNpbR9z8OU, arxiv 2412.17415) on training-free
  VideoQA with question-aware textual context; SG-VLM
  (arxiv 2509.11862) on scene-graph grounding for frozen-VLM VideoQA.
- screen-content specialization as a major branch

Far-distance:

- sensor-fusion timelines or world-state codecs. Treat "video for machines" as
  a synchronized state-update stream: RGB/luma context, depth/ToF summaries,
  event spikes, IMU/odometry, object tracks, camera pose, timestamps, and
  confidence. Start with synthetic sidecars and router-only fusion before
  claiming a new codec.
- AI-native codecs and hardware co-design. Future codecs should expose
  tensor-friendly active tiles, residual concentration, object/state deltas,
  uncertainty, and motion references directly to the model/runtime.
- domain rotations into video generation/world models and audio. These share
  the anti-recomputation shape but need their own evidence: generation should
  refresh around occlusion, entropy spikes, and new-object events; audio should
  treat onset, phoneme boundaries, speaker changes, and prosody as candidate
  refresh signals rather than assuming low energy means low relevance.

## Proxy Chain To State Explicitly

The current training-free planner is a proxy chain:

- pixel-space RGB differencing is standing in for decoded-frame change
- current `STATIC / SHIFTED / NOVEL` planner labels are therefore proxy
  labels under RGB differencing, not literal codec-motion truth
- decoded-frame change is standing in for codec-side motion and
  residual semantics
- codec-side motion and residual semantics are standing in for
  latent-feature reuse decisions

Phase 1.29 (MV/CBF-derived signal path via PyAV/FFmpeg metadata) is the
current bridge from pixel-diff proxy to real codec signals. The current
evidence is split by aggregation rule: MAX-over-span sparse aggregation is
hard-falsified, while continuous codec scores match dense choices on VideoMME
dev all-duration \(n=30\) and survive both calibration-mode and
calibration-source ablations on the local slices we ran. Paper language can
now cite 1.29 as **local codec-native planner-substitution evidence**, but it
should not cite 1.29 as a latency win. The offline extraction path took 7290s
on dev n=30; speed requires streaming decoder integration or cached metadata.

Phase 1.36 (2026-04-17) quantified the pixel-diff ↔ ViT-feature
lower bound: per-block Pearson r is **+0.233 on TOMATO (MEAN)** and
**+0.504 on MVBench (CPF)**. The statistic ranking is
content-dependent, and the best routing statistic from the Planner 2.0
ablation (MAX_ABS) is NOT the best point predictor on either
benchmark. Routing cares about ordering for top-k budget allocation;
point prediction cares about magnitude matching. These are separate
objectives, and the paper should not conflate them.

## Adjacent Lineage: Approximate Computing

Temporal feature reuse sits in a broader tradition of *approximate
computing* (Rinard's loop-perforation, task-skipping, precision-
scaling) where the assumption is that end-task quality is not a
point function of full-precision compute: it's a distribution, and
savings are recovered by skipping work on inputs the task is robust
to. Our mechanism is a temporal analog: for a video clip, many
frame regions change little enough that their ViT features can be
reused without the downstream answer changing. The paper should
cite this lineage explicitly when framing the method — it clarifies
that we are not claiming lossless compute reduction, we are claiming
*answer-stability-preserving* reduction, which is the standard
approximate-computing contract.

This also constrains the claim structure: our correctness criterion
is answer agreement with the dense baseline on a task-defined
evaluation, NOT per-token feature identity (except on
windowed-attention-heavy architectures where feature identity is a
byproduct of the attention topology).

## Machine-First Codec Roadmap

Classical codecs (H.264/H.265, VVC, AV1) optimize for the
human-visual-system rate-distortion objective. A growing body of
standards work targets machine consumption instead:

- **MPEG-AI Part 2 / VCM** (Video Coding for Machines): ISO/IEC DIS
  23888-2, Draft International Standard in enquiry stage 40.20 as of the
  current ISO page, aiming to define bitstream syntax, decoding, and descriptors
  optimized for downstream machine tasks, not human viewing.
- **JPEG AI**: learned image codec standardization activity with
  machine-task rate-distortion as a first-class objective.
- **DCVC-RT** (Deep Contextual Video Compression — Real-Time): the
  current practical SOTA for learned video codecs with fast decoding
  on consumer GPUs.

These are relevant as future-work anchors, not direct dependencies.
Our pixel-diff proxy (phase 1.19+) and codec-native MV/residual path (phase 1.29) both
target the *existing* H.264/H.265 signal surface because that is
what ships on device today. A machine-first codec line would lift
the ceiling on proxy quality (see phase 1.36 Pearson lower bound)
by letting the encoder surface task-relevant change metadata
directly, instead of us reverse-engineering it from pixel deltas.
The paper discussion should note this without claiming we've bridged
the gap.

## Writing Discipline

- every paper claim should link back to local evidence or a primary
  source
- future-work sections should say why a direction follows from observed
  evidence, not just why it sounds interesting
- negative results belong in the paper story when they narrow the
  design space in a useful way. The queryable ledger is in
  [research/falsified-hypotheses.md](../research/falsified-hypotheses.md).
- when citing our own numbers, always state the N of the slice and
  whether the evaluation was single-shot or transfer-discovered
