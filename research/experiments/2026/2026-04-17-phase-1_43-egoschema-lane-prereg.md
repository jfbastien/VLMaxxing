# Phase 1.43 — EgoSchema breadth lane (long-form egocentric)

Date: 2026-04-17
State: blocked (preregistered; loader + manifest build not started)
Parent: `paper/claim-matrix.md` claim #12 (long-form/egocentric generalization — new claim to be added; NOT claim #8, which is specifically VideoMME)
Sibling: `research/experiments/2026/2026-04-16-phase-1_41-videomme-lane.md` (claim #8 VideoMME lane — the *specific* benchmark named in claim #8)

## Motivation

TOMATO and MVBench are paper-grade at N=30 but both are short-
form, motion-centric, and third-person. Claim #8 asserts that the
Planner 2.0 family generalizes across video benchmark distributions.
EgoSchema adds a distinct axis — long-form (3-minute clips) and
egocentric (first-person head-mounted camera) — that neither
current benchmark covers. A pass on EgoSchema is evidence that
reuse decisions driven by pixel-diff statistics are not specific
to the third-person short-clip regime; a failure characterizes
the claim boundary.

EgoSchema is prioritized above other breadth candidates
(NExT-QA, MoVQA) because:

- It is the most adversarial frame-budget benchmark available:
  3-minute clips sub-sampled to 8 frames mean each frame covers
  ~22.5 s of action, so reuse fidelity is stressed by large
  per-frame semantic deltas.
- The public Huggingface `lmms-lab/EgoSchema` split exposes 500
  QA items with MP4 URLs — directly loadable without the TOS
  click-through friction that blocks VideoMME.
- Egocentric motion patterns (head-turn, hand approach, ego-motion
  parallax) differ substantially from third-person scene-edit motion;
  this is where the "MAX_ABS outlier-sensitivity" inductive bias
  could break if the claim is ego-specific.

## Hypothesis

H1 (Planner 2.0 transfer): `max_abs(8,32) static+shifted age=4`
achieves ≥ 50 % of dense-8 cached accuracy at
effective_fresh_frames ≤ 5.5 on EgoSchema holdout N=30. Target:
cached_accuracy within 0.10 of dense-8. Stricter target would
require a head-turn-aware statistic (future work).

H2 (benchmark-conditioned): Agreement ≥ 0.80 on EgoSchema (below
MVBench's 0.93-0.95 but above a catastrophic-divergence threshold).
Reason: 22.5-s inter-frame gaps mean more content genuinely
changes, so strict cached-vs-dense agreement should be lower than
on TOMATO/MVBench. We are measuring whether the routing policy
still produces *coherent* decisions, not byte-identity.

H3 (matched dense): Planner 2.0 ties or Pareto-wins vs matched
dense-N at the same `effective_fresh_frames` on EgoSchema. This
is the same Pareto-survival test applied to TOMATO/MVBench.

## Method

**Runs on Qwen 2.5-VL-7B-Instruct-4bit** (same model as phases
1.12.B / 1.20 / 1.21 / 1.26.B — independent of phase 1.42 Gemma
integration). This is a cross-benchmark breadth test for the
Qwen-branch policy (Planner 2.0 MAX_ABS static+shifted age=4);
the Gemma-branch EgoSchema transfer is a separate future phase.

**Phase A — loader** (infra, not yet written):

1. Add `load_egoschema_items` to the benchmark loader stack,
   matching the `load_videomme_items` / `load_mvbench_items`
   interface in `scripts/run_benchmark_track_a.py`.
2. Build motion-stratified dev/holdout manifests (v1) at N=30 each
   using the Huggingface `lmms-lab/EgoSchema` subset. Stratify by
   head-motion intensity if metadata permits; otherwise stratify
   uniformly.
3. Verify video fetch: EgoSchema MP4s are ~80 MB each; 60 clips
   (dev + holdout) = ~5 GB. Fetch via the existing
   `scripts/build_*_manifest.py` pattern.

**Phase B — transfer test** (paper-grade, N=30 holdout, single-shot):

1. `max_abs(8,32) static+shifted age=4` vs dense-8 on EgoSchema
   motion holdout N=30. No dev selection — transfer-discovered
   policy as-is, same framing as phase 1.12.B and 1.42.
2. Metrics: cached_accuracy, dense_accuracy, strict agreement,
   effective_fresh_frames, per-pair reuse class histogram.

**Phase C — matched dense** (if Phase B passes):

1. Dense-N curve at N ∈ {4, 6, 8} for Pareto baseline.
2. Track B dense wall-clock on 10 items to confirm long-form
   speed (per-item time could be 3-5× TOMATO's 61 s given the
   longer clip decode).

## Accept / reject gates (preregistered)

- **Accept benchmark transfer:** cached_accuracy ≥ dense-8 − 0.10
  AND agreement ≥ 0.80 AND Pareto tie-or-win vs matched dense-N.
- **Reject benchmark transfer:** cached_accuracy < dense-8 − 0.20
  OR agreement < 0.65. Either indicates the policy is short-clip-
  conditioned, and the paper's cross-benchmark claim narrows to
  "short-form motion benchmarks."

## Status

- 2026-04-17: preregistered. Loader NOT STARTED.
- Does NOT depend on phase 1.42 (Gemma). This is a Qwen-branch
  breadth lane — the same Qwen 2.5-VL model that powers phases
  1.12.B / 1.20 / 1.21 / 1.26.B runs here. The EgoSchema loader
  follows the `load_mvbench_items` / `load_videomme_items` pattern
  in `scripts/run_benchmark_track_a.py` and is independent of the
  `_mix_gemma_features` work in phase 1.42. Codex round-16
  (2026-04-17) flagged the earlier "blocked on 1.42" framing as
  incorrect — it was an accidental dependency inherited during
  authoring.

## Why this phase

Two paper-grade benchmarks is defensible but thin. Three paper-
grade benchmarks spanning short-form third-person (TOMATO),
short-form third-person with broader task coverage (MVBench), and
long-form egocentric (EgoSchema) is a much stronger cross-
distribution story. This phase is the cheapest path to that third
benchmark given EgoSchema's open licensing.

## Runtime estimate

| Stage | Duration estimate |
|---|---|
| Phase A loader + manifest build | infra (excluded per protocol) |
| Phase A video fetch (~5 GB over HF) | ~15 min |
| Phase B N=30 single-shot cached + dense | ~45 min (assumes ~45 s/item, slower than TOMATO due to longer clips) |
| Phase C dense-N matched curve | ~30 min |
| Track B wall-clock spot-check | ~20 min |
| **Total** | **~2 hr of GPU time** |

## Artifacts (expected)

- `data/benchmarks/egoschema/manifests/egoschema_motion_dev_v1.toml`
- `data/benchmarks/egoschema/manifests/egoschema_motion_holdout_v1.toml`
- `research/experiments/2026/artifacts/phase1_43_egoschema_motion_holdout_v2_cached/*.json`
- `research/experiments/2026/artifacts/phase1_43_egoschema_motion_holdout_v2_dense/*.json`
- `results/track_b/egoschema_mc_spot.json`
