---
date: 2026-04-27
parent: research/experiments/2026/2026-04-26-paper-adaptive-mechanism-runbook.md
status: queue complete 2026-04-26/27. Six-phase consolidated findings.
---

# Adaptive-Mechanism Queue — Consolidated Findings

The 6-phase adaptive-mechanism queue ran end-to-end overnight on the local
laptop (16 GB unified memory) with one MLX approval at launch. **All six phases
completed and landed usable artifacts. The science gates passed where claimed,
but the strict preregistered RSS gates were too tight for 1.55F-long and
1.55F-32f.** The paper's C-PERSIST contribution upgraded from
"strongest single-cell" (1.55F short, 24.91× / 0/21) to "fully scoped
multi-regime adaptive lane" (n=93 across short/medium/long/32f-short /
0/93 paired drift / 15.28-35.97× all-query-median speedup), and the
C-VISION 1.30 lane is
now closed via measurement-grade double-evidence (active=0.0 cache-reuse
path AND active=1.0 cache-invalidation path both produce the same net
aggregate accuracy drop with the latter killing the wall-time benefit).**

## Six-phase summary

| phase | regime | n | paired diffs | speedup | active_fraction | RSS | gate |
|---|---|---|---|---|---|---|---|
| 1.55F-medium | 20f medium | 30 | 0/30 | 15.28× all-query / 14.90× same-class | n/a (adaptive) | 1.94 GB | PASS |
| 1.55F-long | 20f long | 21 | 0/21 | 22.83× all-query / 22.44× same-class | n/a (adaptive) | 6.05 GB | PASS sci, RSS gate fail |
| 1.55F-32f | 32f short | 21 | 0/21 | **35.97×** all-query / 35.92× same-class | n/a (adaptive) | 6.09 GB | PASS sci, RSS gate fail |
| 1.55J | 20f short, T=0.7 | 21 | **1/21** | 12.26× all-query / 12.21× same-class | n/a (sampler) | 5.24 GB | PASS fidelity, exact-match miss |
| 1.30AC | 8f full union, cache-invalidated | 171 | n/a | **1.06×** | **1.0** | — | "hurtful" |
| 1.30AD | 8f full union, cache-reuse | 171 | n/a | **3.02×** | **0.0** | — | reproduces 1.30W |

(Per-phase commits: `364cf17`, `661acd3`, `72ce36b`, `7e2183b`, `c5887ce`,
`66c2a63`. Auto-committed by the queue runner with full pair-metrics +
paired-queries jsonl artifacts.)

## C-PERSIST: paper-headline now four-cell adaptive

Combined with the previously-landed `1.55F` (20f short, 0/21, 24.91×), the
adaptive C-PERSIST lane now spans:

| run | regime | n | paired diffs | speedup |
|---|---|---|---|---|
| 1.55F | 20f short | 21 | 0/21 / 0/21 | 24.91× all-query / 24.76× same-class |
| 1.55F-medium | 20f medium | 30 | 0/30 / 0/30 | 15.28× all-query / 14.90× same-class |
| 1.55F-long | 20f long | 21 | 0/21 / 0/21 | 22.83× all-query / 22.44× same-class |
| 1.55F-32f | 32f short | 21 | 0/21 / 0/21 | **35.97×** all-query / 35.92× same-class |
| **combined** | **all 4 cells** | **93** | **0/93 / 0/93** | **15.28-35.97× all-query** |

Rule-of-three at n=93 with 0 observed diffs: upper one-sided 95% CI on
diff rate is **≤3.2%**.

This is the paper's strongest claim. The adaptive Q1-cold / Q2-K=1 /
Q3-K=0-from-post-Q2-state policy:

- Preserves answer identity exactly across n=93 paired queries spanning
  three duration regimes plus the 32f depth boundary
- Achieves **15-36× all-query-median speedup** and **15-36× same-class
  follow-up speedup** after rounding (vs fixed K=1's
  9-20×; the 1.55F adaptive lane is consistently 1.5-2.6× faster than
  fixed K=1 on matched tranches)
- The 35.97× single-cell result on 32f-short is the strongest local
  efficiency number the paper has

## C-PERSIST sampler robustness (1.55J)

The fixed-K=1 short-bucket result (1.55D) survives a substantive
non-greedy sampler (T=0.7, top_p=0.95) at:
- 1/21 paired correctness diffs (close to 0/21 greedy)
- 1/21 paired choice diffs
- session correctness 17/21 (matches 1.55D K=1 baseline — H5 floor PASS)
- speedup 12.26× all-query / 12.21× same-class follow-up

This is **paper-defensible reviewer evidence** that the repaired-frontier
stability is not purely a greedy-path artifact. It should not be written as
"exact sampler-invariant fidelity": the exact-match subgate missed at 1/21.
A reviewer asking "does a warmer sampler immediately expose the pathological
basin?" gets a measurement-backed "no — at T=0.7 the result is 1/21 with no
pathological follow-up collapse."

## C-VISION 1.30: comprehensively closed via double-evidence

The 1.30 admission lane now has measurement-grade evidence that it is
structurally bounded:

| variant | mechanism | Δacc | speedup | active_fraction |
|---|---|---|---|---|
| **1.30AD** (= 1.30W instrumented) | dense Q0, K-cache reuse on Q2/Q3 | **−0.0585** | **3.02×** | **0.0** |
| **1.30AC** | dense Q0, cache invalidation on Q2/Q3 | **−0.0585** | **1.06×** | **1.0** |
| 1.30Z | kr_Q0=0.67 long-bucket | −0.130 | 3.12× | 0.0 |
| 1.30AB sweep (kr_Q0 ∈ {0.75, 0.80, 0.85, 0.90}) | long-bucket Q0 admission | −0.130 to −0.185 | 3.3× | 0.0 |

**Two cache strategies, the same net aggregate accuracy drop, opposite ends of
the speedup spectrum.** The active_fraction=0.0 vs 1.0 measurement is the
crux: 1.30AC forced V-pruning to actually fire on every follow-up
(active=1.0, all 3200 image tokens recomputed per query) and the
resulting net accuracy drop matches 1.30W's cache-reuse path
where V-pruning was suppressed. So:

- **The 1.30 admission family is structurally bounded under both
  cache-strategy mechanisms at the aggregate level.** Cache-reuse produces -5.85pp via K-cache
  state mismatch from kr=0.50 fold-in; cache-invalidation produces the
  same -5.85pp via fresh per-query V-pruning. Neither is in-band of the
  -10pp rescue gate.
- **The wall-time win disappears under cache invalidation** (1.06× vs
  3.02×). Forcing V-pruning to fire costs essentially as much as cold
  prefill, defeating the policy's purpose.

The paper's C-VISION 1.30 narrative now reads as a clean negative +
mechanism finding, not an open search. 1.30AD additionally locks the
published 1.30W number under measurement (active=0.0) instead of
inference.

## Q0 admission decoupling — paper-paragraph mechanism

A subtle finding from the cumulative 1.30 evidence (1.30Z + 1.30AB
sweep + 1.30AD + 1.30AC):

- At kr_Q0 ≥ 0.85, **Q0 fidelity is exact** (q0_dacc = 0.000 across all
  cache-reuse runs) but follow-ups still drift −19pp under cache reuse.
- 1.30AD (kr_Q0 = 1.0) shows q0_dacc = 0.0 and follow_up_dacc = −0.088
  on the full union.
- 1.30AC (kr_Q0 = 1.0 with cache invalidation) shows q0_dacc = 0.0 and
  follow_up_dacc = −0.088 on the full union.

So the follow-up drift is **independent of Q0 admission accuracy** at
dense Q0 — it depends on the K-cache state quality (under cache reuse)
or the per-query V-pruning recomputation (under cache invalidation).
Both paths produce the same aggregate Δacc.

The row-level flip sets differ, so this is not evidence that cache-reuse and
cache-invalidation fail on exactly the same items. The scientific point is
stricter and narrower: two distinct mechanisms land on the same net aggregate
loss while only one preserves the 3× wall-clock profile.

This is paper-paragraph mechanism evidence isolating cache-state
quality (or its V-pruning replacement) as the dominant fidelity driver
in the 1.30 lane, separable from Q0 admission accuracy.

## Anomalies and notes

- **H4 RSS gate technically failed on 1.55F-long and 1.55F-32f** because
  the prereg ceilings (5.5 and 6.0 GB) were set before the actual peaks
  were measured. Both runs completed cleanly within the 9 GB safe-RSS
  guard; no aborts. Same retroactive-too-tight pattern as 1.55G K=1.
  Future preregs should size H4 against measured prior runs.
- **1.55J Q1 elapsed_ms is higher than 1.55D K=1 short** (~104s vs ~80s)
  because non-greedy sampling at T=0.7 generates more tokens before
  hitting EOS. Doesn't change the science — both arms of 1.55J are
  paired at the same sampler.
- **Active-fraction measurement on 1.30AC** validated that the
  `--reset-cache-between-queries` flag is mechanically correct: every
  follow-up shows prefix_hit=0, image_tokens_recomputed=3200 (full),
  vision_pruning_active=True, refresh_reason="per_query_reset". The
  smoke-gate caught no regressions before the full 5h run.
- **1.30AC speedup of 1.06×** is the marginal benefit of cache reuse
  for K-cache only (Q2/Q3 generate-time reuse) when the vision tower is
  forced to re-fire per query. Effectively a dense-Q-everywhere baseline.

## Combined pre-launch and queue commits (this AFK round)

15 queue + commit-direct + paper-sync commits in this AFK session,
auto-staged by the queue runner where applicable. Including:

- 5 future-experiment preregs from prior session (1.55F-medium, -long,
  -32f, 1.30AC, 1.30AD, 1.55J)
- 2 P0/P1 fixes (`5ca9238`, `07856f2`) addressing pre-launch peer review
- 6 phase auto-commits + 6 phase findings docs (this consolidated file)
- 2 paper-narrative integration commits (e59bd2c, f5e48eb, 7c6ac44)

## Implications for paper closeout

1. **C-PERSIST headline rewrite**: lead with adaptive 4-cell n=93 with
   0/93 drift and 15.28-35.97× all-query-median speedup, supported
   by fixed K=1 4-cell n=93 with 0/93 drift (no-coordination baseline)
   and 1.55J sampler defense.
2. **C-VISION 1.30 narrative becomes a clean boundary result** with
   measurement-grade evidence from 1.30AD (active=0.0) and 1.30AC
   (active=1.0). Paper section reads "1.30 admission policy is
   structurally bounded under both cache strategies; same net aggregate
   accuracy drop, divergent speedup, different row-level flip sets."
3. **No new SOTA on benchmarks.** The story remains efficiency/mechanism.
4. **Rule-of-three CI on n=93 is ≤3.2%** for the paired-drift claim. The
   paper should keep "no observed paired drift" wording with this CI.
5. **The 1.30AC `mechanism_outcome = "hurtful"` finding** is itself a
   publishable mechanism contribution: forcing V-pruning to fire on
   follow-ups produces equivalent accuracy drop to the cache-reuse-only
   path, but with 2.85× lower speedup. Composition is non-additive in a
   measurable sense.

## Pending follow-ups (deferred to next batch / next venue)

- **Deployment baselines**: low-FPS dense, screenshot polling,
  SimpleStream-like recency. Plan staged at
  `research/experiments/2026/2026-04-26-deployment-baseline-plan.md`.
  Required for systems-venue submission, not for arXiv preprint.
- **1.58 bf16 KV control**: larger-memory machine work.
- **Matched Gemma 1.57 drift probe**: ~30-60 min, would convert C-VISION
  cross-architecture from "Qwen+Gemma-aggregate-transfer" to "two-arch
  drift geometry."
- **1.55F at 16f**: frame-budget interpolation for adaptive lane.

These are next-batch polish, not paper-headline blockers.
