# ChatGPT Seed Artifacts

These files were imported from local ChatGPT outputs on 2026-04-13.

Purpose:

- preserve starting ideas
- preserve prototype code
- preserve seed plots and reports

Non-purpose:

- serve as the repo's final source of truth
- bypass local verification

## Provenance

Imported from:

- `~/Downloads/whitepaper.pdf`
- `~/Downloads/codec_through_reference.py`
- `~/Downloads/run_codec_through_toy_experiments.py`
- `~/Downloads/codec_through_expansions.py`
- `~/Downloads/run_codec_through_expansion_experiments.py`
- `~/Downloads/codec_through_toy_report.md`
- `~/Downloads/codec_design_space_report.md`
- `~/Downloads/video_codec_vlm_mac_workplan.md`
- `~/Downloads/codec_through_codebase_review_revised_plan.md`
- `~/Downloads/codec_through_experiment_backlog.json`
- the related PNG assets in `~/Downloads`

## Duplicate Files

Several downloaded files also existed with a ` (1)` suffix.

They were not imported separately because local SHA-1 comparison showed they are byte-for-byte identical to the unsuffixed versions.

## Trust Level

Treat these artifacts as:

- useful
- promising
- unverified

The main repo plan promotes a claim only after:

- we reproduced it locally
- or we verified it against a primary source

## Running The Seed Scripts

The Python files in this directory are kept close to their imported form.

They will likely need:

- `numpy`
- `pandas`
- `matplotlib`
- `Pillow`

and later possibly:

- video tooling such as `av`

Because the scripts import sibling files by name, run them from the repo root in a way that uses the script path directly, for example:

```bash
uv run python seed/chatgpt/run_codec_through_toy_experiments.py
```

## Directory Contents

- `codec_through_reference.py`
- `run_codec_through_toy_experiments.py`
- `codec_through_expansions.py`
- `run_codec_through_expansion_experiments.py`
- `codec_through_toy_report.md`
- `codec_design_space_report.md`
- `video_codec_vlm_mac_workplan.md`
- `reviews/codec_through_codebase_review_revised_plan.md`
- `reviews/codec_through_experiment_backlog.json`
- `assets/`
