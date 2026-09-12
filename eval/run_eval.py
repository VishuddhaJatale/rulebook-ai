import json
import sys
from pathlib import Path

# Allow importing backend modules when this script is run from the project root.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.state_detector import StateDetector


QUESTIONS_FILE = ROOT / "eval" / "questions.json"


def main():
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)
        questions = (
        questions["answerable"]
        + questions["not_covered"]
        + questions["contradiction"]
    )

    detector = StateDetector()

    total = len(questions)
    correct = 0

    by_state = {}
    failed = {}

    print(f"Evaluating {total} questions...\n")

    for item in questions:
        question_id = item["id"]
        question = item["question"]
        expected = item["expected_state"]

        result = detector.detect(question)
        predicted = result["state"]

        if predicted == expected:
            correct += 1

        else:
            failed[question_id] = {
                "question": question,
                "expected": expected,
                "predicted": predicted,
            }

        if expected not in by_state:
            by_state[expected] = {
                "total": 0,
                "correct": 0,
            }

        by_state[expected]["total"] += 1

        if predicted == expected:
            by_state[expected]["correct"] += 1

        print(
            f"{question_id}: "
            f"expected={expected:<15} "
            f"predicted={predicted:<15} "
            f"{'OK' if predicted == expected else 'WRONG'}"
        )

    print("\nFAILED QUESTIONS")
    print("=" * 60)

    for question_id, failure in failed.items():

        print(
            f"{question_id}: "
            f"expected={failure['expected']} | "
            f"predicted={failure['predicted']}"
        )

        print(
            f"Question: {failure['question']}"
        )

        print("-" * 60)

    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)

    accuracy = correct / total if total else 0

    print(f"Overall: {correct}/{total} ({accuracy:.1%})")

    for state, stats in by_state.items():
        state_accuracy = stats["correct"] / stats["total"]

        print(
            f"{state}: "
            f"{stats['correct']}/{stats['total']} "
            f"({state_accuracy:.1%})"
        )

    
if __name__ == "__main__":
    main()