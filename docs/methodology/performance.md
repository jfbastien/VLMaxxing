# Performance Methodology

This repo treats performance work as science, not vibes.

The goal is not to produce impressive-looking latency numbers. The goal is to
measure the right thing, under controlled conditions, with enough context that
another person can tell whether the result matters.

## Core Rules

Every serious performance claim needs:

- a hypothesis
- a primary metric
- a comparison point
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

## Define The Unit Of Analysis

Do not mix units casually.

Examples:

- per clip
- per prompt
- per request
- per frame
- per model turn

If the unit changes, say so explicitly.

## Separate Quality Metrics From Systems Metrics

For this repo, both are first-class.

Quality metrics:

- answer agreement
- accuracy delta
- semantic disagreement rate
- failure rate by content bucket

Systems metrics:

- TTFT
- total latency
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

## Failure Analysis Matters

When an experiment fails:

- say what was expected
- say what was observed
- state which hypothesis got weaker
- record the likely next test

Negative results are data. Unrecorded negative results are waste.

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

## What We Will Not Do

- claim speedups from dense post-hoc replacement alone
- claim quality preservation from a tiny cherry-picked prompt set
- present one-off wall-clock anecdotes as stable evidence
- stack theoretical multipliers from unrelated methods and present them as measured system gains
