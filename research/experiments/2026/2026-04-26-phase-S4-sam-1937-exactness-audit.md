# S4: Re-audit of the 1,937 sparse-exactness claim (Qwen 2.5-VL-7B)

- **Date:** 2026-04-26
- **Phase:** S4
- **Status:** **closed-partial** — 513/1,937 items have raw paired responses
  in their artifacts and reproduce 100% byte-identical with 0 parse failures.
  The remaining 1,644 items (TOMATO 1,484 + MVBench 160) have only
  correctness booleans logged; the byte-identical claim on those is
  *unverifiable from the artifacts alone* (loose-match holds 1,644/1,644).
- **Drift cases consistent with the S0/Gemma `PromptCacheState` bug shape:** **0**
  (all 513 paired pairs are full-string identical, no single-token-diff cases).

## 1. Inventory: where do the per-benchmark numbers come from?

| Benchmark   | Source artifact                                  | Items in artifact | Paired raw responses logged? | Parse-failure recoverable? | Item-IDs in artifact?              | Maps to whitepaper claim                   |
|-------------|--------------------------------------------------|-------------------|------------------------------|----------------------------|-------------------------------------|---------------------------------------------|
| TOMATO      | `experiments/tomato_7b_ALL_10.json`              | 60                | **yes** (`bl_response`, `ca_response`) | yes (`bl_parse_ok`, `ca_parse_ok`)      | no — only `split` + `gt`            | "60-item strict-parse sub-audit" (line 113) |
| TOMATO      | `experiments/tomato_7b_ALL_1000.json`            | **1,484**         | **no** — only `bl_correct`, `ca_correct`, `match` | **no** — `parse_ok` flags absent      | no                                  | "1,484 questions" (lines 99–113)            |
| MVBench     | `experiments/mvbench_7b_3.json`                  | 53                | **yes**                      | yes                        | no — only `split` + `gt`            | "53 strict-audit items" (line 744)          |
| MVBench     | `experiments/mvbench_7b_10.json`                 | 160               | **no**                       | **no**                     | no                                  | "160 items, 100% choice agreement" (line 744) |
| VideoMME    | `experiments/videomme_7b_n100_f32.json`          | 300               | **yes**                      | yes                        | yes — `question_id`                 | "VideoMME 300" (line 11)                    |
| EgoSchema   | `experiments/egoschema_7b_n100_f32.json`         | 100               | **yes**                      | yes                        | yes — `video_idx` + `question_idx`  | "EgoSchema 100" (line 11)                   |

**Notes on schema:**

- The "paired-with-raw" artifacts have schema:
  `[split, gt, bl_correct, ca_correct, match, strict_match, bl_parse_ok,
  ca_parse_ok, bl_response, ca_response, reuse]` (+ task/domain/question_id
  fields where applicable). These come from a later version of
  `experiments/run_tomato_mlx.py` (see lines 339–342, 605–611, 700–705 of
  that file).
- The "boolean-only" artifacts have schema: `[split, gt, bl_correct,
  ca_correct, match, reuse]`. These predate the strict-parse / raw-response
  schema upgrade. The `match` field is `bl_loose == ca_loose` where
  `_loose` is `extract_choice(..., strict=True)` defaulting to A on parse
  failure (i.e., the "default-to-A" loose parser reviewer Codex flagged
  earlier). So `match=True` does **not** imply byte-identical — it only
  implies "either both parsed to the same letter, or both fell back to A".
- **None of the artifacts preserve the prompt text**, so `prompt_hash` is
  empty in every JSONL row. Reproducing the prompt would require rerunning
  with the original loader (out of scope for an audit).
- The 1,484-row TOMATO artifact is named `_ALL_1000.json`. The "1000" is a
  misnomer — the file actually has 1,484 rows (the per-split caps in the
  loader sum to >1,000). This matches the paper's "1,484" claim numerically.

**Reconciliation of claimed totals:**

- Whitepaper claim (line 11): 1,937 = 1,484 (TOMATO) + 53 (MVBench) +
  300 (VideoMME) + 100 (EgoSchema). Confirmed numerically.
- Artifacts containing **paired raw responses** (i.e., the only set on
  which "byte-identical" is operationally checkable from logs alone):
  60 + 53 + 300 + 100 = **513 items**.
- Artifacts that contributed booleans only and feed the claimed 1,937
  total but cannot themselves verify byte-identity: **1,484 + 160 = 1,644**
  items. Note the boolean-only MVBench file has **160** items, which is
  larger than the 53 that the paper attributes to MVBench inside the
  1,937 — the 53 came from the *strict-paired* artifact, not the 160-item
  loose run.

## 2. Re-audit results

### 2.1 Per-benchmark paired-with-raw subset (n=513)

| Benchmark | n  | byte-identical | byte-identical % | parse-fail dense | parse-fail cached | Δacc (dense − cached) | 95% paired-bootstrap CI | drift cases |
|-----------|----|---------------:|-----------------:|-----------------:|------------------:|----------------------:|------------------------:|------------:|
| TOMATO    | 60 |             60 |          100.00% |                0 |                 0 |                  0.000 |            [0.000, 0.000] |           0 |
| MVBench   | 53 |             53 |          100.00% |                0 |                 0 |                  0.000 |            [0.000, 0.000] |           0 |
| VideoMME  |300 |            300 |          100.00% |                0 |                 0 |                  0.000 |            [0.000, 0.000] |           0 |
| EgoSchema |100 |            100 |          100.00% |                0 |                 0 |                  0.000 |            [0.000, 0.000] |           0 |
| **Total** |**513** |        **513** |      **100.00%** |            **0** |             **0** |              **0.000** |        **[0.000, 0.000]** |       **0** |

Bootstrap CIs are short-circuited to [0, 0] because every per-item
`accuracy_dense - accuracy_cached` is exactly 0 (a direct consequence of
byte-identical responses → identical parsed letters → identical correctness).
Bootstrap config when not short-circuited: 1,000 resamples, seed=42,
percentile method.

### 2.2 Per-benchmark boolean-only subset (n=1,644) — coverage gap

| Benchmark | n     | "byte-identical" | parse-fail | loose-match (bl_loose == ca_loose) | Δacc | 95% CI       |
|-----------|------:|-----------------:|-----------:|-----------------------------------:|-----:|--------------|
| TOMATO    | 1,484 | **unverifiable** | **unknown** | 1,484 / 1,484 (100%)              |  0.0 | [0.0, 0.0]   |
| MVBench   |   160 | **unverifiable** | **unknown** |   160 /   160 (100%)              |  0.0 | [0.0, 0.0]   |
| **Total** |**1,644** |        **n/a** |    **n/a** |             **1,644 / 1,644**     |  0.0 | [0.0, 0.0]   |

**Why "unverifiable":** byte-identicality requires comparing
`dense_response` to `cached_response`. The artifacts only persist the
correctness booleans (`bl_correct`, `ca_correct`) and a `match` flag
defined as `bl_loose == ca_loose` where `_loose` defaults to letter A on
parse failure. Two responses that both fail to parse a letter and silently
default to A would register `match=True` while being completely different
strings — a known loose-parser failure mode that has been raised by
external review on this codebase before. We cannot rule that mode out for
the 1,644 boolean-only items from the artifact alone.

**Why parse-failure status is unknown:** the older script version did not
log `bl_parse_ok` / `ca_parse_ok`. The summary script could in principle
have inferred parse-failure rate from the strict_match flag, but that
flag is also absent from the boolean-only artifacts.

### 2.3 Drift scan for the S0/Gemma `PromptCacheState` bug shape

The S0 audit (separate, on Gemma 4 26B-A4B) found that mlx-vlm 0.4.4's
`PromptCacheState` follow-up path silently corrupts a single token at a
content position in the cached follow-up response while leaving the rest
of the string intact. We scanned all 513 paired Qwen items for that
signature:

- Items where `byte_identical=False` but `first_diff_token_position` is
  small/well-defined: **0**.
- Items with any character difference at all: **0**.

The Qwen 7B audit shows no evidence of the Gemma-shape drift on this
single-turn cached-vs-dense path. (Note: the Gemma bug is in the
`PromptCacheState` *multi-turn* path, which the Qwen 1,937 runs do not
exercise — they are single-turn cached-embedding swaps. So the absence is
expected, but the explicit scan is now in the artifact.)

## 3. Reconciliation with the 1,937 claim

| Claim in whitepaper                                                 | Audit result |
|----------------------------------------------------------------------|--------------|
| "byte-identical VLM outputs on 1,937 benchmark items"               | **Verifiable on 513 items, 100%. Unverifiable on the remaining 1,424 TOMATO + 107 MVBench items inside the 1,937 (1,937 − 513 = 1,424; the additional 1,484 TOMATO − 60 paired = 1,424; MVBench 53 − 53 paired = 0). The 53 MVBench inside the 1,937 are fully verifiable; the 1,484 TOMATO have only loose-match logged.** |
| "100% strict agreement on all 1,937 items"                          | Verifiable on 513/513. The remaining 1,424 TOMATO items show 100% loose-match, which is necessary but not sufficient for strict agreement. |
| "zero parse failures" on all 1,937                                  | Verified on the 513 paired items (0/513). Unknown on 1,424 TOMATO boolean-only items (no parse_ok logged). |
| "zero accuracy delta" on all 1,937                                  | **Verified, 1,937/1,937.** This claim only requires the booleans, which are in every artifact. Bootstrap CI is exactly [0, 0]. |

**Bottom line:** the *accuracy-delta* part of the claim survives in full.
The *byte-identical* part is operationally verified on a 513-item subset;
the rest rests on a `match=True` loose-parser flag that the team itself
flagged as inadequate (the strict-parse audit was added precisely to fix
this), so the whitepaper text overstates what the artifacts can support.

## 4. Implications for `whitepaper.md`

Suggested corrections (line numbers from current `whitepaper.md`):

- **Line 9:** "produces byte-identical VLM outputs on 1,937 benchmark items"
  → either (a) reduce to "513 benchmark items with raw paired-response
  logging (TOMATO 60, MVBench 53, VideoMME 300, EgoSchema 100), with an
  additional 1,424-item TOMATO and 160-item MVBench loose-match audit",
  or (b) qualify with "100% loose-match on 1,937; byte-identical
  operationally verified on the 513-item subset with raw response logging
  (TOMATO 60 + MVBench 53 + VideoMME 300 + EgoSchema 100)".
- **Line 11:** "100% strict agreement across all 1,937 items (TOMATO 1,484,
  MVBench 53, VideoMME 300, EgoSchema 100), zero parse failures"
  → "100% strict agreement on 513 paired-response items (TOMATO 60,
  MVBench 53, VideoMME 300, EgoSchema 100), with 1,424 additional TOMATO
  items showing 100% loose-match. Zero parse failures on the 513-item
  paired subset; parse-failure status not recoverable from the
  loose-match-only artifacts."
- **Line 113:** This block already correctly distinguishes the 60-item
  strict sub-audit from the 1,484-item loose run, but the sentence "A
  60-item strict-parse sub-audit with raw response logging confirmed
  100% byte-identical agreement" is the only statement in the paper that
  is fully load-bearing. Strengthen: append a footnote that the
  remaining 1,424 TOMATO items in the full run lack raw-response
  logging, so byte-identicality on that subset is inferred from
  loose-match rather than directly verified.
- **Line 227:** "| Qwen2.5-VL-7B | MVBench | 53 | 100% | 100% | +0.0% |"
  is consistent with the 53-item paired run and is fine.
- **Line 669** (related-work table cell): "0.00% Δ on 1,837 sparse items"
  is a separate number (1,837) that drops the EgoSchema 100, and uses
  "1,484 + 53 + 300" — this is consistent with what is fully
  byte-identical-or-loose-match-verified at the time. No change needed
  unless line 9/11 are revised.
- **Line 744:** "MVBench was run on 53 strict-audit items (100%
  byte-identical) and 160 items (100% choice agreement)." This is
  already correctly hedged ("choice agreement" ≠ "byte-identical"), no
  change needed. This is the model the line 9/11 prose should adopt.
- **Line 756:** "100% byte-identical agreement on 413 Qwen items
  (TOMATO 60 + MVBench 53 + VideoMME 300)" — the audit confirms this
  413 plus the EgoSchema 100, for 513 total. Suggest update to "513
  Qwen items (TOMATO 60 + MVBench 53 + VideoMME 300 + EgoSchema 100)".
- **Line 766:** Same edit as line 9 / 11.

## 5. Artifact pointers

- Per-benchmark paired JSONL exports:
  - `/Users/sam/repos/codec-through/research/2026-04-26-s4-1937-exactness/tomato.jsonl` (1,544 rows: 60 paired + 1,484 boolean-only)
  - `/Users/sam/repos/codec-through/research/2026-04-26-s4-1937-exactness/mvbench.jsonl` (213 rows: 53 paired + 160 boolean-only)
  - `/Users/sam/repos/codec-through/research/2026-04-26-s4-1937-exactness/videomme.jsonl` (300 rows, all paired)
  - `/Users/sam/repos/codec-through/research/2026-04-26-s4-1937-exactness/egoschema.jsonl` (100 rows, all paired)
- Audit summary JSON (per-benchmark byte-id %, parse-fail counts, bootstrap CIs, drift list):
  `/Users/sam/repos/codec-through/research/2026-04-26-s4-1937-exactness/audit_summary.json`
- Re-export + bootstrap script:
  `/Users/sam/repos/codec-through/research/2026-04-26-s4-1937-exactness/export_and_bootstrap.py`
- This findings doc:
  `/Users/sam/repos/codec-through/research/2026-04-26-s4-1937-exactness-audit.md`

## 6. Re-run command

```bash
cd /Users/sam/repos/codec-through
python3 research/2026-04-26-s4-1937-exactness/export_and_bootstrap.py
```

Pure-stdlib (json, hashlib, random); no external deps. Deterministic
(seed=42 in the bootstrap, but every Δ is identically zero so the
bootstrap short-circuits).

## 7. What an authorized rerun would buy

To upgrade `closed-partial` → `closed-earned`, the 1,484-item TOMATO and
160-item MVBench runs need to be redone with the current
`run_tomato_mlx.py` schema (which logs `bl_response`, `ca_response`,
`bl_parse_ok`, `ca_parse_ok`, `strict_match`). Estimated runtime is
substantial (the existing 60-item strict TOMATO log shows ~6h45m on M5
Max for 60 items, so 1,484 items at the same per-item rate would be
~150–170 hours). A pragmatic alternative is to rerun a stratified
sample (e.g., 200 TOMATO items spread across the 6 splits) with the
current schema to bound the loose-vs-strict gap, rather than rerunning
the whole 1,484. **Not authorized in this audit.**
