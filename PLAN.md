# Research Plan

Last updated: 2026-04-13

## Charter

Build a rigorous research program around codec-conditioned dynamic compute for video VLMs.

Primary objective:

- determine which cheap temporal and codec-derived signals can reduce video VLM work on Apple Silicon without unacceptable answer drift

Secondary objectives:

- keep a clean boundary between semantic validation and true systems speedup
- preserve negative results so we stop repeating dead ideas
- create a repo that other agents can review and extend without inheriting prototype drift

Non-goals for the current phase:

- large-scale training
- paper-ready grand compression stackups
- architecture changes without local evidence

## Current Verified Position

The imported whitepaper and original repo justify a narrow but strong starting claim:

- video VLM outputs can tolerate substantial temporal embedding reuse

The original repo also makes the main missing proof point explicit:

- dense post-encoder substitution is a quality benchmark
- it is not yet proof of sparse visual execution

That distinction is the center of this plan.

See:

- [docs/original-repo-audit.md](docs/original-repo-audit.md)
- [docs/external-feedback-validation.md](docs/external-feedback-validation.md)
- [docs/knowledge-base-notes.md](docs/knowledge-base-notes.md)

## Evidence And Trust Model

Use these trust levels consistently.

Highest trust:

- primary papers and official docs in [docs/literature-map.md](docs/literature-map.md)
- checked-in code under `src/`
- raw saved result artifacts that we inspected directly

Medium trust:

- imported reference scripts under `seed/original_repo/`
- imported ChatGPT seed artifacts under `seed/chatgpt/`
- the original repo's benchmark outputs and mechanism experiments

Lower trust:

- `fleet-kb` synthesized findings
- `missions/*.toml` plans and agent prompts
- speculative extrapolations from seed material

Rules:

- missions generate hypotheses, not conclusions
- KB summaries can set priorities, but they do not replace raw artifacts
- every future claim in this repo should say whether it is a reproduced result, an imported result, or a hypothesis

## What We Are Carrying Forward

From the original repo, these ideas are strong enough to guide the next phase:

- same-position temporal caching is the default baseline
- pixel differencing is the best current semantic-validation planner baseline
- frame packet metadata and keyframe detection are promising cheap routing signals
- Q-table and flatness signals are useful as binary spatial pre-filters
- architecture-specific attention checkpoints matter for any later sparse execution path

From the original repo and KB, these cautions are also strong enough to preserve:

- Qwen-style windowed/full-attention hybrids should not inherit FastV-style early-prune assumptions without direct validation
- B-frame reuse analysis should log GOP position, not just aggregate frame type
- exact per-macroblock bit-count recovery is not an early milestone
- stacked compression multipliers should stay conservative until each component is independently measured

## What We Are Deprioritizing Or Treating As Killed

These are not banned forever, but they should not lead the next round of work.

- embedding relocation as a primary temporal path
- DCT-bypass as a near-term systems win
- continuous H.264 spatial scoring as a main saliency path
- provenance-aware KV allocation as an early milestone
- aggressive composed speedup/compression arithmetic before local measurements

Reasoning:

- relocation was mostly negative in the original repo
- DCT and fine-grained bit-allocation ideas consumed substantial effort for weak evidence
- spatial codec signals look more useful as uncertainty or pre-filter signals than as saliency oracles

## Adoption Map

### Rewrite Into `src/`

Use clean rewrites, not direct prototype imports:

- frame count probing, packet probing, and frame extraction
- temporal block classification
- frame-level early-exit routing
- strict benchmark answer parsing that fails closed
- the Q-table pre-filter core with fallback behavior

### Keep As Reference Only

Imported under `seed/original_repo/`:

- `run_tomato_mlx.py`
- `codec_pipeline.py`
- `exp_wall_clock_speedup.py`
- `exp_vit_attention_baseline.py`
- `exp_per_block_mv_lookup.py`
- `qtable_prefilter.py`
- selected benchmark and analysis result JSON files

### Do Not Port As Working Code

- `run_gemma4_validation.py` because it contains a leaked token and poor hygiene
- mission files as executable workflow
- fleet KB as a source of truth

## Explicit Experiment Tracks

Every experiment belongs to one of these tracks.

### Track A: Semantic Substitution

Purpose:

- prove that cached or mixed visual features preserve downstream behavior

Characteristics:

- dense vision encode may still happen
- feature substitution after encode is allowed
- quality agreement is the primary metric

### Track B: Sparse Execution

Purpose:

- prove real compute savings inside decode, vision, attention, or prefill

Characteristics:

- timing must distinguish decode, preprocessing, planner, vision, prefill, and generation
- analytic speedup models are allowed only as projections, never as primary evidence
- wall-clock and memory evidence are required

No result should blur these tracks.

## Phase Order

### Phase 0: Repo Hygiene And Integration

Objective:

- make the repo safe, reviewable, and reusable

Tasks:

- remove all leftover seed references that should not survive in final docs
- import selected original-repo references under `seed/original_repo/`
- keep external ChatGPT reviews under `seed/chatgpt/reviews/`
- create clean reusable utilities in `src/`
- record the original repo audit, mapping, and KB notes in `docs/`

Exit criteria:

- repo intent is obvious from `README.md`
- imported material is partitioned by trust level
- no benchmark hygiene bug is intentionally copied forward

### Phase 1: Reproduce Semantic Substitution Cheaply

Objective:

- confirm the reuse-is-safe story on local Apple hardware

Hypothesis:

- conservative same-position reuse preserves answers on a small TOMATO slice and curated clips

Tasks:

- run local MLX-VLM baselines on a small subset
- compare dense versus cached-answer outputs
- log parse failures explicitly instead of defaulting to option A
- sweep refresh intervals conservatively

Primary metrics:

- answer agreement
- accuracy delta
- reuse ratio

Falsifiers:

- cached answers diverge materially on temporal ordering, OCR, color, or egomotion clips

### Phase 2: Systems Baseline And Honest Timing

Objective:

- find where latency actually goes on the target machine

Hypothesis:

- temp I/O, decode, and dense vision dominate before planner overhead does

Tasks:

- build a clean timing harness around the rewritten utilities
- report decode, preprocess, planner, feature mixing, vision, prefill, and generation separately
- keep semantic-substitution timing separate from sparse-execution projections

Primary metrics:

- TTFT
- total latency
- peak memory
- planner overhead

Falsifiers:

- if planner overhead dominates on the laptop, codec routing is less attractive than expected

### Phase 3: Decoder-Side Routing And Scheduling

Objective:

- reduce work before full visual encoding

Hypotheses:

- tiny non-I frames can often be routed as trivially static
- frame scheduling can save more than token tricks on constrained hardware

Tasks:

- packet-size/keyframe routing
- low-resolution and luma-first baselines
- mixed-resolution global-plus-ROI baselines
- dynamic frame scheduling around novelty bursts and GOP position

Guardrails:

- prefer skip/non-skip or packet-scale metadata first
- do not pursue exact per-MB bit counts as a prerequisite
- log GOP position for B/P frames
- validate MV sign and reference-frame semantics before trusting per-block lookup experiments

Primary metrics:

- selected-frame count
- answer agreement
- TTFT
- total latency

### Phase 4: Sparse Visual Execution

Objective:

- move wins into actual model compute

Hypothesis:

- changed-window recompute is the lowest-risk path to real savings

Tasks:

- prototype changed-window or changed-region recompute contracts
- keep Qwen-specific layer boundaries explicit
- validate whether any useful merge/prune point exists for the target model family

Guardrails:

- do not assume early-layer pruning transfers across architectures
- for Qwen-like stacks, verify global-attention checkpoints before any pruning claim

Primary metrics:

- measured vision-side speedup
- quality delta
- memory delta

### Phase 5: Dynamic Attention And Memory Policies

Objective:

- test whether changed tokens should become the active working set

Status:

- this is a hypothesis, not a repo-validated result

Hypothesis:

- static tokens can behave more like memory while changed tokens carry the global query burden

Tasks:

- simulate changed-query attention schedules
- test summary-bank or memory-bank variants
- only attempt runtime implementation after simulation shows clear value

Primary metrics:

- attention interaction counts
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

Primary metrics:

- reuse ratio on FPV or mobile clips
- answer agreement
- failure bucket analysis

### Phase 7: Task-Aware Spatial Policies

Objective:

- use codec truths beyond simple motion

Hypotheses:

- Q-table and flatness signals help as pre-filters
- luma/chroma and resolution decisions should depend on task class
- screen content likely wants a separate path

Tasks:

- Q-table binary pre-filter experiments
- luma/chroma task-policy sweeps
- low-res plus ROI refinement
- screen-content fork for slides, UI, and code

Primary metrics:

- task-conditioned quality deltas
- latency deltas
- failure concentration by task family

## Measurement Contract

This repo treats performance work as science, not anecdotes.

Required for every serious benchmark:

- hypothesis
- primary metric
- unit of analysis
- comparison point
- warmup policy
- raw sample retention
- exact model, prompt, clip, and commit metadata

Required reporting:

- cold versus warm behavior when relevant
- p50, p95, and p99 when sample sizes support them
- quality metrics and systems metrics reported separately
- decode and temp-I/O kept separate from model timing when possible

Negative results must record:

- what was expected
- what was observed
- what hypothesis got weaker
- what next test follows logically

See [docs/methodology/performance.md](docs/methodology/performance.md).

## Local Hardware Plan

Target machine:

- Apple M3 MacBook Air
- 16 GB unified memory

Implications:

- prefer MLX-VLM for main local VLM runs
- iterate on 3B to 4B-class models first
- use 7B confirmation selectively on smaller subsets
- treat large-server timing claims from imported repos as context, not local evidence

See [docs/local-setup.md](docs/local-setup.md).

## Immediate Backlog

Near-term priority order:

1. clean timing baseline with honest phase splits
2. packet-size and keyframe routing
3. semantic substitution reproduction on a small local subset
4. changed-window sparse-execution design
5. stabilization and multi-reference experiments for egomotion
6. Q-table pre-filter and task-aware luma/chroma sweeps

## Open Questions

- which local multimodal models expose enough of the vision path to support sparse execution cleanly?
- which target models have usable late global-attention checkpoints for merge or prune?
- how much of the original repo's temporal gain survives once decode and file-I/O are measured honestly on this laptop?
- do the Qwen-specific conclusions generalize at all to Gemma-scale VLMs?
- which failure classes dominate first: color, OCR, egomotion, or small-object localization?
- which MV extraction path preserves correct B-frame reference semantics without excessive implementation complexity?

## Review Requests

The next review pass should focus on:

- whether the phase order is still the highest-signal path for a 16 GB Air
- whether the killed and deprioritized claims are scoped correctly
- whether Track A and Track B stay cleanly separated in the docs and future code
- whether we are still missing a closer benchmark baseline or stronger sparse-execution comparison
