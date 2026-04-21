---
date: 2026-04-21
parent: paper/framing.md
status: paper-facing draft introduction — three-contributions structure with Sam as deployment-scale evidence
---

# Introduction (codec-through-2, draft)

This intro is the paper-facing narrative counterpart to `framing.md`
(which is internal planning) and `abstract.md` (which is the
paper-opening). It operationalizes the structural request from Codex
round 25: **stop foregrounding Lane A as the center of gravity; make
C-CEILING, C-PERSIST, and C-VISION first-class; keep Qwen routing as
mechanism-validation backbone; move Sam from "applications/support" to
deployment-scale evidence.**

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

This is the paper's analytical contribution in its own right. It is
also a diagnostic: when a reported end-to-end gain exceeds the
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
- **Qwen 2.5-VL-3B-4bit**: clean at ≤ 36 frames / ≤ 14.5 k prefill
  (Δacc = −0.19 plateau). Basin onset at ~40 frames. At 3 B-40 f
  the basin is sampler-dispersible (4/14 → 1/14) but returns only to
  the pre-basin plateau, not to baseline — sampler-invariance is an
  architecture-conditional property, not a universal rescue.
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
`0.50` on Gemma 4-E4B-4bit yields a vision-reduction of **39–43 %**
that is benchmark-invariant and frame-invariant across

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
  4-bit: medium buckets improve from 8 f → 16 f by ≈ +30 pp, long
  buckets collapse by ≈ −20 pp, and 32 f does not recover. "More
  frames is better" is false on this model at this quantization.

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

The two repos run on disjoint axes by design. codec-through is
stricter and more reductionist — smaller local models, sparse-sampled
benchmark regimes, careful end-to-end accounting, pixel-diff proxy
science before full codec-native deployment, mechanism isolation, and
preregistered falsification. codec-through-sam is the full stack in
the right regime — 26 B-class model, real streaming protocol,
codec-native classifier, live decode in loop, persistent KV across
queries, temporal + spatial composition. Bridging between the two
repos is ongoing work: a local streaming-protocol reproduction of
Sam's N = 60 line (phase 1.30) is the largest remaining bridge
experiment on the codec-through side.

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
