# S0 — Gemma 4 26B-A4B cache-correctness smoke + provenance audit

- **Date:** 2026-04-26
- **Phase:** S0 (mandatory blocker for §2.13.3 persistent-KV claims)
- **Status:** **closed-arch-blocked** — followup-correctness FAILS on 3/5 items
- **Operator:** Claude Code (codec-through repo, primary.local M5 Max)
- **Repo SHA at run time:** `4c7fd19a886b2bb0db01907f0601fdc331f17da2`

## Verdict (one paragraph)

**The mlx-vlm 0.4.4 `PromptCacheState` follow-up path on Gemma 4 26B-A4B
is silently divergent from dense recomputation on a non-trivial fraction
of inputs.** Determinism (10/10) and within-turn cache-equivalence (10/10)
both PASS — i.e., a single dense run is reproducible, and building a
PromptCacheState during the *first* turn's prefill and immediately
generating from it returns the same output as the dense path. **But** the
cross-turn follow-up scenario — build cache from `[video, Q1]`, then ask
`[video, Q2]` reusing that cache versus dense `[video, Q2]` — produces
**byte-different output text on 3 of 5 items** under greedy decoding with
matching `input_ids_hash`. On the failing items, the warm followup
completes in ~0.28–1.7 s (almost no prefill) versus 2–4 s for the cold
path, confirming the cache reuse is happening — and producing wrong
answers. This reproduces the 1.55C/1.55D-style breakage class JF asked us
to audit before deepening any cache-reuse claims.

## Provenance summary

| field | value |
|---|---|
| model_id | `google/gemma-4-26B-A4B-it` |
| HF snapshot | `7d4c97e54145f8ffd1a4dd1b4986a5015a517842` |
| top-level dtype | `bfloat16` (no quantization in HF config; native BF16) |
| safetensors files | 2 shards |
| mlx | 0.31.1 |
| mlx-lm | 0.31.2 |
| mlx-vlm | 0.4.4 (installed under `/opt/homebrew`; no upstream commit pin available — Homebrew Python site-packages, treat as PyPI) |
| transformers | 5.5.4 |
| python | 3.14.3 |
| OS | Darwin 25.4.0 (macOS 16-equivalent) |
| chip | Apple M5 Max — 18 cores (6P + 12E), 128 GB RAM |
| thermal_state | no warning recorded |
| power_mode | sleep prevented; standby on |

### Attention topology (the JF audit target)

Gemma 4 26B-A4B is **not** a uniform-attention model. The text tower
interleaves sliding-window and full attention:

- 30 hidden layers total
- **25 sliding-window layers** (`sliding_window = 1024`, `rope_theta = 10000`)
- **5 full-attention layers** at indices `{5, 11, 17, 23, 29}`
  (`partial_rotary_factor = 0.25`, `rope_theta = 1e6`, `rope_type = proportional`)
- pattern: 5×SWA, 1×FA, 5×SWA, 1×FA, 5×SWA, 1×FA, 5×SWA, 1×FA, 5×SWA, 1×FA
- vision: bidirectional attention, 280 soft tokens/image
- max_position_embeddings = 262144

This is the "alternating SWA + global" topology Gemma 3 used, scaled to
30 layers in Gemma 4. The full-attention layers are necessary for
cross-turn KV reuse to be meaningful — a SWA layer with `sliding_window =
1024` and an input length of 2086 will *already* have evicted the start
of the prompt within a single turn. Any cache trimming logic in mlx-vlm
that doesn't model the SWA window per-layer will silently mis-align KV
state on follow-up turns. (mlx-vlm's `prompt_cache_state.find_prefix_length`
+ unconditional `keys[:, :, :prefix_len, :]` trim in `generate.py:687-697`
treats every layer's cache as a flat prefix-trimmable buffer, which is
unsafe for RotatingKVCache / SWA layers — even when prefix_len exceeds
the sliding window length, the trim assumes positions are contiguous.)

## Smoke test results (5 items × 2 questions, greedy, max_tokens=32)

| item_id | dur. | det. (Q1) | det. (Q2) | cache-eq. (Q1) | cache-eq. (Q2) | followup |
|---|---|---|---|---|---|---|
| `fFjv93ACGo8` | short | PASS | PASS | PASS | PASS | **FAIL** (warm "red" vs cold "green") |
| `N1cdUjctpG8` | short | PASS | PASS | PASS | PASS | **FAIL** (warm "Based on the images…" vs cold "The most prominent…") |
| `HIjX8OPuf-w` | short | PASS | PASS | PASS | PASS | PASS |
| `HwnB8aCn8yE` | short | PASS | PASS | PASS | PASS | PASS |
| `24i4ncHuf6A` | short | PASS | PASS | PASS | PASS | **FAIL** (warm "The provided images do not contain…" vs cold "The most prominent color in the scene is black.") |

Aggregate:

| test | pass / total |
|---|---|
| determinism (Arm A == Arm A') | **10 / 10** |
| cache-equivalence (Arm A == Arm B, build cache during turn-1 prefill) | **10 / 10** |
| followup-correctness (warm-Q2-after-Q1-cache == cold-Q2) | **2 / 5** |

### Smoking-gun details

For `fFjv93ACGo8` Q2 ("What color is most prominent in the scene?"):

- Same `input_ids_hash = acdafe0dcabcbf36` for **all five arms** of Q2 (dense_a,
  dense_a_repeat, cached_cold, warm_followup, cold_followup) — the prompts
  are byte-identical going into `stream_generate`.
- `dense_a` (2.19 s, 2086 input tokens):    `"The most prominent color in the scene is green."`
- `dense_a_repeat` (3.29 s):                `"The most prominent color in the scene is green."`
- `cached_cold` (2.18 s, fresh PromptCacheState built in this turn): `"…green."`
- `cold_followup` (3.92 s, fresh dense): `"…green."`
- `warm_followup` (**0.29 s**, reusing the cache built from Q1): `"The most prominent color in the scene is red."`

Token diff: `[…, 8317, 563, **2604**, 236761, 106]` (warm) vs `[…, 8317, 563,
**3826**, 236761, 106]` (cold) — single-token divergence at the
content-bearing position (the color word). This is consistent with KV
state from Q1 (which was about a Christmas tree decorated with apples,
candles, berries) leaking into Q2's first-token attention output —
plausibly via the SWA-layer KV that the cache trim treats as positionally
contiguous when it isn't. On `24i4ncHuf6A` (educational slides about
WW1) the warm path's response talks about WW1 while the cold path's
talks about color — same pattern: Q1 context bleeds into Q2's
generation.

The 2-of-5 successes are **not** evidence of correctness — they are
items where Q1 happened to produce a Q2 answer compatible with the Q1
context (`HwnB8aCn8yE` and `HIjX8OPuf-w`). With greedy decoding and
identical prompts, byte-equality is the correct bar; we hit it on 2/5.

## Implications

This blocks every persistent-KV claim in §2.13.3. Specifically:

1. **The 0.8 s follow-up / 10–18× speedup numbers** in §2.13.3 are
   measuring the wrong thing if the model is occasionally returning
   different text for the same question depending on conversation
   history. The speedup is *real* (cache reuse trims prefill from ~2 s
   to ~0.3 s for 2086-token prompts on M5 Max), but it cannot be
   reported as a free lunch — quality is being silently degraded on
   ≥60 % of items.
2. **Any benchmark that uses `PromptCacheState` for multi-turn QA on
   Gemma 4 26B-A4B (mlx-vlm 0.4.4) is contaminated.** This includes any
   prior phase-1.55C / 1.55D / persistent-KV scratchpad runs that built
   on the assumption of cache equivalence.
3. **The bug is mlx-vlm-side, not codec-through-side.** We are calling
   `stream_generate(..., prompt_cache_state=...)` exactly the way the
   library documents and exactly the way `run_gemma4_validation.py:181-221`
   uses it. The defect is most likely in the unconditional cache-trim
   loop at `generate.py:687-697` that does not honor sliding-window /
   RotatingKVCache semantics — which matches the JF hypothesis about
   `get_rope_index` broadcast / partial-image-block reuse on
   non-sliding attention.
4. **What still works:**
   - Single-turn dense generation is deterministic and reproducible
     (10/10 determinism).
   - Within-turn cache-state construction (cold cache build during
     prefill, then immediate generation) matches dense (10/10
     cache-equivalence). So a single-turn streaming generation that
     happens to allocate a PromptCacheState but never *reuses* it
     across turns is safe.

## Proposed follow-up

- **Stop using `PromptCacheState` for cross-turn reuse on Gemma 4 26B
  in mlx-vlm 0.4.4.** Anywhere we currently rely on this for the §2.13.3
  numbers, mark those numbers as **provisional / unvalidated** and
  re-run with one of:
    (a) full dense re-prefill on every turn (loses speedup, restores
        correctness — establishes the ceiling we should report);
    (b) a fixed mlx-vlm where the cache-trim path is SWA-aware
        (file an upstream issue with the smoking-gun JSONL attached);
    (c) our own cache implementation that skips the SWA layers' KV
        and only reuses full-attention layer KV across turns (would
        need empirical validation that it produces dense-equivalent
        output).
- **Re-run this smoke test** on any candidate fix as a regression gate.
- **Expand corpus** to N=20 paired items before reporting any
  cache-reuse number externally. 5 items establishes the bug exists; we
  need ≥20 to estimate the failure rate with confidence (~2/5 → 95 %
  CI is wide).
- **Consider testing the same harness on `mlx-community/gemma-4-26b-a4b-it-4bit`**
  (already cached locally) to see whether the bug is dtype-dependent or
  attention-topology-dependent.

## Artifact pointers

- script (cache-correctness): `/Users/sam/repos/codec-through/experiments/exp_s0_cache_correctness_smoke.py`
- script (provenance): `/Users/sam/repos/codec-through/experiments/exp_s0_provenance.py`
- provenance dump: `/Users/sam/repos/codec-through/research/2026-04-26-s0-provenance.json`
- per-arm JSONL (40 rows = 5 items × 8 arms: dense_a/repeat/cached_cold ×2 questions + warm_followup + cold_followup): `/Users/sam/repos/codec-through/research/2026-04-26-s0-cache-correctness/results.jsonl`
- summary: `/Users/sam/repos/codec-through/research/2026-04-26-s0-cache-correctness/summary.json`

## Re-run command

```bash
cd /Users/sam/repos/codec-through
HF_TOKEN=... python3 experiments/exp_s0_provenance.py
HF_TOKEN=... python3 experiments/exp_s0_cache_correctness_smoke.py --n_items 5 --n_frames 8
```

Smoke-only (1 item) variant for harness validation:

```bash
HF_TOKEN=... python3 experiments/exp_s0_cache_correctness_smoke.py --smoke_one
```

Total wall time on M5 Max / 128 GB / mlx-vlm 0.4.4: ~17 min for the 5-item
run (model load 7 s, ffmpeg frame extraction for 5 videos at 8 frames
each ~30 s, then ~3 min/item average for 8 arms each — 6 prefills of
~2086 input tokens + 1 warm + 1 cold followup).
