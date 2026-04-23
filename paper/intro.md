---
date: 2026-04-21
parent: paper/framing.md
status: paper-facing draft introduction — three-contributions structure with Sam as deployment-scale evidence
---

# Introduction (codec-through-2, draft)

<!--
Internal: this intro is the paper-facing narrative counterpart to
`framing.md` (internal planning) and `abstract.md` (paper-opening). It
operationalizes the structural request from Codex round 25: stop
foregrounding Lane A as the center of gravity; make C-CEILING,
C-PERSIST, and C-VISION first-class; keep Qwen routing as
mechanism-validation backbone; move Sam from "applications/support"
to deployment-scale evidence.
-->

## 1. Setting: what the efficiency papers are quietly overstating

Token-pruning, frame-routing, and KV-cache reuse methods for video VLMs
routinely report multiplicative speedups on one component. Readers then
compound those numbers in their heads: "2× here, 1.5× there, about 3×
end-to-end." Those mental compositions are usually wrong, because

1. they ignore what fraction of wall-clock the accelerated stage
   actually owns on the model-size and frame-count regime that users
   deploy (small model, shorter context, commodity hardware), and
2. they understate the fidelity cost of cache reuse under realistic
   conversational / streaming workloads, where the accumulated drift is
   an attention-context phenomenon and not the positional-encoding
   drift the literature occasionally blames.

This paper is about what stays true when the arithmetic is honest.

## 2. Contributions

We have three.

### 2.1  C-CEILING — an arithmetic bound on token-pruning end-to-end gain

Any acceleration applied to only one stage of a pipeline is bounded by
that stage's wall-clock share. For token-pruning with per-stage speedup
`s` and stage share `(1 − fixed_frac)`,

> E2E ≤ 1 / (fixed_frac + (1 − fixed_frac) / s)

We validate this ceiling predictively, not post-hoc, across seven
regime dimensions on Gemma 4-E4B-4bit: 8-frame and 32-frame counts, two
benchmarks, three keep-rates, and two anchor arms. Observed and
predicted E2E agree within ≤ 5.2 % everywhere, and the ceiling is sharp
enough to *rule out* proposed compositions before they are run. A
vision-axis analog,

> E2E ≤ 1 / (1 − V_share × V_red),

governs C-VISION (below) and matches observed speedups within 2.7 pp
across four vision-axis cells plus a fifth stacked cell.

This is the paper's analytical contribution. It is also a diagnostic:
when a reported end-to-end gain exceeds the
fixed-stage ceiling, the denominator is wrong (usually thermal drift,
decode-path conflation, or unreported prefill caching).

### 2.2  C-PERSIST — a cross-architectural safe-deployment envelope for persistent KV

Reusing the first-query KV across subsequent questions on the *same*
video collapses follow-up latency into a conversational regime on
commodity hardware: after the first-query prefill is paid (cold), the
second and later questions on Qwen 2.5-VL-7B-4bit at ≤ 16 frames return
in sub-second time, zero accuracy loss, across 21 queries. The
envelope is architecturally bounded and characterized:

- **Qwen 2.5-VL-7B-4bit**: clean at ≤ 16 frames / ≤ 6.5 k prefill
  tokens (Δacc = 0). Soft transition at 18–20 frames into a
  non-letter-attractor basin (mixed `addCriterion` + garbage); saturated
  single-token attractor at ≤ 24 frames. The basin is
  sampler-invariant at both 20 f and 40 f; sampler intervention does
  not rescue it at 7 B.
- **Qwen 2.5-VL-3B-4bit**: tolerated Δacc = −0.19 plateau at ≤ 36
  frames / ≤ 14.5 k prefill — **not clean**, bounded. Basin onset at
  ~40 frames. At 3 B-40 f the basin is sampler-dispersible (4/14
  → 1/14) but returns only to the pre-basin plateau, not to baseline
  — sampler-invariance is an architecture-conditional property, not
  a universal rescue.
- **Basin-onset depth scales ~1.6× with parameter count** (7 B onset
  ~16–20 f; 3 B onset ~36–40 f). The basin geometry — non-letter
  attractor emergence, not a random letter flip — is cross-
  architectural and appears at 1/21 signature on all four probes.
- **Gemma 4-E4B-4bit** does not expose the persistent-KV path under
  the current mlx-vlm sliding-window driver semantics; this is an
  infrastructure limitation, not a fidelity result.

All persistent-KV numbers in this paper are **after-ingest /
follow-up-query** latencies; we explicitly do not claim sub-second
first-query latency on any fresh video.

### 2.3  C-VISION — training-free vision-tower pruning with a transferable operating point

Pruning the vision-tower's token stream at `L = 2` with keep-rate
`0.50` on Gemma 4-E4B-4bit yields a vision-reduction that clusters in
the **39–43 %** range on the dev tranche, while the holdout spread is
wider and should be described more softly than “benchmark-invariant,” across

- VideoMME 8-frame and 16-frame dev (n = 30 each)
- MVBench 8-frame dev (n = 30)
- TOMATO 8-frame dev (n = 30)

with the vision-axis ceiling predicting observed E2E within 2.7 pp on
all four, plus a fifth cell at 1.064× where we stack novelty-pruning
on top (H-stack, ceiling-matched). Dev-n=30 headline cells are

| Benchmark        | E2E speedup | V_red observed | V_share (dense) |
|------------------|-------------|----------------|-----------------|
| TOMATO (8 f)     | **1.24×**   | 0.40           | 0.48            |
| MVBench (8 f)    | **1.21×**   | 0.47           | 0.45            |
| VideoMME (16 f)  | **1.12×**   | 0.42           | 0.28            |
| VideoMME (8 f)   | **1.08×**   | 0.43           | 0.15            |

A held-out VideoMME 8 f paired measurement at **1.113×** confirms the
dev signal (holdout V_share 0.155, V_red 0.413, decode Δ 1.53 %, acc Δ
0.000). Held-out MVBench 8 f and TOMATO 8 f paired measurements are
*advisory* for decode-thermal reasons documented in the reproduction
log (MVBench 1.407× with favorable-direction 50 ms drift on a 432 ms
decode window; TOMATO 1.194× with favorable-direction 119.7 ms drift
below a revised 100 ms floor). We report both headline and holdout
numbers with their thermal-calibration notes.

One regression is **localized, not broad**: MVBench aggregate accuracy
drops 3 items (n = 30), all concentrated in object-binding categories
(2 object_interaction + 1 moving_attribute); spatial/motion categories
preserve 1.000 agreement. We footnote rather than wave away.

### What stacks and what doesn't

The three contributions do *not* compose as a naive product. C-CEILING
bounds every token-pruning speedup from above, and C-VISION's
`V_share × V_red` term shares the same vision budget: you cannot spend
it twice. Each mechanism earns its safety envelope only in the regime
where we audited it: C-VISION at single-query kr_V=0.50 L=2, C-PERSIST
at 40f with dense V. Our 1.30 session-streaming stack attempted the
across-queries composition (C-VISION on Q0 prefill, C-PERSIST on Q1–Q3
follow-ups) at 8f on Qwen 2.5-VL-7B-4bit and measured Δacc = −0.193
— paired amortized 3.326× speedup, but a preregistered accuracy-band
FALSIFY. The paper therefore treats the three contributions as
**separately-auditable safety envelopes**, not a stack whose union is
claimed without evidence; a root-cause decomposition (H_V / H_K /
H_interaction / H_reset) is preregistered to adjudicate which
mechanism or interaction owns the composition loss. Our 1.064 ×
H_stack cell (n = 60) is ceiling-matched, a preregistered NULL on
"stacking beats the ceiling" and a positive on the ceiling law itself.
The paper reports composed numbers against their ceiling bound, never
as a bare product of independent multipliers.

## 3. What Qwen routing contributes: a mechanism-validation backbone

Our original Qwen 2.5-VL-7B-4bit routing lane ("Lane A") is not the
headline of this paper. It is the **mechanism-validation backbone** on
which we decide what is and is not load-bearing on temporal redundancy.
A bounded-staleness, concentration-aware pixel-diff planner matches
dense-8 on MVBench motion holdout (0.600 @ 4.06 fresh frames, Pareto
win vs dense-6) and ties dense-8 on TOMATO motion holdout (0.333 @ 3.55
fresh frames, n = 30 each). Six intuitive refinements fall under
matched conditions:

- Naive mean-diff is blunt on temporally concentrated evidence; the
  `max_abs` statistic plus bounded staleness recovers ground.
- Sticky-dynamic quantity without placement helps MVBench holdout by
  +1 item but strictly *hurts* TOMATO dev — quantity is not the
  explanatory variable; placement of refresh in time is.
- Positional-encoding-only correction does not isolate
  cache-substitute fidelity; the refresh mechanism that works
  (periodic re-encode) addresses attention-propagation drift, not PE
  drift. We adopt attention-propagation-drift vocabulary throughout.
- Novelty-pruning on the vision side (1.51R on Gemma VideoMME) is a
  clean null on its own axis; the duration-conditional partial
  reproduction is a secondary composition appendix result, not a
  headline.
- Selective re-prefill of the last-K frames (1.55D) is
  infrastructure-falsified by mlx-vlm's image-block reuse contract,
  not experimentally falsified.
- VideoMME frame-count scaling is non-monotonic on Qwen 2.5-VL at
  4-bit: on the dev split, medium buckets improve from 8 f → 16 f by
  ≈ +30 pp and 32 f does not recover the aggregate. The 16 f long-
  bucket regression of ≈ −20 pp on dev **does not replicate on the
  disjoint holdout** (holdout 16 f long 0.900 vs dev 0.100, n = 30
  each); we treat the long-bucket shape as item-draw-dependent and
  dev-only. The broader point — "more frames is better" is false on
  this model at this quantization — survives.

Preserving these nulls is the work Lane A does for the paper.

## 4. Deployment-scale evidence: codec-through-sam

The numbers above come from a 4 B-class model at commodity 4-bit
quantization and sparse benchmark protocols. The sibling system
**codec-through-sam** (`~/s/codec-through-sam`) exercises the full
streaming stack at a different regime and supplies the deployment-scale
evidence C-PERSIST and C-VISION predict:

- **~50× dominant-pipeline compute reduction** on streaming VideoMME
  with exact Qwen caching across 1,937 sparse-sampled items.
- **13× ViT reduction** on a real streaming protocol.
- **5.4× prefill speedup** on Gemma novelty-pruning.
- **4.2–4.5× real-video end-to-end speedups** in selected regimes.
- **Median 0.8 s follow-up latency** with persistent KV.
- **5–300× live-camera ViT savings** depending on scene activity.

We do not claim these as codec-through numbers; we claim them as
deployment-scale evidence from a shared ceiling theory and a shared
attention-propagation-drift fidelity story. They establish that
C-PERSIST (conversational follow-up) and C-VISION (stage-bounded
vision speedup) are not artifacts of 4 B-class small-scale probing —
the same mechanisms, instantiated at 26 B-class on a real streaming
protocol, deliver product-scale multiplicative wins on the regime
where users actually deploy this class of model: mostly static
surveillance, talking-head conferencing, FPV/egomotion, and repeated
querying over the same stream.

Two categories of Sam numbers, carrying different evidential weight.
**Deployment-scale** — the bullets above — have paired baselines,
named protocols, and corpus sizes stated. They stand as main-body
evidence. **Case-study** — piecewise-reuse single-cell illustrations,
streaming anecdotes lacking a matched wall-clock comparison — are
appendix-bound. A case-study multiplier is not evidence for a
deployment-scale claim, and the paper does not mix the two.

The two repos run on disjoint axes by design. codec-through is
stricter and more reductionist — smaller local models, sparse-sampled
benchmark regimes, careful end-to-end accounting, pixel-diff proxy
science before full codec-native deployment, mechanism isolation, and
preregistered falsification. codec-through-sam is the full stack in
the right regime — 26 B-class model, real streaming protocol,
codec-native classifier, live decode in loop, persistent KV across
queries, temporal + spatial composition. Bridging between the two
repos is ongoing work: phase 1.30 reproduced Sam's session-streaming
protocol at 4 B-class scale (dev+holdout union n = 57 sessions / 171
queries, paired amortized 3.326× speedup, Δacc = −0.193 FALSIFIES
the preregistered ±0.05 accuracy band). The remaining bridge
experiment is therefore no longer the initial reproduction but the
root-cause decomposition (preregistered 2026-04-23, 6-arm Phase A
scout plus Q0 parity against 1.51V) that attributes the composition
loss to V-only, K-only, interaction, or a harness regression.

## 4.5. What the evidence has ruled out

A reviewer who believes only the positive claims has not read the paper.
The following nulls and boundaries shape the claim boundary as much as
the positives:

- **1.51R at Sam's reference `kr=0.50`:** own-axis null on Gemma
  4-E4B-4bit VideoMME 8 f dev (e2e = 1.00 ×, gen = 1.01 ×). The 1.51R
  numbers in the body come from `kr=0.10` with a different aggregate-
  accuracy story.
- **EXP10 n = 60 H_stack composition: preregistered NULL** on
  "stacking beats the ceiling." The 1.064 × is ceiling-matched, which
  is a positive result on the ceiling law and a null on stack-beats-
  ceiling.
- **1.29 codec-native sparse retrofit** at 8 f after-ingest: HARD-
  FALSIFIED under MAX-over-span aggregation (mean |Δ| = 53.8 pp vs
  pixel-diff, 2026-04-22). A continuous-score redesign passes the
  10 pp aggregate gate at 7.9 pp but fails per-item at 16–25 pp; off
  the critical path unless reframed to continuous-planner-signal or
  native-rate streaming.
- **1.55D v1 selective re-prefill: INFRASTRUCTURE-FALSIFIED.** An
  mlx-vlm image-block-reuse contract the harness does not respect;
  v2 reopens the experiment behind an in-repo monkey-patch, not yet
  landed.
- **1.60 scroll/pan regime-boundary probe:** closed as a natural-
  VideoMME corpus limitation. The wider 60-item audit found 0/60 items
  above `shifted_fraction >= 0.30` (max 0.125), so the scroll/pan
  boundary requires an egomotion/scroll corpus rather than more VideoMME
  mining.
- **Cross-architecture C-VISION probe on Qwen 2.5-VL:** landed on
  2026-04-23 at matched L=2, kr=0.50; Claim 15 is now two-architecture
  mechanism evidence, with broader Qwen benchmark coverage optional
  rather than a missing gate.

These are boundaries, not failures of the contributions. Where a
mechanism *does not* generalize we say so; where it does, we cite the
evidence inline.

## 5. Where we are on SOTA, honestly

codec-through alone is a strong methods paper, a publishable
analytical contribution, and a credible small systems lane. It is not
broad SOTA. codec-through-sam, evaluated on its own protocol, delivers
the product-scale multiplicative numbers. What we claim here is
**three linked contributions** — C-CEILING, C-PERSIST, C-VISION —
*and* the honest accounting of where the evidence mix sits across the
two systems. The paper is the evidence union, not either part alone.

## 6. Roadmap

§ 2 develops C-CEILING formally and cross-validates it across the
seven regime dimensions. § 3 characterizes the C-PERSIST
safe-deployment envelope and its onset-depth scaling. § 4 presents
C-VISION's operating point, V-reduction invariance, and three-
benchmark transfer. § 5 gives Lane A's matched-conditions
mechanism-validation evidence (what works, what doesn't). § 6
presents deployment-scale evidence from codec-through-sam. § 7
discusses limitations, a cross-architecture probe on Qwen for
C-VISION, the outstanding sparse-execution delta for claim 5, and the
future phases documented in `paper/priority.md`. Weak streaming case
studies without matched baselines are bounded to the appendix.
