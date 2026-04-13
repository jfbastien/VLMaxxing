# Research Workflow

This directory is the durable experiment ledger.

## Structure

- [decision-log.md](decision-log.md): adopted, weakened, killed, revived ideas
- [prompt_bank](prompt_bank/): versioned prompt sets and answer keys
- `experiments/<year>/...`: one dated file per decision-worthy experiment family

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

## Update Rules

- one file per experiment family, not one file per tiny run
- append new runs chronologically
- link raw artifacts instead of pasting giant dumps
- update [decision-log.md](decision-log.md) when a hypothesis changes status
