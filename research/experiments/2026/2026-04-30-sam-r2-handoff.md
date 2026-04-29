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
| **B1 (broken-cache diagnostic)** | DIAGNOSTIC — DO NOT cite as 26B C-PERSIST speedup. 10× speedup numbers were measured on the same broken cache path B0b caught. Findings doc IS honest (`closed-arch-blocked`). | `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b1_cpersist_replication*` |
| **B4-adjacent (post-ViT hard prune)** | NEGATIVE — hard-prune does NOT pay off on this stack. 8f median 0.757× (slower); 32f 1.042×. Useful null evidence + C-CEILING limitations data. NOT strict sparse-ViT Track B. | `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b4_sparse_vit_ceiling*` |

## Step 1 — install a CORRECTNESS-CONTROL guard (do not pursue a speedup-preserving shim)

**This step changed after a second-round review.** The original draft
proposed a shim that cleared `RotatingKVCache` layers and let mlx-vlm's
`stream_generate` continue to trim `input_ids = input_ids[:, prefix_len:]`.
That is broken: the model would receive only suffix tokens, so SWA
layers (which got their cache cleared) would be missing the entire
prefix's attention context, while full-attention layers would still
have the prefix in cache. Per-layer prompt state would be inconsistent
and the model output would diverge from the dense baseline for a
second, different reason than the one we are diagnosing.

The correct r2 step is a **diagnostic correctness control**: when any
`RotatingKVCache` is present in the prompt cache, **disable cross-turn
cache reuse entirely** for that turn. Forces full re-prefill on cross-
turn. Slow but correct. This proves the bug is in the cache-reuse path
and unblocks B0b's gate (the gate measures correctness, not speedup).

Drop this at the top of
`scripts/run_sam_b0b_cache_correctness.py` AFTER the `from mlx_vlm import …`
imports. **Do not** hand-trim cache entries; let mlx-vlm see no cache
state at all on cross-turn:

```python
# --- BEGIN B0b correctness-control guard ---
# Background: mlx_vlm/generate.py:671-697 (mlx-vlm 0.4.4) flat-slices
# c.keys[:, :, :prefix_len, :] for every prompt-cache entry. That is
# correct for KVCache (Qwen, full-attention everywhere) but corrupts
# RotatingKVCache (Gemma 4 SWA layers — slot 0 of a rotated buffer is
# not the oldest temporal token). Combined with the input_ids trim on
# the same path, partial-cache reuse on Gemma 4 26B-A4B is unsafe.
#
# Until a topology-aware vendor patch lands, this guard refuses to
# reuse the cache cross-turn whenever any RotatingKVCache is present.
# The result: B0b's correctness gate can pass; the C-PERSIST speedup
# claim on Gemma 26B remains BLOCKED until the upstream fix.
import mlx_vlm.generate as _gen
from mlx_lm.models.cache import RotatingKVCache  # type: ignore

_orig_stream_generate = _gen.stream_generate

# Sticky module-level flag. The runner reads this AFTER every
# stream_generate call to decide whether to emit "cache-reuse" or
# "guarded full-refill" metadata for that row. Reset by the runner
# before the next call.
B0B_GUARD_TRIGGERED = False

def _correctness_guard_stream_generate(*args, **kwargs):
    global B0B_GUARD_TRIGGERED
    B0B_GUARD_TRIGGERED = False
    cache_state = kwargs.get("prompt_cache_state")
    if cache_state is not None and getattr(cache_state, "cache", None):
        if any(isinstance(c, RotatingKVCache) for c in cache_state.cache):
            # Refuse cross-turn cache reuse on mixed-topology models.
            # Force full re-prefill. mlx-vlm sees no cache, takes the
            # cold path, and produces a correctness-clean output.
            kwargs["prompt_cache_state"] = None
            B0B_GUARD_TRIGGERED = True
    return _orig_stream_generate(*args, **kwargs)

_gen.stream_generate = _correctness_guard_stream_generate
# --- END B0b correctness-control guard ---
```

### Step 1b — patch the cross-turn row emission to honour the guard

Without this, rows from a guarded full-refill will falsely advertise
cache reuse. The current runner emits hard-coded
`policy="prompt_cache_state_cross_turn_chained"`, `vit_calls=0`,
`prefix_hit=cross["n_input_tokens"]`, `prefix_coverage=1.0` regardless
of whether the cache was actually reused (lines 743-761 of
`scripts/run_sam_b0b_cache_correctness.py`). Replace that block with
guard-aware metadata, and add a `cache_guard_triggered` field to
`make_row` (~3 lines change to the make_row signature too):

```python
# In the cross-turn row append (was: lines 740-762):
guard_fired = bool(B0B_GUARD_TRIGGERED)  # reads the module flag
rows.append(make_row(
    **base_kw,
    pair_key=f"v={it['video_id']}/q={q_idx}/cross",
    arm="cross_turn_warm",
    baseline_arm="cold_dense",
    policy=(
        "full_refill_guard_rotating_kv"  # guard fired -> no cache reuse
        if guard_fired
        else "prompt_cache_state_cross_turn_chained"
    ),
    baseline_policy="cold_dense_no_cache",
    comparator_arm="cold_dense",
    input_ids_hash=cross["input_ids_hash"],
    raw_response=cross["output_text"],
    session_choice=cross_choice,
    session_correct=cross_correct,
    session_parse_failure=cross_pf,
    prompt_tokens=cross["n_input_tokens"],
    generation_tokens=cross["n_output_tokens"],
    prefill_ms=cross["prefill_ms"],
    generate_ms=cross["generate_ms"],
    repair_prefill_ms=None,
    end_to_end_ms=cross["wall_time_ms"],
    vit_calls=1 if guard_fired else 0,
    prefix_hit=0 if guard_fired else cross["n_input_tokens"],
    prefix_coverage=0.0 if guard_fired else 1.0,
    cache_guard_triggered=guard_fired,  # new field; thread through make_row
))
```

The `make_row` signature at line 388 needs a new
`cache_guard_triggered: bool` parameter that lands in the row dict
(default `False` for backward-compat with B5/B3 row emitters that
don't use the guard). The summary aggregator should then count rows
by `effective_policy` so the gate can distinguish "guarded full-
refill PASSES" from "actual cache reuse PASSES" — they are different
scientific outcomes.

The same emission bug exists in `scripts/run_sam_b1_cpersist_replication.py`
around lines 534-535 and 562-563. If you ever rerun B1 under the same
guard, apply the same patch there. **Until B1 is rerun under the
guard, do not cite its 10× speedup numbers as a 26B C-PERSIST result
— B1 ran on the broken cache path.**

## Step 2 — smoke-validate the guard (≤30 min)

```bash
./.venv/bin/python scripts/run_sam_b0b_cache_correctness.py \
  --smoke \
  --out research/experiments/2026/artifacts/sam_scaleout_m5_r2_20260430/sam_b0b_cache_correctness_smoke.jsonl
```

`--smoke` sets `n_videos=1`. With the default 3 questions per video,
this gives 1 video × 3 questions × {within_turn, cross_turn} = 6 rows
plus 3 cold_dense baselines = 9 rows total. Runs in ~5–10 minutes on
M5.

Pass criterion (read from the resulting `*_summary.json`):
- `cross_turn_warm.text_diffs == 0` — guard prevents corruption.
- `cross_turn_warm.choice_diffs == 0` — answers identical to dense.
- `cross_turn_warm.correctness_diffs == 0`.
- `within_turn_cache_replay.text_diffs == 0` (positive control still
  passes, because within-turn replay short-circuits the trim block
  entirely — `prefix_len == input_ids.shape[1]` so the buggy code is
  never executed).
- `cross_turn_warm` per-turn timing should be ~comparable to a cold
  prefill (the speedup is intentionally surrendered).
- **Every cross-turn row has `cache_guard_triggered = true` and
  `policy = "full_refill_guard_rotating_kv"`** — confirms the guard
  fired and the metadata is honest. If any row reports
  `policy = "prompt_cache_state_cross_turn_chained"` with
  `cache_guard_triggered = false`, the guard didn't trigger when it
  should have; investigate before scaling.

Falsifier: any `text_diff ≥ 1` on `cross_turn_warm` would mean there
is a SECOND bug class — most likely position-ID continuation across
turns, since Gemma uses absolute positions and the old prefix's
positions would need to chain into the new turn's. If smoke fails,
stop, write a fresh findings note, and pursue the position-ID
hypothesis before going further.

## Step 3 — full B0b rerun (after smoke passes; ~1h on M5)

```bash
./.venv/bin/python scripts/run_sam_b0b_cache_correctness.py \
  --out research/experiments/2026/artifacts/sam_scaleout_m5_r2_20260430/sam_b0b_cache_correctness.jsonl
```

Expected: 42 rows (7 videos × 3 questions × {within, cross}), gate
PASS on both arms. Commit as
`research(sam-r2): B0b -- cache-correctness gate PASS under
correctness-control guard (cross-turn reuse disabled on Gemma 26B
mixed-topology)`. The findings doc should explicitly state that the
PASS is achieved by **disabling** cross-turn cache reuse, and that the
C-PERSIST speedup question on Gemma 26B remains OPEN until an upstream
mlx-vlm topology-aware trim lands.

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

1. **B0b correctness-control guard** — `fix(sam-r2): correctness-
   control guard disabling cross-turn cache reuse on Gemma 26B mixed
   topology`. Just the patched `run_sam_b0b_cache_correctness.py`. The
   commit message must call out (a) the root cause is mlx-vlm 0.4.4's
   flat-trim of `RotatingKVCache`, (b) this is a correctness control
   not a speedup-preserving fix, (c) the speedup question is now an
   open architecture boundary that requires a topology-aware upstream
   patch.
2. **B0b smoke artifacts** — `research(sam-r2): B0b smoke -- gate PASS
   under correctness-control guard`. ~3 row JSONL.
3. **B0b full artifacts** — `research(sam-r2): B0b full -- gate PASS,
   42 rows under correctness-control guard`. Findings doc status moves
   to `closed-correctness-control / open-speedup-boundary`. Make the
   "speedup BLOCKED on Gemma 26B" framing explicit; do not let the
   PASS imply C-PERSIST works on Gemma 26B today.
4. **S0 / S1 / S2** — separate `research(sam-r2): S0 -- ...`, etc.

If any phase fails its gate, commit the artifacts anyway with
`status: closed-arch-blocked` or `closed-partial` framing — the
negative result is still evidence for the paper.

### Future work (do NOT do in r2; this is post-paper)

5. **Topology-aware upstream fix to mlx-vlm.** Replace the inline
   slice at `mlx_vlm/generate.py:687-697` with a call to
   `mlx_lm.models.cache.trim_prompt_cache(prompt_cache, n_to_keep)`
   that respects each cache's `is_trimmable()`. For
   `RotatingKVCache.is_trimmable() == False`, the model.forward path
   needs a way to re-prefill that single layer's prefix while still
   reusing other layers' caches. This is a real upstream contribution
   to mlx-vlm (and possibly mlx-lm) and unlocks C-PERSIST on every
   Gemma family that uses SWA. Out of scope for r2; track as a
   separate engineering project.

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
