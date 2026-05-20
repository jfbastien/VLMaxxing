# VLMaxxing + RLT Closeout Readiness Audit

Status: M3 paper-closeout audit plus optional M5 scale-confirmation runbook.
Audience: experiment driver, paper editor, and skeptical reviewer.

This note replaces the stale fifth-pass closeout prereg. Several proposed
"missing" experiments were already closed by later artifacts, or were
mis-scoped across Qwen magnitude C-VISION and Gemma RLT C-VISION. The purpose
of this file is therefore not to launch a new M3 queue by default. It records
what is already closed, what remains optional, and exactly which dormant
query-aware infrastructure must not be mixed into the VLMaxxing + RLT paper.

The query-aware visual-routing substrate landed in commit `86033d5`
(`feat(query-routing): add Q0b and Q1 experiment queue`) remains deferred to a
separate paper. Do not pass `--run-query-routing-q0b` or
`--run-query-routing-q1` during VLMaxxing + RLT closeout.

2026-05-20 update: the later cross-benchmark admission-only cost-accounting
run is now recorded in
`research/experiments/2026/2026-05-20-vlmaxxing-rlt-cost-accounting-closeout.md`
with source artifact
`research/experiments/2026/artifacts/rlt_m3_cost_accounting_followup/cost_model_fit_n19.json`.
It strengthens C-CEILING/stage-cost accounting and helps explain why
admission-only rows move E2E when prefill owns enough of the bill. It does
**not** turn admission-only query routing into a VLMaxxing+RLT closeout
headline. For this branch, admission-only rows are cost-accounting controls;
full-composition and C-VISION rows remain the RLT/VLMaxxing evidence.

## Validated Closeout State

### C-VISION holdout replication is already closed

The older note
`research/experiments/2026/2026-04-21-phase-1_51V-holdout-findings.md` says the
V-only VideoMME holdout pair was unmeasured. That statement was superseded the
same day by session 3.

Closed evidence:

- `research/experiments/2026/2026-04-21-phase-1_51V-session3-findings.md`
- `research/experiments/2026/artifacts/phase1_51V_session3/exp17_videomme_holdout_8f_unpatched.jsonl`
- `research/experiments/2026/artifacts/phase1_51V_session3/exp18_videomme_holdout_8f_L2_kr050.jsonl`
- `paper/claim-matrix.md`, claim 15

Result: VideoMME 8f V-only holdout is clean: E2E `1.113x`, `V_red=0.413`,
decode drift `1.53%`, accuracy delta `0.000`. MVBench and TOMATO holdout
V-only rows are also closed, with advisory thermal footnotes already recorded
in the claim matrix.

Decision: do not rerun the old V-only holdout pair as a closeout blocker. If
the paper editor wants a current-commit reproduction, run it as a reproduction
cell and label it as such; do not claim it was previously missing.

### Random-keep robustness is already a Qwen magnitude control, not RLT

The completed multi-seed random baseline is for Qwen 2.5-VL-7B 1.51V
`magnitude_norm` C-VISION versus `uniform_random` at matched `kr=0.5`. It is
not an RLT-as-C-VISION random-control experiment.

Closed evidence:

- `scripts/run_phase1_51VC_random_keep_multiseed.sh`
- `research/experiments/2026/artifacts/phase1_51VC_random_keep_baseline/`
- `paper/arxiv/generated/data/competitor_positioning_snapshot.json`
- `research/experiments/registry.md`

Result: structured `magnitude_norm` accuracy is `0.500`; four-seed
`uniform_random` mean accuracy is `0.358` (`min=0.333`, `max=0.367`) on the
same VideoMME dev n=30 Qwen setup. The structured-minus-random gap is
`14.2pp`.

Decision: keep this as a Qwen C-VISION sanity baseline. Do not describe it as
RLT evidence. A true RLT random-control row is optional and belongs either in a
reviewer-response appendix or in the query-aware paper's Q1 controls.

### C-PERSIST dense-anchored stress is already closed with a mixed result

Closed evidence:

- `scripts/run_phase1_55M_dense_anchored_cpersist.sh`
- `research/experiments/2026/2026-05-02-phase-1_55M-dense-anchored-cpersist-findings.md`
- `research/experiments/2026/artifacts/phase1_55M_dense_anchored_cpersist/summary.json`

Result at horizon 20, Qwen 7B, 20 frames, dense-answer-anchored prompt
variation:

| Policy | Follow-up drift | Gate |
|---|---:|---|
| `fixed_k1` | `0/133 = 0.00%` | pass |
| `adaptive_post_q2` | `6/133 = 4.51%` | fail 3% gate |
| `refresh10` | `6/133 = 4.51%` | fail 3% gate |

The aggressive policies still deliver roughly `113x-115x` follow-up speedups
against cold dense, but with a measured 4.51pp paired-drift cost. The
conservative `fixed_k1` policy is the quality-clean dense-anchored headline.

Decision: do not rerun this cell expecting a pass for `adaptive_post_q2`.
Paper framing should say C-PERSIST has a measured content-conditional drift
boundary, not that all aggressive policies survive realistic dialogue stress.

### RLT full-composition holdout and pooled analyses are already closed

Closed evidence:

- `research/experiments/2026/artifacts/rlt_followup_queue/full_composition_rlt_combined_*_analysis.json`
- `research/experiments/2026/artifacts/rlt_followup_queue/full_composition_rlt_rescue_combined_*_analysis.json`
- `research/experiments/2026/2026-05-08-rlt-followup-next-prereg.md`

Pooled n=60 direct composition, no rescue:

| Benchmark | E2E | Accuracy delta | Verdict |
|---|---:|---:|---|
| VideoMME | `1.029x` | `-0.067` | CI crosses zero; weak speed |
| TOMATO | `1.233x` | `-0.067` | CI crosses zero; speed clear |
| MVBench | `1.842x` | `-0.117` | speed frontier, fidelity fails |

Pooled n=60 rescue policy:

| Benchmark | E2E | Accuracy delta | Verdict |
|---|---:|---:|---|
| VideoMME | `1.078x` | `-0.050` | quality CI crosses zero |
| TOMATO | `1.237x` | `-0.083` | borderline; low absolute accuracy |
| MVBench | `1.433x` | `-0.050` | paper-clean aggregate; bucket caveats |

Decision: paper-facing RLT composition headline should use the rescue policy
for MVBench (`1.43x`) and reserve the `1.84x` direct row for the speed frontier
with a clear quality-regression caveat. Do not quote the round-18 n=30
`1.90x` number as the final headline after holdout replication.

### MVBench moving_attribute remains a hypothesis generator, not a settled law

Closed evidence:

- Dev bracket:
  `research/experiments/2026/artifacts/rlt_followup_queue/full_composition_rlt_mvbench_moving_attribute_kr100_analysis.json`
- Holdout rescue:
  `research/experiments/2026/artifacts/rlt_followup_queue/full_composition_rlt_rescue_holdout_mvbench_analysis.json`

Facts:

- Dev `moving_attribute` remains poor at `kr=1.0`: dense `0.833`,
  composed `0.333`, delta `-0.50` on n=6.
- Holdout `moving_attribute` is clean under the rescue policy at `kr=0.85`:
  dense `0.500`, composed `0.500`, delta `0.00` on n=6.
- Pooled rescue still shows `moving_attribute` delta `-0.25` on n=12.
- The optional holdout bracket has now been run:
  `research/experiments/2026/artifacts/rlt_followup_queue/full_composition_rlt_holdout_mvbench_moving_attribute_kr100_analysis.json`.
  It lands aggregate E2E `1.438x` with accuracy delta `0.000`, and its
  `moving_attribute` row is favorable: dense `0.500`, composed `0.667`,
  delta `+0.167` on n=6. The preregistered falsifier (`delta < -0.30`) was not
  hit. The bucket gate failure is instead `action_localization`, where one item
  flips at the default `kr=0.5`.

Decision: the right statement is that the dev `moving_attribute` failure did
not replicate on this disjoint holdout slice. Because the decisive subgroup is
only n=6, do not overclaim "not structural" as a settled population fact. This
remains a strong seed for query-aware visual routing, but it should not become
a deterministic claim inside the VLMaxxing + RLT paper.

## Optional M3 Work

No mandatory M3 experiments remain for the VLMaxxing + RLT closeout. The
holdout version of the MVBench moving_attribute bracket was the only optional
cell, and it has now run. The executable path remains available for
reproduction:

```bash
.venv/bin/python scripts/run_rlt_followup_queue.py \
  --run-cvision-rlt \
  --run-moving-attribute-holdout-bracket
```

Result: falsifier not hit; holdout `moving_attribute` delta `+0.167`.
Scientific status: appendix-level boundary probe, not a powered bucket-level
claim.

2026-05-20 addendum: a bounded reviewer-response M3 cost-accounting follow-up
is preregistered and executed separately at
`research/experiments/2026/2026-05-20-rlt-m3-cost-accounting-followup-prereg.md`.
The executed extended tier accepts the `n=19` stage-cost model (`R²=0.97097`,
MARE `1.72%`) and shows VideoMME-short `kr=0.3/0.7` are parsed-choice clean.
Treat it as cost-model/Pareto evidence, not as query-aware routing or a new
VLMaxxing/RLT headline.

## M5 Scope

M5 is scale confirmation, not discovery. Use the same Gemma-family paper target
Sam has been using: prior M5 artifacts identify it as
`google/gemma-4-26B-A4B-it` on an M5 Max with 128 GB unified memory. Do not
hard-code a user-specific path; require `GEMMA_MODEL_PATH` from the operator
environment and run the n=1 smoke before any n=30 cell.

M5 should stay scoped to C-VISION scorer transfer and C-CEILING scale behavior.
After the M3 `n=19` cost-model follow-up, the default M5 wrapper is core-only:
n=1 smoke plus VideoMME n=30 RLT C-VISION. Optional scorer or full expansion
tiers require explicit `M5_CONFIRMATION_TIER=scorer` or
`M5_CONFIRMATION_TIER=full`. The wrapper intentionally excludes direct
composition, rescue, admission-only, query-routing, and moving-attribute
bracket cells. If an M5 composition or admission-control run is needed later,
add a separate preregistered wrapper with explicit flags rather than widening
this closeout launcher.

Recommended M5 command shape:

```bash
export GEMMA_MODEL_PATH=/path/to/sams/gemma-4-26b-a4b-it-mlx-model
scripts/run_rlt_m5_scale_confirmation.sh
```

Optional tiers:

```bash
M5_CONFIRMATION_TIER=scorer scripts/run_rlt_m5_scale_confirmation.sh
M5_CONFIRMATION_TIER=full scripts/run_rlt_m5_scale_confirmation.sh
```

M5 hypotheses:

1. **Scorer-cost scaling.** RLT raw-frame scoring remains cheap while max-min
   diversity grows with vision feature dimension. Expected result: RLT remains
   at tens of milliseconds; max-min grows toward multi-second or larger cost;
   scorer-cost ratio widens versus 4B.
2. **C-CEILING cross-scale validation.** The dense-arm `V_share` at 26B should
   be lower than at E4B because decode grows faster than the vision tower. The
   same scatter-back ceiling should predict observed E2E within the preregistered
   tolerance once measured on that session.

M5 should not run query-routing Q0b/Q1, moving-attribute bracket, or holdout
replication. Those are either paper #2 work or already covered on M3.

Acceptance gate update from the M3 follow-up: use `<= 8%` absolute relative
error against the stage-cost ceiling as the M5 scale-confirmation band. The
current M3 table's max error is `7.85%`; a tighter row can still be labeled
"green," but `>8%` is the preregistered falsifier for the scale check.

## Paper Narrative Recommendation

The paper is strongest if it presents C-CEILING as a co-primary methodology
contribution rather than a background detail. The two mechanism contributions
are:

1. **C-VISION:** real vision-tower work skipped with scatter-back, with RLT as
   a cheap redundancy scorer and measured keep-rate / scorer-cost controls.
2. **C-PERSIST:** persistent KV reuse for same-video follow-up regimes, with
   explicit drift envelopes.

C-CEILING is the ruler that makes both mechanism claims credible, and that
ruler is itself a contribution because the VLM-efficiency literature often
reports component savings without the denominator discipline needed to predict
user-facing speed. It explains why VideoMME, TOMATO, and MVBench have different
E2E gains, why direct composition does not multiply cleanly, and why holdout
replication should be pooled rather than cherry-picked.

Recommended editor-facing wording:

> The final RLT composition result is not the original 2x speed-frontier point.
> The defensible headline is `1.08x / 1.24x / 1.43x` on
> VideoMME / TOMATO / MVBench at n=60 with disjoint holdout replication and no
> statistically decisive aggregate accuracy regression. The `1.84x` MVBench
> direct row is the speed frontier and carries a quality-regression caveat. The
> scientific win is that the cheap raw-patch redundancy scorer gets most of the
> benefit, exposes where pruning fails, and keeps the measurement honest through
> C-CEILING.

## Query-Aware Fork Notes

The query-aware paper should reuse the lessons above but not inherit the
headline numbers. In particular:

- Treat MVBench `moving_attribute` as a motivation for typed evidence
  operators, not as a solved or universal failure.
- Reuse Qwen random-keep artifacts only as a historical baseline; Q1 must
  produce its own fixed/random controls under the query-aware operator ledger.
- Reuse C-CEILING features for H5a cost-model training, but keep query-aware
  conclusions tied to query-aware artifacts.
