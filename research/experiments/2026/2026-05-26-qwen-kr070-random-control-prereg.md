# 2026-05-26 — Qwen kr=0.7 Four-Seed Random-Control Preregistration

Status: preregistered, not run.

Branch: `onevision-vlmaxxing-research`

Blessed launch path:

```bash
M5Q_CLEAN_CONTROL_PREREG=research/experiments/2026/2026-05-26-qwen-kr070-random-control-prereg.md scripts/run_ov6_m5_qwen_kr070_random_control.sh
```

This wrapper is the only blessed launch path for the clean M5 Qwen
VideoMME-short N=57 / 8-frame / layer-2 / kr=0.7 random-control protocol. Do
not use ad-hoc `scripts/run_phase1_51V.py` invocations to populate the
canonical tree.

## Motivation

The current Qwen kr=0.7 sparse-pruning evidence compares `codec_novel_coded`
against `magnitude_norm`, but the project already observed that
`magnitude_norm` can be weaker than random keep at kr=0.5/layer=2. A paper
sentence saying codec ranking is better than a baseline therefore needs a
matched random-keep control at the promoted kr=0.7 operating point.

## Fixed Configuration

- Model: `Qwen2.5-VL-7B-Instruct-4bit`
- Manifest: `research/benchmark_manifests/videomme_short_present_v1_n57.toml`
- Frame count: 8
- Max tokens: 32
- Vision prune layer: 2
- Configured keep rate: 0.70
- Codec source: `novel_coded`
- Codec score path: precomputed Qwen sidecars, geometry
  `qwen_merged_groups_v1`
- Random seeds: 1, 7, 42, 100

## Required Artifact Tree

Canonical root:

- `m5_ov6_qwen_n57_kr070_l2_random_control/`

Required arm paths:

- `m5_ov6_qwen_n57_kr070_l2_random_control/dense/`
- `m5_ov6_qwen_n57_kr070_l2_random_control/magnitude_norm/`
- `m5_ov6_qwen_n57_kr070_l2_random_control/codec_novel_coded/`
- `m5_ov6_qwen_n57_kr070_l2_random_control/uniform_random_seed1/`
- `m5_ov6_qwen_n57_kr070_l2_random_control/uniform_random_seed7/`
- `m5_ov6_qwen_n57_kr070_l2_random_control/uniform_random_seed42/`
- `m5_ov6_qwen_n57_kr070_l2_random_control/uniform_random_seed100/`

Required audit:

- `codec_vs_random_multiseed_audit.json`

## Hypothesis

If `codec_novel_coded` is a useful sparse-token ranking signal beyond exposing
a weak `magnitude_norm` baseline, the same-run M5 `codec_novel_coded` correct
count should meet or exceed the matched four-seed uniform-random keep
distribution at the promoted kr=0.7/layer=2 operating point.

## Gate

A bounded positive paper sentence is allowed only if all conditions hold:

- same-run `codec_novel_coded` correct count is at least the random-seed mean;
- at least 3/4 random seeds are less than or equal to `codec_novel_coded` by
  point estimate;
- no random seed beats `codec_novel_coded` by three or more items.

This supports only a bounded point-estimate statement for this operating point.
It does not support broad codec superiority or statistical significance unless
the paired tests and sample size justify that separately.

## Falsifier

Classify the positive codec-over-random sentence as falsified if either
condition holds:

- the random-seed mean exceeds the same-run `codec_novel_coded` count;
- at least two random seeds beat `codec_novel_coded` by three or more items.

If the positive gate fails and the falsifier does not fire, classify the result
as inconclusive and report the exact point estimates without a positive
codec-over-random claim.

## Analysis

Run:

```bash
scripts/analyze_ov6_qwen_kr070_random_control.py --root research/experiments/2026/artifacts/m5_ov6_qwen_n57_kr070_l2_random_control
```

The analyzer must write `codec_vs_random_multiseed_audit.json` and
`codec_vs_random_multiseed_audit.md`, hard-fail on missing arms, mismatched
item order, parse failures, configuration drift, non-sidecar codec scoring, or
effective keep-rate mismatch, and compare `codec_novel_coded` against each
random seed with exact McNemar tests.

## Paper Use

This run is a control for the sparse-pruning claim only. It is not an
end-to-end model speedup run, not a refresh-planning run, and not a session
reuse result. The paper-facing text must name the random-control denominator
and avoid any positive codec-over-random language unless the gate above passes.
