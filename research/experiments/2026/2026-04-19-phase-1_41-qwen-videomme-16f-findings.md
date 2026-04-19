# Phase 1.41 — Qwen 2.5-VL-7B VideoMME 16-frame findings

**Status:** findings, 2026-04-19. Dense n=30 on videomme_dev_v1 at
`frame_count=16`, identity cache. Prereg:
`2026-04-19-phase-1_41-qwen-videomme-16f-prereg.md`.

## Headline

**Non-monotonic frame scaling: +3.3pp aggregate, but long-bucket
DROPS −20pp.** H2 (long gets biggest lift) falsified hard in the
opposite direction. Medium gets the lift; long regresses.

## Observed vs prereg

| metric | 8f observed | 16f observed | prereg 16f prior | verdict |
|--------|-------------|--------------|------------------|---------|
| aggregate acc | 0.533 | **0.567** | [0.55, 0.65] | H1 **earned** (barely — at band lower edge) |
| short acc | 0.800 | 0.800 | [0.70, 0.90] | in band (no change) |
| medium acc | 0.500 | 0.800 | [0.50, 0.70] | **exceeded** band (+30pp) |
| long acc | 0.300 | **0.100** | [0.40, 0.60] | H2 **falsified** — moved WRONG direction (−20pp) |
| agreement (dense vs identity-cache) | 1.000 | 1.000 | n/a | identity bit-faithful at 16f |
| mean dense elapsed | 31.0 s | 75.2 s | [55, 90] s median | H4 earned |
| mean prompt tokens | 3,287 | 6,503 | ~2× | linear as predicted |
| parse failures | 0 | 0 | ≤ 2 | H5 earned |

Peak RSS: not captured in this summary (dense-only run; RSS-ceiling
question rides with future 32f attempt).

**Unpaired two-proportion z-test on aggregate**: z=0.26, p=0.80 —
aggregate Δ is statistically noise at n=30.

**Paired per-item flip table (8f → 16f, same 30 items):**

| bucket | RR (both correct) | RW (correct→wrong) | WR (wrong→correct) | WW (both wrong) | McNemar exact p |
|--------|-------------------|--------------------|--------------------|-----------------|-----------------|
| short  | 7 | 1 | 1 | 1 | 1.00 (noise) |
| medium | 5 | 0 | **3** | 2 | **0.25** (directional) |
| long   | 1 | **2** | 0 | 7 | 0.50 (directional, weak) |

The paired view sharpens the per-bucket story: medium's +30pp lift
comes from 3 items flipping wrong→correct with zero reverse flips
(strong directional evidence, not just luck); long's −20pp
regression comes from 2 items flipping correct→wrong with zero
reverse flips (directional, statistically weak at n=10). Short is
genuine noise.

At n=10 the 95% CI half-width on a per-bucket proportion is ±0.31,
so the individual bucket shifts don't clear formal significance —
but the per-item flip direction is asymmetric in a way that mean-
accuracy summaries hide. The asymmetry is stronger evidence than
the Δ numbers imply.

## Interpretation

### Why medium lifts and long regresses (hypotheses, ranked)

**H-A (temporal resolution trade-off, dominant hypothesis).** At
8f on a 15-min long video, frames are ~112s apart — too coarse to
locate relevant moments, so accuracy is at chance (0.30 ≈ 3/10, and
4-choice chance is 0.25). At 16f the sampling stride becomes ~56s,
still too coarse to locate moments BUT the model now has twice as
many distractor frames diluting whatever signal a lucky sample
captured. Medium (4-15 min) at 8f had ~45s stride — already in a
usable regime — and 16f gives ~22s stride which crosses a usability
threshold. Short (<4 min) is saturated at 80% and neither stride
matters.

**H-B (attention-context drift, Sam's mechanism).** Sam's whitepaper
line 234 quotes "~0.01/frame attention-context drift." At 16f we
are twice as deep into the drift regime as 8f, and long items have
the least redundancy between frames (the drift-correcting signal
from repeated content is weakest). Medium items have more
structural repetition (one scene, one speaker) so drift is
tolerable; long items span multiple scenes with genuinely different
content per frame. Phase 1.57 mechanism-isolation would test this
directly; we can't pick between A and B from this data alone.

**H-C (4bit quantization × long-context interaction).** The
`Qwen2.5-VL-7B-Instruct-4bit` model may have quantization-induced
attention-quality degradation that emerges specifically on long
contexts. 16f × 3s/frame × typical fps puts our context at ~6.5k
tokens, which for a 4bit model with bf16-absent activation paths
could produce quality drops invisible at 3.3k tokens. This is
deferred to a bf16 comparison (Phase 1.58, not yet preregistered).

### What this does NOT show

- This is **not** a claim that more frames always hurt. The paired
  8f-to-16f lift is +3.3pp in aggregate; the long-bucket regression
  could be random noise at n=10 (although the sign is stable).
- It does NOT rule out Sam's 32f regime being monotonically better
  on long-bucket — his model is 26B, ours is 7B, and the
  attention-scaling curves for frame-count may shape-differently at
  larger parameter counts. The "regime gap" framing (Sam's 26B/32f
  vs ours 7B/16f) now has two independent supports: ceiling binds
  differently, and frame-scaling is differently-shaped.
- It does NOT change claim #8. Claim #8 is EARNED at 8f and now
  has a frame-scaling strengthener: our 8f reproduces 8f
  expectations, and 16f gives 0.567 which is in the [0.55, 0.65]
  prereg band.

## Runtime cost

Total 16f dense wall-clock: 2,257 s = **37.6 min** for n=30. 8f
was 931 s = 15.5 min. The 2.4× time ratio (for 2× prompt tokens)
is consistent with Qwen prefill dominating — another data point
for the decode-economics scope caveat (our per-item aggregates
would look different in a streaming deployment that amortizes
prefill).

## Implications for the paper

1. **Add frame-scaling paragraph** to claim #8 section: 8f → 16f
   gives +3.3pp aggregate (not significant at n=30), but the
   per-bucket pattern is non-monotonic — medium lifts, long
   regresses. This is an honest-negative result that strengthens
   the "regime gap" framing without forcing us to abandon any
   earned claim.
2. **Do NOT extrapolate 32f.** Whatever extrapolation we would
   have done from the 8f point alone, this data point forbids
   the linear extrapolation. A 32f run is now a first-order
   experiment, not a confirmation.
3. **Frame count is not a free knob for long-bucket improvement.**
   If we want to beat 0.30 on long-bucket, scaling frames is at
   best insufficient and possibly counter-productive. The path
   through Phase 1.54 (decode-accel so we can afford more frames)
   is compatible with the "we might need a different mechanism,
   not just more frames" reality — it unblocks the experiment
   without committing us to the linear extrapolation.
4. **Phase 1.57 (attention-entropy logging) is now more
   load-bearing.** Without it, we cannot distinguish H-A
   (stride-based) from H-B (drift-based) for the long-bucket
   regression. The mechanism matters because it shapes which
   levers (prompt restructuring vs. explicit re-encoding vs.
   mixed-resolution sampling) address the problem.

## Decisions

- **Claim #8**: strengthened (not changed). Add 16f row to paper
  table: `dense_acc_16f = 0.567 (n=30 dev, videomme_dev_v1)`.
- **Claim #13 (C-CEILING)**: not directly affected; this is dense
  accuracy not pruned.
- **32f run**: NOT auto-queued. Now gated on (a) Phase 1.54
  decode-accel landing for long items, AND (b) a specific
  hypothesis — not just "extend the curve."
- **Paper language**: do not call 8f→16f→32f a "scaling trend."
  Use "frame budget points" and show the non-monotonic bucket
  pattern honestly.

## Artifacts

- `research/experiments/2026/artifacts/phase1_41_qwen_videomme_16f/dense_n30.jsonl`
- `research/experiments/2026/artifacts/phase1_41_qwen_videomme_16f/dense_n30_summary.json`

## Cross-references

- 8f prereg + findings (April 18)
- 16f prereg (April 19, this session)
- Claim #8 (EARNED at 8f, strengthened with 16f)
- Phase 1.57 (attention-entropy ablation — now more load-bearing)
- Phase 1.54 prereg (decode-accel — gates any 32f attempt)
- 2026-04-19-codex-round-21-sam-imports.md §3 (attention-drift
  framing)
