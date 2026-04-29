# Phase 1.42 — Gemma integration design note (pre-code)

Date: 2026-04-17
State: historical design note; implementation landed 2026-04-24 with pooled-token grouping
Parent: `paper/claim-matrix.md` claim #7 (architecture-conditioned reuse fidelity)
Depends on: nothing; this is a pre-coding design gate
Unlocks: phase 1.51 (novelty-pruning, **big-numbers headline**), phase 1.52 (combined temporal + spatial)

**2026-04-24 correction:** for the cached-feature Track A path used in this
repo, the live Gemma MLX `encode_image(...)` call emits **133 pooled cached
tokens per 560×560 frame** by pooling a 35×35 patch grid with
`pooling_kernel_size=3`. Earlier `256` / `16×16` and `280` / `14×20` notes in
this design sketch were wrong for this path or referred to different Gemma
routes, and are retained below only where explicitly labeled historical.

## Why this note exists

Codex flagged that we should **not** start coding `_mix_gemma_features` without a deliberate design pass. Gemma 4's token layout is NOT a clean port of Qwen's block-level reuse:

- **Qwen 2.5-VL**: windowed patch embedding; `qwen_merged_token_counts` gives per-frame token counts tied to 2D patch positions; `active_region_block_mask` is a pixel → block map; `_mix_qwen_features` operates on 28×28 blocks with clean pixel correspondence.
- **Gemma 4-E4B**: the current cached-feature driver path produces **133 pooled
  cached tokens per image** by grouping a 35×35 patch grid through the vision
  pooler. The post-vision tokens still have learned 2D positional structure
  before they enter the projector / LLM stack, but the spatial footprint is a
  pooled, non-square layout rather than a clean square token grid.

This means every concept in `_mix_qwen_features` needs a deliberate Gemma analog decision, not a port:

| Qwen concept | Maps to (Gemma candidate) | Decision needed |
|---|---|---|
| `qwen_merged_token_counts` → per-frame token counts | Fixed 133 cached tokens per frame on 560×560 benchmark inputs | None; constant across frames on the current benchmark path |
| `active_region_block_mask` (pixel→block) | Approximate pooled-token grouping from the 35×35 patch grid | Implement the grouped-mask analog, not a square-grid port |
| `classify_blocks_with_planner` on pixel blocks | Option A: run on pixel blocks and aggregate to post-pool tokens; Option B: run per-frame at whole-frame level (binary reuse); Option C: run on post-pool token vectors directly (feature-space novelty) | Pick one for v0 — see §Design options |
| 28×28 pixel block granularity | Does not generalize — post-pool token footprint is irregular | Abandon block-size parameter for Gemma |

## Design options (ranked by tractability)

### Option A — whole-frame-or-nothing reuse (simplest v0)

**Decision**: reuse the entire 256-token vector from a prior frame when the pair passes a threshold; otherwise recompute all 256.

- **Pro**: smallest code change (wraps `model.vision_tower` with a frame-level memoizer). Clean semantics. No spatial-footprint bookkeeping.
- **Pro**: maps cleanly to the pre-release source §2.7 framing (architecture-conditioned fidelity tested at the frame boundary).
- **Con**: crude. Can't capture "this corner of the frame changed, the rest didn't."
- **Con**: reuse ratio is bimodal (0 or 1 per frame) — less informative ablation surface.

**Threshold**: pixel-diff MAX_ABS at frame level (same statistic as Planner 2.0, aggregated over the whole frame). Same 8.0/32.0 thresholds for static/shifted as Qwen — an unjustified transfer but a reasonable v0 prior.

**Active-region masking**: drop it for v0. Revisit if accuracy drops below Gemma-dense.

### Option B — post-pool token-level reuse (token-novelty)

**Decision**: compute per-token similarity between the current frame's post-pool tokens and the prior frame's; reuse tokens with similarity above a threshold.

- **Pro**: respects Gemma's native token layout; no spatial-footprint handwaving.
- **Pro**: directly compatible with phase 1.51 novelty-pruning (same token axis).
- **Con**: requires one forward pass through the vision tower anyway to GET the current tokens — defeats the point unless we can predict token novelty from pixel space (which is phase 1.36's open question, now answered: r=0.233–0.504, content-conditional).
- **Con**: the threshold is a new hyperparameter that can't be transferred from Qwen.

### Option C — pre-pool block-level reuse

**Decision**: reuse at the pre-pool patch-grid level (16×16 patches, 196 per frame), then pool to 280 tokens.

- **Pro**: closest analog to Qwen's block-level reuse.
- **Pro**: pixel-to-patch mapping is exact (patch_size=16, frame 224×224 → 14×14=196 patches).
- **Con**: requires instrumenting the Gemma vision tower to separate pre-pool patches from post-pool tokens; intrusive change.
- **Con**: the avg-pool kernel=3 smears pre-pool changes across ~9 post-pool tokens, so a small pre-pool reuse ratio translates to a very small post-pool savings — diminishing returns.

## Recommended path

**v0: Option A (whole-frame-or-nothing), MINIMAL smoke test only.**

Justification: the point of phase 1.42 is to establish claim #7 (architecture fidelity) with the **smallest possible** integration. We don't need a competitive temporal-reuse policy on Gemma — we need *a* reuse path that ships correct features. Option A gives that at ~20 LoC. The "big-numbers" story (claim #11) is **phase 1.51 novelty-pruning, which does NOT depend on Option B or C**.

**Critical re-read** (round-17): phase 1.51 is a *fresh code path* (per-frame novelty-based token drop before LLM prefill). It does not require `_mix_gemma_features` at all. The code needed is:

1. Compute per-token novelty score (distance from a "static anchor" token per the pre-release source's WP §2.11 / per §2.7 background-class preservation).
2. Sort tokens by novelty descending, keep the top K (per a `--novelty-keep-rate` sweep).
3. Pass the kept tokens into the LLM prefill (Gemma supports variable-length prefill because its LLM uses standard 1D RoPE).

**This means phase 1.51 can land independently of phase 1.42**, contrary to what publishability-status.md step 1 currently says. Let me correct that.

## Implementation plan for Option A (v0)

### File touches (all CPU-only planning; no runs during halo sweep)

1. `scripts/run_benchmark_track_a.py`:
   - Add `--model-family {qwen, gemma}` CLI flag with auto-detect from model path (fallback `qwen`).
   - Add `_mix_gemma_features(sample, features, planner_config, reuse_classes, max_age, ...)` — returns `(mixed, raw_reused_ratios, active_reused_ratios)`.
   - In `_select_cached_features`, dispatch on `model_family`: qwen → `_mix_qwen_features`, gemma → `_mix_gemma_features`.
   - Handle `DEFAULT_MODEL_PATH` correctly when user passes
     `--model-path "$HOME/models/gemma-4-e4b-it-4bit"`.
2. `scripts/run_benchmark_track_a.py` — frame input path:
   - Verify `prepare_inputs(processor, images=frames, prompts=...)` works for Gemma (mlx-vlm supports it generically; confirmed via `.venv/lib/python3.12/site-packages/mlx_vlm/models/gemma4/gemma4.py:100-106`).
   - `cached_image_features` kwarg is already supported in Gemma forward pass (same file, lines 100-106).
3. `_compute_cached_features` — Gemma uses a different vision-tower signature:
   - Qwen: `model.vision_tower(pixel_values, image_grid_thw, output_hidden_states=False)`.
   - Gemma: `model.vision_tower(pixel_values)` (no `image_grid_thw`; fixed layout). Then `model.embed_vision(features)` to map to LLM embedding dim.
   - Dispatch on `model_family` or on `hasattr(model, 'embed_vision')`.

### Smoke test (minimum-viable)

File: `tests/test_gemma_track_a_smoke.py` (importorskip MLX):

1. Load `$HOME/models/gemma-4-e4b-it-4bit`.
2. Call `_compute_cached_features` on 2 frames of a small TOMATO video.
3. Assert features shape is `(2 * 256, hidden_size)` (or whatever the per-item Gemma token count × hidden_size is; the validated current path is 256×hidden_size).
4. Call `_mix_gemma_features` with whole-frame threshold that should trigger full reuse on near-identical frames.
5. Assert `mixed` has the same shape as `features` and the per-token distance between `mixed[0:256]` and `mixed[256:512]` is exactly 0 (byte-identical reuse).
6. Repeat with divergent frames; assert reuse_ratio = 0 and mixed equals features (no reuse).

### Runtime cost for phase 1.42 v0 after code lands

- Smoke: ≈ 30 s on one item.
- Byte-identity regression (1 item × both code paths): ≈ 1 min.
- Full phase 1.42 N=30 holdout on Gemma (TOMATO): ≈ 90 min (cold cache — Gemma features not in current cache).
- **Total to earn claim 7 partial on one benchmark: ≈ 1.5 h GPU wall time.**

## What Option A does NOT give us (and what phase 1.51 WILL)

Option A gives us *a* reuse path on Gemma with SOMETHING above zero reuse ratio on temporally stable content. It does NOT give us a measured end-to-end speedup — the vision encode on Gemma is a smaller fraction of end-to-end than on Qwen (Gemma has a smaller vision tower), and prefill still dominates.

**The big-numbers path is phase 1.51 (novelty-pruning, per-token input drop).** Phase 1.42 v0 is a claim-7 enabler, not a claim-11 enabler.

## Implications for immediate ordering

Given the round-17 one-paper goal (big numbers, fast):

1. **Phase 1.41 Qwen + VideoMME** — not blocked by Gemma. Only blocked by video corpus unpack. **Unblock this first**, it gives us the benchmark our paper needs to compare against.
2. **Phase 1.51 novelty-pruning on Gemma** — can be independently prototyped as a minimal Gemma-prefill-drop path, bypassing phase 1.42 temporal-reuse integration entirely. This is the big-numbers path. We should NOT gate 1.51 on 1.42.
3. **Phase 1.42 v0 Gemma temporal reuse (Option A)** — still worth landing for claim 7, but not on the critical path to the headline result.
4. **Phase 1.52 combined** — depends on BOTH 1.42 and 1.51 landing because the composition test needs both mechanisms live simultaneously.

## What goes in the paper from this phase

- A sentence in §Methods: "On Gemma, temporal reuse operates at frame-level (whole-frame-or-nothing) because the post-pool token layout does not admit a pixel-block decomposition analogous to Qwen's windowed patch grid."
- Table in §Results cross-architecture line: Gemma-dense-8 vs Gemma + temporal-reuse accuracy and fresh-frame count.
- Appendix: the Option A / B / C tradeoff; justification for Option A v0.

## Artifacts (pre-registered)

When phase 1.42 v0 runs (post-halo-sweep + post-Gemma-smoke):
- `tests/test_gemma_track_a_smoke.py` — pre-MLX design test.
- `research/experiments/2026/artifacts/phase1_42_gemma_smoke/*_summary.json` — 1-item byte-identity test.
- `research/experiments/2026/artifacts/phase1_42_tomato_gemma_holdout_v2_cached/*_summary.json` — full N=30.

## Related memories / references

- `$HOME/models/gemma-4-e4b-it-4bit/config.json`: `patch_size=16`,
  `pooling_kernel_size=3`; use the live cached-feature geometry (35×35 patches
  pooled to 133 cached tokens) rather than stale metadata fields.
- `.venv/lib/python3.12/site-packages/mlx_vlm/models/gemma4/gemma4.py:100-106`: `cached_image_features` kwarg supported.
- the pre-release source §2.7: "architecture-conditioned reuse fidelity is a spectrum, not a binary (windowed-exact vs all-global-approximate)."
- Phase 1.51 prereg (novelty-pruning on Gemma): `research/experiments/2026/2026-04-17-phase-1_51-novelty-pruning-gemma-prereg.md`.
- Phase 1.52 prereg (combined temporal+spatial): `research/experiments/2026/2026-04-17-phase-1_52-combined-temporal-spatial-prereg.md`.
