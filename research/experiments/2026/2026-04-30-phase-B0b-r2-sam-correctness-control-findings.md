---
date: 2026-04-30
phase: B0b r2
status: closed-correctness-control / open-speedup-boundary
related:
  - 2026-04-29-phase-B0b-sam-cache-correctness-findings.md (r1 -- the failed gate)
  - 2026-04-30-sam-r2-handoff.md (operator doc)
  - 2026-04-30-sam-integration-and-next-experiments.md (companion narrative)
---

# 2026-04-30 Phase B0b r2 — Cache-correctness gate PASS under correctness-control guard

- **Status:** **closed-correctness-control / open-speedup-boundary.**
- **Verdict:** with the r2 correctness-control guard installed
  (disable cross-turn cache reuse whenever any `RotatingKVCache` is
  present in the prompt cache; force full re-prefill instead),
  **B0b's cache-correctness gate PASSES at full scale on Gemma 4
  26B-A4B / mlx-vlm 0.4.4: 42/42 text-identical, 0 choice diffs,
  0 correctness diffs.** The PASS is achieved by **disabling**
  cross-turn cache reuse, not by repairing it.
- **Important framing:** this is a **correctness control, not a
  C-PERSIST speedup result.** The cross-turn arm of this run took
  the cold-dense path; cache reuse was refused by the guard. The
  speedup question on Gemma 4 26B mixed-SWA topology remains an
  **open architecture boundary** until a topology-aware upstream
  patch lands in mlx-vlm (and possibly mlx-lm cache.py to handle
  per-layer trimmability via `is_trimmable()`).

## Setup

| field | value |
|---|---|
| `model_id` | `google/gemma-4-26B-A4B-it` |
| `model_sha` | `7d4c97e54145f8ffd1a4dd1b4986a5015a517842` |
| `quantization` | `bf16_native` |
| `runtime` | `mlx_vlm-0.4.4` (with monkey-patched `stream_generate` per the guard) |
| `decoding` | greedy (`temperature=0.0`, `seed=0`) |
| `corpus` | first 7 unique videos by `question_id` from VideoMME test parquet (same as r1) |
| `frames` | 8 deterministic timestamps |
| `max_tokens` | 32 |

## What the guard does

`scripts/run_sam_b0b_cache_correctness.py` now installs a top-of-module
monkey-patch on `mlx_vlm.generate.stream_generate` that, before the
broken trim block fires, checks the passed `prompt_cache_state.cache`
for any `mlx_lm.models.cache.RotatingKVCache` instance. If present,
the guard drops the `prompt_cache_state` from kwargs and lets mlx-vlm
take the cold-dense path. A sticky module-level flag
`B0B_GUARD_TRIGGERED` records whether the guard fired during the most
recent call; the runner reads this after each cross-turn
`stream_generate` and emits guard-aware row metadata.

Why a "correctness control" and not a "speedup-preserving fix":

- The original draft of this step proposed clearing only the
  `RotatingKVCache` entries while leaving full-attention `KVCache`
  entries cache-reused. That is broken: with a partial cache state,
  mlx-vlm still trims `input_ids = input_ids[:, prefix_len:]`, so SWA
  layers receive only the suffix tokens against an empty cache and
  miss the prefix's attention context entirely. Per-layer prompt
  state would be inconsistent and outputs would diverge for a
  different reason than the bug being diagnosed.
- The clean fix is to refuse cross-turn cache reuse entirely on
  mixed-SWA topologies and accept the cold-dense cost. This proves
  the bug is in the cache-reuse path; B0b's correctness gate can
  pass under this control.

## Result table

42 rows (7 videos × 3 questions × {within_turn_cache_replay,
cross_turn_warm}). Cross-turn rows all carry the guard-fired
metadata.

| metric | within_turn_cache_replay (n=21) | cross_turn_warm (n=21, guard fired) | overall (n=42) |
|---|---:|---:|---:|
| text_identical | 21/21 (100%) | **21/21 (100%)** | **42/42 (100%)** |
| choice_diffs | 0 | 0 | 0 |
| correctness_diffs | 0 | 0 | 0 |
| parse_failures | 2 (matched, on q1_mc) | 2 (matched, on q1_mc) | 4 |
| input_hash_mismatches vs baseline | 0 | 0 | 0 |
| prompt_hash_mismatches | 0 | 0 | 0 |
| frame_hash_mismatches | 0 | 0 | 0 |

The 4 parse failures are matched (same on cross/within and on
cold_dense baseline) — Gemma 4's tendency to produce free-text
preamble before the multiple-choice letter on q1_mc. They are NOT
guard-induced; the same 4 q1_mc rows had matched parse failures in
the r1 run on the broken cache path.

Per-row policy metadata:

- All 21 `within_turn_cache_replay` rows: `policy = "prompt_cache_state_within_turn"`,
  `policy_params = null`. Within-turn replay never tripped the
  guard (the cache is fresh-built within the turn; there is no
  cross-turn prefix to trim, so the buggy code path is never
  reached).
- All 21 `cross_turn_warm` rows: `policy = "full_refill_guard_rotating_kv"`,
  `policy_params = {cache_guard_triggered: True, guard_reason:
  "rotating_kv_present", cache_reuse_disabled: True}`,
  `provenance_note` prefixed with
  `"[B0b r2 guard fired: cross-turn cache reuse disabled because
  RotatingKVCache present in prompt cache; effective path is full
  re-prefill] "`,
  `vit_calls = 1`, `prefix_hit = 0`, `prefix_coverage = 0.0`.

## Validator output

```json
{
  "n_rows": 42,
  "phases": {"B0b": 42},
  "arms": {"within_turn_cache_replay": 21, "cross_turn_warm": 21},
  "policies": {
    "prompt_cache_state_within_turn": 21,
    "full_refill_guard_rotating_kv": 21
  },
  "choice_diffs": 0,
  "correctness_diffs": 0,
  "text_diffs": 0,
  "parse_failures": 4,
  "input_hash_mismatches": 0,
  "prompt_hash_mismatches": 0,
  "frame_hash_mismatches": 0,
  "schema_or_gate_errors": 0,
  "first_errors": [],
  "pass": true
}
```

Validator flags used (per the r2 handoff guidance):

```bash
--require-zero-choice-diffs
--require-zero-correctness-diffs
--require-zero-text-diffs
--require-matching-input-hash
--require-matching-prompt-hash
--require-matching-frame-hashes
--require-b0b-protocol
```

**`--require-positive-prefix-on-followups` was deliberately NOT
passed.** That gate WILL fail by design on guarded rows, because
`prefix_hit=0 / prefix_coverage=0.0` is the correct semantic value
for cross-turn rows where cache reuse was refused. The bundle
README must record this exemption when guarded B0b rows are
imported into the bundle validator.

## Comparison vs r1 (the failed gate)

| metric | r1 (broken cache path) | r2 (guarded full-refill path) |
|---|---:|---:|
| n_rows | 42 | 42 |
| within_turn text-identical | 21/21 | 21/21 |
| **cross_turn_warm text-identical** | **5/21 (24%)** | **21/21 (100%)** |
| **cross_turn_warm choice diffs** | **2/21** | **0/21** |
| cross_turn_warm correctness diffs | 0/21 | 0/21 |
| **gate PASS** | **FAIL** | **PASS (under correctness control)** |
| **C-PERSIST speedup on Gemma 26B** | broken (10× speedup but 76% wrong text) | **disabled (no speedup; gate-clean)** |

## What this means for the paper

- **Cache-correctness gate is now closed under the explicit caveat
  "cross-turn cache reuse disabled on Gemma 26B mixed-SWA topology
  via correctness-control guard."** This is what unblocks downstream
  paper claims that need a passing B0b: correctness-preserving
  derivative claims can quote this gate as cleared.
- **C-PERSIST speedup on Gemma 26B mixed-SWA: BLOCKED.** The cross-
  arch C-PERSIST evidence in the paper today is M5-5b's prefix-
  snapshot result (9.11× per-turn / 26.59× at 32f, distinct from
  Qwen 7B's 47×–150× full-attention regime) — that mechanism
  AVOIDS the broken trim by never persisting question-specific
  tokens into the cache, so it does not require this guard. B0b r2
  documents the boundary: default `PromptCacheState` cross-turn
  reuse is unsafe; the prefix-snapshot is the supported alternative
  on this stack.
- **Future work (NOT in r2):** topology-aware upstream patch that
  replaces the inline slice at `mlx_vlm/generate.py:687-697` with a
  per-cache-class trim respecting `is_trimmable()`. For
  `RotatingKVCache.is_trimmable() == False`, the model.forward path
  needs a way to re-prefill that single layer's prefix while still
  reusing other layers' caches. Real upstream contribution; tracked
  separately.

## Caveats

- **Diagnostic correctness control, not a speedup mechanism.** Do
  not cite the r2 PASS as a C-PERSIST speedup result. The cross-turn
  arm in this run paid the full cold-dense prefill cost.
- **Validator flag warning:** the bundle validator at
  `scripts/validate_sam_scaleout_bundle.py:46` passes
  `--require-positive-prefix-on-followups` by default. **For r2-
  guarded B0b rows that gate fails by design.** Pass guarded B0b
  rows through the validator without that flag (or document the
  exemption per `policy=full_refill_guard_*` in the bundle README
  when wrapping into the next bundle build).
- **Within-turn rows are not affected by the guard.** They short-
  circuit the broken trim block entirely (`prefix_len ==
  input_ids.shape[1]` so the cache-reuse code path is never
  executed). Within-turn passing here doesn't tell us anything new.
- **The guard is a runtime monkey-patch, not a vendor patch.** It
  applies only inside this runner. Other scripts that use mlx-vlm's
  default `stream_generate` on Gemma still hit the bug.

## Artifacts

- Smoke (n=2, gate clean): `research/experiments/2026/artifacts/sam_scaleout_m5_r2_20260430/sam_b0b_cache_correctness_smoke.jsonl`
- Full (n=42, gate PASS): `research/experiments/2026/artifacts/sam_scaleout_m5_r2_20260430/sam_b0b_cache_correctness.jsonl`
- Validator summary: `research/experiments/2026/artifacts/sam_scaleout_m5_r2_20260430/sam_b0b_cache_correctness_summary.json`
- Run log: `research/experiments/2026/artifacts/sam_scaleout_m5_r2_20260430/sam_b0b_cache_correctness.log`
- Patched runner: `scripts/run_sam_b0b_cache_correctness.py` (commit 8568fc4: correctness-control guard + make_row policy_params + cross-turn row guard-aware emission)

## Re-run command

```bash
cd /Users/sam/repos/codec-through-jfb
HF_TOKEN=... python3 scripts/run_sam_b0b_cache_correctness.py \
  --out research/experiments/2026/artifacts/sam_scaleout_m5_r2_20260430/sam_b0b_cache_correctness.jsonl

python3 scripts/validate_sam_scaleout_artifact.py \
  --jsonl research/experiments/2026/artifacts/sam_scaleout_m5_r2_20260430/sam_b0b_cache_correctness.jsonl \
  --phase B0b --min-rows 42 \
  --require-zero-choice-diffs --require-zero-correctness-diffs \
  --require-zero-text-diffs \
  --require-matching-input-hash --require-matching-prompt-hash \
  --require-matching-frame-hashes \
  --require-b0b-protocol \
  --summary-output ...
# NOTE: do NOT add --require-positive-prefix-on-followups; it will
# fail by design on guard-fired rows.
```

Wall time on M5 Max: ~10 min for the full 7-video sweep.
