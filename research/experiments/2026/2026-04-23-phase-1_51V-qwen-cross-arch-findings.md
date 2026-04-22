---
phase: 1.51V
date: 2026-04-23
parent: research/experiments/2026/2026-04-22-phase-1_51V-qwen-cross-arch-prereg.md
prior:
  - research/experiments/2026/2026-04-21-phase-1_51V-expansion-findings.md
  - research/experiments/2026/2026-04-21-phase-1_51V-exp10-n60-findings.md
status: findings 2026-04-23. C-VISION upgrades from single-arch (Gemma) to two-arch mechanism (Gemma + Qwen).
tracking: autonomous AFK session 2026-04-22/23
---

# 1.51V Qwen cross-architecture transfer — findings

## TL;DR

The scatter-back vision-tower pruning ceiling `E2E ≤ 1/(1 − V_share × V_red)`
transfers cleanly from Gemma 4-E4B-4bit to Qwen 2.5-VL-7B-4bit at matched
`(L=2, kr_V=0.50)` on VideoMME dev n=30, 8 frames. All three preregistered
gates pass:

- **V_red = 0.398** (gate [0.35, 0.50]) — essentially identical to the
  Gemma 39–43% band at the same operating point, despite Qwen's different
  internal ViT layout (flat `[seq, hidden]` with `cu_seqlens`/`cu_window_seqlens`
  routing, `spatial_merge_unit=4` alignment).
- **E2E speedup = 1.044× measured vs 1.043× predicted by the ceiling**
  (gate: within 15% of prediction; actual: 0.1% deviation). Ceiling binds.
- **Aggregate accuracy Δ = −3.3pp** (0.533 → 0.500; gate |Δ| ≤ 0.10). Noise-level
  at n=30 (binomial SE ≈ 9pp at p=0.5).

C-VISION upgrades from "single-architecture mechanism (Gemma)" to
"two-architecture mechanism (Gemma + Qwen)" in the claim matrix.

## Results

### Headline numbers (VideoMME dev n=30, 8f)

| Metric                        | Unpatched (dense) | Patched (L=2, kr_V=0.50) | Δ / ratio         |
|-------------------------------|-------------------|--------------------------|-------------------|
| Aggregate accuracy            | 0.533             | 0.500                    | −0.033            |
| Mean V_wall (ms)              | 8789.7            | 5293.5                   | V_red = +0.398    |
| Mean E2E wall (ms)            | 85436.9           | 81862.2                  | 1.044× speedup    |
| Mean decode (ms)              | 54280.3           | 54524.6                  | +0.45% (noise)    |
| Mean prefill tokens           | 3286.9            | 3286.9                   | identical         |
| V_share (dense)               | 0.103             | —                        | —                 |
| Ceiling @V_red=0.398, V_share=0.103 | —           | —                        | 1.043×            |
| Mean kept groups (ViT)        | 3200              | 1600                     | exactly 50%       |

Prefill token count is bit-identical between arms — scatter-back preserves
the LM-visible token count, so the V_red saving is ViT-compute-only. This
is the correct geometry for the ceiling law as written.

### Per-bucket accuracy (n=10 each)

| Bucket | Unpatched | Patched | Δ     |
|--------|-----------|---------|-------|
| short  | 0.800     | 0.600   | −0.20 |
| medium | 0.500     | 0.800   | +0.30 |
| long   | 0.300     | 0.100   | −0.20 |

Per-bucket at n=10 is dominated by noise (binomial 95% CI width ≈ ±0.30);
no single bucket is distinguishable from zero. Short-bucket −20pp and
medium-bucket +30pp approximately cancel at the aggregate. The long-bucket
−20pp is consistent with the known 1.41 Qwen long-bucket collapse pattern,
not with a pruning-induced regression specifically (long is already at
0.30 on the dense arm, so there is little headroom to move correctly).

## Hypothesis verdicts

| ID          | Gate                                               | Measured                       | Verdict      |
|-------------|----------------------------------------------------|--------------------------------|--------------|
| H_qwen_Vred | V_red ∈ [0.35, 0.50]                               | V_red = +0.398                 | **PASS**     |
| H_qwen_E2E  | E2E speedup within 15% of `1/(1 − V_share × V_red)`| 1.044× vs 1.043× predicted (0.1% deviation) | **PASS** |
| H_qwen_acc  | |Δacc| ≤ 0.10 aggregate                            | Δacc = −0.033                  | **PASS**     |

V_share = 0.103 on Qwen (above the 0.05 VACUOUS threshold), so H_qwen_E2E
is properly falsifiable on this architecture and its pass carries weight.
The narrower ceiling on Qwen (~4.4% vs Gemma's ~20% at high V_share) is
an expected consequence of Qwen having a larger LM relative to its ViT;
it does not reflect a mechanism weakness.

## Interpretation

The claim being upgraded is *the ceiling law*, not the specific headline
number. On Gemma, V_share is ~20–30% across benchmarks, so the ceiling
predicts 1.20–1.40× lifts; on Qwen at 8f VideoMME, V_share is ~10%, so
the ceiling predicts 1.04×. Both architectures hit their respective
ceilings to within the preregistered envelope. What transfers is the
*mechanism* — not a particular speedup magnitude.

This matters for the paper's C-VISION narrative in two ways:

1. **Universality.** The `E2E ≤ 1/(1 − V_share × V_red)` bound was
   previously written as "validated on Gemma 4-E4B-4bit". With this run
   it reads "validated on Gemma 4-E4B-4bit and Qwen 2.5-VL-7B-Instruct-4bit
   at matched (L=2, kr_V=0.50)". That is a meaningfully broader claim
   without new moving parts.
2. **Honesty about headline magnitudes.** The paper should continue to
   cite Gemma's 1.08–1.40× numbers as the *achievable* end-to-end lifts,
   because V_share is architecture-dependent; Qwen's smaller lift is
   structural, not a weakness of the method.

## Methodology notes

- **Implementation.** Codex landed the Qwen wrapper `QwenVisionPruneConfig` /
  `patch_qwen_vision_tower` during the 2026-04-22 session, with
  `spatial_merge_unit`-aligned group pruning and `cu_seqlens` / `cu_window_seqlens`
  recomputation as preregistered in the 04-22 design doc. The dense path
  is bit-identical at `kr_V=1.0` (parity check from the implementation
  session).
- **Thermal pairing.** Arms run back-to-back on the same machine; no
  explicit cool-down was enforced beyond the natural ~20 min gap between
  arms. Mean peak memory was 6.67 GB (unpatched) vs 6.62 GB (patched),
  well under the 10 GB RSS guard.
- **Dirty-tree guard.** The multi-arm wrapper `run_phase1_51V_qwen_cross_arch.sh`
  previously failed between arms because the unpatched arm's artifacts
  make the tree dirty. Fixed in commit 7580e6a by threading `--allow-dirty`
  through the wrapper; the research guard is still enforced when
  `--allow-dirty` is *not* passed.
- **Per-bucket n=10.** This is a first-point cross-arch probe. n=30 is
  enough to gate the aggregate ceiling claim (which is what the paper
  depends on) but is not designed to resolve per-bucket effects; if a
  future revision needs per-bucket Qwen evidence, n=20–30 per bucket is
  the appropriate follow-up.

## Paper implication

- **`paper/claim-matrix.md`** (C-VISION row): upgrade "single-architecture
  mechanism (Gemma 4-E4B-4bit)" → "two-architecture mechanism at L=2 kr_V=0.50
  (Gemma 4-E4B-4bit and Qwen 2.5-VL-7B-Instruct-4bit, VideoMME dev n=30 at
  8 frames)".
- **V_share × V_red ceiling plot** (C-CEILING figure): add a Qwen data
  point at (V_share=0.103, E2E=1.044×, predicted=1.043×). The Qwen point
  lives low-left on the curve; Gemma's benchmark points populate the
  high-share region. The fact that both architectures sit *on* the curve
  is the figure's new load-bearing claim.
- **Abstract / intro** do not need softening; the narrative tightens.

## Reproduction

```
bash scripts/run_phase1_51V_qwen_cross_arch.sh
```

Outputs:
- `research/experiments/2026/artifacts/phase1_51V_qwen_cross_arch/videomme_dev30_8f_unpatched.jsonl`
- `research/experiments/2026/artifacts/phase1_51V_qwen_cross_arch/videomme_dev30_8f_unpatched_summary.json`
- `research/experiments/2026/artifacts/phase1_51V_qwen_cross_arch/videomme_dev30_8f_L2_kr050.jsonl`
- `research/experiments/2026/artifacts/phase1_51V_qwen_cross_arch/videomme_dev30_8f_L2_kr050_summary.json`
- `research/experiments/2026/artifacts/phase1_51V_qwen_cross_arch/pair_analysis.txt`

## Next steps

1. **Paper pass** — batch with the 1.57 holdout upgrade: update
   `paper/claim-matrix.md` C-VISION row + C-CEILING figure caption with
   the Qwen data point. (Defer until autonomous session ends; keep in
   research-doc form for now so the user can do the final JF-voice pass.)
2. **Optional follow-up: MVBench or TOMATO on Qwen at (L=2, kr_V=0.50).**
   Would move C-VISION from single-benchmark on Qwen to two-benchmark,
   further strengthening the "mechanism-class" framing. Not critical path
   — the ceiling law's architecture-portability is already established.
3. **Optional follow-up: Qwen kr sweep at 8f VideoMME.** kr ∈ {0.33, 0.25}
   would test whether the ceiling continues to bind at more aggressive
   pruning on Qwen, the same way Gemma Stage 6 did. Queue as P2.

## Artifacts

- `pair_analysis.txt`:
  ```
  V_red:            +0.3978
  E2E speedup:      1.0437x
  Decode drift:     +0.4501%
  Accuracy delta:   -0.0333
  V_share (dense):  +0.1029
  Ceiling@V_red:    1.0427x
  ```
