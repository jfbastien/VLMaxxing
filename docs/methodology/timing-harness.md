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

## Warmup Policy

Warmup is required for timing claims.

Minimum rule:

- discard clearly first-run compile/load outliers
- log how many warmup iterations were used
- keep warming until consecutive runs stabilize within a small band, or record that they did not stabilize

If warmup never stabilizes, the harness should report that explicitly instead of
pretending to have a steady-state number.

## Thermal Guard

This machine class is fanless and can throttle.

Required guardrails:

- randomize or ABBA-order paired comparisons
- keep clip order identical across compared conditions
- log elapsed benchmark duration
- stop and cool down if later runs drift materially for reasons unrelated to the method

If thermal state is measured directly, log the source. If not, say so.

## Decode And I/O Separation

Timing reports must separate at least these phases when they exist:

- demux or decode
- frame extraction or image serialization
- planner or routing
- vision encode
- multimodal prefill
- text generation

Do not time temp-file-heavy reference helpers and present the result as decode cost.

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

## Composition Gate

Do not multiply independent speedup or compression factors unless:

- each factor was measured on the same hardware
- each factor used the same model family
- each factor used the same clip set or a documented shared subset
- sub-multiplicative interaction was measured, not assumed

Until then, composition arithmetic is hypothesis-generation only.
