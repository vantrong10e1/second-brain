from pathlib import Path
import json
import re
import requests

from collections import defaultdict
from tqdm import tqdm


# ============================================================
# CONFIG
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"

DOCUMENTS_FILE = DATA_DIR / "documents.json"
OUTPUT_FILE = DATA_DIR / "entities.json"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

TIMEOUT = 300


# ============================================================
# LOAD DOCUMENTS
# ============================================================

def load_documents():
    """Doc documents tu documents.json."""

    try:
        with open(DOCUMENTS_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    except (FileNotFoundError, json.JSONDecodeError, OSError) as error:
        print("Khong the load documents:", error)
        return []


# ============================================================
# GROUP DOCUMENTS BY SOURCE
# ============================================================

def group_documents_by_source(documents):
    """Gom cac chunk theo source."""

    documents_by_source = defaultdict(list)

    for document in documents:
        source = document.get("source", "unknown")
        documents_by_source[source].append(document)

    return documents_by_source


# ============================================================
# CREATE ENTITY ID
# ============================================================

def make_entity_id(name):
    """Tao entity ID tu canonical name."""

    name = str(name).lower().strip()

    name = re.sub(
        r"[^a-z0-9]+",
        "-",
        name
    )

    return name.strip("-")


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_text(text):
    """Chuan hoa text de so sanh."""

    if not isinstance(text, str):
        return ""

    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)

    return text


# ============================================================
# CLEAN JSON RESPONSE
# ============================================================

def clean_json_response(raw_response):
    """Lam sach response JSON cua LLM."""

    if not raw_response:
        return ""

    raw_response = raw_response.strip()

    raw_response = re.sub(
        r"```json",
        "",
        raw_response,
        flags=re.IGNORECASE
    )

    raw_response = raw_response.replace(
        "```",
        ""
    ).strip()

    start = raw_response.find("{")
    end = raw_response.rfind("}")

    if start != -1 and end != -1:
        raw_response = raw_response[start:end + 1]

    return raw_response


# ============================================================
# EXTRACT ENTITIES
# ============================================================

def extract_entities(source, chunks):
    """Dung Ollama de trich xuat entity tu tai lieu."""

    content = "\n\n".join(
        document.get("content", "")
        for document in chunks
    )

    content = content[:12000]

    domain = chunks[0].get(
        "domain",
        "unknown"
    )

    prompt = f"""
Bạn là hệ thống Entity Extraction của Second Brain.

Hãy đọc tài liệu và tìm những entity kỹ thuật quan trọng.

MỤC TIÊU:

Phải tìm entity chính mà tài liệu đang nói về.

Các loại entity có thể gồm:

- programming language
- framework
- library
- software
- tool
- AI concept
- technology
- programming concept
- product
- technical concept

Ví dụ:

C#
Java
Python
Claude
Claude Code
RAG
LLM
Vector Database
Embedding
Class
Object
Inheritance

Không lấy những từ quá chung chung như:

system
information
thing
example
question

CANONICAL NAME:

canonical_name là tên chuẩn của entity.

Ví dụ:

C#
Java
Claude Code
RAG
Vector Database

ALIASES:

aliases là các cách người dùng có thể viết CHÍNH entity đó.

Ví dụ C#:

[
    "C#",
    "c#",
    "C Sharp",
    "c sharp",
    "csharp"
]

Ví dụ Java:

[
    "Java",
    "java"
]

Ví dụ Claude Code:

[
    "Claude Code",
    "claude code"
]

QUAN TRỌNG:

Alias phải thực sự chỉ đến canonical_name đó.

Không được đưa tên của entity khác vào aliases.

Ví dụ:

Java KHÔNG được:

[
    "Java",
    "java",
    "C#"
]

C# phải thuộc entity C#.

Canonical name phải luôn nằm trong aliases.

DOMAIN:

{domain}

SOURCE:

{source}

DOCUMENT:

{content}

Hãy đặc biệt chú ý:

1. Tên sản phẩm hoặc công nghệ chính.
2. Tên xuất hiện trong SOURCE.
3. Tên xuất hiện nhiều lần trong DOCUMENT.
4. Entity mà tài liệu đang giải thích.
5. Entity mà người dùng có khả năng dùng để tìm tài liệu.

Chỉ trả về JSON.

Không giải thích.

FORMAT:

{{
    "entities": [
        {{
            "canonical_name": "C#",
            "aliases": [
                "C#",
                "c#",
                "C Sharp",
                "c sharp",
                "csharp"
            ]
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
        return []

    try:
        data = response.json()

    except ValueError:
        return []

    raw_response = data.get(
        "response",
        ""
    )

    raw_response = clean_json_response(
        raw_response
    )

    try:
        result = json.loads(
            raw_response
        )

    except json.JSONDecodeError:
        return []

    extracted_entities = result.get(
        "entities",
        []
    )

    if not isinstance(
        extracted_entities,
        list
    ):
        return []

    valid_entities = []

    for entity in extracted_entities:

        if not isinstance(
            entity,
            dict
        ):
            continue

        canonical_name = entity.get(
            "canonical_name",
            ""
        )

        if not isinstance(
            canonical_name,
            str
        ):
            continue

        canonical_name = canonical_name.strip()

        if not canonical_name:
            continue

        aliases = entity.get(
            "aliases",
            []
        )

        if not isinstance(
            aliases,
            list
        ):
            aliases = []

        aliases.append(
            canonical_name
        )

        cleaned_aliases = []

        for alias in aliases:

            if not isinstance(
                alias,
                str
            ):
                continue

            alias = alias.strip()

            if not alias:
                continue

            if alias not in cleaned_aliases:
                cleaned_aliases.append(
                    alias
                )

        valid_entities.append({
            "canonical_name": canonical_name,
            "aliases": cleaned_aliases
        })

    return valid_entities


# ============================================================
# NORMALIZE EXTRACTED ENTITIES
# ============================================================

def normalize_extracted_entities(extracted_entities):
    """Chuan hoa entity va loai entity trung."""

    normalized = {}

    for entity in extracted_entities:

        canonical_name = entity.get(
            "canonical_name",
            ""
        )

        if not isinstance(
            canonical_name,
            str
        ):
            continue

        canonical_name = canonical_name.strip()

        if not canonical_name:
            continue

        entity_id = make_entity_id(
            canonical_name
        )

        if not entity_id:
            continue

        if entity_id not in normalized:

            normalized[entity_id] = {
                "canonical_name": canonical_name,
                "aliases": []
            }

        aliases = entity.get(
            "aliases",
            []
        )

        if not isinstance(
            aliases,
            list
        ):
            aliases = []

        aliases.append(
            canonical_name
        )

        for alias in aliases:

            if not isinstance(
                alias,
                str
            ):
                continue

            alias = alias.strip()

            if not alias:
                continue

            if alias not in normalized[
                entity_id
            ]["aliases"]:

                normalized[
                    entity_id
                ]["aliases"].append(alias)

    return list(
        normalized.values()
    )


# ============================================================
# BUILD ENTITY DATABASE
# ============================================================

def build_entity_database(
    extracted_entities,
    source,
    domain
):
    """
    Tao entity database.

    Moi alias chi duoc thuoc mot entity.
    """

    entities = {}

    # --------------------------------------------------------
    # STEP 1: Create entities from canonical names
    # --------------------------------------------------------

    for entity in extracted_entities:

        canonical_name = entity.get(
            "canonical_name",
            ""
        )

        entity_id = make_entity_id(
            canonical_name
        )

        if not entity_id:
            continue

        if entity_id not in entities:

            entities[entity_id] = {
                "canonical_name": canonical_name,
                "aliases": [],
                "domains": [],
                "sources": []
            }

        current = entities[
            entity_id
        ]

        if canonical_name not in current[
            "aliases"
        ]:

            current[
                "aliases"
            ].append(
                canonical_name
            )

        if domain not in current[
            "domains"
        ]:

            current[
                "domains"
            ].append(
                domain
            )

        if source not in current[
            "sources"
        ]:

            current[
                "sources"
            ].append(
                source
            )

    # --------------------------------------------------------
    # STEP 2: Build canonical registry
    # --------------------------------------------------------

    canonical_registry = {}

    for entity_id, entity in entities.items():

        canonical_name = entity.get(
            "canonical_name",
            ""
        )

        canonical_key = normalize_text(
            canonical_name
        )

        if canonical_key:

            canonical_registry[
                canonical_key
            ] = entity_id

    # --------------------------------------------------------
    # STEP 3: Build alias registry
    # --------------------------------------------------------

    alias_registry = {}

    for entity_id, entity in entities.items():

        canonical_name = entity.get(
            "canonical_name",
            ""
        )

        canonical_key = normalize_text(
            canonical_name
        )

        if canonical_key:

            alias_registry[
                canonical_key
            ] = entity_id

    # --------------------------------------------------------
    # STEP 4: Add aliases
    # --------------------------------------------------------

    for entity in extracted_entities:

        canonical_name = entity.get(
            "canonical_name",
            ""
        )

        entity_id = make_entity_id(
            canonical_name
        )

        if entity_id not in entities:
            continue

        aliases = entity.get(
            "aliases",
            []
        )

        for alias in aliases:

            if not isinstance(
                alias,
                str
            ):
                continue

            alias = alias.strip()

            if not alias:
                continue

            alias_key = normalize_text(
                alias
            )

            if not alias_key:
                continue

            # ------------------------------------------------
            # Canonical name always wins.
            # ------------------------------------------------

            canonical_owner = canonical_registry.get(
                alias_key
            )

            if canonical_owner is not None:

                if canonical_owner != entity_id:
                    continue

            # ------------------------------------------------
            # Alias already belongs to another entity.
            # ------------------------------------------------

            existing_owner = alias_registry.get(
                alias_key
            )

            if existing_owner is not None:

                if existing_owner != entity_id:
                    continue

            # ------------------------------------------------
            # Add alias.
            # ------------------------------------------------

            alias_registry[
                alias_key
            ] = entity_id

            if alias not in entities[
                entity_id
            ]["aliases"]:

                entities[
                    entity_id
                ]["aliases"].append(
                    alias
                )

    return entities


# ============================================================
# MERGE ENTITIES
# ============================================================

def merge_entities(
    entities,
    extracted_entities,
    source,
    domain
):
    """Merge entity moi vao entity database."""

    normalized_entities = normalize_extracted_entities(
        extracted_entities
    )

    # --------------------------------------------------------
    # STEP 1: Create missing entities.
    # --------------------------------------------------------

    for entity in normalized_entities:

        canonical_name = entity.get(
            "canonical_name",
            ""
        )

        entity_id = make_entity_id(
            canonical_name
        )

        if not entity_id:
            continue

        if entity_id not in entities:

            entities[entity_id] = {
                "canonical_name": canonical_name,
                "aliases": [],
                "domains": [],
                "sources": []
            }

        current = entities[
            entity_id
        ]

        if domain not in current[
            "domains"
        ]:

            current[
                "domains"
            ].append(
                domain
            )

        if source not in current[
            "sources"
        ]:

            current[
                "sources"
            ].append(
                source
            )

        if canonical_name not in current[
            "aliases"
        ]:

            current[
                "aliases"
            ].append(
                canonical_name
            )

    # --------------------------------------------------------
    # STEP 2: Build canonical registry.
    # --------------------------------------------------------

    canonical_registry = {}

    for entity_id, entity in entities.items():

        canonical_name = entity.get(
            "canonical_name",
            ""
        )

        canonical_key = normalize_text(
            canonical_name
        )

        if canonical_key:

            canonical_registry[
                canonical_key
            ] = entity_id

    # --------------------------------------------------------
    # STEP 3: Build alias registry.
    # --------------------------------------------------------

    alias_registry = {}

    for entity_id, entity in entities.items():

        for alias in entity.get(
            "aliases",
            []
        ):

            alias_key = normalize_text(
                alias
            )

            if not alias_key:
                continue

            if alias_key not in alias_registry:

                alias_registry[
                    alias_key
                ] = entity_id

    # --------------------------------------------------------
    # STEP 4: Add new aliases safely.
    # --------------------------------------------------------

    for entity in normalized_entities:

        canonical_name = entity.get(
            "canonical_name",
            ""
        )

        entity_id = make_entity_id(
            canonical_name
        )

        if entity_id not in entities:
            continue

        aliases = entity.get(
            "aliases",
            []
        )

        for alias in aliases:

            if not isinstance(
                alias,
                str
            ):
                continue

            alias = alias.strip()

            if not alias:
                continue

            alias_key = normalize_text(
                alias
            )

            if not alias_key:
                continue

            # Canonical name of another entity.
            canonical_owner = canonical_registry.get(
                alias_key
            )

            if canonical_owner is not None:

                if canonical_owner != entity_id:
                    continue

            # Alias already belongs to another entity.
            existing_owner = alias_registry.get(
                alias_key
            )

            if existing_owner is not None:

                if existing_owner != entity_id:
                    continue

            alias_registry[
                alias_key
            ] = entity_id

            if alias not in entities[
                entity_id
            ]["aliases"]:

                entities[
                    entity_id
                ]["aliases"].append(
                    alias
                )


# ============================================================
# CLEAN ALIAS CONFLICTS
# ============================================================

def clean_alias_conflicts(entities):
    """
    Kiem tra lai alias sau khi merge.

    Neu alias thuoc nhieu entity,
    chi giu alias cho entity co canonical name trung alias.
    """

    # --------------------------------------------------------
    # STEP 1: Find canonical owners.
    # --------------------------------------------------------

    canonical_owners = {}

    for entity_id, entity in entities.items():

        canonical_name = entity.get(
            "canonical_name",
            ""
        )

        canonical_key = normalize_text(
            canonical_name
        )

        if canonical_key:

            canonical_owners[
                canonical_key
            ] = entity_id

    # --------------------------------------------------------
    # STEP 2: Clean aliases.
    # --------------------------------------------------------

    alias_owners = {}

    for entity_id, entity in entities.items():

        cleaned_aliases = []

        for alias in entity.get(
            "aliases",
            []
        ):

            alias_key = normalize_text(
                alias
            )

            if not alias_key:
                continue

            # Canonical name has highest priority.

            canonical_owner = canonical_owners.get(
                alias_key
            )

            if canonical_owner is not None:

                if canonical_owner != entity_id:
                    continue

            # Alias already belongs to another entity.

            existing_owner = alias_owners.get(
                alias_key
            )

            if existing_owner is not None:

                if existing_owner != entity_id:
                    continue

            alias_owners[
                alias_key
            ] = entity_id

            if alias not in cleaned_aliases:

                cleaned_aliases.append(
                    alias
                )

        # ----------------------------------------------------
        # Ensure canonical name exists.
        # ----------------------------------------------------

        canonical_name = entity.get(
            "canonical_name",
            ""
        )

        if canonical_name:

            if canonical_name not in cleaned_aliases:

                cleaned_aliases.insert(
                    0,
                    canonical_name
                )

        entity[
            "aliases"
        ] = cleaned_aliases


# ============================================================
# SAVE ENTITIES
# ============================================================

def save_entities(entities):
    """Luu entities.json."""

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
            entities,
            file,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# DISPLAY STATISTICS
# ============================================================

def display_statistics(entities):
    """Hien thong ke."""

    total_entities = len(
        entities
    )

    total_aliases = sum(
        len(
            entity.get(
                "aliases",
                []
            )
        )
        for entity in entities.values()
    )

    print(
        "Entities:",
        total_entities
    )

    print(
        "Aliases:",
        total_aliases
    )

    print(
        "Output:",
        OUTPUT_FILE
    )


# ============================================================
# BUILD ENTITIES
# ============================================================

def build_entities(show_progress=False):
    """Build entity database tu documents.json."""

    documents = load_documents()

    if not documents:
        return {}

    documents_by_source = group_documents_by_source(
        documents
    )

    entities = {}

    sources = documents_by_source.items()

    if show_progress:

        sources = tqdm(
            sources,
            total=len(documents_by_source),
            desc="Building entities",
            unit="source",
            dynamic_ncols=True,
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}"
        )

    for source, chunks in sources:

        domain = chunks[0].get(
            "domain",
            "unknown"
        )

        extracted_entities = extract_entities(
            source,
            chunks
        )

        if not extracted_entities:
            continue

        merge_entities(
            entities,
            extracted_entities,
            source,
            domain
        )

    # ========================================================
    # FINAL CONFLICT CLEANUP
    # ========================================================

    clean_alias_conflicts(
        entities
    )

    # ========================================================
    # SAVE
    # ========================================================

    save_entities(
        entities
    )

    return entities


# ============================================================
# MODULE STATUS
# ============================================================

if __name__ == "__main__":

    print(
        "Building entity database..."
    )

    entities = build_entities(
        show_progress=True
    )

    print()

    display_statistics(
        entities
    )

    print(
        "Build Entities finished!"
    )