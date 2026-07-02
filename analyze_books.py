"""
Analyze all book texts against the Rungus morphological analyzer.
Measures success/failure rates and identifies gaps.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

# Add project dir to path
sys.path.insert(0, str(Path(__file__).parent))
from rungus_analyzer import load_dictionary, analyze, PREFIXES, SUFFIXES, INFIXES

DATA_PATH = Path(__file__).parent / "mainDataset_merged.json"
BOOKS_DIR = Path(__file__).parent / "data" / "books"

# Function words / particles that are common Rungus but not in dictionary
FUNCTION_WORDS = {
    "i", "di", "do", "om", "dit", "dot", "sid", "ku", "nu", "no", "mo",
    "ko", "po", "ka", "a", "o", "nga", "yo", "tu", "no", "ot", "bo",
    "na", "da", "po", "to", "so", "ro", "dino", "dioti", "dih", "dih",
    "iti", "iti", "ino", "dino", "sinod", "sid", "insan", "manjadi",
    "nopo", "kopo", "song", "ong", "it", "tu", "diti", "diti",
}

def clean_word(w):
    """Clean a word: lowercase, strip punctuation, keep only alpha chars."""
    w = w.strip().lower()
    w = re.sub(r'^[^a-záéíóúàèìòùâêîôûãõñç\']+', '', w)
    w = re.sub(r'[^a-záéíóúàèìòùâêîôûãõñç\']+$', '', w)
    return w

def is_likely_rungus(w):
    """Basic heuristic: skip very short words, numbers, etc."""
    if len(w) <= 1:
        return False
    if re.match(r'^[0-9.,;:!?()\[\]{}]+$', w):
        return False
    return True

def main():
    print("=" * 80)
    print("RUNGUS BOOK CORPUS ANALYSIS")
    print("=" * 80)
    
    # Load dictionary
    print("\n[*] Loading dictionary...")
    dictionary = load_dictionary()
    print(f"    {len(dictionary)} words in dictionary")
    
    # Calculate affix stats
    print(f"    {len(PREFIXES)} known prefixes")
    print(f"    {len(SUFFIXES)} known suffixes")
    print(f"    {len(INFIXES)} known infixes")
    
    # Collect all words from books
    print("\n[*] Scanning book files...")
    all_words = []
    book_word_counts = {}
    
    for i in range(1, 10):
        path = BOOKS_DIR / f"book_{i}.json"
        with open(path, 'r', encoding='utf-8') as f:
            lines = json.load(f)
        
        book_words = []
        for line in lines:
            for raw_word in line.split():
                cleaned = clean_word(raw_word)
                if cleaned and is_likely_rungus(cleaned):
                    book_words.append(cleaned)
                    all_words.append(cleaned)
        
        book_word_counts[f"book_{i}"] = len(book_words)
        print(f"    book_{i}: {len(lines):>5} lines, {len(book_words):>6} words")
    
    print(f"\n    TOTAL: {sum(book_word_counts.values()):,} word tokens")
    
    # Get unique words and their frequencies
    word_freq = Counter(all_words)
    unique_words = len(word_freq)
    print(f"    UNIQUE words: {unique_words:,}")
    
    # Run analysis on each unique word
    print("\n[*] Running morphological analysis on all unique words...")
    
    results = {
        "matched": [],      # word found directly in dictionary
        "analyzed": [],     # word decomposed via affix stripping -> root found
        "partial": [],      # affixes detected but root not in dictionary
        "failed": [],       # no affixes detected, not in dictionary
        "function": [],     # likely function words (particles, pronouns)
    }
    
    word_index = {}  # word -> root info
    unknown_counter = Counter()  # most common unknown words
    
    for idx, (word, freq) in enumerate(word_freq.most_common()):
        if idx % 1000 == 0 and idx > 0:
            print(f"    Progress: {idx}/{unique_words}...")
        
        # Check if it's a known function word
        if word in FUNCTION_WORDS:
            results["function"].append((word, freq, "function word"))
            continue
        
        # Run analysis
        result = analyze(word, dictionary)
        
        if result["matched"]:
            if result["root"] == result["input"]:
                results["matched"].append((word, freq, result))
            else:
                results["analyzed"].append((word, freq, result))
        elif any([result["prefix"], result["infix"], result["suffix"], result["clitic"]]):
            results["partial"].append((word, freq, result))
        else:
            results["failed"].append((word, freq))
            unknown_counter[word] += freq
    
    # Print summary
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    
    total = len(word_freq)
    matched_count = len(results["matched"])
    analyzed_count = len(results["analyzed"])
    partial_count = len(results["partial"])
    failed_count = len(results["failed"])
    function_count = len(results["function"])
    
    print(f"\n{'Category':<30} {'Count':>8} {'% of Unique':>12}")
    print("-" * 52)
    
    def pct(n): return f"{n/total*100:>10.1f}%"
    
    print(f"{'✅ Direct dictionary match':<30} {matched_count:>8} {pct(matched_count)}")
    print(f"{'🔍 Decomposed via affixes':<30} {analyzed_count:>8} {pct(analyzed_count)}")
    print(f"{'⚠️ Partial (affixes found, root missing)':<30} {partial_count:>8} {pct(partial_count)}")
    print(f"{'❌ No match at all':<30} {failed_count:>8} {pct(failed_count)}")
    print(f"{'🧩 Function words (excluded)':<30} {function_count:>8} {pct(function_count)}")
    print("-" * 52)
    print(f"{'TOTAL unique words':<30} {total:>8} {'100.0%':>10}")
    
    # Print top unknown words
    print(f"\n{'=' * 80}")
    print(f"TOP 50 MOST COMMON UNKNOWN WORDS (failed to analyze)")
    print(f"{'=' * 80}")
    print(f"{'#':>4} {'Word':<25} {'Freq':>6} {'Possible analysis'}")
    print("-" * 80)
    
    for i, (word, freq) in enumerate(unknown_counter.most_common(50)):
        if i >= 50:
            break
        # Run analysis again to show partial info
        result = analyze(word, dictionary)
        parts = []
        if result["prefix"]: parts.append(f"P:{result['prefix']}")
        if result["infix"]: parts.append(f"INF:{result['infix']}")
        if result["suffix"]: parts.append(f"S:{result['suffix']}")
        if result["clitic"]: parts.append(f"C:{result['clitic']}")
        hint = ", ".join(parts) if parts else "(no affixes detected)"
        print(f"{i+1:>4} {word:<25} {freq:>6}  {hint}")
    
    # Print successfully analyzed examples
    print(f"\n{'=' * 80}")
    print(f"SAMPLE SUCCESSFUL DECOMPOSITIONS")
    print(f"{'=' * 80}")
    print(f"{'Word':<25} {'Root':<20} {'Breakdown'}")
    print("-" * 80)
    for word, freq, result in results["analyzed"][:30]:
        parts = []
        if result["prefix"]: parts.append(f"P:{result['prefix']}")
        if result["infix"]: parts.append(f"INF:{result['infix']}")
        if result["suffix"]: parts.append(f"S:{result['suffix']}")
        if result["clitic"]: parts.append(f"C:{result['clitic']}")
        breakdown = " + ".join(parts) if parts else "(direct)"
        gloss = result.get("dictionary_gloss", "")[:30]
        print(f"{word:<25} {str(result['root']):<20} {breakdown}")
    
    # Book-by-book stats
    print(f"\n{'=' * 80}")
    print(f"BOOK-BY-BOOK ANALYSIS")
    print(f"{'=' * 80}")
    
    for i in range(1, 10):
        path = BOOKS_DIR / f"book_{i}.json"
        with open(path, 'r', encoding='utf-8') as f:
            book_lines = json.load(f)
        
        book_unknown = Counter()
        book_total = 0
        for line in book_lines:
            for raw_word in line.split():
                cleaned = clean_word(raw_word)
                if cleaned and is_likely_rungus(cleaned) and cleaned not in FUNCTION_WORDS:
                    book_total += 1
                    result = analyze(cleaned, dictionary)
                    if not result["matched"]:
                        book_unknown[cleaned] += 1
        
        total_analyzed = book_total
        total_unknown = sum(book_unknown.values())
        coverage = (total_analyzed - total_unknown) / total_analyzed * 100 if total_analyzed > 0 else 0
        content_type = "folk tales" if i <= 2 else "religious"
        print(f"    book_{i:<2} ({content_type:<10})  {len(book_lines):>5} lines  {total_analyzed:>7} words  {coverage:>5.1f}% coverage")
    
    print("\n[*] Analysis complete.")
    print(f"[*] Results saved to: {Path(__file__).parent / 'book_analysis_report.txt'}")

if __name__ == "__main__":
    main()
