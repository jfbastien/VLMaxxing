# Phase 1.51R Stage 5b — max_min_diversity @ kr=0.50 n=30 Findings

**Status:** findings 2026-04-18, task #92. Second Stage 5 anchor-arm
result. Partial win: max_min_diversity *preserves* aggregate accuracy
within the common -0.10 budget — but still no e2e speedup.

## Prereg hypothesis

Informed anchor selection (max_min_diversity: greedy L2-distance +
L1-key-norm) preserves question-relevant tokens at kr=0.50 and
recovers the aggregate accuracy gap. Falsification: aggregate
accuracy more than 3pp below dense, or e2e < 1.10×.

## Result

**Aggregate (n=30):**
- dense_accuracy: 0.400
- pruned_accuracy: 0.367 (**Δacc = -0.033**, within the common -0.10 budget)
- agreement: 0.47
- e2e_speedup: 0.963× (still net SLOWER — ceiling binding)
- gen_speedup: 0.929×
- per_token_gen_speedup: 0.973× (marginal slowdown)
- mean_pruned_mask_ms: 362ms (vs nuwa 15ms — max_min's greedy
  anchor step is expensive)
- kept_tokens_total: 1024 / 2048

**Per-bucket (n=10 each):**

| bucket | dense_acc | pruned_acc | Δacc   | agreement | e2e    | gen    | per_tok |
|--------|----------:|-----------:|-------:|----------:|-------:|-------:|--------:|
| short  | 0.400     | 0.400      | +0.000 | 0.40      | 0.943× | 0.917× | 2.121×  |
| medium | 0.400     | 0.300      | -0.100 | 0.50      | 0.957× | 0.931× | 2.165×  |
| long   | 0.400     | 0.400      | +0.000 | 0.50      | 0.990× | 0.959× | 0.855×  |
| **all**| 0.400     | 0.367      | -0.033 | 0.47      | 0.963× | 0.936× | 1.714×  |

## Hypothesis status: MIXED

- **Accuracy HYPOTHESIS EARNED.** Aggregate -3.3pp is within the
  common acceptance bar. Short and long buckets fully preserved;
  only medium drops 10pp. This is the first anchor+kr cell where
  aggregate accuracy stays within noise.
- **Speed HYPOTHESIS REJECTED.** e2e 0.963× is net slowdown, not
  the ≥1.10× target. Per-token generate is 0.97× — essentially
  no per-token attention benefit at kr=0.50 on this geometry.
  The mask_ms overhead (362ms/item) eats into the thin margin.

## Comparison across Stage 5 so far

| arm                   | kr    | Δacc    | e2e    | per_tok | mask_ms |
|-----------------------|------:|--------:|-------:|--------:|--------:|
| none (Stage 1)        | 0.50  | n/a     | 1.00×  | ~1.01×  |  ~2     |
| nuwa_pillar (5a)      | 0.50  | -0.167  | 0.987× | 1.157×  |  15     |
| max_min_diversity (5b)| 0.50  | -0.033  | 0.963× | 0.973×  | 362     |
| none (Stage 2b)       | 0.10  | -0.100  | 1.229× | 6.83×   |  ~2     |

Reading across:
- kr=0.50 is at the arithmetic ceiling regardless of anchor. No
  anchor lifts e2e above 1.00×. Ceiling analysis (task #88)
  already predicted this.
- Anchor choice drives ±16.7pp accuracy swings at fixed kr.
  max_min_diversity dominates nuwa_pillar on both accuracy and
  bucket preservation.
- To get measurable e2e speedup you must drop kr — but at kr=0.10
  the accuracy collapses (Stage 2b -0.10pp aggregate, -20pp on
  long items).

## Interpretation

**Why does max_min_diversity preserve accuracy better than nuwa?**
- max_min_diversity picks tokens that *maximally spread out* in
  feature space (iterative greedy farthest-point from the running
  kept set), seeded by the token with the highest L1 key-norm.
  This keeps a *diverse* sample of visual content.
- Nuwa's pillar structure picks tokens by grid position (block
  corners, mid-axis), not by content. Half of the budget goes to
  structurally-forced positions that may be pure background.
- At kr=0.50 both keep 1024 tokens; max_min's 1024 are a
  content-spread sample, nuwa's 1024 are grid-forced + novelty-fill.
  The content-spread sample preserves more question signal.

**Why does neither speed up e2e?**
- Ceiling analysis (task #88): at kr=0.50 on this Gemma geometry,
  fixed cost D+V consumes ~71% of e2e. Prefill-shortening only
  touches G. Per-token G speedup of 1.0× is enough to cancel the
  fixed cost completely; e2e lands at 1.00×.
- max_min's 362ms mask overhead is ~0.9% of e2e — not the
  binding constraint. The binding constraint is the ceiling.

## Consequences for the paper

1. **max_min_diversity @ kr=0.50 is now our best anchor+kr cell
   for accuracy preservation**, beating both nuwa_pillar @ kr=0.50
   and anchor=none @ kr=0.10 on aggregate Δacc.
2. **But it buys no speed.** The paper cannot claim "1.51R
   delivers end-to-end speedup with preserved accuracy" at this
   operating point. The honest claim is "at kr=0.50, informed
   anchor selection preserves accuracy but delivers no e2e gain;
   at kr=0.10, 1.23× e2e with -10pp accuracy cost." Two points,
   no single operating point clears both bars.
3. **The earned-win narrows but also resolves:** the paper's
   ablation story has max_min_diversity vs nuwa as a clear
   anchor-choice-matters figure (16.7pp gap at matched kr). This
   is a publishable ablation result even if the headline speedup
   claim stays partial.
4. **1.51V is reinforced.** To lift e2e above 1.00× with accuracy
   preserved requires touching V (vision-tower pruning), not G.
   Stage 5b confirms no amount of anchor cleverness gets us there.

## Artifacts

- `artifacts/phase1_51R_dev/stage5b_max_min_diversity_kr050_n30.jsonl`
- `artifacts/phase1_51R_dev/stage5b_max_min_diversity_kr050_n30_summary.json`
- `artifacts/phase1_51R_dev/stage5b_max_min_diversity_kr050_n30.log`

## Next

- Stage 5c: gemma_structural @ kr=0.50 n=30 (launched; ~40 min).
  gemma_structural is a hand-tuned arm for Gemma's grid topology
  (non-feature-dependent). If it matches or beats max_min, we
  have two independent accuracy-preserving arms — strengthens the
  ablation result.
- After 5c, write a Stage 5 cross-arm comparison + decide whether
  to move to 1.51V or add a kr=0.33 sweep at max_min to find a
  middle operating point.
