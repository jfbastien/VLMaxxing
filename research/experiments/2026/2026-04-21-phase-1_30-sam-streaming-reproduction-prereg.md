---
phase: 1.30
date: 2026-04-21
parent: paper/priority.md (should-do #4)
prior:
  - research/experiments/2026/2026-04-16-phase-1_30-streaming-window-harness.md
  - research/experiments/2026/2026-04-19-phase-1_55A-persistent-kv-findings.md
  - research/experiments/2026/2026-04-21-phase-1_51V-expansion-findings.md
  - paper/whitepaper-revised-2026-04-16.md (§2.13.3, §5)
status: prereg (deferred — queued after EXP17/18 + EXP10 n=60 land)
---

# 1.30 Sam streaming/deployment-protocol reproduction — prereg

## Motivation (why round-24 promoted this to "biggest Sam bridge")

Codex round-24 identified that every local result in this repo is a
**phase-isolated** experiment: one benchmark, one frame-count, one
(L, kr) pair, one persistent-KV depth. Sam's whitepaper §5 describes
a **deployment-grade protocol** where these mechanisms compose across
a streaming client and where a reviewer would want to see an N=60
line matching Sam's reporting template:

> Video arrives frame-by-frame; the client runs a rolling pre-prefill
> queue with KV-cache reuse across consecutive queries on the same
> clip; selective re-prefill fires only at attention-context-drift
> boundaries; the decoder is co-located with the client.

We have the individual ingredients (1.51V vision-tower pruning at
L=2 kr_V=0.50, 1.55A persistent-KV replay with safe-prefill envelope,
1.49 refresh sweep to bound drift, 1.57 drift measurement as
lower-bound proxy) but we have **no integration experiment** that
runs them together on a benchmark we report on. This prereg closes
that gap by running the full stack on VideoMME 60-item (dev+holdout
union) paired with the cold baseline.

## Hypotheses (preregistered)

### H_sam_e2e (primary)

**Paired within-run E2E speedup (cold-baseline vs streaming-stack)
≥ 3.0× on VideoMME 60-item union at 8f, with acc Δ ∈ [−0.05,
+0.05].**

Rationale: 1.51V ceiling alone predicts 1.06–1.24× on VideoMME
8f (V_share=15.2% × V_red=39.0% = 1.064×, before LLM-side composition).
Adding persistent-KV reuse on follow-up queries lifts that to 47×–91×
on the follow-up path per 1.55A; amortized over a realistic
query-per-clip distribution (assume 3 queries per clip, 1 first-query
+ 2 follow-ups), expected amortized e2e is approximately:
`(1 × first_query_e2e + 2 × follow_up_e2e) / (3 × cold_e2e)` — with
follow_up_e2e ≈ 0.8 s (Sam line) and cold_e2e ≈ 40 s (VideoMME 8f
dense on M3 16GB), the amortized e2e is ~14× on 3-query clips. The
H_sam_e2e ≥ 3.0× threshold is a conservative lower bound that
accommodates (a) first-query overhead dominating short clips, (b)
drift-triggered re-prefill cost on longer clips, (c) per-item variance.

**Failure condition:** amortized e2e < 1.5× — would falsify the
composition-of-mechanisms argument on VideoMME and indicate that
per-clip overhead swamps per-query wins at this scale.

### H_sam_bucket (primary)

**Sam's "clean / mixed / degenerate" bucket distribution
reproduces locally with clean-bucket fraction ≥ 0.50 and
degenerate-bucket fraction ≤ 0.15** across the 60-item × 3-queries
stream.

Sam's §5 deployment table reports per-item bucket tallies for his
26B/M5 Max setup. A local reproduction that does not hit comparable
bucket shares on the same VideoMME manifest (adjusted for our 4B/M3
setup — expect higher degenerate share if 7B basin collapse triggers
at our prefill depths) would indicate the protocol is not transferring.

### H_sam_drift_refresh (secondary)

**Drift-triggered re-prefill fires on ≤ 30% of follow-up queries
AND reduces degenerate-bucket share by ≥ 50% vs a no-refresh baseline
on the same 60 items.**

This tests whether the 1.49 refresh sweep's "refresh at attention-
context-drift boundary" heuristic transfers to the streaming setting.
If refresh fires too often (> 30%), we lose the persistent-KV
speedup; if it fires too rarely, degenerate-bucket share will not
drop.

### H_sam_thermal (process)

**Decode Δ across cold vs streaming stack: |decode_ms(streaming) −
decode_ms(cold)| / decode_ms(cold) < 2%.**

Same invariant as 1.51V pairs. 60-item runs take ~90 min per arm,
so this is the first pair where thermal drift across a 3-hour
session-duration matters. If the invariant fails we auto-retry with
the session 3 thermal-pairing pattern (cold, streaming, re-cold,
re-streaming) and report the minimum-drift pair.

## Non-hypotheses

- No UCF-Crime or continuous-video corpus (dropped from original 1.30
  prereg — use VideoMME since that is what we report on).
- No decoder co-location measurement (requires deployment
  infrastructure we don't have locally).
- No pre-prefill queue measurement (our single-client harness is a
  degenerate-pre-prefill-queue — depth 1).

## Configuration

```
model-path        /Users/jfb/models/gemma-4-e4b-it-4bit
manifest          union(videomme_dev_v1.toml, videomme_holdout_v1.toml)
                   (60 items — expect 30 dev + 30 holdout, 1 overlap
                    per VideoMME subset manifest)
frame-count       8
n                 60 (full union)
queries-per-clip  3 (one first-query + two follow-ups; sampled
                    from VideoMME's per-clip question pool)
max-tokens        32
rss-guard-mb      10000

COLD baseline:     no persistent-KV, no 1.51V patching,
                   no drift-triggered refresh — cold prefill per query
STREAMING stack:   --persistent-kv-reuse
                   --vision-tower-layer 2 --vision-tower-keep-rate 0.50
                   --drift-refresh-threshold <TBD from 1.49 sweep>
                   (anchor=none, novelty keep-rate=1.0 — C-VISION axis only;
                    H_stack is tested separately under EXP10 n=60)
```

Drift-refresh threshold: use 1.49's adjacent-frame ViT cos ≥ 0.95
trigger as the default; parameter-sweep is out of scope for this
prereg (could be added as a follow-up if H_sam_drift_refresh fails).

## Dependencies (gating)

This prereg is **queued but blocked** on:
1. EXP17/EXP18 V-only holdout pair (must-do #1, in progress
   2026-04-21) — need the V-only holdout anchor before adding
   persistent-KV composition on top.
2. EXP10 n=60 H_stack re-check (should-do #1) — need to know whether
   the novelty stacking axis is composable before stacking
   persistent-KV on top of V-patching.
3. A driver that wires persistent-KV + 1.51V + drift-refresh into a
   single CLI. Currently `scripts/run_novelty_pruning_gemma.py` has
   1.51V but not persistent-KV; the 1.55A driver has persistent-KV
   but not 1.51V. Driver merge ~2-3 h eng work.

## Runtime estimate

60 items × 3 queries × ~45 s per cold query = ~2.25 h for cold arm.
Streaming arm ~0.5–1 h (first-query + 2 × ≈0.8 s follow-ups per clip,
with occasional refresh bumps). Total ~3.5 h wall-clock including
thermal-pair retries. **Single autonomous session.**

## Adjudication rules

- **H_sam_e2e**: CONFIRMED if paired amortized e2e ≥ 3.0× AND acc
  Δ in band AND H_sam_thermal passes. EARNED if ≥ 1.5× with thermal
  gate failing (diagnostic). NULL if < 1.5× with thermal gate passing.
- **H_sam_bucket**: CONFIRMED if clean ≥ 0.50 AND degenerate ≤ 0.15.
  PARTIAL if one criterion meets, other within 10 pp.
- **H_sam_drift_refresh**: CONFIRMED if refresh-rate ≤ 30% AND
  degenerate-reduction ≥ 50%. NULL if refresh-rate > 50% (heuristic
  fails) or degenerate-reduction ≤ 20% (refresh doesn't help).
- **Paper promotion rule**: if H_sam_e2e + H_sam_bucket both pass,
  this reopens C-VISION as a **deployment-grade composition**
  contribution and unlocks the "streaming/deployment" framing of
  the paper's main result (raising submission tier from efficiency
  workshop to main-track systems venue).

## Artifacts expected

- `research/experiments/2026/artifacts/phase1_30_sam_streaming/cold_summary.json`
- `research/experiments/2026/artifacts/phase1_30_sam_streaming/streaming_summary.json`
- `research/experiments/2026/artifacts/phase1_30_sam_streaming/per_clip_bucket_tally.json`
- `research/experiments/2026/artifacts/phase1_30_sam_streaming/drift_refresh_trace.json`
- Findings: `research/experiments/2026/2026-04-??-phase-1_30-sam-streaming-findings.md`
- Runner: `scripts/run_phase1_30_sam_streaming.sh` (to be written)

## Relationship to original 1.30 harness prereg

The 2026-04-16 harness prereg targeted a CodecSight-comparable
UCF-Crime operating point. This prereg drops UCF-Crime entirely
because (a) we do not report on it and (b) Sam does not report on it
either — he reports on VideoMME-adjacent manifests. The streaming
*protocol* is preserved, the *corpus* changes. Once this lands, the
2026-04-16 harness prereg should be closed as historical or
re-scoped to a v2 that measures UCF-Crime as an external check.
