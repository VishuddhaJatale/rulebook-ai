from pathlib import Path
import json
import re

import fitz


ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "corpus"
OUTPUT_DIR = ROOT / "data" / "processed"
OUTPUT_FILE = OUTPUT_DIR / "chunks.json"


PROVISION_NUMBER_RE = re.compile(
    r"^\s*(\d+\.\d+(?:\.\d+)*(?:\([a-z]\))?)\s*$"
)

MARKDOWN_HEADING_RE = re.compile(
    r"^\s*#{1,6}\s+(.+)"
)


def clean_lines(text):
    lines = []

    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()

        if not line:
            continue

        # Remove standalone PDF page numbers.
        if re.fullmatch(r"\d{1,3}", line):
            continue

        lines.append(line)

    return lines


def get_section_from_provision(provision, section_map):
    """
    Convert a provision such as 4.6 into its major section 4.0.
    """

    if not provision:
        return None

    major_number = provision.split(".")[0]
    return section_map.get(major_number)


def build_pdf_section_map(lines):
    """
    Detect PDF major sections where the section number and title
    may appear on separate lines.

    Example:

        5.0
        AWARD OF CREDITS AND GRADES
    """

    section_map = {}

    for i, line in enumerate(lines):

        match = re.fullmatch(
            r"\s*(\d+)\.0\s*",
            line
        )

        if not match:
            continue

        number = match.group(1)

        # The title is normally the next meaningful line.
        title = None

        for next_line in lines[i + 1:i + 4]:

            if next_line.strip():

                # Don't use another numeric provision as title.
                if re.fullmatch(
                    r"\d+(?:\.\d+)+",
                    next_line.strip()
                ):
                    break

                title = next_line.strip()
                break

        if title:
            section_map[number] = f"{number}.0 {title}"
        else:
            section_map[number] = f"{number}.0"

    return section_map


def split_markdown(file_path):
    text = file_path.read_text(encoding="utf-8")
    lines = clean_lines(text)

    chunks = []

    current_section = None
    current_lines = []

    def flush():
        nonlocal current_lines

        if not current_lines:
            return

        blocks = split_into_provisions(current_lines)

        for block in blocks:
            text = "\n".join(block["lines"]).strip()

            if not text:
                continue

            chunks.append(
                {
                    "text": text,
                    "source": file_path.name,
                    "page": None,
                    "pages": [],
                    "section": current_section,
                    "provision": block["provision"],
                    "file_type": "markdown",
                }
            )

        current_lines = []

    for line in lines:

        heading_match = MARKDOWN_HEADING_RE.match(line)

        if heading_match:
            flush()
            current_section = heading_match.group(1).strip()
            continue

        current_lines.append(line)

    flush()

    return chunks


def split_into_provisions(lines):
    """
    Split text without cutting regulation provisions apart.
    """

    blocks = []
    current_lines = []
    current_provision = None

    for line in lines:

        match = PROVISION_NUMBER_RE.match(line)

        if match:

            if current_lines:
                blocks.append(
                    {
                        "provision": current_provision,
                        "lines": current_lines,
                    }
                )

            current_provision = match.group(1)
            current_lines = [line]

        else:
            current_lines.append(line)

    if current_lines:
        blocks.append(
            {
                "provision": current_provision,
                "lines": current_lines,
            }
        )

    return blocks

def provision_key(provision):
    """
    Convert a provision number into a comparable tuple.

    Examples:
        4.2       -> (4, 2, 0)
        4.6       -> (4, 6, 0)
        4.6(a)    -> (4, 6, 1)
        4.1.2     -> (4, 1, 2)
    """

    if not provision:
        return None

    numbers = re.findall(r"\d+", provision)

    return tuple(int(x) for x in numbers)


def is_new_provision(candidate, current):
    """
    A provision should normally move forward through the document.

    This prevents text such as:

        4.2 and 4.5 above...

    from being incorrectly treated as a new 4.2 provision
    when we are already inside provision 4.6.
    """

    if current is None:
        return True

    candidate_key = provision_key(candidate)
    current_key = provision_key(current)

    if candidate_key is None or current_key is None:
        return False

    # A lower provision number is almost certainly continuation text.
    if candidate_key < current_key:
        return False

    # Same provision number = continuation.
    if candidate_key == current_key:
        return False

    return True

def split_pdf(file_path):
    """
    Extract PDF provisions using the actual visual/text structure.

    RGPV PDFs place provision numbers such as 4.5, 4.6 and 4.7
    on their own lines. We therefore only recognize standalone
    provision-number lines.

    This prevents references such as:

        "rule 4.2 and 4.5 above"

    from being mistaken for a new provision.
    """

    document = fitz.open(file_path)

    page_data = []

    for page_number, page in enumerate(document, start=1):

        text = page.get_text("text")

        lines = clean_lines(text)

        page_data.append(
            {
                "page": page_number,
                "lines": lines,
            }
        )

    document.close()

    # Collect all lines to discover major sections.
    all_lines = []

    for page in page_data:
        all_lines.extend(page["lines"])

    section_map = build_pdf_section_map(all_lines)

    chunks = []

    current_lines = []
    current_provision = None
    current_pages = []

    def flush():

        nonlocal current_lines
        nonlocal current_provision
        nonlocal current_pages

        if not current_lines:
            return

        text = "\n".join(current_lines).strip()

        if text:

            section = get_section_from_provision(
                current_provision,
                section_map,
            )

            chunks.append(
                {
                    "text": text,
                    "source": file_path.name,
                    "page": current_pages[0]
                    if current_pages
                    else None,
                    "pages": sorted(set(current_pages)),
                    "section": section,
                    "provision": current_provision,
                    "file_type": "pdf",
                }
            )

        current_lines = []
        current_provision = None
        current_pages = []

    for page in page_data:

        page_number = page["page"]

        for line in page["lines"]:

            # Only standalone numbers such as "4.6".
            provision_match = PROVISION_NUMBER_RE.match(line)

            if provision_match:

                # Finish previous provision.
                flush()

                current_provision = provision_match.group(1)

                current_lines = [line]

                current_pages = [page_number]

                continue

            # Normal text.
            current_lines.append(line)

            if page_number not in current_pages:
                current_pages.append(page_number)

    flush()

    return chunks

def create_chunks():

    all_chunks = []

    for file_path in sorted(CORPUS_DIR.iterdir()):

        if file_path.suffix.lower() == ".md":

            file_chunks = split_markdown(file_path)

        elif file_path.suffix.lower() == ".pdf":

            file_chunks = split_pdf(file_path)

        else:
            continue

        all_chunks.extend(file_chunks)

        print(
            f"Processed {file_path.name}: "
            f"{len(file_chunks)} regulation-aware chunks"
        )

    # Stable IDs.
    for index, chunk in enumerate(all_chunks):
        chunk["chunk_id"] = f"chunk_{index:04d}"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(
            all_chunks,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("-------------------------------------")
    print(f"Total chunks: {len(all_chunks)}")
    print(f"Output: {OUTPUT_FILE}")
    print("-------------------------------------")


if __name__ == "__main__":
    create_chunks()