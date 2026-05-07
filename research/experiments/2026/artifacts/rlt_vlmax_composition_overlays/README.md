# RLT/VLMaxxing Overlays

Generated with:

```bash
uv run python scripts/render_rlt_vlmax_composition_overlays.py
```

These are deliberate review artifacts. They use the same three windows as the
VLMaxxing overlay reel and are regenerated from local benchmark assets rather
than hand-annotated.

Current scientific contract:

- Default `measured_c_vision` mode shows the measured Gemma sparse-vision
  mechanism: dense encoder positions, fixed-K RLT-kept positions, and skipped
  vision-tower compute.
- RLT panes recompute the local `codec_through.rlt_masks` kernel with
  `tau=0.1`, `tubelet_size=2`, 224x224 ImageNet-normalized input, and
  `patch_size=16`, then project scores to a fixed-K Gemma 32x32 encoder mask
  at `keep_rate=0.5`.
- The committed benchmark JSONLs record counts and timings, not the per-position
  boolean mask. The renderer reconstructs masks from the logged algorithm config
  and source video, so the visualization is algorithmically faithful rather than
  a replay of persisted mask arrays.
- The older pixel-domain union view is still available with
  `--panel-mode preregistration_overlay`. It is provenance for the hypothesis
  visualization and should not be used as the post-result speedup explanation.

Source media are not vendored by this artifact; see the manifest for local
source paths and regeneration metadata.
