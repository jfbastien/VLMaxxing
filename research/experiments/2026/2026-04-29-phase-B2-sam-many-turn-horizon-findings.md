# 2026-04-29 Phase B2 — Sam many-turn streaming horizon

- **Status:** **closed-arch-blocked (diagnostic).** B2 is contractually
  gated on B0b passing; ran anyway to surface the drift-curve shape.
  Result is more nuanced than B0b/B1 alone suggested.
- **Verdict, the right axis (effective frame ingestion at fixed
  correctness):** **no operating regime on this stack delivers both
  correctness AND speedup at the same time.** You get one or the
  other:
  - `fixed_k1_after_setup` (rebuild cache per turn): **28× wall-clock
    speedup**, but **answers are incorrect on 100/150 rows** (66 %)
    when the cold-dense answer is non-trivial; correct only when the
    answer is content-obvious enough to survive the cache bug.
  - `adaptive_post_prev_repaired` (cumulative cache grows across
    turns): **98–100 % correct** (after the first turn the cache
    stabilizes and reproduces the cold-dense answer), but **median
    speedup 0.84× — actually slower than cold-dense** because the
    cache state grows pathologically with each turn.
  - `scheduled_refresh_every_10_turns`: **90–100 % correct, 0.83×
    speedup**; correctness fails specifically at the 5 refresh
    boundaries (turns 0, 10, 20, 30, 40) where the cache resets to
    "post-setup" state and the bug fires.
- **Implication for §2.13.3 (sdamico whitepaper):** the C-PERSIST
  claim "0.8 s follow-up at correctness preserved" is not supported
  on Gemma 4 26B / mlx-vlm 0.4.4. The fastest regime (fixed_k1) is
  fast but content-conditional on correctness; the correct regime
  (adaptive cumulative) is slower than dense. **The "ingestion-
  density gain at fixed compute and fixed quality" claim does not
  hold on this stack.**
- **Surprise for the paper to keep:** the cache actually
  **self-corrects after turn 0** when the same question is asked
  repeatedly. This is consistent with B0b/B1's "first cached
  follow-up is unsafe" finding and explains why JF's local Qwen
  C-PERSIST evidence is consistent with our 26B finding —
  same-question repeated polling under cumulative cache is the safe
  regime; fresh-setup-then-one-followup is the unsafe regime.

## Setup

| field | value |
|---|---|
| `model_id` | `google/gemma-4-26B-A4B-it` |
| `model_sha` | `7d4c97e54145f8ffd1a4dd1b4986a5015a517842` |
| `quantization` | `bf16_native` |
| `runtime` | `mlx_vlm-0.4.4` |
| `decoding` | greedy (`temperature=0.0`, `seed=0`) |
| `corpus` | first 3 unique videos from VideoMME test parquet |
| `frames` | 8 deterministic timestamps |
| `repeated question` | "What is the most prominent color in this video? Answer in one word." |
| `max_tokens` | 16 |
| `horizon` | 50 turns / video / arm |
| `refresh_every` | 10 turns (scheduled_refresh arm only) |

3 videos × 50 turns × 3 session arms = **450 paired rows**, with
cold-dense recorded as `*_baseline` columns on every row.

## Result table — correctness × speedup

| arm | text-identical (per-video) | overall correctness | speedup median |
|---|---|---:|---:|
| `fixed_k1_after_setup` | fFjv93ACGo8: 50/50 (100%) · HIjX8OPuf-w: 0/50 · N1cdUjctpG8: 0/50 | **33%** (100/150) | **28.60×** |
| `adaptive_post_prev_repaired` | fFjv93ACGo8: 50/50 · HIjX8OPuf-w: 49/50 · N1cdUjctpG8: 49/50 | **99%** | 0.84× |
| `scheduled_refresh_every_10_turns` | fFjv93ACGo8: 50/50 · HIjX8OPuf-w: 45/50 · N1cdUjctpG8: 45/50 | **93%** | 0.83× |

**No row of the table has both ≥95 % correctness and ≥1× speedup.**

## What the cache actually does — the per-turn drift curve

Cold-dense answer is deterministic: same answer on every turn (e.g.
"Black" for `HIjX8OPuf-w`). The cached arms diverge on turn 0 (the
bug fires on the first cached follow-up) and then their behavior
depends on cache policy:

| arm | turn 0 | turn 1 | turn 5 | turn 25 | turn 49 |
|---|---|---|---|---|---|
| `fixed_k1_after_setup` (HIjX8OPuf-w, dense="Black") | "White" | "White" | "White" | "White" | "White" |
| `adaptive_post_prev_repaired` (HIjX8OPuf-w) | "White" | "Black" | "Black" | "Black" | "Black" |
| `scheduled_refresh_every_10_turns` (HIjX8OPuf-w) | "White" | "Black" | "Black" | "Black" (drifts again at turn 30, 40) | "Black" |

The two failure modes of the `fixed_k1` arm depend on the question's
difficulty:

- `fFjv93ACGo8` (cold-dense answer = "Purple", a common video color):
  cached arm also says "Purple" → 100 % correct.
- `HIjX8OPuf-w` (cold-dense = "Black", a more subtle answer): cached
  arm consistently says "White" → 0 % correct.
- `N1cdUjctpG8` (cold-dense = "Black", subtle): cached says "Brown"
  → 0 % correct.

This is exactly the cache-state-mis-alignment signature B0b found,
now showing how it interacts with question difficulty:
**the bug fires deterministically; whether it produces the *wrong*
answer depends on whether the model's mis-aligned attention happens
to land on the same content as the dense baseline.**

## What the headline-axis ("frames at fixed compute and quality") says

The user-pushback frame: cache reuse should let us **ingest more
frames per fixed compute and matched quality**. Translating per arm:

- `fixed_k1`: 28× per-query speedup → at fixed compute you could
  fit 28× more queries (or 28× more frames per query). But: **only
  on questions whose answer is content-obvious enough to survive the
  bug**. Reliability is content-conditional — that fails the
  "matched quality" gate.
- `adaptive`: 99 % reliable but 0.84× speedup → at fixed compute
  you fit slightly fewer queries than dense. **No ingestion-density
  gain; small loss.**
- `scheduled_refresh`: 93 % reliable, 0.83× speedup → same as
  adaptive but worse on both axes.

**On this stack, the cache mechanism does not deliver an
effective-frame-rate gain at deployment-grade quality.** That is the
honest paper conclusion. The §2.13.3 numbers (47×–150× speedup
on Qwen 7B-4bit) are local-arch evidence; they do not transfer to
Gemma 4 26B-A4B / mlx-vlm 0.4.4 under any of the three policies B2
tested.

## Why is `adaptive` slower than dense, even though it caches?

Cumulative cache grows turn over turn. Each new turn's input_ids
are constructed fresh (the harness rebuilds the prompt for the
current question), and `PromptCacheState.find_prefix_length` then
walks the cache against the new input_ids. The longer the cache, the
slower the prefix lookup and the more state to manipulate. By turn
49 the cache contains 50 prior responses' worth of accumulated
state.

This is a known pathological scaling pattern of `PromptCacheState`
when used for stateless repeated-question polling: the cache grows
even though you don't need most of it. **A correct cumulative-cache
deployment would be to keep just the visual prefix in the cache and
reset the conversational tail per turn**, but that requires a
custom cache wrapper not in mlx-vlm 0.4.4.

The `fixed_k1` arm sidesteps this by rebuilding the setup-only
cache each turn. That cache is small. Hence its 28× speedup.

## Validator output

```json
{
  "n_rows": 450,
  "phases": {"B2": 450},
  "arms": {
    "fixed_k1_after_setup": 150,
    "adaptive_post_prev_repaired": 150,
    "scheduled_refresh_every_10_turns": 150
  },
  "choice_diffs": 0,
  "correctness_diffs": 0,
  "text_diffs": 112,
  "parse_failures": 0,
  "input_hash_mismatches": 0,
  "prompt_hash_mismatches": 0,
  "frame_hash_mismatches": 0,
  "schema_or_gate_errors": 0,
  "first_errors": [],
  "pass": true
}
```

Schema validates clean: 0 input/prompt/frame hash mismatches across
paired arms (the harness builds identical inputs every turn). The
112 text diffs decompose as 50 × 2 videos for fixed_k1 (the always-
wrong rows) + 1 + 1 turn-0 errors for adaptive on the 2 hard videos +
5 × 2 refresh-boundary errors for scheduled_refresh.

## Handoff B2 gate evaluation

The handoff B2 gate:

> Report longest horizon with ≤3 % paired choice and correctness drift.
> Flag a cliff if any 10-turn bucket exceeds 10 % drift.

| arm | longest horizon ≤3 % drift | 10-turn cliff? |
|---|---|---|
| `adaptive_post_prev_repaired` | **horizon=50** (1 % overall drift) | no cliff |
| `scheduled_refresh_every_10_turns` | none (7 % overall) | every refresh boundary is a 10-turn cliff (~67 % drift in that bucket on hard videos) |
| `fixed_k1_after_setup` | none (67 % overall) | every bucket is a permanent cliff |

**Adaptive passes the gate at horizon 50.** But — note — the gate
measures drift against cold-dense. It does not measure speedup, and
adaptive is slower than dense. So a "passes the gate" cell is
necessary-but-not-sufficient for an ingestion-density claim.

## What this means for the paper

- **§2.13.3 (sdamico whitepaper) — explicit qualifier required.** The
  Gemma 4 26B C-PERSIST follow-up speedup numbers must come with:
  - "first cached follow-up is unsafe (~67 % chance of producing
    a different answer than dense)"
  - "subsequent same-question turns under cumulative cache stabilize
    to the cold-dense answer, but at no wall-clock speedup vs dense"
  - "rebuild-from-setup-per-turn delivers 28× speedup at content-
    conditional reliability; do not deploy on diverse-question
    streams"
- **Headline framing for §S6 / streaming section:** the
  ingestion-density claim ("more frames at fixed compute") on this
  stack reduces to: **streaming cache at the ViT-fire-rate level
  works** (per E3: 22–64× ViT-fire reduction at matched temporal
  coverage) **but cross-turn LLM cache reuse for follow-up Qs does
  not deliver matched-quality density gain on this stack**. The two
  cache levels (visual-feature reuse vs LLM-prefix reuse) should be
  reported as separate mechanisms with separate gains.
- **JF claim register:** `C-PERSIST` cell on `7B-4bit` Qwen
  (1.55F/I) is local-architecture-correct and unaffected by this
  finding. **The cell needs an explicit "architecture-conditional"
  flag stating that the claim does not transfer to mixed
  SWA + full-attention topologies under mlx-vlm 0.4.4.**
- **C-CEILING (jfb publishability-status round 26):** the speedup
  ceiling formula is silent on correctness; it predicts wall-clock
  multipliers given fixed-share assumptions. B2 shows that on this
  stack the formula's predictions are achievable (28× via fixed_k1)
  only at correctness costs. The **C-CEILING applicability
  envelope** for cross-arch deployment claims should include a
  "correctness preservation" precondition — without that, the
  predicted speedup may be hitting the wrong axis.

## Caveats

- **Diagnostic, not contractually conformant.** B2 was supposed to be
  skipped if B0b failed. Run anyway at user request.
- **`adaptive_post_prev_repaired` is an approximation** of the
  1.55F adaptive scheme — it uses the cumulative cross-turn cache
  rather than a real "post-Q2 repaired" cache wrapper. The local
  1.55F mechanism may behave differently.
- **N=3 videos × 50 turns × 3 arms = 450 rows.** Sample size is OK
  for the headline correctness numbers; bootstrap CIs not computed.
- **Same-question repeated polling.** B2 deliberately holds the
  question constant across turns. A diverse-question harness would
  exercise the bug more (each new question has a different answer
  to converge to). The B0b/B1 results suggest the bug fires per
  turn on diverse questions.
- **Wall-clock for `adaptive` arm.** As noted, adaptive's slowness
  is dominated by `PromptCacheState`'s cache-growth pathology, not
  the underlying model. A correct cumulative-cache deployment would
  prune the conversational tail per turn.

## Artifacts

- `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b2_many_turn_horizon.jsonl` (450 rows, schema-validated)
- `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b2_many_turn_horizon_summary.json`
- `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b2_many_turn_horizon.log`
- Runner: `scripts/run_sam_b2_many_turn_horizon.py`

## Cross-reference

- B0b findings (parent): `2026-04-29-phase-B0b-sam-cache-correctness-findings.md`
- B1 findings: `2026-04-29-phase-B1-sam-cpersist-replication-findings.md`
- E3 findings (sdamico, the throughput-axis pair to this finding): `sdamico/codec-through @ 6594a7b` -- `research/2026-04-26-e3-sectional-scroll-walltime/findings.md`
- Handoff contract: `2026-04-29-sam-scaleout-handoff.md` § B2
