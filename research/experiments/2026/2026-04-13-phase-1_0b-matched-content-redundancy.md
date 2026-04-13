# Phase 1.0b: Matched Content-Class Redundancy

## Preregistration

Claim register target:

- `WP-2.4` supporting context
- whitepaper content-class redundancy story for talking-head, surveillance, and
  FPV or egomotion-like clips

Reproduction mode:

- generalized reproduction

Hypothesis:

- the local predecessor cross-check clips will preserve the imported ordering:
  talking-head has the highest reuse, FPV-like egomotion has the lowest reuse,
  and surveillance-like content falls between them

Track:

- A-supporting measurement

Primary metrics:

- full-trim clip average `static_ratio`
- full-trim clip average `reused_ratio`

Secondary metrics:

- `shifted_ratio`
- `novel_ratio`
- stable Xiph surveillance-proxy comparison via `xiph_hall_monitor_cif`

Unit of analysis:

- whole locally trimmed clip, averaged over every adjacent frame pair in the
  clip after repo-standard preprocessing

Acceptance band:

- `crosscheck_talking_head` has the highest `reused_ratio`
- `crosscheck_fpv_drone` has the lowest `reused_ratio`
- `crosscheck_surveillance` lands between them

Rejection band:

- the ordering above does not hold

Inconclusive:

- one of the cross-check clips is missing or decode fails
- the ordering is ambiguous because the middle class overlaps both extremes too
  closely to interpret

Notes:

- this is not yet benchmark evidence
- the cross-check set is useful for whitepaper reproduction, but it is still
  local-only and not stable enough for primary paper evidence
- `xiph_hall_monitor_cif` is included as a stable surveillance-like anchor, not
  as a substitute for the predecessor surveillance clip

## Execution

Run date:

- 2026-04-13

Artifact:

- [phase1_0b.json](artifacts/phase1_0b.json)

## Result

Preregistration outcome:

- Accepted

Observed clip-wide averages:

- `crosscheck_talking_head`: `static_ratio = 0.931`, `reused_ratio = 0.970`
- `crosscheck_surveillance`: `static_ratio = 0.768`, `reused_ratio = 0.895`
- `crosscheck_fpv_drone`: `static_ratio = 0.393`, `reused_ratio = 0.781`
- `xiph_hall_monitor_cif`: `static_ratio = 0.771`, `reused_ratio = 0.970`

Imported-order check:

- talking-head has the highest `reused_ratio`
- FPV-like egomotion has the lowest `reused_ratio`
- the predecessor surveillance clip lands between them

Notable comparison against the imported whitepaper shape:

- the local cross-check talking-head clip remains very high-reuse
- the local cross-check surveillance clip remains intermediate
- the local cross-check FPV clip remains much less reusable and is very close
  to the imported low-static regime
- the stable `hall_monitor` proxy is more static than the predecessor
  surveillance clip, which is a useful reminder that "surveillance-like" is not
  a single temporal regime

## Interpretation

This is a successful generalized reproduction of the whitepaper's content-class
redundancy ordering on this machine. It is not yet strict reproduction because
the YouTube cross-check bitstreams are not guaranteed to match the predecessor's
historical downloads, but the class structure and the clip-specific ordering are
now locally grounded rather than imported-only.

The `hall_monitor` comparison is useful in its own right. A fixed-camera
surveillance-style proxy can still land near the talking-head reuse regime when
the scene is extremely stable, while the predecessor surveillance clip sits
closer to the whitepaper's intended "moderate motion under a fixed viewpoint"
bucket. That means future surveillance conclusions should not collapse all fixed
camera footage into one reuse number.

## Links

- [docs/claim-register.md](../../docs/claim-register.md)
- [2026-04-13-phase-1_0-local-redundancy.md](2026-04-13-phase-1_0-local-redundancy.md)
- [docs/reproduction-status.md](../../docs/reproduction-status.md)
