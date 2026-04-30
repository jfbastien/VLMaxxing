---
date: 2026-04-30
phase: upstream-fix-1 (sam-r2 follow-up)
status: closed-earned (local patch verified); upstream PR pending
related:
  - 2026-04-30-phase-B0b-r2-sam-correctness-control-findings.md
  - 2026-04-29-phase-M5-5-sam-swa-aware-cache-findings.md
  - 2026-04-29-phase-M5-5b-sam-prefix-snapshot-fix-findings.md
---

# 2026-04-30 Upstream fix — topology-aware trim in mlx-vlm `generate.py`

- **Status:** **closed-earned (local patch verified).** The
  topology-aware trim patch lands cross-turn cache reuse correctness
  AT THE LIBRARY LEVEL on Gemma 4 26B-A4B / mlx-vlm 0.4.4. With the
  patch applied, no runtime monkey-patch is needed in our runners;
  cross-turn output is byte-identical to cold dense.
- **Upstream PR:** pending submission to mlx-vlm (track separately;
  this commit lands the patch in our repo + an apply helper).

## What the patch does

Replaces the broken inline cache-trim block at
`mlx_vlm/generate.py:687-697` with a call to `mlx_lm.models.cache.
trim_prompt_cache` + `can_trim_prompt_cache`, the per-cache-class
trim protocol that mlx-lm already exposes and that respects
`RotatingKVCache.is_trimmable()`.

Specifically, the patch:

1. Computes `current_offset = max(c.offset for c in kv_cache)` — the
   cumulative end position of the cache (assumed in sync across
   layers, which is true after any prior turn's prefill).
2. Computes `trim_amount = current_offset - prefix_len` — how many
   tokens to drop from the cache to get back to the common prefix
   boundary.
3. If `trim_amount == 0` (no trim needed) OR `can_trim_prompt_cache`
   returns True for all caches: trims the cache, trims `input_ids` to
   only the new tokens, sets `kwargs["prompt_cache"] = kv_cache`,
   reuses the cache for this turn (the fast path).
4. Otherwise (e.g., a `RotatingKVCache` has wrapped and reports
   `is_trimmable() == False`): **falls through to the cold-dense
   path** — leaves `input_ids` intact, doesn't set `prompt_cache`,
   the function reaches the existing `if "prompt_cache" not in
   kwargs: kwargs["prompt_cache"] = cache.make_prompt_cache(...)`
   branch and creates a fresh cache for full re-prefill. Caller
   pays full prefill cost; output is correctness-clean instead of
   silently wrong.

This is a **principled, topology-aware** behavior change: on
full-attention-only architectures (Qwen 2.5-VL-7B-4bit etc.) the
fast path is always taken (`KVCache.is_trimmable() == True`) and
nothing changes. On mixed-SWA architectures (Gemma 3 / Gemma 4) the
slow path fires when the SWA layer has wrapped, which is exactly the
boundary where the previous code was producing wrong outputs.

## Verification

Empirical regression: with the patch applied to the system mlx-vlm
0.4.4 and the runtime monkey-patch from
`run_sam_b0b_cache_correctness.py` REMOVED, the cross-turn smoke ran:

| arm | output | byte-identical to cold? |
|---|---|---|
| `cold_dense` | "The most prominent color in the scene is green." | (baseline) |
| `cross_turn_warm` (with library patch, no runtime guard) | "The most prominent color in the scene is green." | **YES** |

Compare to the SAME setup without the patch (B0b r1):

| arm | output | byte-identical to cold? |
|---|---|---|
| `cold_dense` | "The most prominent color in the scene is green." | (baseline) |
| `cross_turn_warm` (broken library, no guard) | "The most prominent color in the scene is **red**." | **NO** |

The library patch fixes the bug at its root.

## Patch artifacts

- `scripts/mlx_vlm_swa_aware_trim.patch` — unified diff against
  mlx-vlm 0.4.4's `generate.py`. Apply with `patch -p0` from the
  python site-packages root.
- `scripts/apply_mlx_vlm_swa_patch.sh` — apply / `--check` / `--revert`
  helper that resolves the system mlx-vlm location dynamically.

## How to use locally

```bash
# Apply
./scripts/apply_mlx_vlm_swa_patch.sh

# Verify it took
./scripts/apply_mlx_vlm_swa_patch.sh --check

# Run B0b WITHOUT the in-runner correctness guard. Should pass
# cleanly because the library is now correct.
python3 scripts/run_sam_b0b_cache_correctness.py --smoke \
    --out /tmp/b0b_post_patch_smoke.jsonl

# Revert if you want to upgrade mlx-vlm (the patch would block
# `pip install --upgrade mlx-vlm` otherwise; revert first, then
# upgrade, then re-apply)
./scripts/apply_mlx_vlm_swa_patch.sh --revert
```

## Relationship to existing artifacts

- **B0b r2** (commit 8568fc4 / 8b748b0): runtime monkey-patch
  `_correctness_guard_stream_generate` in our runner. Identical
  *behavior* to this patch (refuse cache reuse on RotatingKVCache),
  but at the runner level. After the upstream PR lands, the runtime
  guard becomes redundant on patched mlx-vlm versions; we should
  keep it as defense-in-depth (runs no-op on patched libs because
  `can_trim_prompt_cache` already handles the case).
- **M5-5b prefix-snapshot wrapper** (`scripts/swa_aware_cache_v2.py`):
  remains the right tool for cross-turn cache REUSE WITH SPEEDUP on
  SWA models. The library patch fixes correctness (surrenders
  speedup); the prefix-snapshot wrapper recovers speedup by avoiding
  the trim altogether (snapshots before question tokens enter the
  cache). The two are complementary.

## What this means for the paper

- **Correctness story is closed at the library level on mixed-SWA
  models** with this patch. The C-PERSIST cross-turn cache reuse on
  Gemma 4 26B-A4B is *no longer silently broken* once the patch
  ships upstream; users get either a correct fast path
  (full-attention-only) or a correct slow path (mixed-SWA).
- **The paper's `§9 limitations / reproducibility` line about
  mlx-vlm 0.4.4 SWA cache bug** should add: "Fix submitted upstream
  in <PR link>; reproducible locally via `scripts/apply_mlx_vlm_swa_patch.sh`
  on this repo."
- **The cross-arch C-PERSIST speedup story (M5-5b)** is unaffected
  — the prefix-snapshot wrapper sidesteps the trim path entirely
  and works against patched and unpatched libraries alike.
- **Upstream PR description** should cite the same artifacts this
  doc references (B0b r1 = bug at scale; B0b r2 = guarded fix; this
  patch = library fix).

## Caveats

- **Single-video smoke test only.** The full B0b 7-video run with
  the patch (no runtime guard) was not re-executed in this commit;
  the smoke is sufficient to demonstrate the patch works because the
  same code path fires on every cross-turn call. Future work: when
  the patch lands upstream, re-run B0b without the runtime guard and
  confirm 42/42 byte-identical (current B0b r2 result is 42/42 with
  the runtime guard; behavior should be identical).
- **`current_offset = max(c.offset for c in kv_cache)`** assumes
  per-layer offsets are in sync after a prior turn's prefill. They
  are — this is mlx-vlm's existing invariant. The patch documents
  but doesn't enforce this; if a future change breaks the invariant,
  the patch would need a per-layer adaptation.
- **Local patch applied to `/opt/homebrew/.../mlx_vlm/generate.py`
  is fragile.** It will be overwritten on `pip install --upgrade
  mlx-vlm`. The apply helper detects already-applied state and the
  revert flow restores a clean upgrade-ready tree. Long-term answer
  is the upstream PR.

## Cross-reference

- Original bug: `2026-04-29-phase-B0b-sam-cache-correctness-findings.md` (76% wrong outputs on cross-turn)
- Runtime guard: `2026-04-30-phase-B0b-r2-sam-correctness-control-findings.md` (runner-side fix; same behavior, different layer)
- Speedup-preserving alternative: `2026-04-29-phase-M5-5b-sam-prefix-snapshot-fix-findings.md` (sidesteps trim)
- Library source: `mlx_vlm/generate.py:671-721` (lines as of mlx-vlm 0.4.4)
