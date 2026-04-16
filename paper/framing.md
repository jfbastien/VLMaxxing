# Paper Framing

This file tracks the paper story, contribution boundary, and anti-claims.

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

Last material update: 2026-04-16 (post-CodecSight repositioning + first
credible held-out Pareto signal in phase 1.12.B).

## Candidate Paper Slot (target, not current claim)

> A training-free temporal routing method that TARGETS a better
> quality–compute Pareto frontier for video VLMs on temporal-reasoning
> tasks, when reuse is concentration-aware, age-bounded,
> architecture-aware, and backed by real skipped compute.

If phase 1.29 MV-only signal path lands: "codec-guided." If not:
"codec-inspired / pixel-diff proxy for codec-guided."

The current state is "paper-grade MVBench-local evidence, credible
method signal, not SOTA." Phase 1.21 N=30 holdout PASSED (base policy
0.600@4.06 Pareto-wins dense-6; sticky4 0.633@4.49 ties dense-8 at
56% budget). TOMATO N=30 + Track B + VideoMME still gate full paper.
For the per-claim breakdown, see
[`paper/claim-matrix.md`](claim-matrix.md) and
[docs/literature-map-2026-04-16.md § Current evidence level (2026-04-16)](../docs/literature-map-2026-04-16.md).

## Current Narrow Claim Boundary

We claim, with current evidence:

- training-free temporal feature reuse is a real, benchmark-validatable
  mechanism on our local Qwen 2.5-VL MLX stack
- the base policy family `max_abs(8,32) static+shifted age=4`
  **passes N=30 MVBench motion holdout** (cached=0.600@4.06, Pareto
  win vs dense-6; clean tree). A sticky_window=4 refinement reaches
  0.633@4.49 (ties dense-8 at 56% budget; dirty-tree, supplementary)
- the same base policy ties dense-8 on **TOMATO motion holdout at
  N=30** (0.333@3.55 = dense-8 at 44% budget; dirty-tree, pending
  clean rerun). Low-accuracy regime but Pareto relationship holds.
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

## Reviewer-Facing Limitations (import from sam, tightened)

These are the caveats a reviewer will check. Per sam's revised
whitepaper §8 and codex 2026-04-16 review, the paper must state:

1. **Architecture-dependent exactness**: on windowed-attention ViTs
   (Qwen 2.5-VL), cached features are byte-identical to fresh. On
   all-global-attention ViTs (Gemma 4 SigLIP), cached features are
   approximate. Output stability is architecture-conditioned, not
   universal. We must NOT say "exact" beyond Qwen-family models.
2. **Thinking amplifies divergence**: on models with chain-of-thought
   (Gemma 4 thinking-on), small embedding differences cascade through
   reasoning chains, dropping strict agreement. This interaction is
   documented, not solved.
3. **VideoMME at 32 frames vs competitors' 64-256**: our evaluation
   budget is lower than some adjacent work. Frame-count scaling study
   is noted as future work.
4. **Pixel diff is still a proxy**: we classify by pixel differencing,
   not actual codec MV+CBF metadata. Real codec metadata would be
   faster and more precise. Phase 1.29 (MV-only) is the bridge.
5. **Composition remains projected**: temporal × KV-compression
   composition ratios are projected from independent-layer
   assumptions, not measured end-to-end.
6. **Per-frame binary decision**: our mechanism cannot prune WITHIN
   novel frames. On all-dynamic content, temporal caching provides
   near-zero benefit. This is a fundamental limitation, not a
   policy gap.

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
  1.20 TOMATO N=30 also shows positive signal (0.333@3.55 ties
  dense-8 at 44% budget; dirty-tree, pending clean rerun).
- budget-placement instrumentation + failure predictor (phase 1.31 +
  temporal-coverage-metrics doc)
- matched dense frame-budget baselines PLUS novelty-ranked dense (phase
  1.34) and event-window oracle (phase 1.35)
- careful Track B timing only after sparse execution exists

Follow-on systems paper if evidence lands:

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

Medium-distance:

- machine-oriented codec sidecars
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

Phase 1.29 (MV-only signal path via PyAV) is the deployability bridge
from pixel-diff proxy to real codec signals. Until that phase lands,
paper language should keep "proxy for codec motion" explicit.

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
