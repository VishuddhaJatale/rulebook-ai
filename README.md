# Rulebook AI

> A checkable, evidence-grounded academic regulation assistant that knows when to answer, when to refuse, and when the rulebook disagrees with itself.

Rulebook AI is an academic regulation question-answering system built for the **It Geeks AI Developer vibe-coding round**.

The system answers student questions using a controlled academic regulation corpus. Instead of behaving like a general-purpose chatbot and guessing an answer from general knowledge, Rulebook AI retrieves evidence from the provided rulebook and explicitly determines whether the question is:

- **`ANSWERABLE`** — the corpus contains sufficient evidence to answer the question.
- **`NOT_COVERED`** — the corpus does not establish the requested information, so the system refuses to invent an answer.
- **`CONTRADICTION`** — the corpus contains incompatible claims relevant to the question.

Every result is backed by retrieved source passages containing provenance such as:

- Source document
- Section
- Provision / rule number
- Page number where available

The goal is not simply to build a chatbot that produces plausible answers. The goal is to build a **checkable regulation assistant whose decisions can be inspected, traced to evidence, and evaluated**.

---

## Table of Contents

- [Why This Project Exists](#why-this-project-exists)
- [Core Idea](#core-idea)
- [Key Features](#key-features)
- [Three-State System](#three-state-system)
- [Architecture](#architecture)
- [End-to-End Pipeline](#end-to-end-pipeline)
- [Document Corpus](#document-corpus)
- [Official RGPV Source](#official-rgpv-source)
- [Document Ingestion](#document-ingestion)
- [Semantic Retrieval](#semantic-retrieval)
- [FAISS Vector Search](#faiss-vector-search)
- [Cross-Encoder Reranking](#cross-encoder-reranking)
- [Evidence Sufficiency](#evidence-sufficiency)
- [Three-State Detection](#three-state-detection)
- [Contradiction Detection](#contradiction-detection)
- [Planted Contradictions](#planted-contradictions)
- [Evaluation Dataset](#evaluation-dataset)
- [Evaluation Results](#evaluation-results)
- [Running the Evaluation](#running-the-evaluation)
- [Installation](#installation)
- [Preparing the Corpus](#preparing-the-corpus)
- [Running the Application](#running-the-application)
- [Example Questions](#example-questions)
- [User Interface](#user-interface)
- [Source Grounding](#source-grounding)
- [Why There Is No Generative LLM](#why-there-is-no-generative-llm)
- [Design Decisions](#design-decisions)
- [Limitations](#limitations)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Development History](#development-history)
- [Project Status](#project-status)
- [Future Improvements](#future-improvements)
- [Demo Instructions](#demo-instructions)
- [Links](#links)

---

# Why This Project Exists

Academic regulations are often difficult for students to navigate because:

- rules are spread across different documents,
- students ask questions in natural language rather than regulation terminology,
- some questions are not actually answered by the available documents,
- different documents can contain conflicting rules,
- and a system that confidently invents an answer can be worse than one that admits uncertainty.

For example, a student might ask:

> What attendance percentage do I need to be eligible for the examination?

If the corpus contains a clear rule, the system should return the relevant evidence.

If the corpus does not contain such a rule, the system should say:

> **NOT_COVERED**

If two applicable documents state different requirements, the system should say:

> **CONTRADICTION**

It should **not silently choose one rule**.

This makes the problem different from ordinary retrieval-based question answering.

The system must answer two separate questions:

1. **Can I find relevant information?**
2. **Does that information actually establish an answer?**

---

# Core Idea

Rulebook AI treats academic regulation QA as an **evidence and state-detection problem**, rather than simply a text-generation problem.

The system retrieves potentially relevant regulations, reranks them for question-specific relevance, checks whether the evidence is sufficient, and then classifies the question into one of three states.

```text
Student Question
       |
       v
Controlled Regulation Corpus
       |
       v
Document Ingestion
       |
       v
Semantic Retrieval
       |
       v
Cross-Encoder Reranking
       |
       v
Evidence Sufficiency Checks
       |
       v
Three-State Detection
       |
       +-------------------+-------------------+
       |                   |                   |
       v                   v                   v
 ANSWERABLE          NOT_COVERED       CONTRADICTION
       |                   |                   |
       v                   v                   v
Supporting          No invented        Conflicting
Evidence              answer            Evidence
```

The central design principle is:

> **Retrieving a related passage is not the same thing as proving that the corpus contains the answer.**

---

# Key Features

- **Three-state regulation QA**
  - `ANSWERABLE`
  - `NOT_COVERED`
  - `CONTRADICTION`

- **Semantic retrieval** using Sentence Transformers.

- **FAISS vector search** for efficient candidate retrieval.

- **Cross-encoder reranking** for question-specific evidence relevance.

- **Evidence sufficiency checks** to distinguish related passages from passages that actually answer the question.

- **Contradiction detection** for incompatible applicable claims.

- **Source provenance** including source, section, provision, and page metadata where available.

- **Controlled corpus** combining official regulation material and synthetic evaluation documents.

- **Hard unanswerable evaluation set** containing 25 plausible questions that the corpus does not genuinely establish.

- **Independent evaluation runner** that can be executed without the Streamlit UI.

- **Student-facing Streamlit interface** with separate presentations for all three states.

- **Contradiction comparison UI** that exposes conflicting evidence rather than silently selecting one rule.

---

# Three-State System

## `ANSWERABLE`

The corpus contains sufficient evidence to answer the student's question.

Example:

> What is the minimum CGPA required for the award of the degree?

If the regulation contains the relevant requirement, the system returns:

```text
ANSWERABLE
```

and displays the supporting rulebook evidence.

The evidence includes metadata such as the source, section, provision, and page where available.

---

## `NOT_COVERED`

The corpus does not establish the requested information.

The system does **not** use general university knowledge to fill the gap.

Example:

> What is the exact CGPA required to qualify for a university gold medal?

If the corpus discusses CGPA but does not specify a gold-medal requirement, the correct result is:

```text
NOT_COVERED
```

This distinction is important because a retrieval system may still find passages mentioning CGPA.

A passage can be:

```text
Relevant to the topic
```

without being:

```text
Sufficient to answer the question
```

Rulebook AI explicitly tries to make this distinction.

---

## `CONTRADICTION`

The corpus contains incompatible claims that are applicable to the student's question.

Example:

```text
Rule A:
Medical exemption attendance requirement = 60%

Rule B:
Medical exemption attendance requirement = 65%
```

For a question specifically asking about the medical exemption attendance requirement, the system returns:

```text
CONTRADICTION
```

Instead of selecting one passage and hiding the other, the UI presents the conflicting evidence.

This allows the student or reviewer to inspect the disagreement directly.

---

# Architecture

Rulebook AI consists of several stages.

```text
                    +----------------------+
                    |   Student Question   |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    |  Semantic Retrieval  |
                    |  all-MiniLM-L6-v2    |
                    |       + FAISS        |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    | Cross-Encoder        |
                    | Reranking             |
                    | ms-marco-MiniLM      |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    | Evidence Sufficiency |
                    | Checks                |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    | State Detection       |
                    +----------+-----------+
                               |
             +-----------------+-----------------+
             |                 |                 |
             v                 v                 v
       ANSWERABLE        NOT_COVERED      CONTRADICTION
             |                 |                 |
             v                 v                 v
       Rulebook          Refusal to        Conflicting
       Evidence           invent            Evidence
```

---

# End-to-End Pipeline

## Step 1 — Ingest Documents

The documents in the corpus are parsed and converted into structured chunks.

Each chunk retains provenance information.

```text
Document
├── Source
├── Section
├── Provision
├── Page
├── File Type
└── Text
```

---

## Step 2 — Retrieve Candidate Evidence

The student question is converted into an embedding using:

```text
all-MiniLM-L6-v2
```

The corpus chunks are also represented as embeddings.

FAISS is then used to retrieve the most semantically similar candidates.

---

## Step 3 — Rerank Candidates

The retrieved candidates are passed through:

```text
cross-encoder/ms-marco-MiniLM-L-6-v2
```

The cross-encoder evaluates the relationship between the question and each candidate passage.

This produces a more question-specific ranking than embedding similarity alone.

---

## Step 4 — Check Evidence Sufficiency

The system checks whether the retrieved evidence actually supports the requested information.

For example:

```text
Question:
What is the maximum credit load?

Retrieved:
Several passages about credits and registration.
```

Those passages may be related to the question but may not contain the requested maximum.

Therefore, the system should not automatically classify the question as `ANSWERABLE`.

---

## Step 5 — Detect Contradictions

The system checks whether multiple applicable evidence passages contain incompatible claims.

The contradiction detector considers the question context so that unrelated numbers from nearby regulations are not automatically treated as contradictions.

---

## Step 6 — Return a State

The final output is one of:

```text
ANSWERABLE
NOT_COVERED
CONTRADICTION
```

along with the supporting evidence or conflicting evidence where appropriate.

---

# Document Corpus

The project uses a controlled academic regulation corpus.

The corpus contains multiple document formats:

- Markdown
- Academic policy documents
- Examination policy
- Fee deadline table
- Official PDF

Current corpus:

```text
corpus/
├── academic_regulations.md
├── attendance_policy.md
├── examination_policy.md
├── fee_deadlines.md
└── rgpv_ordinance_4A_2013.pdf
```

The corpus is intentionally designed to contain more than **6,000 words**.

It combines official regulation material with synthetic material created specifically for evaluation.

The synthetic documents are used to:

- test retrieval across multiple documents,
- introduce controlled contradictions,
- create realistic adjacent questions,
- test refusal behavior,
- evaluate the three-state classifier.

---

# Official RGPV Source

The active official source is:

```text
RGPV Ordinance No. 4(A)

For candidates admitted in 1st year on and after July 2010

Credit Based Grading System

Amended up to June 2013
```

The active corpus uses this source as the official regulation document.

The older RGPV Ordinance No. 4 source was intentionally removed from the active corpus.

This avoids mixing different regulation versions and reduces ambiguity about which rules apply to a student's cohort.

The official regulation contains provisions covering areas such as:

- minimum CGPA requirements,
- passing grades,
- promotion requirements,
- failed-subject restrictions,
- improvement examinations,
- grading,
- maximum course duration,
- attendance,
- medium of instruction.

Examples of relevant provisions include:

```text
4.2  Minimum CGPA requirement for award of degree

4.3  Passing grade requirements

4.4  Restrictions based on failed subjects

4.5  Progression requirements

4.6  Improvement opportunity

5.6  Grading table

8.4  Maximum course duration

10.1 Attendance requirements

11.1 Medium of instruction
```

The ingestion pipeline preserves provision-level metadata where possible.

---

# Document Ingestion

Document ingestion is implemented in:

```text
backend/ingest.py
```

The ingestion pipeline supports both Markdown and PDF sources.

It extracts structured chunks containing:

- text,
- source filename,
- section,
- provision,
- page number where available,
- document type.

A chunk may look conceptually like:

```json
{
  "text": "4.2 For the award of degree minimum CGPA...",
  "source": "rgpv_ordinance_4A_2013.pdf",
  "page": 3,
  "section": "4.0 PROMOTION TO HIGHER SEMESTER AND YEAR",
  "provision": "4.2",
  "file_type": "pdf"
}
```

The ingestion process attempts to preserve regulation provisions rather than arbitrarily splitting rules.

---

# Semantic Retrieval

Semantic retrieval is implemented in:

```text
backend/retrieval.py
```

The project uses:

```text
all-MiniLM-L6-v2
```

from Sentence Transformers.

The retrieval process is:

```text
Question
   |
   v
Question Embedding
   |
   v
FAISS Similarity Search
   |
   v
Candidate Evidence
```

The corpus chunks are embedded and stored in a FAISS index.

The retrieval stage intentionally obtains a larger candidate set before reranking so that the cross-encoder has multiple potentially relevant passages to compare.

---

# FAISS Vector Search

The project uses:

```text
FAISS IndexFlatIP
```

with normalized embeddings.

The normalized vectors allow inner product to correspond to cosine similarity.

Conceptually:

```text
Question
   |
   v
Embedding Vector
   |
   v
Compare Against Corpus Vectors
   |
   v
Top-K Candidate Chunks
```

FAISS is used for efficient similarity search over the processed regulation corpus.

---

# Cross-Encoder Reranking

Reranking is implemented in:

```text
backend/reranker.py
```

The project uses:

```text
cross-encoder/ms-marco-MiniLM-L-6-v2
```

The cross-encoder evaluates:

```text
(question, passage)
```

pairs.

Conceptually:

```text
Question
   |
   +---- Passage A -> relevance score
   |
   +---- Passage B -> relevance score
   |
   +---- Passage C -> relevance score
   |
   +---- Passage D -> relevance score
```

The candidates are then sorted by their reranking scores.

The reranker score is an internal relevance score and is **not treated as a probability**.

---

# Evidence Sufficiency

One of the most important components of the project is evidence sufficiency.

A common failure mode in retrieval-based QA systems is:

```text
Relevant passage found
        |
        v
Assume answer exists
        |
        v
ANSWERABLE
```

Rulebook AI instead attempts:

```text
Relevant passage found
        |
        v
Does it establish the requested fact?
        |
        +---- YES -> ANSWERABLE
        |
        +---- NO  -> NOT_COVERED
```

This is particularly important for hard unanswerable questions.

For example:

> How many revaluation requests may a student submit in one semester?

The corpus may contain examination rules and revaluation-related language without actually establishing a maximum number.

The system should therefore avoid treating the mere presence of related terminology as proof of answerability.

---

# Three-State Detection

The main state detection logic is implemented in:

```text
backend/state_detector.py
```

The detector combines:

1. semantic retrieval,
2. cross-encoder reranking,
3. explicit absence detection,
4. contradiction detection,
5. evidence sufficiency checks,
6. relevance thresholds.

The conceptual decision flow is:

```text
                 Retrieved Evidence
                         |
                         v
               Is the question explicitly
               outside the corpus?
                    /          \
                  YES           NO
                   |             |
                   v             v
             NOT_COVERED   Check evidence
                                  |
                                  v
                         Are there applicable
                         conflicting claims?
                            /          \
                          YES           NO
                           |             |
                           v             v
                    CONTRADICTION   Is evidence
                                    sufficient?
                                    /       \
                                  YES        NO
                                   |          |
                                   v          v
                              ANSWERABLE  NOT_COVERED
```

The implementation avoids hardcoding individual evaluation question IDs.

The goal is for the same logic to work on unseen questions.

---

# Contradiction Detection

Contradiction detection is one of the defining features of Rulebook AI.

A contradiction is not simply the presence of two different numbers.

The system first considers whether the retrieved claims are applicable to the question.

For example:

```text
Question:
What attendance percentage applies to a medical exemption?
```

If the corpus contains:

```text
Medical exemption -> 60%
Medical exemption -> 65%
```

the claims are relevant to the same requested rule and should produce:

```text
CONTRADICTION
```

The system should not treat unrelated values as contradictions merely because they appear in the same retrieval result.

---

# Planted Contradictions

The repository contains exactly three intentionally planted contradictions.

They are documented in:

```text
docs/contradictions.md
```

## C001 — Medical Attendance

Two synthetic policy sections provide different attendance requirements for medical exemption.

```text
60%
vs.
65%
```

---

## C002 — Improvement Subjects

Two synthetic documents specify different maximum numbers of subjects for improvement.

```text
3 subjects
vs.
2 subjects
```

---

## C003 — Tuition Deadline

The synthetic fee document contains two different tuition deadlines.

```text
15 July
vs.
31 July
```

The contradiction detector should surface both claims rather than silently choosing one.

The contradiction documentation identifies:

- contradiction ID,
- source,
- section/provision,
- conflicting values,
- explanation,
- intended evaluation behavior.

---

# Evaluation Dataset

The current evaluation dataset contains:

| Category | Questions |
|---|---:|
| `ANSWERABLE` | 20 |
| `NOT_COVERED` | 25 |
| `CONTRADICTION` | 6 |
| **Total** | **51** |

The evaluation data is stored in:

```text
eval/questions.json
```

The 25 `NOT_COVERED` questions are particularly important.

They are intentionally designed as plausible student questions that the corpus does not genuinely answer.

Examples include questions about:

- university gold medal requirements,
- compensation for cancelled examinations,
- revaluation request limits,
- maximum semester credit loads,
- special examination situations.

The purpose is to test whether the system can resist the temptation to answer every semantically related question.

---

# Evaluation Results

The current measured baseline is:

```text
Overall:          50/51  (98.0%)

ANSWERABLE:       19/20 (95.0%)

NOT_COVERED:      25/25 (100.0%)

CONTRADICTION:     6/6  (100.0%)
```

Summary:

| State | Correct | Total | Accuracy |
|---|---:|---:|---:|
| `ANSWERABLE` | 19 | 20 | 95.0% |
| `NOT_COVERED` | 25 | 25 | 100.0% |
| `CONTRADICTION` | 6 | 6 | 100.0% |
| **Overall** | **50** | **51** | **98.0%** |

The system correctly identifies:

```text
25/25
```

of the hard `NOT_COVERED` questions.

This clears the important evaluation target of:

```text
19/25
```

The contradiction set currently achieves:

```text
6/6
```

---

# Running the Evaluation

From the repository root:

```bash
python eval/run_eval.py
```

The evaluator:

1. loads the evaluation questions,
2. initializes the state detector,
3. evaluates every question,
4. compares predicted and expected states,
5. prints per-question results,
6. prints overall and per-state accuracy.

Example:

```text
Evaluating 51 questions...

A01: expected=ANSWERABLE      predicted=ANSWERABLE      OK
A02: expected=ANSWERABLE      predicted=ANSWERABLE      OK
...
U01: expected=NOT_COVERED     predicted=NOT_COVERED     OK
...
C01: expected=CONTRADICTION   predicted=CONTRADICTION   OK

============================================================
EVALUATION SUMMARY
============================================================
Overall: 50/51 (98.0%)
ANSWERABLE: 19/20 (95.0%)
NOT_COVERED: 25/25 (100.0%)
CONTRADICTION: 6/6 (100.0%)

```

The evaluation script is intended to be runnable by a reviewer without requiring the Streamlit interface.

---

# Installation

## Requirements

Recommended:

```text
Python 3.10+
```

The project dependencies are listed in:

```text
requirements.txt
```

Current dependencies:

```text
PyMuPDF==1.26.4
sentence-transformers==5.1.0
faiss-cpu==1.12.0
streamlit==1.63.0
```

---

# Clone the Repository

```bash
git clone https://github.com/VishuddhaJatale/rulebook-ai.git
cd rulebook-ai
```

---

# Create a Virtual Environment

## Windows

```bash
python -m venv .venv
```

Activate it:

```bash
.venv\Scripts\activate
```

---

## Linux / macOS

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

---

# Install Dependencies

```bash
pip install -r requirements.txt
```

The Sentence Transformer models are downloaded automatically when they are first loaded.

The first startup may take longer because model files need to be downloaded and initialized.

---

# Preparing the Corpus

The source documents are located in:

```text
corpus/
```

The ingestion pipeline converts these documents into structured processed chunks.

Run:

```bash
python backend/ingest.py
```

This prepares the processed corpus used by the retrieval system.

The generated processed data is stored under:

```text
data/processed/
```

Make sure the processed corpus required by the application is available before starting the application.

---

# Running the Application

Start Streamlit from the repository root:

```bash
streamlit run app.py
```

The application will normally be available at:

```text
http://localhost:8501
```

Open the URL in a browser and enter an academic regulation question.

---

# Example Questions

## Example 1 — ANSWERABLE

Question:

```text
What is the minimum CGPA required for the award of the degree?
```

Expected state:

```text
ANSWERABLE
```

The application displays the relevant regulation evidence.

---

## Example 2 — NOT_COVERED

Question:

```text
What is the exact CGPA required to qualify for a university gold medal?
```

Expected state:

```text
NOT_COVERED
```

The corpus does not establish a gold-medal CGPA requirement.

---

## Example 3 — CONTRADICTION

Question:

```text
What attendance percentage applies to a student seeking medical exemption?
```

Expected state:

```text
CONTRADICTION
```

The UI presents the conflicting claims instead of choosing one silently.

---

# Source Grounding

Rulebook AI is designed around the following principle:

```text
Question
   |
   v
Retrieved Evidence
   |
   v
State Decision
   |
   v
User-visible Result
```

The application does not intentionally use general knowledge about universities to fill gaps in the corpus.

If the information is not established by the available documents, the correct behavior is:

```text
NOT_COVERED
```

rather than an inferred answer.

---

# Why There Is No Generative LLM

The current implementation does **not** use a generative LLM.

Instead, the core pipeline is:

```text
Sentence Transformer
        +
FAISS
        +
Cross Encoder
        +
Evidence / State Detection
```

This is intentional.

The main challenge in this project is not generating fluent text.

The main challenge is determining:

> **Does the corpus actually support this answer?**

and:

> **Does the corpus contain conflicting applicable claims?**

A generative model could produce a convincing answer even when the corpus does not support it.

That would work against the project's primary goal.

Therefore, the current implementation prioritizes:

- evidence retrieval,
- traceability,
- refusal when unsupported,
- contradiction detection,
- reproducible evaluation.

A future version could add a constrained answer-summarization layer after evidence selection, but generation should never override the evidence/state decision.

---

# Design Decisions

## 1. Why Three States?

A binary:

```text
Answer / No Answer
```

classification is insufficient for a regulation assistant.

The corpus can contain enough information to answer, contain no answer, or contain conflicting answers.

Therefore:

```text
ANSWERABLE
NOT_COVERED
CONTRADICTION
```

are treated as separate states.

---

## 2. Why Explicit `NOT_COVERED`?

A regulation assistant should not be rewarded for producing an answer when the source does not establish one.

Explicit refusal prevents unsupported claims from appearing authoritative.

---

## 3. Why Contradiction Detection?

If two applicable rules disagree, selecting one based only on retrieval rank can hide an important problem.

The system instead exposes the conflict.

---

## 4. Why Semantic Retrieval?

Students may ask questions using terminology different from the wording in the regulation.

Semantic embeddings help bridge that language gap.

---

## 5. Why Cross-Encoder Reranking?

Embedding retrieval provides candidate passages efficiently, but semantic similarity alone can rank broadly related passages above passages that specifically answer the question.

The cross-encoder provides a second, more question-specific relevance stage.

---

## 6. Why Evidence Sufficiency?

A passage can be related to a question without containing the requested fact.

Therefore:

```text
Similarity != Answerability
```

Evidence sufficiency is used to reduce this failure mode.

---

## 7. Why Remove the Older RGPV Regulation?

The older regulation was removed from the active corpus to avoid mixing different regulation versions and creating unnecessary ambiguity about which rules apply.

The active corpus focuses on the selected RGPV Ordinance 4(A) source and the synthetic evaluation documents.

---

## 8. Why No LLM?

The primary objective is checkable evidence and reliable state detection.

A generative model is not required to retrieve, compare, and expose the relevant regulation passages.

Generation may be added later as a constrained presentation layer, but it should not determine whether evidence exists.

---

# Limitations

The current system is a focused prototype rather than a complete production regulation platform.

## 1. Contradiction Reasoning Is Limited

The contradiction detector focuses on detectable conflicting claims and contextual relevance.

It is not a general-purpose formal logic engine capable of proving every possible regulatory inconsistency.

---

## 2. The Corpus Is Controlled

The system only knows what is contained in the supplied corpus.

This is intentional for the evaluation, but it means questions requiring external university information may correctly return:

```text
NOT_COVERED
```

---

## 3. Regulation Version Matters

The active official source is the RGPV Ordinance 4(A) amended through June 2013.

Real-world deployment would require stronger handling of:

- admission cohort,
- academic year,
- programme,
- regulation version,
- amendment date,
- supersession,
- institutional notices.

---

## 4. Retrieval Quality Matters

The state detector can only reason over evidence that reaches its candidate set.

Therefore:

```text
Retrieval quality
       |
       v
Evidence quality
       |
       v
State detection quality
```

The semantic retriever and cross-encoder reranker are therefore important parts of the overall system.

---

## 5. Current Answers Are Evidence-First

For `ANSWERABLE` questions, the current application surfaces the strongest retrieved rulebook evidence rather than generating a fully paraphrased answer with a generative model.

This is a deliberate tradeoff:

```text
Traceability > Fluency
```

for the current prototype.

---

# Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python |
| User Interface | Streamlit |
| PDF Processing | PyMuPDF |
| Embedding Framework | Sentence Transformers |
| Embedding Model | `all-MiniLM-L6-v2` |
| Vector Search | FAISS |
| Vector Index | `IndexFlatIP` |
| Retrieval Similarity | Normalized Inner Product / Cosine Similarity |
| Reranking | Cross Encoder |
| Reranker Model | `ms-marco-MiniLM-L-6-v2` |
| Evaluation | Custom Python Evaluation Runner |
| Corpus Formats | Markdown + PDF |
| Version Control | Git / GitHub |

---

# Project Structure

```text
rulebook-ai/
│
├── app.py
│
├── corpus/
│   ├── academic_regulations.md
│   ├── attendance_policy.md
│   ├── examination_policy.md
│   ├── fee_deadlines.md
│   └── rgpv_ordinance_4A_2013.pdf
│
├── backend/
│   ├── ingest.py
│   ├── retrieval.py
│   ├── reranker.py
│   └── state_detector.py
│
├── data/
│   └── processed/
│       └── chunks.json
│
├── docs/
│   ├── contradictions.md
│   └── screenshots/
│       ├── answerable.png
│       ├── not-covered.png
│       └── contradiction.png
│
├── eval/
│   ├── README.md
│   ├── evaluation_spec.json
│   ├── questions.json
│   ├── run_eval.py
│   └── summary.json
│
├── requirements.txt
├── README.md
└── .gitignore
```

---

# File Responsibilities

## `app.py`

The student-facing Streamlit application.

Responsibilities include:

- accepting student questions,
- invoking the state detector,
- displaying the detected state,
- displaying supporting evidence,
- displaying source metadata,
- showing contradiction comparisons,
- providing expandable source passages.

---

## `backend/ingest.py`

Responsible for document processing.

Responsibilities include:

- reading Markdown documents,
- reading PDF documents,
- extracting text,
- detecting sections,
- detecting provisions,
- preserving page information,
- creating structured chunks.

---

## `backend/retrieval.py`

Responsible for semantic retrieval.

Responsibilities include:

- loading the embedding model,
- loading processed chunks,
- generating embeddings,
- building the FAISS index,
- retrieving semantically similar passages.

---

## `backend/reranker.py`

Responsible for evidence reranking.

Responsibilities include:

- receiving retrieved candidates,
- scoring question/passage pairs,
- sorting candidates,
- returning higher-quality evidence.

---

## `backend/state_detector.py`

Responsible for the final three-state decision.

Responsibilities include:

- retrieval,
- reranking,
- absence detection,
- contradiction detection,
- evidence sufficiency,
- state classification.

---

## `eval/run_eval.py`

Independent evaluation runner.

It evaluates the state detector against the labeled evaluation dataset.

---

## `eval/questions.json`

Contains the labeled evaluation questions and expected states.

---

## `eval/evaluation_spec.json`

Defines the evaluation categories and expected evaluation behavior.

---

## `eval/summary.json`

Contains the recorded evaluation summary.

---

## `docs/contradictions.md`

Documents the intentionally planted contradictions.

---

# Development History

The project was developed incrementally rather than as a single final implementation.

The major development stages were:

```text
Official Source Documents
        |
        v
Synthetic Regulation Corpus
        |
        v
Evaluation Question Set
        |
        v
Contradiction Ground Truth
        |
        v
Document Ingestion
        |
        v
Semantic Retrieval
        |
        v
Cross-Encoder Reranking
        |
        v
Three-State Detection
        |
        v
Evaluation Runner
        |
        v
Student-Facing Streamlit UI
```

The Git history preserves these implementation stages through separate commits.

The incremental history makes it possible to inspect how the system evolved from corpus construction to retrieval, reranking, state detection, evaluation, and finally the user interface.

---

# Evaluation Philosophy

A regulation QA system should not be judged only by how many questions it can answer.

It should also be judged by whether it knows when **not** to answer.

Therefore, Rulebook AI explicitly measures:

```text
ANSWERABLE
NOT_COVERED
CONTRADICTION
```

A system that answers every question but fabricates unsupported information is not considered reliable.

The evaluation therefore treats **calibrated refusal** and **contradiction detection** as first-class capabilities.

---

# Project Status

Current implementation includes:

- [x] Controlled academic regulation corpus
- [x] Official RGPV regulation source
- [x] Synthetic regulation documents
- [x] 6,000+ word corpus
- [x] Multiple corpus formats
- [x] Three planted contradictions
- [x] Contradiction documentation
- [x] 25 hard `NOT_COVERED` questions
- [x] 51-question evaluation set
- [x] Markdown ingestion
- [x] PDF ingestion
- [x] Structured source metadata
- [x] Provision-level metadata
- [x] Semantic retrieval
- [x] FAISS similarity search
- [x] Cross-encoder reranking
- [x] Evidence sufficiency checks
- [x] Three-state detection
- [x] Evaluation runner
- [x] Student-facing Streamlit UI
- [x] Evidence/source display
- [x] Contradiction comparison UI
- [x] Public GitHub repository
- [ ] Public deployment
- [ ] Final demo video

Update the final two items once deployment and the demo video are completed.

---

# Future Improvements

## Regulation Version Awareness

Support multiple regulation versions while explicitly selecting the applicable version based on:

- admission year,
- programme,
- regulation date,
- amendment history.

---

## Better Contradiction Reasoning

Expand contradiction detection beyond simple numeric/date conflicts to handle:

- conditional rules,
- exceptions,
- superseding provisions,
- hierarchical regulations,
- cross-document precedence.

---

## Constrained Answer Generation

Add an optional generation layer that summarizes only the already-selected evidence.

The architecture would remain:

```text
Question
   |
   v
Retrieval
   |
   v
Reranking
   |
   v
State Detection
   |
   +---- NOT_COVERED
   |
   +---- CONTRADICTION
   |
   +---- ANSWERABLE
              |
              v
       Evidence-grounded
       answer synthesis
```

The generator would never be allowed to override the state detector or introduce unsupported claims.

---

## Larger Evaluation Set

Future versions could include:

- more answerable questions,
- more hard unanswerables,
- more contradiction types,
- adversarial questions,
- cohort-specific questions,
- paraphrased questions.

---

## Regression Testing

Every future retrieval or state-detection change could automatically run the complete evaluation suite.

This would prevent improvements for one question category from silently reducing performance elsewhere.

---

## Improved Provenance

Future versions could provide:

- exact document links,
- page-level references,
- highlighted source text,
- regulation version,
- amendment information.

---

# Demo Instructions

A recommended demonstration should show all three states.

## 1. Start the application

```bash
streamlit run app.py
```

---

## 2. Demonstrate `ANSWERABLE`

Ask:

```text
What is the minimum CGPA required for the award of the degree?
```

Show:

- the `ANSWERABLE` state,
- the evidence,
- source metadata.

---

## 3. Demonstrate `NOT_COVERED`

Ask:

```text
What is the exact CGPA required to qualify for a university gold medal?
```

Show:

- the `NOT_COVERED` state,
- the refusal to invent an answer.

---

## 4. Demonstrate `CONTRADICTION`

Ask:

```text
What attendance percentage applies to a student seeking medical exemption?
```

Show:

- the `CONTRADICTION` state,
- both conflicting claims,
- their source metadata,
- the comparison UI.

This demonstrates the core behavior of the project in a short sequence.

---

# Links

## Live Demo

https://rulebook-ai.streamlit.app/

## Contradiction Documentation

```text
docs/contradictions.md
```

## Evaluation Documentation

```text
eval/README.md
```

---

# Final Summary

Rulebook AI is designed around a simple but important principle:

> **A trustworthy regulation assistant should know when the rulebook answers a question, when it does not, and when the rulebook disagrees with itself.**

The system therefore does not treat every retrieved passage as an answer.

Instead, it combines:

```text
Semantic Retrieval
        +
FAISS
        +
Cross-Encoder Reranking
        +
Evidence Sufficiency
        +
Contradiction Detection
        +
Three-State Detection
        =
Checkable Regulation QA
```

with the three possible outcomes:

```text
ANSWERABLE
NOT_COVERED
CONTRADICTION
```

This makes the project **checkable, evidence-grounded, explicitly evaluated, and designed to avoid unsupported answers**.
