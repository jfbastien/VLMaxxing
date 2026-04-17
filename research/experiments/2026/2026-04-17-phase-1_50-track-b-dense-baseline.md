# Phase 1.50 — Track B dense baseline on TOMATO (n=10, mc_scoring)

Date: 2026-04-17
Parent: `paper/claim-matrix.md` claim #5 (real skipped compute)

## Hypothesis

Claim #5 demands **measured**, not projected, end-to-end speedup.
Before any sparse-execution path exists, we need the dense wall-clock
baseline on the M3 Air 16GB MLX stack so that a future sparse run
has a reference to subtract from. Without this baseline, any Track B
speedup number would be floating. The matching-pair plan: measure
dense once with the same prompt format and preprocessing that Track A
uses, then measure sparse later with the same harness.

## Method

`scripts/run_track_b.py --mode mc_scoring` emulates Track A's
scoring path: prefill the `(vision + prompt + options)` tokens and
measure through the first forward pass. We do NOT run full
autoregressive generation (`--mode full_generation` is available
for a future comparison, but mc_scoring is what phase 1.21 / 1.24
actually used).

Phases measured:

| Phase | What it times |
|---|---|
| `decode_ms` | opencv frame decoding |
| `preprocess_ms` | square-pad + 560×560 resize on all frames |
| `vision_encode_ms` | full vision tower forward through merger (the ViT) |
| `prefill_ms` | text+vision token prefill through the LLM backbone |
| `generation_ms` | 0 in `mc_scoring`, the real number in `full_generation` |

Peak MLX memory via `mx.get_peak_memory()` is sampled after vision
encode and after inference. A warmup item loads and runs through the
full path but is not recorded.

## Dataset

- Benchmark: TOMATO motion
- Manifest: `tomato_motion_dev_v2.toml` (first 10 items, dev split)
- Frame count: 8 (matches the dense-8 Pareto anchor on TOMATO)
- Mode: `mc_scoring`
- Warmup: one additional item run before recording
- Hardware: M3 Air 16GB, Qwen2.5-VL-7B-Instruct-4bit (MLX 4-bit)
- Commit: `8920e36` (dirty tree — manifest builder uncommitted at launch)

## Results

Per-item timing (ms) and peak memory (GB), N=10 TOMATO motion dev:

| Phase | mean | median | p95 | min | max |
|---|---:|---:|---:|---:|---:|
| decode | 3516 | 3338 | 4116 | 2391 | 5635 |
| preprocess | 152 | 165 | 195 | 68 | 196 |
| **vision_encode** | **13390** | **13869** | **17499** | **6875** | **18802** |
| **prefill** | **43043** | **41846** | **53906** | **27540** | **62807** |
| generation | 0 | 0 | 0 | 0 | 0 |
| **total** | **60103** | **61210** | **71659** | **36874** | **87442** |

Peak memory: 6.85 GB mean post-inference, 6.87 GB p95, 6.87 GB max.

## What this means

1. **Prefill dominates at 72% of per-item wall time**, not vision
   encode. At 8 frames × 400 tokens/frame = 3200 vision tokens plus
   ~100 text tokens, prefill is attending across ~3300 tokens with a
   7B decoder. Any Track B win that only skips vision encode has a
   22% ceiling on end-to-end speedup unless it also shrinks the
   prefill token count (that's the SparseVLM / FastV / VisionZip
   territory) or reuses KV cache across frames (the CoPE-style path).
2. **Vision encode is 13.4s for 8 frames at 560×560 4-bit MLX.**
   That's ≈1.7s per frame. Stacked blockwise-cache reuse of the
   vision tower would save up to that 13.4s minus the bookkeeping
   overhead — worthwhile for the "frames you already saw" case but
   not a dominant end-to-end signal on its own.
3. **Decode takes 3.5s** just getting 8 frames out of disk via
   opencv. This is a real fixed cost on mp4 input that no sparse
   method beats without swapping the decoder or keeping a decoded
   cache warm.
4. **Memory is 6.87 GB peak.** On a 16 GB M3 Air this leaves headroom
   for a separate baseline process, but the 7B 4-bit model plus
   8-frame ViT activations already sits near half of unified memory.
   A 32-frame run on this geometry would likely OOM without careful
   activation streaming (relevant for phase 1.41 VideoMME at 32+
   frames).
5. **Variance matters**: max/min is 2.4× (87s vs 37s). Decode time
   tracks clip length; vision encode time is surprisingly variable
   (2.7×) even at fixed frame count and resolution — MLX's JIT
   compilation cost is item-order-dependent and the warmup does not
   fully amortize it. A paper-grade Track B number needs a larger N
   (30+) and a repeated-measure design, not just n=10.

## Paper implications

- **Claim #5 status moves from "no baseline" to "dense baseline
  captured, sparse path pending."** The paper can quote "dense
  forward measures 60 s/item median on TOMATO 8-frame
  mc_scoring; prefill is 72 % of that, vision encode 22 %,
  decode 6 %."
- The **ceiling on vision-cache-only Track B speedup is 22 %** at
  TOMATO-8-frame geometry. That's a hard number we should put in
  the paper's limitations paragraph before anyone else does.
- Reported numbers must stay **end-to-end**. Reporting "vision
  encode speedup" as Track B would double-count the saved work
  (sam's feedback from the round-5 review, now enforced in the
  harness by the mutually-exclusive `--mode` flag).

## Open questions

- Run n=30 on TOMATO and MVBench motion (holdout) for real variance
  bands. Rough runtime estimate: 30 items × 60s/item × 2 benchmarks
  = 60 min of GPU time.
- Run `--mode full_generation` on a small n to characterize the
  autoregressive-generation tail. Track A uses mc_scoring, but any
  system paper will need full_generation numbers too.
- Repeat on higher-frame geometry (16, 32) to map the prefill-vs-vision
  mix as F grows. Prediction: prefill fraction grows because prefill is
  O(F²) due to attention but vision encode is O(F).
- When a sparse-execution path lands, the **delta** here is the claim.
  Today's number is the null hypothesis the sparse method must beat
  to justify the paper.

## Reproduction

```bash
uv run python scripts/run_track_b.py \
  --manifest research/benchmark_manifests/tomato_motion_dev_v2.toml \
  --mode mc_scoring \
  --frame-count 8 \
  --limit 10 \
  --output results/track_b/tomato_mc_n10.jsonl
```

Output schema per-item: `item_id, benchmark, group, frame_count,
mode, decode_ms, preprocess_ms, vision_encode_ms, prefill_ms,
generation_ms, generation_tokens, total_ms,
peak_memory_after_vision_gb, peak_memory_after_inference_gb`.
