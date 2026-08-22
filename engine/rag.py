from pathlib import Path
import json
import requests
import msvcrt
import re
import subprocess
import sys
import os

from dotenv import load_dotenv
from langfuse import get_client

from tqdm import tqdm
from colorama import Fore, Style, init

from query_understanding import understand_query, load_domains
from ner import extract_entities
from entity_resolution import resolve_entities, build_candidates
from domain_search import domain_search
from search import search
from rag_retrieval import retrieve
from hybrid_search import hybrid_search
from reranker import rerank

from memory import (
    load_memory,
    add_user_message,
    add_assistant_message,
    get_recent_memory,
    get_memory_text,
    get_last_entity
)

from evaluation import evaluate_rag


# ============================================================
# COLOR
# ============================================================

init(autoreset=True)

TITLE = Fore.GREEN


# ============================================================
# CONFIG
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"

ENV_FILE = PROJECT_DIR / "config" / ".env"
load_dotenv(ENV_FILE)

LANGFUSE_ENABLED = all([
    os.getenv("LANGFUSE_PUBLIC_KEY"),
    os.getenv("LANGFUSE_SECRET_KEY"),
])

langfuse = get_client() if LANGFUSE_ENABLED else None

CATALOG_FILE = DATA_DIR / "data_catalog.json"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

DOMAIN_TOP_K = 5
SEARCH_TOP_K = 5
RETRIEVAL_TOP_K = 5
HYBRID_TOP_K = 5
RERANK_TOP_K = 2
FACK_TOP_K = 5


# ============================================================
# LANGFUSE
# ============================================================

def _safe_trace_output(value, max_length=2000):
    """Keep Langfuse trace output compact."""
    if value is None:
        return None

    if isinstance(value, str):
        return value[:max_length]

    if isinstance(value, (int, float, bool)):
        return value

    if isinstance(value, list):
        return {
            "count": len(value),
            "items": [
                _safe_trace_output(item, 500)
                for item in value[:5]
            ]
        }

    if isinstance(value, dict):
        output = {}
        for key, item in list(value.items())[:20]:
            output[str(key)] = _safe_trace_output(item, 500)
        return output

    return str(value)[:max_length]


def trace_call(name, function, input_data=None, as_type="span"):
    """Run one RAG operation and record it in Langfuse."""
    if not LANGFUSE_ENABLED:
        return function()

    with langfuse.start_as_current_observation(
        as_type=as_type,
        name=name,
        input=input_data
    ) as observation:
        try:
            result = function()
            observation.update(
                output=_safe_trace_output(result)
            )
            return result
        except Exception as error:
            observation.update(
                level="ERROR",
                status_message=str(error)
            )
            raise


def flush_langfuse():
    """Flush pending Langfuse events."""
    if LANGFUSE_ENABLED:
        langfuse.flush()


# ============================================================
# SYSTEM INITIALIZATION
# ============================================================

def initialize_system():
    """Load and initialize RAG system modules."""

    steps = [
        ("Query Understanding", load_domains),
        ("NER", lambda: True),
        ("Entity Resolution", build_candidates),
        ("Central Data Catalog", load_catalog),
        ("Domain Search", lambda: True),
        ("Search", lambda: True),
        ("RAG Retrieval", lambda: True),
        ("Hybrid Search", lambda: True),
        ("Reranker", lambda: True),
        ("Memory", load_memory),
        ("Evaluation", lambda: True)
    ]

    for _, function in tqdm(
        steps,
        desc="Loading system",
        unit="module",
        dynamic_ncols=True,
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}"
    ):
        function()

    print("System ready.")


# ============================================================
# CENTRAL DATA CATALOG
# ============================================================

def load_fack():
    """Load Fack business knowledge."""

    fack_file = DATA_DIR / "fack.json"

    if not fack_file.exists():
        return []

    try:
        with open(fack_file, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data.get("knowledge", [])
    except (json.JSONDecodeError, OSError):
        return []


def _fack_text(item):
    """Build searchable text from one Fack item."""

    return " ".join([
        str(item.get("name", "")),
        str(item.get("definition", "")),
        str(item.get("description", "")),
        str(item.get("rule", "")),
        str(item.get("sql", "")),
    ]).lower()


def search_fack(query, domain, resolved_entities, top_k=FACK_TOP_K):
    """Find Fack knowledge relevant to the current query."""

    knowledge = load_fack()
    if not knowledge:
        return []

    query_lower = query.lower()
    query_terms = set(re.findall(r"[\wÀ-ỹ+#.-]+", query_lower))

    entity_names = {
        str(item.get("canonical_name", "")).lower()
        for item in resolved_entities
        if item.get("canonical_name")
    }

    scored = []

    for item in knowledge:
        if domain and item.get("domain") != domain:
            continue

        name = str(item.get("name", "")).strip()
        name_lower = name.lower()
        text = _fack_text(item)

        score = 0

        if name_lower and name_lower in query_lower:
            score += 10

        if name_lower in entity_names:
            score += 20

        score += sum(1 for term in query_terms if term in text)

        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:top_k]]


def build_fack_context(results):
    """Convert Fack knowledge into LLM context."""

    context = []

    for index, item in enumerate(results, start=1):
        knowledge_type = item.get("type", "unknown")
        name = item.get("name", "unknown")
        source = item.get("source", "unknown")

        if knowledge_type == "term":
            detail = item.get("definition", "")
        elif knowledge_type == "business_rule":
            detail = item.get("rule", "")
        elif knowledge_type == "metric":
            detail = item.get("definition", "")
        elif knowledge_type == "entity":
            detail = item.get("description", "")
        elif knowledge_type == "sql_example":
            detail = item.get("sql", "")
        else:
            detail = ""

        context.append(
            f"FACK {index}\n"
            f"TYPE: {knowledge_type}\n"
            f"NAME: {name}\n"
            f"SOURCE: {source}\n"
            f"CONTENT: {detail}"
        )

    return "\n\n".join(context)


def load_catalog():
    """Load Central Data Catalog."""

    if not CATALOG_FILE.exists():
        return []

    try:

        with open(
            CATALOG_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except (
        json.JSONDecodeError,
        OSError
    ):

        return []


def select_catalog_sources(
    catalog,
    domain
):
    """Select active sources for a domain."""

    sources = []

    for item in catalog:

        item_domain = item.get(
            "domain",
            []
        )

        status = item.get(
            "status"
        )

        source = item.get(
            "source"
        )

        if domain not in item_domain:
            continue

        if status != "active":
            continue

        if not source:
            continue

        sources.append(
            source
        )

    return sources


def normalize_source(source):
    """Normalize source path."""

    return str(
        source
    ).replace(
        "\\",
        "/"
    ).lower()


# ============================================================
# SETUP DATA
# ============================================================

def setup_data():
    """Run run_build_data.py to setup RAG data."""

    build_file = (
        Path(__file__).resolve().parent.parent
        / "scripts"
        / "run_build_data.py"
    )

    print()

    print(
        f"{TITLE}Setup data:{Style.RESET_ALL}"
    )

    if not build_file.exists():

        print(
            "run_build_data.py not found."
        )

        print(
            "Expected path:",
            build_file
        )

        return False

    print(
        "Setting up data..."
    )

    result = subprocess.run(
        [
            sys.executable,
            str(build_file)
        ],
        cwd=build_file.parent
    )

    print()

    if result.returncode == 0:

        print(
            f"{TITLE}Setup data finished!"
            f"{Style.RESET_ALL}"
        )

        return True

    print(
        f"{TITLE}Setup data failed!"
        f"{Style.RESET_ALL}"
    )

    return False


# ============================================================
# QUERY CONTEXTUALIZATION
# ============================================================

def contextualize_query(
    query,
    memory
):
    """
    Resolve references using the latest entity
    from conversation memory.

    Example:

        C# la gi?

        Ung dung cua no la gi?

    Becomes:

        Ung dung cua C# la gi?
    """

    if not memory:
        return query

    entity = get_last_entity()

    if not entity:
        return query

    canonical_name = entity.get(
        "canonical_name"
    )

    if not canonical_name:
        return query

    reference_words = [
        "cái này",
        "cai nay",
        "cái đó",
        "cai do",
        "công cụ này",
        "cong cu nay",
        "ngôn ngữ này",
        "ngon ngu nay",
        "phần mềm này",
        "phan mem nay",
        "nó",
        "no",
        "này",
        "nay",
        "đó",
        "do"
    ]

    rewritten_query = query

    for reference in reference_words:

        pattern = re.escape(
            reference
        )

        if re.search(
            pattern,
            rewritten_query,
            flags=re.IGNORECASE
        ):

            rewritten_query = re.sub(
                pattern,
                canonical_name,
                rewritten_query,
                count=1,
                flags=re.IGNORECASE
            )

            break

    return rewritten_query


# ============================================================
# LLM
# ============================================================

def ask_llm(
    query,
    context,
    memory
):
    """Send query, memory and RAG context to Ollama."""

    prompt = f"""
Bạn là trợ lý Second Brain.

Bạn có ba nguồn context:

1. CONVERSATION MEMORY

Lịch sử hội thoại trước đó.

2. FACK CONTEXT

Knowledge có cấu trúc về term, entity, business rule, metric
và SQL example được trích xuất từ knowledge base.

3. DOCUMENT CONTEXT

Nội dung document được RAG retrieval và reranker chọn ra.

RULES:

- Conversation Memory chỉ dùng để hiểu ngữ cảnh.
- Fack Context dùng để bổ sung thông tin có cấu trúc về entity và knowledge.
- Document Context là nguồn nội dung chính để kiểm chứng câu trả lời.
- Chỉ trả lời dựa trên Fack Context và Document Context.
- Không dùng kiến thức bên ngoài các context trên.
- Không bịa thông tin.
- Nếu RAG Context không đủ thông tin, hãy nói:

"Tài liệu không cung cấp đủ thông tin để trả lời câu hỏi này."

CONVERSATION MEMORY:

{memory}

RAG CONTEXT:

{context}

CURRENT QUESTION:

{query}

ANSWER:
"""

    def call_ollama():
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

        return response.json().get(
            "response",
            ""
        ).strip()

    try:
        if not LANGFUSE_ENABLED:
            return call_ollama()

        with langfuse.start_as_current_observation(
            as_type="generation",
            name="ollama-generation",
            model=OLLAMA_MODEL,
            input={
                "query": query,
                "context": context,
                "memory": memory
            }
        ) as generation:
            answer = call_ollama()
            generation.update(
                output=answer
            )
            return answer

    except requests.exceptions.RequestException:
        return ""


# ============================================================
# DISPLAY RESULTS
# ============================================================

def display_results(
    title,
    results,
    limit=5
):
    """Display search results with clean section spacing."""

    print()

    print(
        f"{TITLE}  {title}:{Style.RESET_ALL}"
    )

    for index, result in enumerate(
        results[:limit],
        start=1
    ):

        document = result.get(
            "document",
            {}
        )

        source = document.get(
            "source",
            "unknown"
        )

        content = document.get(
            "content",
            ""
        )

        content = content.replace(
            "\n",
            " "
        ).strip()

        if len(content) > 150:

            content = (
                content[:150]
                + "..."
            )

        print(
            f"    - [{index}] {source}: {content}"
        )


# ============================================================
# DISPLAY CATALOG
# ============================================================

def display_catalog(
    sources
):
    """Display selected catalog sources."""

    print()

    print(
        f"{TITLE}  Central Data Catalog:"
        f"{Style.RESET_ALL}"
    )

    for source in sources:

        print(
            f"    - {Path(source).name}"
        )


# ============================================================
# DISPLAY FACK CONTEXT
# ============================================================

def display_fack_context(
    fack_context
):
    """Display the exact Fack knowledge that will enter the LLM."""

    print()

    print(
        f"{TITLE}  Fack Context:{Style.RESET_ALL}"
    )

    if not fack_context:

        print(
            "    - None"
        )

        return

    for line in fack_context.splitlines():

        if line.strip():

            print(
                f"    {line}"
            )


# ============================================================
# DISPLAY FINAL LLM CONTEXT
# ============================================================

def display_final_llm_context(
    fack_context,
    document_context
):
    """Display the final context assembled for the LLM."""

    print()

    print(
        f"{TITLE}  Final LLM Context:{Style.RESET_ALL}"
    )

    print(
        "    FACK CONTEXT:"
    )

    if fack_context:

        for line in fack_context.splitlines():

            if line.strip():

                print(
                    f"      {line}"
                )

    else:

        print(
            "      - None"
        )

    print()

    print(
        "    DOCUMENT CONTEXT:"
    )

    if document_context:

        for line in document_context.splitlines():

            if line.strip():

                print(
                    f"      {line}"
                )

    else:

        print(
            "      - None"
        )


# ============================================================
# BUILD CONTEXT
# ============================================================

def build_context(
    results
):
    """Build context for LLM."""

    context = []

    for index, result in enumerate(
        results,
        start=1
    ):

        document = result.get(
            "document",
            {}
        )

        context.append(
            f"CHUNK {index}\n"
            f"SOURCE: {document.get('source', 'unknown')}\n"
            f"CONTENT:\n{document.get('content', '')}"
        )

    return "\n\n".join(
        context
    )


# ============================================================
# DISPLAY EVALUATION
# ============================================================

def display_evaluation(
    result
):
    """Display evaluation result."""

    print()

    print()
    print(
        f"{TITLE}  Evaluation:{Style.RESET_ALL}"
    )

    print(
        f"    - Faithfulness: {result['faithfulness']} /10"
    )

    print(
        f"    - Groundedness: {result['groundedness']} /10"
    )

    print(
        f"    - Relevance: {result['answer_relevance']} /10"
    )

    print(
        f"    - Correctness: {result['correctness']} /10"
    )

    print(
        f"    - Overall: {result['overall']} /10"
    )


# ============================================================
# RAG PIPELINE
# ============================================================

def _run_rag(
    query,
    trace_id=None
):
    """Run query through the complete RAG pipeline."""

    print()

    print(
        f"{TITLE}Processing:{Style.RESET_ALL}"
    )

    # ========================================================
    # 1. MEMORY
    # ========================================================

    memory = trace_call(
        "memory-load",
        get_recent_memory
    )

    memory_text = get_memory_text()

    print(
        f"{TITLE}  Memory:{Style.RESET_ALL}",
        "loaded"
        if memory
        else "empty"
    )

    # ========================================================
    # 2. ENTITY MEMORY / REFERENCE RESOLUTION
    # ========================================================

    last_entity = get_last_entity()

    if last_entity:

        print(
            f"{TITLE}  Memory Entity:"
            f"{Style.RESET_ALL}",
            last_entity.get(
                "canonical_name",
                "unknown"
            )
        )

    else:

        print(
            f"{TITLE}  Memory Entity:"
            f"{Style.RESET_ALL}",
            "None"
        )

    contextualized_query = trace_call(
        "query-contextualization",
        lambda: contextualize_query(query, memory),
        {"query": query, "memory": memory}
    )

    print(
        f"{TITLE}  Contextualized Query:"
        f"{Style.RESET_ALL}",
        contextualized_query
    )

    # ========================================================
    # 3. QUERY UNDERSTANDING
    # ========================================================

    query_info = trace_call(
        "query-understanding",
        lambda: understand_query(contextualized_query),
        {"query": contextualized_query}
    )

    if not query_info:

        print(
            f"{TITLE}  Query Understanding:"
            f"{Style.RESET_ALL}",
            "failed"
        )

        return None

    print()
    print(
        f"{TITLE}  Query Understanding:"
        f"{Style.RESET_ALL}"
    )

    print(
        f"    - intent: {query_info.get('intent')}"
    )

    print(
        f"    - domain: {query_info.get('domain')}"
    )

    print(
        f"    - topic: {query_info.get('topic')}"
    )

    # ========================================================
    # 4. NER
    # ========================================================

    ner_result = trace_call(
        "ner",
        lambda: extract_entities(contextualized_query),
        {"query": contextualized_query}
    )

    ner_entities = ner_result.get(
        "entities",
        []
    )

    print()
    print(
        f"{TITLE}  NER:{Style.RESET_ALL}"
    )

    for entity in ner_entities:

        print(
            f"    - {entity.get('text')} → {entity.get('type')}"
        )

    # ========================================================
    # 5. ENTITY RESOLUTION
    # ========================================================

    resolution_result = trace_call(
        "entity-resolution",
        lambda: resolve_entities(ner_entities),
        {"entities": ner_entities}
    )

    resolved_entities = resolution_result.get(
        "resolved",
        []
    )

    not_found = resolution_result.get(
        "not_found",
        []
    )

    ambiguous = resolution_result.get(
        "ambiguous",
        []
    )

    print()
    print(
        f"{TITLE}  Entity Resolution:"
        f"{Style.RESET_ALL}"
    )

    for entity in resolved_entities:

        print(
            f"    - {entity.get('canonical_name')} "
            f"→ {entity.get('entity_id')}"
        )

    if ambiguous:

        print(
            "    - AMBIGUOUS"
        )

    if not_found:

        print(
            f"    - NOT_FOUND: {len(not_found)}"
        )

    # ========================================================
    # ENTITY VALIDATION
    # ========================================================

    if ambiguous:

        print(
            f"{TITLE}  RAG:{Style.RESET_ALL}",
            "entity is ambiguous"
        )

        return None

    if ner_entities and not resolved_entities:

        print(
            f"{TITLE}  RAG:{Style.RESET_ALL}",
            "entity not found"
        )

        return None

    # ========================================================
    # 7. CENTRAL DATA CATALOG
    # ========================================================

    domain = query_info.get(
        "domain"
    )

    # ========================================================
    # 6. FACK SEARCH
    # ========================================================

    fack_results = trace_call(
        "fack-search",
        lambda: search_fack(
            contextualized_query,
            domain,
            resolved_entities,
            top_k=FACK_TOP_K
        ),
        {
            "query": contextualized_query,
            "domain": domain,
            "entities": resolved_entities
        },
        as_type="retriever"
    )

    print()
    print(
        f"{TITLE}  Fack Search:{Style.RESET_ALL}"
    )

    for index, item in enumerate(fack_results, start=1):
        print(
            f"    - [{index}] {item.get('type')} | "
            f"{item.get('name')} | "
            f"{item.get('source', 'unknown')}"
        )

    fack_context = build_fack_context(
        fack_results
    )

    display_fack_context(
        fack_context
    )

    # ========================================================
    # 7. CENTRAL DATA CATALOG
    # ========================================================

    catalog = load_catalog()

    allowed_sources = select_catalog_sources(
        catalog,
        domain
    )

    display_catalog(
        allowed_sources
    )

    if not allowed_sources:

        print(
            f"{TITLE}  Central Data Catalog:"
            f"{Style.RESET_ALL}",
            "no valid source"
        )

        return None

    allowed_source_set = {
        normalize_source(source)
        for source in allowed_sources
    }

    # ========================================================
    # 8. DOMAIN SEARCH
    # ========================================================

    domain_results = trace_call(
        "domain-search",
        lambda: domain_search(
            contextualized_query,
            domain,
            top_k=DOMAIN_TOP_K
        ),
        {"query": contextualized_query, "domain": domain},
        as_type="retriever"
    )

    domain_results = [
        result
        for result in domain_results
        if normalize_source(
            result.get(
                "document",
                {}
            ).get(
                "source",
                ""
            )
        ) in allowed_source_set
    ]

    display_results(
        "Domain Search",
        domain_results,
        DOMAIN_TOP_K
    )

    search_documents = [
        result["document"]
        for result in domain_results
        if "document" in result
    ]

    # ========================================================
    # 9. SEARCH
    # ========================================================

    search_results = trace_call(
        "vector-search",
        lambda: search(
            contextualized_query,
            documents=search_documents,
            top_k=SEARCH_TOP_K
        ),
        {
            "query": contextualized_query,
            "document_count": len(search_documents)
        },
        as_type="retriever"
    )

    display_results(
        "Search",
        search_results,
        SEARCH_TOP_K
    )

    # ========================================================
    # 10. RAG RETRIEVAL
    # ========================================================

    retrieval_results = trace_call(
        "rag-retrieval",
        lambda: retrieve(
            query=contextualized_query,
            domain=domain,
            resolved_entities=resolved_entities,
            top_k=RETRIEVAL_TOP_K
        ),
        {
            "query": contextualized_query,
            "domain": domain,
            "entities": resolved_entities
        },
        as_type="retriever"
    )

    retrieval_results = [
        result
        for result in retrieval_results
        if normalize_source(
            result.get(
                "document",
                {}
            ).get(
                "source",
                ""
            )
        ) in allowed_source_set
    ]

    display_results(
        "RAG Retrieval",
        retrieval_results,
        RETRIEVAL_TOP_K
    )

    candidate_documents = [
        result["document"]
        for result in retrieval_results
        if result.get("document")
    ]

    if not candidate_documents:

        print(
            f"{TITLE}  RAG Retrieval:"
            f"{Style.RESET_ALL}",
            "no documents"
        )

        return None

    # ========================================================
    # 11. HYBRID SEARCH
    # ========================================================

    hybrid_results = trace_call(
        "hybrid-search",
        lambda: hybrid_search(
            contextualized_query,
            documents=candidate_documents,
            top_k=HYBRID_TOP_K
        ),
        {
            "query": contextualized_query,
            "candidate_count": len(candidate_documents)
        },
        as_type="retriever"
    )

    display_results(
        "Hybrid Search",
        hybrid_results,
        HYBRID_TOP_K
    )

    if not hybrid_results:

        print(
            f"{TITLE}  Hybrid Search:"
            f"{Style.RESET_ALL}",
            "no results"
        )

        return None

    # ========================================================
    # 12. RERANKER
    # ========================================================

    reranked_results = trace_call(
        "reranker",
        lambda: rerank(
            contextualized_query,
            hybrid_results,
            top_k=RERANK_TOP_K
        ),
        {
            "query": contextualized_query,
            "candidate_count": len(hybrid_results)
        },
        as_type="retriever"
    )

    display_results(
        "Reranker",
        reranked_results,
        RERANK_TOP_K
    )

    if not reranked_results:

        print(
            f"{TITLE}  LLM:{Style.RESET_ALL}",
            "no context"
        )

        return None

    # ========================================================
    # 13. BUILD CONTEXT
    # ========================================================

    document_context = build_context(
        reranked_results
    )

    context = f"""
FACK CONTEXT:
{fack_context}

DOCUMENT CONTEXT:
{document_context}
"""

    display_final_llm_context(
        fack_context,
        document_context
    )

    # ========================================================
    # 14. LLM
    # ========================================================

    answer = ask_llm(
        contextualized_query,
        context,
        memory_text
    )

    print(
        f"{TITLE}  LLM:{Style.RESET_ALL}",
        "generated"
        if answer
        else "failed"
    )

    if not answer:
        return None

    # ========================================================
    # 15. SAVE MEMORY + ENTITIES
    # ========================================================

    history = load_memory()

    add_user_message(
        history,
        query,
        resolved_entities
    )

    add_assistant_message(
        history,
        answer,
        resolved_entities
    )

    print(
        f"{TITLE}  Memory:{Style.RESET_ALL}",
        len(history),
        "messages",
        "| entities:",
        len(resolved_entities)
    )

    # ========================================================
    # 16. EVALUATION
    # ========================================================

    evaluation_result = evaluate_rag(
        query,
        context,
        answer,
        trace_id=trace_id
    )

    display_evaluation(
        evaluation_result
    )

    # ========================================================
    # RETURN RESULT
    # ========================================================

    return {
        "query": query,
        "contextualized_query": contextualized_query,
        "query_understanding": query_info,
        "ner": ner_result,
        "entity_resolution": resolution_result,
        "fack_results": fack_results,
        "fack_context": fack_context,
        "catalog_sources": allowed_sources,
        "domain_results": domain_results,
        "search_results": search_results,
        "retrieval_results": retrieval_results,
        "hybrid_results": hybrid_results,
        "reranked_results": reranked_results,
        "context": context,
        "memory": memory,
        "answer": answer,
        "evaluation": evaluation_result
    }


# ============================================================
# LANGFUSE ROOT TRACE
# ============================================================

def run_rag(query):
    """Run the complete RAG pipeline inside one Langfuse trace."""
    if not LANGFUSE_ENABLED:
        return _run_rag(query)

    with langfuse.start_as_current_observation(
        as_type="chain",
        name="rag-pipeline",
        input={"query": query},
        metadata={
            "ollama_model": OLLAMA_MODEL,
            "project": "second-brain"
        }
    ) as trace:
        try:
            result = _run_rag(
                query,
                trace_id=trace.trace_id
            )

            if result:
                trace.update(
                    output={
                        "answer": result.get("answer", ""),
                        "fack_results": len(result.get("fack_results", [])),
                        "retrieval_results": len(result.get("retrieval_results", [])),
                        "reranked_results": len(result.get("reranked_results", []))
                    }
                )
            else:
                trace.update(output={"status": "failed"})

            return result

        except Exception as error:
            trace.update(
                level="ERROR",
                status_message=str(error)
            )
            raise
        finally:
            flush_langfuse()


# ============================================================
# USER INPUT
# ============================================================

def get_question():
    """Get query and allow ESC to exit."""

    print()

    print(
        "Nhập câu hỏi của bạn (Nhấn ESC để Quit): ",
        end="",
        flush=True
    )

    query = ""

    while True:

        key = msvcrt.getwch()

        if key == "\x1b":

            print()

            print(
                f"{TITLE}RAG system stopped:"
                f"{Style.RESET_ALL}"
            )

            return None

        if key in (
            "\r",
            "\n"
        ):

            print()

            return query.strip()

        if key == "\b":

            if query:

                query = query[:-1]

                print(
                    "\b \b",
                    end="",
                    flush=True
                )

            continue

        if key in (
            "\x00",
            "\xe0"
        ):

            msvcrt.getwch()

            continue

        query += key

        print(
            key,
            end="",
            flush=True
        )


# ============================================================
# MAIN
# ============================================================

def main():
    """Start RAG system."""

    print(
        f"{TITLE}Second Brain RAG:{Style.RESET_ALL}"
    )

    print(
        f"{TITLE}Langfuse:{Style.RESET_ALL}",
        "enabled"
        if LANGFUSE_ENABLED
        else "disabled"
    )

    initialize_system()

    while True:

        print()

        print(
            "Nếu chưa thiết lập dữ liệu, nhập: setup-data"
        )

        query = get_question()

        if query is None:
            break

        if not query:
            continue

        if query.lower() == "setup-data":

            setup_data()

            continue

        result = run_rag(
            query
        )

        if not result:
            continue

        print()

        print(
            f"{TITLE}Answer:{Style.RESET_ALL}"
        )

        print(
            result["answer"]
        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()