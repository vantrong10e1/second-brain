import asyncio
import json
import os
import re
import requests
from pathlib import Path

from dotenv import load_dotenv
from langfuse import get_client


# ============================================================
# CONFIG
# ============================================================

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"
TIMEOUT = 300

PROJECT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_DIR / "config" / ".env"

load_dotenv(ENV_FILE)


# ============================================================
# LANGFUSE
# ============================================================

LANGFUSE_ENABLED = bool(
    os.getenv("LANGFUSE_PUBLIC_KEY")
    and os.getenv("LANGFUSE_SECRET_KEY")
)

langfuse = get_client() if LANGFUSE_ENABLED else None


# ============================================================
# RAGAS 0.3.9
# ============================================================

RAGAS_AVAILABLE = False
RAGAS_IMPORT_ERROR = None

try:
    from ragas.dataset_schema import SingleTurnSample
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import (
        Faithfulness as RagasFaithfulness,
        LLMContextPrecisionWithoutReference
    )
    from langchain_ollama import ChatOllama

    RAGAS_AVAILABLE = True

except Exception as error:
    RAGAS_IMPORT_ERROR = str(error)


# ============================================================
# EXTRACT JSON
# ============================================================

def extract_json(raw_response):
    """Lay JSON object tu response cua Ollama."""

    if not raw_response:
        return None

    raw_response = raw_response.strip()

    # Plain JSON
    try:
        result = json.loads(raw_response)

        if isinstance(result, dict):
            return result

    except json.JSONDecodeError:
        pass

    # ```json ... ```
    match = re.search(
        r"```json\s*(.*?)\s*```",
        raw_response,
        re.DOTALL | re.IGNORECASE
    )

    if match:
        try:
            result = json.loads(match.group(1).strip())

            if isinstance(result, dict):
                return result

        except json.JSONDecodeError:
            pass

    # ``` ... ```
    match = re.search(
        r"```\s*(\{.*?\})\s*```",
        raw_response,
        re.DOTALL
    )

    if match:
        try:
            result = json.loads(match.group(1))

            if isinstance(result, dict):
                return result

        except json.JSONDecodeError:
            pass

    # Find first { and last }
    start = raw_response.find("{")
    end = raw_response.rfind("}")

    if start != -1 and end != -1:
        try:
            result = json.loads(
                raw_response[start:end + 1]
            )

            if isinstance(result, dict):
                return result

        except json.JSONDecodeError:
            pass

    return None


# ============================================================
# SAFE SCORE
# ============================================================

def safe_score(value):
    """Gioi han score trong khoang 0-10."""

    try:
        value = float(value)

    except (TypeError, ValueError):
        return 0.0

    return max(
        0.0,
        min(10.0, value)
    )


# ============================================================
# BUILD EVALUATION PROMPT
# ============================================================

def build_evaluation_prompt(
    query,
    context,
    answer
):
    """Tao prompt danh gia RAG bang LLM Judge."""

    return f"""
Bạn là một chuyên gia đánh giá hệ thống RAG.

Chỉ đánh giá câu trả lời dựa trên CONTEXT được cung cấp.
Không sử dụng kiến thức bên ngoài CONTEXT.

QUERY:
{query}

CONTEXT:
{context}

ANSWER:
{answer}

Hãy chấm 4 tiêu chí từ 0 đến 10:

1. Faithfulness
Câu trả lời có trung thành với CONTEXT không?

2. Groundedness
Các thông tin trong câu trả lời có được CONTEXT hỗ trợ không?

3. Answer Relevance
Câu trả lời có trực tiếp trả lời QUERY không?

4. Correctness
Câu trả lời có chính xác dựa trên CONTEXT không?

0 = hoàn toàn sai
10 = hoàn toàn tốt

Chỉ trả về JSON.
Không giải thích bên ngoài JSON.
Không markdown.

FORMAT:
{{
    "faithfulness": 0,
    "groundedness": 0,
    "answer_relevance": 0,
    "correctness": 0,
    "reason": ""
}}
"""


# ============================================================
# CALL OLLAMA LLM JUDGE
# ============================================================

def call_evaluation_llm(prompt):
    """Gui evaluation prompt cho Ollama."""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0
                }
            },
            timeout=TIMEOUT
        )

        response.raise_for_status()

    except requests.exceptions.RequestException as error:
        return {
            "faithfulness": 0,
            "groundedness": 0,
            "answer_relevance": 0,
            "correctness": 0,
            "overall": 0.0,
            "reason": f"Loi ket noi Evaluation LLM: {error}"
        }

    try:
        data = response.json()

    except ValueError:
        return {
            "faithfulness": 0,
            "groundedness": 0,
            "answer_relevance": 0,
            "correctness": 0,
            "overall": 0.0,
            "reason": "Ollama khong tra ve JSON HTTP hop le."
        }

    raw_response = data.get(
        "response",
        ""
    )

    result = extract_json(
        raw_response
    )

    if result is None:
        return {
            "faithfulness": 0,
            "groundedness": 0,
            "answer_relevance": 0,
            "correctness": 0,
            "overall": 0.0,
            "reason": "Evaluation LLM khong tra ve JSON hop le."
        }

    faithfulness = safe_score(
        result.get(
            "faithfulness",
            0
        )
    )

    groundedness = safe_score(
        result.get(
            "groundedness",
            0
        )
    )

    answer_relevance = safe_score(
        result.get(
            "answer_relevance",
            0
        )
    )

    correctness = safe_score(
        result.get(
            "correctness",
            0
        )
    )

    overall = (
        faithfulness
        + groundedness
        + answer_relevance
        + correctness
    ) / 4

    return {
        "faithfulness": faithfulness,
        "groundedness": groundedness,
        "answer_relevance": answer_relevance,
        "correctness": correctness,
        "overall": round(
            overall,
            2
        ),
        "reason": str(
            result.get(
                "reason",
                ""
            )
        )
    }


# ============================================================
# NORMALIZE RETRIEVED CONTEXT
# ============================================================

def normalize_context(context):
    """
    Chuyen context cua RAG thanh list[str] cho Ragas.

    Ragas 0.3.9 expects:

        retrieved_contexts=[
            "context 1",
            "context 2",
            ...
        ]

    Project hien tai build_context() thanh mot string
    gom nhieu CHUNK, nen ham nay tach lai tung CHUNK.
    """

    if context is None:
        return []

    # --------------------------------------------------------
    # Already list
    # --------------------------------------------------------

    if isinstance(context, list):

        normalized = []

        for item in context:

            if isinstance(item, str):
                text = item.strip()

            elif isinstance(item, dict):
                text = (
                    item.get("page_content")
                    or item.get("content")
                    or item.get("text")
                    or item.get("document")
                    or ""
                )

                text = str(
                    text
                ).strip()

            else:
                text = str(
                    item
                ).strip()

            if text:
                normalized.append(
                    text
                )

        return normalized

    # --------------------------------------------------------
    # String context
    # --------------------------------------------------------

    context = str(
        context
    ).strip()

    if not context:
        return []

    # --------------------------------------------------------
    # Project format:
    #
    # CHUNK 1
    # SOURCE: ...
    # CONTENT:
    # ...
    #
    # CHUNK 2
    # SOURCE: ...
    # CONTENT:
    # ...
    # --------------------------------------------------------

    chunks = re.split(
        r"(?=CHUNK\s+\d+\s*)",
        context,
        flags=re.IGNORECASE
    )

    chunks = [
        chunk.strip()
        for chunk in chunks
        if chunk.strip()
    ]

    if chunks:
        return chunks

    return [context]


# ============================================================
# CREATE RAGAS LLM
# ============================================================

def create_ragas_llm():
    """
    Tao Ragas evaluator bang cung Ollama model.

    Ragas 0.3.x su dung LangchainLLMWrapper de bridge
    LangChain LLM -> Ragas.
    """

    if not RAGAS_AVAILABLE:
        return None

    ollama_llm = ChatOllama(
        model=OLLAMA_MODEL,
        temperature=0
    )

    return LangchainLLMWrapper(
        ollama_llm
    )


# ============================================================
# RUN RAGAS
# ============================================================

async def _run_ragas_async(
    query,
    retrieved_contexts,
    answer
):
    """Chay Ragas metrics tren mot sample."""

    evaluator_llm = create_ragas_llm()

    sample = SingleTurnSample(
        user_input=query,
        response=answer,
        retrieved_contexts=retrieved_contexts
    )

    # --------------------------------------------------------
    # Ragas Faithfulness
    # --------------------------------------------------------

    faithfulness_metric = RagasFaithfulness(
        llm=evaluator_llm
    )

    ragas_faithfulness = await (
        faithfulness_metric.single_turn_ascore(
            sample
        )
    )

    # --------------------------------------------------------
    # Ragas Context Precision Without Reference
    # --------------------------------------------------------
    #
    # Khong co ground-truth/reference answer trong project,
    # nen dung metric khong can reference.
    # --------------------------------------------------------

    context_precision_metric = (
        LLMContextPrecisionWithoutReference(
            llm=evaluator_llm
        )
    )

    ragas_context_precision = await (
        context_precision_metric.single_turn_ascore(
            sample
        )
    )

    return {
        "faithfulness": (
            float(ragas_faithfulness)
            if ragas_faithfulness is not None
            else None
        ),
        "context_precision": (
            float(ragas_context_precision)
            if ragas_context_precision is not None
            else None
        )
    }


def run_ragas_evaluation(
    query,
    context,
    answer
):
    """
    Chay Ragas 0.3.9.

    Ragas scores:
        0.0 -> 1.0
    """

    if not RAGAS_AVAILABLE:

        return {
            "available": False,
            "faithfulness": None,
            "context_precision": None,
            "reason": (
                "Ragas import failed: "
                f"{RAGAS_IMPORT_ERROR}"
            )
        }

    retrieved_contexts = normalize_context(
        context
    )

    if not query:
        return {
            "available": True,
            "faithfulness": None,
            "context_precision": None,
            "reason": "Missing query."
        }

    if not answer:
        return {
            "available": True,
            "faithfulness": None,
            "context_precision": None,
            "reason": "Missing answer."
        }

    if not retrieved_contexts:
        return {
            "available": True,
            "faithfulness": None,
            "context_precision": None,
            "reason": "No retrieved contexts."
        }

    try:

        result = asyncio.run(
            _run_ragas_async(
                query,
                retrieved_contexts,
                answer
            )
        )

        result["available"] = True
        result["context_count"] = len(
            retrieved_contexts
        )
        result["reason"] = (
            "Ragas 0.3.9 evaluation completed."
        )

        return result

    except Exception as error:

        return {
            "available": True,
            "faithfulness": None,
            "context_precision": None,
            "context_count": len(
                retrieved_contexts
            ),
            "reason": (
                "Ragas evaluation failed: "
                f"{error}"
            )
        }


# ============================================================
# SEND SCORES TO LANGFUSE
# ============================================================

def send_scores_to_langfuse(
    query,
    context,
    answer,
    evaluation_result,
    ragas_result,
    trace_id=None
):
    """
    Gui ca LLM Judge scores va Ragas scores len Langfuse.

    LLM Judge:
        0-10 -> normalize -> 0-1

    Ragas:
        already 0-1
    """

    if not LANGFUSE_ENABLED or langfuse is None:
        return

    try:

        with langfuse.start_as_current_observation(
            as_type="evaluator",
            name="evaluation",
            input={
                "query": query,
                "context": context,
                "answer": answer
            },
            output={
                "llm_judge": evaluation_result,
                "ragas": ragas_result
            },
            metadata={
                "llm_judge_model": OLLAMA_MODEL,
                "ragas_model": OLLAMA_MODEL,
                "ragas_version": "0.3.9",
                "llm_judge_score_scale": "0-10",
                "ragas_score_scale": "0-1"
            }
        ):

            target_trace_id = (
                trace_id
                or langfuse.get_current_trace_id()
            )

            if not target_trace_id:

                print(
                    "Langfuse: no active trace; "
                    "scores were not attached."
                )

                return

            # =================================================
            # LLM JUDGE SCORES
            # =================================================

            for metric in (
                "faithfulness",
                "groundedness",
                "answer_relevance",
                "correctness",
                "overall"
            ):

                value = evaluation_result.get(
                    metric
                )

                if value is None:
                    continue

                langfuse.create_score(
                    trace_id=target_trace_id,
                    name=metric,
                    value=float(value) / 10.0,
                    data_type="NUMERIC",
                    comment=(
                        "LLM-as-a-Judge "
                        f"({OLLAMA_MODEL}), "
                        f"original score: {value}/10"
                    )
                )

            # =================================================
            # RAGAS SCORES
            # =================================================

            if (
                ragas_result
                and ragas_result.get("available")
            ):

                ragas_faithfulness = (
                    ragas_result.get(
                        "faithfulness"
                    )
                )

                ragas_context_precision = (
                    ragas_result.get(
                        "context_precision"
                    )
                )

                if ragas_faithfulness is not None:

                    langfuse.create_score(
                        trace_id=target_trace_id,
                        name="ragas_faithfulness",
                        value=float(
                            ragas_faithfulness
                        ),
                        data_type="NUMERIC",
                        comment=(
                            "Ragas 0.3.9 "
                            "Faithfulness using "
                            f"Ollama {OLLAMA_MODEL}"
                        )
                    )

                if ragas_context_precision is not None:

                    langfuse.create_score(
                        trace_id=target_trace_id,
                        name=(
                            "ragas_context_precision"
                        ),
                        value=float(
                            ragas_context_precision
                        ),
                        data_type="NUMERIC",
                        comment=(
                            "Ragas 0.3.9 "
                            "LLM Context Precision "
                            "Without Reference using "
                            f"Ollama {OLLAMA_MODEL}"
                        )
                    )

        langfuse.flush()

    except Exception as error:

        # Langfuse must never break RAG.
        print(
            "Langfuse evaluation logging failed:",
            error
        )


# ============================================================
# MAIN EVALUATION FUNCTION
# ============================================================

def evaluate_rag(
    query,
    context,
    answer,
    trace_id=None
):
    """
    Evaluate RAG with two independent evaluation layers:

    1. Ollama LLM Judge
       - Faithfulness
       - Groundedness
       - Answer Relevance
       - Correctness
       - Overall

    2. Ragas 0.3.9
       - Faithfulness
       - Context Precision Without Reference

    Return format remains FLAT for compatibility with rag.py.
    """

    # ========================================================
    # EMPTY INPUT
    # ========================================================

    if not query or not answer:

        return {
            "faithfulness": 0,
            "groundedness": 0,
            "answer_relevance": 0,
            "correctness": 0,
            "overall": 0.0,

            "ragas_faithfulness": None,
            "ragas_context_precision": None,

            "ragas_available": RAGAS_AVAILABLE,

            "reason": (
                "Missing query or answer."
            )
        }

    # ========================================================
    # 1. LLM JUDGE
    # ========================================================

    prompt = build_evaluation_prompt(
        query,
        context,
        answer
    )

    evaluation_result = call_evaluation_llm(
        prompt
    )

    # ========================================================
    # 2. RAGAS
    # ========================================================

    print()

    print(
        "  Ragas:"
    )

    print(
        "    Running Ragas 0.3.9 evaluation..."
    )

    ragas_result = run_ragas_evaluation(
        query,
        context,
        answer
    )

    ragas_faithfulness = (
        ragas_result.get(
            "faithfulness"
        )
    )

    ragas_context_precision = (
        ragas_result.get(
            "context_precision"
        )
    )

    if ragas_faithfulness is not None:

        print(
            "    - Faithfulness:",
            f"{ragas_faithfulness:.4f}"
        )

    else:

        print(
            "    - Faithfulness: unavailable"
        )

    if ragas_context_precision is not None:

        print(
            "    - Context Precision:",
            f"{ragas_context_precision:.4f}"
        )

    else:

        print(
            "    - Context Precision: unavailable"
        )

    print(
        "    - Contexts:",
        ragas_result.get(
            "context_count",
            0
        )
    )

    print(
        "    - Status:",
        ragas_result.get(
            "reason",
            ""
        )
    )

    # ========================================================
    # 3. MERGE RESULTS
    # ========================================================
    #
    # IMPORTANT:
    # rag.py currently expects:
    #
    # result["faithfulness"]
    # result["groundedness"]
    # result["answer_relevance"]
    # result["correctness"]
    # result["overall"]
    #
    # Therefore we DO NOT nest the LLM result inside
    # {"llm_judge": ...}.
    # ========================================================

    final_result = {
        "faithfulness": evaluation_result.get(
            "faithfulness",
            0
        ),

        "groundedness": evaluation_result.get(
            "groundedness",
            0
        ),

        "answer_relevance": evaluation_result.get(
            "answer_relevance",
            0
        ),

        "correctness": evaluation_result.get(
            "correctness",
            0
        ),

        "overall": evaluation_result.get(
            "overall",
            0.0
        ),

        "reason": evaluation_result.get(
            "reason",
            ""
        ),

        "ragas_faithfulness": (
            ragas_faithfulness
        ),

        "ragas_context_precision": (
            ragas_context_precision
        ),

        "ragas_available": (
            ragas_result.get(
                "available",
                False
            )
        ),

        "ragas_reason": ragas_result.get(
            "reason",
            ""
        )
    }

    # ========================================================
    # 4. LANGFUSE
    # ========================================================

    send_scores_to_langfuse(
        query=query,
        context=context,
        answer=answer,
        evaluation_result=evaluation_result,
        ragas_result=ragas_result,
        trace_id=trace_id
    )

    return final_result


# ============================================================
# MODULE STATUS
# ============================================================

if __name__ == "__main__":

    print(
        "Evaluation module"
    )

    print(
        "Ollama:",
        OLLAMA_MODEL
    )

    print(
        "Langfuse:",
        "Enabled"
        if LANGFUSE_ENABLED
        else "Disabled"
    )

    print(
        "Ragas:",
        "Available"
        if RAGAS_AVAILABLE
        else "Unavailable"
    )

    if RAGAS_IMPORT_ERROR:

        print(
            "Ragas import error:",
            RAGAS_IMPORT_ERROR
        )
