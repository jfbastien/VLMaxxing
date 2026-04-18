# Phase 1.51R — Pilot findings (n=1 VideoMME long, 2026-04-18)

**State:** landed. First GPU execution of `scripts/run_novelty_pruning_gemma.py` on
Gemma 4-E4B-4bit MLX after the bounded-decode OOM fix.
**Parent preregs:**
- `research/experiments/2026/2026-04-17-phase-1_51-novelty-pruning-gemma-prereg.md`
- `research/experiments/2026/2026-04-17-sam-reproduction-lane-prereg.md`
**Artifacts:** `research/experiments/2026/artifacts/phase1_51R_pilot/`

## Result

Single-item pilot, `videomme:long:669-1`, arm `none`, keep-rate 0.5,
max-tokens 32, 8 uniformly sampled frames, image size 512×512, Gemma
post-pool grid 16×16 (runtime-verified 2026-04-18; processor's stale
280/14×20 attribute was NOT used).

| Path | end_to_end (ms) | decode | processor | vision | prune+mask+novelty | generate |
|---|---|---|---|---|---|---|
| **dense** | 32,932 | 22,783 | 77 | 4,928 | — | 5,143 |
| **pruned kr=0.5** | 32,571 | 22,783 | 77 | 4,928 | 173 | 4,610 |

- **End-to-end speedup: 1.01×**
- **Generate-only speedup: 1.12×**
- Accuracy: dense_correct=True, pruned_correct=True, agreement=True
- Kept tokens: 1024 / 2048 (exactly kr × F × T as specified).

## Per-stage share of end-to-end (dense path)

| Stage | Duration (ms) | Share |
|---|---|---|
| **decode (video I/O + ffmpeg)** | **22,783** | **69.2%** |
| processor | 77 | 0.2% |
| **vision tower (SigLIP2, runs on ALL tokens)** | **4,928** | **15.0%** |
| **generate (prefill + 32 decode tokens)** | **5,143** | **15.6%** |

## Why end-to-end speedup is capped on E4B at this geometry

The Sam-reproduction prereg predicted ≥ 1.8× end-to-end at kr=0.5 on
Gemma + VideoMME. The pilot shows 1.01×. Root cause is NOT a bug —
it's the arithmetic of the pipeline:

1. **Video decode is 69% of end-to-end.** Pruning can never touch
   this — it's ffmpeg / PyAV pulling bytes off disk. On VideoMME
   `long` items (multi-minute videos) this fraction is even higher
   than on `short` items; we should stratify.
2. **Vision tower (~5s) runs on ALL tokens pre-prune.** Sam's
   mechanism drops tokens between the vision tower and the LLM
   prefill — the ViT still processes the full 2048-token grid. On
   the E4B backbone, vision tower cost (4.9s) is comparable to LLM
   generate cost (5.1s), so vision caps how much prefill-shortening
   can do.
3. **Generate includes decode of `max_tokens` autoregressive
   tokens.** At max_tokens=32, observed 1.12× generate speedup is
   consistent with halving prefill (which is a small share of
   generate) while leaving per-token decode unchanged.

## Arithmetic: what's the hard ceiling for end-to-end speedup on E4B?

Let `D` = decode_ms, `V` = vision_ms, `G` = generate_ms, `s` =
generate-only speedup factor. End-to-end speedup is bounded by:

    ceiling = (D + V + G) / (D + V + G/s)

On this pilot item (`D = 22.8s`, `V = 4.9s`, `G = 5.1s`):

| Hypothesized generate speedup | End-to-end speedup ceiling |
|---|---|
| s = 1.12 (observed at kr=0.5) | 1.017× |
| s = 2.0 (theoretical kr=0.5 ideal) | 1.080× |
| s = ∞ (zero-cost generate) | 1.184× |

Even if prefill-shortening eliminated ALL generate cost, the ceiling
is 1.18× on this long-video item. **Sam's 1.8× claim is
unreachable at these (D, V, G) proportions.** To recover the claim
on E4B we would need one of:

- `D` → near-zero (impossible on real video)
- `V` → near-zero (would require vision-tower pruning, a different
  mechanism not in scope for 1.51R)
- `G/(D+V+G)` → much larger (smaller video → smaller D; OR much
  larger model → G scales with layer count; OR larger context → G
  scales with tokens²)

## Falsified / supported hypotheses

| Hypothesis | Status |
|---|---|
| H-decode (decode dominates end-to-end) | **Confirmed** — 69% of wall time is I/O-bound. |
| H-vision (vision tower caps prefill-shortening gains on E4B) | **Confirmed** — V ≈ G, so removing G halves only part of non-decode. |
| H-sam-1.8× reproduces at kr=0.5 on VideoMME long | **Falsified** — analytically impossible at this (D, V, G). |
| H-generate-path-correct (pruning ≠ bug) | **Confirmed** — dense and pruned answers agree, kept_tokens exactly 1024/2048. |

## What this means for the paper

The Sam-reproduction lane lands a **partial / null reproduction** as
the headline result for claim #11:

- **Sign matches:** pruning at kr=0.5 gives positive generate-only
  speedup (1.12×).
- **Order-of-magnitude fails on E4B:** end-to-end speedup is capped
  near 1.0× by decode + vision share, not by the mechanism itself.
- **Mechanism is correct:** agreement + exact kept-token count
  show the prefill-shortener is functioning as specified.

This is a **publishable negative result** under the prereg's
accept/reject gate: speedup < 1.3× at the best cell → "NO-REPRO on
E4B, preregistered null with mechanistic explanation (vision tower +
decode dominance)." The paper discusses this as evidence that Sam's
mechanism is model-scale-sensitive (26B prefill dominates; E4B
prefill does not).

## Next experiments (post-pilot)

Ordered by diagnostic value. Only one runs at a time to avoid
disturbing measurements.

1. **Stage 1 — n=30 dev scale-up at matched config** (in-flight).
   Confirms the n=1 finding with error bars, stratified across
   short/medium/long. Gives the error-barred null for claim #11.
2. **Stage 2 — kr-aggressiveness sweep** (pending Stage 1).
   `kr ∈ {0.10, 0.25, 0.50, 0.75}` × arm=none × n=5 subset. Tests
   whether kr=0.10 recovers any of the ceiling; expected result:
   generate speedup trends up, end-to-end stays capped by vision.
3. **Stage 3 — max_tokens=1 sensitivity** (pending Stage 1-2).
   Shrinks decode-token share of generate so prefill fraction rises;
   tests whether the 1.12× limit is prefill-saturation or
   prefill-is-tiny. Expected: doesn't fix end-to-end because vision
   still dominates.
4. **Stage 4 — (out of 1.51R scope)** vision-tower pruning as a
   separate mechanism. Would fully reproduce Sam's 1.8× feasibility
   envelope but requires a different drop point (pre-vision).

## Runtime estimates (benchmark-only, not implementation)

| Stage | Config | Items × Cells | Estimated wall clock |
|---|---|---|---|
| 1 | n=30 VideoMME dev, arm=none, kr=0.5 | 30 × 1 | ~15 min |
| 2 | kr sweep, n=5 subset, arm=none | 5 × 4 | ~12 min |
| 3 | max_tokens ∈ {1, 8, 32}, n=5 subset | 5 × 3 | ~8 min |
| — | **Cumulative after stages 1–3** | | **~35 min** |

Stage 4 is out of 1.51R scope; not budgeted here.
