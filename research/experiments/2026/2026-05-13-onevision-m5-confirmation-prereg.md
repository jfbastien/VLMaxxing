# 2026-05-13 — OneVision x VLMaxxing M3 Sidecar and M5 Confirmation Prereg

Status: preregistered, not yet run in this note.

Branch: `onevision-vlmaxxing-research`

## Context

OV-3 and OV-6 established bounded codec-score evidence on the M3:

- Track A: H.264 score sources beat pixel `max_abs` by point estimate on
  VideoMME-short / Qwen / 8f, with pooled-calibration robustness.
- Track B: Qwen `codec_novel_coded` is the best N=57 point estimate at
  kr=0.7/layer=2, but paired tests remain inconclusive and current live PyAV
  extraction erases net wall-clock savings.
- Gemma N=10 smoke gates the geometry path only; it is not yet a cross-family
  result.

This note separates the remaining M3 systems gate from M5 confirmation runs.

## M3 Sidecar Equivalence Gate

Question: can precomputed H.264 score sidecars replace live PyAV extraction
without changing Track B choices?

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

## M5 Qwen Parity / Timing Confirmation

Question: does the Qwen kr=0.7/layer=2 codec point-estimate ordering reproduce
on the M5 with sidecar-separated score runtime?

Hypothesis: M5 reproduces the M3 ordering at N=57: `codec_novel_coded` remains
at least as good as `magnitude_norm` by point estimate, with no material choice
or correctness drift caused by the sidecar path.

Command:

```bash
scripts/run_ov6_m5_qwen_parity.sh
```

Artifacts:

- `research/experiments/2026/artifacts/m5_ov6_qwen_n57_kr070_l2_parity/`

Success gate:

- `codec_novel_coded >= magnitude_norm` by point estimate;
- no parse-failure increase;
- sidecar load timing reported separately;
- paired tests and Wilson intervals emitted by `analyze_track_b_arm_set.py`.

Falsification:

- codec falls below magnitude by at least three items;
- sidecar provenance or shape validation fails;
- model-side timing gain disappears after excluding score runtime.

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

Success gate:

- `codec_novel_coded` or another simple codec source is `>= magnitude_norm` by
  point estimate;
- codec is not worse than `uniform_random` by three or more items;
- unmatched parse/format regressions are absent or explicitly bounded by
  `M5G_MAX_PARSE_FAILURES` (default 3/57).

Falsification:

- all codec sources fall below magnitude by at least three items;
- all codec sources fall below random by at least three items;
- Gemma geometry/provenance validation fails.

## M5 Qwen Frame-Budget Boundary

Question: does Track B codec ranking survive 16 frames, where Track A already
showed codec-to-pixel collapse?

Hypothesis: frame=16 is a boundary condition; codec may converge toward random
or magnitude and should not be presumed to transfer from the 8f result.

Command:

```bash
scripts/run_ov6_m5_qwen_frame16_boundary.sh
```

Artifacts:

- `research/experiments/2026/artifacts/m5_ov6_qwen_n57_16f_kr070_l2_boundary/`

Success gate for promotion:

- codec source `>= magnitude_norm` and `>= uniform_random` by point estimate;
- no material dense-correct breakage;
- memory and timing remain actionable.

Falsification:

- codec collapses to magnitude/random or breaks dense-correct rows without
  compensating fixes.

## OV-8 Composition Policy

OV-8 remains accounting-only unless one of two policies is explicitly chosen:

- find a first-query sparse cell with acceptable drift, then run live
  composition; or
- preregister an accuracy/speed tradeoff and report setup-inclusive curves with
  first-query drift caveats.

Current best Qwen sparse cell has material first-query drift, so it is not a
fidelity-clean C-PERSIST composition result.
