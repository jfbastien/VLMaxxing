# the pre-release source vs Ours — The Regime Gap That Explains the 1.8× vs 1.23× Speedup

**Status:** analysis note 2026-04-18, task #104.

This note makes the regime mismatch between the pre-release source's reference
configuration and ours explicit, so future comparisons don't treat
"1.8× vs 1.23× e2e" as an apples-to-apples headline gap.

## One-sentence summary

the pre-release source runs a **26B-class model on 32 frames** and reports a
**prefill-dominated** 1.8× e2e speedup; we run a **4B-class model on
8 frames** and measure 1.23× e2e at kr=0.10 — the gap is partially
regime, not mechanism.

## The two regimes side-by-side

| dimension             | the pre-release source's reference            | Ours (1.51R)               |
|-----------------------|----------------------------|----------------------------|
| Model                 | Gemma-3 27B / 26B-class    | Gemma 4 E4B 4bit MLX       |
| Frames                | 32                         | 8                          |
| Tokens / frame        | 256 (assumed same geometry)| 256 (runtime-verified)     |
| Total visual tokens   | ~8192                      | 2048                       |
| Reported e2e speedup  | 1.8×                       | 1.23× aggregate at kr=0.10 |
| Measurement regime    | Prefill / streaming        | Strict end-to-end wall clock |
| Budget scope          | Budget on prefill time     | Budget includes D+P+V+G    |

## Why the regimes push the ceiling in opposite directions

The arithmetic ceiling (task #88) binds e2e speedup according to how
much fixed cost D+P+V there is relative to generate G:

```
e2e ≤ (D + P + V + G) / (D + P + V + G/s)
```

where s is the per-token generate speedup. Fix s; then larger G-vs-
fixed-cost ratios push the ceiling higher.

**the pre-release source's regime shifts the ratio upward along three axes:**

1. **32 frames vs 8 frames** → 4× more prefill tokens. At the same
   TPS, prefill time grows ~4×, so G grows relative to fixed
   vision-tower cost V (which scales with frames but sublinearly
   because V is per-frame vs the prefill which stacks tokens and
   amplifies attention).
2. **26B-class vs 4B-class model** → per-token generate cost is
   ~6× higher. Generate time grows faster than fixed costs
   (tokenizer, decode, processor) that don't scale with parameter
   count. G dominates fixed cost more.
3. **Prefill / streaming measurement** → the pre-release source may exclude some of our
   D+P+V from the denominator. Streaming servers frequently report
   TTFT-like metrics that net out fixed decode/upload costs that we
   include in our strict e2e.

**Our regime shifts the ratio downward:**

1. 8 frames → small prefill relative to fixed costs.
2. 4B model → fast generate per token, so cutting prefill tokens
   saves less wall-clock.
3. Strict e2e with a CPU FFmpeg decode path → decode is 66.9% of
   aggregate e2e on 1.51R Stage 2b, 85.7% on long-bucket items.

## Concrete ceiling arithmetic at both regimes

Ours (measured 2026-04-18, Stage 2b aggregate n=30 at kr=0.10):
- D+P+V = 71.4% of e2e
- Ceiling at observed s=6.83 → e2e ≤ 1.213× (observed 1.229×)
- Ceiling at s=∞ → e2e ≤ 1.462×
- 1.8× is arithmetically unreachable without shrinking D+V.

the pre-release source's regime (unmeasured on our stack — projection only):
- If 32 frames shift the prefill share from 29% to, say, 70%, then
  D+P+V drops to 30%.
- Ceiling at observed s=6.83 would be ~1.78× (aligns with the pre-release source's 1.8×).
- If so, the 1.8× is not a mechanism difference but a regime
  difference; the same mechanism in the same regime on our stack
  would reproduce it.

This projection is the **testable prediction** that motivates Stage 6
(task #106): run 1.51R at 32 frames on a few long-bucket items and
see where e2e lands. If it clears 1.5× we've closed most of the
headline gap via regime; if it doesn't, there's a residual
mechanism difference.

## Consequences for paper framing

**Do not compare 1.8× vs 1.23× as mechanism evidence.** The two
numbers are measured in different regimes. The honest claim is:

> On our 8-frame / 4B / strict-e2e regime, 1.51R clears 1.23× e2e at
> kr=0.10 with -10pp aggregate accuracy (0.30 vs 0.40 dense), with
> medium-bucket items preserving accuracy at 2.71× generate speedup.
> The arithmetic ceiling at this regime is 1.46× (s=∞). the pre-release source's 1.8×
> on 32-frame / 26B / prefill-measured is consistent with a higher
> ceiling at that regime, not a mechanism gap; a regime-match pilot
> at 32 frames (Stage 6, task #106) is the direct test.

**Two legitimate paper narratives:**

1. **Headline-matched (requires Stage 6 confirmation):** "at the pre-release source's
   regime our 1.51R reproduces 1.8×; the mechanism works."
2. **Regime-honest (works today with landed evidence):** "at our
   regime 1.51R clears 1.23× e2e bounded by an arithmetic ceiling
   at 1.46×; the medium-bucket slice is an earned win. The 1.8× gap
   vs the pre-release source is a regime-measurement issue; a future 32-frame lane
   closes it."

Both are publishable. Narrative 1 is stronger if Stage 6 lands in
time; narrative 2 is the fallback and does not require any new
experiments.

## References

- `research/experiments/2026/2026-04-18-arithmetic-ceiling-findings.md`
- `research/experiments/2026/2026-04-18-phase-1_51R-stage5-cross-arm-synthesis.md`
- pre-release seed pre-release source import, removed from the OSS tree and summarized
  in `docs/claim-register.md` (the pre-release source's 1.8× figure)
- `docs/literature-map-2026-04-16.md` — FlashVID / FastVID rows report
  prefill-speedup, same regime asymmetry as the pre-release source's
