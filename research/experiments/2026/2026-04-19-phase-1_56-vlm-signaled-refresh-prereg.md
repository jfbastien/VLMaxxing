# Phase 1.56 — VLM-signaled adaptive refresh (PREREG, DEFERRED-DESIGN)

**Status:** preregistration, 2026-04-19. Codex round-21 extension.
DEFERRED-DESIGN — implementation gated on (a) Phase 1.44
answer-margin logging landing, and (b) a refresh-policy API that
reads per-generation logprobs.

**Provenance.** This prereg is a Codex-round-21 hypothesis, not a
reproduction of a documented pre-release source claim. the pre-release source
uses periodic (I-frame-aligned) refresh
(`pre-release external source:234-240`), not
VLM-signal-conditioned refresh. This is a proposed extension.

## Objective

Quantify whether conditioning refresh on a VLM-internal signal
(generation-confidence margin, or attention-entropy peak) beats
pixel-domain or structural-anchor refresh at matched compute.

## Hypotheses

- **H1 (VLM-signal refresh beats pixel-signal refresh at matched
  compute).** On VideoMME dev n=30, conditioning refresh on the
  answer-margin from the previous window (margin < 0.2 → refresh
  next window) delivers ≥ 0.05 higher aggregate accuracy than
  pixel-MEAN refresh at matched refresh rate.
- **H2 (signal is load-bearing, not correlate-of-activity).**
  Ablation: random-refresh at matched rate scores ≥ 0.05 below the
  VLM-signal arm. Rules out "any non-uniform refresh helps."
- **H3 (VLM-signal refresh rate is lower than pixel-signal refresh
  rate at matched accuracy).** When accuracy is tied, VLM-signal
  arm refreshes fewer frames — i.e., the signal identifies
  high-value refresh points more efficiently than pixel change.

## Acceptance / rejection bands

| hypothesis | earn                 | reject              |
|------------|----------------------|---------------------|
| H1         | Δacc ≥ +0.05 over pixel-MEAN at matched refresh | Δacc ≤ 0 |
| H2         | random-refresh Δacc ≤ -0.05 vs VLM-signal      | random ties VLM-signal |
| H3         | VLM-signal refresh rate ≤ 0.7 × pixel rate at matched accuracy | VLM-signal needs ≥ pixel rate |

## Gating

Blocked on:

1. **Phase 1.44 answer-margin logging.** Driver must emit
   per-generation top-1 − top-2 logprob margin. Queued, not
   scheduled.
2. **Refresh-policy API.** Need a `RefreshPolicy` protocol in the
   planner that accepts a `VLMSignal` input and returns a
   per-frame refresh decision. CPU-testable; ~0.5 day design work.
3. **Attention-entropy logging (optional, H1 variant).** Needs
   mlx-vlm hook into the attention layers. ~1 day work; can run H1
   on margin signal alone first.

## Paper-language constraint

Claim-matrix line 82 forbids "confidence-conditioned" framing
until Phase 1.44 logging lands. Paper language for this phase:
**"VLM-signaled" adaptive refresh**, not "confidence-conditioned."
Once 1.44 lands and this experiment earns H1, relax to
"confidence-margin-conditioned" for the specific variant tested.

## Measurement protocol

- **Baselines.** (a) pixel-MEAN refresh at fixed interval (our
  Track-A default), (b) pixel-MEAN refresh at matched-rate to
  VLM-signal arm, (c) random refresh at matched rate.
- **Treatment.** VLM-signal refresh: pre-compute answer-margin from
  dense run on first N windows, use as oracle for subsequent
  windows; compare to online (non-oracle) version.
- **Authoritative artifacts.** `research/experiments/2026/artifacts/
  phase1_56_vlm_signal/{baseline,signal,random}_dev_n30_*.jsonl`.

## Runtime estimate

Benchmark-only: **~45 min** at 8-frame regime (3 arms × n=30
VideoMME dev at Qwen 7B). ~2 hours at 32-frame regime if we want
to co-validate the C-CEILING model's regime sensitivity.

## Cross-references

- `2026-04-19-codex-round-21-scaleout-imports.md` §5
- Phase 1.44 (answer-margin logging — queued)
- `paper/claim-matrix.md` row 3 (routing), row 11 (novelty-pruning)
- pre-release source §3.3 — periodic I-frame refresh

## Status

- [ ] Phase 1.44 answer-margin logging lands
- [ ] RefreshPolicy API lands (CPU-testable)
- [ ] Attention-entropy logging (optional, H1 variant)
- [ ] Oracle-variant run
- [ ] Online-variant run
- [ ] Compare to pixel-signal baselines
