import json
import re
import requests

from tqdm import tqdm


# CONFIG

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

DEFAULT_TOP_K = 2
TIMEOUT = 300


# CLEAN JSON RESPONSE

def clean_json_response(response):
    """Lam sach JSON response tu Ollama."""

    if not response:
        return ""

    response = response.strip()
    response = re.sub(r"```json", "", response, flags=re.IGNORECASE)
    response = response.replace("```", "").strip()

    start = response.find("{")
    end = response.rfind("}")

    if start != -1 and end != -1:
        response = response[start:end + 1]

    return response


# SCORE ONE DOCUMENT

def score_document(query, document):
    """Danh gia relevance cua document voi query."""

    prompt = f"""
Bạn là hệ thống Reranker của RAG.

Nhiệm vụ:
Đánh giá mức độ liên quan của DOCUMENT đối với QUESTION.

QUESTION:
{query}

DOCUMENT:
{document.get("content", "")}

Cho điểm từ 0 đến 100:

100 = trực tiếp trả lời câu hỏi
80-99 = rất liên quan
60-79 = khá liên quan
40-59 = liên quan một phần
20-39 = ít liên quan
0-19 = không liên quan

Chỉ trả về JSON.
Không giải thích.

FORMAT:
{{
    "score": 0
}}
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0
                }
            },
            timeout=TIMEOUT
        )

        response.raise_for_status()

    except requests.exceptions.RequestException:
        return 0.0

    try:
        data = response.json()
    except ValueError:
        return 0.0

    raw_response = data.get("response", "")
    raw_response = clean_json_response(raw_response)

    try:
        result = json.loads(raw_response)
        score = float(result.get("score", 0))
    except (json.JSONDecodeError, ValueError, TypeError):
        return 0.0

    return max(0.0, min(100.0, score))


# RERANK

def rerank(query, results, top_k=DEFAULT_TOP_K, show_progress=False):
    """Sap xep lai candidates bang LLM relevance score."""

    if not query or not query.strip():
        return []

    if not results:
        return []

    reranked = []

    items = results

    if show_progress:
        items = tqdm(
            results,
            desc="Reranking documents",
            unit="document",
            dynamic_ncols=True,
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}"
        )

    for result in items:
        document = result.get("document", {})

        rerank_score = score_document(
            query,
            document
        )

        reranked.append({
            "rerank_score": rerank_score,
            "fusion_score": result.get("fusion_score", 0.0),
            "vector_score": result.get("vector_score", 0.0),
            "keyword_score": result.get("keyword_score", 0.0),
            "document": document
        })

    reranked.sort(
        key=lambda item: item["rerank_score"],
        reverse=True
    )

    return reranked[:top_k]


# MODULE STATUS

if __name__ == "__main__":
    print("Reranker is running...")