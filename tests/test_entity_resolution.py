from pathlib import Path
import sys


# ============================================================
# CONFIG
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
ENGINE_DIR = PROJECT_DIR / "engine"

sys.path.insert(0, str(ENGINE_DIR))

from entity_resolution import resolve_entities


# ============================================================
# NER OUTPUT - TEST DATA
# ============================================================

TEST_ENTITIES = [
    {
        "text": "Claude Code",
        "type": "TOOL"
    },
    {
        "text": "C#",
        "type": "PROGRAMMING_LANGUAGE"
    },
    {
        "text": "Java",
        "type": "PROGRAMMING_LANGUAGE"
    },
    {
        "text": "RAG",
        "type": "CONCEPT"
    }
]


# ============================================================
# RUN TEST
# ============================================================

def run_tests():

    print("Entity Resolution Test:")

    for entity in TEST_ENTITIES:

        result = resolve_entities([entity])

        print()
        print("Entity:", entity["text"])

        if result["resolved"]:

            resolved = result["resolved"][0]

            print("  Status:", "Resolved")
            print("  Entity ID:", resolved["entity_id"])
            print("  Canonical:", resolved["canonical_name"])
            print("  Matched alias:", resolved["matched_alias"])
            print("  Domain:", ", ".join(resolved["domains"]))

        elif result["ambiguous"]:

            print("  Status:", "Ambiguous")

            candidates = result["ambiguous"][0]["candidates"]

            print(
                "  Candidates:",
                ", ".join(
                    candidate["canonical_name"]
                    for candidate in candidates
                )
            )

        elif result["not_found"]:

            print("  Status:", "Not found")


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    run_tests()