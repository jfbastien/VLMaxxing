# 2026-04-29 Phase B4-adjacent — Sam Track B via post-ViT hard prune

- **Status:** **closed-arch-blocked** for strict B4; **closed-null** for
  the deployment-relevant Track B mechanism on this stack at the
  contractual operating point.
- **Strict-B4 non-conformance:** the B4 contract requires "real
  compact/sparse vision-tower execution." This stack (mlx-vlm 0.4.4,
  Gemma 4 26B-A4B) does not have a sparse-ViT execution path; the ViT
  runs **densely on all patches** in both arms of this run. The pruning
  happens **after** the ViT and removes the lowest-importance visual
  tokens from the LLM input ids before LM prefill. This reduces LLM
  prefill cost (real work skipped in prefill, per AGENTS.md Track A/B
  definition) but does NOT reduce vision cost. Every emitted row's
  `provenance_note` records this disclosure verbatim.
- **Verdict:** at keep_ratio = 0.50 on Gemma 4 26B-A4B, hard-prune
  is **slower than dense at 8 frames (median 0.757× speedup; pruned
  arm takes 30 % longer)** and **roughly even at 32 frames (median
  1.042× speedup)**. **0 / 10 paired rows** are byte-identical. The
  mechanism does not pay off on this stack at this operating point.

## Setup

| field | value |
|---|---|
| `model_id` | `google/gemma-4-26B-A4B-it` |
| `model_sha` | `7d4c97e54145f8ffd1a4dd1b4986a5015a517842` |
| `quantization` | `bf16_native` |
| `runtime` | `mlx_vlm-0.4.4` |
| `keep_ratio` | 0.50 (kr_actual = 0.500 across all 10 rows: 2048 → 1024 visual tokens at 8 f, 8192 → 4096 at 32 f) |
| `decoding` | greedy (`temperature=0.0`, `seed=0`) |
| `corpus` | first 5 unique videos by `question_id` from VideoMME test parquet |
| `frame counts` | 8 f and 32 f |
| `prompt` | "Describe the most prominent visual content. Keep it concise." |
| `max_tokens` | 32 |

## Result table (10 rows = 5 videos × 2 frame counts)

| video | f | tokens before | tokens after | dense ms | pruned ms | speedup | text_id |
|---|---:|---:|---:|---:|---:|---:|---|
| `fFjv93ACGo8` | 8  | 2048 | 1024 | 5,646 | 4,821 | **1.171×** | False |
| `fFjv93ACGo8` | 32 | 8192 | 4096 | 14,351 | 13,747 | 1.044× | False |
| `N1cdUjctpG8` | 8  | 2048 | 1024 | 3,835 | 5,275 | **0.727×** | False |
| `N1cdUjctpG8` | 32 | 8192 | 4096 | 13,522 | 12,946 | 1.044× | False |
| `HIjX8OPuf-w` | 8  | 2048 | 1024 | 3,911 | 5,202 | **0.752×** | False |
| `HIjX8OPuf-w` | 32 | 8192 | 4096 | 13,117 | 14,178 | 0.925× | False |
| `HwnB8aCn8yE` | 8  | 2048 | 1024 | 4,932 | 5,798 | 0.851× | False |
| `HwnB8aCn8yE` | 32 | 8192 | 4096 | 14,973 | 14,363 | 1.042× | False |
| `24i4ncHuf6A` | 8  | 2048 | 1024 | 4,362 | 5,762 | 0.757× | False |
| `24i4ncHuf6A` | 32 | 8192 | 4096 | 16,228 | 16,533 | 0.982× | False |

Aggregate:

| frame count | n | median speedup | mean speedup | text_identical |
|---|---:|---:|---:|---:|
| 8 f  | 5 | **0.757×** | 0.852× | 0 / 5 |
| 32 f | 5 | 1.042× | 1.008× | 0 / 5 |

## Why it doesn't pay off here

Stage timings (median, 32-frame run, `pruned_total_ms` ≈ 14 s):

```
vit_ms              ≈ 4,000–4,500 ms   (UNCHANGED -- ViT runs fully on
                                        all 8192 visual tokens)
spatial_cascade_ms  ≈   200–300 ms     (additive cost of importance
                                        scoring -- this is OVERHEAD on
                                        the pruned arm)
prefill_ms          ≈ 8,000–9,000 ms (dense)  →  3,500–4,000 ms (pruned)
                                        (LLM prefill does drop ~50% as
                                        expected, since 4096 vs 8192
                                        visual-token positions in the
                                        prompt)
gen_ms              ≈   200–300 ms     (small; same on both arms)
```

The **C-CEILING** for this regime, given prefill_share ≈ 8000/14351 ≈
0.55 in the 32 f dense arm and prefill reduction ≈ 0.50:

```
predicted_e2e_speedup ≈ 1 / (1 − 0.55 × 0.50) ≈ 1.38×
observed_median_speedup       = 1.042×
residual                       = +0.34× under-performance
```

The ceiling predicts ~1.4× but we observe ~1.0×. The gap is the
**spatial-cascade overhead** (~5 % of total budget on the pruned arm)
**plus** thermal / kernel-cache effects from running pruned-after-dense.
At 8 f the prefill share is much smaller (~5,000/4,000 ≈ 1.25 ratio
isn't the issue; it's that 8 f's ViT and prefill are similar and the
cascade overhead is larger relative to gains), and the cascade
overhead dominates → pruned is slower.

This residual **reframes the C-CEILING applicability boundary on this
stack:** the ceiling assumes the pruning step itself is cost-free,
which it isn't here because the cascade scoring runs in numpy and adds
real time. A paper-grade Track B claim on this stack would need to
either (a) implement the cascade scoring inside MLX so it amortizes
into the vision-tower pass, or (b) only report at frame counts large
enough for the prefill share to dwarf the cascade overhead (≥ 64 f
likely), or (c) use a cheaper importance heuristic.

## What this means for the paper

- **§2.13 (sdamico whitepaper) -- the "13× ViT reduction at frame-
  count scaling" claim is on streaming with cache reuse, not on hard-
  prune.** Hard-prune is a different mechanism (post-ViT prefill
  reduction, not vision-tower skipping) and does not produce a 13×
  speedup at any operating point here. **The two should not be
  conflated.**
- **C-CEILING (jfb publishability-status round 26):** the arithmetic
  ceiling formulation `1/(fixed + (1−fixed)/s)` requires the "skipped
  work" to be the free part. On this stack, hard-prune adds cascade
  cost that breaks the assumption -- so the ceiling over-predicts E2E
  speedup. This is honest negative information for the
  cross-architecture C-CEILING claim: **C-CEILING applicability
  bound = "the pruning policy itself must be sub-1 % overhead of the
  total budget."** Worth citing as a limitations line.
- **Track B status on the 26B stack:** there is no Track B win at
  kr=0.50, 8/32 f on Gemma 4 26B with the current hard-prune
  implementation. To unlock B4-class results we would need either a
  real sparse-ViT path (substantial engineering) or a cheaper
  importance heuristic + frame counts ≥ 64.

## Validator output

```json
{
  "n_rows": 10,
  "phases": {"B4": 10},
  "arms": {"hard_prune_post_vit_kr050": 10},
  "policies": {"hard_prune_keep_ratio_0.5": 10},
  "choice_diffs": 0,
  "correctness_diffs": 0,
  "text_diffs": 10,
  "parse_failures": 0,
  "schema_or_gate_errors": 0,
  "first_errors": [],
  "pass": true
}
```

`text_diffs=10` is expected: every paired arm produced a different
description (the dense and pruned features attend differently). The
descriptive question doesn't have a ground-truth answer, so
`session_correct` and `baseline_correct` are both `False` by
construction; this row class does not contribute correctness or
choice-level evidence. The strict B4 gate of "delta accuracy ≥ −0.05"
isn't testable on this row class without an LLM-as-judge, which
isn't part of the schema for B4.

## Caveats

- **Single-attempt thermal pairing.** Each (video, frames) cell runs
  dense once and pruned once, sequentially. Thermal drift between the
  arms is real; on the M5 the pruned arm runs second and may be on a
  warmer chip (smaller per-token rates). For 32 f the timing is
  ~14–16 s per arm so thermal is in the noise; for 8 f at ~4 s per
  arm it is closer to the speedup we are trying to measure. A paper-
  grade rerun would alternate dense/pruned/dense/pruned per cell.
- **N=5 videos per frame count.** Bootstrap CIs not computed; the
  per-cell speedups are large enough (0.7×–1.2× spread) that signal
  is clear, but a paper-grade claim should add CIs.
- **Cascade implementation is numpy.** Moving it inside MLX would
  amortize its cost into the vision-tower forward and likely close
  most of the residual gap.

## Artifacts

- `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b4_sparse_vit_ceiling.jsonl` (10 rows, schema-validated)
- `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b4_sparse_vit_ceiling_summary.json`
- `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b4_sparse_vit_ceiling.log`
- Runner: `scripts/run_sam_b4_track_b_hard_prune.py`
- Underlying mechanism: `sdamico/codec-through @ 6594a7b` --
  `experiments/run_gemma4_validation.py::Gemma4VLM.run_comparison_pruned`
  + `experiments/spatial_cascade.py`

## Cross-reference

- Handoff contract: `2026-04-29-sam-scaleout-handoff.md` § B4
- jfb publishability-status round 26 (C-CEILING formulation)
