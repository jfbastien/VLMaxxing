
# Video codec → VLM workplan for an M3 MacBook Air (16GB)

This document is meant to be handed to Codex / Claude as an execution plan.

It assumes the current codebase already includes:

- `codec_through_reference.py`
- `run_codec_through_toy_experiments.py`
- `codec_through_expansions.py`
- `run_codec_through_expansion_experiments.py`

## 1. Goal

Advance the whitepaper's core idea — **reuse visual computation when the video codec says little or nothing changed** — from a quality-validation prototype into a practical, measured video-VLM system.

We want to answer four questions:

1. **Can real codec metadata beat pixel differencing?**
2. **Can we turn reuse into real speedups, not just post-hoc token replacement?**
3. **Which codec ideas beyond temporal redundancy actually help VLMs?**
4. **What works well enough on a constrained Apple-silicon laptop to justify deeper work?**

## 2. High-level hypotheses

### H1. Zero-change reuse is real
The whitepaper result is meaningful: many adjacent video regions can likely reuse visual embeddings without changing answers.

### H2. True speedups require moving the reuse decision *before* or *inside* the vision encoder
Post-encoder token replacement is a quality experiment, not yet a full systems optimization.

### H3. Attention should also be change-aware
If only 1%-10% of tokens are dynamic, attention work should scale with that dynamic set rather than with the full dense token grid.

### H4. Codec theory offers more than motion vectors
Useful signals likely include:
- residual energy
- variable block sizes
- luma/chroma asymmetry
- multiple references / bidirectional prediction
- screen-content tools (palette, intra-copy)
- quality / quantization metadata
- hardware-friendly partitioning

### H5. The best near-term system is hybrid
Best results likely come from:
1. codec-guided reuse / pruning
2. sparse window recompute
3. changed-block-focused attention
4. optional token merging/pruning after that

## 3. Practical constraints: M3 MacBook Air, 16GB unified memory

Design for:
- short clips
- few frames per prompt
- 4-bit models for iteration
- lightweight profiling
- MLX / Apple-native paths first

Do **not** begin with giant benchmarks or 70B-class models.

## 4. Recommended local stack

### Core environment
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip

# Core numerics / plotting
pip install numpy pandas matplotlib pillow scipy scikit-image opencv-python

# Apple stack
pip install mlx mlx-vlm

# Optional but useful
pip install av imageio ffmpeg-python
```

### System packages
```bash
brew install ffmpeg pkg-config
```

### Why this stack
- `mlx` / `mlx-vlm` should be the default inference path.
- `ffmpeg` gives us codec-side experiments, frame extraction, and possibly motion-vector side data.
- `PyAV` is optional; if it works cleanly, use it for side-data access. If not, fall back to FFmpeg CLI + JSON / custom parser.

## 5. Which models to use on this machine

### Iteration model
Use a small 4-bit model first:
- `mlx-community/Qwen2-VL-2B-Instruct-4bit`
- or `mlx-community/Qwen2.5-VL-3B-Instruct-4bit` if memory/latency is acceptable

### Confirmation model
Try a 7B 4-bit model only after the pipeline works:
- `mlx-community/Qwen2.5-VL-7B-Instruct-4bit`

### Policy
- Use 2B/3B for fast iteration.
- Use 7B only for final confirmation runs on small subsets.

## 6. Current evidence already available

### From the original toy experiments
- talking-head and fixed-camera regimes show very high reuse
- FPV/egomotion breaks same-position reuse badly
- local search and coarse motion compensation recover most reuse
- halo/window grouping matters a lot for actual recompute cost
- protected ROI for robotics remains much cheaper than full refresh

### From the expanded design-space toy experiments
- luma-only screening misses **pure chroma changes**
- changed-block-focused attention can reduce theoretical attention work by roughly **an order of magnitude** when dynamic tokens are sparse
- adaptive variable-size partitioning can beat fixed 16×16 tokenization on mixed-detail scenes, but only when the stopping rule is well chosen

## 7. Main research questions

### Q1. Real codec metadata
Can actual codec metadata (motion vectors, residual flags, frame type, block partitioning) produce better reuse plans than pixel differencing?

### Q2. Sparse execution
Can we avoid dense encoder compute, not just overwrite outputs?

### Q3. Attention scheduling
Can changed regions be given full/global attention while static regions are frozen or only updated locally?

### Q4. Luma/chroma policies
For which tasks is luma-first safe?
For which tasks must we preserve full chroma?

### Q5. Resolution / quality / frame count
What matters most for answer quality on a small local model:
- more frames?
- better resolution?
- better chroma fidelity?
- less compression artifact?

### Q6. Screen content
Do palette-like, exact-copy, or intra-copy ideas help on UI / code / slides / desktop video?

### Q7. Multi-reference caching
Does one-hop caching leave too much performance on the table?
Do two-reference or offline bidirectional caches help?

## 8. Content buckets to collect locally

Create a tiny but diverse local dataset of short clips (5-20 seconds each):

1. **Talking head / video call**
2. **Static surveillance / parking lot**
3. **FPV / egomotion / walking**
4. **Sports / dynamic scene**
5. **Screen content / UI / code / slides**
6. **Small-object / OCR / color-sensitive clip**

For each clip, store:
- raw source
- H.264 version
- AV1 version if convenient
- extracted frames
- prompt list
- expected difficulty tag

## 9. Measurement rules

Every experiment should log:

### Accuracy / behavior
- exact answer agreement with baseline
- multiple-choice agreement
- benchmark accuracy delta
- per-task failure notes

### Efficiency
- end-to-end latency
- vision encoder time
- decode / preprocessing time
- peak memory
- token reuse %
- recomputed windows %
- frames per second processed
- prompt throughput if applicable

### Diagnostics
- dynamic token ratio
- same-position reuse %
- motion-compensated reuse %
- attention budget estimate
- refresh interval / drift

## 10. Phase-by-phase execution plan

---

## Phase 0 — Reproduce the current baseline on your laptop

### Objective
Get the current pipeline running locally and confirm that the synthetic results look sane.

### Tasks
1. Run:
```bash
python run_codec_through_toy_experiments.py
python run_codec_through_expansion_experiments.py
```
2. Inspect generated plots and reports.
3. Confirm no obvious Apple-silicon issues.

### Success criteria
- scripts run without major modification
- plots / reports are generated
- local results roughly match the included reports

### Why it matters
Before touching real models or codecs, verify the planner logic and experiment harness.

---

## Phase 1 — Build the real codec-metadata path

### Objective
Replace pixel differencing with actual codec signals wherever possible.

### Build tasks
1. Create `codec_metadata_reader.py` with two backends:
   - **PyAV backend** if side-data is exposed cleanly
   - **FFmpeg CLI backend** otherwise

2. Extract, per frame or block:
   - frame type (I / P / B)
   - motion vectors
   - block size if available
   - residual proxy if available
   - QP / quantization info if exposed
   - reference-frame info if exposed

3. Convert codec blocks to planner labels:
   - `MV=0 + residual≈0 -> STATIC`
   - `MV!=0 + residual≈0 -> SHIFTED`
   - `residual>0 or intra -> NOVEL`

4. Save metadata as compact JSON or NPZ for reuse.

### Experiments
Compare on the same clip:
- pixel-diff planner
- local-search planner
- real codec planner

### Metrics
- reuse ratio
- agreement with pixel-diff labels
- end-to-end planner time
- video decode cost
- error cases

### Key question
Does the codec planner produce **better** or just **cheaper** classification?

### Success criteria
- real metadata extracted for at least H.264 clips
- block labels aligned to patch grid
- planner works without full RGB differencing

---

## Phase 2 — Turn reuse into actual compute savings

### Objective
Implement **window-level sparse recompute** rather than dense encode + overwrite.

### Build tasks
1. Identify where the visual encoder can be intercepted in MLX-VLM or PyTorch.
2. Start with a simulated executor:
   - recompute only selected windows
   - splice cached window outputs
3. If full sparse execution is hard in MLX at first, build a **timing proxy**:
   - dense baseline
   - window-count-based compute estimate
   - later replace estimate with actual sparse path

### Minimum viable implementation
- changed windows + halo
- static windows reused from cache
- optional full refresh every N frames

### Experiments
Run on:
- talking head
- surveillance
- FPV

### Metrics
- wall-clock latency
- estimated vs actual speedup
- quality agreement
- recompute window fraction

### Success criteria
- measurable latency reduction on fixed-camera video
- no obvious quality regressions on local prompts

### Important note
This is the phase where the work stops being “just a clever hook”.

---

## Phase 3 — Make attention change-aware

### Objective
Exploit the change map inside attention, not just encoder recompute.

### Candidate strategies
1. **Changed queries, full context**
   - dynamic tokens attend globally
   - static tokens attend locally or stay frozen

2. **Changed queries + summary tokens**
   - dynamic tokens attend dynamic tokens + a few static summary tokens
   - static regions use local attention only

3. **Freeze static token states**
   - static tokens skip attention updates for some layers
   - refresh only on demand

### Build tasks
Create `attention_scheduler.py`:
- takes reuse mask / dynamic mask
- emits sparse attention plan
- supports summary/sentinel tokens

### Validation
First validate by simulation:
- compare estimated FLOPs / interactions
- verify semantics on easy prompts

Then try a limited real implementation:
- one or two layers only
- or an ablation that masks static queries

### Questions
- Which layers tolerate sparse attention best?
- Do later layers need more global refresh than early layers?
- Is there a small set of always-global summary tokens that stabilizes answers?

### Success criteria
- clear theoretical savings
- at least one partial real implementation that preserves output quality on a small clip set

---

## Phase 4 — Explore codec truths beyond temporal redundancy

### Objective
Test other codec-inspired levers one by one.

### 4A. Luma / chroma asymmetry
Build:
- luma-only screening
- luma+periodic-chroma refresh
- full-chroma path for color / screen-content tasks

Test on:
- motion questions
- color questions
- UI / OCR / charts

Question:
When is chroma safe to downweight, and when is it dangerous?

### 4B. Variable block sizes
Build:
- variance or residual-driven quadtree partitioner
- token-budget-aware stopping rule

Question:
Can we reduce token count by using large blocks in flat regions and small blocks around detail?

### 4C. Multi-reference / offline bidirectional cache
Build:
- previous-frame cache
- previous + older I/P reference cache
- offline bidirectional cache for non-streaming video

Question:
Does multi-reference help egomotion content enough to justify complexity?

### 4D. Screen-content tools
Build heuristics for:
- palette-like low-color regions
- exact-copy within frame
- text/UI detection
- cursor/tool-tip protection

Question:
Can desktop/screen video get much higher compression with specialized logic?

### 4E. Lower resolution / lower quality
Build sweep:
- 224 / 280 / 336 resolution
- fps 0.5 / 1 / 2 / 4
- grayscale or luma-only preprocessing
- different CRF / QP levels

Question:
Which dimension matters most for different tasks:
space, time, or color?

---

## Phase 5 — Task-aware / prompt-aware compression

### Objective
Condition the compression policy on the user’s question.

### Rationale
The best frame / region / color budget depends on what is being asked.

### Build tasks
Create a lightweight task classifier:
- motion
- color
- OCR
- localization
- general description
- screen-content

Use it to choose:
- target resolution
- luma-only allowed?
- chroma refresh interval
- protected ROI rules
- attention strategy

### Example policies
- **Color question**: preserve chroma, protect regions with chroma change.
- **OCR question**: higher resolution, protect text, no aggressive merge around edges.
- **Motion question**: low chroma priority, more temporal frames, motion-aware cache.
- **General captioning**: aggressive compression is acceptable.

### Success criteria
- a policy table that beats any single fixed policy on an averaged score
- at least one case where prompt-awareness clearly helps

---

## Phase 6 — Optional model-modified variants

### Objective
Explore gains that require changing the model or learning a small adaptor.

### Options (ranked)
1. **Learned recache gate**
   - tiny MLP or lightweight predictor
   - inputs: residual energy, motion magnitude, patch stats, previous hidden drift
   - output: refresh / reuse probability

2. **Codec-conditioned token type embedding**
   - append features such as:
     - block type
     - motion magnitude
     - residual energy
     - quantizer level
     - reference distance

3. **Delta encoder for changed blocks**
   - only if zero-change methods plateau

### Keep it small
On this laptop, do not start with expensive full-model fine-tuning.
Prefer:
- frozen backbone
- tiny adaptor
- LoRA-scale modifications
- offline training only after strong zero-training evidence

## 11. Experiment matrix

For each clip bucket, run:

### Baselines
- dense frames, no caching
- uniform frame subsampling

### Reuse baselines
- same-position diff
- local-search diff
- global translation / affine estimate if implemented
- true codec metadata

### Sparse execution
- dense encode + overwrite
- window sparse recompute

### Attention variants
- dense attention
- changed queries full context
- changed queries + summary
- frozen static tokens

### Quality sweeps
- full RGB
- luma-first
- lower resolution
- reduced fps
- CRF / QP sweep

## 12. Validation protocol

### Determinism
- fix decode fps
- fix prompts
- fix sampling / generation temperature
- save frame indices

### Output comparison
For multiple-choice:
- compare exact answer IDs

For free-form:
- compare exact text
- then semantic equivalence manually for mismatches

### Failure buckets
Tag each mismatch as:
- small object missed
- OCR/text failure
- color mistake
- temporal ordering mistake
- egomotion / alignment failure
- hallucination / unstable phrasing

### Human review
Review every failure at least once with frame overlays and novelty masks.

## 13. Suggested small local benchmark

Start with **20 clips × 5 prompts each**.

Prompt categories:
1. scene description
2. object location
3. temporal/motion
4. color/detail
5. OCR/screen content if applicable

This is enough to discover where the method fails before touching TOMATO / MVBench subsets.

## 14. Deliverables Codex / Claude should produce

### Code deliverables
1. `codec_metadata_reader.py`
2. `sparse_window_executor.py`
3. `attention_scheduler.py`
4. `task_policy.py`
5. `benchmark_local_videoqa.py`
6. `analyze_failures.py`

### Reports
1. label-quality comparison report
2. sparse-execution timing report
3. attention strategy ablation report
4. luma/chroma sweep report
5. resolution/fps/quality Pareto report
6. final recommendation memo

## 15. Immediate first tasks for Codex / Claude

### Task 1
Read:
- `codec_through_reference.py`
- `codec_through_expansions.py`
- the two markdown reports

Then summarize:
- what already works
- what is simulated
- what still needs real implementation

### Task 2
Implement real codec metadata extraction on macOS.

### Task 3
Wire the planner into an MLX-VLM local video inference script.

### Task 4
Build a small local benchmark harness over 10-20 short clips.

### Task 5
Produce the first dense-vs-cached-vs-codec-planned comparison report.

## 16. Risks and how to manage them

### Risk 1: motion-vector extraction is annoying
Fallback: use RGB differencing first, but architect the planner so codec metadata can drop in later.

### Risk 2: MLX sparse execution may be hard
Fallback: build timing proxies and a partial PyTorch implementation for correctness.

### Risk 3: quality appears perfect on easy clips but fails on hard ones
Mitigation: include color, OCR, egomotion, and screen-content clips early.

### Risk 4: over-compressing static regions hurts hidden-state drift
Mitigation:
- periodic refresh
- summary tokens
- learned recache gate later

## 17. Ranked ideas by expected payoff

1. real codec metadata planner
2. sparse window recompute
3. changed-block-focused attention
4. task-aware luma/chroma policy
5. multi-reference caching
6. screen-content-specialized logic
7. learned recache gate
8. delta encoder / trained adaptor

## 18. Further work beyond video

### Robotics / VLA
Best near-term translation:
- protect gripper, object, contact zone, receptacle
- reuse background aggressively
- add egomotion / proprioception as alignment priors

Questions:
- which ROIs must always refresh?
- how much can static background be frozen before policy quality drops?
- can action history and visual change maps be coupled?

### Audio
Potential translation:
- cache slowly varying acoustic context
- refresh on onsets, speaker changes, prosody shifts, phoneme boundaries
- use temporal saliency rather than raw energy alone

Questions:
- what is the audio analogue of “STATIC / SHIFTED / NOVEL”?
- are spectral deltas sufficient?
- when does low-energy audio still matter semantically?

### Generative video
Potential translation:
- reuse latent hidden states across denoising steps / chunks
- refresh only high-uncertainty or high-motion regions
- use motion/residual priors in latent space

Questions:
- can motion priors stabilize generation while cutting compute?
- does a delta-token world-model formulation work better than frame-wise RGB modeling?

## 19. Final principle

The work should keep one distinction sharp at all times:

- **Quality validation path**: “Does reuse preserve answers?”
- **Systems path**: “Does reuse avoid actual compute?”

Progress is real only when both answers are good.
