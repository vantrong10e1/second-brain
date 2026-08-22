from pathlib import Path
import json
import re
import requests
from tqdm import tqdm


# ============================================================
# CONFIG
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"

DOCUMENTS_FILE = DATA_DIR / "documents.json"
FACK_FILE = DATA_DIR / "fack.json"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

TIMEOUT = 300


# ============================================================
# LOAD DOCUMENTS
# ============================================================

def load_documents():
    """Doc tat ca documents tu documents.json."""

    if not DOCUMENTS_FILE.exists():
        return []

    with open(
        DOCUMENTS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# EXTRACT JSON
# ============================================================

def extract_json(text):
    """Lay JSON object tu response cua Ollama."""

    if not text:
        return None

    text = text.strip()

    text = re.sub(
        r"```json",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = text.replace(
        "```",
        ""
    ).strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        return None

    try:
        return json.loads(
            text[start:end + 1]
        )

    except json.JSONDecodeError:
        return None


# ============================================================
# BUILD PROMPT
# ============================================================

def build_prompt(document):
    """Tao prompt de LLM trich xuat business knowledge."""

    content = document.get(
        "content",
        ""
    )

    domain = document.get(
        "domain",
        ""
    )

    source = document.get(
        "source",
        ""
    )

    return f"""
Bạn là module Business Knowledge Extraction
của một hệ thống RAG.

Nhiệm vụ:
Đọc DOCUMENT và trích xuất các knowledge quan trọng
có thể giúp AI hiểu chính xác nội dung tài liệu.

DOMAIN:
{domain}

SOURCE:
{source}

DOCUMENT:
{content}

Hãy trích xuất các loại knowledge sau:

1. term
Thuật ngữ hoặc khái niệm quan trọng.
Bao gồm tên và định nghĩa.

2. business_rule
Quy tắc hoặc điều kiện được mô tả trong tài liệu.

3. metric
Chỉ số hoặc cách tính được mô tả trong tài liệu.

4. entity
Đối tượng, công nghệ, sản phẩm, framework,
ngôn ngữ lập trình hoặc khái niệm cụ thể.

5. sql_example
Chỉ tạo nếu DOCUMENT thực sự chứa SQL.
Không tự tạo SQL.

RULES:

- Chỉ lấy thông tin có trong DOCUMENT.
- Không tự suy diễn.
- Không bịa thông tin.
- Không tạo knowledge chung chung.
- Không lấy tên domain làm entity nếu nó chỉ là category.
- Nếu loại knowledge không tồn tại thì trả về [].
- Giữ nguyên source và domain của document.
- Không giải thích bên ngoài JSON.

Chỉ trả về JSON theo format:

{{
    "terms": [
        {{
            "name": "RAG",
            "definition": "..."
        }}
    ],
    "business_rules": [
        {{
            "name": "...",
            "rule": "..."
        }}
    ],
    "metrics": [
        {{
            "name": "...",
            "definition": "..."
        }}
    ],
    "entities": [
        {{
            "name": "Claude Code",
            "description": "..."
        }}
    ],
    "sql_examples": [
        {{
            "name": "...",
            "sql": "..."
        }}
    ]
}}
"""


# ============================================================
# EXTRACT KNOWLEDGE
# ============================================================

def extract_knowledge(document):
    """Gui document cho Ollama va lay business knowledge."""

    prompt = build_prompt(
        document
    )

    try:

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
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

    return extract_json(
        raw_response
    )


# ============================================================
# NORMALIZE KNOWLEDGE
# ============================================================

def normalize_knowledge(
    result,
    document
):
    """Chuan hoa knowledge truoc khi luu."""

    if not isinstance(
        result,
        dict
    ):
        return []

    domain = document.get(
        "domain"
    )

    source = document.get(
        "source"
    )

    knowledge = []

    # --------------------------------------------------------
    # TERMS
    # --------------------------------------------------------

    for item in result.get(
        "terms",
        []
    ):

        if not isinstance(
            item,
            dict
        ):
            continue

        name = str(
            item.get(
                "name",
                ""
            )
        ).strip()

        definition = str(
            item.get(
                "definition",
                ""
            )
        ).strip()

        if not name or not definition:
            continue

        knowledge.append({
            "type": "term",
            "name": name,
            "definition": definition,
            "domain": domain,
            "source": source
        })

    # --------------------------------------------------------
    # BUSINESS RULES
    # --------------------------------------------------------

    for item in result.get(
        "business_rules",
        []
    ):

        if not isinstance(
            item,
            dict
        ):
            continue

        name = str(
            item.get(
                "name",
                ""
            )
        ).strip()

        rule = str(
            item.get(
                "rule",
                ""
            )
        ).strip()

        if not name or not rule:
            continue

        knowledge.append({
            "type": "business_rule",
            "name": name,
            "rule": rule,
            "domain": domain,
            "source": source
        })

    # --------------------------------------------------------
    # METRICS
    # --------------------------------------------------------

    for item in result.get(
        "metrics",
        []
    ):

        if not isinstance(
            item,
            dict
        ):
            continue

        name = str(
            item.get(
                "name",
                ""
            )
        ).strip()

        definition = str(
            item.get(
                "definition",
                ""
            )
        ).strip()

        if not name or not definition:
            continue

        knowledge.append({
            "type": "metric",
            "name": name,
            "definition": definition,
            "domain": domain,
            "source": source
        })

    # --------------------------------------------------------
    # ENTITIES
    # --------------------------------------------------------

    for item in result.get(
        "entities",
        []
    ):

        if not isinstance(
            item,
            dict
        ):
            continue

        name = str(
            item.get(
                "name",
                ""
            )
        ).strip()

        description = str(
            item.get(
                "description",
                ""
            )
        ).strip()

        if not name or not description:
            continue

        knowledge.append({
            "type": "entity",
            "name": name,
            "description": description,
            "domain": domain,
            "source": source
        })

    # --------------------------------------------------------
    # SQL EXAMPLES
    # --------------------------------------------------------

    for item in result.get(
        "sql_examples",
        []
    ):

        if not isinstance(
            item,
            dict
        ):
            continue

        name = str(
            item.get(
                "name",
                ""
            )
        ).strip()

        sql = str(
            item.get(
                "sql",
                ""
            )
        ).strip()

        if not name or not sql:
            continue

        knowledge.append({
            "type": "sql_example",
            "name": name,
            "sql": sql,
            "domain": domain,
            "source": source
        })

    return knowledge


# ============================================================
# BUILD FACK
# ============================================================

def build_fack(documents):
    """Doc tat ca documents va build Fack knowledge."""

    fack = []

    for document in tqdm(
        documents,
        desc="Building Fack",
        unit="document",
        dynamic_ncols=True,
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}"
    ):

        result = extract_knowledge(
            document
        )

        if result is None:
            continue

        knowledge = normalize_knowledge(
            result,
            document
        )

        fack.extend(
            knowledge
        )

    return fack


# ============================================================
# REMOVE DUPLICATES
# ============================================================

def remove_duplicates(knowledge):
    """Loai bo knowledge trung nhau."""

    unique = []
    seen = set()

    for item in knowledge:

        key = (
            item.get("type"),
            item.get("name", "").lower(),
            item.get("domain", "")
        )

        if key in seen:
            continue

        seen.add(key)

        unique.append(
            item
        )

    return unique


# ============================================================
# SAVE FACK
# ============================================================

def save_fack(knowledge):
    """Luu business knowledge vao fack.json."""

    FACK_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    data = {
        "knowledge": knowledge
    }

    with open(
        FACK_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# MAIN
# ============================================================

def main():

    documents = load_documents()

    if not documents:
        print(
            "Fack Builder failed: documents.json is empty."
        )
        return

    knowledge = build_fack(
        documents
    )

    knowledge = remove_duplicates(
        knowledge
    )

    save_fack(
        knowledge
    )

    print(
        "Fack Builder is running..."
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()