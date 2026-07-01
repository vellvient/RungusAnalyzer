"""
Merge old and new Webonary datasets.

Strategy:
- New dataset (mainDataset_clean.json) = fresh scrape with latest entries
- Old dataset (backup/mainDataset_v1_clean.json) = has example translations
- Match by: headword → sense index → Rungus example text
- Copy English/Malay translations from old to new where they match
- Also add entries from old that are missing in new
- Preserve any new entries that don't exist in old

Output: mainDataset_merged.json
"""

import json
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).parent
NEW_PATH = BASE / "mainDataset_clean.json"
OLD_PATH = BASE / "backup" / "mainDataset_v1_clean.json"
OUTPUT_PATH = BASE / "mainDataset_merged.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_translation_lookup(dataset):
    """Build lookup: (headword, sense_idx, example_rungus) -> (english, malay)"""
    lookup = {}
    for entry in dataset:
        hw = entry.get("headword", "")
        if not hw:
            continue
        for si, sense in enumerate(entry.get("senses", [])):
            for ex in sense.get("examples", []):
                rungus = ex.get("rungus", "")
                if rungus and (ex.get("english") or ex.get("malay")):
                    key = (hw, si, rungus.strip())
                    lookup[key] = {
                        "english": ex.get("english"),
                        "malay": ex.get("malay"),
                    }
    return lookup


def build_subentry_lookup(dataset):
    """Build lookup for sub-entries: (parent_hw, sub_hw) -> sub_entry_data"""
    lookup = {}
    for entry in dataset:
        parent_hw = entry.get("headword", "")
        for sub in entry.get("subentries", []):
            sub_hw = sub.get("headword", "")
            if sub_hw:
                key = (parent_hw, sub_hw)
                lookup[key] = sub
    return lookup


def merge():
    print("[*] Loading datasets...")
    new_data = load_json(NEW_PATH)
    old_data = load_json(OLD_PATH)

    print(f"    New: {len(new_data)} top-level entries")
    print(f"    Old: {len(old_data)} top-level entries")

    # ── Build lookup from old data ──
    print("[*] Building translation lookup from old dataset...")
    translation_lookup = build_translation_lookup(old_data)
    print(f"    Translations indexed: {len(translation_lookup)}")

    # Build sets of headwords for detecting missing/added entries
    new_hws = {e.get("headword", "") for e in new_data}
    old_index = {e.get("headword", ""): e for e in old_data}

    # ── Merge: enrich new entries with old translations ──
    enriched = 0
    total_examples = 0
    filled_examples = 0

    for entry in new_data:
        hw = entry.get("headword", "")
        for si, sense in enumerate(entry.get("senses", [])):
            for ex in sense.get("examples", []):
                total_examples += 1
                rungus = ex.get("rungus", "")
                if not rungus:
                    continue

                key = (hw, si, rungus.strip())
                if key in translation_lookup:
                    trans = translation_lookup[key]
                    if trans["english"] and not ex.get("english"):
                        ex["english"] = trans["english"]
                    if trans["malay"] and not ex.get("malay"):
                        ex["malay"] = trans["malay"]
                    filled_examples += 1
                    enriched += 1

    print(f"[*] Enriched examples: {filled_examples}/{total_examples}")

    # ── Add entries from old that are missing in new ──
    added_count = 0
    for hw, old_entry in old_index.items():
        if hw not in new_hws:
            new_data.append(old_entry)
            added_count += 1

    print(f"[*] Added {added_count} missing entries from old dataset")

    # ── Merge sub-entries where missing ──
    sub_filled = 0
    old_sub_lookup = build_subentry_lookup(old_data)

    for entry in new_data:
        parent_hw = entry.get("headword", "")
        existing_subs = {s.get("headword", "") for s in entry.get("subentries", [])}
        for (old_parent, sub_hw), sub_data in old_sub_lookup.items():
            if old_parent == parent_hw and sub_hw not in existing_subs:
                entry["subentries"].append(sub_data)
                sub_filled += 1

    print(f"[*] Added {sub_filled} missing sub-entries")

    # ── Final stats ──
    top_count = len(new_data)
    sub_count = sum(len(e.get("subentries", [])) for e in new_data)
    examples_count = sum(
        len(s.get("examples", [])) for e in new_data for s in e.get("senses", [])
    )
    filled_count = sum(
        1
        for e in new_data
        for s in e.get("senses", [])
        for ex in s.get("examples", [])
        if ex.get("english")
    )

    print(f"\n=== MERGED DATASET ===")
    print(f"Top-level entries: {top_count}")
    print(f"Sub-entries:       {sub_count}")
    print(f"Total items:       {top_count + sub_count}")
    print(f"Total examples:    {examples_count}")
    print(f"Filled examples:   {filled_count}")
    print(f"Missing examples:  {examples_count - filled_count}")

    # ── Save ──
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)

    # File size
    size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
    print(f"\n[*] Saved to: {OUTPUT_PATH}")
    print(f"[*] File size: {size_mb:.1f} MB")


if __name__ == "__main__":
    merge()
