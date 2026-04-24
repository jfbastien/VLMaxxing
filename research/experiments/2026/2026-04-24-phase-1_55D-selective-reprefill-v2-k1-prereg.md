# Phase 1.55D v2 — Selective re-prefill K=1 (PREREG EXTENSION)

**Date:** 2026-04-24. **Status:** preregistration extension before run.
**Parent:** `2026-04-20-phase-1_55D-selective-reprefill-prereg.md`.

## Why this extension exists

The original 1.55D preregistered sweep covered `K ∈ {2, 4, 8}`.
Today, repo-local v2 has already landed two completed frontier points on
the full 7-clip 20f short-bucket tranche:

- `K=4`: exact recovery, `3.66×`, RSS narrow fail
- `K=2`: exact recovery, `6.72×`, RSS pass, follow-up median `15.27 s`

That moves the live scientific question. The lane is no longer "does
selective re-prefill work at all?" It does. The question is whether a
**lighter** recovery point can cross the deployment-grade speed line
without giving back too much fidelity.

`K=1` is therefore the highest-information next point.

## Scope

- Model: `Qwen2.5-VL-7B-Instruct-4bit`
- Regime: 20-frame persistent-KV short-bucket VideoMME session
- Clips: `037,100,116,120,158,160,210`
- Queries: 3 per clip, session path vs matched cold baseline
- Output dir:
  `research/experiments/2026/artifacts/phase1_55D_selective_reprefill_v2/`

## Hypotheses

### H1-K1 (partial fidelity recovery)

`K=1` keeps the session within the original K=2 partial-recovery band:
`Δacc <= -0.25` relative to the matched cold baseline.

**Falsification:** `Δacc < -0.25`.

### H2-K1 (deployment-speed crossover)

`K=1` reaches the paper-relevant speed regime:

- paired follow-up median `<= 10.5 s`, and
- speedup `>= 10×` versus the matched cold baseline median.

The 10.5 s line is a practical slack band around the exact 10× ratio
for the current cold-median scale, so the result will still be reported
against the exact measured `>= 10×` multiplier.

**Falsification:** speedup `< 8×` or follow-up median `> 12 s`.

### H3-K1 (basin control)

Pathological follow-up attractors remain controlled:
`<= 2/14` on the established attractor set.

**Falsification:** `>= 5/14`.

### H4-K1 (memory)

Peak RSS remains `<= 5 GB`.

## Interpretation rules

- If H1 and H2 both earn: `K=1` becomes the new paper-default recovery
  point and 1.55D upgrades from "recovery frontier" to "recovery
  recipe with deployment-grade speed".
- If H1 earns but H2 misses narrowly: 1.55D remains a frontier result,
  but the speed gap is likely adaptive-policy territory rather than
  fixed-K.
- If H1 fails while H2 earns: K-only frontier is too brittle at the
  light tail; keep K=2 as best fixed policy and pivot future work to
  adaptive admission/refresh.
- If both fail: K=2 is the best fixed point and the lane is effectively
  mapped for this local setup.

## Non-goals

- This is not a replacement for the original prereg; it is a targeted
  frontier extension motivated by the completed K=2 result.
- This does not reopen K=8. K=8 is lower information now that K=2 and
  K=4 both already establish exact recovery.
