"""
Convert allEntries.json (new scraper format) to mainDataset.json format
expected by rungus_analyzer_lib.py.

New format fields: guid, url, entry_type, parent_guid, headword, senses
Old format fields: guid, url, headword, senses, subentries, [is_subentry, parent]

Conversion rules:
- entry_type='main'     -> top-level entry, subentries=[] initially
- entry_type='subentry' -> top-level entry with is_subentry=True, parent resolved via parent_guid
- Rebuild subentries[] list on each main entry from the subentry entries
- 601 entries with empty senses are kept (real Webonary stubs, not our error)
- Strips headwords with obvious placeholder text like '(??)'
"""

import json
import re
from pathlib import Path

INPUT_FILE  = Path(__file__).parent / "allEntries.json"
OUTPUT_FILE = Path(__file__).parent / "mainDataset.json"


def is_placeholder_headword(hw):
    """Filter out obvious database placeholders."""
    if not hw:
        return True
    # Contains question marks, parens with ??, is just punctuation
    if re.search(r'\(\?\?\)', hw):
        return True
    # Extremely long 'headwords' that are actually full phrases (not words)
    # e.g. "a-gima avi om tumandan do sungkod dot avan"
    # Keep them - they are valid idiom entries in the dictionary
    return False


def normalize_headword(hw):
    """Strip trailing homonym digits for the lookup key (kosunduvo1 -> kosunduvo)."""
    if not hw:
        return hw
    return hw.rstrip("0123456789")


def convert():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"[*] Loaded {len(data)} entries from {INPUT_FILE.name}")

    # Build GUID -> entry index map for resolving parent_guid
    guid_to_entry = {}
    for entry in data:
        g = entry.get("guid")
        if g:
            guid_to_entry[g] = entry

    # --- Pass 1: Build converted entries ---
    converted = []
    guid_to_converted_idx = {}   # guid -> index in converted list

    for entry in data:
        hw = entry.get("headword", "") or ""

        if is_placeholder_headword(hw):
            continue

        c = {
            "guid":       entry.get("guid", ""),
            "url":        entry.get("url", ""),
            "headword":   hw,
            "senses":     entry.get("senses", []),
            "subentries": [],
        }

        # Mark subentries so the analyzer can trace parent
        if entry.get("entry_type") == "subentry":
            c["is_subentry"] = True
            # Resolve parent headword from parent_guid
            pguid = entry.get("parent_guid")
            if pguid and pguid in guid_to_entry:
                c["parent"] = guid_to_entry[pguid].get("headword", "")
            else:
                c["parent"] = None

        idx = len(converted)
        converted.append(c)
        if c["guid"]:
            guid_to_converted_idx[c["guid"]] = idx

    print(f"[*] Converted: {len(converted)} entries (excluded placeholders)")

    # --- Pass 2: Rebuild subentries[] list on main entries ---
    # For each subentry, find its parent in converted and add to subentries[]
    main_idx_by_guid = {
        e["guid"]: i
        for i, e in enumerate(converted)
        if e["guid"] and not e.get("is_subentry")
    }

    added_to_subentries = 0
    for entry in data:
        if entry.get("entry_type") != "subentry":
            continue
        hw = entry.get("headword", "") or ""
        if is_placeholder_headword(hw):
            continue
        pguid = entry.get("parent_guid")
        if pguid and pguid in main_idx_by_guid:
            parent_entry = converted[main_idx_by_guid[pguid]]
            parent_entry["subentries"].append({"headword": hw})
            added_to_subentries += 1

    print(f"[*] Rebuilt {added_to_subentries} subentry references on parent entries")

    # --- Stats ---
    main_count  = sum(1 for e in converted if not e.get("is_subentry"))
    sub_count   = sum(1 for e in converted if e.get("is_subentry"))
    with_senses = sum(1 for e in converted if any(s.get("english") or s.get("malay") for s in e.get("senses", [])))
    ng_count    = sum(1 for e in converted if (e.get("headword") or "").startswith("ng"))
    with_examples = sum(1 for e in converted for s in e.get("senses", []) if s.get("examples"))

    print(f"\n    Main entries:         {main_count}")
    print(f"    Subentries:           {sub_count}")
    print(f"    With real senses:     {with_senses}")
    print(f"    With examples:        {with_examples}")
    print(f"    ng- words:            {ng_count}")
    print(f"    Total:                {len(converted)}")

    # --- Write ---
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(converted, f, ensure_ascii=False, indent=2)

    print(f"\n[+] Saved to {OUTPUT_FILE}")
    print(f"[!!!] mainDataset.json has been updated. Commit and push to deploy.")


if __name__ == "__main__":
    convert()
