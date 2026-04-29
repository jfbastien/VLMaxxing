---
date: 2026-04-30
status: integration plan after Sam scaleout-m5 cherry-pick + codex round-36 review
related:
  - research/experiments/2026/2026-04-29-phase-B0b-sam-cache-correctness-findings.md
  - research/experiments/2026/2026-04-29-phase-B3-sam-streaming-baselines-findings.md
  - research/experiments/2026/2026-04-29-phase-B5-sam-s4-reexport-findings.md
  - research/experiments/2026/2026-04-29-phase-2-final-validation.md
---

# Sam scaleout-m5 integration + next experiments

This note covers what landed when Sam's scaleout-m5-20260429 branch was
cherry-picked onto main, what codex round-36 corrected in our local
phase-2 framing, the verified root cause of Sam's B0b failure, and the
experiments Sam should run concurrently while we wait for our local A6
chain to finish on the 16 GB Air.

## What landed (cherry-picks ac97708…68e5294)

7 commits, no conflicts with our local A6 / chain-runner fixes. Files
touched are exclusively under `scripts/run_sam_b*` and
`research/experiments/2026/{...sam...}/**`.

- B0b runner + artifacts: `closed-arch-blocked` — 14/19 cross-turn rows
  diverge after parse-failure exclusion (16/21 raw, 2 parse-failures).
  Within-turn replay is byte-identical 21/21 (positive control).
- B3 runner + artifacts: `closed-earned-protocol / closed-partial-mech`
  — at matched 4-frame fixed-evidence budget, `low_fps_dense` 17/22
  beats `screenshot_polling` 13/22 = `sam_policy(proxy)` 13/22 =
  `recency_last_k` 12/22. Sam's `sam_policy` here is a T0+window
  proxy, not the full cache-shift mechanism; the proxy can't argue
  against codec-through on the throughput axis (E3).
- B5 re-export: both bounded claims pass schema gate. 1937 sparse-
  sampled rows have zero correctness delta with CI95 [0.0, 0.0]; 513
  raw-paired rows have byte-identical text. The 513 figure must NOT be
  generalised back to 1937 in paper prose.

Sub-agent audit (a7bc3a7bba7170da4) verified all three claims against
the underlying JSONL and cross-checked schema compliance. Wording
fixes still owed in the findings docs (see "Wording fixes" below).

## Codex round-36 corrections to our local framing

Codex flagged three of my (Claude's) framings as too strong; all three
are right:

1. **A3 1.62D row count**: my commit `fccfa2f` says "180/180 paired
   queries". The actual paired count is **171** (the combined VideoMME
   dev+holdout manifest is 60 unique videos but only 171 question slots
   after manifest filtering, not 60 × 3 = 180). The science is
   unchanged; the count is wrong by a fact.
2. **A4 1.63I framing**: my commit `e1aa8bc` calls
   kr_effective=0.8125 "the new fidelity-safe peak" displacing kr=0.85.
   Codex correctly notes that no cell in the bracket passes ALL gates
   simultaneously: cell 1 (kr=0.78→0.75) misses fidelity, cells 2 and 3
   (kr=0.80, 0.82 → both 0.8125) each have 1/60 sparse parse failure
   flipping `pass_format`, and the C-CEILING residual is large
   (`actual − predicted` ≈ +0.12 to +0.20). The accurate framing is
   "format-caveated high-gain candidate; confirms discrete keep-rate
   boundary at 1/16 = 0.0625 quantum per frame on this Qwen 16f path"
   — it's still useful evidence, but it does not replace kr=0.85 as a
   format-clean fidelity-safe operating point.
3. **A6 1.55L baseline rows**: paper prose must say "560 baseline
   rows are deterministic replicas of 21 unique stateless dense runs"
   — they are valid for per-turn pairing and answer drift, but they
   are NOT independent timing samples and must not be cited as such.

These corrections will land in the paper-update notes; the underlying
artifacts are unchanged.

## B0b root cause: mlx-vlm flat-trim is wrong on mixed SWA topology

Sub-agent triage (a346c190099427202) confirmed the SWA-trim hypothesis
by reading mlx-vlm + mlx-lm sources:

- `mlx_vlm/generate.py:687-697` slices `c.keys[:, :, :prefix_len, :]`
  and `c.values[:, :, :prefix_len, :]` for **every** cache entry, then
  sets `c.offset = prefix_len`.
- This is correct for `KVCache` (a flat append-only buffer, used for
  every layer in Qwen 2.5-VL), but it is **wrong for**
  `RotatingKVCache` — a circular buffer with a `_idx` rotation pointer
  whose slot 0 is not the oldest temporal token after the cache is
  full.
- `Gemma4TextModel.make_cache` (mlx-lm `models/gemma4_text.py:653`)
  builds 25 `RotatingKVCache` (sliding-window layers) + 5 `KVCache`
  (full-attention layers). The 25 SWA caches get clobbered by the
  flat-trim, and the cache becomes internally inconsistent —
  divergence at decode time on the 26 of 30 layers that use SWA.
- mlx-lm already exposes `trim_prompt_cache` / per-cache `c.trim(n)`
  that respect topology; mlx-vlm bypasses these APIs and reaches into
  `c.keys` / `c.values` directly. That bypass is the bug.

Within-turn cache replay does not exercise the trim path (the cache is
fresh), which is why the within-turn arm of B0b is byte-identical.

### Recommended fix (B0b-fix-v1)

Smallest correctness-preserving patch: in
`scripts/run_sam_b0b_cache_correctness.py`, monkey-patch the trim block
to skip `RotatingKVCache` entries — i.e. force full re-prefill on SWA
layers and reuse cache only for the 5 full-attention layers
("full-attention-only persist"). Sketch:

```python
# At module top, after imports:
import mlx_vlm.generate as _gen
from mlx_lm.models.cache import RotatingKVCache, KVCache

_original_advance_prompt_cache = getattr(_gen, "_advance_prompt_cache", None)

def _safe_trim_prompt_cache(prompt_cache, prefix_len: int) -> None:
    """Skip the trim for RotatingKVCache entries (SWA layers); flat-trim
    only the KVCache entries (full-attention layers). Forces a fresh
    prefill on SWA layers, which is correct but slower than ideal."""
    for c in prompt_cache:
        if isinstance(c, RotatingKVCache):
            # Reset SWA layer's cache for safe re-prefill of this prefix
            c.keys = None
            c.values = None
            c.offset = 0
            c._idx = 0
        else:
            # KVCache: flat slice is safe
            c.keys = c.keys[:, :, :prefix_len, :]
            c.values = c.values[:, :, :prefix_len, :]
            c.offset = prefix_len
```

Then in `Harness.run` between turns, when reusing
`prompt_cache_state`, call `_safe_trim_prompt_cache(...)` instead of
the inline mlx-vlm trim.

The cleanest version is a vendor patch to mlx-vlm that calls
`mlx_lm.models.cache.trim_prompt_cache(prompt_cache, n_to_keep)`
which already does the right thing. That is the long-term fix (file
PR upstream); the monkey-patch is the short-term unblocker for B0b.

### Validation experiment (≤30 min on M5)

After the patch, rerun B0b at `--smoke` (1 video × 3 questions):
- **Success**: `text_diffs == 0` on `cross_turn_warm`, all hashes still
  match. SWA-trim is the only divergence source.
- **Falsifier**: any text-diff ≥ 1 → there's a second bug class
  (likely position-id reset across turns; Gemma uses absolute
  positions, and reusing a cache implies position must continue from
  the previous turn, not reset).

If `--smoke` passes, scale to the full 7×3×{within,cross} 42-row run
(~1h on M5).

## Concurrent experiments for Sam (do not wait on B0b fix)

**These are safe to run on Sam's M5 while the B0b SWA fix is in
flight**, because they don't exercise the cross-turn warm-cache trim
path:

### S0 — Gemma 26B Track B kr-bracket cross-arch (HIGH value, ~2-3h)

Run 1.51V (or its M5 analogue) at L=2, kr∈{0.25, 0.50, 0.75}, 8f, on
N=30 short+medium VideoMME videos. Within-turn only — no cross-turn
cache. We don't have a Gemma 26B Track B point in the paper today; this
would replicate our local 1.63E (Gemma 4-E4B at 4B-class) at the
26B-A4B class on M5. Strong cross-arch evidence for C-VISION.

Risk: if M5 doesn't have a 26B-A4B 8f Track B harness yet, Sam should
adapt `scripts/run_phase1_51V.py` (already in the repo, used by our
local A4) to Gemma 26B model path. Should be a config change, not new
code.

### S1 — Qwen 7B C-PERSIST at 32f / 64f (MEDIUM value, ~1-2h)

Our local A6 is bounded at 20f because of the 16 GB RSS guard. Sam's
M5 (128 GB) can push this to 32f and 64f. Use the same `policy_phase`
in `scripts/run_phase1_55L_many_turn_cpersist.py` (now baseline-deduped
on main) with `PHASE1_55L_FRAME_COUNT=32` (or 64) and a small video
subset (e.g. 3 videos × {10, 20} turns × {fixed_k1, adaptive_post_q2}).

This produces a frame-scaling C-PERSIST point we cannot collect
locally and gives the paper a "scales to longer evidence budgets"
claim grounded in real measurement.

Risk: Qwen 2.5-VL-7B Track B uses `KVCache` only — no SWA — so the
mlx-vlm trim path is safe. Cross-turn cache reuse should work cleanly
on Qwen, by the same triage logic.

### S2 — Memory-envelope sweep at frame counts that hit our RSS guard locally (LOW-MED value, ~30 min)

Pure measurement run on M5 — no science gate to pass. For each
(model, frame_count) cell hit by our 12 GB MLX cap locally, sample
peak RSS on M5: Gemma 4 26B at 8f/16f/32f, Qwen 7B at 32f/64f,
Gemma 4-E4B at 32f. Outputs a tighter memory table for the paper's
reproducibility section that doesn't have to caveat "we hit the cap"
on every row.

## Order of operations on M5

1. Start S0 (Gemma 26B Track B kr-bracket) — kicks off largest data.
2. While S0 runs, write the B0b-fix-v1 patch (10 lines) and run the
   `--smoke` validation in parallel (~5 min).
3. If `--smoke` passes, queue full B0b rerun behind S0.
4. Run S1 (Qwen frame-scaling C-PERSIST) after S0 to avoid GPU
   contention.
5. S2 (memory envelope) can run any time; pure observation.

## Wording fixes owed (when Sam's findings docs are next touched)

In Sam's docs:

- B0b: change "16 of 21 paired rows (76%)" to make the parse-failure
  exclusion explicit: "14 of 19 paired rows after excluding 2 matched
  parse failures (74%; 16 of 21 raw)".
- B3: rename `arm="sam_policy"` to `arm="sam_policy_t0_anchor_proxy"`
  in the JSONL (or, less invasively, add a callout box at the top of
  the findings doc that the JSONL string is a proxy and any paper
  reference must say so explicitly).
- B5: keep the 1937-row zero-correctness-delta and 513-row
  byte-identical claims as separate sentences. Never collapse them.

In our docs:

- A3: paired count is 171, not 180.
- A4: kr_eff=0.8125 is a "format-caveated high-gain candidate", not
  a fidelity-safe headline that displaces kr=0.85.
- A6: baseline rows are deterministic replicas of 21 unique stateless
  dense runs (valid for pairing, not independent timing samples).

## What this enables in the paper

- Local Qwen 7B C-PERSIST remains the correctness-preserving headline.
- Sam's B0b becomes a "Gemma 4 26B-A4B mixed-attention topology
  blocks naïve persistent-KV reuse on this mlx-vlm version" boundary
  — a real architecture finding worth a paragraph in the limitations
  section, not a hidden failure.
- Sam's B3 strengthens the "low-FPS dense is a serious matched-budget
  baseline" rebuttal we owed reviewers.
- Sam's B5 imports as same-graph evidence in bounded form (1937 zero-
  correctness-delta on sparse-sampled, 513 byte-identical raw-paired).
- New S0 / S1 / S2 give us cross-arch Gemma 26B Track B, Qwen
  long-evidence C-PERSIST, and a clean memory envelope — three
  paper-grade points we cannot collect locally on the Air.
