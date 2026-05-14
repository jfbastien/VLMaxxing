# OV-6 Sidecar Equivalence

Hypothesis: Precomputed H.264 score sidecars preserve live-PyAV codec-grid behavior while moving extraction cost outside model-run timing.
Gate: zero choice/correctness/kept-count drift for every source; live runtime source is live_pyav; sidecar runtime source is sidecar; sidecar load < 1s/item and below live extraction time.
Falsification: any drift, missing runtime-source provenance, or sidecar load >= 1s/item

| source | n | choice drift | correctness drift | kept-count drift | live source | sidecar source | live extract s/item | sidecar load s/item | gate |
| --- | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | --- |
| novel_coded | 3 | 0 | 0 | 0 | live_pyav | sidecar | 20.147311 | 0.002022 | PASS |
| motion | 3 | 0 | 0 | 0 | live_pyav | sidecar | 23.783098 | 0.002940 | PASS |
| residual | 3 | 0 | 0 | 0 | live_pyav | sidecar | 21.087001 | 0.002548 | PASS |

Overall gate: PASS
