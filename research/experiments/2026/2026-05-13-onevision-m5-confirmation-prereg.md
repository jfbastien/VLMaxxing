# 2026-05-13 — OneVision x VLMaxxing M3 Sidecar and M5 Confirmation Prereg

Status: M3 gates run; M5 confirmations not yet run in this note.

Branch: `onevision-vlmaxxing-research`

## Revisions

- 2026-05-26: the original M5 Qwen parity, Gemma N=57 confirmation, and
  frame-16 boundary gates treated the single seed-42 `uniform_random` arm as a
  success criterion or promotion floor. That criterion is superseded before the
  M5 confirmations run. Seed 42 is now a required sanity comparator only; no
  positive codec-over-random paper claim can rest on a single random seed. Any
  positive codec-over-random manuscript sentence requires the clean four-seed
  kr=0.7 random-control protocol described in
  `plan/codec-metadata-paper-edit.md`, preregistered before any Qwen
  VideoMME-short N=57/8f/layer-2/kr=0.7 `uniform_random` arm is launched or
  inspected outside that committed four-seed protocol. In this note, the
  queued `scripts/run_ov6_m5_qwen_parity.sh` seed-42 arm is a known closure
  event if it is launched or inspected before the four-seed protocol is
  committed. The script now hard-fails unless `M5Q_CLEAN_CONTROL_PREREG`
  points to a clean-control preregistration file tracked in `HEAD`, clean in
  the worktree and index, and matching
  `research/experiments/2026/*qwen*kr070*random*control*prereg.md`. The
  committed preregistration must be a blob that names the clean-control
  artifact root, the comparator paths
  `m5_ov6_qwen_n57_kr070_l2_random_control/dense/`,
  `m5_ov6_qwen_n57_kr070_l2_random_control/magnitude_norm/`, and
  `m5_ov6_qwen_n57_kr070_l2_random_control/codec_novel_coded/`, the four
  random-control seed paths listed below, and
  `codec_vs_random_multiseed_audit.json`; the committed, clean experiment
  registry must also name that preregistration path,
  `scripts/run_ov6_m5_qwen_kr070_random_control.sh`, and the clean-control
  comparator and random arm paths. The launcher also refuses the clean path if
  the parity output root already contains a seed-42 `uniform_random` artifact.
  Otherwise the operator must explicitly set
  `OV6_ALLOW_CLOSE_RANDOM_CONTROL_WINDOW=1` and point
  `OV6_CLOSURE_RECORD` at a committed closure note, clean in the worktree and
  index, named in the experiment registry, and matching
  `research/experiments/2026/*qwen*kr070*random*control*closure*.md`.

  Required clean-control arm paths for both the preregistration note and the
  registry entry:

  - `m5_ov6_qwen_n57_kr070_l2_random_control/dense/`
  - `m5_ov6_qwen_n57_kr070_l2_random_control/magnitude_norm/`
  - `m5_ov6_qwen_n57_kr070_l2_random_control/codec_novel_coded/`
  - `m5_ov6_qwen_n57_kr070_l2_random_control/uniform_random_seed1/`
  - `m5_ov6_qwen_n57_kr070_l2_random_control/uniform_random_seed7/`
  - `m5_ov6_qwen_n57_kr070_l2_random_control/uniform_random_seed42/`
  - `m5_ov6_qwen_n57_kr070_l2_random_control/uniform_random_seed100/`

  The clean four-seed protocol is now preregistered in
  `research/experiments/2026/2026-05-26-qwen-kr070-random-control-prereg.md`
  and must be launched through the dedicated wrapper, not through ad-hoc
  `run_phase1_51V.py` calls:

  ```bash
  M5Q_CLEAN_CONTROL_PREREG=research/experiments/2026/2026-05-26-qwen-kr070-random-control-prereg.md scripts/run_ov6_m5_qwen_kr070_random_control.sh
  ```

## Context

OV-3 and OV-6 established bounded codec-score evidence on the M3:

- Refresh planning: H.264 score sources are answer-preserving at the tested
  low-reuse point, but they do not demonstrate a codec-over-pixel advantage:
  the pooled N=57 result is dirty-tree/advisory/pending-clean-rerun evidence,
  in-sample/pixel-budget-matched, and only +2/57 over pixel, while the disjoint
  per-item holdout ties pixel exactly.
- Sparse vision pruning: Qwen `codec_novel_coded` is the best N=57 point
  estimate at kr=0.7/layer=2 versus `magnitude_norm`, but paired tests remain
  inconclusive, the current M3 artifact lacks a kr=0.7 random-keep control, and
  current live PyAV extraction erases net wall-clock savings.
- Gemma N=10 smoke gates the geometry path only; it is not yet a cross-family
  result.

This note separates the remaining M3 systems gate from M5 confirmation runs.

## M3 Sidecar Equivalence Gate

Question: can precomputed H.264 score sidecars replace live PyAV extraction
without changing sparse-pruning choices?

Hypothesis: sidecar-loaded score grids preserve live-PyAV codec-grid behavior
while reducing per-item score runtime from ~19 s extraction to NPZ-load scale.

Commands:

```bash
scripts/run_ov6_sidecar_equivalence.sh
OV6S_FRAME_COUNT=16 scripts/run_ov6_sidecar_equivalence.sh
scripts/run_ov6_gemma_sidecar_equivalence.sh
```

Artifacts:

- `research/experiments/2026/artifacts/phase1_51V_ov6_sidecar_equivalence/`
- `research/experiments/2026/artifacts/phase1_51V_ov6_sidecar_equivalence_f16/`
- `research/experiments/2026/artifacts/phase1_63G_ov6_gemma_sidecar_equivalence/`

Success gate:

- zero choice drift between live and sidecar arms for every tested source;
- zero correctness drift;
- zero kept-count and kept-groups-per-frame drift;
- `codec_score_runtime_source` is `live_pyav` for live arms and `sidecar` for
  sidecar arms;
- sidecar load time is less than 1 s/item and lower than live extraction.
- sidecars validate against the current manifest item IDs, current git commit,
  current score-projection version, score-grid hash, and geometry details.

Falsification:

- any drift between live and sidecar arms;
- stale or dirty sidecar provenance;
- manifest item mismatch or current-commit/projection-version mismatch;
- sidecar load time >= 1 s/item.

Interpretation:

- PASS per geometry/frame budget: the corresponding future M5 run may use
  sidecars by default and report model-side timing separately from sidecar
  build/load timing.
- FAIL: do not use sidecars for claim-bearing M5 runs; debug geometry, config
  hashing, and active-box projection before more GPU time.

## M3 TOMATO Keep-Rate Boundary Smoke

Question: did the TOMATO motion sparse-pruning collapse come from an overly aggressive
keep rate, or from frame/content/model headroom at 8 frames?

Hypothesis: if prune rate is the main boundary, a milder `kr=0.9` setting on a
balanced N=9 TOMATO motion slice should lift at least one sparse arm toward
dense. If dense remains weak or all sparse arms stay near the prior sparse
floor, TOMATO remains a boundary diagnostic rather than an M5 target.

Command:

```bash
scripts/run_ov6_tomato_kr090_boundary_smoke.sh
```

Artifacts:

- `research/experiments/2026/artifacts/phase1_51V_ov6_tomato_motion_kr090_l2_balanced_smoke/`

Success gate for follow-up:

- best sparse arm is within one item of dense on the balanced N=9 slice;
- best sparse arm exceeds the previous sparse-floor band (`> 0.22` on N=9).

Falsification:

- dense is still weak on the balanced slice; or
- all sparse arms remain at or below the prior sparse-floor band.

Interpretation:

- PASS: TOMATO motion has a keep-rate-sensitive sparse window worth a focused
  follow-up.
- FAIL: do not spend M5 time on TOMATO in this branch; keep it as a bounded
  negative/boundary result.

## M5 Qwen Parity / Timing Confirmation

The M5 sidecar-backed scripts validate the M3 gate artifacts with
`--allow-historical-commit`: sidecars generated at a clean ancestor commit are
acceptable, while dirty sidecars and non-ancestor commits still hard-fail. This
keeps the committed M3 gates reusable after later analysis commits without
weakening provenance.

Question: does the Qwen kr=0.7/layer=2 codec point-estimate ordering reproduce
on the M5 with sidecar-separated score runtime?

Hypothesis: M5 reproduces the M3 ordering at N=57: `codec_novel_coded` remains
at least as good as `magnitude_norm` by point estimate, with no material choice
or correctness drift caused by the sidecar path.

Command:

Replace the path below with the committed, repo-relative preregistration note
you add for the clean four-seed control; do not copy it before that file
exists and the registry names it.

```bash
M5Q_CLEAN_CONTROL_PREREG=research/experiments/2026/2026-05-26-qwen-kr070-random-control-prereg.md scripts/run_ov6_m5_qwen_parity.sh
```

If the clean four-seed random-control window has intentionally been closed,
record that decision first, then launch with the explicit closure override:

```bash
OV6_ALLOW_CLOSE_RANDOM_CONTROL_WINDOW=1 OV6_CLOSURE_RECORD=research/experiments/2026/2026-05-26-qwen-kr070-random-control-closure.md scripts/run_ov6_m5_qwen_parity.sh
```

Artifacts:

- `research/experiments/2026/artifacts/m5_ov6_qwen_n57_kr070_l2_parity/`
- `research/experiments/2026/artifacts/m5_ov6_qwen_n57_kr070_l2_parity/track_b_arm_set_audit.json`

Success gate:

- `codec_novel_coded >= magnitude_norm` by point estimate;
- a PASS here means hardware-stable parity against the weak
  `magnitude_norm` comparator only. It is not a sparse-ranking success over
  random, and it cannot be promoted as codec-over-random even if
  `codec_novel_coded` beats the seed-42 random row;
- `codec_motion` and `codec_residual` are secondary source-consistency rows,
  not the primary gate;
- the seed-42 `uniform_random` row is a required sanity comparator, not a
  success gate for any codec-over-random paper claim. A favorable seed-42 row
  is still single-seed evidence only; it cannot support even a preliminary
  positive codec-over-random sentence. Any positive codec-over-random claim
  requires a separate clean four-seed kr=0.7 preregistration before any Qwen
  VideoMME-short N=57/8f/layer-2/kr=0.7 `uniform_random` arm is launched or
  inspected outside that committed four-seed protocol. If
  `codec_novel_coded` trails the seed-42 random row, classify that under the
  Boundary warning rules below rather than changing the magnitude-parity gate;
- no parse-failure increase;
- sidecar load timing reported separately;
- paired tests and Wilson intervals emitted by `analyze_track_b_arm_set.py`.

Falsification:

- `codec_novel_coded` falls below magnitude by at least three items;
- sidecar provenance or shape validation fails;
- model-side timing gain disappears after excluding score runtime.

Boundary warning:

- If `codec_novel_coded` trails magnitude by one or two items, report this as
  hardware-parity weakening, not success and not falsification.
- If `codec_novel_coded` clears the primary gate but `codec_motion` or
  `codec_residual` trails magnitude by at least three items, report
  source-heterogeneity boundary evidence. Secondary-source failures do not
  falsify the primary Qwen parity gate.
- If `codec_novel_coded` falls below the seed-42 random sanity row by at least
  three items, report this as a boundary warning, not as falsification or as a
  codec-over-random statistical result. If secondary codec sources show the
  same pattern, report that as source-consistency evidence for the boundary.
  The random row is single-seed.

## M5 Gemma kr=0.5 Random-vs-Magnitude Confirmation

Question: does the Qwen `uniform_random > magnitude_norm` inversion at
kr=0.5/layer=2 transfer to Gemma's SigLIP-family vision tower?

Hypothesis: on Gemma E4B, at least 3/4 random seeds satisfy
`uniform_random >= magnitude_norm` by point estimate on N=57 VideoMME-short.

Command:

```bash
scripts/run_ov6_m5_gemma_kr05_inversion.sh
```

Artifacts:

- `research/experiments/2026/artifacts/m5_ov6_gemma_n57_kr050_l2_random_multiseed/`
- `research/experiments/2026/artifacts/m5_ov6_gemma_n57_kr050_l2_random_multiseed/random_multiseed_summary.json`

This run uses the multiseed analyzer; its summary artifact is
`random_multiseed_summary.json`, not `track_b_arm_set_audit.json`.

Success gate:

- at least 3/4 seeds satisfy `uniform_random >= magnitude_norm` by point
  estimate;
- no seed has `magnitude_norm` ahead by three or more items.

Falsification:

- at most 1/4 seeds satisfy the point-estimate gate; or
- any seed has `magnitude_norm` ahead by three or more items.

Interpretation:

- PASS: the magnitude-prior failure is not Qwen-only at this operating point.
- FAIL: keep the magnitude-prior failure claim scoped to Qwen kr=0.5/layer=2.

## M5 Gemma N=57 Cross-Family Confirmation

Question: was the Gemma N=10 codec-grid smoke only a wiring check, or does the
codec ranking signal transfer across vision-tower family?

Hypothesis: on Gemma E4B at kr=0.7/layer=2, at least one simple codec source is
competitive with `magnitude_norm` on N=57 VideoMME-short.

Command:

```bash
scripts/run_ov6_m5_gemma_n57_confirmation.sh
```

Artifacts:

- `research/experiments/2026/artifacts/m5_ov6_gemma_n57_kr070_l2_confirmation/`
- `research/experiments/2026/artifacts/m5_ov6_gemma_n57_kr070_l2_confirmation/track_b_arm_set_audit.json`

Success gate:

- `codec_novel_coded` or another simple codec source is `>= magnitude_norm` by
  point estimate;
- the seed-42 `uniform_random` row is a required sanity comparator, not a
  success gate for any codec-over-random paper claim. A single seed cannot
  support even a preliminary positive codec-over-random sentence; if a codec
  source is worse than seed-42 random by three or more items, report that as a
  boundary warning;
- unmatched parse/format regressions are absent or explicitly bounded by
  `M5G_MAX_PARSE_FAILURES` (default 3/57).

Falsification:

- all codec sources fall below magnitude by at least three items;
- Gemma geometry/provenance validation fails.

Boundary warning:

- If all codec sources trail magnitude by one or two items, report this as a
  cross-family boundary, not success and not falsification. Mixed outcomes
  where some codec sources are competitive with magnitude and others are not
  should be reported per source.
- If all codec sources fall below the seed-42 random sanity row by at least
  three items, report a strong boundary warning. Mixed results where only some
  codec sources fall below seed-42 random by at least three items are weaker
  boundary warnings. Neither case is falsification, because the random row is a
  single-seed comparator.

## M5 Qwen Frame-Budget Boundary

Question: does sparse-pruning codec ranking survive 16 frames, where the
refresh-planning probe already showed codec-to-pixel collapse?

Hypothesis: frame=16 is a boundary condition; codec may converge toward random
or magnitude and should not be presumed to transfer from the 8f result.

Command:

```bash
scripts/run_ov6_m5_qwen_frame16_boundary.sh
```

Artifacts:

- `research/experiments/2026/artifacts/m5_ov6_qwen_n57_16f_kr070_l2_boundary/`
- `research/experiments/2026/artifacts/m5_ov6_qwen_n57_16f_kr070_l2_boundary/track_b_arm_set_audit.json`

Success gate for promotion:

- at least one simple codec source is `>= magnitude_norm` by point estimate;
- the seed-42 `uniform_random` row is a required boundary comparator, not a
  success gate for any codec-over-random paper claim. A single seed cannot
  support even a preliminary positive codec-over-random sentence;
- no material dense-correct breakage;
- memory and timing remain actionable.

Falsification:

- all codec sources fall below magnitude_norm by at least three items; or
- all codec sources break dense-correct rows without compensating fixes.

Mixed source outcomes where only some codec sources fall below `magnitude_norm`
by at least three items, or only some codec sources break dense-correct rows,
are boundary/inconclusive evidence, not falsification.

Boundary warning:

- If all codec sources fall below the seed-42 random sanity row by at least
  three items, report a strong frame-budget boundary warning. Mixed results
  where only some codec sources fall below seed-42 random by at least three
  items are weaker boundary warnings. Do not report either case as
  falsification or as a codec-over-random statistical result, because the
  random row is a single-seed comparator.

## OV-8 Composition Policy

OV-8 remains accounting-only unless one of two policies is explicitly chosen:

- find a first-query sparse cell with acceptable drift, then run live
  composition; or
- preregister an accuracy/speed tradeoff and report setup-inclusive curves with
  first-query drift caveats.

Current best Qwen sparse cell has material first-query drift, so it is not a
fidelity-clean C-PERSIST composition result.

## Execution Update: M3 Follow-up Chain

Run status: completed on M3 16GB MacBook Air with MLX unified GPU.

Command:

```bash
bash scripts/run_m3_followup_chain.sh
```

Artifacts:

- `research/experiments/2026/artifacts/phase1_51V_ov6_sidecar_equivalence/`
- `research/experiments/2026/artifacts/phase1_51V_ov6_sidecar_equivalence_f16/`
- `research/experiments/2026/artifacts/phase1_63G_ov6_gemma_sidecar_equivalence/`
- `research/experiments/2026/artifacts/phase1_51V_ov6_tomato_motion_kr090_l2_balanced_smoke/`

Sidecar gates:

- Qwen 8f: PASS, zero choice/correctness/kept-count drift across
  `novel_coded`, `motion`, and `residual`. Live PyAV extraction was
  16.81-19.54 s/item; sidecar load was 0.00097-0.00174 s/item.
- Qwen 16f: PASS, zero drift across all three sources. Live extraction was
  20.15-23.78 s/item; sidecar load was 0.00202-0.00294 s/item.
- Gemma 8f: PASS, zero drift across all three sources. Live extraction was
  17.15-18.75 s/item; sidecar load was 0.00199-0.00451 s/item.

Interpretation: the 3-item gates are engineering equivalence gates, not
accuracy claims. They validate the sidecar contract and unblock sidecar-backed
M5 confirmation runs.

TOMATO kr=0.9 balanced N=9:

- Dense: 3/9 correct.
- `magnitude_norm`: 3/9 correct.
- `codec_novel_coded`: 3/9 correct, 8/9 choice agreement with `magnitude_norm`.
- `codec_motion`: 2/9 correct.
- `codec_residual`: 1/9 correct.

Interpretation: `codec_novel_coded` and `magnitude_norm` match the weak dense
baseline at mild pruning, so kr=0.9 avoids the harsher kr~0.69 collapse on this
small slice. But dense itself is weak, Wilson intervals are wide, and this does
not justify a TOMATO M5 promotion in this branch.
