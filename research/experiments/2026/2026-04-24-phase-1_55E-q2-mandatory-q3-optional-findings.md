---
phase: 1.55E
date: 2026-04-24
parent: research/experiments/2026/2026-04-24-phase-1_55E-q2-mandatory-q3-optional-prereg.md
artifacts:
  - research/experiments/2026/artifacts/phase1_55E_adaptive_reprefill_q2_k1_q3_k0/
status: CLOSED-NEGATIVE. Q2 survives, but dropping selective re-prefill on Q3 reintroduces the pathological basin.
---

# Phase 1.55E — Adaptive selective re-prefill (`Q2=K1`, `Q3=K0`) findings

## Headline

The simplest adaptive extension of the landed `1.55D K=1` frontier does
**not** work.

`Q2=K1` remains clean and fully correct, but `Q3=K0` reintroduces the
same pathological follow-up behavior that `1.55D` was built to remove.

## Setup

- Model: `Qwen2.5-VL-7B-Instruct-4bit`
- Regime: 20-frame persistent-KV short-bucket VideoMME session
- Clips: `037,100,116,120,158,160,210`
- Queries: 3 per clip, matched cold baseline
- Policy:
  - `Q1`: cold / retained full-cache path
  - `Q2`: selective re-prefill with `K=1`
  - `Q3`: no selective re-prefill (`K=0`)
- Output dir:
  `research/experiments/2026/artifacts/phase1_55E_adaptive_reprefill_q2_k1_q3_k0/`

## Results

From `summary_k1_n7.json` plus paired row analysis against the matched
baseline in the same artifact directory:

- `session_accuracy = 15/21 = 0.7143`
- `baseline_accuracy = 17/21 = 0.8095`
- `accuracy_delta_session_minus_baseline = -0.0952`
- `session_follow_up_accuracy = 9/14 = 0.6429`
- `baseline_follow_up_accuracy = 11/14 = 0.7857`
- `session_follow_up_median (= paired session-follow-up median) = 13.472 s`
- paired cold-follow-up median `= 97.215 s`
- paired all-query cold median `= 97.264 s`
- paired correctness diffs `= 4/21`
- paired answer-choice diffs `= 6/21`
- paired cold-follow-up / session-follow-up speedup `= 7.22×`
- paired all-query cold / session-follow-up speedup `= 7.22×`
- `peak_rss_gb = 4.555`

Query-index split:

- `Q2`: `7/7` correct, `0/7` pathological-like outputs
- `Q3`: `2/7` correct, `7/7` pathological-like outputs

The failure mode is highly concentrated:

- all seven `Q3` outputs collapse back into the `addCriterion` /
  SQL-like basin or close variants
- two of those `Q3` rows become parse failures outright
- only two Q3 rows remain correct, and both are "correct by luck" on
  pathological text rather than clean answer recovery

The four paired correctness regressions are:

- `videomme:short:037-3`
- `videomme:short:116-3`
- `videomme:short:160-3`
- `videomme:short:210-3`

## Preregistered verdicts

### H1 — exact paired fidelity survives

**FALSIFIED.**

Observed:

- `Δacc = -0.0952`
- paired correctness diffs `= 4/21`
- paired answer-choice diffs `= 6/21`

### H2 — deployment-speed crossover lands

**FALSIFIED.**

Observed:

- paired cold-follow-up / session-follow-up speedup `= 7.22×`
- paired all-query cold / session-follow-up speedup `= 7.22×`

This is faster than fixed `K=1` on the dropped-`Q3` queries, but still
well below the preregistered `>= 10×` gate.

### H3 — basin control survives

**FALSIFIED strongly.**

Observed:

- pathological-like `Q3` outputs `= 7/7`
- parse failures on follow-ups `= 2/14`

So the apparent speed win is bought by stepping directly back into the
pathological basin.

### H4 — memory stays in budget

**EARNED.**

Observed:

- `peak_rss_gb = 4.555`

## Interpretation

This run resolves the highest-value adaptive question cleanly:

- `Q2` is the real rescue point
- `Q3` is **not** safely dispensable under a simple retained-full-cache path

That is stronger than a generic "adaptive policy did not help" claim.
It says the live problem is specifically the **state presented to Q3**,
not the existence of adaptive refresh in the abstract.

In other words:

1. `1.55D K=1` remains the best local fixed policy.
2. The simplest adaptive omission (`Q2=K1`, `Q3=K0`) is a real negative.
3. Any further adaptive 1.55 continuation must change the **Q3 state
   construction** or use a richer admission criterion than "always skip
   Q3 refresh."

## Baseline note

The paired verdict above uses the matched baseline rerun inside the
`1.55E` artifact directory, which is the correct preregistered control.

One cross-run caveat is worth recording explicitly: compared with the
earlier `1.55D K=1` baseline artifact, one false item
(`videomme:short:120-3`) flipped wrong-answer choice (`A` vs `D`) while
remaining incorrect in both runs. That does **not** change the
preregistered `1.55E` outcome, but it means cross-run answer-choice
comparisons between `1.55D` and `1.55E` should be read as approximate
unless they are re-paired to a single baseline.

## Decision

Do not spend more time on blind adaptive omission policies in this lane.

If `1.55` continues, the next experiment should be one of:

1. a richer Q3 admission rule with an explicit risk signal, or
2. a different Q3 state-construction path that preserves the post-Q2
   repair instead of jumping back to the retained-full-cache path.

What should **not** be next:

- another "skip refresh on some fixed query index" variant,
- another blind fixed-K sweep,
- or paper language implying that adaptive refresh is still an
  untested near-miss.
