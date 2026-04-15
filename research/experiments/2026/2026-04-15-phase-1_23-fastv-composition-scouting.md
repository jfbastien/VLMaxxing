# Phase 1.23: FastV Composition Scouting (Design Doc Only)

## Preregistration

Objective:

- produce a written implementation plan and dependency map for
  composing the temporal-reuse policy with FastV's token-pruning hook
  on the Qwen 2.5-VL MLX path
- no benchmark runs, no code change — this phase only determines
  whether Stage F composition is a 1–2 day job or a 1–2 week job

Claim register targets:

- Stage F integration readiness; paper-framing contingency if phase
  1.12 holdout fails outright (fallback narrative in
  `docs/execution-plan-round-7.md`)

Reproduction mode:

- scouting

Track:

- methodology / paper-framing

Gating:

- runs any time; intentionally a low-cost filler phase that slots in
  between GPU-bound phases and does not contend with the sweep.

Hypotheses:

- H1 (orthogonality): FastV hooks at the decoder layer (post-encode),
  while temporal reuse is at the encoder layer (pre-decode) — the two
  compose with no interference beyond token-count arithmetic.
- H2 (cost): multiplicative budget reduction (e.g. 30% cached × 45%
  FastV = 16.5% of baseline tokens) IF no degradation.
- H3 (engineering effort): integrating FastV in MLX requires a
  per-layer attention mask override that is not currently exposed;
  the scouting report should confirm or deny this and estimate lines
  of change.

Acceptance band:

- scouting produces `docs/fastv-composition-plan.md` with:
  - hook point map
  - MLX API touch list
  - 1–2 day vs 1–2 week classification
  - smoke-test strategy (1-item pilot before full slice eval)
- no contradictory evidence found that would kill Stage F.

Rejection band:

- MLX does not expose the layer-level mask hook FastV requires →
  Stage F blocked or requires a fork of mlx-vlm.

Inconclusive:

- partial information only; need runtime experimentation to confirm
  hook semantics.

Planned sources to read:

- FastV paper (FastV: Fast Video Understanding via Fast Vision Token
  Reduction, CVPR 2024)
- mlx-vlm attention mask exposure in Qwen2.5-VL
- existing composition precedents in the repo's seed/ directory

Runtime: ~1 hr research + 30 min writing.

## Execution

Pending. Runs as a filler task when GPU-bound phases are in flight.

## Result

Pending.

## Interpretation

Pending.

## Links

- [execution plan round 7 — Stage F](../../../docs/execution-plan-round-7.md)
- [PLAN.md — SOTA position](../../../PLAN.md)
