from pathlib import Path
import sys


# ============================================================
# CONFIG
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
ENGINE_DIR = PROJECT_DIR / "engine"

sys.path.insert(0, str(ENGINE_DIR))

from hybrid_search import hybrid_search


# ============================================================
# TEST CASES
# ============================================================

TEST_QUERIES = [
    "Claude Code là gì?",
    "C# có hỗ trợ inheritance không?",
    "Java là gì?",
    "RAG là gì?"
]


# ============================================================
# RUN TEST
# ============================================================

def run_tests():

    print("Hybrid Search Test:")

    for query in TEST_QUERIES:

        results = hybrid_search(
            query,
            top_k=5
        )

        print()
        print("Query:", query)
        print("Results:", len(results))

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
                "Fusion:",
                round(
                    result.get(
                        "fusion_score",
                        0
                    ),
                    4
                )
            )

            print(
                "     Vector:",
                round(
                    result.get(
                        "vector_score",
                        0
                    ),
                    4
                )
            )

            print(
                "     Keyword:",
                round(
                    result.get(
                        "keyword_score",
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


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    run_tests()