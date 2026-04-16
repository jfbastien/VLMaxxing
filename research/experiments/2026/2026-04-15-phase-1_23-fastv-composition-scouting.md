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

Completed 2026-04-16 as a research-only scouting pass. No code was
written, no mlx-vlm fork was made. Scouting report committed to
`docs/fastv-composition-plan.md`.

## Result

Preregistration outcome: **Accepted with caveat** — the scouting
output is a clean design doc (`docs/fastv-composition-plan.md`) and
covers all preregistered deliverables, but the `trivially portable`
claim was too strong and had to be corrected per 2026-04-16 audit.

Key findings:

- **Hook site confirmed**: `Qwen2Model.__call__` layer loop in
  `mlx_vlm/models/qwen2_5_vl/language.py` (~line 250-253)
- **Blocker identified**: mlx-vlm does NOT expose per-layer attention
  scores. The fused Metal SDPA kernel
  (`mx.fast.scaled_dot_product_attention`) returns only the projected
  output; no flag exposes softmax weights. FastV requires patching
  the attention class to materialize attention scores at the K-th
  layer.
- **Effort classification**: requires an mlx-vlm fork with attention
  API additions. Estimated ~1–2 weeks engineering including KV cache
  bookkeeping and MRoPE (3-D position IDs) index surgery for dropped
  tokens.
- **No prior art**: mlx-vlm and mlx-lm issue trackers have no open
  or closed issues about attention-score introspection or token
  dropping. Starting from scratch.
- **Smoke test proposed**: one-clip prefill before/after with K=2,
  R=50%; assert answer match + prefill time reduction.

## Interpretation

Revised from "trivially portable" earlier framing (caught by
2026-04-16 audit):

- FastV is **algorithmically orthogonal** to our encoder-side
  temporal cached method — the two attack different compute axes
  and compose in principle.
- FastV is **NOT trivially portable** to MLX. The logic is simple
  (sort tokens by attention score, mask downstream layers) but the
  *required signal* (per-layer attention scores) is not exposed by
  the current mlx-vlm stack.
- Therefore phase 1.32 requires an mlx-vlm fork as a prerequisite.
  Gate Stage F engineering on phase 1.20 N=30 confirmation first;
  if temporal reuse has a paper claim on its own, FastV is optional
  rather than mandatory.

## Links

- [execution plan round 7 — Stage F](../../../docs/execution-plan-round-7.md)
- [PLAN.md — SOTA position](../../../PLAN.md)
