from pathlib import Path
import json


# ============================================================
# CONFIG
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"

CATALOG_FILE = DATA_DIR / "data_catalog.json"


# ============================================================
# LOAD CATALOG
# ============================================================

def load_catalog():

    with open(
        CATALOG_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# DISPLAY CATALOG
# ============================================================

def display_catalog(catalog):

    print("Central Data Catalog:")

    if not catalog:
        print("  Catalog: Empty")
        return

    print("  Total items:", len(catalog))

    for index, item in enumerate(catalog, start=1):

        print()
        print(f"  Item {index}:")
        print("  ", item)


# ============================================================
# TEST
# ============================================================

def run_test():

    catalog = load_catalog()

    display_catalog(catalog)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    run_test()