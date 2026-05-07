# RLT/VLMaxxing Composition Overlays

Generated on 2026-05-07 with:

```bash
uv run python scripts/render_rlt_vlmax_composition_overlays.py
```

These are deliberate review artifacts. They use the same three windows as the
VLMaxxing overlay reel and are regenerated from local benchmark assets rather
than hand-annotated.

Scientific contract:

- VLMaxxing panes recompute the existing Fig. 1 routing-budget policy.
- RLT panes recompute the local `codec_through.rlt_masks` kernel with
  `tau=0.1`, `tubelet_size=2`, 224x224 ImageNet-normalized input, and
  `patch_size=16`.
- Combined panes show a conservative pixel-domain union of VLMaxxing fresh
  regions and RLT representative-token regions. They visualize the hypothesis
  being tested, not an earned multiplier claim.

Source media are not vendored by this artifact; see the manifest for local
source paths and regeneration metadata.
