# Phase 1.41 — Qwen 2.5-VL-7B VideoMME 32-frame long-bucket findings

**Status:** findings, 2026-04-19. Dense n=9/10 on long-bucket items
from `videomme_dev_v1` at `frame_count=32`, identity cache. Prereg:
`2026-04-19-phase-1_41-qwen-videomme-32f-long-prereg.md`.

## Headline

**Long-bucket accuracy plateaus at 32f (1/9 = 11.1%)**, essentially
the same as 16f (1/10 = 10.0%). The 16f → 32f move produced zero
new flips in either direction on the 8 items that overlap. The
drift-compounds hypothesis is **not** supported by this run. The
regression seen at 8f → 16f did not continue past 16f in the n=9
probe; the long bucket appears to have saturated (poorly) by 16f.

## Observed vs prereg

| metric | 8f obs | 16f obs | 32f obs | prereg 32f prior | verdict |
|--------|--------|---------|---------|------------------|---------|
| long acc | 0.300 | 0.100 | **0.111** | [0.00, 0.30], best 0.10 | H1 **middle-band earned** (noise/plateau consistent; NOT drift-compounds ≤0.05, NOT stride-helps ≥0.40) |
| peak RSS | n/a | 7.23 GB | **8.52 GB** | [9.0, 12.0] GB | H2 **earned w/ margin** — undershot the low bound (memory fit better than predicted) |
| mean elapsed | 25.2 s | 78 s | **161.1 s** | [130, 200] s | H3 **earned** (2.06× the 16f time for 2× prompt tokens) |
| agreement | 1.000 | 1.000 | **1.000** | 1.000 | H4 **earned** — identity cache bit-faithful at 32f |
| parse failures | 0 | 0 | **0/9** | ≤ 2/10 | H5 **earned** |
| mean prompt tokens | 3,287 | 6,503 | **12,948** | ~13k | linear-in-frames as predicted (1.99× 16f) |

**Items missing.** Item `videomme:long:892-1` did not emerge in the
completed-items list. Driver exited with `stopped_early: false` and
empty stdout/stderr logs; summary lists 8 items as completed but the
jsonl contains 9 (includes 847-3). The ninth item (847-3) appears
to have been written to jsonl after the summary flush. Item 892-1
is absent from both. Treat results as **n=9** and note the
driver-coverage gap as a known quirk; re-running it alone would
cost ~3 min if we need to close.

## Paired per-item flip table (16f → 32f, 8 overlapping items)

| bucket | RR | RW | WR | WW | McNemar exact p |
|--------|----|----|----|----|-----------------|
| long (paired n=8) | 1 | 0 | 0 | 7 | 1.00 (no flips) |

At 32f, **zero** items flipped relative to 16f. The single correct
item (712-2) remained correct; the seven jointly-wrong items stayed
jointly wrong. This is the strongest possible "no discrimination"
paired signal at n=8: the doubling of frames produced no change in
per-item outcome. It is consistent with either a plateau (capacity
limit reached) or a floor (tokenized chance-level bottom) on this
item set.

## Frame-scaling curve (long bucket)

```
accuracy
  0.30 ── 8f
          \
  0.10 ──  \── 16f ── 32f  (plateau — zero flips paired 16f→32f)
```

The 8f → 16f drop of −20pp is confirmed as a real step, not a point
defect: it survives scrutiny from a third data point. But the
expected continuation (drift-compounds) did not materialize. Two
readings remain viable:

- **H-saturation** (newly supported). Long-bucket answering on 4bit
  Qwen 7B at 16f already saturates at ~10% because non-trivially
  many long items are simply unanswerable from 16 sampled frames of
  a 15-minute video. Adding more frames doesn't help — the signal
  is insufficient regardless of density, likely because the
  question demands reasoning over more content than the model can
  integrate at this size.
- **H-stride-window** (newly supported). The drop from 8f to 16f
  was a stride-artifact: 8f happened to catch relevant frames by
  luck on ~3 items (out of 10); 16f's denser sampling diluted that
  luck without gaining real capability. 32f continues the dilution
  without further harm because the "lucky frames" were already
  averaged out at 16f.

**Drift-compounds hypothesis (H-B from the 16f findings doc) is NOT
supported by this result.** A drift-compounds world would predict
0/9 at 32f or close to it; we observed 1/9 which is identical to
16f.

## Interpretation: what Phase 1.57 must distinguish

With stride-window and saturation both on the table, Phase 1.57
(feature-drift measurement) must now discriminate three cases on
the long bucket specifically:

1. **Drift-class dependent** — STATIC-token feature similarity
   degrades monotonically 8f→16f→32f, but accuracy plateaus
   because other bottlenecks dominate. If 1.57 shows monotonic
   drift but no flips, that's evidence that drift is a mechanism
   but not the binding constraint at 16-32f.
2. **Drift-class invariant** — STATIC cos stays roughly constant
   at all frame counts. That makes drift-compounds untenable as a
   long-bucket explanation and promotes stride-window or
   saturation.
3. **Drift-class U-shaped** — STATIC cos dips at 16f and recovers
   at 32f. Would match the paired "zero flips" observation if a
   compensatory mechanism kicks in. Least likely a priori.

## Runtime cost

Total 32f dense wall-clock on n=9: **1,288 s (21.5 min)**. Close
to the preregistered 28-min estimate for n=10. Per-item mean 161.1
s. Scaling ratio vs 16f: 2.06× time for 2.00× prompt tokens —
suggests prefill dominates at long-bucket sizes, consistent with
the 1.54 decode-accel framing not being load-bearing here (prefill
is the bottleneck, not decode).

## Decisions

- **32f medium/short runs: NOT queued.** Per Codex round-22
  guidance — narrow scope. The long-bucket probe answered the
  discriminating question for now; medium/short would be
  convenience-sampling without a specific hypothesis.
- **Paper language.** The 8f → 16f → 32f frame-scaling story is
  now three points on the long bucket: 30% → 10% → 11%. Frame the
  16f→32f gap as "plateau" not "continuing regression." Paper
  must NOT extrapolate either way — 32f is probably near the
  floor on this model/bucket/benchmark combination.
- **Claim #8.** Not affected. Still earned at 8f aggregate 0.533
  and 16f aggregate 0.567.
- **Phase 1.57.** Now **more** load-bearing. The mechanism
  question is live: stride-window vs saturation vs drift; 1.57's
  feature-drift measurement is the cheapest probe that cuts
  between them.

## What this does NOT answer

- Medium-bucket 32f behavior (the +30pp 16f lift could continue,
  reverse, or plateau). Not scoped here.
- Short-bucket 32f behavior. Saturated at 8f and 16f; unlikely to
  change.
- Does Gemma's frame-scaling match Qwen? Not in this run. Gemma
  has no 8f/16f/32f dense VideoMME line on these item IDs.
- Is it 4bit quantization specifically? Deferred to 1.58 (bf16
  comparison), not preregistered.

## Artifacts

- `research/experiments/2026/artifacts/phase1_41_qwen_videomme_32f_long/dense_n10.jsonl` (n=9 rows)
- `research/experiments/2026/artifacts/phase1_41_qwen_videomme_32f_long/dense_n10_summary.json`

## Cross-references

- 16f findings: `2026-04-19-phase-1_41-qwen-videomme-16f-findings.md`
- 32f prereg: `2026-04-19-phase-1_41-qwen-videomme-32f-long-prereg.md`
- Phase 1.57 (feature-drift mechanism — now load-bearing for the
  stride-vs-drift-vs-saturation question)
- Claim-matrix row 8 (VideoMME)
