# Historical Seed Imports

These files are imported artifacts from the predecessor (pre-release source) repo. They were originally working-tree-only files referenced by an audit doc that was removed in the OSS-prep cleanup; this directory rematerializes them under a tracked path so they are eligible to back paper-body claims that previously could only be supported by ignored working-tree state.

## Files

| File | Records | Schema | Role |
|---|---|---|---|
| `tomato_7b_ALL_1000.json` | 1,484 | `{split, gt, bl_correct, ca_correct, match, reuse}` per record; all `match: true` | Predecessor TOMATO baseline-vs-cached headline agreement |
| `mvbench_7b_10.json` | 160 | same schema; all `match: true` | Predecessor MVBench baseline-vs-cached headline agreement |
| `vit_attention_results.json` | 15 images | `{experiment, model, num_images, vit_config, aggregate_layer_correlations, aggregate_signal_correlations, per_image}` | ViT-attention vs pixel-variance / JPEG-surviving-AC saliency proxy correlations |
| `mv_relocation_results.json` | 3 content classes | keyed `{surveillance, talking_head, fpv_drone}` with per-pair classifications | MV-relocation finding (mostly negative across content) |
| `h264_spatial_signals_results.json` | per-video aggregate | `{experiment, num_videos, per_video, aggregate}` | H.264-vs-pixel-variance correlations |
| `codec_native_results.json` | 3 video files | keyed by video filename | Codec-native routing comparison across video types |

## Naming caveat preserved from upstream

`tomato_7b_ALL_1000.json` contains 1,484 entries despite the `1000` suffix. The filename is preserved for provenance; any text discussing it must use the actual content count.

## Provenance

These files were copied from `seed/original_repo/results/` in the working tree. They were not previously tracked in git. The earlier OSS hygiene pass (commit `73fb023`, 2026-04-29) deleted the audit doc that referenced them; this rematerialization undoes only the artifact side. Any paper-body or claim-matrix re-promotion is a separate decision and should be tracked alongside a successor audit doc that links back to these checked artifacts.
