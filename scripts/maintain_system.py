import os
import shutil
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')
import datetime

# Workspace root (assume script resides in <workspace>/scripts)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
WIKI_ROOT = PROJECT_ROOT / "wiki"

def remove_empty_pages():
    for md_file in WIKI_ROOT.rglob("*.md"):
        if md_file.stat().st_size == 0:
            md_file.unlink()
            print(f"Removed empty page: {md_file}")

def remove_temp_files():
    for temp_file in WIKI_ROOT.rglob("~*"):
        temp_file.unlink()
        print(f"Removed temporary file: {temp_file}")
    for tmp_file in WIKI_ROOT.rglob("*.tmp"):
        tmp_file.unlink()
        print(f"Removed temporary file: {tmp_file}")

def rebuild_index():
    index_path = WIKI_ROOT / "index.md"
    with index_path.open("w", encoding="utf-8") as idx:
        idx.write("# Index\n\n")
        for md_file in sorted(WIKI_ROOT.rglob("*.md")):
            if md_file.name == "index.md":
                continue
            rel = md_file.relative_to(WIKI_ROOT)
            idx.write(f"- [{rel.stem}]({rel.as_posix()})\n")
    print(f"Rebuilt index at {index_path}")

def append_log():
    log_path = WIKI_ROOT / "log.md"
    timestamp = datetime.datetime.now().isoformat()
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"\n- Maintenance run at {timestamp}\n")
    print(f"Appended log entry to {log_path}")

def main():
    try:
        remove_empty_pages()
        remove_temp_files()
        rebuild_index()
        append_log()
        print("Bảo trì hệ thống hoàn tất!")
    except Exception as e:
        print(f"Error during maintenance: {e}")

if __name__ == "__main__":
    main()
