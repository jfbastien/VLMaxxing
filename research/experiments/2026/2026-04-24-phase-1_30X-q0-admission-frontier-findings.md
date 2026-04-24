---
phase: 1.30X
date: 2026-04-24
parent: research/experiments/2026/2026-04-24-phase-1_30X-q0-admission-frontier-prereg.md
artifacts:
  - research/experiments/2026/artifacts/phase1_30X_q0_admission_frontier/
status: COMPLETE. Speed/accuracy rescue is feasible; no format-clean point exists within the current 1.30 / 1.30W endpoint family.
---

# 1.30X — Q0 admission frontier analysis (findings)

## Result

The offline frontier analysis over the landed `1.30` and `1.30W`
session outputs answers the key question cleanly:

- **same-protocol 1.30 is not dead on speed/accuracy**
- **but the current 2-endpoint family has no format-clean rescue point**

### Deployable simple policy

The best deployable duration-only policy is:

- **`dense_on_medium_short`**

Observed by exact replay over the landed session outputs:

- stream correct `82/171`
- cold correct `96/171`
- **Δacc = `−0.0819`**
- **paired amortized speedup = `3.0168×`**
- q0 delta `= −1/57`
- follow-up delta `= −13/114`
- parse failures `= 2`
- degenerates `= 2`

So a simple duration-gated admission policy **does pass the preregistered
speed/accuracy rescue band**, but it still fails format hygiene.

The remaining bad sessions under that policy are exactly:

- `videomme:long:783-2`
- `videomme:long:847-3`

Both are long-session residuals inherited from the original `1.30`
endpoint.

### Oracle / exact frontier

The exact per-session frontier is stronger:

- best strict point: **Δacc = `0.0000`, speedup = `3.0781×`**
- best rescue point: **same**
- best speed at or above the rescue floor:
  **Δacc = `−0.0994`, speedup = `3.2851×`**

So the protocol is **rescue-feasible in principle**. An oracle selector
over the already-landed endpoints can recover full cold accuracy while
staying above `3.0×`.

But there is an equally important negative result:

- **best strict-with-format: none**
- **best rescue-with-format: none**

That means no per-session mixture of the current `1.30` and `1.30W`
endpoint families simultaneously achieves:

1. speedup `>= 3.0×`
2. rescue/strict accuracy band
3. zero parse failures / zero degenerates

## Preregistered verdicts

### H1 — duration-only gating is insufficient

**FALSIFIED on the preregistered speed/accuracy criterion.**

`dense_on_medium_short` passes `H_rescue`:

- `Δacc = −0.0819`
- `speedup = 3.0168×`

But it still fails `H_format`, so the falsification is narrow and
important: duration gating is enough to reopen speed/accuracy, not
enough to earn a full paper-grade bridge on its own.

### H2 — the lane is still rescue-feasible in principle

**EARNED strongly.**

The exact frontier contains a point at:

- **Δacc = `0.0000`**
- **speedup = `3.0781×`**

So the live scientific question is no longer "is the current protocol
structurally dead?" It is "can we realize a good frontier point with a
deployable policy that also clears format hygiene?"

## Interpretation

This changes the 1.30 story again:

1. `1.30` remains the hard negative baseline.
2. `1.30W` remains the key mechanistic bridge:
   dense Q0 solves the first-query loss exactly.
3. `1.30X` shows that a cheaper safe-Q0 admission lane **does exist**
   under the current 3-query protocol.

So the repo should no longer frame 1.30 as a lane that is only alive via
longer-session amortization. That is too strong after `1.30X`.

The stronger, more accurate claim is:

- speed/accuracy rescue is achievable with session-level admission,
- but the current endpoint family cannot eliminate the remaining format
  failures,
- and those failures are concentrated in two long sessions.

## Decision

1. Reopen 1.30 as an active **admission-policy / protocol-redesign**
   lane.
2. Do **not** rerun another global keep-rate or global dense-Q0 policy.
3. If 1.30 continues immediately, target the remaining long-session
   format failures explicitly.

## Next work implied by this result

The next 1.30 continuation should be one of:

1. a targeted policy that changes behavior on the two remaining
   long-session failure modes, or
2. a third endpoint family that changes those long follow-ups directly
   (for example, a refresh/reset variant), because the current 2-endpoint
   family has no format-clean frontier point.

What should *not* be next:

- another blind same-protocol global rerun,
- another follow-up-only keep-rate sweep,
- or another attempt to argue that the current protocol is simply dead.
