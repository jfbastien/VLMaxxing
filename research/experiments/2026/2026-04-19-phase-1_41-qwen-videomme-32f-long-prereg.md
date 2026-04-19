# Phase 1.41 — Qwen 2.5-VL-7B VideoMME 32-frame long-bucket probe (prereg)

**Status:** pre-registration 2026-04-19 (autonomous session).
Predictions committed BEFORE running. Third point on the
frame-scaling curve for the **long bucket only** — the bucket that
regressed −20pp from 8f to 16f.

## Motivation

The 16f follow-up (findings
`2026-04-19-phase-1_41-qwen-videomme-16f-findings.md`) showed
**non-monotonic bucket scaling** on Qwen 2.5-VL-7B-4bit VideoMME
dev n=30: aggregate +3.3pp, medium +30pp, **long −20pp**. Paired
item-level comparison on long-bucket: 2 items flipped correct→wrong
(8f → 16f), 0 items flipped the other way; McNemar p=0.5 (weak,
directionally consistent, n=10 is under-powered).

16f memory usage was peak 7.23 GB — well under the 13 GB cap.
32f doubles prompt tokens again (~6.5k → ~13k). Predicted 32f peak
RSS ~10-11 GB on 16 GB Mac, still with margin.

A 32f long-bucket probe adds a critical third data point on the
frame-scaling curve. It discriminates:

- **drift-compounds hypothesis** (H_B from 16f findings): long
  accuracy continues to degrade at 32f (e.g., 0.10 → 0.05 or 0.00).
- **stride-saturates hypothesis** (H_A weakening): long accuracy
  bottoms out or partially recovers at 32f (e.g., 0.10 → 0.15+).
- **noise hypothesis** (null): long accuracy jumps around without
  systematic trend (e.g., 0.10 → 0.30 or 0.00 randomly).

## Scope

- **Bucket:** long only (n=10 — same item IDs as 8f and 16f runs
  for paired comparison).
- **Model:** Qwen 2.5-VL-7B-Instruct-4bit (same as prior runs).
- **Cache:** identity (bit-faithfulness continues to be verified).
- **Max tokens:** 32 (matching prior runs).
- **NOT running medium or short at 32f in this probe** — long is
  where the interesting signal lives; if long data is decisive we
  can extend later.

## Pre-registered predictions

### Hypotheses

- **H1 (aggregate long accuracy).** `long_acc(32f) ∈ [0.00, 0.30]`,
  best-guess 0.10 (= 16f). **Falsification bands:**
  - `long_acc(32f) ≥ 0.40`: stride-helps regime kicks in only at
    high frame counts — inverts the 16f regression story.
  - `long_acc(32f) ≤ 0.05`: drift-compounds regime — regression
    continues monotonically past 16f.
  - `long_acc(32f) ∈ [0.10, 0.30]`: 16f was a local dip; noise.

- **H2 (peak RSS fits).** `peak_RSS_GB ∈ [9.0, 12.0]`, predicted
  from linear-in-prompt-tokens extrapolation (16f: 7.23 GB at
  ~6.5k tokens → 32f at ~13k tokens ≈ 10-11 GB). **Falsification:**
  RSS > 13.5 GB → 32f on 16 GB Mac is infeasible for n=30 scaled
  runs.

- **H3 (mean elapsed per item).** `mean_elapsed_s ∈ [130, 200]` s
  (16f was 78s on long; 2× prompt tokens → 2-2.5× elapsed).
  **Falsification:** mean > 240s → decode-bound surprise; mean
  < 100s → unexpected prefill batching savings.

- **H4 (identity-cache agreement).** `agreement = 1.000` (Qwen
  identity-cache at 32f geometry; first time verified).
  **Falsification:** any divergence → identity-cache bug at 32f
  (would be a real finding; no prior evidence for it).

- **H5 (parse failure rate).** `parse_failures ≤ 2/10`. Qwen
  stable at 8f and 16f VideoMME. **Falsification:** ≥ 3/10 →
  prompt handling at 32f has quality regression, separate from
  accuracy regression.

### Paired-delta predictions (comparison to 16f long)

Looking at the 8f → 16f paired deltas (2 correct→wrong flips, 0
reverse), a symmetric model predicts 32f to show at most 1
correct→wrong flip from the current 1/10 correct. Best guess:
same 1 correct item (712-2) remains correct; others flip in
random walk. If **2+ new correct→wrong flips** emerge, long acc
drops to 0 and the drift-compounds hypothesis is strongly
corroborated (directionally; n=10 remains statistically weak).

## Decision rules

- H1 lower-tail (≤ 0.05): add "drift compounds past 16f on long"
  to the claim #8 strengthener section of the paper. Elevate
  Phase 1.57 (attention-entropy ablation) to high priority.
- H1 upper-tail (≥ 0.40): reinterpret the 16f long regression as
  sampling noise. Note in findings; Phase 1.57 remains deferred.
- H1 middle band (0.10-0.30): insufficient discrimination; note
  as suggestive, preserve honest-negative framing.
- H2 OOM (> 13.5 GB): abort 32f further experiments on this Mac;
  add scope-limit note to the 1.54 prereg (32f Qwen on 16 GB Mac
  is not a feasible setup).
- H4 identity divergence: halt, investigate cache path, do not
  report 32f results until resolved.

## Run plan

```bash
uv run python scripts/run_benchmark_track_a.py run \
    --benchmark videomme \
    --manifest research/benchmark_manifests/videomme_dev_v1.toml \
    --groups long \
    --frame-count 32 \
    --cache-mode identity \
    --max-tokens 32 \
    --output-path research/experiments/2026/artifacts/phase1_41_qwen_videomme_32f_long/dense_n10.jsonl \
    --summary-path research/experiments/2026/artifacts/phase1_41_qwen_videomme_32f_long/dense_n10_summary.json
```

Expected wall-clock: 10 × ~170s ≈ 28 min.

## What this does NOT answer

- **Does the medium-bucket +30pp at 16f hold at 32f?** That needs a
  separate 32f medium-bucket probe. Deferred to a follow-up if
  this run goes well AND the user gives go-ahead.
- **Does the short-bucket saturation stay saturated?** Same — not
  in this probe's scope.
- **Does frame scaling on Gemma match or diverge from Qwen?** Not
  this run. Gemma doesn't have a VideoMME 8f/16f dense baseline
  on identical items yet.
- **Is the mechanism drift or stride or 4bit-interaction?** None
  of the above. That requires Phase 1.57 (attention-entropy
  ablation) or Phase 1.58 (bf16 comparison), not another frame
  point.

## Cross-references

- 16f findings: `2026-04-19-phase-1_41-qwen-videomme-16f-findings.md`
- Claim-matrix row 8 (VideoMME)
- Phase 1.57 (mechanism ablation — load-bearing if H1 lower-tail)
- `2026-04-19-codex-round-21-sam-imports.md` §3 (attention-drift)
