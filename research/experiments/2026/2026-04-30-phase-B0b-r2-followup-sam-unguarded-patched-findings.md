---
date: 2026-04-30
phase: B0b r2-followup (closure of upstream-fix gate)
status: closed-earned (full B0b regression PASS with library patch + runtime guard disabled)
related:
  - 2026-04-29-phase-B0b-sam-cache-correctness-findings.md (r1 -- 76% wrong on broken cache path)
  - 2026-04-30-phase-B0b-r2-sam-correctness-control-findings.md (r2 -- runner-side guard PASS)
  - 2026-04-30-phase-upstream-mlx-vlm-swa-aware-trim-findings.md (the patch this run validates)
  - 2026-04-29-phase-M5-5b-sam-prefix-snapshot-fix-findings.md (speedup-preserving alternative)
---

# 2026-04-30 Phase B0b r2-followup — Full unguarded B0b PASS with library patch

- **Status:** **closed-earned.** Full 42-row B0b paired suite re-run on
  patched mlx-vlm 0.4.4 with the in-runner correctness guard
  **disabled** (`B0B_DISABLE_RUNTIME_GUARD=1`). Result: **42/42 text-
  identical to cold-dense, 0 choice diffs, 0 correctness diffs, 4
  matched parse failures**, cross-turn wall-clock at **0.98× of cold
  dense** confirming the patched library surrendered cache reuse
  cleanly and produced correct outputs.
- **Why this run exists:** JF's commit `223c8fb` flagged the upstream-
  fix doc's prior "closed-earned" status as premature because the
  patch had only been smoke-verified on a single cross-turn pair. The
  closure gate JF defined was the full 42-row B0b regression, with
  the runtime guard disabled, on the patched library. This run
  closes that gate.
- **What this proves:** the library patch (`scripts/mlx_vlm_swa_aware_trim.patch`)
  reproduces B0b's correctness guarantee at full scale **without any
  runner-level intervention**. Cross-turn runs are correctness-clean
  (byte-identical to cold dense) and pay the full cold-dense prefill
  cost — i.e., the patched library does what it promises: surrenders
  cache reuse rather than producing silently wrong outputs.

## Setup

| field | value |
|---|---|
| `model_id` | `google/gemma-4-26B-A4B-it` |
| `model_sha` | `7d4c97e54145f8ffd1a4dd1b4986a5015a517842` |
| `quantization` | `bf16_native` |
| `runtime` | `mlx_vlm-0.4.4` **with `scripts/mlx_vlm_swa_aware_trim.patch` applied** |
| `runtime_commit` | `pypi` (with local patch on `/opt/homebrew/.../mlx_vlm/generate.py`) |
| `runner monkey-patch` | **DISABLED** via `B0B_DISABLE_RUNTIME_GUARD=1` |
| `decoding` | greedy (`temperature=0.0`, `seed=0`) |
| `corpus` | first 7 unique videos by `question_id` from VideoMME test parquet (same as r1/r2) |
| `frames` | 8 deterministic timestamps |
| `max_tokens` | 32 |
| hardware | M5 Max, 128 GB unified, Darwin 25.4.0 |

## Configuration delta vs B0b r2

| dimension | r2 (closed-correctness-control) | r2-followup (this run) |
|---|---|---|
| mlx-vlm library | unpatched 0.4.4 | **patched 0.4.4** |
| runner monkey-patch | active (`stream_generate` rebound) | **disabled** (`B0B_DISABLE_RUNTIME_GUARD=1`) |
| effective code path | runner refuses cache reuse before `stream_generate` runs | library accepts the prompt cache, internal `can_trim_prompt_cache` returns False on RotatingKVCache, falls through to cold-dense |
| cross-turn `policy` field | `full_refill_guard_rotating_kv` | `prompt_cache_state_cross_turn_chained` (runner *intended* reuse; library refused) |
| how correctness is achieved | runtime monkey-patch in our process | upstream fix at the library boundary |

The two paths produce **functionally identical** outputs: cross-turn
arm running at cold-dense speed and cold-dense byte-text. The
difference is *where* the cache-reuse refusal happens.

## Results

### Validator summary

```json
{
  "n_rows": 42,
  "phases": {"B0b": 42},
  "arms": {"within_turn_cache_replay": 21, "cross_turn_warm": 21},
  "policies": {
    "prompt_cache_state_within_turn": 21,
    "prompt_cache_state_cross_turn_chained": 21
  },
  "choice_diffs": 0,
  "correctness_diffs": 0,
  "text_diffs": 0,
  "parse_failures": 4,
  "session_parse_failures": 4,
  "baseline_parse_failures": 4,
  "input_hash_mismatches": 0,
  "prompt_hash_mismatches": 0,
  "frame_hash_mismatches": 0,
  "schema_or_gate_errors": 0,
  "first_errors": [],
  "pass": true
}
```

Validator flags used:

```bash
--require-zero-choice-diffs
--require-zero-correctness-diffs
--require-zero-text-diffs
--require-matching-input-hash
--require-matching-prompt-hash
--require-matching-frame-hashes
--require-b0b-protocol
```

`--require-positive-prefix-on-followups` was **NOT** passed. As with
r2, that gate would fire here for the wrong reason: cross-turn rows
report `prefix_hit > 0 / prefix_coverage = 1.0` (the runner *passed*
a positive prefix to `stream_generate` — it was the library that
internally refused to reuse it). The flag's intent — that downstream
turns actually benefit from prior-turn caching — is satisfied
neither here nor in r2; both are cold-dense paths under the hood.

### Cross-turn arm — per-row policy + timing

All 21 cross-turn rows: `policy = "prompt_cache_state_cross_turn_chained"`,
`prefix_hit > 0`, `prefix_coverage = 1.0`, `vit_calls = 0`,
`baseline_vit_calls = 1`. The runner-emitted prefix metadata reflects
what it sent to `stream_generate`; the library's internal trim
refusal is invisible at the runner boundary.

| metric | value | what it tells us |
|---|---:|---|
| median `end_to_end_ms` (cross-turn) | 2482.3 ms | matches baseline cold-dense |
| median `baseline_end_to_end_ms` | 2458.8 ms | cold dense for the same rows |
| **median wall-clock speedup** | **0.98×** | **proof that cache reuse was abandoned** — if cache had been reused, this would be 5–10× per the broken r1 numbers |
| median `prefill_ms` (cross-turn) | 2313.3 ms | full ~2K-token prefill happened on cross-turn (would be near-zero if cache had been reused) |
| `peak_memory_gb` max | 49.13 GB | within Gemma 4 26B-A4B envelope; consistent with M5-5b/r2 |

The 0.98× cross-turn wall-clock — slightly slower than cold dense
because of an extra Python-level pass over the cache state that gets
discarded — is the **mechanical signature** of the patched library
falling through. A correctness-clean cache reuse path would be
substantially faster; a broken reuse path would be fast and wrong;
this run is slow and right, exactly as designed.

### Within-turn arm

Within-turn rows are not affected by the patch (they short-circuit
the trim block: `prefix_len == input_ids.shape[1]`, `trim_amount = 0`,
`can_trim_prompt_cache` is bypassed). 21/21 text-identical, as
expected.

### Parse failures

4 matched parse failures: 2 on `q1_mc` for video `24i4ncHuf6A`
(within + cross), 2 on `q1_mc` for video `0ay2Qy3wBe8` (within +
cross). Both `session_parse_failure` and `baseline_parse_failure` are
True for each — Gemma 4 26B-A4B emits free-text preamble before the
multiple-choice letter on these two questions, defeating the strict
parser. **Identical row-set to B0b r2 and B0b r1**, confirming this
is a corpus/parser interaction that is independent of the cache
path.

## Comparison vs r1, r2

| metric | r1 (broken library, no guard) | r2 (broken library, runner guard) | r2-followup (patched library, no guard) |
|---|---:|---:|---:|
| n_rows | 42 | 42 | 42 |
| within_turn text-identical | 21/21 | 21/21 | 21/21 |
| **cross_turn text-identical** | **5/21 (24%)** | **21/21 (100%)** | **21/21 (100%)** |
| cross_turn choice_diffs | 2/21 | 0/21 | 0/21 |
| cross_turn correctness_diffs | 0/21 | 0/21 | 0/21 |
| cross_turn parse_failures | 2 (matched) | 2 (matched) | 2 (matched) |
| **gate PASS** | **FAIL** | **PASS (correctness control)** | **PASS (library fix)** |
| where the fix lives | — | runner monkey-patch | upstream library |
| cross-turn median wall vs cold | ~0.1× (broken-fast) | ~1.0× (full refill via runner) | **0.98× (full refill via library)** |
| `cross_turn` policy field | `prompt_cache_state_cross_turn_chained` | `full_refill_guard_rotating_kv` | `prompt_cache_state_cross_turn_chained` |

r2 and r2-followup are **functionally equivalent**: both achieve
correctness-clean cross-turn behavior by abandoning cache reuse on
mixed-SWA topologies, just at different layers (runner vs library).

## What this means

- **The upstream-fix doc's "closed-earned" claim is now backed by full-
  scale data.** Per JF's framing in `223c8fb`, the missing data point
  was the unguarded full B0b regression. This run produces it: 42/42
  byte-identical to cold dense, 0 correctness diffs, cross-turn
  wall-clock at cold-dense speed. The patch reproduces the
  correctness guarantee at the same scale that B0b r2's runner-level
  fix did.
- **The runner monkey-patch becomes redundant on patched mlx-vlm
  versions.** With the library patched, the runner's
  `_correctness_guard_stream_generate` no-ops effectively (it would
  fire its own guard and refuse cache reuse, but the library would
  have done the same thing internally via `can_trim_prompt_cache`).
  We keep the runner guard as defense-in-depth so that B0b runs
  stay correctness-clean on unpatched mlx-vlm (e.g., a fresh
  `pip install --upgrade mlx-vlm` that reverts the local patch).
- **Speedup story is unchanged.** Both r2 and r2-followup achieve
  correctness by surrendering cross-turn speedup. The C-PERSIST
  speedup-preserving mechanism for mixed-SWA models remains
  M5-5b's prefix-snapshot wrapper (`scripts/swa_aware_cache_v2.py`),
  which sidesteps the trim path entirely by snapshotting before
  question tokens enter the cache.

## Caveats

- **`vit_calls = 0` on cross-turn rows is technically misleading.**
  The runner records `vit_calls = 0` because the python-level vision
  features are cached at the wrapper boundary (independent of the
  text-token KV cache the patch operates on). The patched library
  re-prefills the *text/visual-token* KV cache from scratch, but
  doesn't re-run the ViT encoder. So the row metadata is correct as
  emitted; it just doesn't surface the internal full re-prefill that
  did happen on the language-model side. The wall-clock proves the
  re-prefill (median 2313 ms prefill_ms vs near-zero if cache had
  been reused).
- **Local patch fragility.** The library patch is applied to
  `/opt/homebrew/.../mlx_vlm/generate.py` and will be reverted by
  any `pip install --upgrade mlx-vlm`. Closing this loop properly
  requires merging the upstream PR. Until that lands, a local
  workflow needs the apply helper before running.
- **`policy="prompt_cache_state_cross_turn_chained"` on guarded-by-
  library rows is semantically correct from the runner's POV but
  could mislead a reader assuming the policy label tracks the
  effective code path inside the library.** A future runner change
  could introspect the patched library's behavior and emit a
  `policy_params={"library_can_trim": False}` flag, but that's not
  needed for the gate; the wall-clock signal is unambiguous.
- **No new architectural insight.** This run does not add new
  scientific evidence beyond r2; it just relocates the existing
  fix from the runner to the library. The value is reproducibility
  for downstream users on patched mlx-vlm.

## Artifacts

- JSONL (42 rows): `research/experiments/2026/artifacts/sam_scaleout_m5_r2_followup_20260430/sam_b0b_cache_correctness_unguarded_patched.jsonl`
- Validator summary: `research/experiments/2026/artifacts/sam_scaleout_m5_r2_followup_20260430/sam_b0b_cache_correctness_unguarded_patched_summary.json`
- Run log: `research/experiments/2026/artifacts/sam_scaleout_m5_r2_followup_20260430/sam_b0b_cache_correctness_unguarded_patched.log`
- Library patch: `scripts/mlx_vlm_swa_aware_trim.patch`
- Apply helper: `scripts/apply_mlx_vlm_swa_patch.sh`
- Runner with env-var gate: `scripts/run_sam_b0b_cache_correctness.py`
  (the `B0B_DISABLE_RUNTIME_GUARD` opt-out added in this commit)

## Re-run command

```bash
cd /Users/sam/repos/codec-through-jfb

# 1. Apply the library patch (or `--check` first to dry-run).
./scripts/apply_mlx_vlm_swa_patch.sh

# 2. Run B0b with the runner-level guard DISABLED. Only the library
#    patch is in effect. The library's `can_trim_prompt_cache` will
#    return False for RotatingKVCache and fall through cleanly.
B0B_DISABLE_RUNTIME_GUARD=1 python3 scripts/run_sam_b0b_cache_correctness.py \
  --out research/experiments/2026/artifacts/sam_scaleout_m5_r2_followup_20260430/sam_b0b_cache_correctness_unguarded_patched.jsonl

# 3. Validate (without --require-positive-prefix-on-followups; see
#    the analogous r2 caveat).
python3 scripts/validate_sam_scaleout_artifact.py \
  --jsonl research/experiments/2026/artifacts/sam_scaleout_m5_r2_followup_20260430/sam_b0b_cache_correctness_unguarded_patched.jsonl \
  --phase B0b --min-rows 42 \
  --require-zero-choice-diffs --require-zero-correctness-diffs \
  --require-zero-text-diffs \
  --require-matching-input-hash --require-matching-prompt-hash \
  --require-matching-frame-hashes \
  --require-b0b-protocol \
  --summary-output research/experiments/2026/artifacts/sam_scaleout_m5_r2_followup_20260430/sam_b0b_cache_correctness_unguarded_patched_summary.json

# 4. Revert the library patch when done so future `pip install
#    --upgrade mlx-vlm` works cleanly.
./scripts/apply_mlx_vlm_swa_patch.sh --revert
```

Wall time on M5 Max: ~10 min for the full 7-video sweep, indistinguishable
from r2 (cross-turn full re-prefill happens either way; the difference
is which layer refuses cache reuse).
