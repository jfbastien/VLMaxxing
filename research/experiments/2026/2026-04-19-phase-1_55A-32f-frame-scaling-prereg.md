# Phase 1.55A-32f — Persistent-KV frame-scaling third point (PREREG)

**Status:** preregistration, 2026-04-19. Extension of 1.55A 8f/16f
landings (47.23× and 91.06× respectively) to a third frame count.

**Parents:**
- 8f findings: `2026-04-19-phase-1_55A-persistent-kv-findings.md`
- 16f findings: `2026-04-19-phase-1_55A-16f-frame-scaling-findings.md`

## Purpose

The 8f + 16f linear scaling gives us a beautifully clean 2-point
mechanism-confirming dataset:

| | 8f | 16f | Scaling |
|---|---|---|---|
| First-query median | 38.5 s | 73.5 s | 1.91× |
| Follow-up median | 815 ms | 807 ms | 0.99× |
| Speedup | 47.23× | 91.06× | 1.93× |

A third point at 32f tests whether the linear trend continues or
breaks at a higher prefill. Possible break mechanisms:

1. **Memory allocator cliff** — at 32f prefill ~13k tokens, the KV
   cache may push the allocator into a different regime (paging,
   bucket rebalancing). We already know 1.41 32f works at 8.5 GB
   RSS, so this is unlikely but worth verifying.
2. **Prefix-matcher overhead** — at 13k prefix tokens, `find_prefix_
   length` scan time may become measurable for follow-ups.
3. **Decode time grows with position** — if per-token decode cost
   scales with KV cache size, follow-up time could creep up from
   ~807 ms.

If the trend is linear, we get a **3-point scaling curve** for the
paper plus a testable extrapolation ("on 64f, speedup ~360×").

## Hypotheses

**Protocol:** identical to 1.55A 8f/16f. Only change: `--frame-count 32`.

Expected prefill at 32f: ~13k tokens (based on 1.41 32f run).

### H1'' — speedup continues linear scaling

**Prediction.** Follow-up speedup in band [**130×, 220×**]. Midpoint
175× ≈ 16f value × (32/16) × safety. Lower bound 130× ≈ linearity
requires ~70% of the 16f→32f prediction. Upper bound 220× allows for
the possibility that longer first-query has slightly super-linear
prefill time.

**Falsifies mechanism if:** speedup < 130× — would indicate a non-
prefill cost floor in first-query that saturates as prefill grows
(e.g. per-layer fixed overhead dominates at high prefill).

### H2'' — follow-up latency stays sub-2s at 32f

**Prediction.** Median follow-up latency ≤ **2000 ms** at 32f.
Rationale: decoded suffix is still 40-90 tokens. Added cost is the
longer `find_prefix_length` scan (~13k vs ~6.5k tokens, so ~2× scan
time) and potentially a longer position-aware KV access time.

**Band:** [500 ms, 2000 ms]. If follow-up exceeds 2000 ms, the
"conversational" deployment narrative needs a prefill-budget caveat.

### H3'' — prefix coverage stays ≥ 0.90

**Prediction.** Mean prefix coverage ≥ 0.90 (same as H3, H3').
Mechanism unchanged.

### H4'' — peak RSS stays under 12 GB

**Prediction.** Peak RSS ≤ **12 GB**. The 1.41 32f single-query run
hit 8.5 GB; adding a KV cache for a second query threading could add
~1.5 GB per clip. Budget headroom vs the 16 GB machine ceiling.

## Scoring

Identical to 1.55A 8f/16f. All four H'' earn requires all four
thresholds met.

## Runtime budget

Expected: ~35 min × 2 (32f prefill ≈ 2× 16f prefill) = ~70 min
session+baseline. If actual exceeds 2 hours, abort and investigate.

## Pre-registered decisions

| Outcome | Decision |
|---------|----------|
| All 4 H'' earn with linear trend | Paper gets 3-point scaling curve; claim #14 publishes with confirmed extrapolation to long-context scenarios |
| H1'' rejects low (speedup < 130×) | Mechanism saturates at large prefill; investigate first-query cost decomposition (prefill vs non-prefill) |
| H1'' rejects high (speedup > 220×) | Surprise — investigate; might mean prefix-hit eliminates costs beyond prefill itself |
| H2'' rejects | Deployment narrative needs prefill-budget caveat |
| H4'' rejects | Memory-pressure evidence; paper scopes claim #14 to ≤16f prefill |

## What this does NOT test

- Medium/long bucket (video-duration effects are orthogonal)
- Gemma path (deferred per 1.55A scope)
- 1.55B decode-accel composition (separate prereg)
