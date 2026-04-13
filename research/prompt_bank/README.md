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

- [local_suite_v1.toml](local_suite_v1.toml): initial scored synthetic pilot
  suite for Track A bring-up

## Relationship To The Corpus

- `data/corpus/manifest.toml` says what the clips are
- this directory says what we ask about those clips, which contiguous window to show, and how we score the answers

Do not store long-form per-run outputs here. Those belong in raw artifacts and
experiment notes.
