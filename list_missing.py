import json
from pathlib import Path

def list_missing_data():
    file_path = Path("mainDataset_clean.json")
    if not file_path.exists():
        print(f"Error: {file_path} not found.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    missing_english = []
    missing_malay = []
    missing_examples = []

    for entry in data:
        headword = entry.get("headword", "Unknown")
        url = entry.get("url", "")
        senses = entry.get("senses", [])

        # Check if any sense has English/Malay
        has_en = any(s.get("english") for s in senses)
        has_ms = any(s.get("malay") for s in senses)
        has_ex = any(s.get("examples") for s in senses)

        if not has_en:
            missing_english.append(f"{headword} ({url})")
        if not has_ms:
            missing_malay.append(f"{headword} ({url})")
        if not has_ex:
            missing_examples.append(f"{headword} ({url})")

    print("=== ENTRIES MISSING ENGLISH DEFINITIONS ===")
    if missing_english:
        for item in missing_english:
            print(f"- {item}")
    else:
        print("None")

    print("\n=== ENTRIES MISSING MALAY DEFINITIONS ===")
    if missing_malay:
        for item in missing_malay:
            print(f"- {item}")
    else:
        print("None")

    print("\n=== ENTRIES MISSING EXAMPLE SENTENCES ===")
    if missing_examples:
        for item in missing_examples:
            print(f"- {item}")
    else:
        print("None")

if __name__ == "__main__":
    list_missing_data()
