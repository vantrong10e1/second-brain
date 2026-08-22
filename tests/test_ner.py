from pathlib import Path
import sys
import json
import requests


# ============================================================
# CONFIG
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
ENGINE_DIR = PROJECT_DIR / "engine"

sys.path.insert(0, str(ENGINE_DIR))

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"


# ============================================================
# NER
# ============================================================

def extract_entities(query):

    prompt = f"""
Bạn là module Named Entity Recognition (NER).

Nhiệm vụ:
Tìm các entity cụ thể xuất hiện trong câu hỏi.

Các loại entity:

- TOOL
- PROGRAMMING_LANGUAGE
- CONCEPT
- TECHNOLOGY
- PERSON
- ORGANIZATION

Rules:

- Chỉ lấy entity thực sự xuất hiện trong câu.
- Không tự thêm entity.
- Không resolve entity.
- Không tìm entity_id.
- Không xác định domain.
- Không giải thích.

QUESTION:
{query}

Chỉ trả về JSON:

{{
    "entities": [
        {{
            "text": "Claude Code",
            "type": "TOOL"
        }}
    ]
}}
"""

    try:

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=300
        )

        response.raise_for_status()

        data = response.json()

        raw_response = data.get(
            "response",
            ""
        ).strip()

        start = raw_response.find("{")
        end = raw_response.rfind("}")

        if start == -1 or end == -1:
            return []

        result = json.loads(
            raw_response[start:end + 1]
        )

        return result.get(
            "entities",
            []
        )

    except Exception:
        return []


# ============================================================
# TEST CASES
# ============================================================

TEST_QUERIES = [
    "Claude Code là gì?",
    "C# có hỗ trợ inheritance không?",
    "Java được sử dụng để làm gì?",
    "RAG là gì?",
    "Python có phải ngôn ngữ lập trình không?"
]


# ============================================================
# RUN TEST
# ============================================================

def run_tests():

    print("NER Test:")

    for query in TEST_QUERIES:

        entities = extract_entities(
            query
        )

        print()
        print("Query:", query)

        if not entities:

            print("  Entity: None")
            continue

        for entity in entities:

            print(
                "  Entity:",
                entity.get("text")
            )

            print(
                "  Type:",
                entity.get("type")
            )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    run_tests()