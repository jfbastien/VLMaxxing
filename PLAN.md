# Current Plan

Last updated: 2026-05-11.

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
- **Candidate C-STREAM** has a checked mixed/boundary bundle. It is
  paper-facing as a candidate scale-out regime, not as a fourth headline:
  default cache reuse is unsafe, topology-aware correctness can be restored
  without speed, prefix snapshots are promising but small-\(N\), and low-FPS
  dense remains a serious baseline.
- 26B follow-up reuse remains diagnostic until a topology-safe path preserves
  correctness without surrendering the speed path.
- **OneVision x VLMaxxing Track A** has a bounded positive codec-source signal
  on VideoMME short / Qwen2.5-VL-7B-4bit / 8 frames. Treat it as semantic
  substitution evidence only: N=57 point estimates favor codec over pixel, but
  per-source McNemar tests are inconclusive and frame=16 collapses codec to the
  pixel answer set.
- **OneVision x VLMaxxing Track B** has bounded Qwen evidence, not a broad
  speedup claim. At VideoMME short / Qwen2.5-VL-7B-4bit / 8 frames,
  `codec_novel_coded` at kr=0.7/layer=2 is the best tested sparse arm by point
  estimate over `magnitude_norm`, but paired tests remain inconclusive and
  current PyAV metadata extraction erases model-side wall-clock savings.

## Active Gates Before Paper/OSS Freeze

1. **Finish incoming experiment bundles.**
   - local phase-2 chain: finish remaining follow-on gates and update the
     registry/status docs from the artifacts
   - scale-out bundle: import only checked artifact bundles, not sibling
     markdown, personal handoff prompts, or screenshots
   - natural-dialogue C-PERSIST and one adjacent-method comparison are the
     highest-value main-track science gaps after the current integration pass
   - OneVision follow-up: Qwen OV-6 has landed as bounded point-estimate Track B
     evidence. Next, run Gemma only after codec-grid geometry is wired and
     CPU-tested; use M5 for broader Qwen only after preregistering whether the
     question is larger-N power, cross-benchmark transfer, or frame-budget
     transfer. Do not claim net codec wall-clock speedup until metadata
     extraction is precomputed or decoder-integrated.

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
