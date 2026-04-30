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

## Step 0a — finish the current Sam run first, THEN start r2

If Sam still has a run going on `sam/scaleout-m5-20260429`, **let it
finish, commit and push the artifacts, then read this doc**. r2 is
explicitly built on top of what's already in your run, not a parallel
branch. Do not interrupt a productive M5 job to start r2.

When the current run is done:

1. Commit any uncommitted artifacts on `sam/scaleout-m5-20260429`.
2. `git push origin sam/scaleout-m5-20260429` so we can cherry-pick
   anything new from your branch (we already imported B0b/B1/B2/B3/B4-adj/B5
   on main as of this doc; if you've added more since, we will pick
   the new commits selectively before you start r2).

## Step 0b — branch + sync

```bash
cd ~/path/to/codec-through
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c sam/scaleout-m5-r2-20260430
```

After the pull, verify the cherry-picks landed and our local fixes
are present (commit-presence checks, since `git log -10` will keep
moving as new commits land):

```bash
# Sam B0b/B1/B2/B3/B4-adj/B5 commits all present?
git rev-list --count main ^$(git merge-base origin/sam/scaleout-m5-20260429 main) \
  -- 'research/experiments/2026/artifacts/sam_scaleout_m5_20260429/**'
# expect: > 0

# Local fixes preserved?
grep -c "unique_baselines" scripts/run_phase1_55L_many_turn_cpersist.py
# expect: 3
grep -c "start_new_session" scripts/run_phase2_local_chain.py
# expect: 1

# Artifact files actually exist on disk?
test -f research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b2_many_turn_horizon.jsonl && echo OK B2
test -f research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b1_cpersist_replication.jsonl && echo OK B1
test -f research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b4_sparse_vit_ceiling.jsonl && echo OK B4
```

If any of those checks fail, stop — main is in an unexpected state
and you should sync with the team before proceeding.

## What NOT to re-run

These artifacts are already on main. Do not regenerate them; reading
the JSONL or summaries is fine.

| Phase | Status | Where |
|---|---|---|
| B5 1937 | PASS — 0 correctness deltas, CI95 [0.0, 0.0] | `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b5_s4_accuracy_1937.jsonl` |
| B5 513 | PASS — 513 byte-identical raw paired | `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b5_s4_raw_paired_513.jsonl` |
| B3 protocol | PASS schema; partial mechanism — `low_fps_dense` 17/22 wins matched 4-frame budget | `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b3_streaming_baselines.jsonl` |
| **B1 (broken-cache diagnostic)** | DIAGNOSTIC — DO NOT cite as 26B C-PERSIST speedup. 10× speedup numbers were measured on the same broken cache path B0b caught. Findings doc IS honest (`closed-arch-blocked`). | `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b1_cpersist_replication*` |
| **B2 (many-turn horizon)** | DIAGNOSTIC — `correct` fields in B2 mean **text-identical-to-cold-dense**, not ground-truth correctness (every row has `session_correct=False, baseline_correct=False, session_choice=None`). Adaptive arm achieves 99% text agreement after the first turn but at 0.84× speedup; fixed_k1 has 28× speedup but 33% text agreement (broken cache). Cite as text-stability data, never as semantic correctness. | `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b2_many_turn_horizon*` |
| **B4-adjacent (post-ViT hard prune)** | NEGATIVE at fixed frames: 8f median **0.757× (slower; 30% overhead)**; 32f median **1.042× (essentially flat)**; 0/10 byte-identical. The earlier "~1.5× ingestion-density" reframe in some docs is NOT supported by this artifact (would need fixed-wall-clock variable-frames experiment). NOT strict sparse-ViT Track B. | `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b4_sparse_vit_ceiling*` |

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
`scripts/run_sam_b0b_cache_correctness.py`).

**Important schema constraint:** `research/schemas/sam_scaleout_artifact_v1.schema.json`
declares `additionalProperties: false`. We **cannot** add a new
field like `cache_guard_triggered`. Encode the same information in
existing fields that already validate:

- `policy`: change the string to `"full_refill_guard_rotating_kv"`
  when the guard fires.
- `policy_params`: a dict (already in the schema), set to
  `{"cache_guard_triggered": true, "guard_reason": "rotating_kv_present", "cache_reuse_disabled": true}`
  when guard fires; `null` when not.
- `provenance_note`: prepend
  `"[B0b r2 guard fired: cross-turn cache reuse disabled because RotatingKVCache present in prompt cache; effective path is full re-prefill] "`
  when guard fires.
- `vit_calls`, `prefix_hit`, `prefix_coverage`: clamp to the
  full-refill values (`1`, `0`, `0.0`) when guard fires.

Replace the cross-turn append block:

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
    policy_params=(
        {
            "cache_guard_triggered": True,
            "guard_reason": "rotating_kv_present",
            "cache_reuse_disabled": True,
        }
        if guard_fired
        else None
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
    provenance_note=(
        "[B0b r2 guard fired: cross-turn cache reuse disabled because "
        "RotatingKVCache present; effective path is full re-prefill] "
        + (base_kw.get("provenance_note") or "")
        if guard_fired
        else base_kw.get("provenance_note")
    ),
))
```

This keeps the row schema-valid AND makes the guarded vs reuse
distinction explicit through `policy` + `policy_params`.

The summary aggregator (`b0b_summarize` or whatever computes the
`*_summary.json`) should count rows by `policy` so the gate can
report "PASS under full-refill guard" vs "PASS under actual cache
reuse" — they are different scientific outcomes.

The same emission bug exists in `scripts/run_sam_b1_cpersist_replication.py`
around lines 534-535 and 562-563. If you ever rerun B1 under the same
guard, apply the same patch there. **Until B1 is rerun under the
guard, do not cite its 10× speedup numbers as a 26B C-PERSIST result
— B1 ran on the broken cache path.**

## Step 2 — smoke-validate the guard (≤10 min)

```bash
./.venv/bin/python scripts/run_sam_b0b_cache_correctness.py \
  --smoke \
  --out research/experiments/2026/artifacts/sam_scaleout_m5_r2_20260430/sam_b0b_cache_correctness_smoke.jsonl
```

**`--smoke` sets `n_videos=1` AND filters questions to just `q1_mc`**
(the multiple-choice question). So a smoke run is exactly **1 video ×
1 question × {within_turn, cross_turn}** = 2 paired rows + 1
`cold_dense` baseline = 3 rows total. ~5–10 minutes on M5.

Pass criterion (read from the resulting `*_summary.json` and JSONL):
- `cross_turn_warm.text_diffs == 0` — guard prevents corruption.
- `cross_turn_warm.choice_diffs == 0` — answers identical to dense.
- `cross_turn_warm.correctness_diffs == 0`.
- `within_turn_cache_replay.text_diffs == 0` (positive control still
  passes, because within-turn replay short-circuits the trim block
  entirely — `prefix_len == input_ids.shape[1]` so the buggy code is
  never executed).
- `cross_turn_warm` per-turn timing should be ~comparable to a cold
  prefill (the speedup is intentionally surrendered).
- **Every cross-turn row has `policy = "full_refill_guard_rotating_kv"`
  and `policy_params.cache_guard_triggered = true`** — confirms the
  guard fired and the metadata is honest. If any cross-turn row reports
  `policy = "prompt_cache_state_cross_turn_chained"` and
  `policy_params == null`, the guard didn't trigger when it should
  have; investigate before scaling.

If you want a slightly larger smoke (e.g. to catch RSS pressure
issues), run **without** `--smoke` but with `--n-videos 1` so all 3
questions of a single video go through:

```bash
./.venv/bin/python scripts/run_sam_b0b_cache_correctness.py \
  --n-videos 1 \
  --out research/experiments/2026/artifacts/sam_scaleout_m5_r2_20260430/sam_b0b_cache_correctness_smoke3q.jsonl
```

That gives 1 vid × 3 q × {within, cross} = 6 paired + 3 baseline = 9
rows, ~15-20 min on M5.

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
the local Air. L=2, kr ∈ {0.25, 0.50, 0.75}, 8f, N=60 short+medium
VideoMME videos (the same combined manifest A4 used), paired vs
dense.

`scripts/run_phase1_51V.py` reads its config from CLI flags
(`--manifest`, `--output`, `--summary` are required; no env vars).
Run one cell per kr:

```bash
OUT=research/experiments/2026/artifacts/sam_S0_gemma26b_track_b_kr_bracket
mkdir -p "$OUT"
for KR in 0.25 0.50 0.75; do
  TAG="L2_kr$(printf '%03d' $(python3 -c "print(int($KR*1000))"))_8f"
  ./.venv/bin/python scripts/run_phase1_51V.py \
    --manifest research/benchmark_manifests/videomme_combined_v1_n60.toml \
    --frame-count 8 \
    --max-tokens 32 \
    --model-path "$HOME/models/Gemma-4-26B-A4B-it-mlx-bf16" \
    --vision-tower-layer 2 \
    --vision-tower-keep-rate "$KR" \
    --rss-guard-mb 80000 \
    --output "$OUT/sparse_${TAG}.jsonl" \
    --summary "$OUT/sparse_${TAG}_summary.json" \
    --allow-dirty
done
```

Then pair vs an 8f dense Gemma 26B reference. If a dense reference
doesn't exist yet, run one with the same CLI but `--vision-tower-keep-rate 1.0`
and a `dense_8f.jsonl` output, then use
`scripts/analyze_phase1_51v_pair.py` (or the analyzer used by our
local 1.51V; check the script tree under `scripts/` for the most
recent pair-summary tool).

Within-turn only — no cross-turn cache. Safe even before the B0b
guard lands.

Risks:
- `run_phase1_51V.py` was authored against Qwen 2.5-VL. The vision-
  tower hook signatures may differ for Gemma 4 (different model class,
  different layer module names). If you get an `AttributeError` on
  `--vision-tower-layer`, dump the model's structure with
  `python -c "from mlx_vlm import load; m,_=load('$MODEL_PATH'); print(m)"`
  and adapt the hook target. Patch + document; do not silently mask.
- If kr=0.25 produces a high parse-failure rate (>20%), still commit
  the artifacts and let the analysis flag it as a Gemma 26B kr
  boundary. That's still useful evidence.

### S1 — Qwen 7B C-PERSIST at 32f / 64f (~1-2h)

Goal: extend C-PERSIST evidence to frame budgets we cannot collect on
the 16 GB Air. **Use the shell wrapper, not the .py directly** — the
.py uses argparse defaults that would write into the local A6 path
and clobber our running chain. The shell wrapper reads the
`PHASE1_55L_*` env vars and translates them to CLI args:

```bash
# 32f run (drop refresh10 to keep within budget)
PHASE1_55L_OUT_DIR=research/experiments/2026/artifacts/sam_S1_qwen_long_evidence_cpersist_32f \
PHASE1_55L_VIDEO_IDS=037,100,116 \
PHASE1_55L_TURN_COUNTS=10,20 \
PHASE1_55L_POLICIES=fixed_k1,adaptive_post_q2 \
PHASE1_55L_FRAME_COUNT=32 \
RSS_GUARD_MB=80000 \
bash scripts/run_phase1_55L_many_turn_cpersist.sh

# 64f run (only if 32f was healthy and didn't OOM)
PHASE1_55L_OUT_DIR=research/experiments/2026/artifacts/sam_S1_qwen_long_evidence_cpersist_64f \
PHASE1_55L_VIDEO_IDS=037,100,116 \
PHASE1_55L_TURN_COUNTS=10,20 \
PHASE1_55L_POLICIES=fixed_k1,adaptive_post_q2 \
PHASE1_55L_FRAME_COUNT=64 \
RSS_GUARD_MB=80000 \
bash scripts/run_phase1_55L_many_turn_cpersist.sh
```

Qwen 2.5-VL-7B has KVCache only — no SWA — so the mlx-vlm trim is
safe. Sam does not need the SWA guard from Step 1 for S1.

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
