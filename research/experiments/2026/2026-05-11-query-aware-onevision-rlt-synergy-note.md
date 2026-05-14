# Query-Aware / RLT Synergy Note For OneVision Work

Date: 2026-05-11  
Status: future-branch planning note; no current-branch query-aware implementation.

## Boundary

Do not mix RLT/query-aware science into the OneVision x VLMaxxing OV-3/OV-6 evidence
chain. The current branch should close codec-native Track A and then test Track B sparse
vision. Query-aware routing needs a separate branch, separate preregistration, and a
fresh design/dev/holdout split.

## Ideas To Carry Forward Later

1. **Codec planes as physical evidence operators.**  
   The OV-3 score planes (`novel_coded`, motion magnitude, residual proxy, fused
   motion/residual) may become low-cost physical evidence operators for a later
   query-aware planner. Example: query asks about motion, object contact, text, or
   scene change; the query-aware planner chooses which codec evidence plane should
   bias refresh.

2. **Do not tune on inspected OV-3 items.**  
   Any rule design that uses the OV-3 forensics burns those items for design. A later
   query-aware branch should create a `design_v1` slice, freeze rules, then validate
   on dev and touch holdout once.

3. **Import statistical discipline before promotion.**  
   Future query-aware/RLT work should use paired bootstrap or paired exact tests as the
   primary inferential object, keep family handling explicit, and avoid coercing sets
   when bootstrapping overlap/rescue metrics.

4. **Improve visualization contracts.**  
   OneVision manifests already record source provenance. Future query-aware overlays
   should also include an `accuracy_contract` field that states which masks are
   computed, which overlays are intuition only, which denominators are measured, and
   which claims are pending model evidence.

5. **Operational runner pattern.**  
   The RLT queue-runner pattern is useful for later OneVision queues: phase estimates,
   dependency gates, dry-run mode, elapsed timing, command capture, skip/stop decisions,
   and summary JSON. The codec-score sidecar contract added for OV-6 is also useful
   future scaffolding: query-aware/RLT runs can consume precomputed physical evidence
   planes without re-extracting H.264 metadata or changing the OneVision evidence chain.
   Import the scaffolding later, not the RLT science.

6. **Query-aware role selection, not query-aware tuning here.**
   The completed OV-6 follow-up sweep suggests the same H.264 signal plays different
   roles in different denominators: refresh prior in Track A, bounded sparse-ranking
   candidate in Track B, and setup-cost input for C-PERSIST accounting. A later
   query-aware branch should test whether the query can choose between codec evidence,
   random selection, and model-internal magnitude without tuning on inspected OV-3/OV-6
   items. This branch should not implement that selector.

7. **Sidecar architecture makes cheap query-aware A/B feasible.**
   The H.264 score sidecar contract (`src/codec_through/codec/score_sidecar.py`,
   built via `scripts/build_ov6_codec_score_sidecars.py`) caches normalized codec
   score grids per (manifest item, source, geometry, frame count, projection
   version) tuple, sha256-bound to score config. Once an M3 sidecar-equivalence
   gate has demonstrated zero-drift parity with live PyAV extraction, a future
   query-aware run can compare codec / random / magnitude routing decisions on
   the same item without re-extracting H.264 metadata. The dominant per-item
   cost in OV-6 (10-19s PyAV extract on M3) becomes a one-time setup. The
   query-aware branch should reuse this sidecar contract; it should not invent
   a parallel cache and it should not bypass the manifest_item_ids /
   score_config_id binding, since that binding is what makes the cached
   decision provenance auditable.

8. **Track A on Gemma is the open cross-family question for the refresh oracle.**
   Phase 4 Qwen Track A pooled-calibration agreement is Wilson-lower 0.91 to
   dense. The OV-3 runner is currently Qwen-coupled (hard-coded grid count
   check, Qwen prefill/reuse plumbing). A future cross-family confirmation
   on Gemma SigLIP would either generalize the refresh-oracle claim or
   bound it to Qwen ViT. The query-aware branch should consider this when
   choosing whether the codec-evidence selector applies across vision-tower
   families or only within one family.

## Explicit Non-Goals For This Branch

- No query-aware implementation.
- No RLT operator claims in the OneVision editor packet.
- No sibling-repo artifacts as OneVision provenance.
- No promotion of codec saliency beyond the bounded OV-3 / OV-6 results without
  a new query-aware preregistration and fresh item split.
