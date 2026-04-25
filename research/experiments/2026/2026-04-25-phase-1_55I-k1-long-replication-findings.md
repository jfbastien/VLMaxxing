---
phase: 1.55I
date: 2026-04-25
parent: research/experiments/2026/2026-04-25-phase-1_55I-k1-long-replication-prereg.md
status: landed 2026-04-25. PASS all gates. C-PERSIST K=1 confirmed multi-regime: short+medium+long n=72 with 0/72 paired drift.
---

# Phase 1.55I — K=1 long-bucket replication (FINDINGS)

**Verdict:** **C-PERSIST K=1 selective re-prefill survives the long bucket
exactly.** With the same Q1-cold / Q2-K=1 / Q3-K=1 protocol that landed
clean on short (1.55D) and medium (1.55G) at 20f, the 7-clip long-bucket
tranche returns **0/21 paired correctness diffs, 0/21 paired choice diffs,
0/14 pathological follow-up, 0/7 pathological Q3**, follow-up median
**7.23 s**, baseline-follow-up median 81.3 s, **same-class follow-up
speedup 11.24×**, peak RSS 5.94 GB. Combined with `1.55D K=1` and
`1.55G K=1`, the C-PERSIST K=1 lane now has **n=72 paired queries across
three duration regimes with 0 observed paired drift**.

## Why this run mattered

`1.55D K=1` and `1.55G K=1` both landed `0/n` paired drift at 20f short
and 20f medium respectively. The remaining open scope question was the
long bucket: persistent-KV's known basin (1.55A) is closer to long-context
behavior, so basin-style failures had been the most likely failure mode
for long-bucket K=1.

`1.55I` was the unbiased test. It also gates whether `1.55F-long` (the
adaptive long-bucket counterpart, not yet preregistered) is a sensible
follow-up.

## Setup

- Model: `Qwen2.5-VL-7B-Instruct-4bit`
- Regime: 20-frame persistent-KV long-bucket VideoMME session
- Clips: `669,711,712,737,756,758,794` (each ≥3 questions in the parquet)
- Queries: 3 per clip, session path vs matched cold baseline
- Session policy:
  - `Q1`: cold (`K=0`)
  - `Q2/Q3`: selective re-prefill with `K=1` (fixed, no adaptive)
- Runner: `scripts/run_kv_selective_reprefill_v2.py`
- Wrapper: `scripts/run_phase1_55I_k1_long_replication.sh`
- Output dir: `research/experiments/2026/artifacts/phase1_55I_k1_long_replication/`
- Auto-committed by the follow-up queue runner as `325f33b`.

## Headline results

From `pair_metrics_k1_n7.json` + `summary_k1_n7.json`:

- `n_pairs = 21`, `n_follow_up_pairs = 14`, `n_sessions = 7`
- `paired_correctness_diffs = 0/21`
- `paired_choice_diffs = 0/21`
- `pathological_follow_up_hits = 0/14`, `pathological_q3_hits = 0/7`
- `accuracy_delta_session_minus_baseline = 0.0` (CI95 `[0.0, 0.0]`)
- `q3_accuracy_delta_session_minus_baseline = 0.0` (CI95 `[0.0, 0.0]`)
- `session_follow_up_median_ms = 7231.32` (= **7.23 s**)
- `baseline_follow_up_median_ms = 81276.25` (= **81.3 s**)
- `baseline_all_query_median_ms = 81264.51` (= **81.3 s**)
- `speedup_follow_up_median_cold_over_session = 11.24×` (same-class)
- `speedup_all_query_median_cold_over_session_follow_up = 11.24×` (cross-class)
- `session_accuracy = baseline_accuracy = 7/21 = 0.333`
- `mean_follow_up_prefix_coverage = 0.941`
- `peak_rss_gb = 5.94`
- `total_wall_ms = 3898104` (= 65.0 min)

Per-Q breakdown (every cell exactly matches between session and baseline):

- Q1: session 4/7, baseline 4/7
- Q2: session 2/7, baseline 2/7
- Q3: session 1/7, baseline 1/7

The model's long-bucket accuracy (33%) is materially below short-bucket
(81%) and medium-bucket (53%), but session and baseline agree exactly
on every row — including the wrong rows.

## Preregistered verdicts

### H1 — long-bucket fidelity remains tightly bounded

**EARNED.** Acceptance: paired correctness diffs `<= 2/21`, paired choice
diffs `<= 3/21`. Observed: **0/21 and 0/21** — the tightest possible value
the gate can take.

### H1' — exact match still survives on the long bucket

**EARNED.** `0/21` correctness diffs and `0/21` choice diffs across the
21 paired queries. Combined with `1.55D K=1` (0/21 short) and `1.55G K=1`
(0/30 medium), the multi-regime claim becomes **n=72 paired with 0
observed drift, 0 pathological**.

### H2 — pathological follow-up attractors remain rare

**EARNED.** Acceptance: pathological follow-up `<= 2/14`, Q3 `<= 1/7`.
Observed **0/14 and 0/7**. The basin onset that affects long-context
persistent-KV is not triggered by K=1 selective re-prefill on this tranche.

### H3 — K=1 still preserves a meaningful local speedup

**EARNED.** Acceptance: `speedup_all_query_median >= 6.0×`. Observed
**11.24×**. Comparable to short (9.48×) and medium (10.76×); the
long-bucket prefill being slightly larger than medium produces marginally
higher speedup ratios.

### H4 — memory remains within the local operating envelope

**EARNED.** Acceptance: `peak_rss_gb <= 7.5`. Observed **5.94 GB** —
between 1.55D K=1 short (4.886 GB) and 1.55G K=1 medium (6.097 GB), with
plenty of margin under the 9 GB safe-RSS guard.

### H5 — the long tranche stays above the signal floor

**EARNED.** Acceptance: baseline accuracy `>= 0.30`. Observed **0.333**.
This is the tightest signal floor in the C-PERSIST series — long-bucket
VideoMME on Qwen 7B-4bit is hard. But 33% is comfortably above the floor
and the accuracy is faithfully preserved by K=1.

## Combined C-PERSIST K=1 lane (after this run)

| run | regime | n | paired diffs | speedup (same-class) | pathology | RSS | baseline acc |
|---|---|---|---|---|---|---|---|
| 1.55D K=1 | 20f short, 7 clips | 21 | 0/21 / 0/21 | 9.48× | 0/14 fu, 0/7 q3 | 4.886 GB | 0.810 |
| 1.55G K=1 | 20f medium, 10 clips | 30 | 0/30 / 0/30 | 10.76× | 0/20 fu, 0/10 q3 | 6.097 GB | 0.533 |
| 1.55I K=1 | 20f long, 7 clips | 21 | 0/21 / 0/21 | 11.24× | 0/14 fu, 0/7 q3 | 5.940 GB | 0.333 |
| **combined** | **all 3 regimes** | **72** | **0/72 / 0/72** | **9.48-11.24×** | **0/48 fu, 0/24 q3** | 4.9-6.1 GB | 0.33-0.81 |

This is a clean three-regime C-PERSIST K=1 result.

Rule-of-three caveat: with 0 observed diffs across n=72, the upper
one-sided 95% CI on the diff rate is ≈ **4.1%**. The paper claim should
remain "no observed paired drift" but the sample size has tripled vs the
prior short-only (n=21) point and the regime scope has broadened from
short-only to all three duration regimes.

## Why the speedup ratio is so uniform across regimes

The same-class follow-up speedup is remarkably stable: 9.48× / 10.76× /
11.24× across short / medium / long. This suggests:

- **K=1 cache reuse is prefill-dominated**: the saved cost equals
  `(prompt_tokens − tail_re-prefill_tokens) × per-token-prefill-cost`
- across regimes the prompt token count varies (~3000 short, ~8100 medium,
  ~8130 long at 20f) but the *fraction* of tokens that need re-prefill
  is constant (`≈ 1/N_frames = 5%`)
- so the speedup ratio is roughly `1 / (re-prefill_fraction +
  decode_fraction)`, and the slight scaling with regime reflects how
  much of cold-arm cost is in prefill vs decode (longer prefills push
  the ratio up)

This is good news for the paper: the C-PERSIST K=1 efficiency claim is
**not regime-specific**, it's a structural property of the policy.

## Implications for the paper

1. **C-PERSIST K=1 lane closes scope-wise.** No further regime-extension
   experiments are needed for K=1 itself. The paper can now state the
   K=1 result on all three duration regimes with consistent ~10× speedup
   and 0 observed paired drift on n=72.

2. **The adaptive lane (1.55F) remains stronger.** With short-bucket
   24.91× vs K=1's 9.48× on the same 7-clip tranche, the adaptive policy
   continues to dominate. The natural three-regime extension of adaptive
   (1.55F-medium, 1.55F-long, 1.55F-32f) is now even more clearly the
   right paper-headline lane.

3. **The 11.24× long-bucket K=1 number is publishable on its own.**
   Together with the 1.30Z falsification of the duration-conditioned
   admission policy, the paper now has:
   - a clean negative on the 1.30 lane (admission policy doesn't generalize
     at kr_Q0=0.67)
   - a clean positive on the 1.55 lane (K=1 selective re-prefill works at
     all three regimes)
   - the cleanest mechanism story the paper has had so far

4. **Long-bucket model accuracy is the constraint, not C-PERSIST K=1.**
   At 0.333 baseline accuracy, the long-bucket regime is dominated by
   the model's intrinsic difficulty, not by streaming-vs-cold differences.
   This is a separate paper-table cell — "long-bucket VideoMME at 20f
   Qwen 7B-4bit is intrinsically hard" — and is consistent with prior
   C-CEILING / 32f frame-scaling findings.

## Anomalies and notes

- The session and baseline accuracies are *byte-identical* at 7/21
  including the per-row choices and responses. The K=1 path produces
  bit-equivalent generation under greedy decode to the cold baseline
  on every paired row.
- The bootstrap CI on `accuracy_delta_session_minus_baseline` is
  degenerate `[0.0, 0.0]` because every paired row contributes 0 to the
  delta. Same observation as 1.55D and 1.55F: the bootstrap is
  uninformative on a degenerate-zero distribution.
- Long-bucket session-follow-up median (7.23s) is *lower* than short-bucket
  (10.14s) for the same K=1 protocol. This is because long-bucket
  follow-ups have higher prefix coverage (94.1% mean) and mostly
  cache-served tokens, so the K=1 tail re-prefill has fewer tokens to
  process.

## What this rules out and what it does not

**Rules out:**
- "C-PERSIST K=1 is short-only." Falsified by short+medium+long zero-drift
  evidence on n=72.
- "Long-bucket persistent-KV automatically triggers basin failures."
  Falsified by 0 pathological outputs on 14 long-bucket follow-ups
  (compare 1.55E's 7/7 Q3 catastrophe at K=0).

**Does not rule out:**
- 32f depth boundary failures (`1.55H` will probe this for fixed K=1).
- Adaptive long-bucket failures (`1.55F-long` is a future test; not yet
  preregistered).
- Larger-n drift detection: at n=72 with 0 observed diffs, drift rates up
  to ~4.1% are statistically consistent with our data.

## Pending follow-ups

- **`1.55F-long` (NEW; preregister, conditional on this finding):** apply
  the 1.55F adaptive policy to the same 7-clip long tranche. If it
  passes, the adaptive C-PERSIST result becomes three-regime as well.
  ~60-90 min compute.
- **`1.55F-medium` (preregistered 8e44ee2):** still ready. ~70 min.
- **Per-bucket stratified speedup analysis (analysis-only):** combine
  the 1.55D + 1.55G + 1.55I follow-up timings to confirm the
  prefill-dominance hypothesis at higher precision.
- **`1.55F-32f` (NEW; preregister, conditional on `1.55H`):** depth
  boundary version of the adaptive policy.

## Decisions

- Paper section C-PERSIST should now cite combined n=72 short+medium+long
  with 0/72 paired diffs at fixed K=1, plus the 1.55F adaptive headline
  at 24.91× on short-bucket.
- `registry.md` 1.55I row updates to `landed-PASS`.
- The C-PERSIST K=1 lane is paper-complete in scope; further experiments
  in that lane should be limited to depth boundary (1.55H) and adaptive
  variants (1.55F-*).
