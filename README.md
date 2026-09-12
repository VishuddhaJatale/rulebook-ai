# Rulebook AI

A checkable, evidence-grounded academic regulation assistant built for the
It Geeks AI Developer vibe-coding round.

Rulebook AI answers student questions using a controlled academic regulation
corpus. Instead of guessing when information is missing or choosing between
conflicting rules, the system explicitly classifies each question into one of
three states:

- `ANSWERABLE` — the corpus contains sufficient evidence to answer the question.
- `NOT_COVERED` — the corpus does not establish the requested information, so
  the system does not invent an answer.
- `CONTRADICTION` — the corpus contains incompatible claims relevant to the
  question.

Every result is backed by retrieved source passages with source, section,
provision, and page metadata where available.

---

## Architecture

```text
Student Question
       |
       v
Document Corpus
       |
       v
Semantic Retrieval
(all-MiniLM-L6-v2 + FAISS)
       |
       v
Cross-Encoder Reranking
(ms-marco-MiniLM-L-6-v2)
       |
       v
Evidence Sufficiency
       |
       v
Three-State Detection
       |
       +------------------+------------------+
       |                  |                  |
       v                  v                  v
 ANSWERABLE         NOT_COVERED       CONTRADICTION
       |                  |                  |
       v                  v                  v
 Supporting          No invented       Conflicting
 Evidence              answer             Evidence