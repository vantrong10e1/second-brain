from pathlib import Path
import sys


# ============================================================
# CONFIG
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
ENGINE_DIR = PROJECT_DIR / "engine"

sys.path.insert(0, str(ENGINE_DIR))


from query_understanding import understand_query
from domain_search import domain_search


# ============================================================
# TEST QUERIES
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

    print("Domain Search Test:")

    for query in TEST_QUERIES:

        query_info = understand_query(query)

        print()
        print("Query:", query)

        if not query_info:

            print("  Query Understanding: Failed")
            continue

        domain = query_info.get(
            "domain"
        )

        print(
            "  Domain:",
            domain
        )

        if not domain:

            print(
                "  Domain Search: No domain"
            )

            continue

        results = domain_search(
            query,
            domain,
            top_k=5
        )

        print(
            "  Results:",
            len(results)
        )

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