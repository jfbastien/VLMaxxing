---
phase: 1.30W
date: 2026-04-24
parent: research/experiments/2026/2026-04-24-phase-1_30W-q0-dense-followup-pruned-full-prereg.md
artifacts:
  - research/experiments/2026/artifacts/phase1_30W_q0_dense_followup_pruned_full/
status: FULL RERUN COMPLETE. Q0 parity exact; strict and rescue gates fail.
---

# 1.30W — Dense Q0 admission, session-reuse follow-ups (full dev+holdout findings)

## Result

Against the completed `cold_dense` control on the same `57` VideoMME
sessions / `171` queries:

- cold accuracy: `0.5614` (`96/171`)
- positioned streaming accuracy: `0.5029` (`86/171`)
- **all-query delta = `-0.0585`**
- **paired amortized speedup = `2.7869×`**
- clean fraction `= 0.7719`
- degenerate fraction `= 0.0`
- parse failures `= 0`

The key decomposition is now exact:

- cold Q0 accuracy: `0.5965` (`34/57`)
- streaming Q0 accuracy: `0.5965` (`34/57`)
- **Q0 delta = `0.0000`**

- cold follow-up accuracy: `0.5439` (`62/114`)
- streaming follow-up accuracy: `0.4561` (`52/114`)
- **follow-up delta = `-0.0877`**

Runtime profile:

- cold mean end-to-end: `87.38 s`
- streaming mean end-to-end: `31.35 s`
- streaming mean first-query end-to-end: `92.09 s`
- streaming mean follow-up end-to-end: `0.984 s`
- streaming mean follow-up prefix coverage: `0.9815`

## Gate adjudication

### H_strict

**FAIL.**

- accuracy delta `= -0.0585` misses the `|Δacc_all| <= 0.05` band
- speedup `= 2.7869×` misses the `>= 3.0×` floor

### H_rescue

**FAIL.**

- accuracy delta `= -0.0585` is inside the `>= -0.10` rescue band
- speedup `= 2.7869×` misses the `>= 3.0×` floor

So the full rerun is a **near-miss on accuracy and a miss on the speed
gate**.

### H_q0

**PASS (exact).**

Q0 accuracy is numerically identical between cold and streaming:
`34/57` in both arms, delta `0.0000`.

Every completed `duration × split` Q0 slice stays exact:

- long dev: `0.25 -> 0.25`
- long holdout: `0.7778 -> 0.7778`
- long mixed: `1.0 -> 1.0`
- medium dev: `0.5 -> 0.5`
- medium holdout: `0.5 -> 0.5`
- short dev: `0.9 -> 0.9`
- short holdout: `0.5556 -> 0.5556`

### H_format

**PASS.**

- parse failures `= 0`
- degenerate fraction `= 0.0`

## Interpretation

This full rerun changes the 1.30 story materially, but it does not
fully reopen the bridge.

### 1. The original 1.30 failure was not the final word

Compared with the original `1.30` stacked run (`Δacc = -0.193`,
`3.326×`), the dense-Q0 admission policy improves fidelity by
**+13.45 pp** while keeping a large systems gain:

- original 1.30 streaming accuracy: `0.368`
- 1.30W streaming accuracy: `0.503`

So this is no longer a pure anti-claim. It is a **bounded near-miss**
with a clean first-query mechanism.

### 2. The remaining loss is entirely a follow-up problem

Q0 is solved exactly. Every remaining deficit sits in Q2/Q3.

That means the residual composition problem is not "session streaming"
in general and not "persistent KV" in general. It is **follow-up
behavior under the existing session-reuse path after dense-Q0
admission**.

### 3. The residual loss is regime-conditioned

The follow-up deltas are not uniform:

- long dev: `0.25 -> 0.125` (`-0.125`)
- long holdout: `0.5556 -> 0.5556` (`0.0000`)
- medium dev: `0.45 -> 0.45` (`0.0000`)
- medium holdout: `0.60 -> 0.50` (`-0.10`)
- short dev: `0.65 -> 0.55` (`-0.10`)
- short holdout: `0.6667 -> 0.5556` (`-0.1111`)

So the right claim is not "the rescue fails on long clips." It is
stronger and narrower:

- Q0 dense admission fully fixes the first-query damage,
- some regimes are already safe on follow-ups,
- the remaining miss is concentrated in a subset of follow-up regimes.

### 4. The `3.0×` rescue miss is structural under this protocol

Under the current 3-query session protocol, **dense Q0 alone makes the
`>= 3.0×` rescue floor unreachable even if follow-ups were free**.

Measured totals:

- actual streaming total: `5.361M ms`
- dense-Q0 total alone: `5.249M ms`
- target total for `3.0×`: `4.981M ms`

So even replacing every follow-up with `0 ms` would still leave the run
about `268.7k ms` short of the `3.0×` gate.

That means the next 1.30 experiment should **not** be "tune follow-ups a
bit more on the same 3-query benchmark." The current gate cannot be
earned that way.

Mechanistic caution:

- this full rerun predates the image-token activity instrumentation
- the configured follow-up keep-rate is `0.50`, but this result alone does
  **not** prove that follow-up vision pruning was materially active under
  prompt-cache reuse
- until the new instrumentation lands on a fresh run, the precise wording
  should stay: **dense-Q0 admission plus the existing session-reuse follow-up
  path**

## Decision

1. Keep the original `1.30` result as the negative baseline and root-cause
   predecessor.
2. Promote `1.30W` as the current best local bridge:
   exact Q0 parity, follow-up-only loss, clean formatting, large but
   sub-threshold speedup.
3. Treat the dense-Q0 3-query protocol as **structurally capped below
   the preregistered `3.0×` rescue floor**.

## Next work implied by this result

If we continue this line, the next experiment should target one of two
questions:

1. **Can we reduce Q0 cost safely on a restricted regime?**
2. **Does the same policy clear the deployment-speed claim under longer
   sessions?**

What should *not* be next: another blind same-protocol follow-up-only
keep-rate tweak. That can improve fidelity, but it cannot earn the
current `3.0×` gate on this 3-query benchmark.
