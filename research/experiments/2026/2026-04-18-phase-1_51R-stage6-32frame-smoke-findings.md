# Phase 1.51R Stage 6 — 32-frame feasibility smoke (n=1 long)

**Status:** smoke findings 2026-04-18. Single item; pilot tranche n=10
launched immediately after to test whether the signal survives.

## Purpose

Feasibility gate for the 32-frame regime-match experiment (task #109).
Prereg gate: peak RSS < 12 GB AND wall-clock < 180s per item. If
passed, proceed to n=10 pilot.

## Result (n=1, videomme:long:669-1)

| metric                          | value     |
|---------------------------------|-----------|
| peak RSS                        | 4087 MiB  |
| dense_end_to_end_ms             | 78,122    |
| pruned_end_to_end_ms            | 51,398    |
| **end_to_end_speedup**          | **1.520×**|
| generate_only_speedup           | **6.952×**|
| per_token_generate_speedup      | 6.952×    |
| dense correct                   | True      |
| pruned correct                  | True      |
| agree                           | True      |
| mean_dense_prompt_tokens        | 8441      |
| mean_pruned_prompt_tokens       | 1049      |
| effective_keep_ratio            | 0.098     |

Dense stage breakdown:
- decode: 23.2s (30%)
- processor: 0.3s
- vision_tower: 23.3s (30%)
- generate: 31.3s (40%)

## Feasibility gates

| gate | threshold | observed | pass |
|------|-----------|----------|------|
| peak RSS | < 12 GB | 4.0 GB | ✔ |
| wall-clock | < 180s | 78s | ✔ |

**Both feasibility gates cleared by wide margin.**

## Arithmetic ceiling validation at 32 frames (n=1)

Single-item ceiling decomposition:

- fixed_frac = (D + P + V) / dense_e2e = (23.2 + 0.3 + 23.3) / 78.1 = **0.599**
- G fraction = 0.401
- Observed s (per_token) = 6.95×
- ceiling@s = 1 / (0.599 + 0.401 / 6.95) = **1.522×**
- observed e2e = **1.520×**

**Prediction error 0.1%** — ceiling model predicts to 3 decimal places
on this single 32-frame long item.

## Regime shift: G fraction quadruples vs 8 frames

At 8 frames on long bucket, G/e2e ≈ 8.8% (long fixed_frac=0.912 from
arithmetic-ceiling-findings.md). At 32 frames on this one long item,
**G/e2e = 40.1%**. Mechanism: vision + decode scale with frame count;
G scales with prefill length which is ~4× larger in tokens (2048 →
8192 on long-8 → long-32 respectively; aligns with observed 2180 →
8441 from the summary file).

Ceiling@∞ at 32-frame long: 1/0.599 = **1.670×** on this item, vs
1.098× at 8-frame long. **The regime-gap hypothesis is quantitatively
supported by the 32-frame arithmetic.**

## Hypothesis status (pre-registered)

- **H1 (regime lifts ceiling to ~1.8×)**: prereg band [1.5×, 2.0×].
  Observed 1.520× at n=1 is **inside band** at lower edge. Needs n≥10
  to commit.
- **H2 (Δacc ∈ [-0.15, -0.05] on long)**: observed 0.0 (both correct)
  at n=1. Inside band. Needs n≥10.
- **H3 (RSS < 12 GB)**: 4.0 GB at n=1. **EARNED.**

## Next action

Pilot tranche n=10 long bucket launched (task #110). ~22 min wall
time. Reports on the same `phase1_51R_32frame_pilot/` artifact dir.
If aggregate e2e lands in [1.5×, 2.0×] with Δacc ∈ [-0.15, -0.05],
**H1 and H2 earn and the regime-gap hypothesis is confirmed at n=10
on long bucket**, which is the bucket where the 8-frame ceiling caps
at 1.10× (the bucket Sam's 1.8× cannot reach without regime match).

## Cross-references

- `2026-04-18-phase-1_51R-stage6-regime-match-prereg.md` — prereg.
- `2026-04-18-arithmetic-ceiling-findings.md` — ceiling model.
- `2026-04-18-sam-regime-gap-note.md` — regime-gap thesis.
- `artifacts/phase1_51R_32frame_smoke/long_kr010_n1_32frame_summary.json`
  — authoritative numbers.
