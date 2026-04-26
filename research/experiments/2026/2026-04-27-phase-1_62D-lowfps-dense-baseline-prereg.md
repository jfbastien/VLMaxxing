---
date: 2026-04-27
phase: 1.62D
status: preregistered; not yet run
related:
  - research/experiments/2026/2026-04-26-deployment-baseline-plan.md
  - research/experiments/2026/2026-04-27-adaptive-mechanism-queue-findings.md
---

# Phase 1.62D — Low-FPS Dense VideoMME Baseline

## Question

Can the simplest deployment baseline, dense inference on fewer uniformly
sampled frames, match the 8f session-protocol reference closely enough that
the paper must caveat C-VISION / session-efficiency claims as "low-FPS dense is
also competitive"?

This is the first deployment-baseline check because it is scientifically clean:
no online timestamp assumptions, no cache policy, no recency heuristic, and no
new model code. It directly tests the reviewer objection "why not just use
fewer frames?"

## Protocol

- Model: `Qwen2.5-VL-7B-Instruct-4bit`.
- Corpus: VideoMME dev+holdout session union used by 1.30W
  (`videomme_dev_v1.toml` + `videomme_holdout_v1.toml`), deduplicated to 57
  sessions / 171 queries by the 1.30 harness.
- Reference: existing 8f cold-dense arm from
  `phase1_30W_q0_dense_followup_pruned_full/cold_dense.jsonl`.
- Candidates:
  - 4f cold dense, all queries
  - 2f cold dense, all queries
- Pairing: exact `(seed_item_id, q_index)` pairing against the 8f reference.
- Statistics:
  - candidate-minus-reference accuracy delta
  - paired session-bootstrap CI preserving duplicate queries per session
  - speedup from total 8f cold wall time over total candidate cold wall time
  - first-query, follow-up, and duration slices

## Gates

This experiment is diagnostic rather than winner-take-all.

- **H_lowfps_competitive**: 4f delta ≥ -0.05 with clean parsing. The low-FPS
  baseline is competitive and paper claims must explicitly state that dense
  low-FPS is a viable simple baseline on this slice.
- **H_lowfps_rejected**: 4f delta ≤ -0.10 with clean parsing. The low-FPS
  baseline is rejected as a replacement for the 8f reference under the same
  session protocol.
- **H_lowfps_ambiguous**: otherwise. Treat as unresolved; use the CI and
  duration slices instead of a binary claim.
- 2f is secondary. It maps the lower boundary and should not override the 4f
  interpretation unless 4f is competitive and 2f also survives.

## Interpretation

Positive or negative outcomes are both useful:

- If 4f is competitive, the current paper should be honest that some VideoMME
  utility comes from lower temporal sampling rather than the proposed reuse
  mechanism alone.
- If 4f is rejected, the paper gets a clean defense against the cheapest
  deployment-baseline objection.
- If only short clips survive, the deployment story should become
  duration-conditioned.

This phase intentionally does not test "low-FPS + C-PERSIST" in the same run.
That is a follow-up only if 4f dense is competitive. The current question is
the simpler reviewer objection: whether dense low-FPS alone replaces the 8f
reference on the same session protocol.

## Runtime

Expected wall time on the 16 GB M3 laptop:

- 4f full session union: ~2-3 h
- 2f full session union: ~1.5-2.5 h
- analysis: <1 min

Peak RSS should remain below the 9 GB guard because both arms are dense cold
Qwen 7B-4bit at fewer frames than the already-landed 8f reference.
