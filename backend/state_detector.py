from pathlib import Path
import json
import re

from .reranker import EvidenceReranker


ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_FILE = ROOT / "eval" / "questions.json"


ABSENCE_PATTERNS = [
    r"\bdoes not specify\b",
    r"\bdoes not state\b",
    r"\bnot specified\b",
    r"\bnot provided\b",
    r"\bno rule\b",
    r"\bnot covered\b",
    r"\bdoes not define\b",
    r"\bnot stated\b",
]


class StateDetector:

    def __init__(
        self,
        retrieval_top_k=30,
        evidence_top_k=8,
        answerable_threshold=0.0,
    ):

        self.reranker = EvidenceReranker()

        self.retrieval_top_k = retrieval_top_k
        self.evidence_top_k = evidence_top_k
        self.answerable_threshold = answerable_threshold

    # =============================================================
    # RETRIEVAL
    # =============================================================

    def retrieve_evidence(self, question):

        return self.reranker.rerank(
            question,
            top_k_retrieval=self.retrieval_top_k,
            top_k_final=self.evidence_top_k,
        )

    # =============================================================
    # EXPLICIT ABSENCE
    # =============================================================

    def contains_explicit_absence(self, text):

        text = text.lower()

        for pattern in ABSENCE_PATTERNS:

            if re.search(pattern, text):
                return True

        return False

    # =============================================================
    # QUESTION TYPE
    # =============================================================

    def is_value_question(self, question):

        q = question.lower()

        patterns = [
            r"\bhow much\b",
            r"\bhow many\b",
            r"\bwhat percentage\b",
            r"\bwhat percent\b",
            r"\bwhat amount\b",
            r"\bwhat number\b",
            r"\bhow long\b",
            r"\bhow many days\b",
            r"\bhow many marks\b",
            r"\bhow many credits\b",
            r"\bexact fee\b",
            r"\bexact amount\b",
            r"\bexact cgpa\b",
            r"\bmaximum number\b",
            r"\bminimum number\b",
        ]

        return any(
            re.search(pattern, q)
            for pattern in patterns
        )

    # =============================================================
    # VALUE EXTRACTION
    # =============================================================

    def value_supported(self, question, text):

        q = question.lower()
        text = text.lower()

        # ---------------------------------------------------------
        # Percentage
        # ---------------------------------------------------------

        if "percentage" in q or "percent" in q:

            return bool(
                re.search(
                    r"\b\d+(?:\.\d+)?\s*(?:percent|%)\b",
                    text,
                )
            )

        # ---------------------------------------------------------
        # Marks
        # ---------------------------------------------------------

        if "marks" in q:

            return bool(
                re.search(
                    r"\b\d+(?:\.\d+)?\s*marks?\b",
                    text,
                )
            )

        # ---------------------------------------------------------
        # Days / duration
        # ---------------------------------------------------------

        if "days" in q or "how long" in q:

            return bool(
                re.search(
                    r"\b\d+(?:\.\d+)?\s*"
                    r"(?:days?|weeks?|months?|years?)\b",
                    text,
                )
            )

        # ---------------------------------------------------------
        # Credits
        # ---------------------------------------------------------

        if "credit" in q:

            return bool(
                re.search(
                    r"\b\d+(?:\.\d+)?\s*credits?\b",
                    text,
                )
            )

        # ---------------------------------------------------------
        # CGPA
        # ---------------------------------------------------------

        if "cgpa" in q:

            return bool(
                re.search(
                    r"\bcgpa\b.{0,80}\b\d+(?:\.\d+)?\b"
                    r"|"
                    r"\b\d+(?:\.\d+)?\b.{0,80}\bcgpa\b",
                    text,
                    flags=re.IGNORECASE | re.DOTALL,
                )
            )

        # ---------------------------------------------------------
        # Subject count
        # ---------------------------------------------------------

        if "subject" in q:

            return bool(
                re.search(
                    r"\b(?:maximum of\s+)?"
                    r"(?:\d+|one|two|three|four|five|six|seven|eight)"
                    r"\s+subjects?\b",
                    text,
                    flags=re.IGNORECASE,
                )
            )

        # ---------------------------------------------------------
        # Money
        # ---------------------------------------------------------

        if any(
            word in q
            for word in [
                "fee",
                "amount",
                "cost",
                "charge",
                "compensation",
            ]
        ):

            return bool(
                re.search(
                    r"(?:₹|rs\.?|inr)\s*[\d,]+"
                    r"|"
                    r"\b\d[\d,]*(?:\.\d+)?\s*"
                    r"(?:rupees?|rs\.?|inr)\b",
                    text,
                    flags=re.IGNORECASE,
                )
            )

        # ---------------------------------------------------------
        # Date
        # ---------------------------------------------------------

        if (
            "deadline" in q
            or "due date" in q
            or "date" in q
        ):

            return bool(
                re.search(
                    r"\b\d{1,2}\s+"
                    r"(?:january|february|march|april|may|june|"
                    r"july|august|september|october|november|december)\b",
                    text,
                    flags=re.IGNORECASE,
                )
            )

        return True

    # =============================================================
    # CONTRADICTION DETECTION
    # =============================================================

    def detect_contradiction(self, question, evidence):

        claims = []

        for item in evidence:

            text = item["text"]

            # -----------------------------------------------------
            # Percentages
            # -----------------------------------------------------

            percentages = re.findall(
                r"\b(\d+(?:\.\d+)?)\s*(?:percent|%)\b",
                text,
                flags=re.IGNORECASE,
            )

            for value in percentages:

                claims.append({
                    "type": "percentage",
                    "value": float(value),
                    "evidence": item,
                })

            # -----------------------------------------------------
            # Subject counts
            # -----------------------------------------------------

            subject_counts = re.findall(
                r"\b(?:maximum of\s+)?"
                r"(\d+|one|two|three|four|five|six|seven|eight)"
                r"\s+subjects?\b",
                text,
                flags=re.IGNORECASE,
            )

            word_to_number = {
                "one": 1,
                "two": 2,
                "three": 3,
                "four": 4,
                "five": 5,
                "six": 6,
                "seven": 7,
                "eight": 8,
            }

            for value in subject_counts:

                number = (
                    int(value)
                    if value.isdigit()
                    else word_to_number[value.lower()]
                )

                claims.append({
                    "type": "subject_count",
                    "value": number,
                    "evidence": item,
                })

            # -----------------------------------------------------
            # Dates
            # -----------------------------------------------------

            dates = re.findall(
                r"\b(\d{1,2})\s+"
                r"(January|February|March|April|May|June|July|"
                r"August|September|October|November|December)\b",
                text,
                flags=re.IGNORECASE,
            )

            for day, month in dates:

                claims.append({
                    "type": "date",
                    "value": (
                        int(day),
                        month.lower(),
                    ),
                    "evidence": item,
                })

        # =========================================================
        # Compare claims
        # =========================================================

        for i in range(len(claims)):

            for j in range(i + 1, len(claims)):

                first = claims[i]
                second = claims[j]

                if first["type"] != second["type"]:
                    continue

                if first["value"] == second["value"]:
                    continue

                first_text = first["evidence"]["text"].lower()
                second_text = second["evidence"]["text"].lower()

                # -------------------------------------------------
                # Determine the concepts represented by each claim.
                #
                # We deliberately use the QUESTION to determine
                # which type of claim is relevant, rather than
                # hardcoding U01/U02/etc.
                # -------------------------------------------------

                q = question.lower()

                if first["type"] == "percentage":

                    if not (
                        "percentage" in q
                        or "percent" in q
                        or "attendance" in q
                    ):
                        continue

                elif first["type"] == "subject_count":

                    if not (
                        "subject" in q
                        or "improvement" in q
                    ):
                        continue

                elif first["type"] == "date":

                    if not (
                        "deadline" in q
                        or "due date" in q
                        or "date" in q
                    ):
                        continue

                # -------------------------------------------------
                # Evidence must be genuinely related to the
                # question. We use the rerank score rather than
                # brittle lexical overlap.
                # -------------------------------------------------

                first_score = first["evidence"]["rerank_score"]
                second_score = second["evidence"]["rerank_score"]

                if (
                    first_score < -1.5
                    or second_score < -1.5
                ):
                    continue

                # -------------------------------------------------
                # The two passages must share meaningful vocabulary.
                # -------------------------------------------------

                question_words = set(
                    re.findall(
                        r"[a-z]+",
                        q,
                    )
                )

                first_words = set(
                    re.findall(
                        r"[a-z]+",
                        first_text,
                    )
                )

                second_words = set(
                    re.findall(
                        r"[a-z]+",
                        second_text,
                    )
                )

                shared = (
                    first_words
                    & second_words
                    & question_words
                )

                if len(shared) < 1:
                    continue

                return {
                    "state": "CONTRADICTION",
                    "reason": (
                        "The corpus contains conflicting claims "
                        "about the same rule."
                    ),
                    "conflicts": [
                        first["evidence"],
                        second["evidence"],
                    ],
                }

        return None

    # =============================================================
    # FINAL STATE DETECTION
    # =============================================================

    def detect(self, question):

        evidence = self.retrieve_evidence(question)

        if not evidence:

            return {
                "state": "NOT_COVERED",
                "reason": "No relevant evidence was retrieved.",
                "evidence": [],
            }

        best = evidence[0]

        # ---------------------------------------------------------
        # 1. Explicit statement that information is absent
        # ---------------------------------------------------------

        if self.contains_explicit_absence(
            best["text"]
        ):

            return {
                "state": "NOT_COVERED",
                "reason": (
                    "The most relevant evidence explicitly indicates "
                    "that the requested detail is not specified."
                ),
                "evidence": evidence,
            }

        # ---------------------------------------------------------
        # 2. Contradiction
        #
        # Check this before the normal answerability decision.
        # ---------------------------------------------------------

        contradiction = self.detect_contradiction(
            question,
            evidence,
        )

        if contradiction:

            contradiction["evidence"] = evidence

            return contradiction

        # ---------------------------------------------------------
        # 3. Value sufficiency
        #
        # Only apply this stricter check when the question explicitly
        # asks for a measurable value.
        # ---------------------------------------------------------

        if self.is_value_question(question):

            value_found = False

            for item in evidence:

                if self.value_supported(
                    question,
                    item["text"],
                ):

                    value_found = True
                    break

            if not value_found:

                return {
                    "state": "NOT_COVERED",
                    "reason": (
                        "Relevant evidence was retrieved, but "
                        "it does not establish the specific "
                        "value requested."
                    ),
                    "evidence": evidence,
                }

        # ---------------------------------------------------------
        # 4. Ordinary semantic relevance
        #
        # Preserve the behavior that gave us 19/20 ANSWERABLE.
        # ---------------------------------------------------------

        if best["rerank_score"] < self.answerable_threshold:

            return {
                "state": "NOT_COVERED",
                "reason": (
                    "Retrieved evidence does not meet "
                    "the relevance threshold."
                ),
                "evidence": evidence,
            }

        return {
            "state": "ANSWERABLE",
            "reason": (
                "The retrieved evidence supports the "
                "question."
            ),
            "evidence": evidence,
        }


def load_questions():

    with QUESTIONS_FILE.open(
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


def main():

    detector = StateDetector()

    print()
    print("Rulebook AI — State Detection Test")
    print("-----------------------------------")

    while True:

        question = input(
            "\nAsk a question (or type 'exit'): "
        )

        if question.lower() == "exit":
            break

        result = detector.detect(question)

        print()
        print(f"State: {result['state']}")
        print(f"Reason: {result['reason']}")

        print("\nEvidence:\n")

        for i, item in enumerate(
            result["evidence"],
            start=1,
        ):

            print(
                f"[{i}] "
                f"Rerank: "
                f"{item['rerank_score']:.4f}"
            )

            print(f"Source: {item['source']}")
            print(f"Page: {item['page']}")
            print(f"Section: {item['section']}")
            print(f"Provision: {item['provision']}")
            print(f"Chunk: {item['chunk_id']}")

            print(
                f"Text: {item['text'][:500]}"
            )

            print("-" * 70)


if __name__ == "__main__":
    main()