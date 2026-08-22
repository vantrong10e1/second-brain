from pathlib import Path
import json
import os

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

    try:
        with open(
            DOCUMENTS_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            documents = json.load(file)

    except (
        FileNotFoundError,
        json.JSONDecodeError,
        OSError
    ):
        return []

    if show_progress:
        documents = list(
            tqdm(
                documents,
                desc="Loading retrieval documents",
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
# NORMALIZE PATH
# ============================================================

def normalize_path(path):
    """Chuan hoa path de so sanh source."""

    if not path:
        return ""

    path = str(path).strip()

    path = os.path.normcase(
        os.path.normpath(path)
    )

    return path.replace(
        "\\",
        "/"
    ).lower()


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_text(text):
    """Chuan hoa text."""

    if not text:
        return ""

    return " ".join(
        str(text)
        .lower()
        .strip()
        .split()
    )


# ============================================================
# FILTER BY DOMAIN
# ============================================================

def filter_by_domain(
    documents,
    domain=None
):
    """Loc documents theo domain."""

    if not domain:
        return documents

    domain = normalize_text(
        domain
    )

    return [
        document
        for document in documents
        if normalize_text(
            document.get("domain", "")
        ) == domain
    ]


# ============================================================
# FILTER BY ENTITY
# ============================================================

def filter_by_entity(
    documents,
    resolved_entities=None
):
    """
    Loc documents theo Entity Resolution.

    Uu tien:
    1. entity_id trong document
    2. source cua entity
    """

    if not resolved_entities:
        return documents

    entity_ids = set()
    entity_sources = set()

    for entity in resolved_entities:

        entity_id = entity.get(
            "entity_id"
        )

        if entity_id:
            entity_ids.add(
                normalize_text(
                    entity_id
                )
            )

        for source in entity.get(
            "sources",
            []
        ):

            normalized_source = normalize_path(
                source
            )

            if normalized_source:
                entity_sources.add(
                    normalized_source
                )

    if not entity_ids and not entity_sources:
        return []

    filtered_documents = []

    for document in documents:

        # ----------------------------------------------------
        # Match by entity_id
        # ----------------------------------------------------

        document_entity_id = document.get(
            "entity_id"
        )

        if document_entity_id:

            if normalize_text(
                document_entity_id
            ) in entity_ids:

                filtered_documents.append(
                    document
                )

                continue

        # ----------------------------------------------------
        # Match by entity_ids
        # ----------------------------------------------------

        document_entity_ids = document.get(
            "entity_ids",
            []
        )

        if isinstance(
            document_entity_ids,
            list
        ):

            normalized_document_ids = {
                normalize_text(
                    entity_id
                )
                for entity_id in document_entity_ids
            }

            if normalized_document_ids.intersection(
                entity_ids
            ):

                filtered_documents.append(
                    document
                )

                continue

        # ----------------------------------------------------
        # Match by source
        # ----------------------------------------------------

        document_source = normalize_path(
            document.get(
                "source",
                ""
            )
        )

        if (
            document_source
            and
            document_source in entity_sources
        ):

            filtered_documents.append(
                document
            )

    return filtered_documents


# ============================================================
# COSINE SIMILARITY
# ============================================================

def cosine_similarity(
    query_embedding,
    document_embedding
):
    """Tinh cosine similarity."""

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

    if (
        query_norm == 0
        or
        document_norm == 0
    ):
        return 0.0

    similarity = np.dot(
        query_embedding,
        document_embedding
    ) / (
        query_norm
        *
        document_norm
    )

    return float(
        similarity
    )


# ============================================================
# SEMANTIC SEARCH
# ============================================================

def semantic_search(
    query,
    documents=None,
    domain=None,
    resolved_entities=None,
    top_k=DEFAULT_TOP_K
):
    """
    Entity-aware semantic retrieval.

    Neu co resolved entity:
        chi search trong entity documents.

    Neu khong co entity:
        search theo domain.

    Khong fallback entity -> toan bo domain.
    """

    if not query or not query.strip():
        return []

    if documents is None:
        documents = load_documents()

    if not documents:
        return []

    # ========================================================
    # ENTITY-AWARE RETRIEVAL
    # ========================================================

    if resolved_entities:

        documents = filter_by_entity(
            documents,
            resolved_entities
        )

        # Da resolve entity nhung khong tim thay document.
        # Khong duoc fallback sang domain.

        if not documents:
            return []

    # ========================================================
    # DOMAIN RETRIEVAL
    # ========================================================

    else:

        documents = filter_by_domain(
            documents,
            domain
        )

        if not documents:
            return []

    # ========================================================
    # EMBEDDING
    # ========================================================

    model = load_embedding_model()

    query_embedding = model.encode(
        query
    )

    results = []

    # ========================================================
    # COSINE SEARCH
    # ========================================================

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

    # ========================================================
    # SORT
    # ========================================================

    results.sort(
        key=lambda item: item[
            "similarity"
        ],
        reverse=True
    )

    return results[
        :top_k
    ]


# ============================================================
# RAG RETRIEVAL
# ============================================================

def retrieve(
    query,
    domain=None,
    resolved_entities=None,
    top_k=DEFAULT_TOP_K
):
    """Thuc hien Entity-aware Retrieval."""

    return semantic_search(
        query=query,
        domain=domain,
        resolved_entities=resolved_entities,
        top_k=top_k
    )


# ============================================================
# MODULE STATUS
# ============================================================

if __name__ == "__main__":

    load_documents(
        show_progress=True
    )

    load_embedding_model()

    print(
        "RAG Retrieval is running..."
    )