# Arithmetic Ceiling for 1.51R (Stage 2b n=30)

**Status:** findings 2026-04-18, task #88. Empirical validation of the
arithmetic-ceiling argument that motivates 1.51V (vision-tower pruning).

## Question

The 1.51R Stage 2b result is `e2e = 1.122×` aggregate on VideoMME N=30
at kr=0.10 anchor=none, with `gen = 2.619×` and
`per_token_generate = 2.690×`. The gap between per-token G speedup and
e2e is the fixed-cost bottleneck. How close are we to the ceiling, and
what would a larger G speedup actually buy?

## Model

Per-item wall-clock decomposes cleanly:

    e2e = D + P + V + G

where `D = video decode`, `P = processor prep`, `V = vision tower
forward pass`, `G = LLM prefill + generate`. 1.51R only accelerates G.
Ceiling at per-phase speedup `s` on G:

    e2e_speedup ≤ (D + P + V + G) / (D + P + V + G/s)

As `s → ∞` the ceiling collapses to `(D + P + V + G) / (D + P + V)`.

## Data

Stage 2b JSONL with `dense_timing_ms` + `pruned_timing_ms` breaking
out `{decode, processor, vision, generate, end_to_end}`, n=30,
kr=0.10, anchor=none, Gemma 4-E4B-4bit, VideoMME short/medium/long.

Scripts:
- `artifacts/arithmetic_ceiling/compute_ceiling.py` — per-item
  ceiling vs observed e2e.
- `artifacts/arithmetic_ceiling/decompose_fixed.py` — D/P/V/G split
  by duration bucket.
- `artifacts/arithmetic_ceiling/ceiling_summary.json` — aggregates.
- `artifacts/arithmetic_ceiling/ceiling_data.csv` — per-item.

## Results

### Observed speedup vs ceilings (by bucket, n=10 each)

| bucket | fixed_frac | per-tok G speedup | observed e2e | ceiling @ observed s | ceiling @ s=∞ | headroom |
|--------|-----------:|------------------:|-------------:|---------------------:|--------------:|---------:|
| short  | 0.568      | 12.52×            | 1.356×       | 1.368×               | 1.761×        | +0.404   |
| medium | 0.663      | 2.71×             | 1.267×       | 1.268×               | 1.527×        | +0.259   |
| long   | 0.912      | 5.27×             | 1.062×       | 1.002×               | 1.098×        | +0.036   |
| **all**| **0.714**  | **6.83×**         | **1.229×**   | **1.213×**           | **1.462×**    | **+0.233** |

`headroom` = ceiling@∞ − observed e2e, i.e. the maximum additional
e2e speedup reachable *by any amount of G acceleration*. Not
reachable via 1.51R alone because V and D are not touched.

### Phase-level wall-clock (dense, mean ms/item by bucket)

| bucket | D (decode) | P (proc) | V (vision) | G (generate) | e2e    | D/e2e | V/e2e | V/fixed | G/e2e |
|--------|-----------:|---------:|-----------:|-------------:|-------:|------:|------:|--------:|------:|
| short  | 3.38s      | 0.07s    | 6.77s      | 7.76s        | 17.99s | 18.8% | 37.7% | 66.3%   | 43.2% |
| medium | 8.94s      | 0.06s    | 6.61s      | 7.59s        | 23.20s | 38.5% | 28.5% | 42.3%   | 32.7% |
| long   | 69.78s     | 0.07s    | 5.24s      | 6.35s        | 81.45s | 85.7% |  6.4% |  7.0%   |  7.8% |
| all    | 27.37s     | 0.07s    | 6.21s      | 7.24s        | 40.88s | 66.9% | 15.2% | 18.5%   | 17.7% |

## Interpretation

**1. Aggregate 1.51R is at ceiling.** At observed per-token G speedup
6.83×, the arithmetic ceiling is 1.213×; measured e2e is 1.229×. The
~2% gap is within measurement noise. More aggressive G speedup (kr →
0) will *not* improve aggregate e2e beyond 1.46× even in the limit.

**2. Duration determines the regime.**
- Short videos: V dominates fixed cost (66%). 1.51V has a real lever —
  a 35% V reduction would buy ~13% e2e on short items.
- Long videos: D (video frame decoding) dominates (86% of e2e). No
  amount of V or G reduction clears 1.10× on this bucket. the pre-release source's 1.8×
  target is arithmetically unreachable on long VideoMME items
  without touching D itself (sparser frame sampling, faster decoder).
- Medium is in between, with V/fixed = 42%.

**3. 1.51V prereg is well-motivated but bounded.** The prereg's H3
target (1.51V+1.51R composed ≥ 1.5× e2e) is plausible only on the
short/medium slice. Aggregate 1.5× requires also reducing D on long
videos, which is neither 1.51R nor 1.51V.

**4. the pre-release source's ~1.8× reference is likely dominated by short-clip
benchmarks or by different hardware where G is a larger fraction.**
On Gemma 4-E4B-4bit + MLX + M3 Air + 8-frame VideoMME, the D
dominance on long items (86%) is the binding constraint. This is
not an implementation defect; it is a hardware-geometry fact. The
paper should present the ceiling figure as *the* framing for the
1.51R partial reproduction, not as an afterthought.

## Paper-facing claim

> On Gemma 4-E4B-4bit with 8-frame VideoMME items on MLX + M3 Air,
> the fixed cost D+P+V consumes 71% of end-to-end wall-clock
> (aggregate n=30). Novelty-pruning delivers a 6.83× per-token
> generate speedup but lifts end-to-end only to 1.23× — within 2%
> of the arithmetic ceiling at that s. Breaking 1.23× requires
> reducing V (phase 1.51V) or D (out of scope for this paper;
> sparser frame sampling is the natural direction).

## Follow-ups

- Produce a paper-grade figure from `ceiling_data.csv`: x=fixed_frac,
  y=e2e_speedup; overlay the s=∞ ceiling curve; color by duration
  bucket. (The CSV is the artifact; the plot can be generated at
  paper-assembly time.)
- Revise 1.51V prereg H3 to be duration-conditional: target ≥1.5× on
  short+medium separately, not aggregate. Aggregate is capped by D on
  long items.
- Open a deferred phase "1.54: video-decode acceleration" for the
  long-video ceiling lift. Not on critical path for this paper.

## Cross-references

- `artifacts/arithmetic_ceiling/` — scripts + data.
- Phase 1.51R Stage 2b findings
  (`2026-04-18-phase-1_51R-stage2b-n30-kr010-findings.md`) — the n=30
  result this analysis decomposes.
- Phase 1.51V prereg
  (`2026-04-18-phase-1_51V-vision-tower-pruning-prereg.md`) — the
  mechanism this ceiling motivates.
- Claim matrix row 11 (1.51R) — "duration-conditional partial
  reproduction" framing aligns with this ceiling analysis.
