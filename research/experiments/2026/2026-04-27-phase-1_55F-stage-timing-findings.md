---
phase: 1.55F-stage-timing
date: 2026-04-27
parent: research/experiments/2026/2026-04-27-phase-1_55F-stage-timing-prereg.md
status: landed 2026-04-27. PASS both gates. Q3 fixed/adaptive speedup 9.85× (paired median 9.50×); tail prompt tokens 451→50 (−89%); post_q2_repaired prefix coverage 99.4%.
related:
  - research/experiments/2026/2026-04-25-phase-1_55F-q3-post-q2-state-findings.md
  - research/experiments/2026/2026-04-27-adaptive-mechanism-queue-findings.md
---

# Phase 1.55F-stage-timing — Adaptive Q3 mechanism (FINDINGS)

**Verdict.** Adaptive C-PERSIST's wall-clock advantage over fixed K=1 is concentrated almost entirely on Q3, and it has a clean, single-cause mechanism: by inheriting the post-Q2-repaired KV cache, adaptive's Q3 only has to prefill the question text (50 tokens median) instead of re-prefilling the last frame (451 tokens median). The work-shape difference is observable per-stage and per-paired-item, not just in an aggregated headline.

## Per-stage decomposition (n=7 short-bucket clips, 21 paired follow-ups)

| Stage | Adaptive median (ms) | Fixed K=1 median (ms) | Speedup | Adaptive prefix coverage | Adaptive tail tokens | Fixed tail tokens |
|-------|----------------------|------------------------|---------|--------------------------|----------------------|--------------------|
| Q1 (cold) | 77,954 | 94,564 | 1.21× | 0.0% (cold) | 8,097 | 8,097 |
| Q2 (re-prefill K=1) | 8,212 | 12,615 | 1.54× | 94.3% | 459 | 459 |
| Q3 | **675** | **6,652** (per-row median; follow-up median 10,135) | **9.85×** | 99.4% | **50** | **451** |

Paired Q3 median fixed/adaptive speedup = **9.50×** across 7 pairs (range 7.82–14.99×). Tail-token reduction Q3 = **−88.9%** (451 → 50 median).

## Mechanism in one sentence

Adaptive Q3 re-uses the cache state that was repaired by Q2's K=1 re-prefill, so the only new tokens it needs to prefill are the Q3 question itself; fixed K=1 always re-prefills the last frame group plus the question, paying ~9× more wall-clock work for no paired accuracy benefit.

## Why this matters for the paper

1. **Headline mechanism support.** The closed adaptive-mechanism queue established a 35.97× session-level / 15.28× follow-up-level wall-clock win on the short tranche (`2026-04-27-adaptive-mechanism-queue-findings.md`). Until this attribution, that headline was unexplained at the per-stage level. Now it is: the speedup is paid for by avoiding re-prefill work on Q3 specifically, not by a diffuse implementation difference.
2. **Boundary clarity for reviewers.** The 9.85× is *measured under K=0 from `post_q2_repaired`*; it is not a generic claim that "adaptive is fast." It can only land when Q2 has already repaired the cache. This is a sharp condition the paper can state in one line.
3. **Q1/Q2 stay honest.** Q1 is cold for both arms; the 1.21× is implementation noise. Q2 is the same K=1 work for both; the 1.54× there comes from process-warmth and is not a mechanism claim. The paper does not need to overclaim on Q1/Q2.

## Falsification check

- If the 9.85× were a measurement artifact, it should not show up consistently per pair. It does: paired median 9.50×, range 7.82–14.99×, n=7 pairs, all positive.
- If the speedup were not driven by tail-prompt length, the tail token counts would be similar. They are not: 50 vs 451 median, a 9.0× ratio that matches the elapsed-time ratio almost exactly.
- The per-pair `prefix_coverage` for adaptive Q3 ranges 99.0–99.5%, vs 94.3–94.5% for fixed K=1 Q3. The marginal 5pp coverage gap is exactly the last-frame re-prefill work fixed K=1 still does.

## Limits and what this does not say

- Short-bucket only (n=7 clips, 21 follow-ups). The 1.55K temperature sweep (running) and any future medium-/long-bucket adaptive timing pass would extend this. The mechanism explanation should generalize because it is an arithmetic identity over prefix coverage, but the magnitude can shift with frame budget and bucket.
- This is **not** a new accuracy claim. Paired choice and correctness diffs were already 0/21 in the parent 1.55F finding — that is the fidelity result; this is the *why-fast* result.
- Only the Qwen 4-bit path is in scope. Gemma adaptive C-PERSIST is blocked by RotatingKVCache / sliding-window cache semantics in mlx-vlm; this attribution does not transfer until that is addressed.

## Paper integration (recommended)

- Abstract: keep the existing C-PERSIST headline number; add a short clause "the 9.85× per-stage Q3 speedup is explained by post-Q2-repaired cache reuse" if space allows.
- Methods: cite this attribution table directly when introducing the adaptive policy.
- Results: this lets the C-PERSIST result section state the mechanism *before* showing the headline, which is a stronger narrative than the reverse.
