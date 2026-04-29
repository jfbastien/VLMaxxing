# Prompt Bank

This directory holds versioned prompt sets and answer keys.

Prompt banks are part of the experimental contract. They should be stable enough
that another person can rerun the same evaluation without reconstructing the
questions from chat history.

## Rules

- version prompt banks instead of editing them silently
- keep prompt ids stable once used in an experiment note
- record the answer key only when the clip is controlled enough to justify it
- if a clip is agreement-only or qualitative, say that explicitly instead of
  pretending it has a ground-truth label

## Current Files

- [local_suite_v2.toml](local_suite_v2.toml): repaired synthetic suite with
  temporal-necessity items and critical-pair metadata; current default for
  local Track A work
- [crosscheck_slice_v2.toml](crosscheck_slice_v2.toml): endpoint-oriented
  real-video slice on the predecessor cross-check clips; current natural-video
  Track A slice for generalized pre-release source reproduction
- [crosscheck_slice_v1.toml](crosscheck_slice_v1.toml): first cross-check
  real-video draft preserved because it surfaced weak middle-event items and
  drove the v2 rewrite
- [local_suite_v1.toml](local_suite_v1.toml): initial scored synthetic pilot
  suite preserved for historical comparison

## Relationship To The Corpus

- `data/corpus/manifest.toml` says what the clips are
- this directory says what we ask about those clips, which contiguous window to show, and how we score the answers

## Item Metadata

Optional item-level fields can make failure analysis more honest:

- `critical_pair_indices`: adjacent frame-pair indices in the selected window
  that matter most for the question
- `requires_middle_frames`: whether the question should fail if only endpoints
  are considered
- `solvable_from_first_last`: whether the question could be answered correctly
  from just the first and last frames

Do not store long-form per-run outputs here. Those belong in raw artifacts and
experiment notes.
