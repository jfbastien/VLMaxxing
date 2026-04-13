# Timing Harness Rules

This file supplements [performance.md](performance.md) with concrete harness
requirements for timing-sensitive work on local Apple hardware.

## Clock Source

Use `time.perf_counter_ns()` for wall-clock timing in Python.

Do not mix clock sources inside one experiment.

## Synchronization

If the backend is lazy, force synchronization before the stop timestamp.

For MLX-based runs, the harness must call the appropriate evaluation/sync point
before timing ends. Otherwise the numbers are not real wall-clock timings.

## Seed Discipline

If the runtime exposes a seed or deterministic mode, set it and log it.

If the runtime does not expose one, say that explicitly in the manifest.

## Warmup Policy

Warmup is required for timing claims.

Minimum rule:

- discard clearly first-run compile/load outliers
- log how many warmup iterations were used
- keep warming until consecutive runs stabilize within a small band, or record that they did not stabilize

If warmup never stabilizes, the harness should report that explicitly instead of
pretending to have a steady-state number.

## Page-Cache Assumption

Cold-start numbers must say whether they assume:

- a warm file-system page cache
- an explicitly cleared page cache

If page-cache state is uncontrolled, do not call the result `cold` without qualification.

## Thermal Guard

This machine class is fanless and can throttle.

Required guardrails:

- randomize or ABBA-order paired comparisons
- keep clip order identical across compared conditions
- log elapsed benchmark duration
- stop and cool down if later runs drift materially for reasons unrelated to the method

If thermal state is measured directly, log the source. If not, say so.

## Background Activity Snapshot

At experiment start, record a lightweight snapshot of background activity or
say that no snapshot was taken. The goal is not perfect observability. The goal
is to explain obvious outliers later.

## Decode And I/O Separation

Timing reports must separate at least these phases when they exist:

- demux or decode
- frame extraction or image serialization
- planner or routing
- vision encode
- multimodal prefill
- text generation

Do not time temp-file-heavy reference helpers and present the result as decode cost.

## MLX Memory Cache Policy

If MLX memory caches are cleared between runs, log that.

If they are intentionally left warm, log that too.

The choice changes what a repeated-run number means.

## Agreement And Determinism

Before any Track A comparison:

- run the dense baseline twice
- verify determinism or record the observed non-determinism

Track A reports must include:

- baseline accuracy
- modified-path accuracy
- baseline-versus-modified agreement
- chance-corrected agreement such as Cohen's kappa when the task format permits it

## Run Manifest

Every raw record should carry:

- git SHA
- experiment note path
- model id and local config hash when possible
- clip id and content hash when possible
- prompt id
- runtime stack versions (`python`, `ffmpeg`, backend libraries)
- machine identifier
- warmup count
- experiment track

Suggested format:

- one JSON object per run record
- stable top-level keys across experiments

## Composition Gate

Do not multiply independent speedup or compression factors unless:

- each factor was measured on the same hardware
- each factor used the same model family
- each factor used the same clip set or a documented shared subset
- sub-multiplicative interaction was measured, not assumed

Until then, composition arithmetic is hypothesis-generation only.
