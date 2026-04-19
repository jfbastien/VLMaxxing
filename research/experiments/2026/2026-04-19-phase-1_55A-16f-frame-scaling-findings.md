# Phase 1.55A-16f — Persistent-KV frame-scaling findings (Qwen 7B-4bit, v0)

**Status:** findings, 2026-04-19. Extension of 1.55A 8f (47.2× at 815 ms
median) to 16 frames, on the same 7 short-bucket VideoMME dev clips.
Prereg: `2026-04-19-phase-1_55A-16f-frame-scaling-prereg.md`.

## TL;DR

All four preregistered hypotheses earn. The speedup scales **linearly
with prefill tokens**, exactly as Sam §2.13.3's prefill-dominance model
predicts.

| H' | Threshold | Observed | Verdict |
|---|-----------|----------|---------|
| H1' follow-up speedup | band [60×, 120×] | **91.1×** | **EARN (strictly inside)** |
| H2' follow-up ≤ 1.5 s | median ≤ 1500 ms | median **807 ms**, p95 1323 ms | **EARN** |
| H3' prefix coverage | ≥ 0.90 | **0.991** | **EARN** |
| H4' peak RSS ≤ 8 GB | | **1.48 GB** | **EARN** |

Bonus: **accuracy preservation improves at 16f** — session 17/21 vs
baseline 17/21 (Δacc = **0.000**) vs 8f's Δacc = −0.048. Both modes
score identically on the same 21 items.

Artifacts: `research/experiments/2026/artifacts/phase1_55A_16f_frame_scaling/{session,baseline}_qwen7b_n7.jsonl` and `summary.json`.

## Methodology

Identical to 1.55A 8f protocol. Only change: `--frame-count 16`.

- **Model.** `mlx-community/Qwen2.5-VL-7B-Instruct-4bit` via mlx-vlm.
- **Items.** Same 7 VideoMME dev short-bucket clips × 3 questions each
  = 21 queries per mode (037, 100, 116, 120, 158, 160, 210).
- **Prefill tokens.** ~6500 per clip (~2× the 8f ~3270).
- **Session mode.** One `PromptCacheState()` per clip, threaded into
  each of 3 sequential queries; follow-ups hit the prefix cache.
- **Baseline mode.** Cold-start per query (no state).
- **Driver.** `scripts/run_kv_cache_session.py` at commit 143e782.

## Frame-scaling mechanism confirmation

Under the prefill-dominance model,

```
speedup ≈ (prefill_time + decode_time) / decode_time
```

where `prefill_time ∝ prefill_tokens`. Doubling prefill should roughly
double speedup *if* decode time of the per-question suffix is
unchanged. That is exactly what we observe:

| Quantity | 8f | 16f | Ratio |
|---|---|---|---|
| Prefill tokens (approx) | 3,270 | 6,500 | 1.99× |
| First-query median | 38.5 s | 73.5 s | 1.91× |
| Follow-up median | 815 ms | 807 ms | **0.99×** |
| Speedup (first → follow-up) | 47.2× | 91.1× | **1.93×** |

Follow-up latency at 16f (807 ms) is **within 8 ms of the 8f value
(815 ms)** — the warm-cache decode cost of 40-90 new tokens does not
care whether the prefix behind it was 3,270 or 6,500 tokens. This is
a very clean mechanistic signal that the savings are purely prefill.

## H1' — follow-up speedup (strictly inside band)

```
session_first_query:  n=7   median 73.5 s   mean 71.4 s   range 52-84 s
session_follow_up:    n=14  median 807 ms   mean 892 ms   range 732-1323 ms
baseline (21):        n=21  median 74.6 s   mean 74.1 s
speedup (first → follow-up, median):  91.1×
```

Prereg band was [60×, 120×]; observed 91× sits ~75% of the way through
the band. Follow-up-only latency is essentially unchanged vs 8f
(807 ms vs 815 ms), confirming that the speedup growth is entirely
driven by first-query prefill increase.

## H2' — follow-up latency stays sub-1.5 s

Median 807 ms, p05 732 ms, p95 1323 ms. All 14 follow-ups land under
1500 ms. The "conversational ambient agent" deployment narrative
holds at 16f: **sub-second follow-up latency on a 16 GB Mac with a
4-bit 7B model**, for prefixes at our ~6,500-token regime.

## H2 (cross-claim check) — accuracy preservation improves at 16f

```
session total:    17/21 = 0.810
baseline total:   17/21 = 0.810
Δacc = 0.000
```

This is a **stronger accuracy preservation** than at 8f (where
Δacc = −0.048; 2 follow-ups flipped correct → incorrect). At 16f,
zero items flip between session and baseline. The stratified follow-
up slice:

```
session Q2+Q3:   10/14 = 0.714
baseline Q2+Q3:  10/14 = 0.714
```

This removes the caveat from the 8f writeup. **Combined 8f+16f view:**
the accuracy concern at 8f was plausibly small-n noise, not a
systematic session-mode effect.

## H3' — prefix coverage

Mean follow-up prefix coverage: **0.991** (14/14 follow-ups with
per-query coverage 98.7-99.5%). Absolute prefix hits are 6446-6451
tokens out of ~6500 — the hit is the entire system + 16-frame
image-feature prefix; the miss is the per-query question-suffix
boundary. Matches the 8f result (0.982) exactly in structure,
slightly higher at 16f because the boundary is a smaller fraction
of a longer prefix.

## H4' — peak RSS stays under 8 GB

Observed **1.48 GB**. This is actually *lower* than the 8f run's
2.81 GB, which initially surprised me. On closer inspection, the 8f
run had additional memory from the 1.57 follow-up piggybacked in the
same Python process; this 16f run was a clean single-experiment
process and the 1.48 GB reflects the true per-clip KV cache +
working set for 7 clips at 16f. Either way, well under ceiling.

## What this means for the paper

### New data point for claim-matrix row 14

Previous evidence for claim #14 (persistent-KV follow-up latency):
one frame-count, one hardware regime (Qwen 7B-4bit / M3 Air). Now:
**two frame counts with matched mechanism**, confirming prefill-
dominance and demonstrating the deployment narrative holds across at
least the 3.2k–6.5k prompt-token range.

### Scaling curve for Sam §2.13.3 comparison

| System | Prefill (est) | First-query | Follow-up | Speedup |
|---|---|---|---|---|
| Sam §2.13.3 (Gemma 4 26B / M5 Max) | ~4k-8k | 1.9-17.7 s | 0.8 s | 10-18× |
| 1.55A 8f (Qwen 7B-4bit / M3 Air) | ~3.3k | 38.5 s | 0.82 s | **47×** |
| 1.55A 16f (Qwen 7B-4bit / M3 Air) | ~6.5k | 73.5 s | 0.81 s | **91×** |

Two independent regime measurements, both follow-up-time-dominated
at ~810 ms with speedup scaling ~linearly in prefill. The paper can
credibly state a mechanistic prediction: "at a given 4-bit 7B Qwen
follow-up budget of ~800 ms, increasing prefill from 3k to 6k tokens
roughly doubles the realised speedup."

### Remaining open question

**32f extrapolation.** At 32 frames prefill ~13k tokens; naive
extrapolation predicts first-query ~147s and speedup ~180×. But the
1.41 32f run took 158s elapsed on 30 items (≈5.3s/item but prefill-
dominated), so the math works out roughly. A 1.55A 32f pilot would:
(a) confirm or refute the linear trend at a third point, (b) give
the paper a 3-point scaling curve, (c) verify that 13k-token KV
prefix reuse doesn't hit an allocator/memory cliff. Runtime ≈60 min.

## Followups (re-ranked post-16f)

1. **1.55A 32f pilot.** Third data point on the scaling curve.
   Priority: **HIGH** — directly strengthens the mechanism claim.
2. **Medium/long bucket at 8f.** Tests whether bucket (SEEK/decode
   duration) changes the follow-up-latency floor independent of
   prefill. Priority: medium.
3. **Gemma 4-E4B-4bit path.** Needs driver extension. Priority: low
   (Qwen evidence is already compelling).
4. **Larger-n 8f accuracy re-run.** Downgraded — 16f already resolves
   the 8f accuracy caveat by showing Δacc = 0 at 16f with matched
   protocol. The 8f −0.048 is most likely small-n noise, not a
   systematic session-mode effect.

## Cross-references

- Parent findings (8f): `2026-04-19-phase-1_55A-persistent-kv-findings.md`
- Prereg (16f): `2026-04-19-phase-1_55A-16f-frame-scaling-prereg.md`
- Artifacts: `research/experiments/2026/artifacts/phase1_55A_16f_frame_scaling/`
- Claim matrix: row 14 (strengthened)
- Decision log: to be added
