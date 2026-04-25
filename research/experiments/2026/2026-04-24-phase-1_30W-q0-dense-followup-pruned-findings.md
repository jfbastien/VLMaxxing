---
phase: 1.30W
date: 2026-04-24
parent: research/experiments/2026/2026-04-24-phase-1_30W-q0-dense-followup-pruned-prereg.md
artifacts:
  - research/experiments/2026/artifacts/phase1_30W_q0_dense_followup_pruned_short/
status: SHORT-SCOUT PASS. Promote to full dev+holdout paired rerun.
---

# 1.30W — Dense Q0 admission, session-reuse follow-ups (short scout findings)

## Result

The short scout passes the preregistered rescue gates.

Compared against a fresh `cold_dense` control on the same
`videomme_dev_v1_short_only.toml` seeds:

- cold accuracy: `0.7333` (`22/30`)
- positioned streaming accuracy: `0.6667` (`20/30`)
- **all-query delta = `-0.0667`**
- **amortized speedup = `3.059×`**
- clean fraction `= 0.667`
- degenerate fraction `= 0.0`
- parse failures `= 0`

Query-position split:

- cold Q0 accuracy: `0.900`
- positioned streaming Q0 accuracy: `0.900`
- **Q0 delta = `0.000`**

- cold follow-up accuracy: `0.650`
- positioned streaming follow-up accuracy: `0.550`
- **Q23 delta = `-0.100`**

## Gate adjudication

### H1-Q0

**PASS.**

Dense Q0 admission removes the short-scout first-query loss entirely:
`0.900 -> 0.900`, delta `0.000`.

### H2-all

**PASS.**

All-query delta versus cold dense is `-0.0667`, inside the preregistered
`>= -0.10` rescue band.

### H3-followup

**PASS (edge).**

Follow-up accuracy lands exactly on the preregistered floor:
`0.550`.

### H4-speed

**PASS.**

Amortized speedup is `3.059×`, above the preregistered `2.5×` floor.

### H5-format

**PASS.**

- parse failures `= 0`
- degenerate fraction `= 0.0`

## Interpretation

This is the first local 1.30 admission-policy lane that does what the
root-cause work predicted on the short scout.

The result is not "Qwen streaming is fixed." It is more specific:

- the dominant first-query failure really was the pruned Q0 leg,
- simply keeping Q0 dense removes that dominant error term,
- once Q0 is dense, the remaining follow-up loss contracts to the
  already-measured K-only scale (`0.55` vs cold `0.65`),
- and the bridge still keeps a real systems gain (`3.059×`).

So the 1.30 negative is no longer a dead end. A position-conditioned
admission policy is a viable direction for the full rerun.

Mechanistic caution:

- this short scout predates the image-token activity instrumentation
- the configured follow-up keep-rate is `0.50`, but this run by itself does
  **not** prove that follow-up vision pruning was materially active under
  prompt-cache reuse
- later write-ups should therefore describe this as **dense-Q0 admission plus
  the session-reuse follow-up path** unless the instrumentation says otherwise

## Decision

Per the preregistered rule, this short-scout PASS **promotes to a full
dev+holdout paired rerun**.

That full rerun is now the paper-relevant next step. If it holds, the
repo has an admission-policy composition lane worth continuing, not yet
a paper-grade bridge claim on its own.
