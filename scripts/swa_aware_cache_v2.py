"""SWA-aware prefix-snapshot cache for Gemma-4-class models.

Strategy that ACTUALLY recovers cross-turn cache reuse on mixed-SWA
topologies, bypassing mlx-vlm 0.4.4's broken trim path:

  1. At setup time, run a prefill of `[system, image, ...]` only --
     i.e., everything in the chat template up to the user's question
     text. This produces a cache state that correctly represents the
     prefix for any subsequent turn (full-attention layers hold
     positions 0..N; SWA layers hold the last `sliding_window` of
     those, which is what they would hold under any subsequent
     prefill of the same prefix).
  2. Deep-copy that cache state -- this is the "prefix snapshot."
  3. For each turn:
     - Restore the snapshot to a fresh working cache.
     - Prefill ONLY the question's trailing tokens against that
       restored cache.
     - Generate.

This avoids the rotating-buffer trim problem entirely because we
never trim; we always start from a clean snapshot.

Cost vs cold-dense:
  - Setup pays a one-time prefill of `n_prefix` tokens (~2080 for
    8 frames at 560x560 on Gemma 4).
  - Each turn pays only `n_question` tokens of prefill (~10) instead
    of the full `n_prefix + n_question`. Speedup ~ n_prefix /
    n_question >> 100x for short questions.

Caveats:
  - The snapshot's SWA cache contains the LAST `sliding_window`
    tokens of `[system, image]`. Any tokens generated within the
    question sequence (Q1's response) would change the SWA window
    in cumulative-cache schemes; here we never let that happen
    because each turn is independent of prior turns.
  - The prefix boundary is determined by chat-template structure:
    everything up to the user's question text. We detect this by
    tokenizing with two different sentinel questions and finding the
    divergence point.

This module provides:
  - `make_prefix_snapshot(harness, img_paths)` -- builds the snapshot
  - `run_turn_with_snapshot(snapshot, harness, question, max_tokens)`
    -- a turn against the snapshot
"""

from __future__ import annotations

import copy
import time
from typing import Any

import mlx.core as mx


def _find_prefix_divergence(ids_a: list[int], ids_b: list[int]) -> int:
    """Return the first index where ids_a and ids_b differ. The shared
    prefix is `ids_a[:divergence]`."""
    n = min(len(ids_a), len(ids_b))
    for i in range(n):
        if ids_a[i] != ids_b[i]:
            return i
    return n


def _deepcopy_cache(cache_list: list[Any]) -> list[Any]:
    """Deep-copy a list of mlx-lm KVCache / RotatingKVCache instances.

    mx arrays are immutable from the outside (`c.keys = ...` rebinds
    the attribute; the underlying buffer can't be in-place mutated by
    the consumer). We need an independent copy so the snapshot survives
    being mutated by a turn's prefill.
    """
    new_list = []
    for c in cache_list:
        # Construct a same-class instance preserving all attributes.
        new_c = copy.copy(c)  # shallow attribute copy
        # Rebind keys / values to fresh array views; mlx arrays are
        # value-semantics from the user's POV (slicing returns a new
        # view), so a copy.copy is sufficient for these attributes.
        if getattr(c, "keys", None) is not None:
            # mx.array.copy() doesn't exist; use mx.array constructor.
            new_c.keys = mx.array(c.keys)
            new_c.values = mx.array(c.values)
        new_list.append(new_c)
    return new_list


def make_prefix_snapshot(harness: Any, img_paths: list[str],
                          sentinel_question_a: str = "Q.",
                          sentinel_question_b: str = "X.",
                          single_shot_prefill: bool = False,
                          ) -> dict[str, Any]:
    """Build a prefix snapshot for the given vision input.

    Parameters
    ----------
    harness : object with .model, .processor, .apply_template,
              .stream_generate, .PromptCacheState attributes.
    img_paths : list[str] -- the same image paths every subsequent
                turn will use.
    sentinel_question_a, sentinel_question_b : two distinct, very
                short sentinel question strings used to detect the
                prefix-boundary token position.

    Returns
    -------
    snapshot : dict with keys
        - "cache": deep-copied cache list at the prefix boundary
        - "n_prefix_tokens": int
        - "prefix_input_ids": mx.array of the prefix (used by callers
                              to construct the per-turn input)
        - "warm_ms": time taken to produce the snapshot
    """
    import mlx.nn as nn  # noqa: F401

    # Step 1: Tokenize with two sentinel questions to find the prefix
    # boundary.
    ids_a = harness.format_inputs(img_paths, sentinel_question_a)[0]
    ids_b = harness.format_inputs(img_paths, sentinel_question_b)[0]
    ids_a_list = ids_a.flatten().tolist()
    ids_b_list = ids_b.flatten().tolist()
    n_prefix = _find_prefix_divergence(ids_a_list, ids_b_list)
    if n_prefix == 0:
        raise RuntimeError(
            "could not find common prefix between sentinel "
            "tokenizations; chat template may not be "
            "deterministic"
        )

    # Step 2: Run prefill of just the prefix portion through the model
    # to populate a fresh cache. Use the language_model directly so we
    # control which tokens get prefilled.
    from mlx_vlm.utils import prepare_inputs  # noqa: F401

    # Build a fresh prompt_cache via the model's make_cache path.
    cache_list = harness.model.language_model.make_cache()

    # Get embeddings for the prefix portion. We need pixel_values to
    # exist so the vision tower runs and image tokens get their
    # embeddings replaced; for this we pass the FULL inputs (including
    # the sentinel question) but cap prefill at n_prefix.
    input_ids_full, pixel_values, mask, _formatted = harness.format_inputs(
        img_paths, sentinel_question_a
    )

    # Vision encode + embedding lookup -- mlx-vlm bundles this in
    # get_input_embeddings.
    embedding_output = harness.model.get_input_embeddings(input_ids_full, pixel_values, mask=mask)
    inputs_embeds = embedding_output.inputs_embeds

    # Prefill the prefix tokens through the language model.
    t0 = time.perf_counter()
    if single_shot_prefill:
        # Single-shot prefill -- no chunking. Eliminates BF16
        # chunked-vs-single-shot numerical drift at the cost of higher
        # peak memory.
        harness.model.language_model(
            inputs=input_ids_full[:, :n_prefix],
            inputs_embeds=inputs_embeds[:, :n_prefix],
            cache=cache_list,
            n_to_process=n_prefix,
        )
        mx.eval([c.state for c in cache_list])
    else:
        # Chunked prefill (default mlx-vlm behavior). Lower peak
        # memory; subject to chunked-vs-single-shot BF16 noise.
        chunk = 512
        pos = 0
        while pos < n_prefix:
            n_to_process = min(chunk, n_prefix - pos)
            slc_ids = input_ids_full[:, pos:pos + n_to_process]
            slc_emb = inputs_embeds[:, pos:pos + n_to_process]
            harness.model.language_model(
                inputs=slc_ids,
                inputs_embeds=slc_emb,
                cache=cache_list,
                n_to_process=n_to_process,
            )
            mx.eval([c.state for c in cache_list])
            pos += n_to_process
    warm_ms = (time.perf_counter() - t0) * 1000.0

    # Step 3: Deep-copy the cache as the immutable snapshot.
    snapshot_cache = _deepcopy_cache(cache_list)

    return {
        "cache": snapshot_cache,
        "n_prefix_tokens": n_prefix,
        "prefix_input_ids": input_ids_full[:, :n_prefix],
        "warm_ms": warm_ms,
    }


def run_turn_with_snapshot(snapshot: dict[str, Any], harness: Any,
                            img_paths: list[str], question: str,
                            *, max_tokens: int = 32,
                            single_shot_prefill: bool = False,
                            ) -> dict[str, Any]:
    """Run a single turn against the prefix snapshot.

    Restores the snapshot into a fresh working cache, prefills only
    the question's trailing tokens, generates, and returns timing and
    output text.

    Caller is responsible for ensuring `img_paths` matches the images
    used to build the snapshot.
    """
    # Restore snapshot.
    working_cache = _deepcopy_cache(snapshot["cache"])
    n_prefix = snapshot["n_prefix_tokens"]

    # Tokenize the full prompt and slice off the cached prefix.
    input_ids_full, pixel_values, mask, _formatted = harness.format_inputs(img_paths, question)
    if input_ids_full.shape[1] <= n_prefix:
        raise RuntimeError("question tokens fit entirely inside the prefix; this should not happen")

    new_ids = input_ids_full[:, n_prefix:]

    # Embed the new tokens. Vision was already done at snapshot time,
    # but we still need text embedding -- and the image tokens (if any
    # in the new portion, which there shouldn't be) need handling. We
    # pass pixel_values=None to skip the vision tower; mlx-vlm will
    # use the cached image features via cached_image_features kwarg if
    # passed. For our purposes, the new tokens contain only text
    # (question + assistant marker), so no vision needed.
    embedding_output = harness.model.get_input_embeddings(new_ids, None, mask=None)
    inputs_embeds = embedding_output.inputs_embeds

    # Prefill the new tokens through the working cache.
    t0 = time.perf_counter()
    if new_ids.shape[1] > 1:
        if single_shot_prefill:
            # Single-shot: process all but last token in one go.
            harness.model.language_model(
                inputs=new_ids[:, :-1],
                inputs_embeds=inputs_embeds[:, :-1],
                cache=working_cache,
                n_to_process=new_ids.shape[1] - 1,
            )
            mx.eval([c.state for c in working_cache])
        else:
            # Chunked prefill (mlx-vlm default).
            chunk = 512
            pos = 0
            while pos < new_ids.shape[1] - 1:
                n_to_process = min(chunk, new_ids.shape[1] - 1 - pos)
                harness.model.language_model(
                    inputs=new_ids[:, pos:pos + n_to_process],
                    inputs_embeds=inputs_embeds[:, pos:pos + n_to_process],
                    cache=working_cache,
                    n_to_process=n_to_process,
                )
                mx.eval([c.state for c in working_cache])
                pos += n_to_process
        # The last token is fed to _step in the generation loop.
        last_token = new_ids[:, -1:]
        inputs_embeds[:, -1:]
    else:
        last_token = new_ids

    # Generate using the working cache via stream_generate. We feed it
    # the last token only and pre-populated prompt_cache.
    text_pieces = []
    token_ids = []
    first_token_id = None
    prefill_t = time.perf_counter() - t0
    t_first = None
    kwargs = {
        "max_tokens": max_tokens,
        "input_ids": last_token,
        "pixel_values": None,
        "temperature": 0.0,
        "prompt_cache": working_cache,
    }
    for resp in harness.stream_generate(harness.model, harness.processor, "", **kwargs):
        if t_first is None:
            t_first = time.perf_counter()
        if resp.text:
            text_pieces.append(resp.text)
        try:
            tok_int = int(resp.token)
        except Exception:  # noqa: BLE001
            tok_int = resp.token
        if first_token_id is None:
            first_token_id = tok_int
        token_ids.append(tok_int)
    wall = (time.perf_counter() - t0) * 1000.0
    return {
        "output_text": "".join(text_pieces),
        "n_input_tokens": int(input_ids_full.shape[1]),
        "n_new_tokens_prefilled": int(new_ids.shape[1]),
        "n_output_tokens": len(token_ids),
        "first_token_id": first_token_id,
        "wall_ms": wall,
        "prefill_ms": prefill_t * 1000.0,
        "generate_ms": wall - prefill_t * 1000.0,
    }
