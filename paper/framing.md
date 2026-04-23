# Paper Framing

This file tracks the paper story, contribution boundary, and anti-claims.

Paper-facing drafts (what a reviewer will actually read):

- [`paper/abstract.md`](abstract.md) — one-page three-contributions
  abstract (C-CEILING / C-PERSIST / C-VISION first-class;
  Lane A as mechanism backbone; Sam as deployment-scale evidence)
- [`paper/intro.md`](intro.md) — paper-facing introduction with the
  same structure

It is NOT the place for raw experimental detail. Evidence lives in:

- [docs/reproduction-status.md](../docs/reproduction-status.md) — per-claim
  whitepaper reproduction state
- [docs/literature-map-2026-04-16.md](../docs/literature-map-2026-04-16.md) —
  positioning map against CodecSight / CoPE / FastV / FrameFusion / etc.
- [docs/related-work-table.md](../docs/related-work-table.md) — paper-facing
  method comparison table with verified numbers
- [docs/research-strategy-post-codecsight.md](../docs/research-strategy-post-codecsight.md)
  — active research strategy with evidence-level table per claim
- [research/experiments/2026/](../research/experiments/2026/) — phase-by-phase
  results
- [research/falsified-hypotheses.md](../research/falsified-hypotheses.md) —
  what the evidence has ruled out

Last material update: 2026-04-23 (Qwen 1.51V cross-architecture probe passed
at matched \(L=2\), \(kr_V=0.50\), upgrading C-VISION from
single-architecture to two-architecture mechanism evidence; 1.57
feature-drift geometry reproduced on holdout at 8f/16f; EXP10 pooled n=60
H\_stack remains a ceiling-matched NULL; 1.29 MAX-over-span codec-native pilot
remains hard-falsified and the continuous-score redesign remains aggregate-only
partial pass, off the paper's critical path unless reframed; C-VISION now
reads as 6 core ceiling scatter points with 9 rendered points total once the
3 holdouts, the pooled null, and the matched Qwen point are included).

## Current Manuscript Position (2026-04-23)

The manuscript should be centered on one anti-recomputation story with three
explicit regimes:

- **C-VISION** for measured first-pass gains on fresh videos
- **C-PERSIST** for the much larger after-ingest follow-up-query wins
- **Qwen routing** for mechanism and boundary evidence

Those regimes matter for different reasons. C-VISION shows that frozen
first-pass pruning already buys real wall-clock savings, but only in proportion
to the vision share that the dense path actually owns. C-PERSIST is where the
largest local multipliers live, because once a video has already been ingested,
the next question can reuse the expensive prefix instead of rebuilding it.
Qwen routing is the cleanest evidence for why any of this works: novelty
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

If the codec-native bridge lands cleanly, the mechanism wording can move toward
``codec-guided.'' Until then, keep the wording more careful: codec-inspired or
pixel-diff proxy for codec-guided.

The paper-grade story is training-free anti-recomputation with measured
first-pass Gemma gains, large after-ingest follow-up wins, and Qwen routing
evidence that explains the mechanism boundary.
For the per-claim breakdown, see
[`paper/claim-matrix.md`](claim-matrix.md) and
[docs/literature-map-2026-04-16.md § Current evidence level (2026-04-16)](../docs/literature-map-2026-04-16.md).

## Three Major Contributions (2026-04-23 status)

Per Codex rounds 25–26 (2026-04-21), the paper spine is these three
first-class contributions — ordered ahead of the Qwen routing lane,
which is reframed as the mechanism-validation backbone + null ledger
(claims 1/2/6/9 earned + halo-veto 1.37B retired + 1.51R VideoMME
duration-conditional partial reproduction + 1.55D infra-falsified):

1. **C-CEILING (claim 13): Arithmetic ceiling model for token-pruning
   wall-clock speedup.** Predicts E2E speedup within ≤5.2% across 7
   regime dimensions on Gemma 4-E4B-4bit (8/32 frame counts × benchmark
   × keep-rate × anchor arm). Formula: `e2e ≤ 1/(fixed_frac + (1 −
   fixed_frac)/s)`. Standalone analytical contribution; validated in the
   1.51R reproduction lane and further extended by 1.51V to a
   vision-axis analog `1/(1 − V_share × V_red)`.

2. **C-PERSIST (claim 14): Cross-architectural persistent-KV
   safe-deployment envelope.** All persistent-KV claims in this paper
   are **after-ingest / follow-up-query** numbers: the user pays the
   full first-query prefill once, subsequent questions on the *same
   video* reuse the KV and return in sub-second time. These are not
   "any-fresh-video" latencies. 7B Qwen 2.5-VL-4bit stays inside the
   safe envelope through ≤16f / ≤6.5k prefill tokens, with a clean 16f
   point (Δacc=0) and a slightly worse but still safe 8f point
   (Δacc=−0.048); 3B at ≤36f / ≤14.5k prefill sits on a tolerated
   Δacc=−0.19 plateau (not clean, bounded). Basin-onset depth scales ~1.6× with parameter
   count; basin geometry (non-letter attractor emergence) is
   cross-architectural; sampler-side intervention is
   architecture-conditional (insufficient at 7B basin at 20f AND 40f;
   partial-only at 3B basin at 40f — disperses to pre-basin plateau,
   not to baseline). Safe-Deployment Regime table in
   [`paper/claim-matrix.md`](claim-matrix.md) provides paper-grade
   practitioner guidance; safety-boundary result in its own right.

3. **C-VISION (claim 15): Vision-tower pruning transfers at `L=2`
   `kr_V=0.50` across Gemma 4-E4B-4bit and Qwen 2.5-VL-7B-4bit, with
   first-pass gains governed by the scatter-back ceiling
   `1/(1 − V_share × V_red)`.**
   Dev n=30 headlines are TOMATO **1.24×**, MVBench **1.21×**, and
   VideoMME **1.08×** (8f) / **1.12×** (16f). Holdout status is now
   differentiated rather than missing: VideoMME 8f is **clean** at
   **1.113×** with zero aggregate accuracy delta; MVBench 8f is
   **advisory** at **1.407×** with a scheduler-scale decode note; and
   TOMATO 8f is **earned-advisory** at **1.194×** from the upstream
   session-5 rerun. The matched Qwen VideoMME 8f cross-arch point lands
   at **1.044× observed vs 1.043× predicted**, with smaller absolute lift
   because Qwen's dense vision share is only ~10\%. The mechanism is
   stable; the exact magnitude remains regime-dependent because `V_share`
   and `V_red` are benchmark-, architecture-, and protocol-sensitive.

These three claims align on a common analytical frame: **share ×
reduction → `1/(1 − share × reduction)` ceiling**, with
architecture-specific and regime-specific bounds characterized. The
paper presents these as three independent instantiations of a unified
efficiency-ceiling theory: C-CEILING (LLM-generate axis), C-VISION
(vision-tower axis), and the LLM-side analog for H_stack. C-PERSIST
adds the orthogonal fidelity-floor axis (where the ceiling falls apart
entirely under cache reuse).

**Venue targeting implication:** the combination of C-PERSIST (safety
boundary, cross-architectural) + C-VISION (three-benchmark Gemma
headline cells plus a matched Qwen transfer point) + C-CEILING
(analytical framework) is paper-grade for an efficiency-focused venue
(NeurIPS / ICML efficiency workshop or ICLR Tiny Papers). The systems
angle is real, but a systems venue like MLSys still wants more: a
measured sparse backend, a clean systems baseline such as screenshot
polling, and a broader streaming evaluation. Main-track readiness now
depends on broader asks: (a) one measured sparse-path end-to-end delta,
(b) a cleaner local bridge into the streaming / deployment regime,
(c) a 1.29 local codec-native benchmark slice, and (d) a scroll/pan or
egomotion regime-boundary probe on a corpus that actually contains that
motion regime.

## Protocol matters — three non-interchangeable evaluation regimes

Every number in this paper lives inside one of three protocols, and the
protocols are not mutually substitutable. Conflating them is the easiest
way to overclaim.

1. **Sparse after-ingest QA.** The VideoMME / MVBench / TOMATO
   benchmarks as we run them: decode N frames once, ask a question,
   score. This is what C-VISION and the 1.51R partial reproduction
   measure. It is *not* streaming, and it is *not* live camera.
2. **Native-rate streaming.** Frames arrive at source rate; the model
   must keep up. Sam's 4.2–4.5× E2E and ~50× streaming-dominant
   multipliers live here. The fixed fraction of the pipeline that is
   decode + ingest is much larger, so the ceiling law
   `1/(fixed + (1−fixed)/s)` bites differently than in (1).
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
- **The EXP10 n=60 H_stack result sits at the ceiling, not above it.**
  Composition of 1.51R prefill-pruning × 1.51V vision-pruning lands at
  1.064 × E2E, ceiling-matched to the predicted H_stack bound — a
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

- **1.51R own-axis null at Sam's reference kr.** At `kr_R=0.50` on
  Gemma 4-E4B-4bit VideoMME 8 f dev n=30, prefill-pruning alone yields
  `e2e=1.00×`, `gen=1.01×`. The 1.51R speedup in the main body comes
  from `kr=0.10` with a different aggregate-accuracy story.
- **EXP10 n=60 H_stack composition: preregistered NULL** on "stacking
  beats the ceiling." The observed 1.064 × E2E is ceiling-matched, not
  super-ceiling. (This is a positive result on the *ceiling law*, and a
  null on stack-beats-ceiling.)
- **1.29 codec-native sparse retrofit: HARD-FALSIFIED (MAX-aggregation)
  → PARTIAL PASS (continuous-score, aggregate only).** Sparse 8-frame
  after-ingest classification from native-rate H.264 metadata degenerates
  to 100 % NOVEL on every pair when aggregated by MAX (pilot
  2026-04-22, mean |Δ| = 53.8 pp vs pixel-diff proxy). The continuous-score
  redesign passes the 10 pp aggregate gate at 7.9 pp but fails the
  per-item gate at 16–25 pp; codec and pixel-diff disagree on *where*
  motion lives within an item, not just on *how much*. Off the paper's
  critical path unless reframed.
- **1.60 scroll/pan regime-boundary probe: closed as a VideoMME corpus
  limitation.** We re-audited the natural corpus on a 60-item VideoMME
  stratification across 8f/16f/32f and found 0/60 items above the relaxed
  `shifted_fraction >= 0.30` gate (max 0.125). The result does not say
  C-VISION is safe on scroll/pan; it says VideoMME does not contain that
  regime at measurable scale. A scroll/pan characterization now requires
  EgoSchema/EPIC-Kitchens/Ego4D or a labeled synthetic set.
- **Sam axis #2b: mixed / null** on a subset of streaming cells. Not
  all of Sam's multipliers generalize to every content type; the
  mixed/null cells are reported alongside the positive ones, not
  averaged away.
- **Sam piecewise reuse: no matched wall-clock baseline.** The
  piecewise-reuse case study in codec-through-sam is a single-cell
  illustration, not a deployment-scale result. Appendix-bound; does not
  contribute to the headline multipliers.

## Sam: case-study vs deployment-scale (not interchangeable)

Within codec-through-sam the numbers fall into two categories and they
carry different evidential weight:

**Deployment-scale** (main-body multipliers, paired baselines,
1,937-item corpus where applicable): streaming E2E 4.2–4.5 ×; ViT-only
13 ×; streaming-dominant-pipeline ~50 ×; live-camera ViT 5–300 ×;
persistent-KV follow-up median 0.8 s. These stay in the main body,
clearly attributed to Sam, with their regime explicitly named.

**Case-study** (single-cell illustrations, no paired baseline, or no
matched wall-clock): piecewise reuse; individual streaming anecdotes
without the paired sparse-benchmark comparison. These are appendix-bound
and do not contribute to the headline — the paper does not present a
case-study multiplier as evidence for a deployment-scale claim.

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

## Sam as deployment-scale evidence (not "applications / support")

Treat codec-through-sam as deployment-scale evidence for C-PERSIST and
C-VISION, not as decorative applications support. The two repos occupy disjoint
regimes by design:

| Axis                  | codec-through (this paper)                 | codec-through-sam                                          |
|-----------------------|--------------------------------------------|------------------------------------------------------------|
| Model size            | 4 B-class, 4-bit quantized                 | 26 B-class                                                  |
| Protocol              | sparse-sampled benchmark                   | real streaming / deployment                                 |
| Eval regime           | N = 30 / 60 holdout, paired, thermally controlled | 1,937 items, live decode in loop                    |
| Classifier            | pixel-diff proxy (scoped future: 1.29 MV-only) | codec-native MV + CBF                                   |
| Focus                 | mechanism isolation, prereg falsification  | full stack, composition, measured end-to-end multipliers    |
| Strongest numbers     | 1.08–1.24× E2E dev; 1.113× VideoMME 8 f holdout; sub-second follow-up inside safe envelope | 4.2–4.5× real-video E2E; 13× ViT; ~50× streaming dominant-pipeline; median 0.8 s follow-up; 5–300× live ViT |

The shared frame is **C-CEILING** (`1/(fixed + (1−fixed)/s)` on any
stage-bounded acceleration, including the vision-axis analog
`1/(1 − V_share × V_red)`) and a shared definition of
**attention-propagation drift** as the fidelity mechanism — NOT
positional-encoding drift. codec-through proves the mechanism at
small scale under strict prereg/falsification discipline; Sam proves
that the same mechanism, instantiated on the full stack in the right
regime, delivers product-scale multiplicative wins. The paper
reports the **evidence union** under a single analytical theory, with
honest accounting of where each number came from.

Weak streaming case-study claims without matched baselines (e.g.
single-cell streaming anecdotes) are **appendix-bound** — they do not
appear in the main body unless the paired baseline is also reported.

Bridge experiments we explicitly do NOT claim as landed in
codec-through locally:

- streaming-protocol reproduction of Sam's N = 60 line (phase 1.30
  preregistered, deferred pending EXP17/18 landing)
- codec-native benchmark evidence from 1.29 as a paper-grade local
  bridge; the pilots now exist, but MAX-over-span sparse sampling is
  hard-falsified and the continuous-score redesign is only an
  aggregate-level partial pass
- sparse-execution measured delta for claim 5 (Track B infra exists
  on dense; sparse path unwritten)
- cross-architecture C-VISION transfer (Qwen 2.5-VL at matched
  `L=?, kr=?`)

These are the four largest outstanding bridges between the repos; the
three contributions above stand *without* them.

## Reviewer-Facing Limitations (shared fidelity vocabulary with codec-through-sam)

These are the caveats a reviewer will check. Per sam's revised
whitepaper §8 and codex 2026-04-16 review, the paper must state:

1. **Architecture-conditioned reuse fidelity is a spectrum**: on
   windowed-attention-heavy ViTs (Qwen 2.5-VL: 28 of 32 layers
   windowed), cached features are byte-identical to fresh. On
   some all-global ViTs (Gemma 4 SigLIP), cached features are
   high-fidelity but non-identical. However, per sam §2.7, InternVL3
   (also all-global) still yields 95% strict agreement and +3.3%
   accuracy delta — so the claim is NOT a clean binary. Output
   stability is attention-topology-conditioned on a spectrum, and
   pretraining matters too. We must NOT say "exact" beyond
   Qwen-family models; we also should not say "approximate
   universally implies quality loss" for all-global encoders.
2. **Thinking amplifies divergence**: on models with chain-of-thought
   (Gemma 4 thinking-on), small embedding differences cascade through
   reasoning chains, dropping strict agreement. This interaction is
   documented, not solved.
3. **VideoMME at 32 frames vs competitors' 64-256**: our evaluation
   budget is lower than some adjacent work. Frame-count scaling study
   is noted as future work.
4. **Pixel diff is still a proxy**: we classify by pixel differencing,
   not actual codec MV+CBF metadata. The latest 1.29 pilots show why
   that bridge is hard: MAX-over-span sparse sampling degenerates to
   all-NOVEL, and continuous codec scores currently earn only an
   aggregate-level partial pass. Real codec metadata remains a future
   bridge, not current paper support.
5. **Composition remains projected**: temporal × KV-compression
   composition ratios are projected from independent-layer
   assumptions, not measured end-to-end.
6. **Per-frame binary decision**: our mechanism cannot prune WITHIN
   novel frames. On all-dynamic content, temporal caching provides
   near-zero benefit. This is a fundamental limitation, not a
   policy gap.
7. **Drift language discipline — attention-propagation drift, not
   PE drift.** Sam's whitepaper §234 attributes the refresh requirement
   to *attention-context* drift (attention weights at a given key
   position evolve ~0.01/frame as the query set shifts), NOT
   positional-encoding drift. Our phase 1.49 refresh sweep shows that
   periodic re-encode *recovers* agreement but does not *isolate* which
   drift mechanism is load-bearing. Phase 1.57 (adjacent-frame ViT
   cosine) is a **lower-bound proxy** on the cache-substitute error via
   fresh-vs-fresh cosine — NOT a direct cache-substitute measurement;
   the 1.45/1.46 identity controls are the direct path. The paper must
   say "attention-propagation drift" (or "attention-context drift") when
   citing Sam and must NOT assert a positional-encoding mechanism absent
   a local PE-ablation. Re-encode at I-frames (what we do) addresses
   attention-propagation drift; temporal-RoPE key correction would
   address PE drift — they require different mitigations. See
   [`publishability-status.md`](publishability-status.md) §Attention-
   context-drift-vs-PE-drift for the Codex round-21 reconciliation.

## Track B Reporting Template (from sam, for future use)

When Track B sparse execution lands, report:

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
sam's table structure). Report ViT-only AND E2E separately; do NOT
use feature-replay timing as the main Track B claim.

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

The systems-engineering thesis:

- modern codecs already expose cheap signals about novelty, motion, and
  reference structure
- current VLM pipelines often ignore those signals and pay dense compute
  anyway
- part of the opportunity is not inventing new model internals first,
  but recovering cross-layer wins that existing systems left on the
  table

Framing to keep distinct from adjacent work:

- classical codecs are hand-designed predictive programs shaped by
  hardware constraints and perceptual objectives
- machine-consumption pipelines may want to reuse some of those ideas,
  but not inherit the human-vision objective blindly

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

- honest reproduction of the whitepaper controls and benchmark lane on
  Apple Silicon (mostly done; see `docs/reproduction-status.md`)
- benchmark-native diagnosis of where same-position reuse fails and why
- a stronger training-free planner: phase 1.21 MVBench N=30 **PASSED**
  (base policy 0.600@4.06 Pareto-wins dense-6; clean tree). Phase
  1.20 TOMATO N=30 also **PASSED** (0.333@3.55 ties dense-8 at 44%
  budget; clean tree, commit 42b06eb).
- budget-placement instrumentation + failure predictor (phase 1.31 +
  temporal-coverage-metrics doc)
- matched dense frame-budget baselines PLUS novelty-ranked dense (phase
  1.34) and event-window oracle (phase 1.35)
- careful Track B timing only after sparse execution exists

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
  >100% at 30 FPS in some settings), ToMe (arxiv id=JroZRaRw7Eu,
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

- sensor-fusion timelines or world-state codecs
- AI-native codecs and hardware co-design

## Proxy Chain To State Explicitly

The current training-free planner is a proxy chain:

- pixel-space RGB differencing is standing in for decoded-frame change
- current `STATIC / SHIFTED / NOVEL` planner labels are therefore proxy
  labels under RGB differencing, not literal codec-motion truth
- decoded-frame change is standing in for codec-side motion and
  residual semantics
- codec-side motion and residual semantics are standing in for
  latent-feature reuse decisions

Phase 1.29 (MV-only signal path via PyAV) was the intended bridge from
pixel-diff proxy to real codec signals. The current evidence is mixed:
MAX-over-span sparse aggregation is hard-falsified and the
continuous-score redesign is only an aggregate-level partial pass.
Until a planner-facing or native-rate streaming version lands cleanly,
paper language should keep "proxy for codec motion" explicit.

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

- **MPEG-VCM** (Video Coding for Machines): specifies a codec
  bitstream whose decoder reconstructs a representation optimized
  for downstream machine tasks, not human viewing.
- **JPEG AI**: learned image codec standardization activity with
  machine-task rate-distortion as a first-class objective.
- **DCVC-RT** (Deep Contextual Video Compression — Real-Time): the
  current practical SOTA for learned video codecs with fast decoding
  on consumer GPUs.

These are relevant as future-work anchors, not direct dependencies.
Our pixel-diff proxy (phase 1.19+) and MV-only path (phase 1.29) both
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
