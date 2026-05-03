# Figure 1 Review Bundle

This bundle contains the current automated Figure 1, planner-appendix, and PDF
review pack after the planner-appendix explainer pass.

Included scripts:
- `paper/arxiv/scripts/fig1_primitives.py`
- `paper/arxiv/scripts/find_fig1_candidates.py`
- `paper/arxiv/scripts/render_fig1_variants.py`
- `paper/arxiv/scripts/render_fig1_appendix.py`
- `paper/arxiv/scripts/validate_fig1_assets.py`

Included review assets:
- updated production schematic `generated/figures/regime_overview.{png,pdf,svg}`
- selected publication/review manifest
  `generated/figures/fig1_candidates/planner_selected_candidates.json`
- corrected internal review variants from `fig1_variants_review2_tomato/`
- corrected internal review variants from `fig1_variants_review2_videomme/`
- appendix views from `fig1_appendix_broadened/` as PNG, PDF, and SVG:
  `planner_trace_real_clip` and `planner_examples_gallery`
- rebuilt manuscript PDF at `paper/arxiv/build/main.pdf`

Current recommendation:
- keep the schematic `regime_overview` as Figure 1;
- use `planner_trace_real_clip` to explain one actual Qwen routing-budget decision;
- use `planner_examples_gallery` to show the same policy on TOMATO, VideoMME
  380, and a lower-reuse VideoMME boundary case;
- treat the real-frame Figure 1 variants as review experiments, not as a
  replacement for the main figure, because the bars visualize fixed-backend
  Qwen routing-budget evidence rather than C-PERSIST timing evidence.

The planner figures visualize the audited block policy behind the Section 6
Qwen routing frontier: `max_abs(8,32)`, active-region only, reuse classes
`static+shifted`, `age < 4`. The trace figure shows previous frame, current
frame, planner classes, and the resulting reused/fresh decision card. The
examples figure shows the strongest fresh transition in each window plus the
window-average reused/fresh budget. C-VISION token masks in the result cards
are schematic because no checked per-example C-VISION keep-mask artifact is
present.

Candidate mining status:
- `planner_selected_candidates.json` references only asset directories included
  in this zip and is suitable for package validation;
- broader ranked manifests are not included in this zip because they reference
  many derivative assets outside the selected publication/review set;
- the checked selected assets here are targeted/recovered review artifacts, not
  evidence that a full `--scan-all-artifacts` mine completed;
- the scripts required to reproduce extraction and rendering are included, but
  regenerated full-corpus mining still requires the benchmark videos locally.

Validation command after extracting the zip:

```bash
python paper/arxiv/scripts/validate_fig1_assets.py \
  --repo-root . \
  paper/arxiv/generated/figures/fig1_candidates/planner_selected_candidates.json
```
