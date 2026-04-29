# Phase 1.55B — Persistent KV × decode acceleration composition (PREREG, DEFERRED)

**Status:** preregistration, 2026-04-19. **DEFERRED** — requires
Phase 1.55A (follow-up-latency reproduction on Qwen) and Phase
1.54 (video-decode acceleration) to both have landed.

## Objective

1.55A measures follow-up query latency at steady-state (first
query already paid; cache is warm). 1.54 attacks the orthogonal
long-clip decode-time floor. This phase measures what happens
when both land on the same stack: does the compound e2e savings
exceed either alone, or does one gate the other?

## Provenance

the pre-release source §2.13.3 (follow-up speedup) and §2.13.4 (e2e
deployment-latency model) are both measured on Gemma 4 26B. The
e2e model states explicitly that "neither mechanism alone delivers
the user-facing conversational ambient agent experience; together
they do" (pre-release source:452). That compound claim is measured on
the pre-release source's hardware but not on ours. This prereg tests it locally.

## Gating (hard)

Blocked on:

1. **1.55A earns H1** (follow-up speedup ≥ 5× on Qwen-7B). If
   1.55A rejects H1, the composition is moot — the compound floor
   is bounded by the weaker lever.
2. **Phase 1.54 decode acceleration** lands (frame-decode ≥ 2×
   or bypass of redundant decode). Otherwise decode dominates on
   long clips and KV-warmth savings are invisible.

## Hypotheses

- **H1 (aggregate long-clip e2e speedup).** On VideoMME long
  bucket (n=10 items), KV + decode composition achieves
  aggregate e2e ≥ **2.0×** vs baseline. Currently the
  arithmetic-ceiling caps us at 1.31× for long items under our
  existing regime. The compound claim must clear that ceiling
  meaningfully. **Falsification:** aggregate ≤ 1.5× → composition
  is not multiplicative; one lever is dominated.

- **H2 (no new accuracy regression).** Compound Δacc stays within
  ±0.05 of the equivalent per-lever baselines. **Falsification:**
  Δacc < -0.10 → interaction between persistent KV and decode
  acceleration has an unexpected accuracy cost.

- **H3 (peak RSS under compound load).** Peak RSS ≤ 13 GB across
  the long-clip session. Both KV caches AND decode-accel buffers
  coexist. **Falsification:** > 14 GB → session driver needs
  bounded eviction.

## Decision rules

- H1 earns → compound claim goes in paper §2.13 as "reproduced on
  Qwen-7B/M3 Air within claim #13's C-CEILING band." High-value
  SOTA-facing number.
- H1 middle (1.5× ≤ x < 2.0×) → report as partial compound; the
  gap to the pre-release source's 2×+ story is explained by regime (smaller model,
  less prefill to amortize).
- H1 rejects → note which lever is gating (KV-warmth is invisible
  means prefill is not the bottleneck on long; decode-accel is
  invisible means generate dominates). Either way, the deployment
  latency story needs a different composition.

## Runtime estimate (benchmark-only)

- Baseline (no KV, no decode-accel): ~28 min (matches 32f long
  baseline already run).
- Treatment (KV + decode-accel): predicted 2× faster → ~14 min.
- **Total: ~45 min** per long-bucket composition pass, plus
  matched-control short/medium-bucket checks (~20 min).

## Scope — what 1.55B does NOT answer

- Cross-video session state — one video per session.
- Gemma 4 reproduction — parallel queue if Qwen lands cleanly.
- 32f composition — stay at 16f (long-bucket context where
  ceiling-gap is biggest).

## Cross-references

- `2026-04-19-phase-1_55A-persistent-kv-reproduction-prereg.md`
- `2026-04-18-phase-1_54-video-decode-acceleration-prereg.md`
- `pre-release external source` §2.13.3, §2.13.4
- Claim #13 (C-CEILING) — composition test extends arithmetic.

## Status

- [ ] 1.55A earns H1
- [ ] 1.54 decode-accel lands
- [ ] Compound driver (`run_kv_cache_session.py` +
      `--decode-accel`) lands
- [ ] Runs + findings
