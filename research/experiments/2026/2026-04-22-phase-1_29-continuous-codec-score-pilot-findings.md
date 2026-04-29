---
phase: 1.29
date: 2026-04-22
parent: research/experiments/2026/2026-04-22-phase-1_29-codec-native-short-bucket-pilot-findings.md
prior:
  - research/experiments/2026/2026-04-22-phase-1_29-codec-native-short-bucket-pilot-findings.md
  - research/experiments/2026/artifacts/phase1_29_continuous_codec_score_pilot/summary.json
status: MIXED — redesign option (2) reduces aggregate divergence 7× (53.8pp → 7.9pp, passes 10pp gate by construction via quantile calibration) but per-item divergence remains 16–25pp (fails per-item gate). Spearman ρ = +0.40 (n=5) on STATIC-share ordering is suggestive-not-significant. Aggregate-level codec↔pixel-diff claims are supportable; per-item label fidelity is not.
tracking: autonomous session 2026-04-21/22 dynamic-loop
---

# 1.29 Continuous codec-score pilot — findings (PARTIAL PASS)

## Headline

| item                 | pix S/X/N             | codec S/X/N           | Δ (codec−pix)                |
|----------------------|-----------------------|-----------------------|------------------------------|
| videomme:short:037-2 | 0.838 / 0.011 / 0.151 | 1.000 / 0.000 / 0.000 | +0.162 / −0.011 / −0.151     |
| videomme:short:210-2 | 0.400 / 0.003 / 0.597 | 0.535 / 0.044 / 0.421 | +0.135 / +0.041 / −0.176     |
| videomme:short:282-2 | 0.442 / 0.117 / 0.441 | 0.276 / 0.035 / 0.689 | −0.166 / −0.082 / +0.248     |
| videomme:short:120-2 | 0.402 / 0.060 / 0.538 | 0.203 / 0.025 / 0.772 | −0.199 / −0.035 / +0.233     |
| videomme:short:158-3 | 0.400 / 0.019 / 0.581 | 0.155 / 0.025 / 0.819 | −0.245 / +0.007 / +0.238     |

**Aggregate (n=5):** pix mean = 0.496 / 0.042 / 0.462, codec mean = 0.434 / 0.026 / 0.540, Δ = −0.062 / −0.016 / +0.079, **max|Δ| = 0.079 ≤ 0.10 PASS**.

**Per-item gate:** max|Δ| per-item ranges 0.162–0.248; **fails 0.10 per-item gate on all five items**.

**Rank correlation:** Spearman(pix_STATIC, codec_STATIC) ρ = +0.400 on n=5 (suggestive, not significant; p≈0.50 for two-tailed test).

**Calibrated thresholds** (on pooled 5-item native-frame codec scores):
`static_t = 0.095` (43.6-th pctile of pooled score), `shifted_t = 0.111` (46.2-th pctile). The SHIFTED band spans only 1.6pp of the pooled score distribution, narrow by design to match pixel-diff's 2.6% SHIFTED share.

## Interpretation

Mechanism redesign did exactly what the hard-falsification note predicted: swapping MAX-over-span for `fraction_of_native_frames_with_intra_or_cbf` breaks the 100%-NOVEL degeneracy. Codec-score distribution is now continuous (`min=0.004 p10=0.008 p43.6=0.095 p90=0.512 max=0.953`), not a binary indicator.

But quantile calibration is **global**, not per-item. Two failure modes:

1. **Extreme-STATIC items saturate.** `037-2` is 84% STATIC by pixel-diff; the codec score for its MBs drops near-zero almost uniformly, pushing **all** tokens below `static_t` → 100% STATIC prediction (off by +16pp STATIC, −15pp NOVEL). The quantile threshold was chosen to match aggregate, not to preserve within-item dynamic range.

2. **Moderately-dynamic items over-predict NOVEL.** Items 282-2 / 120-2 / 158-3 show codec over-predicting NOVEL by +23 to +25pp. These items have mid-range pixel STATIC share (40–44%) but their codec scores concentrate in the upper third of the pooled distribution, pushing many tokens above `shifted_t` → NOVEL. Codec and pixel-diff disagree on *where* motion shows up, not just *how much*.

The Spearman ρ = +0.40 says the codec signal preserves the *ordering* of how-static-clips-are across the 5-item panel, but does not preserve magnitudes. At n=5 the correlation is not distinguishable from 0 (for n=5, |ρ|≥0.9 is needed for p<0.05 on a two-tailed Spearman test).

## What this supports and what it does NOT support

**SUPPORTS:** A paper-body claim of the form *"continuous codec-score, quantile-calibrated to match the pixel-diff aggregate per-class distribution, reproduces the aggregate distribution within 8pp."* This is a weaker claim than the pre-release source implies but it is defensible on this evidence.

**DOES NOT SUPPORT:** A per-block / per-item label-fidelity claim of the form *"codec labels match pixel-diff labels at the block level."* The per-item divergence (16–25pp across all 5 items) rules out per-block fidelity at the ~10pp band.

**DOES NOT TEST:** Downstream planner accuracy. Per-block label divergence does not necessarily translate to per-item planner accuracy divergence — the planner's keep-ratio operates over tokens pooled across pairs and may produce similar token selections even with moderately-drifted labels. The real gate for the paper-body row is a head-to-head planner-accuracy comparison on a matched benchmark slice, not per-block label agreement.

## Where this leaves redesign option (2)

The design-note's option (2) was *"replace label-pass with continuous-score-then-rethreshold, let `classify_blocks_with_planner` re-threshold using existing `static_threshold` / `shifted_threshold` machinery."* This pilot implements that with a **global quantile calibration** on the aggregate. Two refinements remain before the paper-body row is viable:

1. **Per-item quantile calibration** (cheap): calibrate `static_t`, `shifted_t` **per item** rather than pooled, then measure both per-item and aggregate deltas. This would eliminate failure mode (1) above (037-2 saturation) by construction. Expected: per-item max|Δ| drops sharply; aggregate is preserved. If this clears the per-item gate, option (2) is locked.

2. **Full planner-accuracy probe** (medium): swap the planner's pixel-diff label path for a continuous-codec-score + planner-threshold path on a downstream benchmark slice (e.g. VideoMME 8f n=30 short-bucket dev). Measure planner-accuracy parity, not label parity. This is the *real* paper-body gate; per-block label parity is an intermediate proxy that may be unnecessarily strict.

Recommendation: run per-item calibration variant next (≤5 min compute, no MLX needed), then decide whether the planner-accuracy probe is worth the engineering cost of wiring codec-score into `classify_blocks_with_planner`.

## Claim-matrix / priority / registry edits

- `paper/priority.md` should-do #8 (1.29): update from "SHORT-BUCKET PILOT FALSIFIED 2026-04-22" to "**CONTINUOUS-SCORE PARTIAL PASS 2026-04-22**: aggregate max|Δ| 7.9pp passes 10pp gate but per-item max|Δ| 16–25pp fails per-item gate. Next: per-item quantile calibration variant, then planner-accuracy probe."
- `paper/framing.md` Reviewer-Facing Limitations: keep current "codec-native local-benchmark slice is future work"; aggregation redesign has not yet cleared the paper-body gate.
- `research/falsified-hypotheses.md`: no new entry required (the MAX-aggregation falsification still stands; the continuous redesign is a *partial* result on a narrower claim).

## Reproduction

```
uv run python scripts/pilot_1_29_continuous_codec_score.py
```

Reads `research/experiments/2026/artifacts/phase1_57/qwen_8f_dev30.json` (1.57 pixel-diff reference). Writes `research/experiments/2026/artifacts/phase1_29_continuous_codec_score_pilot/summary.json`. Runtime ~100s (5 items × ~20s extract).

Env: `mlx-vlm 0.4.4` / PyAV latest / macOS Darwin 25.3.0 / M3 16 GB. Git SHA at run-time: 9af181b (clean before this doc lands).

## Non-goals

- **No full-panel (n=30 dev or cross-bucket) re-run.** n=5 is enough to bracket the per-item failure mode; scaling to n=30 without a per-item calibration fix would burn compute on a known issue.
- **No Stages A/B/C implementation.** Still blocked upstream on a per-item-calibration gate pass (or a planner-accuracy-probe pass).
- **No Spearman significance test at n=5.** The sample is too small for the correlation to distinguish from chance at α=0.05.
