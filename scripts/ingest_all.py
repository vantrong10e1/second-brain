import os
import shutil
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Folders
RAW_ROOT = PROJECT_ROOT / "raw"
WIKI_ROOT = PROJECT_ROOT / "wiki"


def copy_md_files():
    """Copy all Markdown files from raw/ to wiki/, preserving folder structure."""

    if not RAW_ROOT.exists():
        raise FileNotFoundError(f"Folder not found: {RAW_ROOT}")

    WIKI_ROOT.mkdir(parents=True, exist_ok=True)

    for root, _, files in os.walk(RAW_ROOT):
        rel_root = Path(root).relative_to(RAW_ROOT)
        target_dir = WIKI_ROOT / rel_root
        target_dir.mkdir(parents=True, exist_ok=True)

        for file in files:
            if file.lower().endswith(".md"):
                src = Path(root) / file
                dst = target_dir / file
                shutil.copy2(src, dst)


def main():
    try:
        copy_md_files()
        print("Ingest raw/ -> wiki/ successful!")
    except Exception as e:
        print(f"Ingest failed: {e}")


if __name__ == "__main__":
    main()