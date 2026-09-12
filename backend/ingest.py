from pathlib import Path
import json
import re

import fitz  # PyMuPDF


ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "corpus"
OUTPUT_DIR = ROOT / "data" / "processed"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 120


def clean_text(text: str) -> str:
    """Normalize whitespace while preserving paragraph structure."""
    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """
    Split text into overlapping chunks.

    We use character-based chunks for now.
    Later we can evaluate whether semantic/section-aware
    chunking performs better.
    """
    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == len(text):
            break

        start = end - overlap

    return chunks


def extract_markdown(path: Path):
    """Extract Markdown while preserving section headings."""
    text = clean_text(path.read_text(encoding="utf-8"))

    chunks = chunk_text(text)

    results = []

    for i, chunk in enumerate(chunks):
        # Find the nearest heading appearing in this chunk.
        headings = re.findall(r"(?m)^#{1,6}\s+(.+)$", chunk)
        section = headings[-1] if headings else None

        results.append({
            "text": chunk,
            "source": path.name,
            "page": None,
            "section": section,
            "chunk_id": f"{path.stem}-chunk-{i:04d}",
            "file_type": "markdown",
        })

    return results


def extract_pdf(path: Path):
    """Extract PDF text page-by-page so page metadata is preserved."""
    document = fitz.open(path)

    results = []

    for page_number, page in enumerate(document, start=1):
        text = clean_text(page.get_text())

        if not text:
            continue

        chunks = chunk_text(text)

        for i, chunk in enumerate(chunks):
            results.append({
                "text": chunk,
                "source": path.name,
                "page": page_number,
                "section": None,
                "chunk_id": (
                    f"{path.stem}-page-{page_number}-chunk-{i:04d}"
                ),
                "file_type": "pdf",
            })

    document.close()

    return results


def ingest_corpus():
    """Process every supported document in corpus/."""
    all_chunks = []

    for path in sorted(CORPUS_DIR.iterdir()):

        if path.suffix.lower() == ".md":
            chunks = extract_markdown(path)

        elif path.suffix.lower() == ".pdf":
            chunks = extract_pdf(path)

        else:
            continue

        all_chunks.extend(chunks)

        print(f"{path.name}: {len(chunks)} chunks")

    return all_chunks


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    chunks = ingest_corpus()

    output_file = OUTPUT_DIR / "chunks.json"

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)

    print()
    print(f"Total chunks: {len(chunks)}")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()