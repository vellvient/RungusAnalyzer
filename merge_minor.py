"""
Merge a scraped entries JSON file into mainDataset.json.

Usage:
    python merge_minor.py                    # merges minor_entries.json (default)
    python merge_minor.py ng_entries.json    # merges ng_entries.json
    python merge_minor.py some_other.json    # merges any compatible JSON

Rules:
- If a headword from the input file already exists in mainDataset as a proper
  entry WITH real senses, keep the existing one (skip duplicate).
- Otherwise, add the entry as a new top-level entry.

Run AFTER any scrape_*.py script completes.
"""

import json
import sys
from pathlib import Path

MAIN_FILE = Path(__file__).parent / "mainDataset.json"
OUT_FILE  = Path(__file__).parent / "mainDataset.json"   # overwrite in place

# Accept filename as CLI argument, default to minor_entries.json
_input_arg = sys.argv[1] if len(sys.argv) > 1 else "minor_entries.json"
MINOR_FILE = Path(__file__).parent / _input_arg


def has_real_senses(entry):
    """Return True if the entry has at least one sense with a real gloss."""
    for s in entry.get("senses", []):
        if s.get("english") or s.get("malay"):
            return True
    return False


def main():
    if not MINOR_FILE.exists():
        print(f"[!] {MINOR_FILE} not found. Run scrape_minor_entries.py first.")
        return

    with open(MAIN_FILE, "r", encoding="utf-8") as f:
        main_data = json.load(f)

    with open(MINOR_FILE, "r", encoding="utf-8") as f:
        minor_data = json.load(f)

    print(f"[*] Main dataset: {len(main_data)} entries")
    print(f"[*] Minor entries scraped: {len(minor_data)} entries")

    # Build a set of headwords already in mainDataset with real senses
    main_headwords_with_senses = {
        e["headword"].lower().strip()
        for e in main_data
        if e.get("headword") and has_real_senses(e)
    }

    # Also build set of ALL headwords in mainDataset (including stubs)
    main_headwords_all = {
        e["headword"].lower().strip()
        for e in main_data
        if e.get("headword")
    }

    added   = 0
    skipped = 0

    for minor in minor_data:
        hw = (minor.get("headword") or "").lower().strip()
        if not hw:
            continue

        # Strip trailing homonym digits for comparison (kosunduvo1 → kosunduvo)
        hw_clean = hw.rstrip("0123456789")

        if hw in main_headwords_with_senses or hw_clean in main_headwords_with_senses:
            skipped += 1
            continue

        # Add as a new top-level entry
        main_data.append(minor)
        main_headwords_with_senses.add(hw)
        added += 1

    print(f"[*] Added:   {added} new entries from minor_entries.json")
    print(f"[*] Skipped: {skipped} (already existed in mainDataset with senses)")
    print(f"[*] Total entries now: {len(main_data)}")

    # Save
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(main_data, f, ensure_ascii=False, indent=2)

    print(f"[+] Saved merged dataset to {OUT_FILE}")
    print(f"[!!!] Done. Run your analyzer to verify the improvement.")


if __name__ == "__main__":
    main()
