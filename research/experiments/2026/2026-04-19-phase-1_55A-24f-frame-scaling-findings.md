# Phase 1.55A-24f — Persistent-KV safe-regime bisection (FINDINGS)

**Status:** findings, 2026-04-19. Bisection point on the 1.55A safe-
regime boundary between 16f (clean) and 32f (broken).

**Parent prereg:** `2026-04-19-phase-1_55A-24f-frame-scaling-prereg.md`

**Companion findings:**
- 8f: `2026-04-19-phase-1_55A-persistent-kv-findings.md`
- 16f: `2026-04-19-phase-1_55A-16f-frame-scaling-findings.md`
- 32f: `2026-04-19-phase-1_55A-32f-frame-scaling-findings.md`

## Headline

**H2'''.cliff:** at 24f (~9.7k prefill tokens) the cache-reuse failure
is qualitatively identical to 32f. **The safe-regime boundary sits
between 6.5k and 9.7k prefill tokens**, not past 9.7k. The failure is
a sharp cliff, not a gradient.

| Hypothesis | Prereg | Measured | Verdict |
|---|---|---|---|
| H1''' speedup | [95×, 180×] | **121.58×** | EARN |
| H2''' accuracy | Δ ∈ [−0.05, 0.05] | **Δ = −0.429** | REJECT (cliff) |
| H3''' prefix coverage | ≥ 0.90 | **0.9940** | EARN |
| H4''' peak RSS | ≤ 12 GB | **3.30 GB** | EARN |

## Per-query stratification

| Stratum | n | Session correct | Baseline correct | Δ |
|---|---|---|---|---|
| Q1 (cold first-query) | 7 | 7/7 (100%) | 7/7 (100%) | 0 |
| Q2 (cache follow-up #1) | 7 | 1/7 (14.3%) | 6/7 (85.7%) | −0.71 |
| Q3 (cache follow-up #2) | 7 | 1/7 (14.3%) | 5/7 (71.4%) | −0.57 |
| All follow-ups | 14 | 2/14 (14.3%) | 11/14 (78.6%) | −0.64 |

Identical per-stratum numbers to 32f. Session cache-path follow-ups
emit the literal token `addCriterion` at 14/14 queries. Baseline Q1
accuracy at 24f matches baseline Q1 at 32f (the model's content
understanding is stable; only the cache-reuse decoder trajectory is
broken).

## Updated scaling surface

| Frames | Prefill tokens | First-query (s) | Follow-up (ms) | Speedup | Δacc |
|---|---|---|---|---|---|
| 8  | ~3 270 | 38.5 | 815 | 47.23× | −0.048 |
| 16 | ~6 500 | 73.5 | 807 | 91.06× | **0.000** |
| **24** | **~9 700** | **108.9** | **864** | **121.58×** | **−0.429** |
| 32 | ~12 920 | 163.2 | 1008 | 149.88× | −0.429 |

**Speedup curve continues linearly** across all four points
(47×→91×→122×→150×; first-query 38.5→73.5→108.9→163.2 s, ratios
1.91× / 1.48× / 1.50×). Prefill-dominance mechanism confirmed on
4 points.

**Fidelity cliff is localized:** Δacc jumps from 0.000 at 16f
(6.5k tokens) to −0.429 at 24f (9.7k tokens). Between these two
points, cache-reuse integrity breaks completely. The 24f and 32f
failure statistics are numerically identical (9/21 session, 18/21
baseline, 2/14 follow-up, all follow-ups emit `addCriterion`), so
whatever causes the failure saturates once it triggers.

## Mechanism update

The cliff-versus-gradient distinction favours **threshold mechanisms**
over **accumulation mechanisms**:

- **Supported:** 4-bit KV quantization has a fixed error budget; once
  enough attention-score noise accumulates, the argmax flips into a
  single-token basin. Saturates once triggered.
- **Supported:** M-RoPE frequency bands have a trained support range;
  specific long-position lookups become OOD past a cutoff.
- **Weakened:** Gradual attention-pattern drift with frame count —
  would predict a smooth Δacc descent from 16f to 32f, not a cliff.
- **Weakened:** Suffix-length effects — all runs have 40-90 suffix
  tokens; behaviour is independent of suffix length across 16f/24f/32f.

## Next queued

20f (~8 100 prefill tokens) is the midpoint between 16f (clean) and
24f (broken). One of three outcomes:

- **H2''''.clean (Δacc ∈ [−0.05, 0.05])** — boundary is between
  8.1k and 9.7k. Narrow further via 22f or accept ~8-9k as the safe
  budget.
- **H2''''.cliff (Δacc ≤ −0.30, 14/14 emit artifact)** — boundary is
  between 6.5k and 8.1k. Narrow further via 18f.
- **H2''''.gradient** — partial degeneracy in the 8.1k regime.
  Weakens the threshold hypothesis slightly.

Run launched concurrently with this document.

## Paper implications update

The claim #14 safe-budget language tightens from "≤16f" to **"safe
regime ends between 16f and 24f on Qwen 2.5-VL-7B-Instruct-4bit; the
transition is a qualitative cliff, not a graceful drift."** This
scopes the deployment narrative precisely and preserves the 91× /
16f / 0.8 s / sub-second-follow-up claim.

## Wall-clock

Actual: 3281 s (55 min). Matched prereg prediction.

## Artifacts

- Summary: `research/experiments/2026/artifacts/phase1_55A_24f_frame_scaling/summary.json`
- Session JSONL: `.../session_qwen7b_n7.jsonl`
- Baseline JSONL: `.../baseline_qwen7b_n7.jsonl`
- Run log: `.../run.log`
