from pathlib import Path
import json

from tqdm import tqdm


# ============================================================
# CONFIG
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "raw"
DATA_DIR = PROJECT_DIR / "data"

OUTPUT_FILE = DATA_DIR / "documents.json"

CHUNK_SIZE = 50


# ============================================================
# CHUNK TEXT
# ============================================================

def chunk_text(text, chunk_size=CHUNK_SIZE):
    """Chia text thanh cac chunk dua tren so luong tu."""

    words = text.split()

    chunks = []

    for i in range(0, len(words), chunk_size):

        chunk = " ".join(
            words[i:i + chunk_size]
        )

        chunks.append(chunk)

    return chunks


# ============================================================
# LOAD DOCUMENTS
# ============================================================

def load_documents(show_progress=False):
    """Doc Markdown files va chia thanh cac chunk."""

    documents = []

    files = list(
        RAW_DIR.rglob("*.md")
    )

    if show_progress:

        files = tqdm(
            files,
            desc="Building documents",
            unit="file",
            dynamic_ncols=True,
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}"
        )

    for file in files:

        content = file.read_text(
            encoding="utf-8"
        )

        domain = file.parent.name

        chunks = chunk_text(
            content
        )

        for chunk in chunks:

            documents.append({
                "content": chunk,
                "domain": domain,
                "source": str(file)
            })

    return documents


# ============================================================
# SAVE DOCUMENTS
# ============================================================

def save_documents(documents):
    """Luu documents vao documents.json."""

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            documents,
            file,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# BUILD DOCUMENTS
# ============================================================

def build_documents():
    """Build documents tu raw Markdown files."""

    documents = load_documents(
        show_progress=True
    )

    save_documents(
        documents
    )

    return documents


# ============================================================
# MODULE STATUS
# ============================================================

if __name__ == "__main__":

    build_documents()

    print("Build Documents finished!")