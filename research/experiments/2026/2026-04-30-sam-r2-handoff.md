---
date: 2026-04-30
status: operator handoff for sam/scaleout-m5-r2 — skip what passed, fix B0b, add S0/S1/S2
related:
  - research/experiments/2026/2026-04-30-sam-integration-and-next-experiments.md
  - research/experiments/2026/2026-04-29-sam-scaleout-operator-prompt.md
---

# Sam r2 handoff (next M5 run)

This is the concrete operator doc for Sam's next M5 session. Read the
companion narrative `2026-04-30-sam-integration-and-next-experiments.md`
for the why; this doc is just the what.

## TL;DR

- **Pull from main**, cut `sam/scaleout-m5-r2-20260430`.
- **Do not re-run**: B5 (passed), B3 protocol (passed; only prose
  caveat owed), B0b until the SWA-trim patch is in.
- **Re-run after patch**: B0b on the same 7 videos × 3 questions ×
  {within, cross} grid that failed.
- **Add new**: S0 (Gemma 26B Track B kr-bracket), S1 (Qwen 7B
  C-PERSIST at 32f and 64f), S2 (M5 memory envelope).

## Step 0 — branch + sync

```bash
cd ~/path/to/codec-through
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c sam/scaleout-m5-r2-20260430
```

After the pull, verify the cherry-picks landed and our local fixes
are present:

```bash
git log --oneline -10
# expect to see (in order, newest first):
#   68e5294 sam-scaleout-m5: bundle finalization
#   a872ee0 sam-scaleout-m5: B3 -- matched streaming baselines
#   9318f63 sam-scaleout-m5: B3 runner
#   5b70d82 sam-scaleout-m5: B5
#   851e1fa sam-scaleout-m5: B0b -- gate FAILED on cross_turn_warm
#   0a06a5e sam-scaleout-m5: B0b runner
#   ac97708 sam-scaleout-m5: bundle scaffolding
#   cb098fe fix(phase2): chain process-group kill + 1.55L baseline dedup
#   e1aa8bc research(1.63I): land Qwen 16f keep-rate fine bracket
#   fccfa2f research(1.62D): land 4f cold-dense baseline (4f arm complete)

grep -c "unique_baselines" scripts/run_phase1_55L_many_turn_cpersist.py
# expect: 3
grep -c "start_new_session" scripts/run_phase2_local_chain.py
# expect: 1
```

If any of those checks fail, stop — main is in an unexpected state.

## What NOT to re-run

These artifacts are already on main. Do not regenerate them; reading
the JSONL or summaries is fine.

| Phase | Status | Where |
|---|---|---|
| B5 1937 | PASS — 0 correctness deltas, CI95 [0.0, 0.0] | `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b5_s4_accuracy_1937.jsonl` |
| B5 513 | PASS — 513 byte-identical raw paired | `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b5_s4_raw_paired_513.jsonl` |
| B3 protocol | PASS schema; partial mechanism — `low_fps_dense` 17/22 wins matched 4-frame budget | `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b3_streaming_baselines.jsonl` |

## Step 1 — apply the mlx-vlm SWA-trim patch (B0b root cause)

Root cause is `mlx_vlm/generate.py:687-697` doing `c.keys[:, :, :prefix_len, :]`
and `c.values[:, :, :prefix_len, :]` for **every** prompt-cache entry.
That is correct for `KVCache` (full-attention) but wrong for
`RotatingKVCache` (sliding-window) — the slot-0 of a rotated buffer is
not the oldest temporal token. Gemma 4 26B-A4B builds 25
RotatingKVCache + 5 KVCache; Qwen 7B builds only KVCache so it is
unaffected. mlx-lm already exposes `trim_prompt_cache` and per-cache
`c.trim(n)` that respect topology; mlx-vlm bypasses them.

Add this monkey-patch at the top of
`scripts/run_sam_b0b_cache_correctness.py` (and any future B1/B2 26B
runner), AFTER the `from mlx_vlm import …` import:

```python
# --- BEGIN B0b SWA-trim safety patch ---
# mlx-vlm 0.4.4 flat-slices c.keys / c.values on every cache entry, which
# corrupts RotatingKVCache (SWA layers). Force full re-prefill of SWA
# layers and reuse cache only for full-attention (KVCache) layers.
import mlx_vlm.generate as _gen
from mlx_lm.models.cache import RotatingKVCache, KVCache  # type: ignore

def _safe_trim_prompt_cache(prompt_cache, prefix_len: int) -> int:
    """Return the number of layers whose KV was actually preserved."""
    preserved = 0
    for c in prompt_cache:
        if isinstance(c, RotatingKVCache):
            # SWA layer: drop the cache entirely; this layer re-prefills.
            c.keys = None
            c.values = None
            c.offset = 0
            c._idx = 0
        elif isinstance(c, KVCache):
            c.keys = c.keys[:, :, :prefix_len, :]
            c.values = c.values[:, :, :prefix_len, :]
            c.offset = prefix_len
            preserved += 1
        else:
            # Unknown cache type; refuse to touch it (correctness > speed).
            c.keys = None
            c.values = None
            c.offset = 0
    return preserved

# Patch the trim block. Find the function in mlx_vlm.generate that runs
# the slice loop and replace its body. As of 0.4.4 the loop is inside
# stream_generate. The simplest hook is to wrap the cache reuse decision:
_orig_stream_generate = _gen.stream_generate

def _patched_stream_generate(*args, **kwargs):
    # Override the in-process trim. This is brittle to mlx-vlm version
    # bumps; revisit on every dependency upgrade.
    cache_state = kwargs.get("prompt_cache_state")
    if cache_state is not None and getattr(cache_state, "cache", None):
        # Determine prefix_len exactly the way mlx-vlm would, then call
        # our safe trim instead of the inline slice.
        # If mlx-vlm has already exposed prefix_len, use it; otherwise
        # fall back to find_prefix_length.
        from mlx_vlm.utils import find_prefix_length  # type: ignore
        new_token_ids = kwargs.get("token_ids") or kwargs.get("inputs")
        if cache_state.token_ids is not None and new_token_ids is not None:
            prefix_len = find_prefix_length(
                cache_state.token_ids, new_token_ids
            )
            _safe_trim_prompt_cache(cache_state.cache, prefix_len)
            cache_state.token_ids = new_token_ids[:prefix_len]
            # Hand off to the original generator with the cache already
            # trimmed; mlx-vlm will see prefix_len and skip its own slice.
    return _orig_stream_generate(*args, **kwargs)

_gen.stream_generate = _patched_stream_generate
# --- END B0b SWA-trim safety patch ---
```

Notes:
- This is a **shim**, not a vendor patch. Long-term we want to upstream
  a fix that calls `mlx_lm.models.cache.trim_prompt_cache(...)`
  instead of the inline slice. For now the shim unblocks B0b without
  modifying `.venv/`.
- Revisit on every mlx-vlm version bump — the call signature and trim
  location may move.
- This patch DOES NOT change behaviour for Qwen runs; KVCache slicing
  is identical to the inline mlx-vlm slice. Track A (Qwen 7B) is
  unaffected.

## Step 2 — smoke-validate the patch (≤30 min)

```bash
PHASE2_SAM_VIDEOS_LIMIT=1 \
PHASE2_SAM_QUESTIONS_LIMIT=3 \
./.venv/bin/python scripts/run_sam_b0b_cache_correctness.py \
  --output-dir research/experiments/2026/artifacts/sam_scaleout_m5_r2_20260430 \
  --smoke
```

Pass criterion (read from the resulting `*_summary.json`):
- `cross_turn_warm.text_diffs == 0`
- `cross_turn_warm.choice_diffs == 0`
- `cross_turn_warm.correctness_diffs == 0`
- `within_turn_cache_replay.text_diffs == 0` (positive control still passes)

Falsifier: any text-diff ≥ 1 means the SWA trim was not the only bug.
The likely second-bug class is position-ID continuation across turns
(Gemma uses absolute positions; reusing a cache requires the new
turn's position offset to continue the previous turn's, not reset to 0).
If smoke fails, stop and write a fresh findings note before scaling.

## Step 3 — full B0b rerun (after smoke passes; ~1h on M5)

```bash
./.venv/bin/python scripts/run_sam_b0b_cache_correctness.py \
  --output-dir research/experiments/2026/artifacts/sam_scaleout_m5_r2_20260430
```

Expected: 42 rows (7 videos × 3 questions × {within, cross}), gate
PASS on both arms. Commit as a single
`research(sam-r2): B0b -- cache-correctness gate PASS after SWA-trim patch`.

## Step 4 — concurrent experiments (do NOT block on each other)

These are safe to run on M5 while the B0b patch is being smoke-tested
and they don't share state with B0b. Recommended order: S0 first, S1
second, S2 any time.

### S0 — Gemma 26B Track B kr-bracket cross-arch (~2-3h)

Goal: produce a Track B point at 26B-A4B class that we don't have on
the local Air. L=2, kr ∈ {0.25, 0.50, 0.75}, 8f, N=30 short+medium
VideoMME videos, paired vs dense.

Adapt `scripts/run_phase1_51V.py` (driver in main, used by our local
A4) for the Gemma 26B path:

```bash
PHASE1_51V_MODEL_PATH=$HOME/models/Gemma-4-26B-A4B-it-mlx-bf16 \
PHASE1_51V_MANIFEST=research/benchmark_manifests/videomme_combined_v1_n60.toml \
PHASE1_51V_OUT_DIR=research/experiments/2026/artifacts/sam_S0_gemma26b_track_b_kr_bracket \
./.venv/bin/python scripts/run_phase1_51V.py \
  --frame-count 8 \
  --vision-tower-layer 2 \
  --vision-tower-keep-rate 0.50 \
  --max-tokens 32 \
  --rss-guard-mb 80000 \
  --output ".../sparse_L2_kr050_8f.jsonl" \
  --summary ".../sparse_L2_kr050_8f_summary.json" \
  --allow-dirty
```

(Repeat for kr=0.25 and kr=0.75; pair against an 8f dense Gemma 26B
reference. If one doesn't exist on M5 yet, build it the same way Sam
built B5's reference.)

Within-turn only — no cross-turn cache. Safe even before the B0b
patch lands.

Risks: if Gemma 26B's 1.51V Track B harness needs adapter changes
(e.g. processor differences), patch and document; do not silently
mask. If kr=0.25 produces a high parse-failure rate (>20%), still
commit the artifacts and let the analysis flag it as a Gemma 26B kr
boundary.

### S1 — Qwen 7B C-PERSIST at 32f / 64f (~1-2h)

Goal: extend C-PERSIST evidence to frame budgets we cannot collect on
the 16 GB Air. Use the **already-fixed** baseline-deduplicated
`scripts/run_phase1_55L_many_turn_cpersist.py` (post-cb098fe). Drop
refresh10 to keep budget tight; keep fixed_k1 + adaptive_post_q2.

```bash
PHASE1_55L_OUT_DIR=research/experiments/2026/artifacts/sam_S1_qwen_long_evidence_cpersist \
PHASE1_55L_VIDEO_IDS=037,100,116 \
PHASE1_55L_TURN_COUNTS=10,20 \
PHASE1_55L_POLICIES=fixed_k1,adaptive_post_q2 \
PHASE1_55L_FRAME_COUNT=32 \
PHASE1_55L_RSS_GUARD_MB=80000 \
./.venv/bin/python scripts/run_phase1_55L_many_turn_cpersist.py
# Repeat with PHASE1_55L_FRAME_COUNT=64 if the 32f run looks healthy
```

Qwen has KVCache only — no SWA — so the mlx-vlm trim is safe. Sam
does not need the SWA patch from Step 1 for S1.

### S2 — M5 memory envelope (~30 min)

Pure measurement. For each (model, frame_count) cell that hits the 12
GB MLX cap on the local Air, sample peak RSS on M5:

| Model | Frame counts to sample |
|---|---|
| Gemma 4 26B-A4B | 8, 16, 32 |
| Qwen 2.5-VL-7B-4bit | 32, 64 |
| Gemma 4-E4B-4bit | 32 |

Reuse our `_peak_rss_gb()` helper from
`scripts/run_phase1_55L_many_turn_cpersist.py`. Output a single JSON
table; commit alongside a one-paragraph findings doc that the paper's
reproducibility section can cite.

## Step 5 — what to commit, in what order

1. **B0b SWA shim** — `fix(sam-r2): mlx-vlm SWA-trim shim for Gemma 4
   26B-A4B`. Just the patched `run_sam_b0b_cache_correctness.py`,
   commit message links to this handoff and the local commit cb098fe
   (chain runner process-group precedent).
2. **B0b smoke artifacts** — `research(sam-r2): B0b smoke -- SWA-trim
   patch passes positive and negative arms`. ~3 row JSONL.
3. **B0b full artifacts** — `research(sam-r2): B0b full -- gate PASS,
   42 rows after SWA fix`. Findings doc rewrites status to
   `closed-earned`.
4. **S0 / S1 / S2** — separate `research(sam-r2): S0 -- ...`, etc.

If any phase fails its gate, commit the artifacts anyway with
`status: closed-arch-blocked` or `closed-partial` framing — the
negative result is still evidence for the paper.

## Step 6 — wording fixes in already-landed Sam findings

These need a small follow-up commit on Sam's r2 branch (or a paper-
update commit on main, whichever is cleaner):

- `2026-04-29-phase-B0b-sam-cache-correctness-findings.md`: change
  "16 of 21 (76%)" → "14 of 19 (74%) after excluding 2 matched
  parse failures (16 of 21 raw)".
- `2026-04-29-phase-B3-sam-streaming-baselines-findings.md`: ensure
  every mention of `sam_policy` says "T0-anchor proxy". Add a callout
  box at the top: "the JSONL `arm=sam_policy` string is a proxy for
  the throughput-axis cache-shift mechanism evaluated under the E3
  protocol; do not cite as evidence against the full mechanism."
- `2026-04-29-phase-B5-sam-s4-reexport-findings.md`: keep the
  "1937-row zero-correctness-delta" and "513-row byte-identical" as
  separate sentences. Never merge.

## Things that block the paper that ARE NOT here

- B1 (26B C-PERSIST replication) — wait until B0b PASSES, then run.
- B2 (26B many-turn streaming) — wait until B0b PASSES.
- B4 (sparse-ViT) — needs a real implementation; deferred to a later
  Sam round.

## Sanity checks before committing

- Every JSONL row schema-validates against
  `research/schemas/sam_scaleout_artifact_v1.schema.json`.
- Every paired arm has matching `input_ids_hash` / `prompt_hash` /
  `frame_hash` (any mismatch is a setup bug, not a science result).
- `parse_failures` counts in the summary use the same definition as
  our local 1.41 / 1.51V harness (matched parse failures are excluded
  from drift).
