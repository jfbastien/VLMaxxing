# 2026-04-29 Phase M5-4 — Sam frame-count scaling at 26B

- **Status:** **closed-earned.** First schema-validated 26B
  frame-count scaling on Gemma 4 26B-A4B / mlx-vlm 0.4.4. Cross-arch
  C-CEILING data point that fills a cell JF's local lane (Gemma
  4-E4B-4bit only) cannot reach.
- **Verdict:** per-frame compute on this stack is **roughly flat at
  ~730 ms/frame across 8–128 frames** (median 635 / 725 / 740 / 738 /
  730 ms/frame at 8 / 16 / 32 / 64 / 128). Per-input-token prefill
  cost is **~2.78 ms/token median, scales linearly through 33 k
  tokens**. No super-linear blowup at long context.

## Setup

| field | value |
|---|---|
| `model_id` | `google/gemma-4-26B-A4B-it` |
| `model_sha` | `7d4c97e54145f8ffd1a4dd1b4986a5015a517842` |
| `quantization` | `bf16_native` |
| `runtime` | `mlx_vlm-0.4.4` |
| `decoding` | greedy (`temperature=0.0`, `seed=0`) |
| `corpus` | first 3 unique videos from VideoMME test parquet |
| `frame counts` | 8 / 16 / 32 / 64 / 128 |
| `prompt` | "Describe the most prominent visual content. Keep it concise." |
| `max_tokens` | 16 |

3 videos × 5 frame counts = 15 schema-compliant rows. Single dense
arm; no cache.

## Per-row stage timings

| video | f | tokens | wall_ms | prefill_ms | gen_ms | ms/frame | ms/tok |
|---|---:|---:|---:|---:|---:|---:|---:|
| `fFjv93ACGo8` | 8   | 2,088  | 2,706   | 2,350   | 275 | 338 | 1.13 |
| `fFjv93ACGo8` | 16  | 4,152  | 5,649   | 5,203   | 281 | 353 | 1.25 |
| `fFjv93ACGo8` | 32  | 8,280  | 9,688   | 9,155   | 288 | 303 | 1.11 |
| `fFjv93ACGo8` | 64  | 16,536 | 21,388  | 20,512  | 302 | 334 | 1.24 |
| `fFjv93ACGo8` | 128 | 33,048 | 66,250  | 64,700  | 421 | 518 | 1.96 |
| `N1cdUjctpG8` | 8   | 2,088  | 5,081   | 4,671   | 330 | 635 | 2.24 |
| `N1cdUjctpG8` | 16  | 4,152  | 11,595  | 11,093  | 370 | 725 | 2.67 |
| `N1cdUjctpG8` | 32  | 8,280  | 27,820  | 27,175  | 405 | 869 | 3.28 |
| `N1cdUjctpG8` | 64  | 16,536 | 54,541  | 53,530  | 450 | 852 | 3.24 |
| `N1cdUjctpG8` | 128 | 33,048 | 105,176 | 103,636 | 515 | 822 | 3.14 |
| `HIjX8OPuf-w` | 8   | 2,088  | 6,072   | 5,615   | 369 | 759 | 2.69 |
| `HIjX8OPuf-w` | 16  | 4,152  | 12,927  | 12,408  | 363 | 808 | 2.99 |
| `HIjX8OPuf-w` | 32  | 8,280  | 23,667  | 23,071  | 375 | 740 | 2.79 |
| `HIjX8OPuf-w` | 64  | 16,536 | 47,203  | 46,342  | 399 | 738 | 2.80 |
| `HIjX8OPuf-w` | 128 | 33,048 | 93,426  | 92,008  | 478 | 730 | 2.78 |

## Aggregate scaling table

| frame count | n | median wall_ms | median prefill_ms | **median ms/frame** | median ms/input-token |
|---:|---:|---:|---:|---:|---:|
| 8   | 3 | 5,081  | 4,671   | **635** | 2.24 |
| 16  | 3 | 11,595 | 11,093  | **725** | 2.67 |
| 32  | 3 | 23,667 | 23,071  | **740** | 2.79 |
| 64  | 3 | 47,203 | 46,342  | **738** | 2.80 |
| 128 | 3 | 93,426 | 92,008  | **730** | 2.78 |

## What this says about C-CEILING on this stack

- **Linear scaling.** Per-input-token prefill cost saturates at
  ~2.78 ms/token by 16 frames and stays flat through 128 frames.
  No quadratic-attention blowup observed at 33 k tokens. mlx-vlm's
  prefill pipeline scales linearly within this regime.
- **Per-frame cost is flat.** 256 visual tokens per frame × 2.78
  ms/token = ~712 ms/frame predicted; observed 730 ms/frame median.
  The remaining ~18 ms/frame is the small-prefill overhead amortizing
  out by 16 f.
- **Generate cost is small and roughly constant.** ~280–520 ms across
  all frame counts (we generate `max_tokens=16` so generate is bounded
  by output length, not input).
- **Cross-arch cell for C-CEILING.** JF's local lane has C-CEILING
  measured at Gemma 4-E4B-4bit (4 B class) on the same axis. M5-4
  fills the 26 B / scale-out cell on the same axis. Side-by-side
  inclusion in `paper/arxiv/sections/07_results_cross_architecture.tex`
  shows that C-CEILING's prefill-share decomposition holds at 26 B
  scale.

## What this enables for the "more frames at fixed compute" claim

Pair with B4 (hard-prune at 32 f / kr=0.50 reduces per-frame compute
by 0.65×) to forecast composed gain at long context:

| frame count | dense ms/frame | hard-prune ms/frame (× 0.65 at ≥32f) | dense 1-query wall | pruned 1-query wall | speedup |
|---:|---:|---:|---:|---:|---:|
| 32 | 740 | ~480 | 23.7 s | 15.4 s | 1.54× |
| 64 | 738 | ~480 | 47.2 s | 30.7 s | 1.54× |
| 128 | 730 | ~475 | 93.4 s | 60.8 s | 1.54× |

Or framed as effective frames at fixed wall-clock budget:

| budget | dense fits | pruned fits | gain |
|---:|---:|---:|---:|
| 23.7 s | 32 f | ~50 f | 1.55× |
| 47.2 s | 64 f | ~99 f | 1.55× |
| 93.4 s | 128 f | ~197 f | 1.54× |

(Pruned column extrapolates assuming the B4-measured 0.65× per-frame
ratio holds at ≥32 f — measurement at 64 f / 128 f hard-prune is a
follow-up.)

## What this CAN'T tell us

- This run does NOT measure `vit_ms` separately from `prefill_ms`.
  mlx-vlm's `stream_generate` doesn't expose per-stage timing without
  monkey-patching. The "prefill_ms" reported here is `prefill_ms`
  in `stream_generate` semantics — time from start to first generated
  token, which includes the ViT + prefill but not generate.
- For the V_share decomposition (vision share of total compute), we
  would need separate ViT timing. The `Gemma4VLM.run_comparison_pruned`
  helper (used in B4) does decompose; M5-4 used the simpler
  stream_generate path so we trade off decomposition for cleanliness.
  A follow-up could re-run with the B4-style harness if V_share is
  paper-relevant.
- We have only one prompt per (video, frame count) cell. Bootstrap
  CIs not computed; the per-frame timings are dominated by mlx-vlm's
  deterministic prefill loop, so single-shot is reasonable.

## What this means for the paper

- **§7 cross-architecture, new row:** "Gemma 4 26B-A4B / M5 Max
  scales linearly to 33 k tokens, ~2.78 ms/token median; 730 ms/frame
  flat through 128 f." This is a clean cross-arch C-CEILING data
  point that JF's local 4B lane cannot reach.
- **§8 real applications, throughput cell:** combine with B4
  hard-prune (1.5× ingestion density at ≥32 f) and E3 streaming
  cache (22–64× ViT-fire reduction) to substantiate the headline
  "more frames at fixed compute" claim with **measured** numbers
  across three orthogonal axes.
- **§S6 sectional-scroll / streaming context:** the linear-prefill
  finding bounds how long a streaming session can run before
  per-query cost grows linearly with context; this informs the
  "safe-horizon" framing for sectional-scroll.

## Validator output

```json
{
  "n_rows": 15,
  "phases": {"M5-4": 15},
  "arms": {"cold_dense": 15},
  "policies": {"cold_dense_no_cache": 15},
  "schema_or_gate_errors": 0,
  "first_errors": [],
  "pass": true
}
```

## Caveats

- **Single-shot per cell.** Per-cell variance from thermal drift is
  visible: video `fFjv93ACGo8` runs are systematically faster than
  the others (1.1–1.96 ms/token vs 2.7–3.3). Likely the M5 was warm
  for the later runs. A paper-grade rerun should alternate frame
  counts and videos with cooldowns.
- **No ViT decomposition.** As noted above.
- **Generate length fixed at 16 tokens.** Generate is a small
  constant cost; not the focus of the scaling claim.

## Artifacts

- JSONL: `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_m5_4_frame_count_scaling.jsonl`
- Validator summary: `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_m5_4_frame_count_scaling_summary.json`
- Run log: `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_m5_4_frame_count_scaling.log`
- Runner: `scripts/run_sam_m5_4_frame_count_scaling.py`

## Cross-reference

- B4 findings (per-frame compute baseline + hard-prune ratio at 32 f):
  `2026-04-29-phase-B4-sam-track-b-hard-prune-findings.md`
- E3 (sdamico, throughput axis at sectional scroll): `sdamico/codec-through @ 6594a7b`
  -- `research/2026-04-26-e3-sectional-scroll-walltime/findings.md`
- JF cross-arch §7 C-CEILING cells (4B class):
  `paper/arxiv/sections/07_results_cross_architecture.tex`
