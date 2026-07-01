"""
Clean the scraped Webonary Rungus Dictionary dataset.
Resolves punctuation artifacts, merged translation spans, and formatting issues.
Outputs a production-ready mainDataset_clean.json.
"""

import json
import re
from pathlib import Path

# Paths
CWD = Path(__file__).parent
INPUT_FILE = CWD / "mainDataset.json"
OUTPUT_FILE = CWD / "mainDataset_clean.json"

def remove_duplicate_suffix(text):
    """
    Detects and removes duplicated suffixes caused by nested span extraction.
    E.g. 'loteng, para-paralotengpara-para' -> 'loteng, para-para'
    E.g. 'cergas, cerdas, aktifcergascerdasaktif' -> 'cergas, cerdas, aktif'
    """
    if not text:
        return text
    
    def normalize(t):
        return re.sub(r'[^a-zA-Z0-9]', '', t).lower()

    n = len(text)
    # Iterate forward to find the longest duplicate suffix (smallest prefix)
    for i in range(2, n - 1):
        prefix = text[:i].strip()
        suffix = text[i:].strip()
        
        if not prefix or not suffix:
            continue
            
        norm_prefix = normalize(prefix)
        norm_suffix = normalize(suffix)
        
        if norm_prefix and norm_suffix and norm_prefix.endswith(norm_suffix):
            if len(norm_suffix) >= 4:  # Avoid false positives on very short words
                return prefix
                
    return text

def clean_text(text):
    """
    Clean translation strings by:
    1. Normalizing consecutive whitespaces.
    2. Inserting spaces after commas/semicolons if missing.
    3. Stripping leading/trailing punctuation (commas, semicolons) and spaces.
    4. Removing duplicated suffix artifacts from nested span extraction.
    """
    if not text:
        return None
    
    # Normalize whitespaces
    text = re.sub(r'\s+', ' ', text)
    
    # Ensure space after commas and semicolons
    text = re.sub(r',([^\s])', r', \1', text)
    text = re.sub(r';([^\s])', r'; \1', text)
    
    # Strip leading/trailing spaces, commas, and semicolons
    text = re.sub(r'^[\s,;]+|[\s,;]+$', '', text)
    
    # Deduplicate nested span repetitions
    text = remove_duplicate_suffix(text)
    
    # Clean up double/triple spaces that might have been introduced
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text if text else None

def clean_dataset():
    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} not found!")
        return

    print(f"[*] Loading raw dataset: {INPUT_FILE}")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    stats = {
        "total_entries": len(data),
        "cleaned_english_defs": 0,
        "cleaned_malay_defs": 0,
        "cleaned_english_examples": 0,
        "cleaned_malay_examples": 0,
    }

    cleaned_data = []

    for entry in data:
        cleaned_entry = entry.copy()
        cleaned_entry["senses"] = []

        for sense in entry.get("senses", []):
            cleaned_sense = {}
            
            # Clean English definitions
            orig_en = sense.get("english")
            clean_en = clean_text(orig_en)
            cleaned_sense["english"] = clean_en
            if orig_en != clean_en:
                stats["cleaned_english_defs"] += 1
                
            # Clean Malay definitions
            orig_ms = sense.get("malay")
            clean_ms = clean_text(orig_ms)
            cleaned_sense["malay"] = clean_ms
            if orig_ms != clean_ms:
                stats["cleaned_malay_defs"] += 1

            # Clean examples
            cleaned_sense["examples"] = []
            for ex in sense.get("examples", []):
                cleaned_ex = {
                    "rungus": ex.get("rungus"),
                }
                
                orig_ex_en = ex.get("english")
                clean_ex_en = clean_text(orig_ex_en)
                cleaned_ex["english"] = clean_ex_en
                if orig_ex_en != clean_ex_en:
                    stats["cleaned_english_examples"] += 1
                    
                orig_ex_ms = ex.get("malay")
                clean_ex_ms = clean_text(orig_ex_ms)
                cleaned_ex["malay"] = clean_ex_ms
                if orig_ex_ms != clean_ex_ms:
                    stats["cleaned_malay_examples"] += 1
                
                cleaned_sense["examples"].append(cleaned_ex)

            cleaned_entry["senses"].append(cleaned_sense)
            
        cleaned_data.append(cleaned_entry)

    # Write cleaned dataset
    print(f"[*] Saving cleaned dataset: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

    # Print summary statistics
    print("\n================== CLEANING SUMMARY ==================")
    print(f"Total entries processed: {stats['total_entries']}")
    print(f"English definitions cleaned: {stats['cleaned_english_defs']}")
    print(f"Malay definitions cleaned: {stats['cleaned_malay_defs']}")
    print(f"English examples cleaned: {stats['cleaned_english_examples']}")
    print(f"Malay examples cleaned: {stats['cleaned_malay_examples']}")
    print("======================================================\n")

    # Quick test check for 'abai'
    abai_entry = next((e for e in cleaned_data if e["headword"] == "abai"), None)
    if abai_entry:
        print("[*] Verification check for 'abai' entry:")
        print(json.dumps(abai_entry, ensure_ascii=False, indent=2))
    else:
        print("[!] 'abai' entry not found in the dataset.")

if __name__ == "__main__":
    clean_dataset()
