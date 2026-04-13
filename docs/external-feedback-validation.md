# External Feedback Validation

Scope:

- reviewed the imported ChatGPT files under `seed/chatgpt/reviews/`
- checked their main claims against `codec-through-sam` code and saved result artifacts

## Overall Verdict

The external review is mostly directionally correct.

Its strongest contribution is conceptual clarity:

- semantic substitution versus sparse execution
- codec signals as useful routing signals rather than automatic saliency signals
- the importance of preserving negative results

Its weaker parts are the forward-looking recommendations that are not yet backed by this repo's own evidence.

## Supported

### Semantic substitution versus sparse execution

Supported by:

- imported reference `run_tomato_mlx.py`
- imported reference `exp_wall_clock_speedup.py`

Conclusion:

- this distinction is real and should stay central in our docs and code

### Relocation is mostly a negative result

Supported by:

- imported `mv_relocation_results.json`

Conclusion:

- relocation should not lead the next round of work

Nuance:

- the repo contains isolated improvements, so this is a planning kill, not a mathematical impossibility claim

### Codec-native branch is valuable, but mixed

Supported by:

- imported `codec_pipeline.py`
- imported `exp_per_block_mv_lookup.py`
- imported `codec_native_results.json`

Conclusion:

- codec metadata is worth pursuing for routing and systems work
- pixel diff remains the semantic-validation baseline

### Benchmark hygiene issues are real

Supported by:

- original benchmark parsing behavior
- temp-file-heavy extraction patterns
- the secret leak in the original Gemma validation script

Conclusion:

- clean rewrites and stricter utilities were the right response

## Supported But Should Be Reframed

### The repo is "more mature than the whitepaper suggests"

This is directionally true, but the maturity is uneven.

Better framing:

- strong mechanism work
- strong negative-result exploration
- uneven systems implementation

### Spatial branch value

The external review is right that the spatial branch matters.

Better framing:

- useful for pre-filters and architecture questions
- not yet a proven end-to-end spatial compression story

## Open Hypotheses, Not Verified Findings

### Changed-token-focused attention

Status:

- plausible
- not directly demonstrated by the original repo

Why:

- the repo motivates it indirectly through weak external-signal correlations and model-attention structure
- it does not implement changed-query execution as a measured result

### Canonical-coordinate stabilization as the egomotion path

Status:

- plausible and worth testing
- not a verified repo result

### Codec-conditioned frame scheduling as a major win

Status:

- promising
- only lightly supported so far by routing ideas and packet metadata work

## Claims We Did Not Promote

- M3 Air-specific severity claims derived from M5 Max timing code
- strong DCT-bypass deprioritization without direct artifact review in this repo
- any exact composed compression multiplier from stacked methods

## Consequences For This Repo

The validated takeaways we promoted into the plan are:

- keep semantic and systems tracks separate
- keep relocation deprioritized
- prioritize frame routing and honest timing
- keep changed-query attention and stabilization as explicit hypotheses, not claims
