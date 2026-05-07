# RLT/VLMaxxing Overlays

Generated with:

```bash
uv run python scripts/render_rlt_vlmax_composition_overlays.py
```

These are deliberate review artifacts. They use the same three windows as the
VLMaxxing overlay reel and are regenerated from local benchmark assets rather
than hand-annotated.

Current scientific contract:

- The default artifact is a composition-intuition reel. It shows the source
  frame, the checked VLMaxxing fresh/reuse routing overlay, the local RLT
  keep mask, and a pixel-domain union of the two signals.
- RLT panes recompute the local `codec_through.rlt_masks` kernel with
  `tau=0.1`, `tubelet_size=2`, 224x224 ImageNet-normalized input, and
  `patch_size=16`. The visualization shows the RLT mask only; it does not
  include RLT length encoding.
- The union pane is an explanatory envelope, not a measured runtime claim. It
  is meant to show why VLMaxxing routing and RLT motion masks can be discussed
  as composition partners.
- Measured RLT-as-C-VISION benchmark speedups and scorer-cost ratios are
  included as HUD and manifest context where artifacts are available, but the
  overlay masks are not exact Gemma sparse-vision runtime replays.
- Overlay fractions are active-crop pixel fractions for visual explanation.
  The manifest separately records the RLT token-domain keep rate.

Source media are not vendored by this artifact; see the manifest for local
source paths and regeneration metadata.
