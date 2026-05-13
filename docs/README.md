# Docs Guide

This directory is for durable background, methodology, and provenance.

It is not the place for per-run scratch notes or agent-local thinking.

See [AGENTS.md](../AGENTS.md) for the canonical repo-wide read order.

This file only routes work inside `docs/`.

## What Goes Here

- stable measurement rules
- literature and standards references
- imported-target registers and reproduction status
- setup instructions that apply to any clean checkout
- clip and local-asset policy
- benchmark-native asset setup

## What Does Not Go Here

- one-off experiment notes
- tentative paper prose
- repeated copies of the same conclusion

## Where New Knowledge Goes

- active roadmap: [PLAN.md](../PLAN.md)
- paper claim and readiness ledgers:
  [paper/claim-matrix.md](../paper/claim-matrix.md) and
  [paper/publishability-status.md](../paper/publishability-status.md)
- experiment preregistration and results: [research/experiments](../research/experiments/)
- adopted, weakened, killed, revived ideas: [research/decision-log.md](../research/decision-log.md)
- falsified hypotheses ledger: [research/falsified-hypotheses.md](../research/falsified-hypotheses.md)
- paper contribution framing and anti-claims: [paper/framing.md](../paper/framing.md)

## Read Order

### Active

- [literature-map-2026-04-16.md](literature-map-2026-04-16.md) — current
  positioning map
- [onevision-encoder-research-2026-05-08.md](onevision-encoder-research-2026-05-08.md)
  — primary-source notes for OneVision-Encoder and VLMaxxing integration
- [benchmark-taxonomy.md](benchmark-taxonomy.md) — why each benchmark is
  active or deferred
- [related-work-table.md](related-work-table.md) — paper-facing
  method table with verified numbers
- [methodology/pareto-reporting.md](methodology/pareto-reporting.md)
- [methodology/planner-sweep.md](methodology/planner-sweep.md)
- [methodology/temporal-coverage-metrics.md](methodology/temporal-coverage-metrics.md)
  — budget-placement metrics (instrumentation pending)
- [methodology/feature-replay.md](methodology/feature-replay.md)

### Foundation

- [claim-register.md](claim-register.md)
- [reproduction-status.md](reproduction-status.md)
- [methodology/performance.md](methodology/performance.md)
- [methodology/preprocessing.md](methodology/preprocessing.md)
- [methodology/timing-harness.md](methodology/timing-harness.md)
- [methodology/codec-score-denominators.md](methodology/codec-score-denominators.md)
- [clip-policy.md](clip-policy.md)
- [benchmark-setup.md](benchmark-setup.md)
- [videomme-download-handoff.md](videomme-download-handoff.md)
- [local-setup.md](local-setup.md)

Historical source imports, review packets, and superseded strategy notes are not
kept in the release tree. Use the status docs above for current claims; use git
history only when auditing the provenance of a removed import.
