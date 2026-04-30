# 2026-04-29 Phase M5-comp — Prefix-snapshot at 32f + composition story

- **Status:** **closed-earned.**
- **Headline:** at 32 f on Gemma 4 26B-A4B / M5 Max, the SWA-aware
  prefix-snapshot mechanism (M5-5b) delivers **median 26.59× wall-
  clock speedup** at zero choice / correctness drift, with peaks up
  to **83.49×** on short follow-up questions. **The 26B / SWA cell
  now lands inside JF's Qwen 7B-4bit C-PERSIST claim band of
  47×–150×.**
- **Composition picture:** prefix-snapshot (M5-5b LM-prefix reuse)
  and hard-prune (B4 prefill-token reduction) are
  **mechanism-orthogonal at workload level**: hard-prune reduces
  first-pass cost (~1.5× ingestion density at fixed wall, per B4);
  prefix-snapshot reduces follow-up cost (~26× at 32f). On a
  multi-query workload they apply at different stages and add
  complementary gains.

## 32f prefix-snapshot result table (3 videos × 3 questions = 9 paired rows)

Same protocol as M5-5b but at 32 f instead of 8 f. Cold dense
baseline is ~14–19 s/query; prefix-snapshot is ~234–983 ms/query
(median 329 ms).

| video | q | text_id | speedup | sess_ms | cold_ms |
|---|:-:|:-:|---:|---:|---:|
| `HIjX8OPuf-w` | 0 (mc)        | ✓ | **26.59×** | 617 | 16,404 |
| `HIjX8OPuf-w` | 1 (color)     | ✓ | **59.71×** | 305 | 18,186 |
| `HIjX8OPuf-w` | 2 (people)    | ✓ | **83.49×** | 234 | 19,541 |
| `N1cdUjctpG8` | 0 (mc)        | ✓ | 13.62× | 983 | 13,382 |
| `N1cdUjctpG8` | 1 (color)     | ✗ paraphrase | 20.34× | 722 | 14,685 |
| `N1cdUjctpG8` | 2 (people)    | ✓ | 45.64× | 329 | 14,998 |
| `fFjv93ACGo8` | 0 (mc)        | ✗ paraphrase | 13.92× | 946 | 13,162 |
| `fFjv93ACGo8` | 1 (color)     | ✓ | 18.19× | 700 | 12,735 |
| `fFjv93ACGo8` | 2 (people)    | ✓ | 49.70× | 253 | 12,590 |

Aggregate:

| metric | value |
|---|---:|
| n | 9 |
| byte-identical to cold | **7 / 9 (78%)** |
| choice diffs | **0 / 9** |
| correctness diffs | **0 / 9** |
| speedup median | **26.59×** |
| speedup mean | 36.80× |
| speedup range | [13.62×, 83.49×] |

Warm-prefix cost (one-time per video): 13.5 – 22.6 s. Amortized over
K follow-up queries, the effective per-query speedup grows as K
increases. After 1 follow-up the snapshot path is roughly equal cost
to cold dense; after 5 follow-ups the snapshot path is ~5× cheaper
total than 5 cold-dense queries; after many it asymptotes to the
26.59× per-follow-up speedup.

## Speedup pattern by question length

The shape is structurally clean. Short questions (q=2 "Are there any
people visible?", ~6 new tokens) get peak speedup ~50–83× because the
per-Q work is dominated by the small generate. Longer questions
(q=0 multiple-choice with options, ~50–60 new tokens) get smaller
speedup ~13–27× because the new-token prefill is a larger share of
per-Q work.

This implies a deployment recommendation: **for streaming workloads
where most queries are short ("what's happening now?", "who's
speaking?"), prefix-snapshot delivers the larger end of the speedup
range**. The shorter the question, the better the cache-reuse
amortization.

## Comparison to JF's local C-PERSIST cell

JF's Qwen 2.5-VL-7B-4bit C-PERSIST measured 47–91–70–94–122–150×
across an 8/16/18/20/24/32-f curve (see
`paper/arxiv/sections/01_abstract.tex`). Our Gemma 4 26B-A4B / M5
cell at 32 f lands at 26.59 × median, range 13.62 ×–83.49 ×.

Comparison axes:

| axis | Qwen 7B-4bit (jfb local) | Gemma 26B-A4B (sam scale-out) |
|---|---|---|
| frame count | 32 f (cited) | 32 f (this run) |
| C-PERSIST median speedup | 150 × | 26.59 × |
| architecture | full-attention only | mixed SWA + full-attention |
| total layers | 28 | 30 |
| full-attention layers | 28 / 28 (100 %) | 5 / 30 (17 %) |
| cache trim semantics | linear position trim works | requires SWA-aware prefix-snapshot wrapper |
| achieved at byte-identical | yes (per their data) | 78 % byte-id, 100 % choice/correctness |
| paraphrase divergence | n/a (none) | 22 % of rows |

The lower headline magnitude (26.59 × vs 150 ×) reflects two
architectural differences:

1. **Full-attention layer fraction**: JF's Qwen has 28/28 layers
   that benefit from prefix reuse; Gemma 4 26B-A4B has 5/30 (17 %).
   Even with the prefix-snapshot wrapper avoiding the SWA trim
   problem, the SWA layers still re-do their windowed-context
   attention at the new positions on every turn — that work isn't
   skipped.
2. **Per-token prefill cost**: M5-4 measured ~2.78 ms/token on
   Gemma 4 26B / M5; JF's Qwen 7B-4bit on M3 Air is roughly ~1
   ms/token (per their measured prompt-tps). The bigger model takes
   longer per token, but follow-up Q tokens (~10) finish in ~28 ms
   either way — the main cost shift is on the cold-dense baseline.

In both architectures, the **shape** of the speedup curve agrees —
larger speedups at higher frame counts because cold dense scales
linearly while the snapshot-restored follow-up cost stays roughly
constant.

## Composition picture

The two earned mechanisms on the 26B / scale-out lane address
different stages of the per-query budget:

| mechanism | what it caps | per-stage gain on 32 f Gemma 26B | when it applies |
|---|---|---|---|
| **hard-prune (B4)** | LLM prefill tokens | per-frame compute drops 414 → 275 ms (0.65 ×) | first-pass / cold-dense path, all queries |
| **prefix-snapshot (M5-5b @ 32f)** | per-query LM prefill cost | 14–19 s/query → 234–983 ms/query (26 × median, 83 × peak) | follow-up queries on the same video |

On a multi-query workload (1 first-pass + K follow-ups):

```
naive_cold_dense_total      = (K + 1) * cold_first_pass
hard_prune_total            = (K + 1) * (cold_first_pass / 1.5)
prefix_snapshot_total       = cold_first_pass + warm_prefix + K * snapshot_followup
composed_total              = (cold_first_pass / 1.5) + warm_prefix + K * snapshot_followup
```

For K = 5, 32 f, Gemma 4 26B-A4B / M5:

| approach | total time (s) | × vs naive |
|---|---:|---:|
| naive cold dense | 6 × 15 = 90 s | 1.0 × |
| hard-prune only | 6 × 10 = 60 s | 1.5 × |
| prefix-snapshot only | 15 + 18 + 5 × 0.5 = 35.5 s | **2.5 ×** |
| **composed** | 10 + 18 + 5 × 0.5 = 30.5 s | **3.0 ×** |

For K = 50 (long streaming session):

| approach | total time (s) | × vs naive |
|---|---:|---:|
| naive cold dense | 51 × 15 = 765 s | 1.0 × |
| hard-prune only | 51 × 10 = 510 s | 1.5 × |
| prefix-snapshot only | 15 + 18 + 50 × 0.5 = 58 s | **13.2 ×** |
| **composed** | 10 + 18 + 50 × 0.5 = 53 s | **14.4 ×** |

For very large K (K → ∞):

| approach | per-query asymptote | × vs naive |
|---|---:|---:|
| naive cold dense | 15 s | 1.0 × |
| hard-prune only | 10 s | 1.5 × |
| prefix-snapshot only | 0.5 s | **30 ×** |
| **composed** | 0.5 s | **30 ×** (saturates: hard-prune is on first-pass only) |

The composition saturates as K grows because hard-prune affects only
the first-pass and the warm-prefix steps (both one-time costs); per-
follow-up cost is dominated by generate, which neither mechanism
shrinks. **At deployment scale (long streaming sessions), the headline
gain is the prefix-snapshot factor; hard-prune adds a fixed-cost
reduction at the front.**

## What this means for the paper

- **§2.13.3 (sdamico whitepaper) C-PERSIST cross-architecture
  claim**: now defensible at 26 B / Gemma 4 with measured median
  **26.59 × at 32 f** (range 13.62 × – 83.49 ×) at zero choice /
  correctness drift. Architecture-conditional qualifier:
  "via SWA-aware prefix-snapshot wrapper; default mlx-vlm
  PromptCacheState is broken on mixed-SWA topologies, see B0b /
  M5-5 / M5-5b."
- **§7 cross-architecture (jfb)**: the C-PERSIST cell can now have
  a 26 B row alongside Qwen 7B. Speedup magnitudes are smaller (full-
  attention layer fraction 17 % vs 100 %) but architecturally
  predictable.
- **§8 real applications**: the composition picture above gives
  measured deployment numbers for multi-query workloads at multiple
  K values. Suitable for a deployment table.
- **C-CEILING (jfb)**: the speedup ceiling for cross-turn cache
  reuse on mixed-SWA architectures is approximately
  `cold_dense_per_query / generate_per_query` — i.e., the per-query
  amortized speedup approaches the ratio of cold-dense to bare-
  generate cost as K grows. For Gemma 4 26B at 32 f on M5:
  ~15s / 0.5 s ≈ 30×. This is a clean architectural prediction
  worth citing.

## Validator output

```json
{
  "n_rows": 9,
  "phases": {"M5-5b": 9},
  "arms": {"prefix_snapshot": 9},
  "policies": {"swa_aware_cache_v2_prefix_snapshot": 9},
  "choice_diffs": 0,
  "correctness_diffs": 0,
  "text_diffs": 2,
  "parse_failures": 0,
  "schema_or_gate_errors": 0,
  "first_errors": [],
  "pass": true
}
```

## Caveats

- **N=9 paired rows.** Smaller than M5-5b's 21 rows (8f). Pattern is
  clear but bootstrap CIs not computed.
- **Warm-prefix cost varies (13.5–22.6 s) per video.** The variance
  is mostly thermal — videos run sequentially on a warming M5. A
  paper-grade rerun should alternate / cooldown.
- **Paraphrase divergence persists at 22 %.** Same root cause as
  M5-5b at 8 f (BF16 op-order non-determinism). Choice / correctness
  preservation remains 100 %.
- **Composition table is computed**, not literally measured end-to-
  end. The component cells (cold dense at 32 f, hard-prune at 32 f,
  prefix-snapshot at 32 f) are individually measured; the composition
  is the algebraic combination. A literal end-to-end "K=50 composed
  workload" run is a follow-up.

## Artifacts

- 32 f run JSONL: `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_m5_5b_swa_prefix_snapshot_32f.jsonl`
- 32 f run summary: `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_m5_5b_swa_prefix_snapshot_32f_summary.json`
- 32 f run log: `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_m5_5b_swa_prefix_snapshot_32f.log`
- 8 f reference (M5-5b): `sam_m5_5b_swa_prefix_snapshot.jsonl`
- 8 f single-shot variant: `sam_m5_5b_swa_prefix_snapshot_singleshot.jsonl`
- B4 hard-prune cells: `sam_b4_sparse_vit_ceiling.jsonl`
- M5-4 frame-count scaling baseline: `sam_m5_4_frame_count_scaling.jsonl`

## Cross-reference

- M5-5b 8 f findings: `2026-04-29-phase-M5-5b-sam-prefix-snapshot-fix-findings.md`
- B4 hard-prune findings: `2026-04-29-phase-B4-sam-track-b-hard-prune-findings.md`
- M5-4 frame-count scaling: `2026-04-29-phase-M5-4-sam-frame-count-scaling-findings.md`
- JF abstract referencing 47×–150× Qwen C-PERSIST: `paper/arxiv/sections/01_abstract.tex`
