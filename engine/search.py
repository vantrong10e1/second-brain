from pathlib import Path
import json

import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


# ============================================================
# CONFIG
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"

DOCUMENTS_FILE = DATA_DIR / "documents_with_embeddings.json"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

DEFAULT_TOP_K = 5


# ============================================================
# CACHE
# ============================================================

_documents = None
_model = None


# ============================================================
# LOAD DOCUMENTS
# ============================================================

def load_documents(show_progress=False):
    """Doc documents kem embedding."""

    global _documents

    if _documents is not None:
        return _documents

    with open(
        DOCUMENTS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        documents = json.load(file)

    if show_progress:

        documents = list(
            tqdm(
                documents,
                desc="Loading documents",
                unit="document",
                dynamic_ncols=True,
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}"
            )
        )

    _documents = documents

    return _documents


# ============================================================
# LOAD EMBEDDING MODEL
# ============================================================

def load_embedding_model():
    """Load embedding model."""

    global _model

    if _model is None:
        _model = SentenceTransformer(
            EMBEDDING_MODEL
        )

    return _model


# ============================================================
# CALCULATE COSINE SIMILARITY
# ============================================================

def cosine_similarity(
    query_embedding,
    document_embedding
):
    """Tinh cosine similarity giua query va document."""

    query_embedding = np.asarray(
        query_embedding
    )

    document_embedding = np.asarray(
        document_embedding
    )

    query_norm = np.linalg.norm(
        query_embedding
    )

    document_norm = np.linalg.norm(
        document_embedding
    )

    if query_norm == 0 or document_norm == 0:
        return 0.0

    similarity = np.dot(
        query_embedding,
        document_embedding
    ) / (
        query_norm * document_norm
    )

    return float(similarity)


# ============================================================
# VECTOR SEARCH
# ============================================================

def search(
    query,
    documents=None,
    top_k=DEFAULT_TOP_K
):
    """Tim document gan query nhat bang cosine similarity."""

    if not query or not query.strip():
        return []

    if documents is None:
        documents = load_documents()

    if not documents:
        return []

    model = load_embedding_model()

    query_embedding = model.encode(
        query
    )

    results = []

    for document in documents:

        document_embedding = document.get(
            "embedding",
            []
        )

        if not document_embedding:
            continue

        similarity = cosine_similarity(
            query_embedding,
            document_embedding
        )

        results.append({
            "similarity": similarity,
            "document": document
        })

    results.sort(
        key=lambda item: item["similarity"],
        reverse=True
    )

    return results[:top_k]


# ============================================================
# MODULE STATUS
# ============================================================

if __name__ == "__main__":

    load_documents(
        show_progress=True
    )

    load_embedding_model()

    print("Search is running...")