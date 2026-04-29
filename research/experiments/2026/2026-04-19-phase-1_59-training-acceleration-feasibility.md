# Phase 1.59 — Training-acceleration feasibility (RESEARCH NOTE, FUTURE WORK)

**Status:** research note, 2026-04-19. Not a prereg. Not
an experiment. Scope: articulate whether and how the codec-through
mechanism could extend to **training** (not just inference) video
VLMs, and what a minimal local feasibility check would look like.

## Why this exists

External review (Codex round-22, 2026-04-19) noted that earlier
roadmap discussions flagged three threads:

1. Training speedup (this note)
2. Object/state delta sidecar → Phase 1.53 (real prereg landed)
3. Confidence-gated selective retry → Phase 1.40 + 1.31 (landed)

Two of the three graduated to real research notes or preregs.
Training speedup remained only as a paragraph in
`paper/framing.md:221` ("future work" language). That is too weak
a footprint to treat the thread as surveyed. This note closes the
gap without committing compute.

## Scope of the idea

Current inference-time savings (codec-through § ViT cache +
identity-cache + novelty-pruning) amount to removing most
recomputation on *unchanged* visual regions frame-to-frame. At
training time, the same observation should apply:

- Video pre-training batches contain enormous temporal redundancy
  (single clip, multiple consecutive frames, ~80-99% static in
  many content regimes per whitepaper §1.)
- During backprop, gradients flow through the ViT encoder on
  every frame. If the forward pass already had ≈98% `STATIC`
  tokens, the gradient contribution at those tokens is near-
  identical to the gradient at the previous frame's same
  position.
- **Hypothetical gain**: if we keep forward-pass identity via
  cache-substitute AND block gradient through cached tokens (or
  share gradient across cached tokens), the ViT-side training
  FLOPs should drop roughly by `1 − NOVEL%`.

## What we already know (cheap)

- The method's inference-time gains on *conferencing* video are
  29× (Sam § 3.3).
- ViT FLOPs on a 30B dense video model (e.g., InternVL3-78B) are
  the dominant pretrain cost on video-specific stages per
  published training reports.
- Training requires gradient correctness. Cache-substitute forward
  at ≈0.67-0.80 STATIC cos (per Sam research_queue lines 14-29)
  is not bit-identical; that may or may not matter for training
  convergence.

## Minimal local feasibility check (not yet a prereg)

Before preregistering any compute, the right cheap probe is:

1. **Convergence-under-noise microbench.** Take an existing
   video-VLM fine-tuning recipe (e.g., LLaVA-NeXT-Video on a
   small public instruction dataset). Run two short fine-tunes
   (few hundred steps each): baseline, and treatment where the
   vision encoder forward pass is cache-substituted using our
   existing pipeline. Measure loss trajectory + evaluation
   accuracy.
2. **Falsification band**: if cache-substitute training diverges
   from baseline by more than Δ ≥ 5pp on a validation task, the
   drift-tolerance argument does not extend to training; abandon.
3. **Earn band**: if trajectories match within ±2pp and
   ViT-time drops by the expected `NOVEL%` fraction, graduate
   this to a real prereg with a realistic training run.

Hardware constraint: our M3 Air 16 GB cannot hold any realistic
video fine-tune. The feasibility probe would need cloud or a
larger Mac. That puts this phase **squarely in future work** —
not actionable without resources.

## Related prior art (for when it gets prereg'd)

- **LLaVA-NeXT-Video** (2025): published video fine-tune recipes.
- **VideoLLaMA3** (2025): also a candidate training harness.
- **SigLIP2** (2025): patch-embedding encoder with clean hooks for
  substituting activations during forward.
- **TurboQuant** (2026): KV quantization during training, not
  forward-only; orthogonal mechanism that could compose.
- **StreamingVLM** (Oct 2025, referenced in whitepaper § Landscape):
  trained specifically for streaming regimes — a different cut.

## Decision

- **Do NOT pre-register a training experiment on M3 Air.** The
  hardware gap is decisive.
- **Do write the cheap microbench spec** (~50 lines) if a larger
  Mac or cloud GPU becomes available in the next month. Without
  resources, this stays a research note.
- **Paper language**: § Future Work should now name
  "training-time recomputation elimination" as a named open
  direction with this note as the reference, not as a vague
  sentence. Citing the drift-cosine result (1.57) as the main
  unknown makes the future-work statement concrete.

## Cross-references

- `paper/framing.md` § Future Work (training-speedup paragraph)
- pre-release CodecSight strategy notes preserved in git history (calibrated retry;
  object-state sidecar)
- Phase 1.53 (object-state delta sidecar — another deferred
  future-work thread that graduated)
- Phase 1.57 (feature-drift mechanism — the measurement that
  determines whether cache-substitute forward is safe enough for
  training convergence)

## Status

- [x] Note written (2026-04-19)
- [ ] Hardware available
- [ ] Microbench scaffold
- [ ] Baseline vs cache-substitute fine-tune
- [ ] Graduate to prereg if earn-band hit
