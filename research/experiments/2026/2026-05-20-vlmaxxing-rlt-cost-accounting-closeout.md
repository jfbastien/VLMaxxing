# 2026-05-20 VLMaxxing + RLT cost-accounting closeout

Status: post-run validation and paper-editor notes. This note does not launch
new experiments.

## Question

After the cross-benchmark Gemma run landed in commit `8685f7c`, are we ready to
stop debating the query-aware branch and do the next science? What exactly did
we win, and how should it be explained without jargon?

## Verified Artifacts

- `research/experiments/2026/artifacts/rlt_query_routing_cost_accounting/cost_model_fit_n11.json`
- `research/experiments/2026/artifacts/rlt_query_routing_cost_accounting/mvbench_hosted_dev/`
- `research/experiments/2026/artifacts/rlt_query_routing_cost_accounting/tomato_motion_dev/`
- `research/experiments/2026/artifacts/rlt_query_routing_cost_accounting/videomme_short/`

## Claim Audit

### What Claude got right

- The run materially strengthens the stage-cost story. The prefill+vision
  ceiling fit covers `11` local Gemma cells and lands at `R^2=0.972`, mean
  absolute relative error `2.36%`, and max absolute relative error `7.85%`.
- The new admission-only rows are consistent with the model rather than
  lucky one-offs. The six new rows have prefill+vision relative errors between
  `-2.20%` and `+0.44%`.
- VideoMME-short random admission is the cleanest new row: `20/20` parsed
  choice agreement, `0.000` accuracy delta, and `1.098x` E2E speedup with CI
  `[1.061x, 1.137x]`.
- Random-valid vision masking with admission disabled is the clean denominator
  control in this run: raw generation text matches dense exactly on MVBench
  hosted-dev (`54/54`), TOMATO motion-dev (`30/30`), and VideoMME-short
  (`20/20`). The associated E2E gains are small (`1.025x`, `1.012x`,
  `1.005x`), so the control says "random vision masking does not buy much
  wall-clock here unless the LM prompt is shortened."
- The cost model, not text routing or speculative admission, is the scientific
  object worth carrying forward on this branch.

### Corrections

- Do **not** say VideoMME-short is token-sequence identical. It is parsed-choice
  identical. In the random arm, `14/20` rows have different raw generation text
  while preserving the parsed choice and correctness.
- Do **not** say MVBench hosted-dev is globally "free." The random arm has
  aggregate `+0.019` accuracy delta at `1.188x`, but choice agreement is only
  `0.630` and four n=3 buckets fail the bucket quality gate. The honest wording
  is "no detected aggregate regression at n=54, with bucket churn still visible."
- Do **not** promote the harm-rate residual term to a headline. On the `n=11`
  table, harm-rate correlation with prefill+vision residual is `r=-0.548`,
  and the exploratory harm-augmented fit improves LOOCV RMSE from `0.0559` to
  `0.0478`. Useful diagnostic; not a confirmed predictive term.
- Do **not** call random vision-mask pruning broadly exact-output-equivalent.
  The evidence is narrower: random-valid vision masking with prompt admission
  disabled is raw-text identical on the three cost-accounting controls above.
  It is a denominator control for this Gemma/MLX setup, not a universal
  statement about all random token masks or all substrates.

## New Rows

| cell | n | E2E | accuracy delta | choice agreement | verdict |
|---|---:|---:|---:|---:|---|
| MVBench hosted random admission | 54 | `1.188x` | `+0.019` | `0.630` | aggregate pass, bucket churn |
| MVBench hosted fixed admission | 54 | `1.157x` | `-0.037` | `0.704` | aggregate pass, bucket churn |
| TOMATO motion-dev random admission | 30 | `1.077x` | `+0.000` | `0.367` | aggregate pass, high answer churn |
| TOMATO motion-dev fixed admission | 30 | `1.053x` | `+0.067` | not headline | aggregate pass, small n |
| VideoMME-short random admission | 20 | `1.098x` | `+0.000` | `1.000` | clean parsed-choice row |
| VideoMME-short fixed admission | 20 | `1.117x` | `+0.100` | `0.700` | positive point estimate, likely small-n noise |

## Plain Explanation

There are two different costs hidden inside "visual tokens."

First, the vision encoder has to turn video frames into visual features. RLT is
a cheap way to keep fewer visual patches before that stage. This can save time
when the vision encoder is a meaningful part of the bill, but random-valid
vision masking alone was already raw-output identical in the new no-admission
controls and bought only about `0.5-2.5%` E2E. That is why the paper should not
sell a clever vision-scoring story unless a scorer beats the controls under the
same denominator.

Second, after vision features exist, the language model still has to read a
long prompt full of image-placeholder positions. Admission scheduling removes
some of those placeholders before language-model prefill. That is the lever in
the new cross-benchmark run: the model reads a shorter multimodal prompt, so
prefill gets faster.

The key result is not that one pruning rule is magic. The key result is that
wall-clock speed follows the bill. If you shorten a stage that owns half the
runtime by about `1.4x`, the whole request gets about `1.2x` faster. If video
decode or generation dominates the request, the same pruning can do almost
nothing. The `n=11` model predicts this with `2.36%` mean absolute relative
error across cells spanning `0.984x` to `1.779x` E2E.

## Better Paper Framing

Use this as editor-facing prose, not final manuscript text:

> We do not start from token count. We start from the bill. A video VLM spends
> time decoding video, running the vision encoder, prefilling the language model
> over the multimodal prompt, and generating text. A pruning method only speeds
> up the stages it actually touches.
>
> In Gemma 4 E4B on MLX, removing image placeholders before language-model
> prefill gives repeatable first-query speedups: `1.05x-1.19x` E2E across
> MVBench hosted-dev, TOMATO motion-dev, and VideoMME-short, with no detected
> aggregate accuracy loss in these slices. The cleanest row is VideoMME-short:
> `20/20` parsed choices unchanged at `1.10x` E2E.
>
> A simple stage model predicts the result: measure what fraction of dense
> runtime belongs to prefill and vision, measure how much each changed stage
> was shortened, and compute the expected end-to-end gain. Across `11` Gemma
> cells, that model explains a `0.98x-1.78x` speedup range at `2.36%` mean
> relative error. The practical lesson is simple: prune the stage that dominates
> the bill, and verify paired answers. Token count by itself is not an
> efficiency claim.

Avoid:

- "vision-mask scoring is decorative" as a universal field claim;
- "exact-output equivalent" unless the artifact proves raw text/token identity;
- "free speedup" when choice churn or bucket regressions remain;
- "query-aware routing" as the paper-1 mechanism.

## Next Science

### M3

No more broad M3 query-aware implementation on this branch. The current M3
science supports closeout. Optional M3-only follow-ups are reviewer-response
work, not blockers. The bounded executable plan is now preregistered in
`research/experiments/2026/2026-05-20-rlt-m3-cost-accounting-followup-prereg.md`
and implemented by `scripts/run_rlt_m3_cost_accounting_followup.sh`.

1. Multi-keep-rate admission sweep on the cheapest clean slice if we need a
   Pareto curve. The default M3 follow-up brackets VideoMME-short at `kr=0.3`
   and `kr=0.7` around the existing clean `kr=0.5` row. Hypothesis: lower
   keep-rate increases prefill speed but causes answer churn; falsifier: speed
   does not follow placeholder reduction or misses the stage-cost prediction by
   more than `8%` absolute relative error.
2. A one-item speculative-admission cache-reuse smoke if we later build the
   rollback path. Hypothesis: fallback can reuse vision features and charge no
   second vision stage; falsifier: timing ledger shows a second vision charge
   or fallback differs from no-admission dense.

### M5

Run M5 as scale confirmation, not discovery. The M5 question is not "does
query-aware admission work?" It is:

- Does the cheap RLT scorer remain cheap at the 26B Gemma-family scale?
- Does the stage-cost model still predict the observed E2E gain when dense
  stage shares change?

Acceptance:

- n=1 smoke passes complete pairing, sparse-vision work is actually skipped,
  and scorer timings are present.
- The first n=30 C-VISION row lands inside the preregistered ceiling tolerance
  before any expansion cells are interpreted.

Falsification:

- RLT scorer cost grows enough to erase vision-stage savings.
- The measured E2E row misses the stage-cost prediction beyond tolerance under
  clean timing provenance.
- Fidelity or parse gates fail in the core VideoMME row.

### Query-Aware Fork

Park query-aware implementation until the VLMaxxing/RLT closeout is frozen.
The future branch should inherit the cost-accounting discipline and stage
features, but none of the current branch's headline numbers. It must earn its
own fixed, random, no-admission, and admission-only controls on held-out data.
