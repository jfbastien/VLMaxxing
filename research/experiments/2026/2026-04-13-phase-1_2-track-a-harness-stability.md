# Phase 1.2: Track A Harness Stability

## Preregistration

Hypotheses:

- the long-lived single-process Qwen Track A path on this M3 Air is currently
  unstable for the full `12`-item v2 suite
- simple Python garbage collection plus an explicit MLX cache clear between
  items may be sufficient to stabilize that path

Track:

- A-supporting measurement

Primary metrics:

- completion versus hang for a single-process `track_a_chunk` run
- whether the run returns machine-parseable JSON without manual intervention

Secondary metrics:

- whether a smaller single-process chunk completes after the same fix
- whether the direct `.venv/bin/python3` path behaves differently from `uv run`

Unit of analysis:

- whole local harness run

Model:

- `Qwen2.5-VL-3B-Instruct-4bit`

Prompt bank:

- `research/prompt_bank/local_suite_v2.toml`

Acceptance band:

- the single-process `12`-item run completes cleanly after the cache-clear fix

Rejection band:

- the single-process `12`-item run still hangs or must be killed even after the
  cache-clear fix

Inconclusive:

- the run completes once but behaves too erratically to set a stable operating
  rule

Notes:

- this is a harness-debug experiment, not a method-quality claim
- timing claims still remain out of scope because the subprocess workaround
  includes startup overhead

## Execution

Run date:

- 2026-04-13

Artifact:

- [phase1_2_harness_stability.json](artifacts/phase1_2_harness_stability.json)

## Result

Preregistration outcome:

- Rejected

Observed outcomes:

- direct `./.venv/bin/python3` invocation crashed during MLX Metal device
  initialization with `NSRangeException` before returning JSON
- a full single-process `12`-item `track_a_chunk` run hung without returning
  JSON
- adding `gc.collect()` plus `mx.clear_cache()` between items did not make the
  full `12`-item single-process path stable
- the same cleanup did help a smaller `4`-item single-process run complete
  successfully

Operational additions after the run:

- the runner now supports `--stop-file <path>` for cooperative termination
  after the current item or chunk
- the runner now supports `--checkpoint-path <path>` so long semantic runs can
  persist partial results without relying on force termination

Current operating rule:

- use `uv run` plus chunked subprocesses for Track A semantic runs on this
  machine
- do not treat the long-lived single-process Qwen path as stable yet
- do not use this harness state for Track B timing claims

## Interpretation

The current failure mode is still a harness constraint, not a method result.
`mx.clear_cache()` plus Python garbage collection improved the stable chunk size
boundary but did not remove the core instability. That means the root cause is
still unresolved and remains a blocker for larger benchmark-native Track A runs
unless they are chunked or further debugged.

The new cooperative stop/checkpoint controls change the operating ergonomics,
not the scientific interpretation. They let long semantic runs end cleanly
after a chunk boundary and preserve partial work without requiring `kill`, but
they do not make the single-process path benchmark-safe or timing-safe.

## Links

- [2026-04-13-phase-1_05-temporal-necessity-ablation.md](2026-04-13-phase-1_05-temporal-necessity-ablation.md)
- [2026-04-13-track-a-local-pilot-v2.md](2026-04-13-track-a-local-pilot-v2.md)
