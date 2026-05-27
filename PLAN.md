# Current Plan

Last updated: 2026-05-27.

This file is the active roadmap only. Historical phase detail lives in dated
experiment notes and [research/experiments/registry.md](research/experiments/registry.md).
Git history preserves removed historical source imports and superseded strategy
notes.

## Current Position

- **C-CEILING** is earned as the accounting frame: end-to-end gains are bounded
  by dense component share times component reduction.
- **C-PERSIST** is earned for same-video follow-up latency inside the tested
  envelope. Warm follow-up multipliers remain the headline denominator, while
  setup-inclusive tables now expose the serving economics by session length.
- **C-VISION** has bounded measured sparse-vision evidence. Do not describe it
  as a broad sparse backend or sparse LM prefill result.
- **RLT/Gemma cost accounting** now reinforces C-CEILING: the prefill+vision
  stage model fits 19 Gemma cells at `R^2=0.97097` and `1.72%` mean absolute
  relative error. Treat admission-only rows as cost-accounting controls, not
  as a query-aware implementation result.
- **Candidate C-STREAM** has a checked mixed/boundary bundle. It is
  paper-facing as a candidate scale-out regime, not as a fourth headline:
  default cache reuse is unsafe, topology-aware correctness can be restored
  without speed, prefix snapshots are promising but small-\(N\), and low-FPS
  dense remains a serious baseline.
- 26B follow-up reuse remains diagnostic until a topology-safe path preserves
  correctness without surrendering the speed path.
- **OneVision x VLMaxxing refresh planning** is currently a parity/boundary
  result, not a codec-over-pixel win. The pooled N=57 Qwen/VideoMME-short rows
  are dirty-tree/advisory, in-sample, and matched to the pixel proxy's reuse
  budget; simple codec sources are only +2/57 over pixel there, and the
  disjoint per-item holdout ties pixel exactly. Positive refresh language now
  requires a clean frozen-threshold transfer run against the pixel proxy.
- **OneVision x VLMaxxing sparse vision pruning** is bounded Qwen evidence, not
  a broad speedup claim. At VideoMME short / Qwen2.5-VL-7B-4bit / 8 frames,
  `codec_novel_coded` at kr=0.7/layer=2 is the best tested sparse arm by point
  estimate over `magnitude_norm`, but paired tests remain inconclusive and that
  cell lacks the matched random-keep control. The follow-up sweep adds two
  boundaries: Qwen random beats magnitude on 4/4 seeds at kr=0.5/layer=2 and
  codec does not beat random where that control exists, while TOMATO motion
  stays near chance and is not rescued by codec scoring.
- **OneVision x VLMaxxing sidecars** are the clean systems result: live PyAV
  codec-score extraction is replaced by precomputed score sidecars with zero
  sparse-choice drift in the landed Qwen/Gemma gates. This is an
  extraction-path speedup, not a 10^4x model-pipeline speedup.

## Active Gates Before Paper/OSS Freeze

1. **Finish incoming experiment bundles.**
   - local phase-2 chain: finish remaining follow-on gates and update the
     registry/status docs from the artifacts
   - scale-out bundle: import only checked artifact bundles, not sibling
     markdown, personal handoff prompts, or screenshots
   - close the RLT/VLMaxxing documentation around the 2026-05-20
     cost-accounting result, then keep M5 as scale confirmation only
   - natural-dialogue C-PERSIST and one adjacent-method comparison are the
     highest-value main-track science gaps after the current integration pass
   - defer query-aware implementation until a separate branch can inherit the
     stage-cost ledger and run fresh held-out fixed/random/admission controls
   - OneVision follow-up: sidecar gates have landed; Gemma N=10 smoke clears
     the cross-family wiring gate; TOMATO is a low-headroom boundary result;
     and pooled H.264 refresh evidence is advisory until a clean frozen-threshold
     transfer run. Use M5 only for preregistered confirmation cells. The Qwen
     kr=0.7 parity/timing launcher must either point at a committed four-seed
     random-control preregistration or explicitly close that clean-control
     window with a committed closure note. Do not claim net codec model-pipeline
     speedup; only claim the measured extraction-path sidecar speedup.

2. **Freeze artifact provenance.**
   - every paper table/figure cell needs a source artifact path or a visible
     pending label
   - generated build metadata must be regenerated from the clean release tag
   - no paper automation should read a sibling checkout by default

3. **Keep claim language bounded.**
   - C-PERSIST: distinguish median warm follow-up speedups from mean
     setup-inclusive session economics
   - C-VISION: bounded measured sparse-vision envelope
   - C-STREAM: candidate streaming state reuse until a topology-safe fast path
     and matched native-streaming baselines land
   - imported targets: reproduction targets only, not local evidence

4. **Release hygiene.**
   - default repo should foreground code, tests, checked artifacts, manuscript
     tooling, validators, schemas, and concise reproduction docs
   - historical source imports, stale review packets, and one-off legacy
     harnesses should stay out of the release tree because git history is
     sufficient

## Source Of Truth

- current claim status: [paper/claim-matrix.md](paper/claim-matrix.md) and
  [paper/publishability-status.md](paper/publishability-status.md)
- imported target register: [docs/claim-register.md](docs/claim-register.md)
- local reproduction status: [docs/reproduction-status.md](docs/reproduction-status.md)
- experiment ledger: [research/experiments/registry.md](research/experiments/registry.md)
- manuscript automation: [paper/arxiv/README.md](paper/arxiv/README.md) and
  [paper/arxiv/scripts/sync_sources.py](paper/arxiv/scripts/sync_sources.py)
