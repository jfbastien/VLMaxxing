---
phase: 1.30X
date: 2026-04-24
parent: research/experiments/2026/2026-04-24-phase-1_30W-q0-dense-followup-pruned-full-findings.md
artifacts:
  - research/experiments/2026/artifacts/phase1_30X_q0_admission_frontier/
status: preregistered 2026-04-24. Offline frontier analysis over landed 1.30 and 1.30W session outputs.
---

# 1.30X — Q0 admission frontier analysis (preregistration)

## Objective

Use the already-landed `1.30` and `1.30W` session outputs to answer a
more precise question than "try another policy":

**Can any cheaper safe-Q0 admission policy plausibly reopen the 1.30
bridge under the current 3-query protocol, or is the lane structurally
closed even with an oracle session selector?**

This is an offline analysis only. No new MLX execution is involved.

## Inputs

- original `1.30` paired session artifacts:
  `research/experiments/2026/artifacts/phase1_30_scaleout_streaming/`
- dense-Q0 `1.30W` paired session artifacts:
  `research/experiments/2026/artifacts/phase1_30W_q0_dense_followup_pruned_full/`

For each of the shared `57` VideoMME sessions, the analysis will treat
the repo as already having two honest measured endpoints:

1. `pruned_q0`: original `1.30` stack
2. `dense_q0`: `1.30W` ("Q0 dense, Q2/Q3 pruned")

Any mixed admission policy must choose one of those two observed
session-level outcomes per session. No synthetic within-session timings
or answer edits are allowed.

## Policies to evaluate

### Deployable simple policies

These may only use metadata known before Q0 runs:

- all pruned Q0
- all dense Q0
- dense Q0 on `short`
- dense Q0 on `medium`
- dense Q0 on `long`
- dense Q0 on each 2-bucket duration combination

### Oracle upper bounds

These are not deployable; they are admissible only as upper bounds:

- choose dense Q0 only when it improves Q0 correctness
- choose dense Q0 only when it improves total session correctness
- exact per-session frontier: among all binary session selections,
  compute the best achievable `speedup` at each `delta_correct`

## Hypotheses

### H1 — duration-only gating is insufficient

No duration-only deployable policy earns the preregistered `H_rescue`
bridge gate:

- all-query accuracy delta `>= -0.10`
- paired amortized speedup `>= 3.0x`

**Why this is plausible:** `1.30W` still loses accuracy in more than one
duration/split cell, so a single duration bucket is unlikely to isolate
all remaining Q0 risk cleanly enough.

**Falsified if:** any deployable duration-only policy passes `H_rescue`.

### H2 — the lane is still rescue-feasible in principle

The exact per-session admission frontier contains at least one point
that passes `H_rescue`, even if the simple duration policies fail.

**Why this matters:** if true, the right next step is a better admission
model or predictor. If false, then the current 3-query protocol is
effectively closed even for an oracle selector, and more 1.30 work
should move to protocol redesign rather than same-protocol admission.

**Falsified if:** the exact frontier has no point with
`delta_correct / 171 >= -0.10` and `speedup >= 3.0x`.

## Decision rules

1. If `H1` passes and `H2` passes:
   a simple live rerun is justified immediately.
2. If `H1` fails but `H2` passes:
   do not rerun blindly; move to predictor/admission-model work first.
3. If `H2` fails:
   close same-protocol 1.30 admission work as structurally unpromising
   and redirect to either a cheaper Q0 path or a longer-session protocol.

## Code path

- analysis module:
  `src/codec_through/phase1_30_admission_frontier.py`
- CLI:
  `scripts/analyze_phase1_30_admission_frontier.py`

## Output

- `analysis.json` containing:
  - deployable policy table
  - oracle upper bounds
  - exact frontier summary

## Execution

Pending.

## Result

Pending.

## Interpretation

Pending.
