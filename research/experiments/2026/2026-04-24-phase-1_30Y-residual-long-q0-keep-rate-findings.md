---
phase: 1.30Y
date: 2026-04-24
parent: research/experiments/2026/2026-04-24-phase-1_30Y-residual-long-q0-keep-rate-prereg.md
artifacts:
  - research/experiments/2026/artifacts/phase1_30Y_residual_long_q0_keep_rate_20260424/
status: SCOUT COMPLETE. `kr_Q0 = 0.67` remains alive; `kr_Q0 = 0.75` does not.
---

# 1.30Y — Residual long-session Q0 keep-rate scout findings

## Headline

The residual-pair scout cleanly narrows the next 1.30 continuation.

On the two binding long sessions from `1.30X`
(`videomme:long:783-2`, `videomme:long:847-3`):

- `kr_Q0 = 0.75` is **not** good enough for format hygiene
- `kr_Q0 = 0.67` is the first cheaper-Q0 candidate that remains alive

So the next useful experiment is not another small residual-pair sweep.
It is a **long-bucket continuation** of the `0.67` candidate.

## Setup

- Manifest:
  `research/benchmark_manifests/videomme_long_residual_parse_v1.toml`
- Model: `Qwen2.5-VL-7B-Instruct-4bit`
- Frame count: `8`
- Max tokens: `32`
- Arms:
  - `cold_dense`
  - `streaming_q0_kr100_followup_kr050`
  - `streaming_q0_kr075_followup_kr050`
  - `streaming_q0_kr067_followup_kr050`

## Results

### Matched cold baseline

- `6/6` correct
- parse failures `= 0`
- degenerates `= 0`

### Dense-Q0 reference (`kr_Q0 = 1.0`)

- `4/6` correct
- Q0 accuracy `= 2/2`
- follow-up accuracy `= 2/4`
- parse failures `= 0`
- degenerates `= 0`
- mean Q0 end-to-end `= 162.07 s`

This reproduces the known residual-pair behavior from the full `1.30W`
run:

- video `783` is fully repaired
- video `847` stays format-clean but misses both follow-ups

### Candidate `kr_Q0 = 0.75`

- `4/6` correct
- Q0 accuracy `= 2/2`
- follow-up accuracy `= 2/4`
- parse failures `= 0`
- degenerates `= 1`
- mean Q0 end-to-end `= 159.51 s`

Failure mode:

- `videomme:long:847-2` becomes degenerate again

So `0.75` gives back exactly the format property this scout was meant
to test.

### Candidate `kr_Q0 = 0.67`

- `5/6` correct
- Q0 accuracy `= 2/2`
- follow-up accuracy `= 3/4`
- parse failures `= 0`
- degenerates `= 0`
- mean Q0 end-to-end `= 158.27 s`

Per-session behavior:

- `783` stays fully correct (`3/3`)
- `847` becomes `2/3` correct
  - `847-2`: wrong but clean
  - `847-3`: correct and clean

So `0.67` is the only cheaper-Q0 candidate from this scout that
preserves clean formatting on both binding sessions while improving
accuracy over the dense-Q0 reference.

## Preregistered verdicts

### H_format_075

**FALSIFIED.**

- parse failures `= 0`
- degenerates `= 1`

### H_accuracy_075

**EARNED narrowly.**

`0.75` stays tied with the dense-Q0 reference on all-query correctness
for this 2-session scout (`4/6` vs `4/6`), but that does not rescue the
format failure.

### H_speed_075

**EARNED weakly.**

Mean Q0 wall-clock falls from `162.07 s` to `159.51 s`, but the
improvement is small and not scientifically meaningful given the format
failure.

### H_format_067

**EARNED.**

- parse failures `= 0`
- degenerates `= 0`

### H_accuracy_067

**EARNED strongly.**

`0.67` improves the scout from `4/6` to `5/6`, so it is strictly better
than the dense-Q0 reference on this residual pair.

## Residual-pair interpretation

This scout changes the 1.30 picture in an important but intentionally
limited way.

The live question after `1.30X` was whether the only format-clean fix
for the residual long sessions required fully dense Q0. The answer is
now:

- **not necessarily**

At least one cheaper Q0 regime (`0.67`) preserves clean formatting on
the residual pair and even improves its answer accuracy relative to the
fully dense-Q0 reference.

That does **not** yet earn a paper claim. The scout is only two
sessions, and those sessions were selected because they were already the
binding residual failures from `1.30X`. This makes the scout explicitly
selection-biased by construction.

What it *does* earn is narrower:

- `kr_Q0 = 0.67` is worth a full long-bucket generalization test
- `kr_Q0 = 0.75` is not

## Approximate full-policy implication

Using the new `0.67` scout measurements as a drop-in replacement for the
two binding long sessions, and keeping the already-landed
`dense_on_medium_short` policy elsewhere, the composite policy would
land approximately at:

- `Δacc = -0.0702`
- `speedup = 3.0023×`
- parse failures `= 0`
- degenerates `= 0`

That splice is **not** a promotion-ready result because it mixes new
residual-pair thermals with previously landed full-union runs. It is
only a routing hint: the candidate is now close enough to justify the
full long-bucket confirmation (`1.30Z`) and, if that passes, a fresh
no-splice duration-conditioned union rerun (`1.30AA`).

## Decision

Do not spend more time on the residual pair itself.

Next:

1. run the `kr_Q0 = 0.67`, `kr_followup = 0.50` candidate on the full
   long bucket, then
2. decide whether it deserves a full duration-conditioned union rerun

What should **not** be next:

- another residual-pair keep-rate sweep,
- or a return to `0.75`, which failed the key format requirement.
