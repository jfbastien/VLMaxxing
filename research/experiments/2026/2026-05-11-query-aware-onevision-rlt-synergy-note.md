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
   and summary JSON. Import the scaffolding later, not the RLT science.

## Explicit Non-Goals For This Branch

- No query-aware implementation.
- No RLT operator claims in the OneVision editor packet.
- No sibling-repo artifacts as OneVision provenance.
- No promotion of codec saliency beyond the bounded OV-3 result until OV-6 and
  replication cells are measured.
