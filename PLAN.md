# Research Plan

Last updated: 2026-04-13

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

That is the center of the project today.

## Evidence And Trust Model

Use these levels consistently.

Highest trust:

- primary papers and official docs listed in [docs/literature-map.md](docs/literature-map.md)
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
- run threshold triples: aggressive `(1.5, 4)`, default `(3, 8)`, conservative `(5, 12)`
- sweep refresh intervals to test cache drift directly
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

## Immediate Backlog

Near-term order:

1. finish Phase 0 hygiene fixes and documentation
2. run Phase 0.5 feasibility and determinism checks
3. run Phase 0.75 cache-path identity control
4. fetch the primary Xiph corpus and generate the synthetic local stress corpus
5. measure local redundancy on the initial clip buckets
6. reproduce a small Track A semantic-substitution slice locally
7. build the clean timing harness
6. test packet-size and keyframe routing
7. design changed-window sparse execution against the verified model geometry

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
