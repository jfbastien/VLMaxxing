---
phase: 1.51V
date: 2026-04-21
parent: research/experiments/2026/2026-04-21-phase-1_51V-session3-prereg.md
prior:
  - research/experiments/2026/2026-04-21-phase-1_51V-holdout-findings.md
  - research/experiments/2026/2026-04-21-phase-1_51V-expansion-findings.md
status: CONFIRMED — all four preregistered hypotheses pass, paper-table promotion unlocked
---

# 1.51V session 3 findings — V-only holdout pair on VideoMME 8f (EXP17/EXP18)

## Summary

The V-only VideoMME-8f holdout gap identified by codex round-24 (must-do #1) is
closed. All four preregistered hypotheses pass; the paper's VideoMME-8f V-only
cell can drop the "dev-only n=30" footnote.

| Hypothesis                 | Predicted / Gate      | Observed          | Verdict     |
|----------------------------|-----------------------|-------------------|-------------|
| H_holdout_vonly_e2e (primary) | ≥ 1.05× (prereg spec: EXP17 dense / EXP18 pruned) | **1.113×**       | **CONFIRMED** |
| H_holdout_vred (primary)   | V_red ∈ [0.35, 0.45]  | **0.413**        | **CONFIRMED** |
| H_holdout_thermal (process) | |decode_ms Δ| < 2%    | **1.53%**        | **PASSES**    |
| H_holdout_accuracy         | Δ ∈ [−0.05, +0.05]    | **0.000**        | **CONFIRMED** |

Raw summaries:
- EXP17 (unpatched holdout, 8f, n=30):
  `artifacts/phase1_51V_session3/exp17_videomme_holdout_8f_unpatched_summary.json`
- EXP18 (V-patched L=2 kr_V=0.50 holdout, 8f, n=30):
  `artifacts/phase1_51V_session3/exp18_videomme_holdout_8f_L2_kr050_summary.json`
- Runtime: EXP17 1770 s, EXP18 1628 s; total 56.6 min wall-clock.

## Numerical bookkeeping

Both runs are n=30 on `videomme_holdout_v1.toml`, 8 frames, max_tokens=32, Gemma
4-E4B-it 4bit, anchor=none, keep_rate=1.0.

### Dense-arm baselines (unpatched EXP17 vs V-patched EXP18)

| Quantity                  | EXP17 (unpatched) | EXP18 (V-patched)  |
|---------------------------|-------------------|--------------------|
| `mean_dense_end_to_end_ms`| 49594.15          | 45250.64           |
| `mean_dense_vision_ms`    | 7663.43           | 4498.75            |
| `mean_dense_generate_ms`  | 10330.67          | 8686.48            |
| `mean_dense_generation_tps`| 28.49            | 32.87              |
| `mean_dense_prompt_tokens`| 2194.73           | 2194.73            |
| `mean_decode_ms`          | 31485.12          | 31968.18           |
| `dense_accuracy`          | 0.467             | 0.467              |
| `agreement` (intra-arm)   | 0.967             | 0.967              |

### Pruned-arm (novelty-wrapper no-op at keep_rate=1.0)

| Quantity                  | EXP17 (unpatched) | EXP18 (V-patched)  |
|---------------------------|-------------------|--------------------|
| `mean_pruned_end_to_end_ms`| 47591.08         | 44542.83           |
| `mean_pruned_generate_ms` | 8300.95           | 7957.79            |
| `pruned_accuracy`         | 0.467             | 0.467              |

### Derived cross-arm quantities

- **H_holdout_vonly_e2e (prereg — dense→pruned)**: 49594.15 / 44542.83 = **1.113×**.
  Dense→dense sanity: 49594.15 / 45250.64 = 1.096×. Pruned→pruned sanity:
  47591.08 / 44542.83 = 1.068×. All three exceed the 1.05× gate.
- **H_holdout_vred (primary)**: V_red = (7663.43 − 4498.75) / 7663.43 = **0.413**.
- **V_share (unpatched baseline)**: `mean_dense_vision_ms / mean_dense_end_to_end_ms`
  = 7663.43 / 49594.15 = **0.1545 = 15.45%**. See §"V_share correction" below.
- **Ceiling prediction** at these values: `1 / (1 − 0.1545 × 0.413) = 1.068×`.
- **H_holdout_thermal**: cross-arm `|mean_decode_ms(EXP18) − mean_decode_ms(EXP17)|
  / mean_decode_ms(EXP17)` = |31968.18 − 31485.12| / 31485.12 = 483.06 / 31485.12
  = **0.01534 = 1.53%**.
- **H_holdout_accuracy**: 0.467 − 0.467 = **0.000**.

## Key findings and subtleties

### 1. V_share correction — holdout is NOT V_share-poor

The prereg predicted a 1.034× ceiling based on the auto-memory note "V_share
15.2% (8f dev); 8.6% (8f holdout)". That 8.6% number was wrong — it appears
to have come from a different estimator (possibly a per-item median rather
than a latency-weighted mean) or from a transient thermal regime that made
the baseline vision-tower look smaller. The directly-measured, paired
unpatched baseline yields **V_share = 15.45%** on holdout, equal to the dev
measurement within 0.3 pp. Two corollaries:

- Holdout is not V_share-poor on 8f. The "dev-only caveat" on the VideoMME
  8f V-only cell was holding the paper table back for a reason that does not
  exist in the data.
- The ceiling model generalizes from dev to holdout without regime-conditioning
  at this frame count; that is a stronger story for the paper than the prereg
  anticipated.

The stale memory entry at
pre-release local memory note `project_1_51V_expansion_2026-04-21.md`
says "V_share 15.2/24.3/31.0% at 8f/16f/32f dev, 8.6% at 8f holdout"; the
holdout value must be revised to 15.45% (8f).

### 2. Observed E2E (1.113×) exceeds V-only ceiling (1.068×)

The vision-only ceiling `1/(1 − V_share × V_red)` bounds the speedup that
vision-tower pruning alone can produce. Observed 1.113× exceeds this by
~4.2 pp. Decomposing:

- Dense `generate_ms` drops 10330.67 → 8686.48 (−15.9%); TPS rises 28.49 →
  32.87 (+15.4%). Same prompt-length (2194.73 tokens) in both arms.
- `decode_ms` is thermally stable (+1.53%), which passes the pair gate.
- `processor_ms` drops slightly (114.93 → 97.23; −15.4%).

The extra speedup is almost entirely a generate-side effect. The most likely
mechanism: V-patching reduces vision-tower activation footprint, which
decompresses the Metal/MLX cache pressure during the subsequent LLM prefill
and decode, raising TPS. This is a *composition* effect the ceiling model
does not try to predict, and it means the paper should state the V-only
ceiling as a **conservative lower bound** on observed E2E at this regime,
not a tight prediction.

(We should NOT re-frame this as a generate-side contribution; the *mechanism*
is still vision-tower pruning. We should simply note that scatter-back
produces a small secondary lift on constrained-memory Apple Silicon that is
not captured by the ceiling model.)

### 3. Accuracy is neutral and within-arm stable

`dense_accuracy = pruned_accuracy = 0.467` in both runs. 14/30 items correct
on both paths in both arms. `agreement = 0.967` intra-arm means the
novelty-path (with keep_rate=1.0, i.e. identity) agreed with the dense path
on 29/30 items — one stochastic generation divergence per run. Cross-arm
accuracy is byte-identical at the aggregate level; we have not computed
per-item accuracy overlap but since each arm is 14/30 correct, the cross-arm
agreement is at least `14/30 + (30−14)/30 − 1` = 0.

### 4. Thermal pair gate passed on the first attempt

Three of four prior 1.51V pairs violated the `decode_ms Δ < 2%` gate. Session
3 ran the pair back-to-back in a single autonomous queue; EXP17 (unpatched,
1770 s) → EXP18 (V-patched, 1628 s) with a zero-gap handoff. The resulting
gate margin (1.53%) is the best of the five 1.51V pairs. This suggests the
thermal-pair invariant can be satisfied reliably when (a) the two arms run in
one session, (b) the harder arm runs first (unpatched takes longer due to
full vision tokens), and (c) no thermal rest-pair is needed.

Session-3 methodology lesson: queue unpatched-then-patched back-to-back, never
paired-with-longer-gap-than-one-exp.

## Adjudication against prereg rules

- **H_holdout_vonly_e2e**: CONFIRMED (≥1.05× AND thermal gate passes). The
  prereg-mandated comparison (EXP17 dense vs EXP18 pruned = 1.113×) exceeds
  the gate by 6.3 pp. The conservative dense-dense comparison (1.096×) and
  the pruned-pruned comparison (1.068×) also clear the gate.
- **H_holdout_vred**: CONFIRMED (V_red = 0.413 ∈ [0.35, 0.45]). V_red
  benchmark-invariance at L=2 kr=0.50 holds on holdout: TOMATO dev 0.39,
  MVBench dev 0.42, VideoMME dev 0.39, VideoMME holdout 0.41 — all within
  3 pp of the "V_red ≈ 40%" generalization.
- **H_holdout_thermal**: PASSES (1.53% < 2%).
- **H_holdout_accuracy**: CONFIRMED (Δ = 0 ∈ [−0.05, +0.05]).

## Paper-table implication

Per prereg adjudication rule: "if H_holdout_vonly_e2e passes AND H_holdout_vred
passes, the VideoMME 8f V-only cell in the paper table can drop the 'dev-only'
caveat."

Both pass. The C-VISION paper table row for VideoMME 8f is now holdout-earned.
MVBench and TOMATO V-only cells remain dev-only (queued as should-do #2 in
`paper/priority.md`) but VideoMME 8f is the cell a reviewer is most likely to
probe first since it is the "primary breadth benchmark" for temporal VLM
evaluation in the relevant literature.

## Remaining work (paper-time follow-ups this enables)

1. **MVBench + TOMATO holdout V-only pairs** (should-do #2 in `paper/priority.md`).
   Same protocol, same runner, ~45 min each. Unblocked now — the session-3
   methodology generalizes to the other benchmarks directly.
2. **Update `paper/priority.md` must-do #1 status** from "IN PROGRESS" to
   "CLOSED 2026-04-21 — all four hypotheses pass".
3. **Update `research/experiments/registry.md` running-work**: session 3
   row moves from in-progress to closed; add findings pointer.
4. **Update C-VISION row in `paper/claim-matrix.md`**: VideoMME 8f cell no
   longer needs "dev-only" caveat.
5. **Correct auto-memory**: `project_1_51V_expansion_2026-04-21.md` V_share
   holdout 8.6% is wrong; should be 15.45%.

## Non-findings and open questions

- The dense→pruned E2E of 1.113× exceeds the V-only ceiling. We attribute
  this to Apple-Silicon-specific memory-pressure relief but have not
  mechanistically confirmed. Not on the paper critical path.
- `agreement = 0.967` intra-arm (novelty-wrapper with keep_rate=1.0 is an
  identity no-op, yet one stochastic divergence per arm remains). This
  matches the "stochastic-generation floor" observed on prior 1.51V pairs.
  Not a driver-bug.
- Cross-arm per-item overlap (did the same 14/30 items answer correctly in
  both arms?) is not computed here. If we want a per-item bucket report
  (EXP17-only-correct, EXP18-only-correct, both-correct, both-wrong) for
  the scale-out-style "clean / mixed / degenerate" decomposition, we need to join
  the two jsonls. Deferred to the pre-release source N=60 streaming reproduction prereg.

## Artifacts

- Prereg: `research/experiments/2026/2026-04-21-phase-1_51V-session3-prereg.md`
- EXP17 summary: `research/experiments/2026/artifacts/phase1_51V_session3/exp17_videomme_holdout_8f_unpatched_summary.json`
- EXP17 jsonl:    `research/experiments/2026/artifacts/phase1_51V_session3/exp17_videomme_holdout_8f_unpatched.jsonl`
- EXP18 summary:  `research/experiments/2026/artifacts/phase1_51V_session3/exp18_videomme_holdout_8f_L2_kr050_summary.json`
- EXP18 jsonl:    `research/experiments/2026/artifacts/phase1_51V_session3/exp18_videomme_holdout_8f_L2_kr050.jsonl`
- Queue log:      `research/experiments/2026/artifacts/phase1_51V_session3/queue.log`
- Runner:         `scripts/run_phase1_51V_session3.sh`
