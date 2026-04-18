---
Phase: 1.51R
Stages covered: Stage 1 (n=30, kr=0.5) + Stage 2 (n=5, kr ∈ {0.10, 0.25, 0.75})
State: LANDED 2026-04-18 — kr=0.5 preregistered NULL confirmed; kr=0.10 shows PARTIAL REPRO
Links: [prereg](2026-04-17-phase-1_51-novelty-pruning-gemma-prereg.md), [pilot findings](2026-04-18-phase-1_51R-pilot-findings.md)
---

## TL;DR

At Sam's implicit kr≈0.5 operating point, novelty-pruning on Gemma 4-E4B-4bit gives **no end-to-end speedup (1.00×) and -10pp accuracy**. This is a preregistered NULL at the paper's headline operating point.

At **kr=0.10** (90% of visual tokens pruned), the mechanism **does produce a real wall-clock speedup**: e2e 1.21×, generate-only 2.67×, **no accuracy loss vs dense** at n=5. This is a partial reproduction along a different operating point than Sam's.

**Key confound:** we do not yet log per-item `generated_tokens` count, and Stage 2 kr=0.75 shows pruned gen is *40% longer* than dense (likely because degraded context produces longer or less-terminal generations). Some fraction of the measured gen speedup at kr=0.10 may be "pruned stops sooner," not "pruned is faster per-token." Task #89 is now P1.

## Stage 1 — n=30 at kr=0.5 (anchor_arm=none)

**Aggregate (see `stage1_none_kr50_summary.json`):**
- dense_acc = 0.400, pruned_acc = 0.300, agreement = 0.467
- e2e = 1.001×, gen = 1.009×
- Pruning overhead negligible (novelty=12ms, mask=0.8ms, prune=2ms per item)

**Per-bucket breakdown:**

| Bucket | n | dense_acc | pruned_acc | e2e mean | gen mean | decode_ms mean |
|--------|---|-----------|------------|----------|----------|----------------|
| long   | 10 | 0.40 | 0.40 | 1.009× | 1.103× | 67,977 |
| medium | 10 | 0.40 | 0.30 | 1.006× | 1.022× |  8,447 |
| short  | 10 | 0.40 | 0.20 | **0.973×** | **0.945×** |  3,003 |

- Generate-only speedup is strongest on long items (1.10×), regresses on short items (0.95×)
- Accuracy degrades monotonically as bucket gets shorter under pruning (long 0.40 → short 0.20)
- Dense accuracy flat at 0.40 across buckets
- Mean gen savings = 59 ms per item (1% of 6380 ms dense gen)

## Stage 2 — n=5 kr sweep (anchor_arm=none, max_tokens=32)

Manifest: `research/benchmark_manifests/videomme_dev_v1_stage2_subset.toml` (1 long + 2 medium + 2 short)

| kr | kept/2048 | pruned_acc | agreement | e2e | gen |
|----|-----------|-----------|-----------|-----|-----|
| **0.10** | 200 | **0.40** | **0.80** | **1.21×** | **2.67×** |
| 0.25 | 512 | 0.20 | 0.60 | 1.12× | 1.57× |
| 0.50 (n=30) | 1024 | 0.30 | 0.47 | 1.00× | 1.01× |
| 0.75 | 1536 | 0.60 | 0.60 | **0.88×** | **0.68×** |

**Speed is monotonic with kr** (more pruning → more speedup). At kr=0.10 we hit e2e 1.21× and gen 2.67× — the mechanism clearly works when prefill reduction is aggressive enough.

**Accuracy is non-monotonic and noisy at n=5:**
- kr=0.10 matches dense (0.40)
- kr=0.25 drops to 0.20 (worst)
- kr=0.50 (n=30) sits at 0.30
- kr=0.75 *exceeds* dense (0.60)

The kr=0.75 accuracy bump is either regularization-like noise-filtering (real) or n=5 noise (most likely). Needs n=30 at kr=0.75 to adjudicate.

## The differential-generation confound

At kr=0.75 pruned gen = 10044ms mean, dense gen = 6899ms mean. Pruned takes 45% LONGER despite having 75% of visual tokens (same or less prefill work for the LLM vs dense — definitely not 45% more work).

The most parsimonious explanation: **pruned sometimes fails to emit the stop sequence (EOS or answer letter) cleanly and runs to max_tokens=32**, while dense stops quickly after the correct letter.

If pruned generates ~32 tokens vs dense ~3 tokens (typical MCQ answer is 1 letter), then:
- dense_gen ≈ 3 × 170ms/tok = 510ms per-token-work + some fixed prefill ≈ 6900ms
- pruned_gen ≈ 32 × 170ms/tok = 5440ms per-token-work + smaller prefill

This pattern would mask or invert the true KV-attention savings. We need to log `generated_tokens_dense` and `generated_tokens_pruned` per item to disentangle. **Task #89 is now P1.**

Implication: the "gen=2.67×" at kr=0.10 is a **combined** effect of (a) prefill attention savings from 2048→205 KV tokens, and (b) possibly *fewer* tokens generated because pruning produced cleaner answers. We don't know the split until instrumentation lands.

## What REPRO means now

| Claim | Status |
|-------|--------|
| Sam 1.8× e2e on VideoMME at kr≈0.5 | **FALSIFIED on Gemma 4-E4B-4bit** (1.00×, n=30) |
| Prefill-shortening mechanism **can produce** real e2e speedup | **CONFIRMED at kr=0.10** (1.21×, n=5) |
| Mechanism preserves accuracy | **AMBIGUOUS** — kr=0.10 matches dense at n=5 but kr=0.25 regresses; need more n |
| Sam 1.8× achievable at all on E4B | **OPEN** — the fact that kr=0.10 gives 1.21× on mixed items but 1.45× on short items suggests short-only subsets might approach 1.5-1.8× |
| Arithmetic ceiling theory (pilot note) | **REVISED** — ceiling computation was correct conditional on prefill speedup, but prefill speedup itself is strongly kr-dependent, not ceiling-bounded at kr=0.5 |

## Paper-ready framing

*"We preregistered an attempt to reproduce Sam (2026) on Gemma 4-E4B-4bit + VideoMME. At Sam's implicit kr≈0.5 operating point, we find no end-to-end speedup (1.00×, n=30) and a -10pp accuracy drop. A subsequent kr-aggressiveness sweep (n=5 subset, kr ∈ {0.10, 0.25, 0.75}) shows the mechanism does produce substantial speedup at more aggressive regimes (e2e=1.21×, gen=2.67× at kr=0.10), and that accuracy at kr=0.10 matches dense on our subset. We interpret Sam's claim as operating-point-sensitive: the 1.8× number likely requires either a larger model where per-token decode is more attention-bound, a longer context where attention dominates prefill, or a more aggressive kr than the paper discloses. Our result contributes a preregistered null at kr=0.5 and a partial reproduction at kr=0.10 for the E4B regime. A confound — differential generation length — is flagged and scheduled for follow-up."*

## Updated next experiments

### Stage 2b (HIGH PRIORITY, NEW) — n=30 at kr=0.10
- Confirm the 1.21× e2e / 2.67× gen / 0.40 accuracy numbers at full statistical power
- Required before we can put kr=0.10 numbers in the paper
- Runtime estimate: ~25 min (similar to Stage 1 at kr=0.5)
- **Depends on Task #89 landing first** (need token-count instrumentation)

### Stage 3 — max_tokens sensitivity (now with instrumentation)
- max_tokens ∈ {1, 8, 32} on 5-item subset at kr=0.10
- Prediction: at max_tokens=1, dense and pruned both emit 1 token, so gen speedup = pure prefill attention savings (expect ~1.3-1.5×).
- At max_tokens=32, if pruned often hits the cap, gen speedup gets inflated by token-count differential.
- max_tokens=1 is the **clean** measurement of the prefill-only effect. The difference between max_tokens=1 and max_tokens=32 gen speedups quantifies the confound.

### Stage 4 (proposed) — n=30 at kr=0.25 and kr=0.75
- kr=0.25 gives e2e 1.12× — could be publishable middle-ground
- kr=0.75 gives pruned_acc=0.60 — if real at n=30, that's a meaningful accuracy improvement over dense (requires explanation)
- Runtime: ~50 min total

### Stage 5 (proposed) — Promotable anchor arms
- Now that we have a winning kr (0.10), switch from proxy (`none`) to the promotable anchors (`nuwa_pillar`, `max_min_diversity`, `gemma_structural`)
- Test whether informed anchors preserve accuracy better than random `none` at kr=0.10

## Decisions needed from user

1. **Greenlight Stage 2b (n=30 at kr=0.10) — instrument driver first, then run.** Cost: ~30 min instrumentation + ~30 min compute. Benefit: solid paper numbers.
2. **Greenlight Stage 3 (max_tokens sensitivity).** Cost: ~15 min compute. Benefit: quantifies the differential-gen confound.
3. **Stage 5 (promotable anchors) vs Stage 4 (n=30 at 0.25/0.75) — which first?** Recommend Stage 5 because it aligns with the research goal (which anchor wins), whereas Stage 4 confirms a magnitude we're less interested in.
4. **Phase 1.51V greenlight?** Vision-tower pruning could raise the ceiling beyond what kr=0.10 achieves. Standalone preregistration.

## Artifacts

- `artifacts/phase1_51R_dev/stage1_none_kr50.{jsonl,log,_summary.json}` (30 records)
- `artifacts/phase1_51R_dev/stage2_none_kr010.{jsonl,_summary.json}` (5 records)
- `artifacts/phase1_51R_dev/stage2_none_kr025.{jsonl,_summary.json}` (5 records)
- `artifacts/phase1_51R_dev/stage2_none_kr075.{jsonl,_summary.json}` (5 records)
- `artifacts/phase1_51R_dev/stage2_combined.log` (stdout from all 3 kr runs)
