from sentence_transformers import CrossEncoder

from retrieval import SemanticRetriever


MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class EvidenceReranker:

    def __init__(self):

        self.model = CrossEncoder(MODEL_NAME)

        self.retriever = SemanticRetriever()

    def rerank(self, question, top_k_retrieval=15, top_k_final=5):

        # First retrieve candidates semantically.
        candidates = self.retriever.search(
            question,
            top_k=top_k_retrieval,
        )

        if not candidates:
            return []

        # Create question-passage pairs.
        pairs = [
            [question, candidate["text"]]
            for candidate in candidates
        ]

        # Cross-encoder scores each pair.
        scores = self.model.predict(pairs)

        reranked = []

        for candidate, score in zip(candidates, scores):

            result = candidate.copy()

            result["rerank_score"] = float(score)

            reranked.append(result)

        # Highest score first.
        reranked.sort(
            key=lambda x: x["rerank_score"],
            reverse=True,
        )

        return reranked[:top_k_final]


def main():

    reranker = EvidenceReranker()

    print()
    print("Rulebook AI — Semantic Retrieval + Reranking")
    print("----------------------------------------------")

    while True:

        question = input(
            "\nAsk a question (or type 'exit'): "
        )

        if question.lower() == "exit":
            break

        results = reranker.rerank(
            question,
            top_k_retrieval=15,
            top_k_final=8,
        )

        print("\nReranked evidence:\n")

        for i, result in enumerate(results, start=1):

            print(
                f"[{i}] "
                f"Semantic: {result['similarity']:.4f} | "
                f"Rerank: {result['rerank_score']:.4f}"
            )

            print(f"Source: {result['source']}")
            print(f"Page: {result['page']}")
            print(f"Section: {result['section']}")
            print(f"Provision: {result['provision']}")
            print(f"Chunk: {result['chunk_id']}")

            print(
                f"Text: {result['text'][:700]}"
            )

            print("-" * 70)


if __name__ == "__main__":
    main()