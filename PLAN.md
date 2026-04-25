# Research Plan

Last updated: 2026-04-25

> **This file is the project charter and top-level router.**
>
> **Paper spine (2026-04-21, round-26):** three contributions —
> **C-CEILING**, **C-PERSIST**, **C-VISION** — with Qwen routing as the
> **mechanism-validation backbone** and codec-through-sam as
> **deployment-scale evidence**. The paper-facing spine lives in:
> [`paper/abstract.md`](paper/abstract.md),
> [`paper/intro.md`](paper/intro.md),
> [`paper/framing.md`](paper/framing.md), and
> [`paper/priority.md`](paper/priority.md).
>
> Per-phase experiment state lives in:
> [`research/experiments/registry.md`](research/experiments/registry.md)
> — that file is the single source of phase truth.
>
> **Current execution router (2026-04-25):** the original closeout queue has
> finished. The active sequential follow-up queue is
> `1.55F → 1.55I → 1.55H → 1.30AB sweep → conditional 1.30AE`.
> `1.30AA` is closed for the old `kr_Q0=0.67` policy after `1.30Z`, and
> `1.58` is explicitly a larger-memory-machine experiment under the current
> 16 GB laptop policy. See
> [`research/experiments/2026/2026-04-25-paper-followup-runbook.md`](research/experiments/2026/2026-04-25-paper-followup-runbook.md).
>
> Lane A / temporal-routing research strategy (now the
> mechanism-validation backbone, not the headline) lives in:
> [`docs/research-strategy-post-codecsight.md`](docs/research-strategy-post-codecsight.md)
>
> Literature positioning lives in:
> [`docs/literature-map-2026-04-16.md`](docs/literature-map-2026-04-16.md)
>
> If any other part of PLAN.md contradicts the registry or paper spine,
> fix PLAN.md.

## Charter

Build a rigorous research program around codec-conditioned dynamic compute for
video VLMs on Apple Silicon.

Primary objective:

- determine which cheap temporal and codec-derived signals can reduce video-VLM
  work without unacceptable answer drift

Secondary objectives:

- keep semantic validation separate from true systems speedup
- preserve negative results so the project narrows the space over time
- accumulate durable notes that are strong enough to support a later paper

Non-goals for the current phase:

- large-scale training
- speculative end-to-end stackup arithmetic presented as measured fact
- architecture changes without local evidence

## Current Verified Position

The imported whitepaper, predecessor repo, and direct artifact checks justify a
narrow but useful starting point:

- video-VLM outputs can tolerate substantial temporal feature reuse
- the strongest current evidence is Track A answer-stability evidence
- Track A does not yet prove skipped encoder or attention work
- simple pixel or packet signals are worth testing as routing signals
- local Qwen 3B and Gemma E4B control runs now show deterministic dense baselines and exact dense-through-cache identity on the preregistered local probes
- the initial local Qwen synthetic pilot produced dense-versus-cached agreement
  of `1.0` on `12` scored items, but the current suite does not yet include
  divergence-capable or natural-video scored items and should not be generalized
- the repaired local v2 suite now contains a real controlled failure:
  default same-position reuse missed one middle-dependent OCR event that dense
  answered correctly
- a follow-up temporal-necessity ablation shows that two apparent v2 passes are
  contaminated by prompt structure or endpoint solvability, so the current
  discriminating subset is smaller than the raw `11/12` cached headline
- direct repeated-image feature identity is now reproduced locally on the Qwen
  3B vision path, while the imported locality and shift-strength claims remain
  only partially reproduced here
- repaired mechanism probes removed the worst synthetic boundary artifact, but
  the local MLX `4-bit` path still remains weaker than the imported
  whitepaper-strength locality and shift story
- the whitepaper's content-class redundancy ordering is now reproduced locally
  in generalized form on the predecessor cross-check clips: talking-head stays
  highest-reuse, surveillance stays intermediate, and FPV-like egomotion stays
  lowest-reuse
- a narrow endpoint-oriented real-video slice on the predecessor cross-check
  clips now reproduces dense-versus-cached answer stability locally on Qwen 3B
  with `6/6` dense, `6/6` `STATIC`-only, and `6/6` `STATIC+SHIFTED`; this is
  accepted with caveat as an endpoint-oriented generalized reproduction, not a
  middle-event real-video reproduction
- the current Qwen Track A harness on this M3 Air remains unstable for a full
  long-lived single-process `12`-item run; chunked subprocess execution remains
  the adopted semantic harness constraint
- real-video `720p` cross-check work currently requires `chunk_size = 1` on
  this M3 Air to avoid the same Metal timeout class seen at larger chunk sizes
- long local semantic runs now support cooperative stop-file termination and
  checkpointed partial results so automation does not depend on force-killing
  jobs
- the benchmark-native TOMATO and MVBench lanes are now online on local Qwen
  `7B` via MLX, but they diverge materially:
  - TOMATO `30`-item subset: dense `0.300`, cached `0.233`, agreement `0.833`
  - MVBench hosted `54`-item subset: dense `0.630`, cached `0.648`, agreement
    `0.870`
- local strict and loose parser rescoring are identical on both benchmark
  slices because dense and cached parse failures stayed at `0`
- the predecessor `100%` benchmark-agreement headline is not a safe strict-parser
  target for this repo:
  direct artifact inspection plus the documented parse-`A` fallback mean local
  comparisons should treat it as parser-permissive external evidence rather
  than as the sole benchmark target
- the MVBench `+1` cached-over-dense edge is sampling noise on the current
  hosted `54`-item slice (`3` cached improvements versus `2` regressions, exact
  paired `p = 1.0`)
- benchmark interpretation caveat:
  the imported benchmark path is also Qwen `7B` via `mlx-vlm`; local benchmark
  gaps should be framed around subset policy, quantization, package revisions,
  and preprocessing rather than a generic `MLX versus PyTorch` mismatch
- benchmark-path identity now holds exactly on smoke items from both TOMATO and
  MVBench on the local Qwen `7B` runner
- benchmark reuse accounting is now pad-masked by default, with raw padded
  reuse kept only as an auxiliary descriptive field
- benchmark process rules are now part of the research substrate:
  - benchmark runs should fail on dirty trees by default
  - planner search should happen on explicit dev manifests rather than on the
    only reported slice
  - disjoint holdout manifests should stay frozen until a candidate policy is
    selected
- first-frame benchmark ablations now sharpen the contrast:
  - TOMATO `30`-item slice drops from dense `0.300` at `8` frames to `0.067`
    at frame `0` only
  - hosted MVBench `54`-item slice drops from dense `0.630` at `8` frames to
    `0.519` at frame `0` only
- the current TOMATO versus MVBench gap therefore looks more like a
  temporal-evidence-concentration / budget-placement difference than a
  parser issue on the current slices (see `paper/claim-matrix.md`
  language rule: avoid "content-conditioned" as too broad)
- targeted TOMATO `direction` refresh sweeps now show that the current failure
  is refresh-sensitive on that five-item slice rather than an obvious
  benchmark-path breakage:
  - no refresh: cached `0.2`, agreement `0.6`
  - refresh every `4` frames: cached `0.6`, agreement `1.0`, active reuse
    `0.732`
- the first motion-focused planner comparison now narrows the method space:
  - on the TOMATO motion dev slice, `mean + static,shifted + max_age=4`
    improved agreement from `0.733` to `0.867` while keeping active reuse at
    `0.698`
  - the same policy failed to generalize on the disjoint motion holdout:
    agreement fell from `0.867` to `0.800` and cached accuracy stayed flat
  - the first `changed_pixel_fraction` attempt did not beat the default mean
    planner on the same dev slice
  - the next statistic-only comparison tightened that further:
    - `max_abs (24, 96)` matched the default mean planner exactly at the same
      active reuse budget
    - `top_k_mean (12, 36)` and `max_abs (12, 48)` spent about the same
      fresh-vision budget as `mean + max_age=4`, but still failed to improve
      agreement over the default mean planner
    - all tested statistic-only variants left the TOMATO `direction` bucket at
      cached `0.2`, agreement `0.6`
    - bounded age therefore remains the strongest current dev-only lever on
      the motion slice
  - matched dense frame-budget baselines now add a stronger control:
    - on the motion dev slice, dense `1` through `4` frames all plateau at
      `0.267`
    - dense `6` is the first real dense recovery at `0.400`
    - `mean + max_age=4` matches that `0.400` cached accuracy at about
      `1247` fresh-vision token-equivalent budget versus dense `6` at `2400`
    - the disjoint holdout does not preserve that win cleanly:
      dense `6` only reaches `0.267`, while the cached holdout policies stay at
      `0.200`
  - matched MVBench motion frame-budget baselines (phase 1.9) extend the
    same control to a different content class:
    - MVBench motion dev dense curve is non-monotonic (peak `0.733` at
      `4` frames, drops to `0.600` at `8` frames)
    - MVBench motion holdout dense curve is monotonically increasing (peaks
      `0.733` at `8` frames)
    - same task labels, disjoint clips: the curve-shape difference is
      content-driven and motivates content-aware sampling later
  - infrastructure landed in round 7 to enable proper grid-search:
    - feature replay cache with v2 model-content-hash key
    - planner grid-search driver with calibration + sweep + max-policies cap
    - Pareto analysis driver with strict-domination semantics
    - per-letter logprob logging + stratification analyzer for the
      confidence-vs-staleness split
    - all 4 motion-slice planner calibrations (TOMATO + MVBench, dev +
      holdout, 144 candidate policies each)

That is the center of the project today.

## Current SOTA Position

Historical router note: the live SOTA / publishability ordering now
lives in [`paper/priority.md`](paper/priority.md) and
[`paper/publishability-status.md`](paper/publishability-status.md).
The detail below is preserved as background on how the project got
here; do not treat it as the active execution queue.

The scientific target is not merely to reproduce the imported whitepaper. The
target is to use an honest reproduction base to build **one results paper,
co-authored with Sam, that advances SOTA with measured big-number speedups.**
Method work serves that scientific goal and may land in an appendix; it is
not a standalone methods paper. See the round-17 reframe in
`paper/publishability-status.md` and `paper/claim-matrix.md`.

Current position relative to the adjacent efficiency literature tracked in
[docs/literature-map-2026-04-16.md](docs/literature-map-2026-04-16.md)
(post-CodecSight map; supersedes the earlier
[docs/literature-map.md](docs/literature-map.md) which remains as
historical context). See also
[docs/research-strategy-post-codecsight.md](docs/research-strategy-post-codecsight.md)
and [docs/benchmark-taxonomy.md](docs/benchmark-taxonomy.md) and
[docs/related-work-table.md](docs/related-work-table.md) for paper
framing:

- we now have real benchmark-native semantic evidence, which is necessary but
  not sufficient for a competitive systems or efficiency paper
- we do not yet have Track B skipped-compute evidence, so we are not yet
  competitive on latency, throughput, or memory claims against FastV, ToMe,
  CoPE-VideoLM, CodecSight, or related pruning and compressed-domain methods
- on quality, the current local benchmark agreement range (`0.833` to `0.870`)
  is scientifically useful but still weaker than the low-drop quality stories
  reported by stronger efficiency papers
- **first locally-measured Track A Pareto-dominant frontier (DEV ONLY)**:
  on the TOMATO motion dev slice (phase 1.10, 30-policy grid sweep),
  `7` of `30` cached policies reach `cached_accuracy >= 0.400` at lower
  effective-fresh-frames budgets than dense-6's 6 frames. The lowest-budget
  frontier point is `max_abs(8.0, 32.0) static+shifted age=4` at cached
  `0.400` and fresh budget `3.99`, representing `~33%` fresh-vision-token
  reduction vs dense-6 at equal accuracy. Note: the total Pareto-candidate
  count of `25/30` mixes genuine frontier points with lower-accuracy
  non-dominated policies that qualify only because the dense curve is weak
  on this slice (dense-2 through dense-4 all sit at `0.267`). The
  paper-citable signal is the `0.400`-accuracy frontier, not the raw count.
  N=15, Wilson 95% CI wide, point estimate only; holdout validation in
  phase 1.12 is the discipline gate.
- **UPDATED 2026-04-16: MVBench motion holdout has a STRONG EARLY
  SIGNAL** (phase 1.12.B, N=15 transfer-discovered single-shot).
  `max_abs(8,32) static+shifted age=4` reaches cached=0.667, fresh=4.59,
  agreement=0.933 on MVBench motion holdout — strict Pareto win vs
  dense-6 (0.667 @ 6 frames = 77% budget at equal accuracy).
  **Not paper-grade SOTA**; caveats:
  - N=15, Wilson CI [0.41, 0.85]
  - single-shot; holdout test was a transfer-discovered follow-up,
    not a benchmark-blind holdout — the policy was chosen on TOMATO
    dev but selection was informed by MVBench dev via phase 1.16
  - dirty-tree artifacts
  - Track B compute measurement is NOT built; "speedup" claims are
    not yet supported
  - Phase 1.21 N=30 enlargement is the next hardening gate. See
    `docs/research-strategy-post-codecsight.md` for ordering.
- Phase 1.11 MVBench dev sweep completed at 30/30; the primary dev
  winners failed phase 1.12 holdout; the current live winner is the
  transfer-discovered age=4 variant described above (the original
  phase 1.11 grid had a hole at this threshold × age combination).
- the current best path toward a competitive paper is therefore:
  - finish honest whitepaper reproduction on this stack
  - isolate when the planner fails
  - use that diagnosis to build a stronger training-free planner before making
    Track B claims
  - keep reproduction bounded once the control tranche is complete, so later
    benchmark effort goes into policy improvement rather than repeated slice
    archaeology
- immediate next method loop from the new evidence:
  - keep bounded token age in the search space, but stop treating it as the
    only active lever before combined-axis testing lands
  - use dense feature replay to expand policy search without paying redundant
    dense vision encodes on every rerun
  - add matched dense frame-budget baselines so policy gains are compared
    against equally expensive dense alternatives
  - add dense answer-margin logging so confidence-limited items can be
    separated from staleness-limited ones; these are repo-local operational
    labels, not a standard external taxonomy yet
  - revisit planner statistics through calibrated grids rather than one-point
    probes
  - treat FastV composition as an explicit later baseline/composition step, but
    assume adaptation or partial reimplementation on the Qwen/Gemma/MLX stack
    rather than a plug-and-play import from the published LLaVA codebase

## Evidence And Trust Model

Use these levels consistently.

Highest trust:

- primary papers and official docs listed in [docs/literature-map-2026-04-16.md](docs/literature-map-2026-04-16.md) (current) and [docs/literature-map.md](docs/literature-map.md) (pre-CodecSight, historical)
- checked-in code under `src/`
- raw saved result artifacts that we inspected directly

Medium trust:

- imported reference scripts under `seed/original_repo/`
- imported ChatGPT seed artifacts under `seed/chatgpt/`
- imported result files whose schema and headline claims we inspected directly

Lower trust:

- synthesized KB notes
- mission files and planning prompts
- future-work memos and backlogs

Special trust tier:

- imported results that are not locally reproducible on this machine due to
  memory or runtime constraints remain external evidence even if checked in here

Rules:

- every important claim should say whether it is `reproduced here`,
  `imported result`, or `hypothesis`
- KB summaries can set priorities, but they do not replace raw artifacts
- future-work memos are framing input, not proof

## What We Are Carrying Forward

Strong enough to guide the next phase:

- same-position reuse is the default temporal baseline
- pixel differencing is the best current semantic-validation planner baseline
- packet metadata and keyframe detection are promising cheap routing signals
- Q-table flatness is useful as a binary pre-filter, not a saliency oracle
- architecture-specific checkpoints matter for any later sparse-execution path
- the current pixel-diff planner is an RGB proxy for a deeper production hypothesis about codec motion and residual signals

Strong enough to preserve as cautions:

- Qwen-style hybrids should not inherit generic early-prune folklore without direct validation
- B/P-frame analysis should log GOP position, not just aggregate frame type
- exact per-macroblock bit-count recovery is not an early milestone
- composed compression or speedup claims stay gated until measured on the same stack

## What We Are Deprioritizing

These are not mathematically impossible. They are simply poor early bets.

- embedding relocation as the primary temporal path
- DCT-bypass as a near-term systems win
- continuous H.264 spatial scoring as a main saliency path
- provenance-aware KV allocation as an early milestone
- aggressive composed speedup or compression arithmetic before local measurements

## Adoption Map

### Rewrite Into `src/`

Use clean rewrites, not direct prototype imports:

- strict answer parsing
- frame count and packet probing
- frame extraction helpers
- temporal block classification
- frame-level routing helpers
- Q-table pre-filter core

### Keep As Reference Only

Preserve under `seed/`, but do not treat as working code:

- `run_tomato_mlx.py`
- `codec_pipeline.py`
- `exp_wall_clock_speedup.py`
- `exp_vit_attention_baseline.py`
- `exp_per_block_mv_lookup.py`
- `qtable_prefilter.py`
- selected result JSON files and external review memos

### Do Not Port As Working Code

- `run_gemma4_validation.py` because of the leaked token and poor hygiene
- mission files as executable workflow
- synthesized KB or review text as if it were measured evidence

## Explicit Experiment Tracks

Every experiment belongs to one track.

### Track A: Semantic Substitution

Purpose:

- prove that cached or mixed visual features preserve downstream behavior

Characteristics:

- dense vision encode may still happen
- feature substitution after encode is allowed
- agreement and accuracy are the primary metrics

### Track B: Sparse Execution

Purpose:

- prove real work is skipped in decode, vision, attention, or prefill

Characteristics:

- timing must separate decode, preprocessing, routing, vision, prefill, and generation
- analytic speedup models are projections only
- wall-clock and memory evidence are required

No result should blur these tracks.

## Knowledge-Maintenance Contract

Every decision-worthy experiment must:

- start as a preregistered note under `research/experiments/<year>/`
- state success, rejection, and inconclusive bands before the run
- link raw artifacts instead of hiding them
- update [research/decision-log.md](research/decision-log.md) if a hypothesis changes status
- update [paper/framing.md](paper/framing.md) if the claim boundary changes

## Phase Order

### Phase 0: Repo Hygiene And Integration

Objective:

- keep the repo reviewable, explicit, and fail-closed

Tasks:

- add canonical agent guidance and knowledge-base routing
- clean utility behavior that silently hides bugs
- normalize setup around `uv`, not the current machine's global state
- preserve imported provenance while keeping it out of the source-of-truth path

Exit criteria:

- repo intent is obvious from `README.md`
- methodology and experiment-note workflow are explicit
- fail-closed utility behavior is in place

### Phase 0.5: Feasibility And Determinism

Status:

- completed locally on 2026-04-13
- note: [2026-04-13-phase-0_5-feasibility.md](research/experiments/2026/2026-04-13-phase-0_5-feasibility.md)

Objective:

- prove that the local MLX-VLM path can support Track A work cleanly

Hypothesis:

- Qwen2.5-VL-3B on this machine exposes enough cached-feature functionality for a reliable local Track A bring-up

Tasks:

- verify the local Track A contract via an explicit API DAG
- run repeated dense baselines on the same fixed inputs
- record determinism or non-determinism before interpreting any agreement result

Primary metrics:

- repeated dense-baseline identity
- interface-step pass/fail status
- parseable outputs

Acceptance band:

- exact output-string identity across the preregistered repeated dense runs
- required API DAG steps succeed up to the intended Track A contract

Rejection band:

- interface is unavailable or too unstable to support Track A work

### Phase 0.75: Cache-Path Identity Control

Status:

- completed locally on 2026-04-13
- note: [2026-04-13-phase-0_75-cache-identity.md](research/experiments/2026/2026-04-13-phase-0_75-cache-identity.md)

Objective:

- prove that the cached-feature path itself is not introducing semantic drift

Hypothesis:

- routing unchanged dense features back through the cache interface preserves
  outputs exactly, and deliberate perturbation proves that the path is live

Tasks:

- compare direct dense generation with dense-through-cache generation
- inject a small deliberate feature perturbation to verify that the cache path
  is active
- keep the same clip ids, prompts, and sampling mode as the preregistered note

Primary metrics:

- exact output-string identity for direct dense versus dense-through-cache
- path-liveness evidence from the deliberate perturbation control

Acceptance band:

- direct dense and dense-through-cache are exactly identical
- the deliberate perturbation changes at least one response or intermediate
  feature comparison

Rejection band:

- unchanged dense features routed through the cache path already diverge

### Phase 1.0: Measure Local Redundancy Before Caching

Status:

- completed locally on 2026-04-13
- note: [2026-04-13-phase-1_0-local-redundancy.md](research/experiments/2026/2026-04-13-phase-1_0-local-redundancy.md)

Objective:

- quantify how redundant the local clip buckets actually are before interpreting caching outcomes

Hypothesis:

- the local buckets will span meaningfully different static, shifted, and novel ratios

Tasks:

- measure static, shifted, and novel ratios on the primary local corpus
- report pad-masked reuse ratios when padding exists
- keep contiguous-window sampling separate from uniform-global sampling
- report the ratios before any semantic-substitution comparison
- keep the pixel-diff formulation explicit so later codec-side replacements are comparable

Primary metrics:

- static ratio
- shifted ratio
- novel ratio

### Phase 1: Reproduce Semantic Substitution Cheaply

Objective:

- confirm the reuse-is-safe story on local Apple hardware

Hypothesis:

- conservative same-position reuse preserves answers on a small temporal subset

Tasks:

- keep the Track A contract explicit as nested claims:
  - `A-interface`: cache-path identity already holds
  - `A-static`: conservative low-delta reuse preserves outputs
  - `A-shifted`: low-delta plus mid-delta reuse stays within tolerance
- run local MLX-VLM baselines on the scored synthetic suite first
- use the versioned prompt bank instead of ad hoc questions
- compare dense versus cached outputs under `contiguous_window` sampling first
- log parse failures explicitly
- initial local pilot completed on 2026-04-13:
  - dense, `STATIC`-only, and `STATIC+SHIFTED` matched exactly on all `12` scored synthetic items
  - dense baseline accuracy was `10/12`, and the current suite did not yet include divergence-capable or natural-video scored items
  - treat this as substrate evidence, not as reproduction of the whitepaper's end-to-end quality claim
  - note: [2026-04-13-track-a-local-pilot.md](research/experiments/2026/2026-04-13-track-a-local-pilot.md)
- repaired local v2 pilot completed on 2026-04-13:
  - dense accuracy was `12/12`, while both cached conditions dropped one
    middle-dependent OCR item
  - the failure occurred despite very high clip-wide reuse, which strengthens
    the case for critical-span reporting
  - note: [2026-04-13-track-a-local-pilot-v2.md](research/experiments/2026/2026-04-13-track-a-local-pilot-v2.md)
- temporal-necessity ablation completed on 2026-04-13:
  - two apparent middle-required v2 passes survive without the middle frames
  - the current discrimination-safe subset is `syn2_mid_color_ever_green` plus
    `syn2_mid_text_ever_bravo`
  - metadata for several endpoint-solvable items was corrected immediately
    after the run
  - note: [2026-04-13-phase-1_05-temporal-necessity-ablation.md](research/experiments/2026/2026-04-13-phase-1_05-temporal-necessity-ablation.md)
- repair the synthetic suite before treating it as a strong semantic benchmark:
  - fix weak items whose wording overclaims what is actually visible
  - add temporal-necessity items where middle frames matter and endpoints are insufficient
  - add critical-span metadata so reuse on semantically important pairs is measured explicitly
- reproduce the direct mechanism section locally before claiming the foundation is complete:
  - exact feature identity on repeated image encodes
  - partial-change locality
  - localized-motion similarity
- repair the current mechanism probes before treating weaker local numbers as a
  real disagreement with the imported whitepaper
- add scored natural-video items before broad threshold sweeps
- scored real-video bring-up completed on 2026-04-13:
  - the first middle-event draft was inconclusive and forced a prompt-bank
    rewrite
  - the endpoint-oriented successor slice on the predecessor cross-check clips
    achieved `6/6` dense and `6/6` cached accuracy on Qwen 3B
  - note: [2026-04-13-phase-1_3-crosscheck-real-video-slice.md](research/experiments/2026/2026-04-13-phase-1_3-crosscheck-real-video-slice.md)
- benchmark-native bring-up completed on 2026-04-13 and 2026-04-14:
  - TOMATO subset is online but weaker than the imported story
  - MVBench hosted subset is supportive but materially weaker than the imported
    `1.000` agreement headline
  - parser and contrast diagnostics show that the local disagreement is real on
    the saved slices and that the predecessor `100%` agreement headline should
    be treated as parser-permissive external evidence rather than a strict
    local target
  - notes:
    [2026-04-13-phase-1_4-tomato-benchmark-subset.md](research/experiments/2026/2026-04-13-phase-1_4-tomato-benchmark-subset.md),
    [2026-04-13-phase-1_5-mvbench-benchmark-subset.md](research/experiments/2026/2026-04-13-phase-1_5-mvbench-benchmark-subset.md),
    and
    [2026-04-14-phase-1_45-benchmark-diagnostics.md](research/experiments/2026/2026-04-14-phase-1_45-benchmark-diagnostics.md)
- immediate benchmark follow-up order:
  - extend the targeted TOMATO diagnosis beyond the current `direction` subset
    to see whether the same refresh-sensitive recovery pattern holds elsewhere
  - extend natural-video scoring beyond endpoint scene facts
  - only then decide whether larger TOMATO or MVBench reruns are the best next
    use of local runtime budget
- run threshold triples: low-reuse `(1.5, 4)`, default `(3, 8)`, high-reuse
  `(5, 12)` on the discrimination-safe subset and then on natural-video items
- sweep refresh intervals to test cache drift directly after the benchmark-path
  identity and pad-masked controls land
- keep open-ended prompts qualitative only; use multiple-choice prompts for the
  primary statistics

Primary metrics:

- agreement
- accuracy delta
- reuse ratio
- kappa when the task format permits it

Acceptance band:

- accuracy stays within the preregistered tolerance
- agreement remains high enough to justify further systems work

Rejection band:

- quality drops materially even under conservative thresholds

Important outputs:

- bucketed failures by OCR, color, small-object, egomotion, and screen-like content
- refresh-interval versus drift evidence
- explicit prompt-bank version and sampling mode on every run
- any machine-specific execution constraint, such as the current need to chunk the Qwen synthetic pilot on this M3 Air to avoid Metal GPU timeouts

### Phase 1.05: Temporal-Necessity Ablation

Status:

- completed locally on 2026-04-13
- note: [2026-04-13-phase-1_05-temporal-necessity-ablation.md](research/experiments/2026/2026-04-13-phase-1_05-temporal-necessity-ablation.md)

Objective:

- separate genuinely discriminating temporal items from prompt-prior or
  endpoint-solvable items before interpreting threshold sweeps

Outcome:

- two middle-required v2 items remain discrimination-safe
- two other apparent middle-required passes are contaminated and should not be
  used as primary sweep targets without rewrite

### Phase 1.1: Direct Mechanism Reproduction

Status:

- completed locally on 2026-04-13
- note: [2026-04-13-phase-1_1-direct-mechanism-reproduction.md](research/experiments/2026/2026-04-13-phase-1_1-direct-mechanism-reproduction.md)

Objective:

- directly test the mechanistic feature-space claims that the whitepaper uses
  to justify Track A reuse

Outcome:

- exact repeated-image feature identity is reproduced locally
- partial-change locality and localized-shift similarity reproduce only
  qualitatively, not yet at the imported whitepaper strength

### Phase 1.15: Mechanism Probe Repair

Status:

- completed locally on 2026-04-13
- note: [2026-04-13-phase-1_15-mechanism-probe-repair.md](research/experiments/2026/2026-04-13-phase-1_15-mechanism-probe-repair.md)

Objective:

- separate probe-design artifacts from real stack-specific weakness in the
  direct mechanism reproductions

Outcome:

- repaired within-block shifts no longer show the earlier catastrophic
  non-monotonic collapse
- repaired probes still remain weaker than the imported whitepaper-strength
  locality and shift bands on the local MLX `4-bit` path
- the next discriminating follow-up is a precision/runtime comparison, not more
  synthetic-probe tweaking

### Phase 1.2: Track A Harness Stability

Status:

- completed locally on 2026-04-13
- note: [2026-04-13-phase-1_2-track-a-harness-stability.md](research/experiments/2026/2026-04-13-phase-1_2-track-a-harness-stability.md)

Objective:

- determine whether the local Qwen Track A harness can run the full v2 suite in
  a stable long-lived single process on this M3 Air

Outcome:

- direct `.venv/bin/python3` invocation is not currently stable on the MLX
  Metal path here
- `gc.collect()` plus `mx.clear_cache()` improved the smaller single-process
  chunk case but did not stabilize a full `12`-item long-lived run
- chunked subprocess execution remains the adopted Track A semantic operating
  rule
- cooperative stop-file termination plus checkpointed partial results now exist
  so long semantic runs do not need force termination

### Phase 2: Systems Baseline And Honest Timing

Objective:

- find where latency actually goes on the target machine

Hypothesis:

- for the non-generation part of the pipeline, decode, preprocessing, and dense
  vision dominate before planner cost does

Tasks:

- build a clean timing harness
- add an in-memory decode path for timing-sensitive runs
- separate decode, frame extraction, routing, vision, prefill, and generation
- use short constrained outputs so generation does not hide earlier savings
- measure cold, warm, and after-idle behavior when relevant

Primary metrics:

- TTFT
- total latency
- peak memory
- planner overhead

Acceptance band:

- harness can reproduce paired timing runs with stable warm results

Rejection band:

- timing noise or harness overhead dominates enough that Track B claims are not interpretable

### Phase 3: Decoder-Side Routing And Scheduling

Objective:

- reduce work before full visual encoding

Hypotheses:

- tiny non-I frames can often be routed as trivially static
- frame scheduling may outperform token tricks first on constrained hardware

Tasks:

- packet-size and keyframe routing
- low-resolution and luma-first baselines
- mixed-resolution global-plus-ROI baselines
- dynamic frame scheduling around novelty bursts and GOP position

Guardrails:

- use simple metadata first
- do not require exact per-block bit accounting
- record frame type and GOP position
- validate MV semantics before trusting per-block experiments
- keep `uniform_global` sampling as comparability mode, not the default
  codec-like mechanism path

Primary metrics:

- selected-frame count
- agreement and kappa
- TTFT
- total latency

### Phase 4: Sparse Visual Execution

Objective:

- move the savings into actual model compute

Hypothesis:

- changed-window recompute is the lowest-risk path to real speedup

Tasks:

- prototype changed-window or changed-region recompute contracts
- keep model-specific geometry explicit
- verify Qwen full-attention checkpoints locally before depending on merge claims
- include Gemma as the early cross-family check once the Qwen path is burned in

Guardrails:

- do not assume early-layer pruning transfers across architectures
- do not inherit imported `layer 23` merge claims as if reproduced here

Primary metrics:

- measured vision-side speedup
- quality delta
- memory delta

### Phase 5: Dynamic Attention And Memory Policies

Objective:

- test whether changed tokens should become the active working set

Status:

- hypothesis only

Hypothesis:

- static tokens can behave more like memory while changed tokens carry most of the global query burden

Tasks:

- simulate changed-query attention schedules
- test summary-bank or memory-bank variants
- only attempt runtime implementation after simulation and earlier phases justify it

Primary metrics:

- interaction counts
- measured latency if implemented
- answer drift on motion-sensitive tasks

### Phase 6: Egomotion, Multi-Reference, And Stabilization

Objective:

- recover reuse on mobile and egocentric video without reviving dead relocation ideas

Hypothesis:

- pixel-space stabilization plus same-position reuse is more promising than token relocation

Tasks:

- global stabilization before caching
- multi-reference cache experiments
- residual-gated reuse after stabilization
- optional IMU-assisted variants only after basic stabilization works

Primary metrics:

- reuse ratio on FPV or mobile clips
- agreement and kappa
- failure-bucket analysis

### Phase 7: Task-Aware Spatial Policies

Objective:

- use codec truths beyond simple motion

Hypotheses:

- Q-table and flatness signals help as pre-filters
- luma, chroma, and resolution policies should depend on task class
- screen content wants a separate path

Tasks:

- Q-table binary pre-filter experiments
- luma/chroma task-policy sweeps
- low-res plus ROI refinement
- dedicated screen-content bucket

Primary metrics:

- task-conditioned quality deltas
- latency deltas
- failure concentration by task family

Predicted failure ordering:

- OCR
- small-object localization
- color fidelity
- egomotion

## Measurement Contract

Every serious benchmark requires:

- a hypothesis
- a track label
- a primary metric
- a comparison point
- a preregistered success/rejection band
- raw sample retention
- exact model, clip, prompt, and commit metadata
- preprocessing and sampling metadata

Required reporting:

- baseline accuracy, modified-path accuracy, agreement, and kappa when possible
- cold versus warm behavior when relevant
- p50 and p95, plus p99 when sample sizes support it
- quality metrics and systems metrics reported separately
- decode and temp-I/O separated from model timing when possible

Negative results must record:

- what was expected
- what was observed
- what hypothesis got weaker
- what next test follows logically

See:

- [docs/methodology/performance.md](docs/methodology/performance.md)
- [docs/methodology/preprocessing.md](docs/methodology/preprocessing.md)
- [docs/methodology/timing-harness.md](docs/methodology/timing-harness.md)

## Local Hardware Plan

Target machine:

- Apple M3 MacBook Air
- 16 GB unified memory

Implications:

- prefer MLX-VLM for local Track A and early Track B work
- iterate on Qwen2.5-VL-3B first
- use Gemma 4 E4B as the second model, with per-family evaluation bands
- freeze Gemma E4B at a `280` visual-token budget for the initial pilot unless
  a preregistration explicitly overrides it
- use Qwen2.5-VL-7B selectively for confirmation
- treat full 7B benchmark reproductions that do not fit in memory as partial reproductions, not full replications
- treat generalized reproduction as the default benchmark standard on this
  machine unless a stricter rerun becomes feasible elsewhere

## Immediate Backlog

Near-term order:

1. keep the protocol split explicit in every paper-facing doc:
   sparse-sampled QA uses pixel diff by design, native-rate streaming uses
   codec metadata by design, and after-ingest follow-up is a separate reuse
   regime again
2. treat phase 1.29 as semantically closed on the local slices we ran:
   planner-substitution evidence is landed and calibration-mode/source
   ablations are neutral; the remaining bridge is decoder-integrated
   streaming/native-rate systems evidence
3. treat phase 1.30W as the mechanistic reference point and phase 1.30X as
   the new routing reference point: dense Q0 solves the first-query leg
   exactly, and a simple duration-gated admission policy already reopens the
   speed/accuracy rescue band
4. do not spend more time on blind global 1.30 reruns or same-protocol
   follow-up-only tweaks: phase 1.30X shows the live gap is now format
   hygiene in two remaining long sessions (`783-2`, `847-3`). Reopen 1.30
   only with a targeted fix for those failures or a third endpoint family
5. treat phase 1.55D v2 selective re-prefill as an active, landed fixed-policy
   frontier: K=4/K=2/K=1 now all run end-to-end with exact paired recovery, so
   the next useful move is adaptive refresh policy rather than waiting on the
   old co-slicing blocker or running another blind fixed-K sweep
6. treat phase 1.58 bf16 KV control as the cleanest mechanism discriminator for
   the persistent-KV basin, but keep it blocked on this 16 GB / ~10 GB-RSS
   laptop plan even if the checkpoint appears; it only reopens on a deliberate
   higher-memory exception or different hardware
7. keep Track B sparse-path work separate: semantic-substitution rows are not
   speed claims until the backend itself skips measured work
8. keep scroll/pan work off VideoMME: phase 1.60 closed that corpus as the
   wrong regime, so future work needs EgoSchema, Ego4D, EPIC-Kitchens, or a
   labeled synthetic set

## Future Horizons

Keep these visible, but clearly outside the current evidence boundary:

- robustness against novelty amplification or compute-denial inputs
- screen-content specialization as a major branch
- machine-oriented codec sidecars
- feature-compression and machine-first media standards as adjacent framing
- sensor-fusion timelines or world-state codecs
- AI-native codecs and hardware co-design

These are paper-story or long-range-program ideas until local evidence lands.

## Open Questions

- does the local MLX-VLM path expose a stable enough cached-feature interface for Track A work?
- how much of the imported temporal gain survives once decode and file-I/O are measured honestly on this laptop?
- do Qwen-specific reuse results generalize at all to Gemma-scale VLMs?
- which failure classes dominate first: OCR, small objects, color, egomotion, or screen content?
- which MV path preserves correct B-frame semantics without blowing up implementation complexity?
- after routing and sparse execution, is changed-query attention still worth the engineering cost?

## Review Requests

The next review pass should focus on:

- whether the phase order is still the highest-signal path for a 16 GB Air
- whether the `deprioritized` list is scoped correctly
- whether Track A and Track B stay cleanly separated in code and docs
- whether the preregistration and timing-harness rules are strong enough for paper-grade evidence
- whether the future-horizon section is ambitious enough without pretending to be current evidence
