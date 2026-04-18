# Phase 1.41 — Qwen 2.5-VL-7B VideoMME 16-frame follow-up (prereg)

**Status:** pre-registration 2026-04-19. Predictions committed
BEFORE running. Extension of claim #8 (already EARNED at 8f on
2026-04-18). This run measures the frame-scaling slope toward the
public 32f ≈ 0.55 reference.

## Motivation

The 8-frame run landed `dense_acc = 0.533` aggregate (short 0.800 /
medium 0.500 / long 0.300) with peak RSS 6.67 GB and agreement 1.000.
H3 (`RSS < 8 GB`) left ~6 GB of headroom on a 16 GB Mac. At 16
frames we expect roughly double the prompt-token count (→ ~6,560
tokens) and 2× the vision-encoder work, which empirically scales
peak RSS roughly linearly in prompt tokens (not frame tensors, which
fit in the UMA pool). The public Qwen 2.5-VL-7B VideoMME number is
at 32 frames, so 16f is the midpoint data point that tells us
whether the frame-scaling slope is steep (→ 32f worth running) or
flat (→ 16f suffices for scaled-up baselines elsewhere).

## What this earns vs. what 8f already earned

8f already landed:
- Claim #8 EARNED (aggregate 0.533 on videomme_dev_v1).
- Identity-cache bit-faithfulness on VideoMME (agreement 1.000).
- Monotone short → long degradation pattern (0.80 / 0.50 / 0.30).

16f is incremental-value, not gate-clearing:
- A second point on the frame-scaling curve → slope estimate for
  claim #5 Track B ceiling analysis.
- Long-bucket sensitivity: if long jumps from 0.30 → ≥ 0.45, the
  "long-items under-resourced at 8f" framing gains direct evidence.
- Memory-headroom validation: confirms the `ffwd-to-32f feasibility`
  argument used in the 1.54 prereg.

## Pre-registered predictions

### Hypotheses

- **H1 (aggregate dense accuracy lifts)**: 16f aggregate
  `dense_acc ∈ [0.55, 0.65]`. Best-guess 0.60. Rationale: public 32f
  ≈ 0.55 but on n=2700 test; our dev n=30 at 8f already ran 0.02
  above public-test-adjusted 8f expectation, so 16f should land in
  or slightly above the public band. **Falsification:** aggregate
  ≤ 0.533 (no lift over 8f) **or** aggregate > 0.70 (sampling
  artifact on the small dev slice).
- **H2 (long-bucket gets the biggest lift)**: `long_acc(16f) -
  long_acc(8f) ≥ +0.10`. Rationale: 8 extra frames over a 15+ min
  video is a 2× sampling density for the most under-resourced
  bucket. **Falsification:** `long_acc(16f) - long_acc(8f) < 0.05`
  would indicate the long-bucket bottleneck is not frame count
  (probably G-side reasoning, not sampling).
- **H3 (peak RSS stays under ceiling)**: peak RSS < 13 GB. The
  linear-in-prompt-tokens heuristic predicts ~13.3 GB at 2× prompt
  tokens. **Falsification:** RSS > 14 GB → we are inside the OOM
  ceiling and 32f is infeasible on 16 GB.
- **H4 (wall-clock per item)**: median dense e2e ∈ [55, 90] s
  (8f median was 30.5 s; expect ~2× with a Qwen prefill-dominated
  long end). **Falsification:** median > 120 s (signals we've
  crossed into the decode-bound regime and 1.54 lever becomes
  relevant for Qwen too) **or** median < 45 s (model/fast-path
  surprise — investigate).
- **H5 (parse failure rate)**: ≤ 2/30 dense parse failures. Qwen
  stable at both 8f VideoMME and other benchmarks. **Falsification:**
  ≥ 5/30 halts and forces prompt investigation.

### Bucket priors (tighter than 8f given calibrated monotone trend)

| bucket | 8f observed | 16f prior band | rationale                                               |
|--------|-------------|----------------|---------------------------------------------------------|
| short  | 0.800       | [0.70, 0.90]   | Already near ceiling; 16f may or may not lift.          |
| medium | 0.500       | [0.50, 0.70]   | Frame budget relief helps most here.                    |
| long   | 0.300       | [0.40, 0.60]   | Biggest expected lift (H2).                             |

### Decision rules

- H1 + H3 earned → Claim #8 strengthened; add a frame-scaling row
  to the findings and to `paper/claim-matrix.md`.
- H1 falsified downward (≤ 0.533) → flag as surprising; do not
  re-anchor claim #8 (which is already earned), but add a deferred
  task to investigate (possibly a cache_mode quirk at higher frame
  count, possibly an adversarial interaction with Qwen's multi-grid
  pipeline).
- H3 falsified (RSS > 14 GB) → abandon any future 32f run on this
  Mac; note as OOM-ceiling in claim #8.
- H2 falsified → long-bucket story in the paper needs a rewrite
  (frame count is NOT the bottleneck; G-side reasoning is).

## Run plan

Dense-only, identity cache for bit-faithfulness verification on the
16f path too (first time we run that geometry on Qwen):

```bash
uv run python scripts/run_benchmark_track_a.py run \
    --benchmark videomme \
    --manifest research/benchmark_manifests/videomme_dev_v1.toml \
    --frame-count 16 \
    --cache-mode identity \
    --max-tokens 32 \
    --output-path research/experiments/2026/artifacts/phase1_41_qwen_videomme_16f/dense_n30.jsonl \
    --summary-path research/experiments/2026/artifacts/phase1_41_qwen_videomme_16f/dense_n30_summary.json
```

Estimated wall-time: 30 items × ~55-60 s/item median ≈ **30-45 min**.

## Cross-references

- 8f prereg: `2026-04-18-phase-1_41-qwen-videomme-baseline-prereg.md`
- 8f findings: `2026-04-18-phase-1_41-qwen-videomme-baseline-findings.md`
- Claim-matrix row 8: already EARNED at 8f; this is a strengthener.
- 1.54 prereg: H3-earn here validates the "16f feasibility" argument
  used in its runtime-budget section.
