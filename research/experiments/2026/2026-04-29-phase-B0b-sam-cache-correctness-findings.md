# 2026-04-29 Phase B0b — Sam scale-out cache-correctness gate

- **Status:** **closed-mixed** — default cache reuse FAILS; patched
  topology-aware fallback PASSES correctness but is not a speedup path.
- **Verdict:** mlx-vlm 0.4.4 `PromptCacheState` cross-turn cache reuse on
  Gemma 4 26B-A4B is silently divergent from cold-dense recomputation on
  **14 of 19 paired rows (74%)** after excluding 2 matched parse
  failures (raw count: 16 of 21). Within-turn cache replay path passes
  cleanly (21/21 byte-identical). A later patched-library full-regression run
  fixes correctness by refusing unsafe rotating-cache trimming: 42/42 rows are
  text-identical, with 0 choice diffs, 0 correctness diffs, and 4 matched parse
  failures. That closes the correctness gate, but not the speed path.
- **Implication for downstream:**
  - **B1 (C-PERSIST replication) — speed path still BLOCKED.** The
    patched path is correctness-clean because it refuses unsafe rotating-cache
    trim, so it can be used as a control but not as positive follow-up speed
    evidence.
  - **B2 (many-turn streaming horizon) — speed path still BLOCKED** for the
    same reason; a many-turn correctness-only control is possible but does not
    promote C-STREAM.
  - **B3 (matched streaming baselines) — RUNNABLE.** The handoff
    explicitly says B3 can run while B0b blocks cross-turn cache reuse,
    as long as the policies compared do not depend on the broken cache
    path. Polling, low-FPS dense, and recency baselines are all
    independent of `PromptCacheState`; the sam-policy arm will use
    within-turn cache reuse only (validated by B0b at 21/21).
  - **B5 (S4 re-export) — RUNNABLE** (artifact re-packaging, no cache).

## 2026-04-30 patched-library full-regression closure

The follow-up run under the topology-aware patched library path is
correctness-clean because the patched `PromptCacheState` path refuses the
unsafe cross-turn trim. Validator summary:

```json
{
  "n_rows": 42,
  "arms": {"within_turn_cache_replay": 21, "cross_turn_warm": 21},
  "policies": {"prompt_cache_state_within_turn": 21, "prompt_cache_state_cross_turn_chained": 21},
  "choice_diffs": 0,
  "correctness_diffs": 0,
  "text_diffs": 0,
  "parse_failures": 4,
  "input_hash_mismatches": 0,
  "prompt_hash_mismatches": 0,
  "frame_hash_mismatches": 0,
  "schema_or_gate_errors": 0,
  "pass": true
}
```

This is the evidence used by the manuscript's scale-out row: patched
cache-correctness is full-regression verified, but it does not earn C-STREAM
speedup because the unsafe trim is refused and cross-turn wall-clock is roughly
cold dense.

## Provenance

| field | value |
|---|---|
| `model_id` | `google/gemma-4-26B-A4B-it` |
| `model_sha` | `7d4c97e54145f8ffd1a4dd1b4986a5015a517842` |
| `quantization` | `bf16_native` |
| `runtime` | `mlx_vlm-0.4.4` |
| `mlx_version` | `0.31.1` (per S0 audit) |
| `metal_version` | `Metal 4` |
| `hardware` | Apple M5 Max, 128 GB unified memory |
| `os_version` | `Darwin 25.4.0` |
| `commit_sha` | `20396be...` (this branch HEAD at run start) |
| `decoding` | greedy (`temperature=0.0`, `seed=0`) |
| `corpus` | first 7 unique videos by `question_id` from VideoMME test parquet |
| `frame extraction` | 8 frames @ deterministic `np.linspace(1%, 99%)` of duration, ffmpeg-extracted, 560×560 letterboxed |
| `max_tokens` | 32 |

## Cache topology (the JF audit target)

`Gemma 4 26B-A4B` text tower has 30 hidden layers in the pattern
`5×SWA, 1×FA, 5×SWA, 1×FA, …` — **25 sliding-window layers**
(`sliding_window=1024`) **+ 5 full-attention layers** at indices
`{5, 11, 17, 23, 29}`. This is recorded in every row's `cache_topology`
field.

mlx-vlm 0.4.4's `PromptCacheState` `find_prefix_length` + unconditional
`keys[:, :, :prefix_len, :]` trim in
`mlx_vlm/generate.py:687-697` treats every layer's cache as a flat
prefix-trimmable buffer. With 25 SWA layers whose KV is only valid for
the last 1,024 tokens of the trimmed range, cross-turn cache reuse
silently mis-aligns positions on those layers. This matches the
1.55C / 1.55D `get_rope_index` broadcast / partial-image-block class
JF flagged before the scale-out lane started.

## Protocol

- 7 videos × 3 evaluation questions per video.
- Q1 = parquet's `question` (multiple-choice with options, instruction
  to "Answer with a single letter A/B/C/D"); Q2 = "What color is most
  prominent in the scene?"; Q3 = "Are there any people visible?
  Answer YES or NO and one short phrase."
- Three arms per (video, question), all with identical frames + identical
  prompt:
  - `cold_dense` (baseline): full prefill+generate, no cache
  - `within_turn_cache_replay`: build `PromptCacheState` during this
    turn's prefill, generate from it; cache is fresh, scoped to this
    turn only
  - `cross_turn_warm`: build cache during a Q0 setup turn ("Briefly
    describe what you see."), then ask Q1, Q2, Q3 chained against that
    cache (each turn's response added to the conversation; cache reused
    across turns)
- One paired row per (video, q_index, arm) where arm ∈ {within, cross},
  baseline_arm = cold_dense; identical `frame_hashes` /
  `frame_selection_hash` between paired arms; identical raw_prompt;
  `input_ids_hash` recorded per arm.
- Total: 21 within-turn rows + 21 cross-turn rows = 42 schema-compliant
  rows in `sam_b0b_cache_correctness.jsonl`.

## Result table

| arm | n | text_identical | choice_diffs | correctness_diffs | parse_failures (per-arm OR baseline) |
|---|---:|---:|---:|---:|---:|
| `within_turn_cache_replay` | 21 | **21 (100%)** | 0 | 0 | 0 |
| `cross_turn_warm` | 21 | **5 (24%)** | 2 | 0 | 4 |
| **total** | **42** | **26 (62%)** | **2** | **0** | **4** |

Validator output (full):

```json
{
  "n_rows": 42,
  "arms": {"within_turn_cache_replay": 21, "cross_turn_warm": 21},
  "choice_diffs": 2,
  "correctness_diffs": 0,
  "text_diffs": 16,
  "parse_failures": 4,
  "session_parse_failures": 4,
  "baseline_parse_failures": 4,
  "input_hash_mismatches": 0,
  "prompt_hash_mismatches": 0,
  "frame_hash_mismatches": 0,
  "schema_or_gate_errors": 3,
  "first_errors": [
    "paired choices must match for every row",
    "raw paired responses must be identical for every row",
    "per-arm parse failures must be false for every row"
  ],
  "pass": false
}
```

Schema validation: **clean** (0 schema errors; 0 derived-consistency
errors; 0 input-hash / prompt-hash / frame-hash mismatches between
paired arms — i.e. when the two arms diverge it is purely the LLM
output that diverges, not the inputs).

## Smoking-gun examples

| `pair_key` | Q | `cold_dense` (baseline) | `cross_turn_warm` |
|---|---|---|---|
| `v=fFjv93ACGo8/q=1/cross` | "What color is most prominent?" | "The most prominent color in the scene is **green**." | "The most prominent color in the scene is **purple**." |
| `v=HwnB8aCn8yE/q=2/cross` | "Are there any people visible?" | "**YES, various human ancestors.**" | "**NO**, silhouettes of hominids." |
| `v=24i4ncHuf6A/q=1/cross` | "What color is most prominent?" | "The most prominent color in the scene is **black**." | "**The provided images appear to be a sequence of slides from a**…" (Q1 about WW1 leaks into Q2) |
| `v=fFjv93ACGo8/q=0/cross` | (Q1 multiple-choice) | "Based on the image provided that demonstrates the historical…" | "**A**" |
| `v=HIjX8OPuf-w/q=0/cross` | (Q1 multiple-choice) | "**C**" | "**A**" — different chosen letter |

The model is producing internally-consistent but **factually different**
answers when the cache is reused across turns. Several text diffs are
single-token / minor formatting variations; the highlighted ones above
are content-bearing divergences (different color word, opposite YES/NO
answer, different MC letter).

## What this means for the paper

- **§2.13.3 persistent-KV claims (sdamico whitepaper):** the 0.8 s /
  10–18× / 47–150× follow-up speedup numbers are about wall-clock and
  remain measured-true; what they cannot claim — and what the
  whitepaper currently misstates — is that the *answers* match the
  cold-dense baseline. They don't, on a non-trivial fraction (~74%
  excluding matched parse failures, ~76% raw, on
  these 21 rows). The §2.13.3 prose needs to be qualified; the speedup
  remains a real result, but as a *speed* result, not a *correctness-
  preserving speed* result.
- **JF-side claim register (`docs/claim-register.md`, C-PERSIST cell):**
  the local 7B-4bit C-PERSIST evidence (1.55F adaptive, 1.55I K=1, etc.)
  is on a different model family (Qwen) and a different attention
  topology (no SWA at the same scale). The bug we caught here does not
  invalidate any of those local cells. But it does pin C-PERSIST as
  **architecture-conditional**: the safe-regime claim must explicitly
  not extend to mixed SWA/full-attention topologies under mlx-vlm 0.4.4.
- **Path forward:** the contractually correct response is to
  (a) report this failure in the paper as a boundary, **and**
  (b) implement either (i) a SWA-aware cache trim that respects per-layer
  window semantics, (ii) a custom cache wrapper that only persists KV
  for the 5 full-attention layers and re-prefills the SWA layers each
  turn, or (iii) full re-prefill on every turn (loses speedup, restores
  correctness — establishes the ceiling). Each of (i)–(iii) is a
  separate piece of engineering work; B0b's job here is to catch the
  bug, which it did.

## Artifacts

- Paired JSONL (42 rows, schema-validated):
  `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b0b_cache_correctness.jsonl`
- Validator summary:
  `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b0b_cache_correctness_summary.json`
- Run log:
  `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b0b_cache_correctness.log`
- Guarded full-refill JSONL and summary:
  `research/experiments/2026/artifacts/sam_scaleout_m5_r2_20260430/sam_b0b_cache_correctness.jsonl`,
  `research/experiments/2026/artifacts/sam_scaleout_m5_r2_20260430/sam_b0b_cache_correctness_summary.json`
- Patched full-regression JSONL and summary:
  `research/experiments/2026/artifacts/sam_scaleout_m5_r2_followup_20260430/sam_b0b_cache_correctness_unguarded_patched.jsonl`,
  `research/experiments/2026/artifacts/sam_scaleout_m5_r2_followup_20260430/sam_b0b_cache_correctness_unguarded_patched_summary.json`
- Runner: `scripts/run_sam_b0b_cache_correctness.py`
- Validator: `scripts/validate_sam_scaleout_artifact.py`

## Re-run command

```bash
cd /Users/sam/repos/codec-through  # for VideoMME data
HF_TOKEN=... python3 \
  /Users/sam/repos/codec-through-jfb/scripts/run_sam_b0b_cache_correctness.py

python3 /Users/sam/repos/codec-through-jfb/scripts/validate_sam_scaleout_artifact.py \
  --jsonl /Users/sam/repos/codec-through-jfb/research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b0b_cache_correctness.jsonl \
  --phase B0b \
  --min-rows 42 \
  --require-zero-choice-diffs --require-zero-correctness-diffs \
  --require-zero-text-diffs --require-zero-parse-failures \
  --require-matching-input-hash --require-matching-prompt-hash \
  --require-matching-frame-hashes \
  --require-positive-prefix-on-followups \
  --require-b0b-protocol \
  --summary-output ...
```

Wall time on M5 Max: ~5 min for the 7-video sweep + 8 s model load.

## Cross-reference

- `research/experiments/2026/2026-04-29-sam-scaleout-handoff.md` (the
  contract this gate executes against)
- S0 finding (sdamico/codec-through @ `e4ffc27`,
  `research/2026-04-26-s0-cache-correctness-findings.md`) — original
  5-item N=10 audit that found the same bug at smaller scale; B0b is
  the contractual scale (21 paired rows / 7 videos / 3 questions).
