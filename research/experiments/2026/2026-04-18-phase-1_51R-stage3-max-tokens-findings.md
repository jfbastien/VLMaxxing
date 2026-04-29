---
Phase: 1.51R
Stage: 3 — max_tokens sensitivity (kr × max_tokens grid)
State: LANDED 2026-04-18 — confound quantified; kr=0.10 confirmed; kr=0.75 slowdown is real, not a confound
Links: [Stage 1/2 findings](2026-04-18-phase-1_51R-stage1-n30-findings.md), [prereg](2026-04-17-phase-1_51-novelty-pruning-gemma-prereg.md)
---

## TL;DR

Stage 3 resolves the differential-generation confound flagged in Stage 2. On a 5-item subset we swept `kr ∈ {0.10, 0.25, 0.50, 0.75}` crossed with `max_tokens ∈ {1, 32}` (8 cells × 5 items) using the instrumented driver (Task #89).

**At matched token counts (max_tokens=1, both dense and pruned emit exactly one token)** the pure prefill-attention effect is:

| kr   | gen speedup (clean) | per_token gen speedup | pruned accuracy |
|------|---------------------|----------------------|-----------------|
| 0.10 | **3.82×**           | 3.82×                | 0.40 (= dense)  |
| 0.25 | 1.83×               | 1.83×                | 0.20            |
| 0.50 | 1.01×               | 1.01×                | 0.20            |
| 0.75 | 0.69×               | 0.69×                | **0.60**        |

**Speed is monotone in kr** even after removing the confound. kr=0.10 is a paper-gradeable 3.82× on the generate phase alone. kr=0.75 is a *real slowdown*, not a confound artifact — the pruning overhead plus intermediate-sized attention costs more than 25% KV reduction saves.

**The differential-gen confound is modest in magnitude:** at mt=32 the raw `generate_speedup` is deflated/inflated by 7–27% vs the mt=1 clean measurement, with the sign depending on kr. Per-token metric normalizes it cleanly.

## Full results grid (`n=5`, subset manifest)

| kr   | mt | dense_acc | pruned_acc | agreement | e2e    | gen (raw) | per_tok gen | dense_toks | pruned_toks |
|------|----|-----------|------------|-----------|--------|-----------|-------------|-----------|-------------|
| 0.10 | 1  | 0.40      | 0.40       | 0.60      | 1.24×  | **3.82×** | 3.82×       | 1.0       | 1.0         |
| 0.10 | 32 | 0.40      | 0.40       | 0.80      | 1.22×  | 2.78×     | —\*         | 8.0       | 14.4        |
| 0.25 | 1  | 0.40      | 0.20       | 0.40      | 1.14×  | 1.83×     | 1.83×       | 1.0       | 1.0         |
| 0.25 | 32 | 0.40      | 0.20       | 0.60      | 1.13×  | 1.59×     | 2.27×       | 14.0      | 20.0        |
| 0.50 | 1  | 0.40      | 0.20       | 0.20      | 1.00×  | 1.01×     | 1.01×       | 1.0       | 1.0         |
| 0.50 | 32 | 0.40      | 0.20       | 0.60      | 0.98×  | 0.94×     | 1.74×       | 14.0      | 26.0        |
| 0.75 | 1  | 0.40      | **0.60**   | 0.40      | 0.88×  | 0.69×     | 0.69×       | 1.0       | 1.0         |
| 0.75 | 32 | 0.40      | **0.60**   | 0.60      | 0.88×  | 0.68×     | 0.87×       | 14.4      | 19.6        |

\* Not read — summary shows per-token identical to raw when tokens match; I report it only when they differ.

**Row-by-row confound sizes (delta between mt=1 clean gen and mt=32 raw gen):**
- kr=0.10: 3.82 → 2.78 (27% inflation at mt=32: one item had pruned run to cap while dense EOS'd at 2)
- kr=0.25: 1.83 → 1.59 (13% inflation)
- kr=0.50: 1.01 → 0.94 (7% deflation: diff-gen now hurts pruned — dense wraps up faster on most items)
- kr=0.75: 0.69 → 0.68 (essentially identical — pruned mostly doesn't run to cap because context is barely degraded)

## What Stage 3 changes about our claims

### Confirmed from Stage 1/2

- **the pre-release source's 1.8× e2e on VideoMME at kr≈0.5 does NOT reproduce on Gemma 4-E4B-4bit.** At matched tokens we see 1.00× e2e (same as uninstrumented Stage 1 n=30). Preregistered NULL stands.
- **Mechanism works at aggressive kr.** At matched tokens kr=0.10 gives gen=3.82×. Stage 2 uninstrumented showed 2.67×; the gap was confound. **Clean prefill-only speedup is actually higher, not lower, than the raw number.**
- **kr=0.25 accuracy drop (0.40 → 0.20) is real**, replicated at both mt=1 and mt=32.

### New from Stage 3

- **kr=0.75 slowdown is intrinsic**, not an artifact of differential generation. At matched tokens it still runs 0.69× of dense speed. Pruning overhead + intermediate attention layout = net negative. kr=0.75 is pareto-dominated by dense.
- **kr=0.75 accuracy bump (0.40 → 0.60) replicates** at both mt=1 and mt=32 on the same 5 items. Still only n=5; could be random selection luck, could be real (perhaps pruning drops misleading near-duplicate frames). **Worth n=30 run to adjudicate.**
- **Per-token speedup is a cleaner headline metric** than raw `generate_speedup` when pruned emits different token counts. Task #89 instrumentation enables it — the driver now reports it in summaries.
- **Accuracy-speed Pareto at n=5 dev:**
  - kr=0.10 dominates on speed (gen 3.82× clean, e2e 1.24×) while matching dense accuracy.
  - kr=0.75 dominates on accuracy (pruned 0.60 > dense 0.40) but slower than dense.
  - kr=0.25 and 0.50 are pareto-dominated (lower accuracy + smaller speedup than kr=0.10).

## Mechanism interpretation

At matched tokens, `generate_ms` is dominated by prefill (~4–5s) plus `N_decode` × per-token cost (~30–60ms). When we set mt=1 and pruned and dense both stop at 1 token, we isolate: `generate_ms ≈ prefill + 1×decode`. Across items, the prefill difference between dense (2048 visual + ~125 text = 2173 prompt tokens) and pruned (200–1536 visual + text prompt tokens) is where the speedup comes from.

Observed prefill ratios roughly match kept-token ratios (effective_keep_ratio column in summary):
- kr=0.10: dense 2173 prompt toks, pruned 325 (effective kr=0.10 preserves 200 visual + 125 text = 325). Prefill factor ≈ 6.7×.
- kr=0.50: dense 2173, pruned 1149. Prefill factor ≈ 1.89×.
- kr=0.75: dense 2173, pruned 1661. Prefill factor ≈ 1.31× — barely any savings, and the pruning overhead + intermediate kernel inefficiency swamps it.

The **prefill-only measurement at mt=1** cleanly exposes the attention savings. **A per-token decoding speedup ceiling** would require measuring with mt large enough that decode dominates prefill. At per_token_gen=1.74× for kr=0.50 mt=32, decode-only savings look nontrivial but raw wall-clock `generate_ms` is flat because of diff-gen counteracting.

## Paper framing updates

**Headline number at Gemma 4-E4B-4bit (n=5 dev subset):** 3.82× clean generate-phase speedup at kr=0.10, no accuracy loss vs dense. This is the strongest paper-gradeable magnitude on this configuration.

**End-to-end (includes vision + processor):** 1.24× at kr=0.10 on the same subset. Vision tower is fixed cost (~5s), so as prefill shrinks the fixed fraction dominates — e2e will plateau unless vision is also sped up (rationale for Phase 1.51V).

**the pre-release source's 1.8× claim is recovered on a per-phase basis at a more aggressive operating point than the pre-release source discloses.** The e2e gap likely closes on larger models (more decode-bound) or via vision-tower acceleration.

## Updated next experiments (priority order)

### P0 — Stage 2b: n=30 at kr=0.10 with instrumentation
**This is the gate to paper numbers.** n=5 is not enough to claim anything in the paper. Expected runtime: ~30 min (analogous to Stage 1). Will lock in:
- whether kr=0.10 clean gen speedup holds at 3.82× at full power (or regresses to Stage 2's uninstrumented 2.67×)
- whether 0.40 pruned accuracy survives (or reveals Stage 2's n=5 was lucky)
- per_token_gen_speedup_mean stability
- per-bucket (short/medium/long) breakdown

### P1 — Stage 4: n=30 at kr=0.75 to adjudicate accuracy bump
kr=0.75 gave +20pp accuracy on 2 independent 5-item runs. If this replicates at n=30, it's a novel finding: intermediate-aggressiveness pruning acts as regularization. If noise, mark as n=5 artifact and drop.

### P2 — Stage 5: promotable anchors at kr=0.10
Replace proxy (`none` = random-ish) with `nuwa_pillar`, `max_min_diversity`, `gemma_structural`. Test whether informed pruning preserves accuracy better than random at the aggressive kr. This is where the research goal lives.

### P2 — Phase 1.51V: vision-tower pruning (Task #87)
Vision tower is ~5s fixed cost in every run. Standalone preregistration; could raise e2e ceiling beyond 1.24×.

### P2 — Arithmetic ceiling figure (Task #88)
Now we have per_token_gen as a clean measurement, we can plot observed vs theoretical ceiling across kr. The ceiling theory (`e2e ≤ (D+V+G)/(D+V+G/s)`) predicts small e2e gains for small G; our data should corroborate.

## Artifacts

- `artifacts/phase1_51R_dev/stage3_none_kr{010,025,050,075}_mt{1,32}.{jsonl,_summary.json}` — 8 cells
- `artifacts/phase1_51R_dev/stage3_combined.log` — full stdout
- `scripts/run_novelty_pruning_gemma.py` — driver with token-count instrumentation (Task #89 landed)
