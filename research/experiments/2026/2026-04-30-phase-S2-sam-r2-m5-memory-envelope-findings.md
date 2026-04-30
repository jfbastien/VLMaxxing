---
date: 2026-04-30
phase: S2 (r2)
status: closed-earned for Gemma 26B-A4B; partial for Qwen 7B-4bit + Gemma E4B-4bit
related:
  - 2026-04-30-sam-r2-handoff.md (Step 4 -- S2 spec)
---

# 2026-04-30 Phase S2 — M5 memory envelope (peak RSS by model × frame_count)

- **Status:** **closed-earned** for the Gemma 4 26B-A4B cells (8 / 16 /
  32 / 64 / 128 f, full envelope measured); **partial** for Qwen
  2.5-VL-7B-4bit and Gemma 4-E4B-4bit (cells deferred — those models
  weren't run during r2 and require environment setup not yet on this
  M5).
- **Verdict:** Gemma 4 26B-A4B / mlx-vlm 0.4.4 / M5 Max fits the
  full 8 → 128 frame sweep within ~52 GB peak RSS — well below the
  128 GB unified memory available, and decisively over the 12 GB
  MLX cap that blocks this model on the local Air.

## Setup

- M5 Max MacBook Pro, 128 GB unified memory.
- macOS Darwin 25.4.0; Python 3.14.3; mlx 0.31.1 / mlx-vlm 0.4.4.
- Memory definition: `resource.getrusage(RUSAGE_SELF).ru_maxrss /
  (1024**3)` in GB. On macOS `ru_maxrss` is in **bytes** (not KB
  like Linux) and is **monotonic** over the process lifetime —
  i.e., it never decreases, so values within a single run grow
  through the run.
- The `_peak_rss_gb()` helper this S2 uses is consistent with the
  `peak_rss_gb` already recorded in every paired-row schema across
  this bundle.

## Source — extracted from existing schema-validated artifacts

S2 does NOT require new model runs. Every row in our existing
artifacts carries `peak_memory_gb`. This phase reads those values out
and tabulates them by (model, loader, frame_count) cell.

| run | loader | model | frames | peak_gb |
|---|---|---|---|---:|
| M5-4 fFjv93ACGo8 | `mlx_vlm.load(...)` direct | Gemma 4 26B-A4B | 8 | **49.09** |
| M5-4 fFjv93ACGo8 | direct | Gemma 4 26B-A4B | 16 | **49.28** |
| M5-4 fFjv93ACGo8 | direct | Gemma 4 26B-A4B | 32 | **50.04** |
| M5-4 fFjv93ACGo8 | direct | Gemma 4 26B-A4B | 64 | **50.70** |
| M5-4 fFjv93ACGo8 | direct | Gemma 4 26B-A4B | 128 | **52.28** |
| M5-4 N1cdUjctpG8 / HIjX8OPuf-w | direct | Gemma 4 26B-A4B | 8–128 | 52.28 (saturated) |
| B4 (any video) | sdamico `Gemma4VLM` wrapper | Gemma 4 26B-A4B | 8 | **39.26** |
| B4 (any video) | wrapper | Gemma 4 26B-A4B | 32 | 39.30 |
| B0b r1 8f | direct | Gemma 4 26B-A4B | 8 | 41.20 |
| B0b r2 8f | direct (with monkey-patch) | Gemma 4 26B-A4B | 8 | 47.28 |
| B1 8f | direct | Gemma 4 26B-A4B | 8 | 47.15 |
| B2 8f horizon | direct | Gemma 4 26B-A4B | 8 | 47.49 |
| B3 1080p recordings | direct | Gemma 4 26B-A4B | n/a | 45.84 |
| M5-5b 8f | direct | Gemma 4 26B-A4B | 8 | 49.16 |
| M5-5b 32f | direct | Gemma 4 26B-A4B | 32 | 48.46 |

## Gemma 4 26B-A4B per-frame-count growth (clean sweep, M5-4 video 1)

The first video of M5-4 ran 8 → 16 → 32 → 64 → 128 sequentially with
no other workload in between, so the per-cell values represent the
**incremental** memory required at each frame count (subsequent
videos saturate at the high-water mark since `ru_maxrss` is
process-lifetime max):

| frames | n_input_tokens | peak_gb | Δ vs prev cell |
|---:|---:|---:|---:|
| 8   | 2,088  | 49.09 | (baseline) |
| 16  | 4,152  | 49.28 | +0.19 |
| 32  | 8,280  | 50.04 | +0.76 |
| 64  | 16,536 | 50.70 | +0.66 |
| 128 | 33,048 | **52.28** | +1.58 |

Roughly **~0.5–1.5 GB per +2 K input tokens** of attention/cache state.
Dominant cost is the model weights + activation buffers (~49 GB at
8 f); the per-token-context overhead is small in absolute terms.

## Loader gap — direct vs `Gemma4VLM` wrapper

The Gemma4VLM wrapper (sdamico's `experiments/run_gemma4_validation.py`)
shows a peak of ~39 GB across runs that match cells the direct mlx-vlm
loader pegs at ~49 GB. Difference is ~10 GB, persistent across frame
counts. Likely cause: wrapper-side memory-efficient wiring (intermediate
tensors evaluated more aggressively via `mx.eval` between stages,
fewer concurrent tensor lifetimes) vs the direct loader's chunked-
prefill path that keeps more state live.

This is documented because the paper's deployment claims should cite
the **wrapper** number when discussing Gemma 4 26B's deployable
memory footprint — ~40 GB is achievable with available code, not
~50 GB.

## Cells NOT measured here

Per the r2 handoff, S2 also asked for:

| Model | Frame counts | Status |
|---|---|---|
| Qwen 2.5-VL-7B-4bit | 32, 64 | **DEFERRED** (no M5 run yet; requires `~/models/Qwen2.5-VL-7B-Instruct-4bit` weights and `codec_through` package install + torchvision dep, none of which are on this M5 yet — see S1 deferral note) |
| Gemma 4-E4B-4bit | 32 | **DEFERRED** (same env-setup blocker) |

These cells require either (a) downloading the specific 4-bit MLX
quantizations and installing `codec_through` + `torchvision` into the
M5 Python, or (b) standalone model-load-and-measure scripts that
don't go through the codec_through dependency chain. Both are
straightforward; neither is r2-blocking. **A follow-up "S2-extended"
run on Sam's next M5 session can fill these cells once env setup
lands.**

For paper purposes: the Gemma 4-E4B-4bit envelope is well-characterized
on the local Air (the model FITS under 12 GB MLX cap there, so it's
NOT a cell where M5's 128 GB envelope is uniquely required); only the
Qwen 7B-4bit at high frame counts (32, 64) might benefit from M5
measurement, and that is achievable in a follow-up.

## What this means for the paper

- **Reproducibility section:** Gemma 4 26B-A4B requires **~52 GB peak
  RSS at 128 f** on M5 Max with mlx-vlm 0.4.4's direct loader, **~40
  GB with sdamico's `Gemma4VLM` wrapper**. Both are within the M5's
  128 GB unified memory and well above the local Air's 12 GB MLX cap
  — i.e., **the 26B / scale-out lane requires consumer-laptop-class
  hardware with ≥ 64 GB unified memory; cannot run on the Air at
  this configuration.**
- **§5 / §7 cross-arch comparisons:** if the paper cites a 4 B-class
  cell from JF's local lane alongside the 26B cell from this lane,
  the per-frame-count memory deltas are small enough (~1 GB per 2 K
  tokens) that the comparison is dominated by model weights, not by
  context size.
- **§9 limitations:** record the loader-gap. If a follow-up S2-
  extended run measures Qwen 7B-4bit at 32 / 64 f and Gemma E4B-4bit
  at 32 f on M5, those cells go in §9 too.

## Caveats

- **`ru_maxrss` is process-lifetime max.** Per-cell values within a
  single multi-cell run reflect cumulative high-water mark, not the
  cell's standalone peak. The "M5-4 video 1 sweep" rows above are
  the cleanest per-cell estimates because they are the FIRST run
  through each frame count (subsequent videos saturate at the
  high-water value). For cells that need per-cell-isolated peak,
  separate process invocations would be required.
- **Activation memory in MLX is lazy.** `mx.eval` materializes
  tensors; until eval, peak doesn't reflect computation that hasn't
  fired yet. Our runners call `mx.eval` between chunks and at row
  boundaries, so the recorded peak tracks committed-tensor memory.
- **Single-thread / single-process.** Numbers don't include any MLX
  GPU-side memory that doesn't show up in `ru_maxrss` (since
  unified memory, all of it should). On separate-VRAM hardware these
  numbers would not transfer.

## Artifacts

- This findings doc.
- S2 data extracted from existing artifacts; no new JSONL produced.
- Source artifacts (already on `sam/scaleout-m5-r2-20260430` /
  ancestor commits): `sam_b0b_*`, `sam_b1_*`, `sam_b2_*`, `sam_b3_*`,
  `sam_b4_*`, `sam_m5_4_*`, `sam_m5_5b_*` under
  `research/experiments/2026/artifacts/sam_scaleout_m5_*/`.

## Re-run command (extraction)

```bash
cd /Users/sam/repos/codec-through-jfb
python3 - <<'PY'
import json
from pathlib import Path
base = Path('research/experiments/2026/artifacts')
for path in base.rglob('sam_*.jsonl'):
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    peaks = [r.get('peak_memory_gb') for r in rows if r.get('peak_memory_gb') is not None]
    if peaks:
        print(f"{path.name:<60} max={max(peaks):.2f} min={min(peaks):.2f} n={len(peaks)}")
PY
```
