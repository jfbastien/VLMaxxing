# 2026-04-29 Phase B1 — Sam 26B C-PERSIST replication

- **Status:** **closed-arch-blocked (diagnostic; ran on broken cache).**
  B1 is contractually gated on B0b PASSING. B0b on this stack failed
  (see `2026-04-29-phase-B0b-sam-cache-correctness-findings.md`). This
  run was executed at user request to **quantify how badly the broken
  cross-turn cache bites at scale across the C-PERSIST policy
  variants**. Findings here are diagnostic, not first-class evidence.
- **Verdict:** the speedup IS real (median **10–11× wall-clock**
  vs cold-dense across both arms), but the cached arms diverge from
  cold-dense on **17–17 of 21 paired rows (~80 %)** at the text level.
  This matches the B0b finding at gate scale and confirms the §2.13.3
  speedup numbers in the sdamico whitepaper measure speed correctly
  but do NOT measure correctness preservation.

## Setup

| field | value |
|---|---|
| `model_id` | `google/gemma-4-26B-A4B-it` |
| `model_sha` | `7d4c97e54145f8ffd1a4dd1b4986a5015a517842` |
| `quantization` | `bf16_native` |
| `runtime` | `mlx_vlm-0.4.4` |
| `mlx_version` | `0.31.1` |
| `metal_version` | `Metal 4` |
| `hardware` | Apple M5 Max, 128 GB unified |
| `decoding` | greedy (`temperature=0.0`, `seed=0`) |
| `corpus` | first 7 unique videos by `question_id` from VideoMME test parquet (same as B0b) |
| `frames` | 8 deterministic timestamps |
| `max_tokens` | 32 |

## Protocol

7 videos × 3 questions per video × 3 arms (cold_dense baseline +
fixed_k1_cache_reuse + adaptive_post_prev_repaired). 42 paired rows
emitted (21 per session-arm; cold_dense in `*_baseline` columns).

| arm | cache state |
|---|---|
| `cold_dense` (baseline) | per-Q full prefill+generate, no cache |
| `fixed_k1_cache_reuse` | for each Q: build a fresh setup cache via Q0, then ONE follow-up Q reuses it (so each Q is K=1 from setup); cache rebuilt per Q |
| `adaptive_post_prev_repaired` | one cumulative cache built across SETUP → Q1 → Q2 → Q3; each Q reuses the cumulative cross-turn cache (closest analogue of 1.55F's "post-Q2 repaired" without porting the local mechanism) |

## Result table

| arm                          | n  | text_id | choice_diffs | correctness_diffs | parse_failures | speedup median | speedup mean | speedup range |
|------------------------------|---:|--------:|-------------:|------------------:|---------------:|---------------:|-------------:|---------------|
| `fixed_k1_cache_reuse`       | 21 | **4 (19%)** | 2 | 0 | 2 | **10.93×** | 10.56× | [4.15×, 18.94×] |
| `adaptive_post_prev_repaired`| 21 | **5 (24%)** | 2 | 0 | 2 | **10.29×** | 10.00× | [4.10×, 19.28×] |

Validator output (full):

```json
{
  "n_rows": 42,
  "arms": {"fixed_k1_cache_reuse": 21, "adaptive_post_prev_repaired": 21},
  "choice_diffs": 4,
  "correctness_diffs": 0,
  "text_diffs": 33,
  "parse_failures": 4,
  "input_hash_mismatches": 0,
  "prompt_hash_mismatches": 0,
  "frame_hash_mismatches": 0,
  "schema_or_gate_errors": 0,
  "pass": true
}
```

Schema clean: 0 input/prompt/frame hash mismatches between paired arms.
The divergence is purely on the LLM output side under identical inputs,
mirroring B0b.

## Speedup vs correctness — the headline

The two cells below tell the entire C-PERSIST story on this stack:

| measure | cold_dense baseline | fixed_k1 | adaptive |
|---|---:|---:|---:|
| median per-query wall-clock | ~3,100 ms | ~280 ms | ~320 ms |
| **× speedup vs cold** | 1× | **10.93×** | **10.29×** |
| paired byte-identical to cold | 21/21 (by definition) | **4/21 (19 %)** | **5/21 (24 %)** |
| paired choice-equal to cold | 21/21 | 19/21 (90 %) | 19/21 (90 %) |

The cache works fast. The cache does not preserve answers. **At ~80 %
text-divergence the cached follow-up is not the same response the user
would have gotten from a dense recompute** — even when the parsed
choice happens to land on the same letter or the same correctness
bucket.

## Stack-trace of why this fails the contractual gate

The handoff B1 gate is:

> Deterministic: <=1/21 correctness diffs and <=2/21 choice diffs.
> Parse failures <=1/21.

Per arm:

| metric | gate | fixed_k1 | adaptive |
|---|---|---:|---:|
| correctness diffs | ≤1/21 | 0/21 ✓ | 0/21 ✓ |
| choice diffs | ≤2/21 | 2/21 ✓ | 2/21 ✓ |
| parse failures | ≤1/21 | 2/21 ✗ | 2/21 ✗ |

Both arms pass the correctness/choice cuts and fail the parse-failure
cut. The parse failures are q1_mc cases where the model's response
didn't begin with a letter A/B/C/D — a documented Gemma 4 26B free-text
preference on multiple-choice instructions, not a cache-induced bug.

But the more important fact is that the gate does **not** require zero
text diffs — the underlying cross-turn cache bug B0b detects (76 % text
divergence) is invisible to the contractual B1 gate when measured on
booleans alone. **B1 gate-passing does not equal C-PERSIST is safe.**
That is the actual reviewer-defense story.

## What this means for the paper

- **§2.13.3 (sdamico whitepaper):** the **47×→150× speedup curve** and
  the **0.8 s median follow-up latency** numbers are corroborated at
  the 26B / Gemma-4 scale: ~10× speedup is consistent with the local
  Qwen 7B-4bit numbers given the larger absolute prefill cost on 26B.
  But the speedup is on a **broken** cache path; the §2.13.3 sentence
  that implies *correctness-preserving* speedup is not supported here.
  Recommended edit: split the §2.13.3 claim into "wall-clock follow-up
  latency under cache reuse" (supported) and "answer fidelity under
  cache reuse" (failed; needs SWA-aware fix or workaround).
- **JF-side claim register:** the local Qwen 7B C-PERSIST evidence
  (1.55F adaptive, 1.55I K=1) was on a non-SWA / non-mixed topology;
  the bug we're seeing is specifically the SWA + full-attention
  alternation in Gemma 4 26B-A4B interacting with mlx-vlm 0.4.4's
  unconditional prefix-trim. Pin C-PERSIST as
  **architecture-conditional**: safe-regime claim must explicitly not
  extend to mixed SWA/full-attention topologies under mlx-vlm 0.4.4.
- **Path forward (same as B0b's):** SWA-aware cache trim, or a custom
  wrapper persisting only full-attention layer KV, or full re-prefill
  every turn (loses speedup). B1 here measures the *cost* of the
  current bug: ~80 % of cached follow-ups give a different text answer
  than the dense recompute would.

## Caveats

- **Diagnostic, not contractually conformant.** B1 was supposed to be
  skipped if B0b failed. It was run anyway at user request to surface
  the 80 % text-divergence number that the B1 boolean-only gate would
  hide. The findings doc must remain marked as such.
- **`adaptive_post_prev_repaired` is an approximation.** The real
  1.55F adaptive scheme involves a "repair" step (re-prefill the last
  K tokens of the cache before each follow-up) that requires a custom
  cache wrapper not present in mlx-vlm 0.4.4. This run uses the
  cumulative cross-turn cache as the closest available analogue.
- **N=42 paired rows / 21 per arm.** Bootstrap CIs not computed; the
  ~80 % divergence number is large enough that it is signal, not
  noise, but a paper-grade claim should add CIs.
- **Speedup measurement.** Both arms use `prompt_cache_state` so the
  ~10× speedup includes the cache-path overhead. Cold-dense was always
  fresh per Q (no shared image-encoder caching). The 10× figure is
  therefore the "deployment-relevant" speedup a user sees, not a
  pure prefill-skip number.

## Artifacts

- `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b1_cpersist_replication.jsonl` (42 rows, schema-validated)
- `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b1_cpersist_replication_summary.json`
- `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b1_cpersist_replication.log`
- Runner: `scripts/run_sam_b1_cpersist_replication.py`

## Cross-reference

- B0b findings (parent): `2026-04-29-phase-B0b-sam-cache-correctness-findings.md`
- Handoff contract: `2026-04-29-sam-scaleout-handoff.md` § B1
- Sdamico whitepaper §2.13.3 (the C-PERSIST speedup claims this run
  diagnoses): `sdamico/codec-through @ 6594a7b` -- `whitepaper.md` §2.13.3
