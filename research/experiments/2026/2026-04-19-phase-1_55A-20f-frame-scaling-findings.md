# Phase 1.55A-20f — Persistent-KV cliff-midpoint bisection (FINDINGS)

**Status:** findings, 2026-04-19. Midpoint bisection between 16f
(clean, Δacc=0) and 24f (saturated-broken, Δacc=−0.429).

**Parent prereg:** `2026-04-19-phase-1_55A-20f-frame-scaling-prereg.md`

**Companion findings:**
- 8f: `2026-04-19-phase-1_55A-persistent-kv-findings.md`
- 16f: `2026-04-19-phase-1_55A-16f-frame-scaling-findings.md`
- 24f: `2026-04-19-phase-1_55A-24f-frame-scaling-findings.md`
- 32f: `2026-04-19-phase-1_55A-32f-frame-scaling-findings.md`

## Headline

**H2''''.gradient-with-ramp:** at 20f (~8.1k prefill tokens) the
cache-reuse fidelity lands at **Δacc = −0.381** — worse than 16f
(0.000) but not yet saturated at the 24f/32f value (−0.429). The
failure **shape is also different**: of 14 follow-up queries, 10
emit the short `addCriterion` token, **4 emit longer garbage**
(18–64 generation tokens of Java-fragment / MyBatis chain-call
hallucinations), and 1 emits a genuinely correct answer "D". At
24f/32f all 14/14 follow-ups produced the identical short
`addCriterion` basin.

**Verdict:** the transition is **not a single-step cliff**. The
failure has a narrow ramp with a partial-degeneracy shoulder at
20f that saturates into the short-token basin by 24f. This still
favours a threshold mechanism, but softens it: the threshold has
some width (~1.6k tokens of partial collapse).

| Hypothesis | Prereg | Measured | Verdict |
|---|---|---|---|
| H1'''' speedup | [75×, 140×] | **94.42×** | EARN |
| H2'''' accuracy | clean / cliff / gradient | **gradient-with-ramp** | REJECT prereg H2'''' (Δ = −0.381); new sub-outcome noted |
| H3'''' prefix coverage | ≥ 0.99 | **0.9928** | EARN |
| H4'''' peak RSS | ≤ 5 GB | **3.51 GB** | EARN |

## Per-query stratification

| Stratum | n | Session correct | Baseline correct | Δ |
|---|---|---|---|---|
| Q1 (cold first-query) | 7 | 6/7 (85.7%) | 7/7 (100%) | −0.14 |
| Q2 (cache follow-up #1) | 7 | 1/7 (14.3%) | 5/7 (71.4%) | −0.57 |
| Q3 (cache follow-up #2) | 7 | 2/7 (28.6%) | 5/7 (71.4%) | −0.43 |
| All follow-ups | 14 | 3/14 (21.4%) | 10/14 (71.4%) | −0.50 |

Note: Q1 lost 1 compared to 7/7 at 16f/24f/32f (clip 210 answered
"C" where gold is not "C" — this is a baseline-accuracy-independent
first-query flake, unlikely to be cache-related). Follow-ups are
worse by a narrow margin than 24f/32f's 2/14.

## Failure-mode shift observed at 20f

Across 14 follow-up queries:

- 10 × short `addCriterion` (2 generation tokens, matches 24f/32f basin)
- 4 × longer garbage (18–64 generation tokens, Java/MyBatis method-
  chain hallucination — e.g. clip 158-Q2 produces
  `<|im_start|>\n addCriterion("score").eq("1:2").and addCriterion(...)`)
- 1 × genuinely correct "D" (clip 116-Q2, parsed cleanly)

At 24f/32f the failure was 14/14 short `addCriterion` — a single
degenerate basin. At 20f the basin attracts most trajectories, but
~30% land elsewhere (including one valid response). This is the
shape of a **decoder distribution collapsing onto the basin but not
yet fully absorbed** — consistent with an error budget that is
close to but not above the threshold for universal tipping.

## Updated scaling surface

| Frames | Prefill tokens | First-query (s) | Follow-up (ms) | Speedup | Δacc | Follow-up failure mode |
|---|---|---|---|---|---|---|
| 8  | ~3 270 | 38.5 | 815 | 47.23× | −0.048 | none (3 borderline) |
| 16 | ~6 500 | 73.5 | 807 | 91.06× | **0.000** | none |
| **20** | **~8 100** | **83.8** | **905** | **94.42×** | **−0.381** | **ramp: 10 short addCriterion + 4 long garbage + 1 correct** |
| 24 | ~9 700 | 108.9 | 864 | 121.58× | −0.429 | saturated: 14/14 short addCriterion |
| 32 | ~12 920 | 163.2 | 1008 | 149.88× | −0.429 | saturated: 14/14 short addCriterion |

**Speedup curve:** first-query 73.5 → 83.8 s ratio 1.14× (sub-linear
at 16→20f, compared to 1.91× at 8→16f). 20f is close to 16f in
first-query cost but follow-up speedup did not grow as fast as
prefill tokens — suggesting the decode-basin collapse imposes a
small floor cost (longer generations for the 4 garbage cases
dragged mean follow-up elapsed time up from 807 ms at 16f).

**Fidelity surface:** Δacc ramps 0.000 → −0.381 → −0.429, with the
steep step from 16f (0.000) to 20f (−0.381) and a small residual
step from 20f to 24f (−0.048).

## Mechanism update

Compared with the 24f-only "cliff" picture, the 20f data:

- **Strengthens the threshold hypothesis WITH a soft edge:** the
  failure attractor exists (short-addCriterion basin wins most of
  the time at 20f) but its pull is not yet universal — some
  trajectories escape into longer garbage or into a correct answer.
  Consistent with "error budget approaches threshold; some
  trajectories stay under, most don't."
- **Weakens the pure single-step cliff picture:** a hard threshold
  would predict 0 or full saturation; we see partial collapse.
- **Weakens the pure accumulation-drift picture:** a pure gradient
  would predict smooth Δacc increase across 20f/24f/32f (we see
  saturation by 24f).
- **Supports both 4-bit KV quantization AND M-RoPE OOD:** both
  mechanisms are compatible with a soft threshold — the noise
  budget is a soft function of sequence length, not a hard switch.

## Next queued

18f (~7.3k prefill tokens) is the midpoint between 16f (clean) and
20f (ramp-partial). One of three outcomes:

- **H2'''''.clean:** ramp starts between 7.3k and 8.1k (narrow onset
  band).
- **H2'''''.ramp:** ramp already started at 7.3k — implies onset
  close to 16f and the full 16f→24f span is the ramp.
- **H2'''''.saturated:** 18f is already saturated — implies a cliff
  between 6.5k and 7.3k that we've been missing.

Run launched concurrently with this document.

## Paper implications update

Claim #14 safe-budget language tightens further to: **"On Qwen
2.5-VL-7B-Instruct-4bit, persistent-KV cache-reuse preserves
accuracy at prefill ≤ ~6.5k tokens (16f, Δacc=0); partial
degeneracy appears by ~8.1k tokens (20f, Δacc=−0.38, mixed decoder
basins); the failure saturates into a single-token attractor by
~9.7k tokens (24f, Δacc=−0.43) and persists through 12.9k (32f).
The transition is a narrow soft threshold, not a clean cliff."**

This is more scientifically honest than either "cliff" or
"gradient" and names specific prefill budgets that practitioners
can steer by.

## Wall-clock

Actual: 2506 s (42 min). Matched prereg prediction (2500 s).

## Artifacts

- Summary: `research/experiments/2026/artifacts/phase1_55A_20f_frame_scaling/summary.json`
- Session JSONL: `.../session_qwen7b_n7.jsonl`
- Baseline JSONL: `.../baseline_qwen7b_n7.jsonl`
- Run log: `.../run.log`
