from pathlib import Path
import json
from collections import defaultdict
from datetime import datetime


# ============================================================
# CONFIG
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_DIR / "data"

DOCUMENTS_FILE = DATA_DIR / "documents.json"
OUTPUT_FILE = DATA_DIR / "data_catalog.json"


# ============================================================
# LOAD DOCUMENTS
# ============================================================

def load_documents():
    """Load documents da duoc build."""

    with open(
        DOCUMENTS_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


# ============================================================
# GROUP DOCUMENTS BY SOURCE
# ============================================================

def group_by_source(documents):
    """Nhom cac chunk theo source."""

    sources = defaultdict(list)

    for document in documents:

        source = document.get(
            "source",
            "unknown"
        )

        sources[source].append(
            document
        )

    return sources


# ============================================================
# BUILD SOURCE METADATA
# ============================================================

def build_source_metadata(
    source,
    chunks
):
    """Tao metadata cho mot source."""

    domains = set()

    for chunk in chunks:

        domain = chunk.get(
            "domain"
        )

        if domain:
            domains.add(domain)

    path = Path(source)

    return {
        "source": source,
        "name": path.name,
        "file_type": path.suffix.lower().replace(
            ".",
            ""
        ),
        "domain": sorted(domains),
        "chunk_count": len(chunks),
        "status": "active",
        "last_updated": datetime.now().isoformat(
            timespec="seconds"
        )
    }


# ============================================================
# BUILD CATALOG
# ============================================================

def build_catalog():
    """Tu dong build Central Data Catalog."""

    print("Building Data Catalog...")

    documents = load_documents()

    print(
        "Documents:",
        len(documents)
    )

    documents_by_source = group_by_source(
        documents
    )

    print(
        "Sources:",
        len(documents_by_source)
    )

    catalog = []

    for source, chunks in documents_by_source.items():

        metadata = build_source_metadata(
            source,
            chunks
        )

        catalog.append(
            metadata
        )

    catalog.sort(
        key=lambda item: (
            item["domain"],
            item["name"]
        )
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            catalog,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        "Catalog created:",
        OUTPUT_FILE
    )

    return catalog


# ============================================================
# DISPLAY CATALOG
# ============================================================

def display_catalog(catalog):
    """Hien thi catalog de kiem tra."""

    print()
    print("Catalog:")

    for item in catalog:

        print(
            f"  - {item['name']}"
        )

        print(
            f"    domain: {', '.join(item['domain'])}"
        )

        print(
            f"    type: {item['file_type']}"
        )

        print(
            f"    chunks: {item['chunk_count']}"
        )

        print(
            f"    status: {item['status']}"
        )

        print()


# ============================================================
# MAIN
# ============================================================

def main():

    catalog = build_catalog()

    display_catalog(
        catalog
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()