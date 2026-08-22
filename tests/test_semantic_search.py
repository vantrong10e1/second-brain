from pathlib import Path
import sys


# ============================================================
# CONFIG
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
ENGINE_DIR = PROJECT_DIR / "engine"

sys.path.insert(0, str(ENGINE_DIR))

from search import search


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

    print("Search Test:")

    for query in TEST_QUERIES:

        results = search(
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
                "Similarity:",
                round(
                    result.get(
                        "similarity",
                        0
                    ),
                    4
                )
            )

            print(
                "     Domain:",
                document.get(
                    "domain",
                    "unknown"
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