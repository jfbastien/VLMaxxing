# Execution Plan — Round 7

Author: Claude (takeover from codex)
Date: 2026-04-14
Parent: [PLAN.md](../PLAN.md)

## Context

Codex has built a strong methodology substrate (preregistration, dev/holdout
discipline, claim register, reproduction-status ledger, feature replay cache,
frame-budget baseline driver) but has under-explored the method space and
under-sampled the benchmark slices. The user's frustration is that iterations
have been too small and too quickly interpreted as null results.

This plan is a time-boxed push to answer two concrete questions in the next
tranche:

1. **Is there a Pareto-optimal training-free temporal-reuse policy that beats
   matched dense frame-budget baselines on a frozen holdout at stable N?**
2. **What does the quality-vs-compute trade-off curve look like across
   statistic × reuse_classes × max_age × refresh_interval, with proper grid
   coverage?**

If the answer to (1) is yes, we have a method-paper-candidate result and move
to Track B bring-up. If no, we pivot to composition (FastV + ours) and/or
task-aware routing.

## Current Position (2026-04-14)

- Whitepaper reproduction: TOMATO 0.833 agreement on 30-item dev, MVBench 0.870
  on 54-item dev. Neither matches the imported 1.000 headline, but the
  predecessor's 1,155/1,484 both-wrong-matched items make the 1.000 claim
  partly a parser artifact, not a method claim.
- Direct mechanism §2.1 reproduced exactly; §2.2/§2.3 partial at 4-bit MLX.
- Track A substrate locked: cache-path identity (A0=A1 exactly), dense
  determinism, preregistration discipline.
- Best dev-side finding: `mean + max_age=4` reaches cached 0.400 at
  fresh-token-equivalent budget ~1247, matching dense-6 at 2400 tokens. Dev-only
  Pareto win. Holdout flat.
- No Track B measurements anywhere in the repo.

## Strategic Framing

The honest story is:
- The whitepaper's "100% agreement" is partly a parser artifact on
  both-wrong items
- Our strict-parser measurement shows real residual disagreement
- There is a trade-off curve; we have not yet mapped it at scale
- At at least one dev-side point, cached beats matched dense frame-budget
- The path to SOTA is (a) stabilize that win on holdout at larger N and
  matched MVBench, (b) measure actual compute savings in Track B, (c) compose
  with FastV or ToMe for multiplicative token reduction

## Execution Sequence

### Stage A — Provenance + logging infrastructure (today)

**A1. Feature cache model content-hash** (cheap, ~30 min)
- Add `model_content_sha256` to `CacheKey` based on weight-file hashing
- Invalidate existing cache on hash-format change (one-time delete)
- Commit with test
- Addresses: other-codex feedback on silent staleness

**A2. Option-logprob logging** (medium, ~2 hrs)
- In `_generate_text`, capture per-option log-probabilities at the answer
  position (A, B, C, D, E, F depending on item)
- Add `dense_margin`, `cached_margin`, `top2_gap` fields to output records
- Backward-compatible: older artifacts unchanged, new runs include logprobs
- Addresses: chatGPT + Claude feedback on confidence-vs-staleness

**A3. Frame-budget driver env-block parity** (cheap, ~15 min)
- Record full environment block matching the main runner
- Addresses: other-codex feedback on summary divergence

### Stage B — Matched controls on MVBench (tonight)

**B1. MVBench motion frame-budget baselines** (~1.5 hrs LLM time)
- Run dense at {1, 2, 3, 4, 6, 8} frames on `mvbench_motion_dev_v1.toml` and
  `mvbench_motion_holdout_v1.toml`
- Write `phase-1_9-mvbench-motion-frame-budget-baselines.md`
- Artifact: `phase1_9_mvbench_motion_frame_budget_baselines.json`

**B2. Current best policy on MVBench motion** (~45 min LLM time)
- `mean + max_age=4` on mvbench_motion_dev + holdout
- Compare to MVBench dense baselines
- Does the dev-side Pareto win transfer?

### Stage C — Proper grid search with feature replay (day 2)

**C1. Grid search infrastructure** (~2 hrs coding)
- `scripts/planner_grid_search.py`:
  - CPU-only threshold calibration pass to find threshold triples matching
    target active-reuse bins {0.5, 0.65, 0.8, 0.9}
  - Full grid: statistic × thresholds × reuse_classes × max_age
  - Uses feature replay cache — so repeated policies don't re-encode
  - Writes per-policy JSONL + aggregate summary
- Predicted ~60-80 real LLM evaluations per slice (after calibration)

**C2. Run grid on TOMATO motion dev** (~3 hrs LLM time w/ replay)
- Commit artifact + `phase-1_10-planner-grid-tomato-motion-dev.md`

**C3. Run grid on MVBench motion dev** (~3 hrs LLM time w/ replay)
- Commit artifact + `phase-1_11-planner-grid-mvbench-motion-dev.md`

**C4. Pareto analysis + winner selection** (~1 hr coding + analysis)
- `scripts/pareto_analysis.py` — per slice, compute which policies dominate
  dense-N-frame at matched fresh-token budget
- Commit `paper/pareto-findings.md`

**C5. Holdout eval of selected winners ONLY** (~1.5 hrs LLM time)
- Up to 5 Pareto-dominating policies per slice, evaluated on holdout
- `phase-1_12-grid-winners-holdout.md`

### Stage D — Logprob stratification analysis (day 3)

**D1. Rerun existing dev/holdout with logprobs** (~1 hr)
- Default mean + top Pareto policies
- Build stratification: confidence-limited vs staleness-limited

**D2. Conditional Pareto analysis** (~1 hr)
- Report agreement + cached-accuracy conditional on `dense_margin > 0.5`
- The "real" caching quality metric excludes items where dense itself is weak
- Commit `phase-1_13-logprob-stratification.md`

### Stage D' — Post-holdout refinement tranche (day 3–4, conditional)

Added 2026-04-15 after phase 1.11 surfaced a genuinely strong MVBench dev
winner. These phases depend on phase 1.12 holdout outcomes and are
preregistered but not yet launched.

**Phase 1.14 — MVBench `max_abs` threshold refinement** (~1.3 hrs GPU)
- 5 neighbor thresholds around `max_abs(8,32) static+shifted noage`
- Gates on phase 1.11 winner confirmation
- `research/experiments/2026/2026-04-15-phase-1_14-mvbench-max-abs-threshold-refinement.md`

**Phase 1.15 — TOMATO `max_abs` threshold refinement** (~1.6 hrs GPU)
- 6 neighbor thresholds around `max_abs(8,32) static+shifted age=4`
- Gates on phase 1.12 TOMATO winner surviving on at least one slice
- `research/experiments/2026/2026-04-15-phase-1_15-tomato-max-abs-threshold-refinement.md`

**Phase 1.16 — Cross-benchmark winner transfer** (~0.5 hrs GPU)
- TOMATO winner evaluated on MVBench dev, and MVBench winner on TOMATO
  dev, at identical config
- Does NOT gate on phase 1.12 — diagnostic regardless of holdout outcome
- `research/experiments/2026/2026-04-15-phase-1_16-cross-benchmark-winner-transfer.md`

**Phase 1.17 — MVBench winner refresh-interval sweep** (~0.75 hrs GPU)
- `refresh_interval ∈ {1, 2, 4, 0}` traces a quality-vs-reuse curve from
  a single base policy
- Gates on phase 1.11 winner confirmation; runs regardless of phase 1.12
- `research/experiments/2026/2026-04-15-phase-1_17-mvbench-winner-refresh-interval-sweep.md`

**Phase 1.18 — MVBench winner frame-count scaling** (~1.3 hrs GPU)
- `frame_count ∈ {4, 8, 12, 16}` under the same policy
- New dense-12 and dense-16 baselines built if budget allows
- Gates on phase 1.11 winner confirmation; runs regardless of phase 1.12
- `research/experiments/2026/2026-04-15-phase-1_18-mvbench-winner-scale-check.md`

Execution order (if phase 1.12 passes on MVBench):

1. Phase 1.11 sweep completes (in-flight)
2. Phase 1.12 holdout evaluation
3. Phase 1.13 logprob stratification
4. Phase 1.16 cross-benchmark transfer (diagnostic, independent of 1.12)
5. Phase 1.14 MVBench refinement (if MVBench winner survives holdout)
6. Phase 1.17 MVBench refresh sweep
7. Phase 1.18 MVBench frame-count scaling
8. Phase 1.15 TOMATO refinement (if TOMATO winner survives holdout)

Total post-1.11 autonomous budget: ~7–8 hrs GPU when all phases run.

### Stage D'' — Scaling, transfer, and methodology fixes (day 4–5)

Added 2026-04-15. These phases extend the autonomous queue by another
~9 hrs so the agent has a deep enough runway to keep making progress
while the operator is away, without ever needing approvals.

**Phase 1.19 — Calibration-metric alignment** (~1.5 hrs code + 15 min
 CPU)
- Fix the known mismatch between `planner_grid_search.py::_calibrate`
  and `run_benchmark_track_a.py::_compute_reuse_ratio` so calibration
  bins align with runner-reported active reuse
- Low priority; runs as filler between GPU-bound phases
- `research/experiments/2026/2026-04-15-phase-1_19-calibration-metric-alignment.md`

**Phase 1.20 — TOMATO motion slice enlargement (N=15→30)** (~3 hrs)
- New v2 manifests with seed=42 stratified random sample; rerun dense
  curve + TOMATO winner cells
- Tightens or weakens the TOMATO dev Pareto claim with wider CIs
- Gates on phase 1.12 holdout resolution
- `research/experiments/2026/2026-04-15-phase-1_20-tomato-motion-slice-enlargement.md`

**Phase 1.21 — MVBench motion slice enlargement (N=15→30)** (~3.5 hrs)
- Same design as 1.20 but for MVBench motion
- Highest-priority N=30 phase because MVBench winner is the strongest
  point in the repo
- `research/experiments/2026/2026-04-15-phase-1_21-mvbench-motion-slice-enlargement.md`

**Phase 1.22 — MVBench non-motion winner transfer** (~1.5 hrs)
- Does the MVBench winner survive on non-motion MVBench slices?
- Independent of phase 1.12
- `research/experiments/2026/2026-04-15-phase-1_22-mvbench-non-motion-winner-transfer.md`

**Phase 1.23 — FastV composition scouting** (design doc only, ~1.5 hrs)
- Produce `docs/fastv-composition-plan.md` — hook point map, MLX API
  touch list, engineering-effort classification
- No benchmark runs; filler work
- `research/experiments/2026/2026-04-15-phase-1_23-fastv-composition-scouting.md`

Total Stage D'' autonomous budget: ~9 hrs GPU + 1.5 hrs CPU/design.

### Stage E — Track B design + skipped-compute measurement (day 4+)

**E1. In-memory timing harness design doc**
- Clock sources, sync points, decode path
- Before running, get peer review

**E2. Vision-encode skipped-compute measurement**
- Under optimal cached policy, what fraction of vision-encode FLOPs are
  actually skipped in a multi-turn QA path?
- First real Track B number

### Stage F — Composition + larger N (week 2+)

**F1. Larger frozen slices**
- Expand TOMATO motion to 45 items, MVBench motion to 45 items
- Stratified random with seed 42

**F2. Cross-benchmark aggregate numbers**
- "Our method at [config] reaches [agreement] at [fresh-token budget]"
- Across TOMATO full + MVBench hosted full

**F3. FastV composition (stretch)**
- Adapt FastV's token-pruning hook to Qwen 2.5-VL MLX path
- Compose with cached temporal reuse
- Measure quality-compression Pareto

## Concrete Success Criteria

| Stage | Output | Metric to beat |
|---|---|---|
| B1 | MVBench motion Pareto chart | replicate TOMATO dev-side win shape or explain why it fails |
| C5 | Holdout Pareto on 2 slices | ≥1 policy strictly dominates dense-4-frame on ≥1 slice |
| D2 | Stratified agreement | confidence-adjusted agreement ≥ 0.92 on ≥1 slice |
| E2 | Vision-encode FLOP skip | measured ≥30% skipped at agreement ≥ 0.85 |

## What Triggers a Pivot

Pivot to pure composition (FastV + ours) if:
- Stage C5 holdout produces no Pareto-dominating policy
- Stage D2 shows stratified agreement ≤0.88 even on non-confidence-limited items

Pivot to task-aware routing if:
- MVBench motion Pareto is clearly different shape from TOMATO motion
- Content-class signal is strong enough to condition the policy

## Paper Framing After Each Stage

### If Stage C5 wins:
> "Training-free temporal feature reuse with bounded staleness traces a better
> quality-vs-compute Pareto frontier than dense frame subsampling on video
> temporal-reasoning benchmarks. [Agreement X at Y% budget on holdout.] No
> training, no new parameters, composable with existing token-pruning methods."

### If Stage C5 loses:
> "Honest evaluation of training-free temporal feature reuse reveals that the
> naive pixel-diff planner achieves matched dense-frame quality on some
> content classes but does not beat simple frame budgeting on holdout
> motion-heavy benchmarks. We identify the composition axis (temporal × token
> pruning) as the more promising path; preliminary FastV + ours combination
> reaches [Z]."

## Reporting Discipline

- Every stage ends with a committed experiment note + artifact JSON
- Decision log gets a dated row per resolved hypothesis
- `paper/framing.md` only updates when a claim crosses confidence threshold
  (holdout result, ≥1 Pareto-dominating point, Wilson CI doesn't overlap dense
  baseline)
- Claim register stays frozen; status table updates in `reproduction-status.md`

## Non-negotiables

- No dev-to-holdout tuning. Dev selects ≤5 policies; holdout runs once per.
- No silent policy changes. All sweeps are grid-search or preregistered.
- No "we got tired" null results. If a search fails, document what WASN'T tried
  and add it to the plan.
- No Track B claims without in-memory timing, phase separation, and pre-reg.
- No composition claim without matched-budget baselines for both components.

## Expected Duration

- Stage A: 1 day (today)
- Stage B: 0.5 days
- Stage C: 2 days
- Stage D: 1 day
- Stage E: 2-3 days
- Stage F: 3-5 days

Total: ~1-2 weeks to method-paper-competitive result, IF the Pareto
dominance survives holdout.
