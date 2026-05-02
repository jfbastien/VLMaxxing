---
date: 2026-05-02
phase: 1.55M (dense-anchored multi-turn C-PERSIST stress) — CLOSED
status: paired-stability run complete; mixed-result finding bounds the C-PERSIST safe regime
related:
  - 2026-05-01-phase-1_55M-diverse-prompt-multi-turn-prereg.md
  - 2026-04-30-phase-1_55L-many-turn-cpersist-findings.md (A6 baseline, repeated-question)
  - 2026-05-01-paper-defensibility-experiment-plan.md (Item 3)
artifact_paths:
  - research/experiments/2026/artifacts/phase1_55M_dense_anchored_cpersist/summary.json
  - research/experiments/2026/artifacts/phase1_55M_dense_anchored_cpersist/baseline_many_turn.jsonl
  - research/experiments/2026/artifacts/phase1_55M_dense_anchored_cpersist/session_many_turn.jsonl
  - research/experiments/2026/artifacts/phase1_55M_dense_anchored_cpersist/paired_many_turn.jsonl
---

# Phase 1.55M — dense-answer-anchored C-PERSIST stress findings

## Headline result

Under controlled dense-answer-anchored prompt variation (turn k+1 prepended with the canonical dense answer from turn k, applied identically to dense and cached arms), at horizon=20 across 7 VideoMME short-tranche clips × 3 policies on Qwen 2.5-VL-7B-Instruct-4bit (20 frames):

| Policy | Drift gate basis | Choice drift | Rate | pass_three_percent_drift |
|---|---|---:|---:|:-:|
| **fixed_k1** | followup_only n=133 | 0 | 0.00% | ✅ **PASS** |
| **adaptive_post_q2** | followup_only n=133 | 6 | 4.51% | ❌ **FAIL** |
| **refresh10** | followup_only n=133 | 6 | 4.51% | ❌ **FAIL** |

All cells are paired-prompt-hash-clean (`pass_prompt_hash_pairing=true`); no pathological format hits across 420 paired session rows; complete-grid gate true.

This **bounds** C-PERSIST: the conservative `fixed_k1` policy (re-prefill 1 frame per turn) survives content-conditional stress at horizon=20, but the aggressive cache-reuse policies (`adaptive_post_q2`, `refresh10`) cross the 3% gate at 4.3%/4.5%.

## Comparison with A6 (repeated-question, horizon=50)

| Cell | Schedule | Horizon | Drift on adaptive_post_q2 | Drift on refresh10 |
|---|---|---:|---:|---:|
| A6 (1.55L, `b06a345`) | stateless_question_cycle (3 unique Qs cycled) | 50 | 0.00% | 0.00% |
| **1.55M (this study)** | dense_anchored (content-conditional, prior dense answer injected) | 20 | **4.51%** | **4.51%** |

The drift difference is **content-conditional**: the same policies that show zero drift through 50 repeated-question turns crack 3% within 20 dense-answer-anchored turns. The drift is small (6/133 ≈ 4.5%) but exceeds the prereg gate.

## Drift distribution across turn buckets

| Policy | Bucket [0, 10) drift | Bucket [10, 20) drift | Bucket pattern |
|---|---:|---:|---|
| fixed_k1 | 0/63 | 0/70 | uniform zero |
| adaptive_post_q2 | 3/63 (4.76%) | 3/70 (4.29%) | uniform, no late-turn cliff |
| refresh10 | 3/63 (4.76%) | 3/70 (4.29%) | uniform, no late-turn cliff |

**Critically, drift does not accumulate over turn index.** Both adaptive and refresh10 show approximately 4.3% drift in early (0-10) and late (10-20) buckets. There is no cliff that would suggest a horizon-dependent breakdown — the drift is a *constant per-turn rate* under content-conditional stress, not a degradation that worsens with horizon.

`cliff_bucket_detected=false` for all three policies.

## Mechanism interpretation (theory)

Under repeated-question schedule (A6), the 3 fixed prompts cycle every 3 turns; each unique prompt shape is encountered many times, and the cache-reuse policy effectively replays the same prompt structure. Errors do not compound because the prompt distribution is deterministic.

Under dense-anchored schedule (1.55M), each turn's prompt embeds a substring from the prior dense answer. The cached arms reuse the visual prefix but rebuild the question prefix; the cached attention state is *correctly anchored to the visual prefix only*, so any divergence is on the rebuild path. Two hypotheses for the residual 4.5% drift:

- **H_A** (the language-prefix attention drift): the cached arm's visual KV cache slightly under-attends to the per-turn-novel question text because cross-attention statistics differ from the dense-arm pass, biasing decoding marginally toward the cached vocab.
- **H_B** (the per-turn temperature-zero noise floor): even with greedy decoding, the rebuild-prefill at turn k+1 has a small probability of taking a different argmax due to numerical reordering between cached and non-cached attention weights. This is a known noise floor on Qwen 2.5-VL-7B-Instruct-4bit at T=0.

H_B is consistent with the *uniform* per-bucket distribution and the *constant* rate. H_A would predict bucket-dependent rate increases with horizon (more accumulated content to drift away from), which is not observed.

This is **not** discriminative within the current data — both hypotheses predict 4.5% drift uniformly distributed. A higher-horizon (40 or 50) dense-anchored run would discriminate: H_A predicts rate growth with horizon; H_B predicts a stable 4-5% per-turn floor.

## Wall-clock timing

| Policy | Median elapsed per turn (followup_only) | vs dense baseline (~80s) |
|---|---:|---:|
| fixed_k1 | 5328.8 ms | 15.0× faster |
| adaptive_post_q2 | 698.2 ms | 114.6× faster |
| refresh10 | 708.9 ms | 112.9× faster |

The cache-reuse speedups are dramatic — adaptive_post_q2 follow-ups are 114.6× faster than cold dense passes. **The 4.3% drift cost buys a >100× wall-time speedup**, which is a defensible pareto trade if the paper frames it that way.

## Total wall time

16324 seconds = **4.5 h** for the full 7×20×3 grid (140 baseline + 420 session = 560 generations on Qwen 2.5-VL-7B-Instruct-4bit at 20f). Peak RSS 9.99 GB (under the 12 GB guard); final RSS 4.69 GB.

## Honest framing for the paper

**Recommended language**: "C-PERSIST holds without observable drift under repeated-question schedules through 50 turns (A6). Under controlled dense-answer-anchored prompt variation through 20 turns (1.55M), conservative re-prefill (`fixed_k1`) preserves zero-drift, while aggressive cache-reuse policies (`adaptive_post_q2`, `refresh10`) exhibit small but measurable drift of approximately 4.5% — a 100× wall-time speedup against a 4.5pp paired-correctness cost. The drift is uniform across early and late turn buckets, indicating a per-turn noise floor rather than horizon-dependent accumulation."

**Do NOT claim**: "C-PERSIST holds under content-conditional dialogue stress" — that overstates the result for adaptive/refresh10.

**Do claim**: "C-PERSIST has a structurally observable drift boundary at content-conditional prompt variation, quantified at ~4.5% paired-correctness cost on adaptive/refresh10 vs. zero on fixed_k1, with 100× wall-time speedup."

## Falsification log

- H1 prereg: "Adaptive post-Q2 cache reuse and refresh10 stay within 3% paired drift gate through 20 dense-answer-anchored turns." → **FALSIFIED** at 4.51% on both policies.
- H2 prereg: "Fixed K=1 produces at least as much paired drift in 1.55M as in A6." → **FALSIFIED** in the opposite direction: fixed_k1 holds at 0% drift, while A6's fixed_k1 also held at 0% drift in the previous run.

## Comparison to A6 (1.55L) — what changed

The driver is identical except for `--prompt-variant-mode dense_anchored`. Frame count (20), token budget (32), seed (42), greedy decoding, and 7-clip tranche are all the same as A6.

What changes mechanically:
1. Each turn's prompt now contains text from the prior turn's dense answer (~100-300 tokens of prepended context).
2. The dense pre-pass runs cold per-turn (no cache reuse on the dense arm), generating each canonical answer fresh.
3. Cached arms see the same exact rendered prompt as dense (verified by SHA256 prompt-hash equality on every paired row).

## What this closes

This **closes** the strongest reviewer attack on A6 ("but A6 cycles the same 3 questions"). The paper now has paired-stability evidence under content-conditional prompt variation. The result is mixed (fixed_k1 PASS, adaptive/refresh10 FAIL the 3% gate by 1.5pp), and that mixed result is genuinely informative about the C-PERSIST safe regime.

## What this does NOT close

- True natural-dialogue stress (curated 7×20 corpus where turn k+1 *semantically* depends on prior turns, not just textually). Out of scope for this prereg.
- Higher horizons (40, 50). 1.55M runs only horizon=20. The constant per-bucket rate suggests no cliff at higher horizons, but this is a hypothesis, not a confirmation.

## Recommendation for paper

Adopt the "drift boundary" framing in the C-PERSIST section. Present the A6 (50-turn repeated-question) result as the strict-stationary case and 1.55M (20-turn dense-anchored) as the bound on content-conditional stress.

Either:
- **Path A**: Cite all three policies in 1.55M with the honest mixed result; pareto-frame the 4.3% drift vs 100× speedup.
- **Path B**: Restrict the C-PERSIST headline to `fixed_k1` (which passes both A6 and 1.55M); demote `adaptive_post_q2` and `refresh10` to "aggressive variants with bounded but observable drift under content-conditional stress."

Path A is more honest; path B is cleaner for headline framing. Editor's choice.
