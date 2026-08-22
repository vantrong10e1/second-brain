from pathlib import Path
import sys


# ============================================================
# CONFIG
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
ENGINE_DIR = PROJECT_DIR / "engine"

sys.path.insert(0, str(ENGINE_DIR))

from rag_retrieval import retrieve


# ============================================================
# TEST CASES
# ============================================================

TEST_CASES = [
    {
        "query": "Claude Code là gì?",
        "domain": "ai"
    },
    {
        "query": "C# có hỗ trợ kế thừa không?",
        "domain": "programming-language"
    },
    {
        "query": "Java là gì?",
        "domain": "programming-language"
    },
    {
        "query": "RAG là gì?",
        "domain": "ai"
    }
]


# ============================================================
# RUN TEST
# ============================================================

def run_tests():

    print("RAG Retrieval Test:")

    for test in TEST_CASES:

        query = test["query"]
        domain = test["domain"]

        results = retrieve(
            query=query,
            domain=domain,
            top_k=5
        )

        print()
        print("Query:", query)
        print("Domain:", domain)
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