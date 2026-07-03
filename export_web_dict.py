"""
Export a lightweight version of mainDataset_merged.json to rungus-analyzer-web/dictionary.json
by stripping out the heavy examples field.
"""

import json
from pathlib import Path

BASE = Path(__file__).parent
INPUT_PATH = BASE / "mainDataset_merged.json"
OUTPUT_PATH = BASE / "rungus-analyzer-web" / "dictionary.json"

def export_lightweight():
    if not INPUT_PATH.exists():
        print(f"Error: {INPUT_PATH} does not exist. Run merge_datasets.py first.")
        return

    print(f"[*] Loading full dataset: {INPUT_PATH}")
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"[*] Compiling lightweight dictionary ({len(data)} entries)...")
    lightweight = []
    for entry in data:
        # Clone entry without examples
        cleaned_entry = {
            "guid": entry.get("guid", ""),
            "url": entry.get("url", ""),
            "headword": entry.get("headword", ""),
            "senses": [],
            "subentries": entry.get("subentries", [])
        }
        
        # Keep is_subentry and parent if present
        if "is_subentry" in entry:
            cleaned_entry["is_subentry"] = entry["is_subentry"]
        if "parent" in entry:
            cleaned_entry["parent"] = entry["parent"]

        for sense in entry.get("senses", []):
            cleaned_sense = {
                "english": sense.get("english"),
                "malay": sense.get("malay")
            }
            cleaned_entry["senses"].append(cleaned_sense)

        lightweight.append(cleaned_entry)

    print(f"[*] Writing to: {OUTPUT_PATH}")
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(lightweight, f, ensure_ascii=False, indent=2)

    original_size = INPUT_PATH.stat().st_size / 1024
    new_size = OUTPUT_PATH.stat().st_size / 1024
    print(f"[+] Done! Size reduced from {original_size:.1f} KB to {new_size:.1f} KB")

if __name__ == "__main__":
    export_lightweight()
