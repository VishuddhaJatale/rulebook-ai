from pathlib import Path
import json

import faiss
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).resolve().parent.parent
CHUNKS_FILE = ROOT / "data" / "processed" / "chunks.json"
INDEX_DIR = ROOT / "data" / "index"

MODEL_NAME = "all-MiniLM-L6-v2"


class SemanticRetriever:

    def __init__(self):
        self.model = SentenceTransformer(MODEL_NAME)

        with CHUNKS_FILE.open("r", encoding="utf-8") as f:
            self.chunks = json.load(f)

        texts = [chunk["text"] for chunk in self.chunks]

        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=True,
        )

        dimension = embeddings.shape[1]

        # Inner product on normalized vectors = cosine similarity
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings)

    def search(self, question: str, top_k: int = 5):
        query_embedding = self.model.encode(
            [question],
            normalize_embeddings=True,
        )

        scores, indices = self.index.search(
            query_embedding,
            top_k,
        )

        results = []

        for score, index in zip(scores[0], indices[0]):

            if index == -1:
                continue

            chunk = self.chunks[index].copy()
            chunk["similarity"] = float(score)

            results.append(chunk)

        return results


def main():
    retriever = SemanticRetriever()

    print("\nRulebook AI — Semantic Retrieval Test")
    print("-------------------------------------")

    while True:
        question = input("\nAsk a question (or type 'exit'): ")

        if question.lower() == "exit":
            break

        results = retriever.search(question, top_k=10)

        print("\nTop evidence:\n")

        for i, result in enumerate(results, start=1):
            print(f"[{i}] Similarity: {result['similarity']:.4f}")
            print(f"Source: {result['source']}")
            print(f"Page: {result['page']}")
            print(f"Section: {result['section']}")
            print(f"Chunk: {result['chunk_id']}")
            print(f"Text: {result['text'][:500]}")
            print("-" * 70)


if __name__ == "__main__":
    main()