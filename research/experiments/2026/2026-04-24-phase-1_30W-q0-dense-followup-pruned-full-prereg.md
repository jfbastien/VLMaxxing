---
phase: 1.30W
date: 2026-04-24
parent:
  - research/experiments/2026/2026-04-24-phase-1_30W-q0-dense-followup-pruned-prereg.md
  - research/experiments/2026/2026-04-24-phase-1_30W-q0-dense-followup-pruned-findings.md
status: preregistered 2026-04-24. Full dev+holdout confirmation after short-scout PASS.
---

# 1.30W — Dense Q0, pruned follow-ups (full confirmation)

## Why this full run is justified

The short scout passed every preregistered gate:

- Q0 delta `= 0.000`
- all-query delta `= -0.0667`
- follow-up accuracy `= 0.550`
- speedup `= 3.059×`
- parse failures / degenerates `= 0`

That is strong enough to justify a full dev+holdout paired rerun on the
same policy.

## Policy under test

- `cold_dense`
- `streaming_q0_dense_followup_pruned_off`

where streaming uses:

- Q0 keep-rate `1.0`
- Q2/Q3 keep-rate `0.50`
- no hard reset

## Scope

- manifests:
  - `research/benchmark_manifests/videomme_dev_v1.toml`
  - `research/benchmark_manifests/videomme_holdout_v1.toml`
- model: `Qwen2.5-VL-7B-Instruct-4bit`
- frame count: `8`
- max tokens: `32`

## Hypotheses

### H_strict

The positioned admission policy fully reopens the original 1.30 budget:

- `|Δacc_all| <= 0.05`
- amortized speedup `>= 3.0×`

### H_rescue

Even if strict reopen fails, the policy still earns a strong bounded
rescue:

- `Δacc_all >= -0.10`
- amortized speedup `>= 3.0×`

### H_q0

The full-run Q0 loss remains controlled:

- `Δacc_q0 >= -0.05`

### H_format

- parse failures `<= 0.05`
- degenerate fraction `<= 0.10`

## Decision rules

- **H_strict PASS**: 1.30 shifts from a pure negative to a true
  composition rescue.
- **H_strict FAIL, H_rescue PASS**: the paper gets a bounded rescue
  story, not a full reopen.
- **H_rescue FAIL**: the short scout did not scale; keep 1.30 in
  anti-claim territory and treat the policy as split-sensitive.

## Runtime estimate

- cold dense dev+holdout union: ~4.3 h
- positioned streaming dev+holdout union: ~1.5 h
- analysis: ~1 min

Total: **~6 h**
