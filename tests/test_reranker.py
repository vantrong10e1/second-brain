from pathlib import Path
import sys


# ============================================================
# CONFIG
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
ENGINE_DIR = PROJECT_DIR / "engine"

sys.path.insert(0, str(ENGINE_DIR))

from hybrid_search import hybrid_search
from reranker import rerank


# ============================================================
# TEST QUERIES
# ============================================================

TEST_QUERIES = [
    "Claude Code là gì?",
    "C# có hỗ trợ kế thừa không?",
    "Java là gì?",
    "RAG là gì?"
]


# ============================================================
# RUN TEST
# ============================================================

def run_tests():

    print("Reranker Test:")

    for query in TEST_QUERIES:

        # Lấy candidates từ Hybrid Search
        hybrid_results = hybrid_search(
            query,
            top_k=5
        )

        # Rerank
        results = rerank(
            query,
            hybrid_results,
            top_k=2,
            show_progress=False
        )

        print()
        print("Query:", query)
        print("Candidates:", len(hybrid_results))
        print("Final results:", len(results))

        for index, result in enumerate(
            results,
            start=1
        ):

            document = result.get(
                "document",
                {}
            )

            print(
                f"  {index}.",
                "Rerank:",
                round(
                    result.get(
                        "rerank_score",
                        0
                    ),
                    2
                )
            )

            print(
                "     Fusion:",
                round(
                    result.get(
                        "fusion_score",
                        0
                    ),
                    4
                )
            )

            print(
                "     Source:",
                document.get(
                    "source",
                    "unknown"
                )
            )

            print(
                "     Content:",
                document.get(
                    "content",
                    ""
                )[:150]
            )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    run_tests()