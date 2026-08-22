import json
import re
import requests
from pathlib import Path
from tqdm import tqdm


# CONFIG

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"
TIMEOUT = 300


# EXTRACT JSON

def extract_json(text):
    """Lay JSON object tu response cua Ollama."""

    if not text:
        return None

    text = text.strip()
    text = re.sub(r"```json", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "").strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        return None

    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


# VALIDATE ENTITIES

def validate_entities(result):
    """Chuan hoa ket qua NER."""

    if not isinstance(result, dict):
        return None

    entities = result.get("entities", [])

    if not isinstance(entities, list):
        return None

    validated_entities = []

    for entity in entities:

        if not isinstance(entity, dict):
            continue

        text = entity.get("text")
        entity_type = entity.get("type")

        if not text or not entity_type:
            continue

        text = str(text).strip()
        entity_type = str(entity_type).strip().upper()

        if not text or not entity_type:
            continue

        validated_entities.append({
            "text": text,
            "type": entity_type
        })

    return {
        "entities": validated_entities
    }


# BUILD NER PROMPT

def build_ner_prompt(query):
    """Tao prompt cho NER."""

    return f"""
Bạn là module Named Entity Recognition (NER) của hệ thống RAG.

Nhiệm vụ:
Tìm các entity được nhắc trực tiếp trong USER QUERY.

USER QUERY:
{query}

Các loại entity có thể sử dụng:

- PERSON
- ORGANIZATION
- PRODUCT
- SOFTWARE
- TECHNOLOGY
- PROGRAMMING_LANGUAGE
- COMPANY
- CUSTOMER
- EMPLOYEE
- STORE
- ORDER
- LOCATION
- DATE
- OTHER

RULES:

1. Chỉ lấy entity thực sự xuất hiện trong query.

2. Không tự suy đoán entity ID.

3. Không tìm canonical entity.

4. Không resolve entity.

5. Không thêm entity không xuất hiện trong query.

6. Giữ nguyên text entity theo cách người dùng viết.

Ví dụ:

Query:
"Ứng dụng của Claude Code là gì?"

Kết quả:
{{
    "entities": [
        {{
            "text": "Claude Code",
            "type": "SOFTWARE"
        }}
    ]
}}

Query:
"C# có hỗ trợ inheritance không?"

Kết quả:
{{
    "entities": [
        {{
            "text": "C#",
            "type": "PROGRAMMING_LANGUAGE"
        }}
    ]
}}

Query:
"AI là gì?"

Kết quả:
{{
    "entities": [
        {{
            "text": "AI",
            "type": "TECHNOLOGY"
        }}
    ]
}}

Nếu không có entity cụ thể:

{{
    "entities": []
}}

Chỉ trả về JSON.
Không giải thích.
Không markdown.

FORMAT:

{{
    "entities": [
        {{
            "text": "Claude Code",
            "type": "SOFTWARE"
        }}
    ]
}}
"""


# NER

def extract_entities(query):
    """Extract entity mention va entity type tu user query."""

    if not query or not query.strip():
        return {
            "entities": []
        }

    prompt = build_ner_prompt(query)

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
        return {
            "entities": []
        }

    try:
        data = response.json()
    except ValueError:
        return {
            "entities": []
        }

    raw_response = data.get("response", "")
    result = extract_json(raw_response)

    if result is None:
        return {
            "entities": []
        }

    validated_result = validate_entities(result)

    if validated_result is None:
        return {
            "entities": []
        }

    return validated_result


# MODULE STATUS

if __name__ == "__main__":

    for _ in tqdm(
        range(1),
        desc="Loading NER",
        unit="module",
        dynamic_ncols=True,
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}"
    ):
        pass

    print("NER is running...")