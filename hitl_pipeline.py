"""
hitl_pipeline.py — Human-in-the-Loop Pipeline for Rungus Translator
=====================================================================
Enables language experts (like Christine) to review unanalyzed words,
propose roots, and import them back into the lexicon database.

Commands:
  python hitl_pipeline.py run          # scan corpus, export review_queue.csv
  python hitl_pipeline.py import FILE  # import reviewed CSV to custom_vocab.json
  python hitl_pipeline.py coverage     # measure token coverage metrics

Author: Aifven Nelson
"""

import csv
import json
import os
import sys
from pathlib import Path

# Project root path
ROOT_DIR = Path(__file__).parent.resolve()
CUSTOM_VOCAB_PATH = ROOT_DIR / "custom_vocab.json"
REVIEW_CSV_PATH = ROOT_DIR / "review_queue.csv"

def show_help():
    print("""Rungus HITL (Human-in-the-Loop) Pipeline v1.0
============================================
Usage:
  python hitl_pipeline.py run          - Scan corpus and generate review_queue.csv
  python hitl_pipeline.py import FILE  - Import reviewed CSV file into custom_vocab.json
  python hitl_pipeline.py coverage     - Show quick token coverage and top unanalyzed words
""")

def run_pipeline():
    print("[*] Running corpus analysis and exporting review queue...")
    # Import and run the main method from analyze_books.py programmatically
    sys.path.insert(0, str(ROOT_DIR))
    import analyze_books
    
    # Override sys.argv to emulate --export-review and --quick
    sys.argv = [sys.argv[0], "--export-review", "--quick"]
    analyze_books.main()
    print(f"\n[✓] Review queue successfully exported to: {REVIEW_CSV_PATH}")
    print("    Open this file in Excel/Google Sheets, fill in 'your_proposed_root' and 'english_gloss', then import it.")

def import_reviewed_csv(csv_path):
    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"[❌] Error: Reviewed CSV file not found at '{csv_path}'")
        return

    print(f"[*] Reading reviewed entries from: {csv_file}")
    
    # Load existing custom vocabulary
    custom_vocab = {}
    if CUSTOM_VOCAB_PATH.exists():
        try:
            with open(CUSTOM_VOCAB_PATH, "r", encoding="utf-8") as f:
                custom_vocab = json.load(f)
            print(f"    Loaded {len(custom_vocab)} existing custom entries.")
        except Exception as e:
            print(f"    Warning: Failed to load existing custom_vocab.json ({e}). Creating new.")

    imported_count = 0
    skipped_count = 0

    with open(csv_file, "r", encoding="utf-8") as f:
        # Detect delimiter / dialect
        try:
            sample = f.read(2048)
            f.seek(0)
            dialect = csv.Sniffer().sniff(sample)
            reader = csv.DictReader(f, dialect=dialect)
        except Exception:
            f.seek(0)
            reader = csv.DictReader(f)

        for row_idx, row in enumerate(reader, start=1):
            word = row.get("word", "").strip().lower()
            proposed_root = row.get("your_proposed_root", "").strip().lower()
            gloss = row.get("english_gloss", "").strip()
            
            if not word:
                continue
            
            if proposed_root:
                # Add to custom vocabulary
                custom_vocab[word] = {
                    "headword": proposed_root,
                    "gloss": gloss,
                    "pos": "verb" if word.startswith(('m', 'p', 'n', 'k')) else "noun",
                }
                imported_count += 1
            else:
                skipped_count += 1

    if imported_count == 0:
        print("[⚠️] No reviewed entries (with non-empty 'your_proposed_root') were found in the CSV.")
        return

    # Write custom vocabulary back
    try:
        with open(CUSTOM_VOCAB_PATH, "w", encoding="utf-8") as f:
            json.dump(custom_vocab, f, indent=2, ensure_ascii=False)
        print(f"\n[✓] Successfully imported {imported_count} new entries into {CUSTOM_VOCAB_PATH}!")
        print(f"    (Total custom entries in database: {len(custom_vocab)})")
    except Exception as e:
        print(f"[❌] Error writing to custom_vocab.json: {e}")

def show_coverage():
    print("[*] Computing current corpus token coverage...")
    sys.path.insert(0, str(ROOT_DIR))
    import analyze_books
    sys.argv = [sys.argv[0], "--quick"]
    analyze_books.main()

def main():
    if len(sys.argv) < 2:
        show_help()
        return

    cmd = sys.argv[1].lower()
    
    if cmd == "run":
        run_pipeline()
    elif cmd == "import":
        if len(sys.argv) < 3:
            print("[❌] Error: Please specify the reviewed CSV file to import.")
            print("Usage: python hitl_pipeline.py import [FILE_PATH]")
            return
        import_reviewed_csv(sys.argv[2])
    elif cmd == "coverage":
        show_coverage()
    else:
        print(f"[❌] Unknown command: {cmd}")
        show_help()

if __name__ == "__main__":
    main()
