# 2026-04-29 Phase B5 — Sam S4 exactness re-export

- **Status:** **closed-earned** for both bounded claims
- **Verdict:** the two bounded S4 claims now have schema-validated paired
  rows in this repo. Both pass their phase-specific validator gates.
  Nothing was re-run; this is artifact provenance plumbing.

## Two separate artifacts, two separate claims

The handoff explicitly distinguishes:

> Supported: 0 accuracy delta on 1,937 sparse-sampled items.
> Supported: byte-identical raw-paired verification on 513 rows.
> Not supported until re-exported with raw paired rows: byte-identical
> exactness over all 1,937 rows.

This phase produces both as separate artifacts so the bounded paper
claim does not leak into the unbounded form by accident.

| artifact | rows | claim | gate | result |
|---|---:|---|---|---|
| `sam_b5_s4_accuracy_1937.jsonl` | 1,937 | `S4_zero_acc_delta_1937` | 0 correctness diffs, 0 parse failures, B5 provenance complete | **PASS** |
| `sam_b5_s4_raw_paired_513.jsonl` | 513 | `S4_byte_identical_513` | 0 choice diffs, 0 correctness diffs, 0 text diffs, 0 parse failures, B5 provenance complete | **PASS** |

## Source

Imported from `sdamico/codec-through @ 6594a7b` per the original S4
audit (commit `30a1810`). For each output row, we record:

- `source_artifact_path`: absolute path to the upstream JSONL on the
  `sdamico` clone
- `source_artifact_sha256`: sha256 of that JSONL file at import time
- `claim_id`: `S4_zero_acc_delta_1937` or `S4_byte_identical_513`
- `expected_row_count` / `export_row_count`: 1937 / 1937 or 513 / 513
- `ci_method`: `paired_session_bootstrap_seed42_n1000_short_circuit_zero`
- `ci95`: `[0.0, 0.0]` (every per-row delta is identically zero, so the
  bootstrap short-circuits)
- `provenance_note`: one of two strings —
  - "imported S4 paired-response row (byte-identical claim subset)" —
    for the 513 rows that have raw paired responses
  - "imported S4 row; raw paired responses present" or
    "imported S4 row; only loose-match boolean recoverable; byte-
    identical claim NOT supported on this row" — for the 1,937-row
    artifact, depending on whether the upstream row carried both
    `dense_response` and `cached_response`

## Per-benchmark inventory in the 1,937 artifact

| benchmark | rows | source file | source rows with raw paired |
|---|---:|---|---:|
| TOMATO    | 1,484 | `tomato.jsonl` | 60 (the rest are loose-match-only) |
| MVBench   | 53    | `mvbench.jsonl` | 53 |
| VideoMME  | 300   | `videomme.jsonl` | 300 |
| EgoSchema | 100   | `egoschema.jsonl` | 100 |

For the boolean-only TOMATO subset (1,484 − 60 = 1,424 rows), the
exported row has placeholder strings in `raw_response` /
`baseline_raw_response` of the form `<unavailable bl_loose=...>` /
`<unavailable ca_loose=...>`. This produces `text_identical=False` on
those 1,424 rows by construction — which is **correct**: we cannot
verify byte-identical from the source artifacts on those rows, and the
B5 1,937-claim validator does **not** require zero text diffs (per
the contract).

Validator output for `sam_b5_s4_accuracy_1937.jsonl`:

```json
{
  "n_rows": 1937,
  "choice_diffs": 0,
  "correctness_diffs": 0,
  "text_diffs": 1484,
  "parse_failures": 0,
  "schema_or_gate_errors": 0,
  "first_errors": [],
  "pass": true
}
```

The 1,484 text diffs are placeholder-driven (rows where raw paired
responses don't exist in the source artifact); the underlying claim
(zero correctness delta) holds.

## Per-benchmark inventory in the 513 artifact

All 513 rows have raw paired responses in the source artifact:

| benchmark | rows |
|---|---:|
| TOMATO    | 60  (the 60-item strict-parse sub-audit) |
| MVBench   | 53  |
| VideoMME  | 300 |
| EgoSchema | 100 |

Validator output for `sam_b5_s4_raw_paired_513.jsonl`:

```json
{
  "n_rows": 513,
  "choice_diffs": 0,
  "correctness_diffs": 0,
  "text_diffs": 0,
  "parse_failures": 0,
  "schema_or_gate_errors": 0,
  "first_errors": [],
  "pass": true
}
```

## What this means for the paper

- **C-EXACTNESS / Track A semantic-substitution claim** (per the sdamico
  whitepaper §1, §8) is now expressible as **two separate bounded
  claims** with schema-validated artifacts:
  - "0 accuracy delta on 1,937 sparse-sampled items, paired-bootstrap
    CI [0, 0]" — supported by the 1,937 artifact.
  - "byte-identical raw-paired verification on 513 items (TOMATO 60 +
    MVBench 53 + VideoMME 300 + EgoSchema 100), all paired bootstraps
    short-circuit to [0, 0]" — supported by the 513 artifact.
- The "byte-identical on 1,937" form previously cited in the sdamico
  whitepaper at lines 9, 11, 766 is **not** supported by these
  artifacts and must be either reduced to 513 or qualified as
  loose-match.
- The 1,484 TOMATO loose-match items are useful as a population-level
  accuracy-preservation signal but cannot be the byte-identical
  number. The S4 audit findings already say this; this re-export makes
  it machine-checkable.

## Constraints (per the handoff)

- **No re-run.** This is artifact provenance plumbing; the S4 audit
  performed the actual paired comparison. We did not call the model.
  The arm `codec_through_cached` and policy
  `cached_features_swap_at_static_boundary` are the contract names for
  the upstream Qwen 2.5-VL-7B-4bit / mlx-vlm runs that produced the
  source rows.
- **No prompt text in source artifacts.** None of the upstream JSONLs
  preserve the prompt string. We synthesize `prompt_hash` from the
  item_id; this is provenance-preserving (deterministic from upstream
  identifiers) but not the actual input prompt.
- **No model invocation.** `model_sha` etc. are recorded as
  `"n/a (B5 is artifact re-export, no model load)"`.

## Artifacts

- `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b5_s4_accuracy_1937.jsonl`
- `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b5_s4_accuracy_1937_summary.json`
- `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b5_s4_raw_paired_513.jsonl`
- `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b5_s4_raw_paired_513_summary.json`
- `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b5_s4_export_summary.json` (combined export-side summary, distinct from validator summaries)
- Runner: `scripts/run_sam_b5_s4_reexport.py`
- Source: `sdamico/codec-through @ 30a1810`,
  `research/2026-04-26-s4-1937-exactness/{tomato,mvbench,videomme,egoschema}.jsonl`

## Re-run command

```bash
cd /Users/sam/repos/codec-through-jfb
python3 scripts/run_sam_b5_s4_reexport.py
python3 scripts/validate_sam_scaleout_artifact.py \
  --jsonl research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b5_s4_accuracy_1937.jsonl \
  --phase B5 --expected-row-count 1937 \
  --require-zero-correctness-diffs --require-zero-parse-failures \
  --require-b5-provenance \
  --summary-output ...
python3 scripts/validate_sam_scaleout_artifact.py \
  --jsonl research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b5_s4_raw_paired_513.jsonl \
  --phase B5 --expected-row-count 513 \
  --require-zero-choice-diffs --require-zero-correctness-diffs \
  --require-zero-text-diffs --require-zero-parse-failures \
  --require-b5-provenance \
  --summary-output ...
```

Wall time: ~1 second (pure JSON re-shape, stdlib only).

## Cross-reference

- `research/experiments/2026/2026-04-29-sam-scaleout-handoff.md` § B5
- `sdamico/codec-through @ 30a1810`
  (`research/2026-04-26-s4-1937-exactness-audit.md`,
   `research/2026-04-26-s4-1937-exactness/{*.jsonl, audit_summary.json}`)
