# Phase 1.55A — Persistent LLM KV-cache follow-up latency (the pre-release source §2.13.3 REPRODUCTION, PREREG)

**Status:** preregistration, 2026-04-19. Local reproduction of a
**measured** pre-release source result; not a Codex hypothesis.

## Provenance correction

Earlier drafts of 1.55 framed persistent KV-cache as "Codex round-21
extension" / "not a reproduction of a documented pre-release source claim."
This was wrong.

The pre-release external source §2.13.3 (lines 410-430;
removed from the OSS tree, summarized in `docs/claim-register.md`) reports a measured persistent-KV result on Gemma
4 26B × MLX: N=7 videos × 3 questions = 20 queries, first-query
latency 1.9–17.7 s, follow-up latency uniformly sub-2 s (median
0.8 s), **10–18× follow-up speedup**, zero accuracy change on the
20-item subset. The mechanism is `PromptCacheState` + prefix
matching allocated per video, threaded through sequential queries.

The pre-release seed copy was frozen before §2.13.3 landed; that
is the source of the provenance confusion. The external source was
638 lines and §2.13.3 is real measured work.

1.55 is therefore reframed as a local reproduction target, split
into two sub-phases:

- **1.55A (this prereg)**: follow-up latency reproduction on our
  hardware stack (M3 Air 16 GB) using the same `PromptCacheState`
  + prefix-matching API. Measures whether the 10–18× follow-up
  speedup claim generalizes off the pre-release source's M5 Max hardware and onto
  our smaller-model × smaller-Mac regime.
- **1.55B (separate prereg, deferred)**: composition with Phase
  1.54 decode acceleration (what was previously H3 of the combined
  1.55 prereg). That composition question is orthogonal to the
  follow-up-latency question and should not block 1.55A.

## Why this matters (SOTA impact)

Follow-up latency is the highest-product-relevance number in
the whole codec-through story. The "conversational ambient agent"
deployment narrative — "once a video is ingested, follow-up
questions are conversational" — hinges on follow-up queries being
sub-second. the pre-release source shows this is measured-real. We need to show it
holds on our hardware class (16 GB Mac, Qwen 7B-4bit) so that the
paper's deployment-regime claims extend beyond M5 Max / Gemma 26B.

## Gating (corrected — much weaker than prior draft)

Blocked on: **none** of the prior gates.

- ~~`mlx-vlm` KV-cache handle:~~ our local mlx-vlm has
  `PromptCacheState` + `find_prefix_length` in `mlx_vlm.generate`
  (verified 2026-04-19). No fork needed.
- ~~Phase 1.54 decode acceleration:~~ composition is 1.55B, not
  1.55A. 1.55A can land now.
- ~~Phase 1.30 streaming harness:~~ 1.55A measures latency on
  repeated-query patterns *against the same video features*; a
  full streaming harness is nice-to-have, not load-bearing.

Required for 1.55A:

- [ ] Minimal session driver `scripts/run_kv_cache_session.py`
      that: (a) loads features once per video, (b) creates a
      `PromptCacheState`, (c) runs N questions sequentially on
      the same video while re-using the cache via prefix match,
      (d) logs first-query and follow-up-query latency per clip.
- [ ] Question corpus: use the 3 existing VideoMME questions per
      clip from our `videomme_dev_v1` manifest (no synthesized
      paraphrases needed for reproduction — the pre-release source's protocol matches
      exactly). 7 clips × 3 questions = 21 queries, matching the pre-release source.
- [ ] Cache-hit verification: assert `find_prefix_length` returns
      a positive value on Q2, Q3 of each clip; fail loudly if not.

## Hypotheses

Pre-registered against the pre-release source's measured numbers:

- **H1 (follow-up speedup magnitude).** On Qwen 2.5-VL-7B-4bit
  (our primary model), median follow-up generate time is
  **≤ 3 s** and follow-up speedup is **≥ 5×** relative to
  first-query. the pre-release source measures 0.8 s median and 10–18× on Gemma
  4 26B. Because our model is smaller *and* 4-bit, we expect
  absolute latencies lower than the pre-release source's but speedup possibly lower
  (smaller prefill fraction to amortize). **Falsification:**
  median follow-up ≥ 5 s, or speedup ≤ 2× → persistent-KV on our
  stack is not delivering the deployment story.

- **H2 (accuracy preservation).** 21-query session accuracy is
  within ±0.05 absolute of the equivalent 21 cold-start
  evaluations on the same items. the pre-release source saw zero change on 20 items.
  **Falsification:** |Δ acc| > 0.10 → cache threading introduces
  a quality regression.

- **H3 (prefix-hit coverage).** On Q2+Q3, `find_prefix_length`
  returns a value covering ≥ 90% of the feature-buffer tokens
  (video features are stable between questions on the same clip).
  **Falsification:** coverage < 50% → prefix matching is
  failing, likely due to tokenizer instability or feature buffer
  re-ordering.

- **H4 (peak RSS headroom).** Peak RSS across the session stays
  **≤ 13 GB** on 16 GB Mac. The session retains one
  `PromptCacheState` per clip in memory; 7 clips × ~100 MB/cache
  is the back-of-envelope ceiling. **Falsification:**
  peak RSS > 14 GB → session driver needs bounded cache eviction
  before scaling to larger N.

## Acceptance matrix

| Hypothesis | Earn | Reject |
|------------|------|--------|
| H1 | median follow-up ≤ 3 s AND speedup ≥ 5× | median ≥ 5 s OR speedup ≤ 2× |
| H2 | Δacc ∈ [-0.05, +0.05] | \|Δacc\| > 0.10 |
| H3 | prefix coverage ≥ 90% on Q2+Q3 | < 50% |
| H4 | peak RSS ≤ 13 GB | > 14 GB |

Middle bands mean "partially reproduced; document and investigate."

## Scope — what 1.55A does NOT answer

- Decode acceleration composition — deferred to 1.55B.
- Streaming-buffer accumulation under active video ingestion —
  deferred to 1.30 proper.
- Cross-video session pollution — not tested here (one cache per
  video).
- Gemma 4 reproduction — deferred; if 1.55A lands cleanly on Qwen,
  queue a parallel Gemma run to compare follow-up speedup across
  models. This is the strongest SOTA-facing number in the paper.

## Measurement protocol

- **Benchmark:** VideoMME dev `videomme_dev_v1.toml`, 7 items
  selected from short (<4 min) bucket to minimize first-query
  cost and maximize follow-up-speedup signal. Short-bucket items
  are ~3,300 prompt tokens at 8f, matching the pre-release source's feature-buffer
  regime (18-317 features × ~256 tokens ≈ 4.6K-81K tokens; we
  sit at the low end with 8f prefill).
- **Drivers compared:**
  - Baseline: cold-start per-question, current
    `run_benchmark_track_a.py` chunk_size=1.
  - Treatment: new `run_kv_cache_session.py` with
    `PromptCacheState` threaded through 3 sequential questions
    per clip.
- **Artifacts:** `research/experiments/2026/artifacts/
  phase1_55A_persistent_kv_qwen/session_qwen7b_n7.jsonl` +
  per-query timing, cache-hit coverage, peak RSS.

## Runtime estimate (benchmark-only)

- Baseline: 21 queries × ~35 s/query (short bucket at 8f) ≈
  12 min.
- Treatment: 7 × (1 × ~35 s first + 2 × ~3 s follow-up estimated)
  ≈ 5 min.
- **Total: ~17 min wall-clock** on M3 Air for H1-H4.

## Decision rules after execution

- H1+H2+H3+H4 all earn → claim a real follow-up-speedup
  reproduction on Qwen-7B/M3 Air regime. Add to paper §2.13
  pre-release reproduction line. Queue 1.55B (composition with 1.54) and
  a Gemma parallel-run.
- H1 earns but H2 rejects → cache threading has a correctness
  bug; halt and investigate before reporting.
- H3 rejects → the `PromptCacheState` + prefix API is not
  behaving as documented; file a note, investigate, possibly
  trim/re-sync.
- H1 rejects cleanly (speedup ≤ 2×) → the story that motivates
  the paper's conversational-agent framing does NOT hold on
  small-Mac / small-model regime. This is a major finding and
  shapes which deployment regimes we claim.

## Cross-references

- pre-release external source §2.13.3 (authoritative
  the pre-release source measurement, lines 410-430).
- pre-release seed copy, removed from the OSS tree and preserved in git
  history (frozen before §2.13.3 landed).
- `research/experiments/2026/2026-04-19-phase-1_55-persistent-kv-prereg.md`
  (superseded by this file + 1.55B).
- Phase 1.54 (decode acceleration — composition target for 1.55B).
- Claim matrix row 11 (streaming composition — this lands as a
  strengthener, not a new claim).

## Status

- [ ] `PromptCacheState` API verified in our mlx-vlm (done 2026-04-19)
- [ ] `run_kv_cache_session.py` driver landed
- [ ] Baseline + treatment runs
- [ ] Findings doc + decision against H1-H4
- [ ] Claim-matrix update
