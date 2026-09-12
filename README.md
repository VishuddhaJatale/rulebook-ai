# Rulebook AI

A checkable, evidence-grounded academic regulation assistant built for the It Geeks AI
Developer vibe-coding round.

## Core states

- `ANSWERABLE` — the corpus contains sufficient evidence to answer.
- `NOT_COVERED` — the corpus does not establish an answer; the system must refuse to invent one.
- `CONTRADICTION` — applicable corpus evidence contains incompatible rules.

## Corpus

The repository preserves two official RGPV B.E. ordinance PDFs supplied as project source
documents and includes clearly labeled synthetic evaluation documents.

The synthetic corpus intentionally contains exactly three contradictions documented in
`docs/contradictions.md`.

## Current milestone

This repository currently contains the corpus and contradiction ground truth. The next
milestone is document ingestion, chunk metadata, retrieval, and the three-state evidence
pipeline.
