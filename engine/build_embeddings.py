from pathlib import Path
import json

from sentence_transformers import SentenceTransformer
from tqdm import tqdm


# ============================================================
# CONFIG
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"

INPUT_FILE = DATA_DIR / "documents.json"
OUTPUT_FILE = DATA_DIR / "documents_with_embeddings.json"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"


# ============================================================
# LOAD DOCUMENTS
# ============================================================

def load_documents():
    """Doc documents tu documents.json."""

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# LOAD EMBEDDING MODEL
# ============================================================

def load_embedding_model():
    """Load embedding model."""

    return SentenceTransformer(
        EMBEDDING_MODEL
    )


# ============================================================
# CREATE EMBEDDINGS
# ============================================================

def create_embeddings(model, documents):
    """Chuyen content cua documents thanh embeddings."""

    texts = [
        document["content"]
        for document in documents
    ]

    embeddings = model.encode(
        texts,
        show_progress_bar=False
    )

    return embeddings


# ============================================================
# ATTACH EMBEDDINGS
# ============================================================

def attach_embeddings(documents, embeddings):
    """Gan embedding vao tung document."""

    for document, embedding in tqdm(
        zip(documents, embeddings),
        total=len(documents),
        desc="Building embeddings",
        unit="document",
        dynamic_ncols=True,
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}"
    ):

        document["embedding"] = embedding.tolist()

    return documents


# ============================================================
# SAVE DOCUMENTS
# ============================================================

def save_documents(documents):
    """Luu documents kem embedding."""

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
# BUILD EMBEDDINGS
# ============================================================

def build_embeddings():
    """Build embedding cho toan bo documents."""

    documents = load_documents()

    model = load_embedding_model()

    embeddings = create_embeddings(
        model,
        documents
    )

    documents = attach_embeddings(
        documents,
        embeddings
    )

    save_documents(
        documents
    )

    return documents


# ============================================================
# MODULE STATUS
# ============================================================

if __name__ == "__main__":

    build_embeddings()

    print("Build Embeddings finished!")