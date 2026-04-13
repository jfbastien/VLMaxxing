# Original Repo Audit

Scope:

- audited `~/s/codec-through-sam/` as predecessor reference material
- treated `experiments/` as implementation source
- treated top-level `*_result.json`, `missions/*.toml`, and `fleet-kb` as supporting material, not source of truth

## Main Findings

### 1. The best benchmark path is semantic substitution, not sparse execution

The strongest benchmark script is the original [`run_tomato_mlx.py`](../seed/original_repo/experiments/run_tomato_mlx.py).

What it does:

- extracts frames
- runs dense vision encoding for all frames
- mixes cached and fresh segments
- passes the mixed features back through `cached_image_features`

What that proves:

- downstream outputs are robust to aggressive feature reuse

What it does not prove:

- real encoder-side compute savings

This distinction must stay explicit in all future writeups and runners.

### 2. The timing harness is useful, but part of the speedup is modeled

The imported [`exp_wall_clock_speedup.py`](../seed/original_repo/experiments/exp_wall_clock_speedup.py) has two valuable ideas:

- separate timing of vision, classification, prefill, and generation
- compare baseline generation with `cached_image_features` generation

But its main ViT speedup numbers still rely on a model:

- baseline: `N × avg_vit`
- cached: `1 × avg_vit + (N-1) × avg_classify`

That is a reasonable projection for a future sparse path, not direct evidence of one.

### 3. The saved benchmark outputs support the headline agreement claim

Imported result artifacts:

- [tomato_7b_ALL_1000.json](../seed/original_repo/results/tomato_7b_ALL_1000.json)
- [mvbench_7b_10.json](../seed/original_repo/results/mvbench_7b_10.json)

Verified facts:

- TOMATO file contains 1,484 entries and 1,484 `match: true`
- MVBench file contains 160 entries and 160 `match: true`

Important nuance:

- these results support baseline-versus-cached agreement
- they do not imply the base model is highly accurate
- the recorded absolute accuracy is modest and should not be hidden

### 4. Relocation is mostly a negative result

Imported result artifact:

- [mv_relocation_results.json](../seed/original_repo/results/mv_relocation_results.json)

Verified conclusions:

- surveillance pairs show zero relocated tokens
- FPV has a small relocated subset
- average relocation improvement is near zero or negative
- same-position caching is the right default baseline

Important nuance:

- "killed" is fair as a planning decision
- it is not mathematically impossible; there are isolated improved tokens

### 5. Codec-native routing is useful, but pixel diff remains the semantic baseline

Imported result artifact:

- [codec_native_results.json](../seed/original_repo/results/codec_native_results.json)

Verified conclusions:

- packet metadata and MV/residual signals are real routing candidates
- `mv_residual` is clearly worse than pixel diff on talking head and FPV
- `mv_only` can slightly exceed pixel diff cacheability on surveillance
- the right framing is "useful systems signal, not automatic semantic replacement"

### 6. Spatial signals do not replace model saliency

Imported references:

- [qtable_prefilter.py](../seed/original_repo/experiments/qtable_prefilter.py)
- [exp_vit_attention_baseline.py](../seed/original_repo/experiments/exp_vit_attention_baseline.py)
- [vit_attention_results.json](../seed/original_repo/results/vit_attention_results.json)
- [h264_spatial_signals_results.json](../seed/original_repo/results/h264_spatial_signals_results.json)

Verified conclusions:

- pixel variance correlates better with final-layer attention than JPEG surviving AC does
- Q-table flatness is still useful as a cheap binary pre-filter
- Qwen attention structure has meaningful late checkpoints; layer 23 is the strongest reported merge candidate in the imported results
- H.264 spatial signals can correlate with pixel variance reasonably well, but that does not make them strong saliency signals for the VLM

Important nuance:

- some stronger "ceiling" claims in the KB rely on chained correlations and should be treated as suggestive, not definitive

### 7. Benchmark hygiene issues are real

Verified issues in the original repo:

- `run_gemma4_validation.py` contains a hardcoded HF token and was intentionally not imported
- benchmark choice parsing defaults to option A on parse failure
- multiple scripts rely on temp image files and unchecked subprocess success
- the spatial cascade uses approximations and stale-state risks that should not be copied forward blindly

## Targeted Deep-Audit Notes

These are the issues most worth remembering when reading the predecessor code.

### MV experiments need reference validation before reuse

Problems found:

- the relocation and per-block MV scripts assume `fidx - 1` is the relevant prediction source
- B-frame reference structure is therefore under-modeled
- the two MV paths disagree on MV sign convention

Consequence:

- keep MV extraction and per-block lookup as hypotheses or scaffolding
- do not promote their numeric conclusions without re-validating reference semantics

### The timing harness is useful, but biased

Problems found:

- generation timing is measured on a capped frame subset
- the script uses those measurements in `n`-frame rollups
- baseline and cached timing symmetry is imperfect

Consequence:

- keep the component breakdown idea
- rebuild the runner before trusting any final speedup number

### The spatial cascade is not import-safe

Problems found:

- token counts change after merge but downstream masks still reflect pre-merge state
- the MLX path pads reduced tokens back up, so the downstream path does not actually realize the intended win

Consequence:

- use it only as a design sketch
- do not port it as working code

### The H.264 signal studies contain parameterization risk

Problems found:

- QP handling appears to accumulate deltas without a trustworthy base value
- some derived normalization claims therefore deserve caution

Consequence:

- preserve the high-level negative result
- do not treat every specific H.264 signal ranking as settled

## Copy / Rewrite / Discard Map

### Copy As Reference

Imported under `seed/original_repo/`:

- `run_tomato_mlx.py`
- `codec_pipeline.py`
- `exp_wall_clock_speedup.py`
- `exp_vit_attention_baseline.py`
- `exp_per_block_mv_lookup.py`
- `qtable_prefilter.py`
- selected result JSON files

Reason:

- these are useful design references and provenance anchors

### Rewrite Into Working Code

Implemented under `src/codec_through/`:

- strict answer parsing
- temporal block classification
- frame count and packet probing
- frame extraction with bounded temp-file lifetime
- frame-level early-exit routing
- the Q-table pre-filter core

Reason:

- the concepts are worth keeping
- the original implementations were duplicated and too loose for a clean base repo

### Discard From The Active Implementation Path

- `run_gemma4_validation.py`
- mission files as workflow
- KB summaries as direct evidence
- relocation as an early milestone
- the current spatial cascade implementation

Reason:

- security issue, prototype drift, or weak payoff

## Planning Consequences

The most important consequences for this repo are:

- keep semantic substitution and sparse execution as separate tracks
- push frame routing and honest timing earlier in the plan
- treat relocation and continuous spatial codec scoring as deprioritized
- keep Q-table work as pre-filter work, not saliency-oracle work
