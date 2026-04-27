# Phase 1.55F-Gemma — Adaptive C-PERSIST Cross-Architecture Probe (DEFERRED)

Gemma 4-E4B-IT-4bit weights are present locally under
`~/models/gemma-4-e4b-it-4bit`, and prior Gemma 4-bit runs fit this 16 GB
unified-memory laptop under the repo's 9-10 GB RSS policy.

Do **not** run the Qwen selective re-prefill/adaptive driver on Gemma 4.
Phase 1.55C found that Gemma 4 uses rotating/sliding-window KV caches, and the
current mlx-vlm prompt-cache truncation path can silently corrupt those caches
for video-length prefixes. The existing `run_kv_selective_reprefill_v2.py`
therefore hard-fails non-Qwen models by design.

Paper implication: Gemma Track B sparse-ViT (`1.63G`) is ready because it avoids
Gemma language-cache reuse. Gemma adaptive C-PERSIST is blocked on a
cache-type-aware Gemma driver or a non-sliding Gemma-family target.
