from pathlib import Path
import json
import re

import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


# CONFIG

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"

DOCUMENTS_FILE = DATA_DIR / "documents_with_embeddings.json"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

VECTOR_TOP_K = 5
KEYWORD_TOP_K = 5
FINAL_TOP_K = 5

RRF_K = 60


# CACHE

_documents = None
_model = None


# LOAD DOCUMENTS

def load_documents(show_progress=False):
    """Load documents kem embedding."""

    global _documents

    if _documents is not None:
        return _documents

    with open(DOCUMENTS_FILE, "r", encoding="utf-8") as file:
        documents = json.load(file)

    if show_progress:
        documents = list(
            tqdm(
                documents,
                desc="Loading hybrid documents",
                unit="document",
                dynamic_ncols=True,
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}"
            )
        )

    _documents = documents

    return _documents


# LOAD EMBEDDING MODEL

def load_embedding_model():
    """Load embedding model."""

    global _model

    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)

    return _model


# TOKENIZE

def tokenize(text):
    """Chuyen text thanh danh sach token."""

    return re.findall(r"\b\w+\b", str(text).lower(), flags=re.UNICODE)


# COSINE SIMILARITY

def cosine_similarity(query_embedding, document_embedding):
    """Tinh cosine similarity."""

    query_vector = np.asarray(query_embedding)
    document_vector = np.asarray(document_embedding)

    query_norm = np.linalg.norm(query_vector)
    document_norm = np.linalg.norm(document_vector)

    denominator = query_norm * document_norm

    if denominator == 0:
        return 0.0

    return float(np.dot(query_vector, document_vector) / denominator)


# VECTOR SEARCH

def vector_search(query, documents=None, top_k=VECTOR_TOP_K):
    """Tim document bang vector similarity."""

    if not query or not query.strip():
        return []

    if documents is None:
        documents = load_documents()

    if not documents:
        return []

    model = load_embedding_model()
    query_embedding = model.encode(query)

    results = []

    for document in documents:
        document_embedding = document.get("embedding", [])

        if not document_embedding:
            continue

        score = cosine_similarity(query_embedding, document_embedding)

        results.append({
            "document": document,
            "vector_score": score
        })

    results.sort(
        key=lambda item: item["vector_score"],
        reverse=True
    )

    return results[:top_k]


# KEYWORD SCORE

def keyword_score(query, content):
    """Tinh diem keyword matching."""

    query_tokens = set(tokenize(query))
    content_tokens = tokenize(content)

    if not query_tokens:
        return 0.0

    content_set = set(content_tokens)

    matched_tokens = query_tokens & content_set

    if not matched_tokens:
        return 0.0

    coverage = len(matched_tokens) / len(query_tokens)

    frequency = sum(
        content_tokens.count(token)
        for token in matched_tokens
    )

    frequency_score = frequency / max(len(content_tokens), 1)

    return coverage + frequency_score


# KEYWORD SEARCH

def keyword_search(query, documents=None, top_k=KEYWORD_TOP_K):
    """Tim document bang keyword matching."""

    if not query or not query.strip():
        return []

    if documents is None:
        documents = load_documents()

    if not documents:
        return []

    results = []

    for document in documents:
        score = keyword_score(
            query,
            document.get("content", "")
        )

        if score <= 0:
            continue

        results.append({
            "document": document,
            "keyword_score": score
        })

    results.sort(
        key=lambda item: item["keyword_score"],
        reverse=True
    )

    return results[:top_k]


# DOCUMENT KEY

def document_key(document):
    """Tao key duy nhat cho document."""

    return (
        document.get("source", ""),
        document.get("content", "")
    )


# RECIPROCAL RANK FUSION

def reciprocal_rank_fusion(
    vector_results,
    keyword_results,
    top_k=FINAL_TOP_K
):
    """Ket hop Vector Search va Keyword Search bang RRF."""

    fused = {}

    for rank, result in enumerate(vector_results, start=1):
        document = result["document"]
        key = document_key(document)

        item = fused.setdefault(
            key,
            {
                "document": document,
                "vector_rank": None,
                "keyword_rank": None,
                "vector_score": 0.0,
                "keyword_score": 0.0,
                "fusion_score": 0.0
            }
        )

        item["vector_rank"] = rank
        item["vector_score"] = result["vector_score"]
        item["fusion_score"] += 1 / (RRF_K + rank)

    for rank, result in enumerate(keyword_results, start=1):
        document = result["document"]
        key = document_key(document)

        item = fused.setdefault(
            key,
            {
                "document": document,
                "vector_rank": None,
                "keyword_rank": None,
                "vector_score": 0.0,
                "keyword_score": 0.0,
                "fusion_score": 0.0
            }
        )

        item["keyword_rank"] = rank
        item["keyword_score"] = result["keyword_score"]
        item["fusion_score"] += 1 / (RRF_K + rank)

    results = list(fused.values())

    results.sort(
        key=lambda item: item["fusion_score"],
        reverse=True
    )

    return results[:top_k]


# HYBRID SEARCH

def hybrid_search(query, documents=None, top_k=FINAL_TOP_K):
    """
    Ket hop Vector Search va Keyword Search.

    Documents duoc truyen tu Entity-aware Retrieval
    neu pipeline da resolve entity truoc do.
    """

    if not query or not query.strip():
        return []

    if documents is None:
        documents = load_documents()

    if not documents:
        return []

    vector_results = vector_search(
        query,
        documents,
        VECTOR_TOP_K
    )

    keyword_results = keyword_search(
        query,
        documents,
        KEYWORD_TOP_K
    )

    return reciprocal_rank_fusion(
        vector_results,
        keyword_results,
        top_k
    )


# MODULE STATUS

if __name__ == "__main__":

    load_documents(show_progress=True)
    load_embedding_model()

    print("Hybrid Search is running...")