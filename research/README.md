# Research Workflow

This directory is the durable experiment ledger.

## Structure

- [decision-log.md](decision-log.md): adopted, weakened, killed, revived ideas
- [falsified-hypotheses.md](falsified-hypotheses.md): queryable ledger of
  rejected hypotheses (phase id, magnitude, scope of rejection)
- [prompt_bank](prompt_bank/): versioned prompt sets and answer keys
- `experiments/<year>/...`: one dated file per decision-worthy experiment family

Older experiment notes preserve the wording and provenance that existed when
they were written. Some of those notes mention pre-release seed imports or
sibling checkouts that are intentionally absent from the OSS release tree; use
the current [decision log](decision-log.md), [experiment registry](experiments/registry.md),
and [claim register](../docs/claim-register.md) as the live sources of truth.

## Experiment Note Template

Each experiment note should contain these sections in this order:

1. `Preregistration`
2. `Execution`
3. `Result`
4. `Interpretation`
5. `Links`

Put the preregistration in the file before the run happens.

## Pre-Registration Minimum

Every decision-worthy experiment should state:

- hypothesis
- track (`A` or `B`)
- primary metric
- secondary metrics
- unit of analysis
- comparison
- acceptance band
- rejection band
- what counts as inconclusive

When an experiment finishes, explicitly state the preregistration outcome:

- `Accepted`
- `Rejected`
- `Inconclusive`
- `Accepted with caveat` only when the note names the exact caveat

If you want to use softer narrative language like `partial reproduction`, say
that in `Interpretation`, not instead of the preregistration outcome.

## Update Rules

- one file per experiment family, not one file per tiny run
- append new runs chronologically
- link raw artifacts instead of pasting giant dumps
- update [decision-log.md](decision-log.md) when a hypothesis changes status

## Long Local Runs

For long semantic runs on this laptop, prefer cooperative termination over
force-killing processes:

- use `--checkpoint-path <json>` to persist partial results after each chunk
- use `--stop-file <path>` to request clean exit after the current item or
  chunk

This is an operational convenience only. It does not make a run timing-safe for
Track B.
