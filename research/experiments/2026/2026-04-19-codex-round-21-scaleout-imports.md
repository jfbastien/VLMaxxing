# Codex round-21 — pre-release scale-out extensions: survey + action plan

**Status:** planning note, 2026-04-19. Lists five extensions Codex
round-21 flagged as under-explored relative to the pre-release scale-out
source. Each subsection reports: (a) what that source actually
claims, (b) what Codex is asking us to consider, (c) whether it is
actionable on our current hardware, (d) our decision (preregister /
defer / reject-with-reason).

**Scientific-honesty note.** An Explore subagent audited the
pre-release external source against the five topic labels.
Only one (attention-context drift) maps to a direct pre-release source claim.
The other four are Codex-round-21 hypotheses prompted by the scale-out
system, not reproductions of documented pre-release source claims. We frame
them as such throughout. We will not cite "the pre-release source says X" when
the pre-release source does not say X.

## 1. Streaming protocol (continuous vs request/response)

- **Pre-release source:** Does not explicitly frame the system as a
  streaming server. Reuses features at the I-frame boundary
  (pre-release external source line 234: "periodically re-encode
  all tokens at I-frame boundaries"), which is compatible with a
  streaming pipeline but does not require one.
- **Codex round-21:** Our per-item subprocess benchmark driver
  (`scripts/run_benchmark_track_a.py` chunk_size=1) is antagonistic
  to session-warm reuse. A streaming driver would let us compose
  feature reuse with persistent KV-cache (see §2).
- **Our repo state:** Phase 1.30
  (`2026-04-16-phase-1_30-streaming-window-harness.md`) pre-registered
  a sliding-window harness as Track-B groundwork, gated on phases
  1.26/1.27/1.29. Never executed.
- **Actionable on 16GB M3?** Yes, for synthetic continuous-video
  corpus (concat N×10s clips). No, for UCF-Crime licensing cost.
- **Decision.** KEEP 1.30 pre-reg but reframe: streaming is now an
  *architectural lever for composing decode-amortization (§4) with
  persistent KV-cache (§2) and VLM-signaled refresh (§5)*, not a
  standalone Track-B prerequisite. Deferred behind Qwen 16f VideoMME
  (in-flight) and Phase 1.51V (user-blocked). Re-priority is P2.

## 2. Persistent KV-cache across items

- **Pre-release source:** Caches **ViT output embeddings** (vision-side)
  at unchanged-token granularity
  (pre-release external source lines 228-230). Does **not** discuss
  LLM KV reuse across clip/session boundaries.
- **Codex round-21:** Proposes a session-scoped LLM KV-cache that
  survives across clip boundaries, letting us amortize prefill once
  per conversation rather than once per benchmark item.
- **Our repo state:** Feature cache is per-item
  (`src/codec_through/feature_cache.py`). Decision log line 63
  explicitly defers "Temporal RoPE key correction" to Track B with
  note "current Track A path reuses image features (pre-LLM), not
  LLM KV states" — RoPE correction is only load-bearing on a
  session-scoped KV cache.
- **Actionable?** mlx-vlm does not expose a KV-cache handle we can
  retain across `generate()` calls on separate items without
  modifying library internals. Implementation is non-trivial.
- **Decision.** PREREGISTER as Phase 1.55 (persistent-KV streaming
  extension) with explicit gating on (a) an mlx-vlm KV handle, and
  (b) Phase 1.54 decode acceleration so we don't benchmark decode
  as the dominant cost. Marked DEFERRED-DESIGN until implementation
  gate clears; see `2026-04-19-phase-1_55-persistent-kv-prereg.md`
  for the placeholder prereg.

## 3. Attention-context drift (not positional-encoding drift) as the failure mode

- **Pre-release source:** Explicit, line 234: "To prevent error accumulation from global
  **attention context drift (~0.01 per frame)**, periodically re-
  encode all tokens at I-frame boundaries." The quoted drift rate
  was imported without our own measurement.
- **Codex round-21:** We may be conflating attention-map drift with
  PE-update drift. The two have different mitigations: attention
  drift needs re-encode (the source's fix); PE drift would need temporal
  RoPE key correction. Our 1.49 refresh sweep shows *that* refresh
  works on 8-frame windows (1-every-N recovers agreement) but does
  not diagnose the *mechanism*.
- **Our repo state:** 1.49 refresh sweep (n=small) documented in
  decision-log line 41: "no-refresh cached accuracy 0.2; refresh
  intervals 1, 2, 4 all recover to exact dense agreement." No
  attention-entropy or PE-correction ablations have landed.
- **Actionable?** A mechanism-isolation ablation needs (a) attention-
  entropy logging hooks inside mlx-vlm, and (b) a PE-correction
  variant to compare against. Both are multi-day implementation
  work. Reframing the claim is cheap and landable now.
- **Decision.** IMMEDIATE DOC EDIT: add explicit "attention drift,
  not PE drift" framing to (i) the publishability-status section on
  drift, (ii) the decision-log note on RoPE-key correction deferral,
  (iii) claim-matrix row that discusses refresh mechanism. Drift
  quantification (~0.01/frame) is still marked IMPORTED-UNVERIFIED
  in `reproduction-status.md`. Local ablation deferred to Phase
  1.57 (mechanism isolation) as P2.

## 4. Live-decode marginal cost (amortization)

- **Pre-release source:** Silent on decode economics. Does not
  discuss whether decode is amortized across sessions.
- **Codex round-21:** Our per-item driver charges full video decode
  against every inference. On a production streaming server decode
  runs once per session and frame-features are reused across many
  turns, so the decode-vs-generate split seen in our pilots (long-32
  decode = 56.9% of e2e, capping Ceiling@∞ at 1.31×) is a
  worst-case not a fundamental limit.
- **Our repo state:** Claim-matrix row 11 reports the decode-floor
  ceiling as a limit on token-pruning speedup. Phase 1.54 is
  pre-registered as the lever that moves the decode floor by
  swapping the FFmpeg step for a faster decoder. Does not address
  session-level amortization.
- **Actionable?** Benchmark-level amortization requires the
  streaming driver (§1). Claim-level reframing is cheap.
- **Decision.** IMMEDIATE DOC EDIT: add "decode-economics scope"
  paragraph to publishability-status and claim-matrix row 11
  clarifying that our reported aggregates charge decode fully per
  item and that on a streaming deployment the decode fraction is
  an upper bound, not a ceiling. Do not retroactively adjust
  reported numbers — keep them as pessimistic bounds.

## 5. VLM-signaled adaptive refresh

- **Pre-release source:** Does not discuss VLM-output-conditioned
  refresh. Refresh is I-frame-periodic
  (pre-release external source lines 234-240).
- **Codex round-21:** Suggests routing refresh decisions off VLM
  signals (attention entropy, generation confidence, top-k logprob
  margin) instead of pixel-domain or structural anchors. Hypothesis:
  attention-entropy spikes on frames where the VLM is "uncertain,"
  and refreshing those specifically would outperform blind-periodic
  refresh at matched compute.
- **Our repo state:** Claim-matrix explicitly forbids
  "confidence-conditioned" framing in paper language until Phase
  1.44 answer-margin logging lands (claim-matrix:82). Current
  routing uses pixel-diff (MEAN/MAX_ABS/CPF/TOP_K_MEAN) or structural
  anchors (nuwa_pillar, gemma_structural). No VLM-signal-conditioned
  variant has been built.
- **Actionable?** Needs (a) Phase 1.44 answer-margin logging to land
  (already queued), and (b) a refresh policy that reads per-generation
  logprobs and decides refresh on the *next* window. CPU-testable
  design step (planner API) is landable now; MLX integration is
  multi-day.
- **Decision.** PREREGISTER as Phase 1.56 (VLM-signaled refresh)
  with explicit gating on Phase 1.44. Marked DEFERRED-DESIGN; see
  `2026-04-19-phase-1_56-vlm-signaled-refresh-prereg.md` for the
  placeholder prereg. Paper-language rule stays: no
  "confidence-conditioned" claim until earned.

## Priority order (by SOTA-uplift expected value)

1. **Attention-drift-not-PE-drift reframe (§3)** — cheap, lands
   today, removes a latent conflation that could undermine a
   reviewer challenge.
2. **Decode-economics scope note (§4)** — cheap, lands today,
   clarifies that our aggregates are pessimistic bounds on a
   streaming deployment.
3. **VLM-signaled refresh prereg (§5)** — design-only today,
   implementation gated on Phase 1.44.
4. **Persistent-KV-cache prereg (§2)** — design-only today,
   implementation gated on mlx-vlm handle + Phase 1.54.
5. **Streaming harness refresh (§1)** — reframe 1.30 as composition
   lever, deferred to P2.

§1, §2, §5 are each landable as a preregistration today without
blocking the 16f VideoMME run. §3 and §4 are pure documentation
edits.

## Links

- Pre-release external source: summarized in
  `../../../docs/claim-register.md`
- Existing 1.30 harness prereg:
  `2026-04-16-phase-1_30-streaming-window-harness.md`
- Phase 1.54 decode acceleration prereg:
  `2026-04-18-phase-1_54-video-decode-acceleration-prereg.md`
- Phase 1.44 answer-margin logging — queued, not yet scheduled.
