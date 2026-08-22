from pathlib import Path
import subprocess
import sys


# ============================================================
# CONFIG
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
ENGINE_DIR = PROJECT_DIR / "engine"


BUILD_STEPS = [
    ("Documents", "build_documents.py"),
    ("Embeddings", "build_embeddings.py"),
    ("Entities", "build_entities.py"),
    ("Catalog", "build_catalog.py"),
    ("Fack", "build_fack.py"),
]


# ============================================================
# RUN BUILD
# ============================================================

def run_build(
    name,
    filename
):
    print()
    print(
        f"Build {name} starting..."
    )

    build_file = ENGINE_DIR / filename

    if not build_file.exists():

        print(
            f"Build {name} failed!"
        )

        print(
            f"File not found: {build_file}"
        )

        return False

    result = subprocess.run(
        [
            sys.executable,
            str(build_file)
        ],
        cwd=ENGINE_DIR
    )

    if result.returncode != 0:

        print(
            f"Build {name} failed!"
        )

        return False

    print(
        f"Build {name} finished!"
    )

    return True


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "Build Pipeline:"
    )

    for name, filename in BUILD_STEPS:

        success = run_build(
            name,
            filename
        )

        if not success:

            print()
            print(
                "Build pipeline stopped."
            )

            return 1

    print()
    print(
        "========================================"
    )

    print(
        "All builds finished!"
    )

    print(
        "========================================"
    )

    return 0


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    sys.exit(
        main()
    )