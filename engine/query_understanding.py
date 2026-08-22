from pathlib import Path
import json
import re
import requests
from tqdm import tqdm


# CONFIG

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
DOCUMENTS_FILE = DATA_DIR / "documents_with_embeddings.json"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

TIMEOUT = 300


# DOMAIN CACHE

_domains = None


# LOAD DOMAINS

def load_domains(show_progress=False):
    """Doc documents va lay danh sach domain."""

    global _domains

    if _domains is not None:
        return _domains

    try:
        with open(DOCUMENTS_FILE, "r", encoding="utf-8") as file:
            documents = json.load(file)

    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []

    if show_progress:
        documents = tqdm(
            documents,
            desc="Loading domains",
            unit="document",
            dynamic_ncols=True,
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}"
        )

    domains = set()

    for document in documents:
        domain = document.get("domain")

        if domain:
            domains.add(domain)

    _domains = sorted(domains)

    return _domains


# EXTRACT JSON

def extract_json(text):
    """Lay JSON object tu response cua LLM."""

    if not text:
        return None

    text = text.strip()

    text = re.sub(
        r"```json",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = text.replace("```", "").strip()

    try:
        result = json.loads(text)

        if isinstance(result, dict):
            return result

    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        return None

    try:
        result = json.loads(
            text[start:end + 1]
        )

        if isinstance(result, dict):
            return result

    except json.JSONDecodeError:
        return None

    return None


# INFER INTENT

def infer_intent(query):
    """Tu dong xac dinh intent co ban neu LLM khong tra intent hop le."""

    query_lower = query.lower().strip()

    definition_patterns = [
        r"\blà gì\b",
        r"\bla gi\b",
        r"\bnghĩa là gì\b",
        r"\bnghia la gi\b",
        r"\bwhat is\b",
        r"\bwhat's\b",
        r"\bdefine\b",
        r"\bđịnh nghĩa\b",
        r"\bdinh nghia\b"
    ]

    technical_patterns = [
        r"\bcó hỗ trợ\b",
        r"\bco ho tro\b",
        r"\bcó thể\b",
        r"\bco the\b",
        r"\blàm thế nào\b",
        r"\blam the nao\b",
        r"\bhow to\b",
        r"\bhow does\b",
        r"\bsyntax\b",
        r"\berror\b",
        r"\blỗi\b",
        r"\bloi\b"
    ]

    for pattern in definition_patterns:
        if re.search(pattern, query_lower):
            return "definition"

    for pattern in technical_patterns:
        if re.search(pattern, query_lower):
            return "technical_question"

    return "information_seeking"


# VALIDATE RESULT

def validate_result(result, query):
    """Kiem tra va chuan hoa ket qua Query Understanding."""

    if not isinstance(result, dict):
        result = {}

    intent = result.get("intent")
    domain = result.get("domain")
    topic = result.get("topic")

    valid_intents = {
        "definition",
        "technical_question",
        "information_seeking"
    }

    # Normalize intent

    if intent is not None:
        intent = str(intent).strip().lower()

    if intent not in valid_intents:
        intent = infer_intent(query)

    # Normalize domain

    if domain is not None:
        domain = str(domain).strip()

        if not domain:
            domain = None

    # Normalize topic

    if topic is not None:
        topic = str(topic).strip()

        if not topic:
            topic = None

    return {
        "intent": intent,
        "domain": domain,
        "topic": topic
    }


# QUERY UNDERSTANDING

def understand_query(query):
    """Phan tich query cua user bang Ollama."""

    if not query or not query.strip():
        return None

    domains = load_domains()

    if not domains:
        return None

    domain_text = "\n".join(
        f"- {domain}"
        for domain in domains
    )

    prompt = f"""
Bạn là module Query Understanding của một hệ thống RAG.

Nhiệm vụ:
Phân tích câu hỏi của người dùng và trả về JSON.

CHỈ xử lý 3 thông tin:
- intent
- domain
- topic

Entity KHÔNG xử lý ở đây.
Entity sẽ được xử lý bởi module NER.


================ INTENT ================

Chọn đúng một trong ba loại:

- definition
- technical_question
- information_seeking

definition:
Dùng khi người dùng hỏi "X là gì?", "X la gi?",
"X nghĩa là gì?", "What is X?".

Ví dụ:

"Java là gì?"
→ definition

"Claude Code la gi?"
→ definition

"AI nghĩa là gì?"
→ definition


technical_question:
Dùng khi người dùng hỏi về cách hoạt động,
cách sử dụng, tính năng, kỹ thuật hoặc lỗi.

Ví dụ:

"C# có hỗ trợ inheritance không?"
→ technical_question

"Java có hỗ trợ interface không?"
→ technical_question


information_seeking:
Dùng khi người dùng muốn tìm thông tin nhưng
không thuộc hai loại trên.

Ví dụ:

"Java được sử dụng ở đâu?"
→ information_seeking


================ DOMAIN ================

Chọn domain phù hợp nhất trong danh sách domain hiện có.

Không được tự tạo domain mới.

Các domain hiện có:

{domain_text}

Ví dụ:

Java
→ programming-language

C#
→ programming-language

Claude Code
→ ai

AI
→ ai

Nếu không xác định được:
null


================ TOPIC ================

Lấy chủ đề chính của câu hỏi.

Ví dụ:

"Java là gì?"
→ "Java"

"C# có hỗ trợ inheritance không?"
→ "inheritance"

"Claude Code là gì?"
→ "Claude Code"

"AI là gì?"
→ "AI"


================ IMPORTANT ================

Nếu câu hỏi có dạng:

"X là gì?"
"X la gi?"
"X nghĩa là gì?"
"X nghia la gi?"
"What is X?"

thì intent PHẢI là:

"definition"


Không giải thích.
Chỉ trả về JSON.


================ OUTPUT FORMAT ================

{{
    "intent": "definition",
    "domain": "programming-language",
    "topic": "Java"
}}


================ QUESTION ================

{query}
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0
                }
            },
            timeout=TIMEOUT
        )

        response.raise_for_status()

    except requests.exceptions.RequestException:
        return None

    try:
        data = response.json()

    except ValueError:
        return None

    raw_response = data.get(
        "response",
        ""
    )

    result = extract_json(
        raw_response
    )

    return validate_result(
        result,
        query
    )


# MODULE STATUS

if __name__ == "__main__":

    load_domains(
        show_progress=True
    )

    print(
        "Query Understanding is running..."
    )