#!/usr/bin/env bash
# Apply the SWA-aware trim patch to a locally-installed mlx-vlm.
#
# Usage:
#   ./scripts/apply_mlx_vlm_swa_patch.sh         # apply
#   ./scripts/apply_mlx_vlm_swa_patch.sh --check # dry-run
#   ./scripts/apply_mlx_vlm_swa_patch.sh --revert # revert
#
# After applying: the mlx-vlm 0.4.4 cross-turn cache trim respects
# RotatingKVCache.is_trimmable() and surrenders cache reuse cleanly
# when the rotating buffer has wrapped. Cross-turn output on Gemma 4
# 26B-A4B (and any other mixed-SWA model) is then byte-identical to
# cold dense.
#
# This is a LOCAL fix; it will be overwritten on `pip install
# --upgrade mlx-vlm`. Re-run after upgrading. Upstream PR pending --
# track at <https://github.com/Blaizzy/mlx-vlm/issues/...>.

set -euo pipefail

PATCH_FILE="$(dirname "$0")/mlx_vlm_swa_aware_trim.patch"
TARGET="$(python3 -c 'import mlx_vlm.generate, importlib; m = importlib.import_module("mlx_vlm.generate"); print(m.__file__)')"

if [ ! -f "$PATCH_FILE" ]; then
    echo "patch file not found: $PATCH_FILE" >&2
    exit 1
fi

if [ ! -f "$TARGET" ]; then
    echo "mlx_vlm.generate.py not found: $TARGET" >&2
    exit 1
fi

case "${1:-apply}" in
    --check)
        # Test if the patch would apply cleanly (dry run).
        patch --dry-run -p0 -i "$PATCH_FILE" --quiet || {
            echo "patch DOES NOT APPLY cleanly (already applied?, or mlx-vlm version drift?)" >&2
            exit 2
        }
        echo "patch applies cleanly to $TARGET"
        ;;
    --revert)
        patch -R -p0 -i "$PATCH_FILE" --quiet
        echo "reverted: $TARGET"
        ;;
    apply|"")
        # Apply the patch.
        if patch --dry-run -R -p0 -i "$PATCH_FILE" --quiet 2>/dev/null; then
            echo "patch already applied to $TARGET"
            exit 0
        fi
        patch -p0 -i "$PATCH_FILE"
        echo "applied: $TARGET"
        echo
        echo "verify with the B0b regression (no runtime guard needed):"
        echo "  python3 scripts/run_sam_b0b_cache_correctness.py --smoke --out /tmp/post_patch_smoke.jsonl"
        ;;
    *)
        echo "unknown arg: $1" >&2
        echo "usage: $0 [apply|--check|--revert]" >&2
        exit 1
        ;;
esac
