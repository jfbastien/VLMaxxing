# Phase 1.55A-16f — Persistent-KV frame-scaling follow-up (PREREG)

**Status:** preregistration, 2026-04-19. Extension of 1.55A 8f landing
(47.23× follow-up speedup, 815 ms median) to a second frame count.

**Parent findings:** `2026-04-19-phase-1_55A-persistent-kv-findings.md`
**Parent prereg:** `2026-04-19-phase-1_55A-persistent-kv-reproduction-prereg.md`

## Purpose

The 8f 1.55A run established the pre-release source §2.13.3 reproduces on Qwen 7B-4bit /
M3 Air with **first-query prefill ≈ 3270 tokens, follow-up decode ≈
40-90 tokens**. The speedup identity is:

```
speedup ≈ first_query_latency / follow_up_latency
       ≈ (prefill_time + decode_time) / decode_time
```

Under this model, **doubling prefill tokens should roughly double
speedup** (provided decode-time of the question suffix is unchanged).
This is a direct test of whether persistent-KV savings are prefill-
dominated as the pre-release source's mechanism claims, vs. dominated by some other
component (e.g. ViT feature extraction, kernel launch overhead).

## Hypotheses

**Protocol:** identical to 1.55A 8f — 7 short-bucket VideoMME dev
clips × 3 questions × 2 modes (session + cold-start baseline) = 42
queries. Only change: `--frame-count 16` instead of 8.

Expected prefill at 16f: ~6500 tokens (observed on 1.41 16f run).

### H1' — speedup scales roughly linearly with prefill

**Prediction.** Follow-up speedup ≥ 70× (median first-query / median
follow-up) at 16f. Rationale: 1.55A 8f earned 47.23× at ~3270-token
prefill. At 6500-token prefill, under the prefill-dominance model the
first-query time should ~double while follow-up time stays similar,
yielding roughly 2× speedup.

**Band:** [60×, 120×]. Lower bound 60× ≈ 1.3× the 8f measurement.
Upper bound 120× ≈ 2.5× the 8f measurement.

**Falsifies mechanism if:** speedup < 60× — would indicate non-prefill
cost floor in first-query (e.g. seek time on the video decoder) that
prevents speedup from scaling with prefill.

### H2' — follow-up latency stays sub-1.5s

**Prediction.** Median follow-up latency ≤ 1500 ms at 16f.
Rationale: the decode step is unchanged (~40-90 new tokens). The only
cost added at 16f to follow-up is a larger `find_prefix_length` scan
(6500 vs 3270 tokens), which should still be <200 ms.

**Band:** [500 ms, 1500 ms]. If follow-up latency exceeds 1500 ms, the
"conversational ambient agent" deployment narrative weakens at 16f
resolution.

### H3' — prefix coverage stays ≥ 0.90

**Prediction.** Mean follow-up prefix coverage ≥ 0.90 (matched to
parent H3). The mechanism is identical — only the prefix length
changes. If this fails at 16f, it means mlx-vlm's prefix matcher
drops performance at longer prefixes, which would be independently
worth reporting.

### H4' — peak RSS stays under 8 GB

**Prediction.** Peak RSS ≤ 8 GB (matched to Qwen 1.41 16f run
baseline; 1.55A 8f was 2.81 GB).

## Scoring

Identical protocol, driver, scorer as 1.55A 8f. All four H earn
requires all four thresholds met.

## Runtime budget

8f session+baseline was 1060 s. 16f prefill ~2× longer → expect
session+baseline ~2100 s (~35 min). If actual exceeds 3600 s, abort
and investigate.

## Pre-registered decisions

| Outcome | Decision |
|---------|----------|
| All 4 H' earn | Append to 1.55A findings as "frame-scaling confirmed"; paper gets a scaling curve |
| H1' rejects low | Reopen the pre-release source §2.13.3 mechanism — prefill is not the dominant first-query cost at our regime |
| H1' rejects high | Report as surprise finding; investigate whether large prefix-hit reduces other first-query costs (e.g. KV cache allocation) |
| H2' rejects | Deployment narrative caveat: follow-up latency degrades with prompt length on Qwen 7B-4bit |
| H3'/H4' reject | Report; unlikely given 8f result |

## What this does NOT test

- Frame counts beyond 16 (would need 32f run to confirm linearity)
- Medium/long bucket (video-duration effects on SEEK cost are orthogonal)
- Gemma path (deferred per 1.55A scope)
- KV cache survival across non-trivial model-state changes (1.55B)
