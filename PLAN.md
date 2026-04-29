# Current Plan

Last updated: 2026-04-29.

This file is the active roadmap only. Historical phase detail lives in dated
experiment notes and [research/experiments/registry.md](research/experiments/registry.md).
Git history preserves removed seed imports and superseded strategy notes.

## Current Position

- **C-CEILING** is earned as the accounting frame: end-to-end gains are bounded
  by dense component share times component reduction.
- **C-PERSIST** is earned for same-video follow-up latency inside the tested
  envelope. It is not a full-session throughput or energy claim until
  setup-inclusive artifacts land.
- **C-VISION** has bounded measured sparse-vision evidence. Do not describe it
  as a broad sparse backend or sparse LM prefill result.
- **Candidate C-STREAM** is pending. It should become paper-facing only through
  checked, schema-validated streaming artifacts with matched baselines.
- 26B follow-up reuse remains diagnostic until the cache-correctness and raw
  paired-artifact gates pass.

## Active Gates Before Paper/OSS Freeze

1. **Finish incoming experiment bundles.**
   - local phase-2 chain: finish current A5-and-follow-on gates and update the
     registry/status docs from the artifacts
   - scale-out bundle: import only validated artifact bundles, not sibling
     markdown, personal handoff prompts, or screenshots
   - setup-inclusive C-PERSIST: add a table/appendix row once artifacts record
     cache-build setup time

2. **Freeze artifact provenance.**
   - every paper table/figure cell needs a source artifact path or a visible
     pending label
   - generated build metadata must be regenerated from the clean release tag
   - no paper automation should read a sibling checkout by default

3. **Keep claim language bounded.**
   - C-PERSIST: follow-up latency unless setup-inclusive/session-amortized
     metrics are present
   - C-VISION: bounded measured sparse-vision envelope
   - C-STREAM: candidate streaming state reuse until matched artifacts land
   - imported targets: reproduction targets only, not local evidence

4. **Release hygiene.**
   - default repo should foreground code, tests, checked artifacts, manuscript
     tooling, validators, schemas, and concise reproduction docs
   - historical seed imports, stale review packets, and one-off legacy harnesses
     should stay out of the release tree because git history is sufficient

## Source Of Truth

- current claim status: [paper/claim-matrix.md](paper/claim-matrix.md) and
  [paper/publishability-status.md](paper/publishability-status.md)
- imported target register: [docs/claim-register.md](docs/claim-register.md)
- local reproduction status: [docs/reproduction-status.md](docs/reproduction-status.md)
- experiment ledger: [research/experiments/registry.md](research/experiments/registry.md)
- manuscript automation: [paper/arxiv/README.md](paper/arxiv/README.md) and
  [paper/arxiv/scripts/sync_sources.py](paper/arxiv/scripts/sync_sources.py)
