# Performance Methodology

This repo treats performance work as controlled research, not screenshot-friendly anecdotes.

The goal is not to produce impressive-looking latency numbers. The goal is to
measure the right thing, under controlled conditions, with enough context that
another person can tell whether the result matters.

## Core Rules

Every serious performance claim needs:

- a hypothesis
- a primary metric
- a comparison point
- an acceptance or rejection rule
- raw samples
- an environment record

If one of these is missing, the result is provisional.

## Start With The Hypothesis

Bad:

- "This should be faster."

Good:

- "Packet-size routing will reduce total latency on talking-head clips without reducing answer agreement."

- "Replacing pixel differencing with metadata-only routing will lower planner cost, but may lose agreement on FPV clips."

Good hypotheses are falsifiable.

Good experiments are preregistered enough that a later reader can tell whether
we moved the goalposts.

## Define The Unit Of Analysis

Do not mix units casually.

Repo-relevant examples:

- per clip
- per prompt
- per request
- per frame
- per model family

If the unit changes, say so explicitly.

## Separate Quality Metrics From Systems Metrics

For this repo, both are first-class.

Quality metrics:

- answer agreement
- accuracy delta
- chance-corrected agreement when the task format permits it
- semantic disagreement rate
- failure rate by content bucket

Systems metrics:

- TTFT
- total latency
- generation latency
- prompt processing speed
- peak memory
- planner overhead
- reuse ratio
- recompute-window ratio

Do not collapse them into one number.

## Keep Track A And Track B Separate

Track A:

- semantic substitution
- dense vision encode may still happen
- result proves output robustness, not sparse execution

Track B:

- sparse execution
- real decode, vision, attention, or prefill work must be skipped
- result must include wall-clock or memory evidence

Never report a Track A result as if it were a Track B speedup.

For short-answer QA, generation can dominate total latency. Report it as a
separate bucket instead of letting it hide changes in decode, planner, or vision cost.

## Pre-Register Acceptance Bands

Before running a decision-worthy experiment, write down:

- what counts as success
- what counts as rejection
- what counts as inconclusive

Example:

- accepted if accuracy stays within `0.5 pp` and agreement stays above `98%`
- rejected if accuracy drops more than `2 pp` or agreement falls below `90%`
- inconclusive in between, followed by a targeted follow-up

Exact numbers depend on the experiment, but the bands must be written down
before the run.

## Cold, Warm, And Idle

Do not report one latency number as if it explains everything.

Measure separately when relevant:

- cold start
- warm steady-state
- after-idle behavior

Warmup is allowed. Silent warmup is not.

## Report Distributions, Not Just Means

At minimum, report:

- p50
- p95
- p99 when sample sizes support it

When sample size is large enough, add bootstrap confidence intervals.

Mean-only reporting is not enough for latency-sensitive work.

## Agreement Needs Context

Always report enough to tell whether agreement is meaningful:

- baseline accuracy
- modified-path accuracy
- baseline-versus-modified agreement
- the answer-space size when applicable
- chance-corrected agreement such as Cohen's kappa for multiple-choice tasks

Aggregate agreement is not enough on its own.

When content buckets exist, report them per bucket, not only in aggregate.

## Prefer Paired Comparisons

When comparing A versus B:

- use the same clips
- use the same prompts
- use the same decode settings
- use the same sampling settings

If thermal drift or cache effects are plausible, randomize order or use ABBA ordering.

## Separate Decode And Temp I/O From Model Time

This matters especially on laptop hardware.

If the pipeline writes frames to `/tmp` and then reads them back, timing should
be split so we can see:

- decode cost
- temp-file or image encode/decode cost
- planner cost
- model cost

Otherwise the result will blur systems bottlenecks and mislead design choices.

## Preserve Raw Results

Every benchmark runner should be able to emit raw records to disk.

Raw records should include:

- timestamp
- git commit
- machine identifier
- model identifier
- prompt or clip id
- experiment track
- all primary metrics

Summaries are not a substitute for raw records.

## Lock Down Non-Essential Variables

When possible, fix:

- temperature
- max tokens
- frame sampling strategy
- clip resolution
- decode backend
- batch size

If one changes, log it as part of the experiment.

## Determinism Sanity Check

Before interpreting Track A agreement:

- run the dense baseline twice on the same input
- verify that the runtime is deterministic enough for the experiment
- record the runtime/backend versions involved

If the baseline itself is unstable, do not present cached-versus-dense
agreement as if it cleanly isolated the method.

## Failure Analysis Matters

When an experiment fails:

- say what was expected
- say what was observed
- state which hypothesis got weaker
- record the likely next test

Negative results are data. Unrecorded negative results are waste.

## Failure Attribution Ladder

Use one of these labels in experiment notes:

- harness failure: the measurement apparatus broke, so the result is void
- runtime failure: the model or backend could not produce output
- method failure, content-specific: the method failed on a specific bucket and narrows the scope
- method failure, systemic: the method failed across buckets and weakens the core claim
- interpretation failure: the experiment ran, but the preregistered bands or assumptions were wrong

## Minimum Template For A Serious Experiment

Use this template in experiment notes:

```text
Hypothesis:
Track:
Primary metric:
Secondary metrics:
Unit of analysis:
Model:
Clip set:
Prompt set:
Environment:
Warmup policy:
Comparison:
Acceptance band:
Rejection band:
Inconclusive rule:
Result:
Did it match expectation?
If not, what got falsified?
Next step:
```

## Repo-Specific Guidance

### Temporal Reuse Experiments

Always log:

- static ratio
- shifted ratio
- novel ratio
- refresh count
- frame routing decisions
- the exact diff formulation if pixel diff is used

### End-To-End Inference Experiments

Always log:

- dense baseline output
- cached or sparse output
- exact prompt
- clip identifier
- latency before and after

### Model Comparisons

Do not compare a smaller faster model against a larger slower model and call that a systems win for the method.

If the model changes, the result is partly about model size and capability.

For this repo:

- keep Qwen and Gemma acceptance bands separate
- use cross-family disagreement as evidence about scope, not as automatic failure of the whole method

## Timing Harness

For concrete timing rules such as clock source, backend synchronization, warmup
stability, and thermal guardrails, follow
[timing-harness.md](timing-harness.md).

## What We Will Not Do

- claim speedups from dense post-hoc replacement alone
- claim quality preservation from a tiny cherry-picked prompt set
- present one-off wall-clock anecdotes as stable evidence
- stack theoretical multipliers from unrelated methods and present them as measured system gains
