---
phase: 1.63E (8f point)
date: 2026-04-27
parent: research/experiments/2026/2026-04-27-phase-1_63E-track-b-frame-scaling-prereg.md
status: 8f point landed; 4 of 6 prereg gates PASS; H_fidelity FAILS at -0.067 aggregate (-0.25 short); H_ceiling_explained PASSES at gap 0.005. Higher frame counts still running.
---

# Phase 1.63E 8f — Track B Qwen frame scaling, first frame point (FINDINGS)

**Verdict (8f only, n=60 combined manifest).** The arithmetic ceiling model is tightly validated — predicted 1.047× E2E vs measured 1.042× (gap 0.005) — and the sparse vision execution is real (44.8% vision-time reduction). But paired fidelity drops 6.7pp aggregate and 25pp on the short bucket, so this is a *bounded* Track B result, not a fidelity-preserving headline. The C-CEILING contribution gets the strongest support; the C-VISION fidelity claim must be re-scoped.

## Headline numbers

n=60 paired across short (n=20), medium (n=20), long (n=20). Both arms used Qwen2.5-VL-7B-Instruct-4bit, max_tokens=32, vision-tower-layer L=2, vision-tower-keep-rate kr=0.50 for sparse.

| Metric | Dense | Sparse | Δ / ratio |
|---|---|---|---|
| Accuracy | 0.617 | 0.550 | **−0.067** (CI95 [−0.18, +0.05]) |
| Mean vision (ms) | 8,375 | 4,621 | **−44.8%** (1.81× speedup) |
| Mean E2E (ms) | 83,880 | 80,492 | 1.042× speedup |
| Vision share dense | 9.98% | — | — |
| Predicted E2E ceiling | — | — | **1.047×** |
| Actual − predicted | — | — | **−0.005** (within ±0.05 tolerance) |
| Choice agreement | — | — | 71.7% |

By bucket:

| Bucket | n | Δacc | Δacc CI95 | Vision share dense | E2E speedup | Predicted | Gap |
|---|---|---|---|---|---|---|---|
| short | 20 | **−0.25** | [−0.45, −0.10] | 25.0% | 1.065× | 1.115× | −0.050 |
| medium | 20 | +0.15 | [−0.05, +0.35] | 16.7% | 1.107× | 1.090× | +0.017 |
| long | 20 | −0.10 | [−0.30, +0.10] | 4.3% | 1.017× | 1.019× | −0.002 |

## Gate-by-gate against the prereg

- **H_pairing PASS** — 60 paired items, 0 parse failures both arms.
- **H_sparse_vision PASS** — vision reduction 44.8% ≥ 25%.
- **H_e2e_positive PASS** — 1.042× ≥ 1.03×.
- **H_ceiling_explained PASS** — |0.005| ≤ 0.05.
- **H_fidelity FAIL** — −0.067 < −0.05 threshold.

The headline_pass conjunction is therefore FAIL at 8f. This is the prereg behaving correctly: a sparse system that materially regresses the short bucket is not a paper-grade fidelity result.

## What this says, and what it does not say

1. **C-CEILING earns its strongest validation point so far.** The predicted/actual E2E gap is 0.005 across the whole 60-item pair, and is at the tolerance edge (−0.050) only on the short bucket where vision share is highest (25%). The arithmetic model `1 / (1 - V_share · V_red)` is paper-defensible.
2. **Real sparse-vision work was skipped.** 1.81× vision speedup with 44.8% reduction at L=2 kr=0.50 is consistent with the 1.51V landed envelope (39–43% V_red there). This run reaffirms that the scatter-back compact-execution path is genuinely sparse for layers L+1..N.
3. **C-VISION at 8f is not a fidelity-preserving win on this manifest.** Aggregate Δacc=−0.067 (CI upper −0.183) and short-bucket Δacc=−0.25 (CI95 entirely negative) are both real drops. The paper cannot keep the implicit "free speedup" framing for this configuration. It can keep:
   - "C-VISION reduces measurable vision-tower work" (true, 44.8%)
   - "predicted E2E speedup from vision-only matches the measured wall-clock" (true, gap 0.005)
   - "fidelity is paid for in some buckets and configurations" (now empirically anchored)
4. **8f is the bucket where C-VISION's E2E ceiling is smallest.** Vision share 9.98% all-pair, 4.3% on long — the long bucket cannot benefit much from any vision optimization at 8f because video decode dominates. This is why frame-budget scaling (1.63E 16f/20f/32f) is the more interesting science.

## Why is fidelity worse than 1.51V's 0/30?

The previous 1.51V landed cell on `videomme_dev_v1.toml` n=30 returned 0/30 paired drift. The 1.63E 8f run is on `videomme_combined_v1_n60.toml`, a *different* item set spanning short/medium/long. Different short-bucket items in the combined manifest evidently include more vision-dependent questions where L=2 kr=0.50 is too aggressive. This is not a 1.51V regression; it is a manifest-coverage finding.

Mechanism is plausible but not yet item-attributed: at 25% short-bucket vision share, the sparse path is committing to drop 50% of merged-token groups *before the LM sees them*; if the answer-relevant patches are concentrated in the dropped groups for some short items, the LM's choice flips. Per-item analysis (which dropped frames vs. which item lost accuracy) is the natural follow-up.

## Recommended actions

- Continue the queue (16f, 20f, 32f) — the H_ceiling_explained validation is the more important contribution here, and it is *more* interesting at 16f and 32f where vision share grows.
- After the queue lands, run a per-item attribution: for each short-item flip, check whether the dropped patches at L=2 kr=0.50 overlap with answer-bearing image regions. This should be done as a small, scoped diagnostic — not as another big run.
- Update the paper to lead with C-CEILING when introducing C-VISION at 8f, not the other way around.

## Follow-ups already implied

- 1.63E will produce 16f, 20f, 32f points; 16f is currently running.
- 1.63G will check this on Gemma at 8f/16f/32f.
- 1.30AF item-level concentrations (already landed) provide a separate axis on which the same kind of attribution can be done for C-PERSIST.
