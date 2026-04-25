---
phase: 1.55H
date: 2026-04-25
parent: research/experiments/2026/2026-04-25-phase-1_55H-k1-32f-short-probe-prereg.md
status: landed 2026-04-25. PASS all gates. K=1 selective re-prefill survives the 32f depth boundary on the 7-clip short tranche with 0/21 paired drift and 20.37× same-class follow-up speedup.
---

# Phase 1.55H — K=1 short-bucket 32f boundary probe (FINDINGS)

**Verdict:** **C-PERSIST K=1 selective re-prefill survives the 32f depth
boundary exactly.** With the same Q1-cold / Q2-K=1 / Q3-K=1 protocol that
landed clean at 20f short (1.55D), 20f medium (1.55G), and 20f long (1.55I),
the 7-clip short-bucket tranche at 32 frames returns **0/21 paired
correctness diffs, 0/21 paired choice diffs, 0/14 follow-up pathological,
0/7 Q3 pathological**, follow-up median **6.78 s**, baseline-follow-up
median 138.2 s, **same-class follow-up speedup 20.37×**, peak RSS 5.82 GB.

Combined with `1.55D + 1.55G + 1.55I + 1.55H`, the C-PERSIST K=1 lane is
now **n=93 paired short+medium+long+32f-short with 0/93 observed paired
drift, 9.48-20.37× same-class speedup**.

## Why this run mattered

The known persistent-KV basin (1.55A) becomes more dangerous at deeper
prefix length: 7B Qwen-VL has shown basin behavior at 20f long-context
and was hypothesized to be most stressed at 32f. `1.55H` is the depth
boundary probe for fixed K=1.

If `1.55H` had failed (drift or pathology), the C-PERSIST K=1 envelope
would have been bounded to 20f. It didn't fail.

## Setup

- Model: `Qwen2.5-VL-7B-Instruct-4bit`
- Regime: **32-frame** persistent-KV short-bucket VideoMME session
- Clips: `037,100,116,120,158,160,210` (same 7-clip tranche as
  `1.55D K=1` short for direct depth comparison)
- Queries: 3 per clip, session path vs matched cold baseline
- Session policy:
  - `Q1`: cold (`K=0`)
  - `Q2/Q3`: selective re-prefill with `K=1` (fixed, no adaptive)
- Runner: `scripts/run_kv_selective_reprefill_v2.py`
- Wrapper: `scripts/run_phase1_55H_k1_32f_short_probe.sh`
- Output dir: `research/experiments/2026/artifacts/phase1_55H_k1_32f_short_probe/`
- Auto-committed by the follow-up queue runner as `facd82e`.

## Headline results

From `pair_metrics_k1_n7.json` + `summary_k1_n7.json`:

- `n_pairs = 21`, `n_follow_up_pairs = 14`, `n_sessions = 7`
- `paired_correctness_diffs = 0/21`
- `paired_choice_diffs = 0/21`
- `pathological_follow_up_hits = 0/14`, `pathological_q3_hits = 0/7`
- `accuracy_delta_session_minus_baseline = 0.0` (CI95 `[0.0, 0.0]`)
- `q3_accuracy_delta_session_minus_baseline = 0.0` (CI95 `[0.0, 0.0]`)
- `session_follow_up_median_ms = 6783.62` (= **6.78 s**)
- `baseline_follow_up_median_ms = 138215.52` (= **138.2 s**)
- `baseline_all_query_median_ms = 135019.33` (= **135.0 s**)
- `speedup_follow_up_median_cold_over_session = 20.37×` (same-class)
- `speedup_all_query_median_cold_over_session_follow_up = 19.90×` (cross-class)
- `session_accuracy = baseline_accuracy = 18/21 = 0.857`
- `mean_follow_up_prefix_coverage = 0.964`
- `peak_rss_gb = 5.82`
- `total_wall_ms = 5016464` (= 83.6 min)
- `frame_count = 32` (the depth boundary)

Per-Q breakdown (every cell exactly matches between session and baseline):

- Q1: session 7/7, baseline 7/7
- Q2: session 6/7, baseline 6/7
- Q3: session 5/7, baseline 5/7

The 32f short-bucket tranche actually has *higher* model accuracy (85.7%)
than its 20f counterpart (1.55D K=1: 81%). This is consistent with prior
1.41 frame-scaling findings: 32f short benefits from more visual context.
What's notable is that K=1 preserves this elevated accuracy *exactly*.

## Preregistered verdicts

### H1 — K=1 remains materially better than the raw 32f persistent-KV path

**EARNED dramatically.** Acceptance: paired correctness diffs `<= 3/21`,
paired choice diffs `<= 4/21`. Observed: **0/21 and 0/21**. Far below
even the loose drift band the prereg admitted for the 32f boundary.

### H2 — pathological follow-up attractors are not the dominant mode

**EARNED.** Acceptance: pathological follow-up `<= 3/14`, observed
**0/14**. The 32f depth does not push the model into basin behavior under
K=1 selective re-prefill.

### H3 — K=1 still preserves a large local speedup

**EARNED dramatically.** Acceptance:
`speedup_all_query_median_cold_over_session_follow_up >= 8.0×`. Observed
**19.90×** — 2.5× above the gate. The reason is straightforward: at 32f,
cold prefill costs ~135 s/query, while K=1 follow-ups stay near 7 s.
The longer the prefill, the bigger the K=1 savings ratio. This is the
same prefill-dominance scaling we observed across the 20f short/medium/long
results.

### H4 — memory remains within the local single-run envelope

**EARNED.** Acceptance: `peak_rss_gb <= 6.5`. Observed **5.82 GB** —
between 1.55I long (5.94 GB) and 1.55G medium (6.10 GB), comfortable
under the 9 GB safe-RSS guard.

## Combined C-PERSIST K=1 picture (after this run)

| run | regime | n | paired diffs | speedup (same-class) | pathology | RSS | baseline acc |
|---|---|---|---|---|---|---|---|
| 1.55D K=1 | 20f short, 7 clips | 21 | 0/21 / 0/21 | 9.48× | 0/14, 0/7 | 4.886 GB | 0.810 |
| 1.55G K=1 | 20f medium, 10 clips | 30 | 0/30 / 0/30 | 10.76× | 0/20, 0/10 | 6.097 GB | 0.533 |
| 1.55I K=1 | 20f long, 7 clips | 21 | 0/21 / 0/21 | 11.24× | 0/14, 0/7 | 5.940 GB | 0.333 |
| **1.55H K=1** | **32f short, 7 clips** | **21** | **0/21 / 0/21** | **20.37×** | **0/14, 0/7** | **5.821 GB** | **0.857** |
| **combined** | **3-regime + depth** | **93** | **0/93 / 0/93** | **9.48-20.37×** | **0/62, 0/31** | 4.9-6.1 GB | 0.33-0.86 |

This is now a four-cell C-PERSIST K=1 result spanning short/medium/long
regimes at 20f *plus* the 32f depth boundary at short. The rule-of-three
upper one-sided 95% CI on the diff rate at n=93 is **≈ 3.2%**.

## Why the 32f speedup is so much higher than 20f

The 32f speedup of 20.37× is roughly *2× higher* than the 20f speedups
(9.48-11.24×). Mechanistically:

- 32f short prefill: ~12,930 prompt tokens (vs ~3,000 at 20f short and
  ~8,100 at 20f medium/long)
- K=1 cache reuse: ~95% of tokens served from cache regardless of frame
  count
- net wall-time saving: `~95% × prefill_tokens × per-token-prefill-cost`
- so the speedup ratio scales with how much of the cold-arm's median
  is in prefill (which grows with prefix length)

**This is good news for deployment**: K=1 selective re-prefill becomes
*more* useful as context length grows, not less. The 32f point gives us
the first long-context efficiency data point and it's the strongest ratio
in the C-PERSIST series.

## Implications for the paper

1. **The C-PERSIST K=1 envelope is now four-cell, scope-complete.**
   The paper can state K=1 selective re-prefill at 0/93 paired drift,
   ~10-20× same-class follow-up speedup across short/medium/long regimes
   at 20f plus the 32f depth boundary at short. This is a substantially
   stronger paper claim than the prior short-only or short+medium framing.

2. **The 32f depth boundary is open, not bounded.** We had hypothesized
   that 32f might trigger basin failures. It didn't. The next natural
   depth probe is **32f at medium or long bucket**, which would test the
   full content × depth grid, but that's compute that wasn't in this
   queue.

3. **Adaptive 1.55F-32f is now a strong follow-up candidate.** With both
   `1.55F` (20f short adaptive) and `1.55H` (32f short fixed-K=1)
   landing clean, the 32f adaptive variant is the natural intersection.
   If it lands at the predicted ~30-35× speedup, that's the strongest
   single-cell efficiency result the paper has.

## Anomalies and notes

- The 32f session and baseline accuracies are byte-identical at 18/21
  including per-row choices and responses. K=1 produces bit-equivalent
  generation under greedy decode at 32f.
- 32f short Q1 cold prefill is ~131-147 s vs 1.55D K=1 short Q1's
  ~80-90 s, so 32f roughly doubles the cold-arm prefill cost as expected
  (4× more tokens at lower-than-linear scaling).
- The bootstrap CI on `accuracy_delta` is degenerate `[0.0, 0.0]` because
  every paired row contributes 0; same as 1.55D, 1.55F, 1.55G, 1.55I.

## What this rules out and what it does not

**Rules out:**
- "C-PERSIST K=1 collapses at 32f." Falsified.
- "Long-context Qwen-VL basin is automatic at any deep prefix." Falsified
  for 32f short.

**Does not rule out:**
- 32f long-bucket behavior (`1.55H-long` would be a future test;
  computationally expensive at 32f long).
- Adaptive policy at 32f (`1.55F-32f`, prereg-pending).
- Larger-n drift detection: at n=93 with 0 observed diffs, drift rates up
  to ~3.2% are statistically consistent.

## Pending follow-ups

- **`1.55F-32f` (NEW; preregister, conditional on this finding):** apply
  the 1.55F adaptive policy to the same 32f short tranche. Expected
  speedup ~30-35× given that adaptive ÷ fixed ratio is ~2.6× across
  regimes (1.55F/1.55D), and 1.55H fixed is 20.37×. ~1.5-2h compute.
- **`1.55F-medium` (already preregistered, 8e44ee2):** still pending.
- **`1.55F-long` (already preregistered, 8d57474):** still pending.
- **Per-bucket × per-depth stratified speedup analysis (analysis-only):**
  combine 1.55D/G/I/H follow-up timings to fit a model of speedup vs
  prompt token count. The expected functional form is roughly
  `speedup ≈ const + α × prompt_tokens`, which the paper can use to
  predict deployment-time C-PERSIST efficiency in advance.

## Decisions

- Paper section C-PERSIST should now cite combined n=93
  short+medium+long+32f-short with 0/93 paired diffs at fixed K=1, plus
  the 1.55F adaptive headline at 24.91× on 20f short.
- `registry.md` 1.55H row updates to `landed-PASS`.
- The C-PERSIST K=1 envelope is paper-complete in scope-and-depth at
  short. Further fixed-K=1 experiments would only be needed for
  32f-medium or 32f-long; lower priority than the adaptive variants
  (1.55F-medium, 1.55F-long, 1.55F-32f).
