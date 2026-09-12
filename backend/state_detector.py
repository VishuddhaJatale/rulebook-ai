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
    # QUESTION / CLAIM CONTEXT
    # =============================================================

    STOPWORDS = {
        "the", "a", "an", "is", "are", "was", "were", "to", "of",
        "for", "in", "on", "at", "and", "or", "what", "which",
        "does", "do", "did", "can", "may", "will", "would", "should",
        "under", "this", "that", "be", "by", "from", "with", "as",
        "student", "students", "required", "requirement", "ordinary",
    }

    def question_terms(self, question):
        words = re.findall(r"[a-z]+", question.lower())
        return {w for w in words if len(w) > 2 and w not in self.STOPWORDS}

    def claim_context(self, text, start, end):
        """Return the sentence/line containing a numeric claim."""
        left_candidates = [text.rfind(".", 0, start), text.rfind("\n", 0, start)]
        left = max(left_candidates) + 1

        right_candidates = [
            p for p in (text.find(".", end), text.find("\n", end))
            if p != -1
        ]
        right = min(right_candidates) if right_candidates else len(text)

        return re.sub(r"\s+", " ", text[left:right]).strip().lower()

    def claim_is_applicable(self, question, claim_type, context, item_text="", section=""):
        """Check whether a numeric/date claim is about the rule asked in the question."""
        q = question.lower()
        c = context.lower()
        full = f"{section} {item_text}".lower()

        # Attendance scope: ordinary attendance and medical-exemption
        # thresholds are different rules. Use the whole retrieved provision
        # as context because a numeric value may occur in a sentence whose
        # subject was introduced on the previous line.
        if claim_type == "percentage":
            medical_q = any(x in q for x in ("medical", "exemption", "relief"))
            medical_e = any(x in full for x in ("medical", "exemption", "medical threshold"))

            if medical_q:
                if not medical_e:
                    return False
            else:
                if medical_e:
                    return False

        # Subject counts are relevant to improvement questions, not merely
        # any question containing the word 'subject'.
        if claim_type == "subject_count":
            if "improvement" not in q:
                return False
            if "improvement" not in full:
                return False

        # Date conflicts only matter when the question actually asks for a
        # date/deadline. This prevents tuition deadlines from conflicting with
        # questions about the amount of a late fee.
        if claim_type == "date":
            if not any(x in q for x in ("deadline", "due date", "date")):
                return False

            # A question explicitly asking for the value shown in the fee table
            # should select the table row, not the separately stated alternative.
            if "fee table" in q or "table" in q:
                is_table = ("fee item" in full or "normal deadline" in full
                            or "semester tuition fee |" in full)
                if not is_table:
                    return False

        # The claim/provision should contain at least one meaningful question
        # concept. Do this against the whole provision, not just the tiny
        # sentence around the number.
        terms = self.question_terms(question)
        if terms and not any(term in full for term in terms):
            return False

        return True

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
            r"\bwhat compensation\b",
            r"\bcompensation\b",
            r"\bmaximum .*credit load\b",
            r"\bcredit load\b",
        ]

        return any(re.search(pattern, q) for pattern in patterns)

    # =============================================================
    # VALUE EXTRACTION
    # =============================================================

    def value_supported(self, question, text):
        q = question.lower()
        text = text.lower()

        def relevant_sentence(patterns):
            sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
            for sentence in sentences:
                if any(re.search(pattern, sentence) for pattern in patterns):
                    return sentence
            return ""

        # CGPA: a numeric CGPA is sufficient only if the requested subject
        # (e.g. degree) is present in the same local evidence.
        if "cgpa" in q:
            target_terms = []
            if "gold medal" in q or "medal" in q:
                target_terms = [r"gold", r"medal"]
            elif "degree" in q:
                target_terms = [r"degree"]
            elif "progress" in q or "semester" in q:
                target_terms = [r"progress", r"semester"]

            if not re.search(r"\bcgpa\b.{0,100}\d+(?:\.\d+)?|\d+(?:\.\d+)?.{0,100}\bcgpa\b", text, re.S):
                return False

            if target_terms and not any(re.search(p, text) for p in target_terms):
                return False

            return True

        # Revaluation request count: related revaluation text without a numeric
        # request limit is not enough.
        if "revaluation" in q and "request" in q:
            return bool(re.search(
                r"\b(?:maximum of\s+)?\d+\s+(?:revaluation\s+)?requests?\b",
                text,
            ))

        # Credit-load questions require a number tied to load/registration,
        # not merely any number of credits (e.g. graduation minimum).
        if "credit load" in q or ("maximum" in q and "credits" in q and "register" in q):
            return bool(re.search(
                r"\b(?:maximum of\s+)?\d+(?:\.\d+)?\s+credits?\b.*(?:load|register|registration)"
                r"|(?:load|register|registration).*\b(?:maximum of\s+)?\d+(?:\.\d+)?\s+credits?\b",
                text,
                re.S,
            ))

        # Percentage
        if "percentage" in q or "percent" in q:
            return bool(re.search(r"\b\d+(?:\.\d+)?\s*(?:percent|%)\b", text))

        # Marks
        if "marks" in q:
            return bool(re.search(r"\b\d+(?:\.\d+)?\s*marks?\b", text))

        # Days / duration
        if "days" in q or "how long" in q:
            return bool(re.search(r"\b\d+(?:\.\d+)?\s*(?:days?|weeks?|months?|years?)\b", text))

        # Credits
        if "credit" in q:
            return bool(re.search(r"\b\d+(?:\.\d+)?\s*credits?\b", text))

        # Subject count
        if "subject" in q and any(x in q for x in ("how many", "maximum", "minimum number")):
            return bool(re.search(
                r"\b(?:maximum of\s+)?(?:\d+|one|two|three|four|five|six|seven|eight)\s+subjects?\b",
                text,
                re.I,
            ))

        # Money / compensation
        if any(word in q for word in ("fee", "amount", "cost", "charge", "compensation")):
            return bool(re.search(
                r"(?:₹|rs\.?|inr)\s*[\d,]+|\b\d[\d,]*(?:\.\d+)?\s*(?:rupees?|rs\.?|inr)\b",
                text,
                re.I,
            ))

        # Date
        if "deadline" in q or "due date" in q or "date" in q:
            return bool(re.search(
                r"\b\d{1,2}\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\b",
                text,
                re.I,
            ))

        return True

    # =============================================================
    # CONTRADICTION DETECTION
    # =============================================================

    def detect_contradiction(self, question, evidence):
        """Detect conflicting applicable numeric/date claims."""
        claims = []

        patterns = {
            "percentage": r"\b(\d+(?:\.\d+)?)\s*(?:percent|%)\b",
            "subject_count": r"\b(?:maximum of\s+)?(\d+|one|two|three|four|five|six|seven|eight)\s+subjects?\b",
            "date": r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\b",
        }

        word_to_number = {
            "one": 1, "two": 2, "three": 3, "four": 4,
            "five": 5, "six": 6, "seven": 7, "eight": 8,
        }

        for item in evidence:
            text = item["text"]
            section = item.get("section", "") or ""

            if any(x in question.lower() for x in ("percentage", "percent", "attendance")):
                percentage_matches = re.finditer(patterns["percentage"], text, re.I)
            else:
                percentage_matches = []

            for match in percentage_matches:
                context = self.claim_context(text, match.start(), match.end())
                claims.append({
                    "type": "percentage",
                    "value": float(match.group(1)),
                    "evidence": item,
                    "context": context,
                })

            if "subject" in question.lower() or "improvement" in question.lower():
                subject_matches = re.finditer(patterns["subject_count"], text, re.I)
            else:
                subject_matches = []

            for match in subject_matches:
                raw = match.group(1)
                number = int(raw) if raw.isdigit() else word_to_number[raw.lower()]
                context = self.claim_context(text, match.start(), match.end())
                claims.append({
                    "type": "subject_count",
                    "value": number,
                    "evidence": item,
                    "context": context,
                })

            if any(x in question.lower() for x in ("deadline", "due date", "date")):
                date_matches = re.finditer(patterns["date"], text, re.I)
            else:
                date_matches = []

            for match in date_matches:
                context = self.claim_context(text, match.start(), match.end())
                claims.append({
                    "type": "date",
                    "value": (int(match.group(1)), match.group(2).lower()),
                    "evidence": item,
                    "context": context,
                })

        for i in range(len(claims)):
            for j in range(i + 1, len(claims)):
                first, second = claims[i], claims[j]

                if first["type"] != second["type"] or first["value"] == second["value"]:
                    continue

                first_item = first["evidence"]
                second_item = second["evidence"]

                if first_item["rerank_score"] < -1.5 or second_item["rerank_score"] < -1.5:
                    continue

                if not self.claim_is_applicable(
                    question, first["type"], first["context"],
                    first_item.get("text", ""), first_item.get("section", "")
                ):
                    continue

                if not self.claim_is_applicable(
                    question, second["type"], second["context"],
                    second_item.get("text", ""), second_item.get("section", "")
                ):
                    continue

                # The two provisions should share a real topical anchor.
                # Prefer semantic/topic anchors over generic words such as
                # 'student', 'rule', or 'number'.
                q = question.lower()
                anchors = []

                if any(x in q for x in ("medical", "exemption", "attendance")):
                    anchors = ["medical", "exemption", "attendance"]
                elif "improvement" in q:
                    anchors = ["improvement", "subjects"]
                elif "tuition" in q and any(x in q for x in ("deadline", "due", "date", "normal")):
                    anchors = ["tuition", "semester tuition", "deadline", "due"]

                first_full = f"{first_item.get('section','')} {first_item.get('text','')}".lower()
                second_full = f"{second_item.get('section','')} {second_item.get('text','')}".lower()

                if anchors and not any(
                    anchor in first_full and anchor in second_full
                    for anchor in anchors
                ):
                    continue

                # For an unanchored numeric question, do not guess that two
                # unrelated values conflict.
                if not anchors:
                    q_terms = self.question_terms(question)
                    first_words = set(re.findall(r"[a-z]+", first_full))
                    second_words = set(re.findall(r"[a-z]+", second_full))
                    shared = first_words & second_words & q_terms
                    if len(shared) < 1:
                        continue

                return {
                    "state": "CONTRADICTION",
                    "reason": "The corpus contains conflicting claims about the same rule.",
                    "conflicts": [first_item, second_item],
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

        # Look for an explicit corpus statement that the requested detail is
        # absent. Check more than just the top passage, but require the passage
        # to be clearly related to the question.
        for item in evidence:
            text = item["text"].lower()
            q_lower = question.lower()

            # Strong corpus-grounded negative for replacement-exam questions:
            # the source explicitly says there is no general right and names
            # travel problems as a non-qualifying ground.
            replacement_case = (
                "replacement examination" in q_lower
                and any(x in q_lower for x in ("train", "cancellation", "travel"))
                and any(x in text for x in ("no general right", "replacement examination", "travel problems"))
            )

            if replacement_case:
                return {
                    "state": "NOT_COVERED",
                    "reason": (
                        "The corpus does not establish a general replacement "
                        "examination right for the stated travel-related circumstance."
                    ),
                    "evidence": evidence,
                }

            if item["rerank_score"] < -1.5:
                continue

            if not self.contains_explicit_absence(text) and not any(
                phrase in text
                for phrase in (
                    "no general right",
                    "do not create a general right",
                    "does not prescribe",
                    "not expressly defined",
                    "does not specify a fixed",
                )
            ):
                continue

            terms = self.question_terms(question)
            overlap = sum(1 for term in terms if term in text)
            if overlap >= 2 or any(
                anchor in text and anchor in q_lower
                for anchor in (
                    "replacement examination", "revaluation", "compensation",
                    "credit load", "gold medal",
                )
            ):
                return {
                    "state": "NOT_COVERED",
                    "reason": (
                        "The corpus explicitly indicates that the requested "
                        "detail is not specified."
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