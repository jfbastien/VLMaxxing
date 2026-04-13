# Decision Log

This is the canonical ledger for adopted, weakened, killed, and revived ideas.

| Idea | Status | Evidence | Reopen condition |
| --- | --- | --- | --- |
| Track A / Track B split | Adopted | [PLAN.md](../PLAN.md), [docs/original-repo-audit.md](../docs/original-repo-audit.md) | Reopen only if a later runtime exposes a single path that simultaneously proves both semantics and skipped compute |
| Same-position temporal reuse baseline | Adopted | [docs/original-repo-audit.md](../docs/original-repo-audit.md), [seed/original_repo/results/tomato_7b_ALL_1000.json](../seed/original_repo/results/tomato_7b_ALL_1000.json) | Reopen if local reproduction shows major disagreement on the intended clip buckets |
| Embedding relocation as primary path | Weakened | [docs/original-repo-audit.md](../docs/original-repo-audit.md), [seed/original_repo/results/mv_relocation_results.json](../seed/original_repo/results/mv_relocation_results.json) | Reopen only with a stabilization-first or architecture-specific correction that beats same-position reuse |
| Continuous H.264 spatial scoring as saliency oracle | Deprioritized | [docs/knowledge-base-notes.md](../docs/knowledge-base-notes.md), [seed/original_repo/results/h264_spatial_signals_results.json](../seed/original_repo/results/h264_spatial_signals_results.json) | Reopen only if simple routing plateaus and a raw-artifact reread shows stronger-than-expected correlation |
| DCT-bypass as early systems win | Weakened | [docs/knowledge-base-notes.md](../docs/knowledge-base-notes.md), [seed/whitepaper/whitepaper.md](../seed/whitepaper/whitepaper.md) | Reopen only with evidence that work is skipped before dense patch embedding, not merely reparameterized |
| Codec metadata replacing pixel diff in production (`MV=0 + CBF=0 -> STATIC`) | Active hypothesis | [seed/whitepaper/whitepaper.md](../seed/whitepaper/whitepaper.md), [PLAN.md](../PLAN.md) | Promote only after decoder-side routing is measured against the pixel-diff baseline |
| TOMATO 7B baseline accuracy (`22.2%`) | Imported result | [seed/original_repo/results/tomato_7b_ALL_1000.json](../seed/original_repo/results/tomato_7b_ALL_1000.json) | Replace with local reproduction or keep explicitly imported |
| 14-frame drift remaining semantically correct at `0.85` cosine | Imported, unverified | [seed/whitepaper/whitepaper.md](../seed/whitepaper/whitepaper.md) | Reopen via the local refresh-interval sweep in Track A |
| Changed-window sparse execution | Active hypothesis | [PLAN.md](../PLAN.md), [seed/chatgpt/codec_design_space_report.md](../seed/chatgpt/codec_design_space_report.md) | Promote if measured local speedup lands without unacceptable quality drift |
| Changed-query attention | Active hypothesis | [PLAN.md](../PLAN.md), [paper/framing.md](../paper/framing.md) | Promote only after changed-window execution is working and simulation plus runtime evidence agree |
| Screen-content fork | Active hypothesis | [PLAN.md](../PLAN.md), [docs/literature-map.md](../docs/literature-map.md) | Promote if screen-content clips show distinct failure or win patterns under shared policies |
| Aggressive composed stackup arithmetic | Gated | [docs/methodology/timing-harness.md](../docs/methodology/timing-harness.md) | Allow only after same-stack component measurements exist |

When a row changes status, add a dated note or a successor row instead of silently
erasing the previous reasoning. The log is meant to preserve decision history.
