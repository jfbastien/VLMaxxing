"""Codec-native metadata extraction subpackage.

Ported from Sam's whitepaper repo (`codec-through-sam/experiments/`).
See `h264_metadata.py` for per-macroblock MV/residual/skip/CBF
extraction via PyAV side-data. Phase 1.29 (MV-only signal path) uses
this as the source of codec-native classification to compare against
the pixel-diff proxy.
"""
