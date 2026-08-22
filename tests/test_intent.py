from pathlib import Path
import sys

# Cho phep import module tu folder engine
PROJECT_DIR = Path(__file__).resolve().parent.parent
ENGINE_DIR = PROJECT_DIR / "engine"

sys.path.insert(0, str(ENGINE_DIR))

from query_understanding import understand_query


# TEST CASES

TEST_QUERIES = [
    "Claude Code là gì?",
    "C# có hỗ trợ inheritance không?",
    "Python được sử dụng để làm gì?",
    "RAG hoạt động như thế nào?",
    "Embedding là gì?"
]


# RUN TESTS

def run_tests():
    print("Intent Test:")

    for query in TEST_QUERIES:

        result = understand_query(query)

        if result is None:
            print("  Query:", query)
            print("  Intent: failed")
            continue

        print(
            "  Query:",
            query,
            "| Intent:",
            result.get("intent")
        )


# START

if __name__ == "__main__":
    run_tests()