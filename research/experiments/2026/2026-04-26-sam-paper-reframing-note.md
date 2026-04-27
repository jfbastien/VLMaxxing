# Paper Reframing Note — for JF

**Author:** Sam (codec-through main lane)
**Date:** 2026-04-26
**Status:** Proposal, not adopted. Open for pushback.
**Companion:** `paper/publishability-status.md` (jfb), `research/decision-log.md` (this lane)

---

## TL;DR

The current three-claim spine (C-VISION / C-PERSIST / C-CEILING + Qwen
routing as mechanism) is tight, but it scopes the paper to **sparse-sampled
benchmark science on 4B-class models**. I think there are two upgrades that
turn the same evidence into a meaningfully bigger paper without inventing new
runs, plus four candidate additions worth weighing.

## Proposal A — Promote streaming to a fourth claim axis (C-STREAM)

`publishability-status.md` (round-26, line ~46) labels the 26B/streaming work
"deployment-scale operational evidence" — i.e., supplementary case-study
status. I think this undersells three independently-evaluable mechanisms:

- **MV-driven cache staleness** (decision-log 2.03-SCROLL): correlation +0.53
  on real scroll content, clean threshold at MV-sum ≈ 500.
- **Piecewise sectional cache-shift** (2.06): two recordings, matches fresh
  oracle at 87–99% cache reuse, residual-as-rebuild-trigger.
- **MV-inflection segmentation** (2.02): 96% precision on real visual
  discontinuities, static-camera regime.

Their regime — *online query against a live stream* — is one your local
infra can't test (whole-video QA is time-invariant by construction; see
2.03-NULL). It's not "scale-out of the same regime"; it's a different
regime. Reframing them as **C-STREAM** (peer to C-VISION/C-PERSIST/C-CEILING)
gives the paper a fourth claim axis with its own paired baselines, ceiling
model (TBD), and benchmark-mismatch story.

**What this changes about S0–S4.** S3 (native streaming matched baselines)
becomes paper-headline work, not just reviewer defense. S2 stays Track-B.
S0/S1/S4 unchanged.

## Proposal B — Add a shared lemma: cache–attention interaction

Two findings from independent lanes, same shape:

- **Scatter-back ceiling** (1.51V H3 arch-blocked): post-pool fresh tokens
  scattered back into a partly-cached context bound the ceiling.
- **Frankenstein cache** (2.06-NEG): residual-complement fresh-injection
  into a stale cache hurts accuracy on streaming content.

Both say: **attention layers don't tolerate hybrid fresh/cached content
cleanly.** That's a structural bound on every anti-recomputation method
(FastV, codec-through, persistent-KV, selective-reprefill alike). Today
neither lane claims it. As a shared lemma in §3, it raises the paper's
generality without new evidence.

## Candidate additions — flag for discussion, don't commit yet

1. **Codec side-channel as primary signal.** Today V_red / V_share / novelty
   are intrinsic-feature signals. The codec already produces the
   redundancy classification; we're throwing it away. Frame this in §1, not
   buried in a streaming case study.

2. **Evaluation-methodology contribution.** 2.03-NULL → 2.03-SCROLL is the
   cleanest demonstration in either repo that VideoMME / MVBench / TOMATO
   are blind-by-construction to cache-lifetime mechanisms. Earns the right
   to introduce or argue for a streaming benchmark.

3. **Measured energy on M5 Max.** No instrumentation today; with a wall-power
   meter on a 26B run, we can produce a Wh/hour-of-video number. First
   measured number on consumer hardware for a 26B-class video VLM. Unlocks
   systems-venue paths.

4. **Cross-architecture drift law.** Your 1.57 on Qwen + our §8 on Gemma
   share shape (STATIC > SHIFTED > NOVEL, monotone-rising). A predictive
   model — "given codec-class stats and ViT depth, here's where drift
   sets in" — unifies both lanes' mechanism evidence.

## What I'd push back on

- **Resurrecting a multiplicative composition headline (~50× aggregate).**
  You retired claim 11 for good reasons; the ceilings interact. Better to
  keep each claim's ceiling clean and report bounded composition only where
  measured.
- **More N on already-earned cells.** Marginal item doesn't move the
  headline; missing axes above do.

## Asks

1. Push back on A and B specifically — does promoting C-STREAM cost more
   than it earns, given baseline-implementation runtime?
2. If A is in: do we want C-STREAM in the same paper, or split (mechanism
   paper + streaming systems paper)? My instinct is same paper, regime-
   labeled, but I haven't done the venue analysis.
3. Of the four candidate additions, which (if any) earn airtime now versus
   in a follow-up?

I'll keep S0 (Gemma 26B cache-correctness smoke + provenance) going in
parallel since it's needed either way.
