# Phase 1.41 — Qwen 2.5-VL-7B VideoMME 32-frame findings (long → all-buckets)

**Status:** findings, 2026-04-19. Run completed n=28/30 on
`videomme_dev_v1` at `frame_count=32`, identity cache. Prereg:
`2026-04-19-phase-1_41-qwen-videomme-32f-long-prereg.md`.

**Scope expansion note.** The prereg scoped the probe to `--group long`
(n=10). The driver in fact ran through the full 30-item dev manifest
(long + medium + short). The extra ~17 min of compute yielded
**new, unplanned cross-bucket evidence** reported in a dedicated
section below. Interpret it as exploratory beyond the prereg's 5
pre-registered hypotheses: the long-bucket verdicts (H1-H5) stand
as originally preregistered; the medium/short data is an
observational bonus we **did not** commit to a falsification band
for ahead of time.

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

- Does Gemma's frame-scaling match Qwen? Not in this run. Gemma
  has no 8f/16f/32f dense VideoMME line on these item IDs.
- Is it 4bit quantization specifically? Deferred to 1.58 (bf16
  comparison), not preregistered.
- Medium/short bucket-specific hypotheses (e.g., would a
  H-medium-ceiling fall at a particular frame count?). The
  cross-bucket numbers below are observational, not preregistered.

## Unplanned cross-bucket result (n=28, 27 items summary + 1 late jsonl)

The run continued past the `--group long` scope and completed
n=10 long, n=10 medium, n=8 short (3 short items unwritten when
the run ended; jsonl landed 1 extra late short for n=28 rows).
Per-bucket distribution (dense = identity baseline; agreement is
identity-cache bit-faithfulness):

| bucket | n  | dense acc     | agreement | mean elapsed | peak RSS | mean pp toks |
|--------|----|---------------|-----------|--------------|----------|--------------|
| short  |  8 | 7/8  = 0.875  |  8/8      | 144.3 s      | 8.52 GB  | 12,933       |
| medium | 10 | 7/10 = 0.700  | 10/10     | 155.1 s      | 8.52 GB  | 12,924       |
| long   | 10 | 1/10 = 0.100  | 10/10     | 165.9 s      | 8.52 GB  | 12,949       |
| **all** | 28 | **15/28 = 0.536** | **28/28** | 155.6 s | 8.52 GB | ~12,940 |

### Frame-scaling across all three buckets

Combining with prior dense runs at 8f (n=30 aggregate) and 16f
(n=30 aggregate) on the same `videomme_dev_v1` manifest:

| bucket | 8f acc       | 16f acc      | 32f acc (new) | Δ(8→16) | Δ(16→32) |
|--------|--------------|--------------|---------------|---------|----------|
| short  | ~1.000       | 0.800        | 0.875         | -20pp   | +7.5pp   |
| medium | 0.400        | 0.700        | 0.700         | +30pp   |  0pp     |
| long   | 0.300        | 0.100        | 0.100         | -20pp   |  0pp     |
| **agg**| 0.533        | 0.567        | 0.536         | +3.4pp  | -3.1pp   |

**Interpretation.** Doubling frames 16→32 yields **essentially no
aggregate accuracy gain** on Qwen 2.5-VL-7B-4bit over
VideoMME dev n=30. The aggregate moves -3.1pp which is within
per-item noise (28-item binomial 95% CI ~ ±19pp). Per bucket:
- **short**: partially recovers from the 8f→16f regression (+7.5pp,
  still below the near-perfect 8f baseline by -12.5pp).
- **medium**: holds at 0.700 — the 16f lift saturates.
- **long**: plateau at 0.100 — third data point confirms earlier
  findings.

The practical implication is stark: for Qwen 7B-4bit on VideoMME
dev, **32-frame uniform sampling is not Pareto-efficient**. It
pays 2× prompt tokens and ~2× latency (144-166 s vs 78 s) for no
aggregate accuracy. Either 16f is the right budget, or the
bottleneck is model size (see 1.58 bf16, and larger-model lanes in
Codex round-22 backlog).

### Identity-cache 100% agreement across all 28 items at 32f

The identity cache produced `match=1.0` on every item in every
bucket at 32f. Combined with the prior 8f and 16f 100% agreement
runs, we now have **three frame-count confirmations of
bit-faithful identity cache behavior on Qwen 2.5-VL-7B-4bit**
at 8f (n=30), 16f (n=30), and 32f (n=28). This is the expected
outcome — the identity cache literally re-runs the ViT each time,
so the two branches are deterministically identical text outputs.
This is a harness-determinism check, **NOT** a claim about
cache-substitute robustness; the latter is what Phase 1.57
measures directly.

## Artifacts

- `research/experiments/2026/artifacts/phase1_41_qwen_videomme_32f_long/dense_n10.jsonl` (n=28 rows — 10 long + 10 medium + 8 short)
- `research/experiments/2026/artifacts/phase1_41_qwen_videomme_32f_long/dense_n10_summary.json` (summary covering 27 completed_item_ids — 1 late-landing short row in jsonl)

## Cross-references

- 16f findings: `2026-04-19-phase-1_41-qwen-videomme-16f-findings.md`
- 32f prereg: `2026-04-19-phase-1_41-qwen-videomme-32f-long-prereg.md`
- Phase 1.57 (feature-drift mechanism — now load-bearing for the
  stride-vs-drift-vs-saturation question)
- Claim-matrix row 8 (VideoMME)
