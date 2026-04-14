# Research Progress Snapshot — 2026-04-14

This document is a single-file snapshot of where the project stands at the
end of the round-7 takeover tranche.

## Whitepaper Reproduction

| Whitepaper claim | Local status | Notes |
|---|---|---|
| §2.1 ViT identity (cos=1, max_diff=0) | **Reproduced** | Exact identity on Qwen 7B 4-bit MLX repeated encodes |
| §2.2 partial-change locality | Partial | Repaired probes match qualitative shape; far-field below imported 0.99 target |
| §2.3 localized motion preserves embeddings | Partial | 1-4 px shifts hold; 8-14 px shifts weaker than imported (likely 4-bit quantization) |
| §2.4 scored real-video slice | Partial | 6/6 dense + cached on Qwen 3B endpoint suite; need broader natural-video coverage |
| §2.5 TOMATO 100% agreement on 1,484 items | NOT reproduced | Local 30-item dense=0.300, cached=0.233, agreement=0.833. Predecessor 100% partly explained by parser-default-to-A on both-wrong items (1,155/1,484 = 78%) |
| §2.6 MVBench 100% agreement on 160 items | NOT reproduced; weaker analog | Local 54-item dense=0.630, cached=0.648, agreement=0.870. Cached and dense statistically indistinguishable on this slice (McNemar p=1.0) |
| §3.3 14-frame drift tolerance | Partial | Refresh-every-4 recovers TOMATO direction on 5-item subset; broader sweep pending |
| §4 Q-table spatial correlation | Not attempted | Helpers exist but no local correlation note |
| §5 ~175× composed compression | NOT attempted | Track B not yet built; no skipped-compute evidence |

## What "There is a there there" looks like today

The strongest local-evidence finding is from phase 1.8:

> On TOMATO motion dev (15 items, 3 hard groups), `mean + max_age=4`
> achieves cached accuracy 0.400 at fresh-token-equivalent budget ~1247.
> Dense at 6 frames reaches the same 0.400 accuracy at 2400 fresh tokens.
> That is a real dev-side Pareto win at ~52% budget for the same accuracy.

But it does not survive holdout cleanly. On the disjoint 15-item
TOMATO motion holdout, cached stays flat at 0.200 while dense at 6 reaches
0.267. That is a confidence-limited regime (dense itself only 0.267) where
the Pareto comparison is uninterpretable.

## Where we are vs published SOTA

| Method | Compute reduction (claimed) | Quality drop (claimed) | Type |
|---|---|---|---|
| FastV (CVPR 2024) | 45% FLOP | <1% accuracy | training-free, token-prune |
| SparseVLM (ICLR 2025) | 75% token | <2% accuracy | training-free |
| ToMe (ICLR 2023) | ~50% token | <1% accuracy | spatial only, image |
| CoPE-VideoLM (Feb 2026) | 93% token | comparable | TRAINED 21k GPU-h |
| CodecSight (Apr 2026) | 87% GPU | comparable | trained |
| **Our method (this work)** | **0% measured** | **13-17% disagreement** | training-free |

We have a methodology-stack contribution and a content-conditioned
diagnostic finding, but we are not yet on the SOTA quality-vs-compute
chart. Track B (in-memory timing + measured vision-encode skip) is the
non-negotiable bridge to the SOTA conversation.

## Round-7 Tranche Output

Infrastructure landed:

- `model_content_sha256` for paper-grade feature cache provenance (v2 schema)
- `--log-option-logprobs` on the benchmark runner (per-letter logprob capture)
- `scripts/planner_grid_search.py` — replay-accelerated grid driver
  (calibrate + sweep, with `--max-policies` cap)
- `scripts/pareto_analysis.py` — Pareto-domination analyzer with
  effective-fresh-frames axis
- `scripts/inspect_artifact.py` — read-only artifact viewer

Experiments completed this tranche:

- Phase 1.9 MVBench motion dev frame-budget baselines (dense at 1/2/3/4/6/8,
  N=15, full Wilson CIs)
- Phase 1.9 MVBench motion holdout frame-budget baselines (in-progress at
  this snapshot; expected complete within minutes)
- All 4 planner calibrations (TOMATO motion dev/holdout + MVBench motion
  dev/holdout, 144 candidate policies each, binned by active reuse)

Experiments queued for the same tranche:

- Phase 1.10 TOMATO motion dev planner grid sweep (preregistered, awaits
  GPU availability after MVBench holdout completes)
- Phase 1.11 MVBench motion dev planner grid sweep
- Phase 1.12 Holdout evaluation of dev-selected Pareto winners
- Phase 1.13 logprob stratification (confidence-limited vs staleness-limited)

## Strategic Pivot Points

If Phase 1.10/1.11 grid sweeps surface a Pareto-dominating cached policy on
both TOMATO and MVBench motion dev:

→ Phase 1.12 holdout validation is the next gate. If it survives, we have
  the first method-paper-quality finding and Track B becomes the
  highest-leverage next investment.

If grid sweeps produce no Pareto-dominating policy on either dev slice:

→ Pivot to composition with FastV. Our temporal reuse is orthogonal to
  FastV's token pruning; multiplicative gain is plausible. ~1-2 weeks to
  integrate FastV into the Qwen 2.5-VL MLX path.

If Pareto wins on dev but holdout is flat at confidence-limited operating
point (the current phase 1.8 situation):

→ Larger frozen slices (45+ items per dev/holdout) to stabilize CIs and
  separate signal from sampling noise. ~1 week.

## Open Peer Review Asks

- Is "effective fresh frames" (1 + (N-1)*(1-active_reuse)) the right Track A
  proxy for compute budget? Or should we report tokens-through-vision-encoder
  more directly?
- Is per-bin=1 selection across (statistic × reuse_classes × max_age) bins
  the right space coverage, or should we densify around the reuse=0.7-0.85
  bin where most policies cluster?
- For the SOTA framing: does composition with FastV need real implementation,
  or can a "first-pass FLOP count multiplication" estimate suffice?

## Pointers

- [docs/execution-plan-round-7.md](execution-plan-round-7.md) — stage-by-stage roadmap
- [docs/reproduction-status.md](reproduction-status.md) — per-claim WP-* table
- [docs/claim-register.md](claim-register.md) — frozen reproduction targets
- [research/decision-log.md](../research/decision-log.md) — adopted/weakened/killed/pending ledger
- [paper/framing.md](../paper/framing.md) — current paper story scaffold
