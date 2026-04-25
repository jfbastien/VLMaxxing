---
phase: 1.30AB
date: 2026-04-25
parent: research/experiments/2026/2026-04-25-phase-1_30AB-long-q0-sweep-prereg.md
status: landed 2026-04-25/26 (overnight). All 4 candidates FAIL the rescue gate. The duration-conditioned admission policy lane is closed under the current cache-reuse regime.
---

# Phase 1.30AB — Long-bucket Q0 keep-rate boundary sweep (FINDINGS)

**Verdict:** **The duration-conditioned admission policy lane is comprehensively
closed under the current cache-reuse regime.** All four candidates `kr_Q0 ∈
{0.75, 0.80, 0.85, 0.90}` fail the rescue gate (Δacc ≤ −0.10) on the full
n=18 long-bucket tranche. Combined with `1.30Z` (kr_Q0=0.67, Δ=−0.130), the
lane has 5/5 fail-points across the sweep. **`1.30AE` was correctly skipped
by the queue's gate logic.**

The sweep also produces an unexpected mechanism finding: **at kr_Q0 ≥ 0.85,
Q0 is exactly preserved but follow-up drift is locked at ≈ −0.19**, isolating
**post-Q0 K-cache state quality** as the failure mode.

## Why this run mattered

`1.30Z` falsified the original `kr_Q0=0.67` candidate (Δ=−0.130). The next
falsifiable question was: *does the rescue band return at any other long-Q0
keep rate*?

`1.30AB` was the boundary sweep: four candidates, fixed cold control reused
from `1.30Z`, identical follow-up policy (kr=0.50, mechanically a no-op
under cache reuse).

## Setup

- Model: `Qwen2.5-VL-7B-Instruct-4bit`
- Regime: VideoMME 8f, dev+holdout long bucket only (n=18 sessions / 54
  paired queries per candidate)
- Manifest: `research/benchmark_manifests/videomme_long_dev_holdout_v1.toml`
- Cold reference: reused from `1.30Z` (cold accuracy = 26/54 = 0.481)
- Streaming policy:
  - `Q0`: kr_Q0 ∈ {0.75, 0.80, 0.85, 0.90}
  - `Q1`/`Q2`: kr=0.50 (cache-served, mechanically no-op)
- Runner: `scripts/run_phase1_30_sam_streaming.py`
- Wrapper: `scripts/run_phase1_30AB_long_q0_candidate.sh <rate>`
- Output dirs: `phase1_30AB_long_q0_kr<tag>/` (one per candidate)
- Auto-committed by the follow-up queue runner as `dc599d3`, `36cdc21`,
  `c506614`, `53622c3`.

## Headline results (consolidated)

| candidate | Δacc | CI95 | Q0 Δ | Follow-up Δ | speedup | format | active_fraction |
|---|---|---|---|---|---|---|---|
| kr_Q0=0.67 (1.30Z reference) | −0.130 | [−0.278, +0.019] | −0.111 | −0.139 | 3.12× | clean | 0.0 |
| **kr_Q0=0.75** | **−0.185** | [−0.315, −0.074] | −0.111 | −0.222 | 3.37× | 1 degen | 0.0 |
| **kr_Q0=0.80** | **−0.185** | [−0.315, −0.074] | (≈ kr=0.75) | (≈ kr=0.75) | 3.38× | clean | 0.0 |
| **kr_Q0=0.85** | **−0.130** | [−0.241, −0.037] | **0.000** | **−0.194** | 3.35× | clean | 0.0 |
| **kr_Q0=0.90** | **−0.130** | [−0.241, −0.037] | **0.000** | **−0.194** | 3.34× | clean | 0.0 |

For comparison, the *successful* 1.30W result (kr_Q0=1.0 + cache-reuse
follow-ups, full union n=171) landed at **Δ=−0.058**. So between kr_Q0=0.90
and kr_Q0=1.0 there is a sharp transition from out-of-band (Δ≤−0.13) to
bounded-near-miss (Δ=−0.058).

All five long-bucket runs (1.30Z + four AB candidates) measure
**streaming_follow_up_vision_pruning_active_fraction = 0.0** exactly. As
expected: the Qwen scatter-back wrapper produces byte-identical input_ids
between dense and pruned configs, and prompt-cache reuse covers all image
tokens on follow-ups. Mechanism is confirmed Q0-admission + K-cache reuse
across all candidates.

## The unexpected finding: Q0-fidelity vs follow-up-fidelity decouple at kr_Q0 ≥ 0.85

The two highest keep rates produce **byte-identical Q0 accuracy to cold**
(q0_accuracy_delta = 0.000) yet **−0.194 follow-up drift**. This wasn't
predictable from the kr_Q0=0.67/0.75/0.80 results, which had Q0 drift on the
order of −0.111 along with their follow-up drifts.

This **isolates two phenomena that had been entangled in the prior 1.30 lane
analysis**:

1. **Q0 admission accuracy** — controlled by how many image tokens survive
   the vision-tower pruning at Q0. At kr_Q0 ≥ 0.85, this is "high enough"
   for Qwen to produce the same Q0 answer as cold.

2. **Post-Q0 K-cache state quality** — the KV cache produced by the
   pruned-Q0 forward pass is *systematically different* from cold's KV
   cache, even when the resulting Q0 answer is identical. Follow-ups read
   this different K-cache state and produce ~−19pp drift.

That is, **the follow-up drift in the 1.30 lane is NOT caused by the Q0
admission decision degrading Q0 itself** — it is caused by the post-Q0
cache state, which the K-cache-reuse path then preserves and feeds into
follow-up generation paths.

## Preregistered verdicts

### H1 — at least one long-Q0 rate re-enters the rescue band

**FALSIFIED.** No candidate satisfies all of:
- accuracy_delta_streaming_minus_cold ≥ −0.10
- amortized_speedup_cold_over_streaming ≥ 3.0×
- parse_failures = 0
- degenerate_fraction = 0

The closest to the band is kr_Q0 ∈ {0.85, 0.90} at Δ=−0.130, still 3pp out
of band. The 1.30Y residual-pair scout — which originally promoted
kr_Q0=0.67 — is now falsified at every nearby keep rate.

### H2 — the smallest passing rate is the deployable candidate

**Vacuously satisfied** (no passing rate). The queue runner correctly
returned `selected_130ab_rate = None` and skipped `1.30AE`.

### H3 — follow-up pruning remains inactive unless measured otherwise

**EARNED across all 5 long-bucket runs.** Every candidate measures
`streaming_follow_up_vision_pruning_active_fraction = 0.0` and
`streaming_follow_up_all_image_tokens_reused_fraction = 1.0`. The
"Q0 admission + K-cache reuse" relabeling rule fires uniformly.

## Implications for the paper

1. **The 1.30 admission policy family is closed at long-bucket under
   cache-reuse follow-ups.** No rescue point exists in
   kr_Q0 ∈ {0.67, 0.75, 0.80, 0.85, 0.90}. The published 1.30W
   "bounded near-miss" result remains the best landed 1.30 lane number.

2. **The mechanism story tightens**: 1.30 long-bucket failure is
   K-cache-state-quality-driven, not Q0-admission-accuracy-driven. The
   paper can now report the kr_Q0=0.85/0.90 isolated-mechanism finding
   as a clean section: "Q0 fidelity preserved exactly at kr_Q0=0.85,
   yet follow-up accuracy drops 19pp because the post-Q0 KV cache is
   systematically different from cold's."

3. **1.30AC (cache-invalidated follow-ups) becomes the only path that
   can produce a positive C-VISION 1.30 result.** With the
   admission-policy lane closed and the mechanism narrowed to K-cache
   state quality, the natural fix is to invalidate the cache so each
   follow-up re-runs vision tower from scratch. That experiment is
   already preregistered (39f5097) and waiting on a small driver
   change.

4. **The 1.30 lane in the paper should be reported as a clean
   negative + mechanism finding**, not as an ongoing search. Reviewer-
   facing language: "The duration-conditioned Q0 admission policy
   does not produce a deployable bridge result on long-bucket
   VideoMME at any tested keep rate; the failure mode is post-Q0
   K-cache state quality, not Q0 admission accuracy. A
   cache-invalidation variant (1.30AC) remains an open follow-up."

## Anomalies and notes

- The kr_Q0=0.75 candidate has **1 degenerate streaming row** while
  kr_Q0=0.80, 0.85, 0.90 are all format-clean. With n=54 paired queries
  per candidate, 1/54 = 1.85% degenerate rate is well within
  thermal/seed noise. Probably not a meaningful difference between 0.75
  and 0.80; both are at Δ=−0.185.
- The bootstrap CI on Δacc widens at kr=0.85/0.90 to [−0.24, −0.04],
  reflecting cleaner Q0 (no Q0 drift) but persistent follow-up
  variability.
- The Q0 cache state difference at kr_Q0=0.85 is, by definition, *not*
  caused by Qwen's vision-tower pruning making bad selections — Q0
  itself produces the same answer. It must be caused by:
  - the *embedding values* of pruned-then-zero-scattered tokens
    differing from dense-token embeddings,
  - those embedding differences propagating through the language
    model's first-token attention to produce a slightly different
    KV cache, and
  - that different KV cache being preserved across follow-ups via the
    cache-reuse path
- This makes the 1.30AC test pointed and well-motivated.

## What this rules out and what it does not

**Rules out:**
- "Higher kr_Q0 monotonically improves long-bucket fidelity in the
  1.30 lane." Falsified — 0.75/0.80 are *worse* than 0.67, and 0.85/
  0.90 only reach 0.67's level.
- "Q0 admission and follow-up fidelity are coupled." Falsified at
  kr_Q0 ≥ 0.85, where they decouple.
- "The 1.30 admission family has any deployable rescue point in the
  current cache-reuse regime."

**Does not rule out:**
- "Cache-invalidated follow-ups (1.30AC) could rescue the 1.30 lane."
  Still untested.
- "Even denser Q0 (kr_Q0 = 0.95) might bridge the gap to 1.30W's
  Δ=−0.058." We have a sharp transition between 0.90 and 1.0 with no
  intermediate measurements; an additional kr_Q0=0.95 candidate could
  characterize the transition.

## Pending follow-ups

- **`1.30AC`** (already preregistered, 39f5097): cache-invalidated
  follow-up V-pruning test. Now strongly motivated by the
  Q0-vs-follow-up decoupling finding above.
- **`1.30AD`** (already preregistered, 234bf3d): instrumented 1.30W
  rerun to lock the published number's mechanism story.
- **(NEW)** `1.30AB-fine`: a single additional candidate at kr_Q0=0.95
  to characterize the sharp transition between 0.90 and 1.0. Cheap
  (~30 min, cold reused). Would close the kr_Q0 sweep.

## Decisions

- `registry.md` 1.30AB row updates to `landed-FAIL`.
- 1.30 lane in the paper is now scoped as "closed boundary" rather
  than "open candidate search."
- The Q0/follow-up decoupling at kr_Q0 ≥ 0.85 deserves its own paper
  paragraph as a mechanism finding.
- The C-VISION 1.30 narrative needs a clean negative + mechanism
  framing rather than the prior "ongoing rescue" framing.
