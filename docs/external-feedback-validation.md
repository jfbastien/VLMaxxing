# External Feedback Validation

Scope:

- validated the imported ChatGPT review/backlog files under `seed/chatgpt/reviews/`
- validated the newer future-research memo and backlog
- validated the Claude review against the current repo, imported artifacts, local model configs, and primary sources where needed

## Overall Verdict

The external reviews were useful, but not equally trustworthy.

What survived validation:

- the repo's main evidentiary split is Track A versus Track B
- several benchmark-hygiene and fail-closed issues were real
- the project should keep its current narrow claim and expand only with measured local evidence
- changed-window execution, screen-content specialization, and decoder-side routing deserve plan space

What needed reframing:

- `compute-denial` is a worthwhile robustness evaluation bucket, not a current headline claim
- machine-oriented sidecars and AI-native codecs are future horizons, not near-term repo objectives
- several stronger whitepaper numbers and phrasing needed correction before they become paper claims

## Validated And Fixed In This Commit

### 1. Fail-closed utility behavior

Verdict:

- VALID

Evidence:

- `extract_choice` could treat ambiguous `A or B` output as a real answer
- `uniform_frame_indices(1, 4)` previously returned duplicates
- temporal diffing silently cropped mismatched frame shapes

Fixes made:

- ambiguous letter outputs now return `None`
- invalid frame sampling now raises
- mismatched frame shapes and misaligned block geometry now raise

### 2. Timing harness hazard in frame extraction

Verdict:

- VALID

Evidence:

- `src/codec_through/ffmpeg.py` inherited a one-ffmpeg-process-per-frame helper

Fixes made:

- existing helper is now explicitly reference/debug only
- added `extract_frames_single_pass(...)` for timing-sensitive paths

### 3. Qwen geometry and checkpoint nuance

Verdict:

- VALID

Evidence:

- local config inspection confirms Qwen2.5-VL full-attention blocks at `[7, 15, 23, 31]`
- the stronger claim that layer `23` is the best merge point still comes only from imported artifacts

Fixes made:

- docs now distinguish locally verified config structure from imported merge-point ranking

## Validated And Promoted Into The Plan

### 4. Add a Phase 0.5 feasibility spike

Verdict:

- VALID

Why:

- before Phase 1, the repo should prove that the local MLX-VLM path exposes the required cached-feature interface cleanly enough for Track A work

Plan impact:

- added a preregistered Phase 0.5 experiment note under `research/experiments/2026/`

### 5. Determinism and agreement-floor requirements

Verdict:

- VALID

Why:

- Track A agreement is uninterpretable if the dense baseline itself is unstable
- raw agreement without baseline accuracy or chance correction is too weak

Plan impact:

- methodology now requires repeated dense-baseline checks and chance-corrected agreement when task format permits it

### 6. Acceptance bands and composition gate

Verdict:

- VALID

Why:

- the repo needs preregistered success or rejection criteria
- stacked multipliers should stay gated until measured on the same stack

Plan impact:

- performance and timing docs now require acceptance bands and explicit composition rules

### 7. Screen-content path and machine-oriented standards

Verdict:

- VALID, WITH SCOPE CONTROL

Why:

- the repo and external sources both support keeping screen content as a separate later-phase branch
- MPEG VCM, MPEG FCM, JPEG AI, and AV1 screen-content tools support the long-term framing

Plan impact:

- literature map and paper framing now include these directions, but only as future horizons

## Validated But Reframed Or Softened

### 8. Continuous H.264 spatial scoring

Verdict:

- VALID (MINOR)

Why:

- the underlying skepticism is justified
- calling it fully `killed` is stronger than the current local evidence

Plan impact:

- status changed to `deprioritized`

### 9. Provenance-aware KV policy

Verdict:

- OPINION

Why:

- it was never a core tested claim in this repo

Plan impact:

- treated as `not currently in scope`, not as a killed idea

### 10. Robustness / compute-denial framing

Verdict:

- OPINION

Why:

- it is a useful red-team evaluation idea
- it is not yet a primary claim backed by this repo

Plan impact:

- kept in `paper/framing.md` as future evaluation language, not as a top-level result

## Still Hypotheses

### 11. Changed-query attention

Verdict:

- CAN'T VERIFY

Why:

- plausible and worth planning
- not yet backed by local runtime evidence

Plan impact:

- remains after changed-window execution, not before it

### 12. Sensor-fusion codecs and AI-native codecs

Verdict:

- OPINION

Why:

- useful long-term framing
- outside the currently justified repo scope

Plan impact:

- recorded as future horizons only

## Whitepaper Corrections Triggered By Review

Validated issues:

- MVBench wording needed to distinguish the 20-task benchmark from the local 18-task saved run
- cache-size arithmetic needed model- and resolution-specific clarification
- TurboQuant was being presented too aggressively for a quality-neutral composed claim

Those corrections were applied directly in `whitepaper.md`.
