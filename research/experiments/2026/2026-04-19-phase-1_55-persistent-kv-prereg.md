# Phase 1.55 — persistent LLM KV-cache (SUPERSEDED 2026-04-19)

**Status: SUPERSEDED.** This prereg is replaced by:

- `2026-04-19-phase-1_55A-persistent-kv-reproduction-prereg.md`
  (follow-up latency reproduction of the pre-release source's §2.13.3 measurement)
- `2026-04-19-phase-1_55B-persistent-kv-decode-composition-prereg.md`
  (composition with 1.54 decode acceleration — deferred)

## Why superseded

Earlier drafts of this prereg framed persistent KV-cache as a
**Codex-round-21 hypothesis**, not a reproduction of a measured
pre-release source claim. That was wrong.

The pre-release external source (638 lines, §2.13.3 at lines
410-430; removed from the OSS tree, summarized in
`docs/claim-register.md`) reports a
**measured** persistent-KV result on Gemma 4 26B × MLX: 20 queries,
follow-up latency uniformly sub-2 s (median 0.8 s), 10–18× follow-
up speedup, zero accuracy change. The mechanism is
`PromptCacheState` + prefix matching threaded through sequential
queries on the same video.

The pre-release seed copy was frozen before §2.13.3 landed; that is the
source of the provenance confusion in this draft. External review
(2026-04-19 Codex round-22) flagged the mis-attribution.

The original draft also had two wrong gating claims:

- "mlx-vlm fork needed for KV handle" — **false**. Our local
  mlx-vlm `0.x` has `PromptCacheState` + `find_prefix_length` in
  `mlx_vlm.generate` (verified 2026-04-19 grep on
  `.venv/lib/python3.12/site-packages/mlx_vlm/generate.py:346+`).
- "Blocked on 1.54 decode acceleration" — **false**. Decode
  composition is a separable follow-on (→ 1.55B). The latency
  reproduction stands alone (→ 1.55A).

The 1.55A follow-up-latency reproduction is the highest product-
relevance number in the codec-through story and has no real
gating today. It should have been landing weeks before 1.55B.

## Original (INCORRECT) content — retained for provenance only

Everything below this line is the pre-correction draft. Do NOT use.
Work against 1.55A instead.

---

**Status (OLD):** preregistration, 2026-04-19. Codex round-21 extension.
DEFERRED-DESIGN — implementation blocked on (a) an mlx-vlm KV-cache
handle that survives across `generate()` calls, and (b) Phase 1.54
video-decode acceleration so decode is not the dominant cost on
long clips.

**Provenance (OLD and WRONG).** This prereg is a Codex-round-21
hypothesis extending the pre-release source, not a reproduction of a
documented pre-release source claim. the pre-release source's thesis caches ViT output
embeddings at unchanged-token granularity
(`pre-release external source:228-230`), not LLM KV.
Persistent LLM KV across clip boundaries is Codex's suggestion for
a production-streaming composition lever.

## Objective

Design and pre-register an experiment that quantifies the e2e
speedup gain from retaining LLM KV-cache across items on a
streaming driver, vs. our current per-item subprocess driver.

## Hypotheses

- **H1 (warm KV amortizes prefill).** On a synthetic 10-clip
  streaming session (100 total queries; 10 queries per clip), a
  persistent-KV driver achieves at least 1.5× prefill-time speedup
  over cold-start per-item prefill, measured on the 2nd–10th query
  per clip (amortization region).
- **H2 (session KV does not regress accuracy).** Under matched
  frame budgets and kr=0.10, 100-query session accuracy is within
  -0.05 absolute of the equivalent 100 cold-start evaluations.
- **H3 (composes with Phase 1.54 decode acceleration).** On long
  clips (VideoMME long bucket), persistent-KV on top of Phase 1.54
  decode acceleration brings aggregate e2e above 2.0× (currently
  bounded to 1.31× by decode + prefill floor).
- **H4 (RoPE-key correction is load-bearing for KV reuse).** Without
  temporal RoPE key correction, H1 accuracy deltas exceed -0.10
  (mechanism probe; deferred to decision-log row 63).

## Acceptance / rejection bands

| hypothesis | earn                        | reject                    |
|------------|-----------------------------|---------------------------|
| H1         | prefill speedup ≥ 1.5×      | ≤ 1.2× or regresses       |
| H2         | Δacc ≥ -0.05                | Δacc ≤ -0.10              |
| H3         | aggregate e2e ≥ 2.0×        | ≤ 1.5×                    |
| H4         | Δacc without RoPE fix ≤ -0.10 at matched KV reuse | Δacc > -0.05 — RoPE fix not load-bearing |

## Gating

Blocked on:

1. **mlx-vlm KV handle.** Current `generate()` discards KV after
   each call. Need either (a) a fork that exposes a reusable
   `kv_cache` object, or (b) a wrapper that re-runs the model with
   manually-maintained KV. Both are implementation work on the
   order of 2-3 days.
2. **Phase 1.54 decode acceleration** must land first so that the
   comparison is meaningful on long clips (otherwise decode
   dominates and KV warmth is invisible in the aggregate).
3. **Phase 1.30 streaming harness** landed as a driver (`scripts/
   streaming_harness.py`), with support for persistent KV.

## Measurement protocol

- **Session corpus.** 10 clips × 10 queries per clip = 100 queries.
  Clips drawn from VideoMME dev manifest (existing, n=30 available).
  Queries synthesized: the three existing VideoMME questions per
  clip + 7 generated paraphrases. **Pre-register the exact query
  list at execution time.**
- **Drivers compared.**
  - **Baseline:** existing per-item subprocess driver,
    `scripts/run_benchmark_track_a.py` chunk_size=1.
  - **Treatment:** new `scripts/run_streaming_session.py` with
    `--persistent-kv` flag.
- **Metrics.** Per-item prefill ms, per-item generate ms,
  per-item e2e ms, per-clip cumulative savings, session accuracy,
  peak RSS.
- **Authoritative artifacts.** `research/experiments/2026/artifacts/
  phase1_55_persistent_kv/session_{baseline,treatment}_*.jsonl`.

## Runtime estimate

Benchmark-only (not implementation): **~1.5 hours** for the 2×100
query sweep on M3 Air 16GB (8-frame regime). Double to ~3 hours
at 32-frame regime.

## Cross-references

- `2026-04-19-codex-round-21-scaleout-imports.md` §2
- `2026-04-16-phase-1_30-streaming-window-harness.md` (harness)
- `2026-04-18-phase-1_54-video-decode-acceleration-prereg.md`
- `research/decision-log.md` row 63 (RoPE-key correction deferral)

## Status

- [ ] mlx-vlm KV handle design
- [ ] Phase 1.54 decode acceleration lands
- [ ] Phase 1.30 streaming harness lands
- [ ] Baseline session corpus pre-registered
- [ ] Treatment driver lands
- [ ] Run & compare
