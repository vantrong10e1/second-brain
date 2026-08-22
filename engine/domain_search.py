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
# FILTER BY DOMAIN
# ============================================================

def filter_by_domain(documents, domain):
    """Loc documents theo domain."""

    if not domain:
        return documents

    return [
        document
        for document in documents
        if document.get("domain") == domain
    ]


# ============================================================
# SEARCH BY VECTOR
# ============================================================

def search_by_vector(
    query,
    documents,
    top_k=DEFAULT_TOP_K
):
    """Tim documents co similarity cao nhat."""

    if not query or not documents:
        return []

    model = load_embedding_model()

    query_embedding = model.encode(
        query
    )

    query_embedding = np.array(
        query_embedding
    )

    results = []

    for document in documents:

        document_embedding = np.array(
            document.get(
                "embedding",
                []
            )
        )

        if document_embedding.size == 0:
            continue

        similarity = np.dot(
            query_embedding,
            document_embedding
        ) / (
            np.linalg.norm(query_embedding)
            * np.linalg.norm(document_embedding)
        )

        results.append({
            "similarity": float(similarity),
            "document": document
        })

    results.sort(
        key=lambda item: item["similarity"],
        reverse=True
    )

    return results[:top_k]


# ============================================================
# DOMAIN SEARCH
# ============================================================

def domain_search(
    query,
    domain=None,
    top_k=DEFAULT_TOP_K
):
    """Search documents trong domain bang vector similarity."""

    documents = load_documents()

    filtered_documents = filter_by_domain(
        documents,
        domain
    )

    return search_by_vector(
        query,
        filtered_documents,
        top_k
    )


# ============================================================
# MODULE STATUS
# ============================================================

if __name__ == "__main__":

    load_documents(
        show_progress=True
    )

    load_embedding_model()

    print("Domain Search is running...")