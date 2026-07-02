"""
analyze_books.py — Rungus Corpus Coverage Analyzer v3.0
=========================================================
Analyzes all 9 book files against the morphological analyzer.
Measures coverage, identifies gaps, and generates HITL export.

Usage:
    python analyze_books.py               # run full analysis
    python analyze_books.py --export-review  # also export review CSV
    python analyze_books.py --quick          # skip per-book breakdown

Based on rungus_analyzer_lib.py (v3.0 shared library).
"""

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from rungus_analyzer_lib import (
    load_dictionary, analyze,
    PREFIXES, SUFFIXES, INFIXES, ENCLITICS,
    FUNCTION_WORDS, PROPER_NAMES, LOANWORDS, STANDALONE_WORDS,
)

DATA_PATH  = Path(__file__).parent / "mainDataset_merged.json"
BOOKS_DIR  = Path(__file__).parent / "data" / "books"
REVIEW_CSV = Path(__file__).parent / "review_queue.csv"


def clean_word(w):
    """Lowercase, strip leading/trailing punctuation, keep only alphabetic."""
    w = w.strip().lower()
    w = re.sub(r"^[^a-z]+", "", w)
    w = re.sub(r"[^a-z]+$", "", w)
    return w


def is_likely_rungus(w):
    """Skip very short words and pure numbers."""
    if len(w) <= 1:
        return False
    if re.match(r"^[0-9]+$", w):
        return False
    return True


def categorize(word, freq, result, books_found):
    """Return category string for a word based on analysis result."""
    if word in FUNCTION_WORDS:
        return "function"
    if result["proper_name"]:
        return "proper_name"
    if result["loanword"]:
        return "loanword"
    if result["matched"]:
        if result["root"] == word or result["root"] == result["input"]:
            return "matched"
        return "analyzed"
    return "failed"


def main():
    export_review = "--export-review" in sys.argv
    quick         = "--quick"         in sys.argv

    print("=" * 80)
    print("  RUNGUS CORPUS ANALYSIS v3.0")
    print("=" * 80)

    # ── Load dictionary ────────────────────────────────────────────────
    print("\n[*] Loading dictionary...")
    dictionary = load_dictionary()
    print(f"    {len(dictionary):,} entries  |  "
          f"{len(PREFIXES)} prefixes  |  "
          f"{len(SUFFIXES)} suffixes  |  "
          f"{len(INFIXES)} infixes  |  "
          f"{len(ENCLITICS)} enclitics")

    # ── Collect all words ──────────────────────────────────────────────
    print("\n[*] Scanning book files...")
    all_words  = []
    word_books = {}   # word → set of book numbers

    for i in range(1, 10):
        path = BOOKS_DIR / f"book_{i}.json"
        with open(path, "r", encoding="utf-8") as f:
            lines = json.load(f)

        book_words = []
        for line in lines:
            for raw in line.split():
                c = clean_word(raw)
                if c and is_likely_rungus(c):
                    book_words.append(c)
                    all_words.append(c)
                    word_books.setdefault(c, set()).add(i)

        print(f"    book_{i}: {len(lines):>5} lines  |  "
              f"{len(book_words):>7,} tokens")

    print(f"\n    TOTAL: {len(all_words):,} tokens")

    # ── Frequency count ────────────────────────────────────────────────
    word_freq    = Counter(all_words)
    unique_words = len(word_freq)
    print(f"    UNIQUE: {unique_words:,} word types")

    # ── Morphological analysis ─────────────────────────────────────────
    print("\n[*] Running morphological analysis...")

    cats = {c: [] for c in
            ("function", "proper_name", "loanword", "matched", "analyzed", "failed")}
    token_matched = 0
    token_failed  = 0

    for idx, (word, freq) in enumerate(word_freq.most_common()):
        if idx % 2000 == 0 and idx > 0:
            pct = (token_matched / (token_matched + token_failed) * 100
                   if (token_matched + token_failed) > 0 else 0)
            print(f"    Progress: {idx:>5}/{unique_words}  |  "
                  f"coverage so far: {pct:.1f}%")

        books = sorted(word_books.get(word, set()))
        result = analyze(word, dictionary)
        cat    = categorize(word, freq, result, books)
        cats[cat].append((word, freq, result, books))

        if cat in ("function", "proper_name", "loanword", "matched", "analyzed"):
            token_matched += freq
        else:
            token_failed += freq

    # ── Summary ────────────────────────────────────────────────────────
    total_tokens = token_matched + token_failed
    coverage_pct = token_matched / total_tokens * 100 if total_tokens > 0 else 0

    print("\n" + "=" * 80)
    print("  RESULTS SUMMARY")
    print("=" * 80)

    total_u = unique_words
    print(f"\n  {'Category':<35} {'Unique':>7}  {'% Unique':>9}  {'Tokens':>8}")
    print("  " + "-" * 65)
    labels = {
        "matched":     "Direct dictionary match",
        "analyzed":    "Decomposed via affixes",
        "proper_name": "Proper names (biblical/geo)",
        "loanword":    "Loanwords (Malay/Arabic)",
        "function":    "Function words",
        "failed":      "Failed (no analysis found)",
    }
    for cat, label in labels.items():
        items  = cats[cat]
        count  = len(items)
        tokens = sum(freq for _, freq, *_ in items)
        print(f"  {label:<35} {count:>7,}  {count/total_u*100:>8.1f}%  {tokens:>8,}")

    print("  " + "-" * 65)
    print(f"  {'TOTAL':<35} {total_u:>7,}  {'100.0%':>9}  {total_tokens:>8,}")
    print(f"\n  TOKEN COVERAGE: {coverage_pct:.1f}%  "
          f"({token_matched:,} / {total_tokens:,})")

    # ── Top unknowns ───────────────────────────────────────────────────
    unknown_counter = Counter({w: f for w, f, *_ in cats["failed"]})

    print(f"\n{'=' * 80}")
    print("  TOP 40 MOST COMMON UNKNOWN WORDS")
    print(f"{'=' * 80}")
    print(f"  {'#':>4}  {'Word':<22}  {'Freq':>6}  {'Books'}  Notes")
    print("  " + "-" * 65)

    for i, (word, freq) in enumerate(unknown_counter.most_common(40)):
        books = sorted(word_books.get(word, set()))
        print(f"  {i+1:>4}  {word:<22}  {freq:>6}  {str(books):<16}")

    # ── Sample successful decompositions ──────────────────────────────
    print(f"\n{'=' * 80}")
    print("  SAMPLE SUCCESSFUL DECOMPOSITIONS (first 25)")
    print(f"{'=' * 80}")
    print(f"  {'Word':<22}  {'Root':<18}  {'Breakdown'}")
    print("  " + "-" * 65)

    shown = 0
    for word, freq, result, books in cats["analyzed"]:
        if shown >= 25:
            break
        parts = []
        if result["prefix"]:
            p = result["prefix"]
            if result.get("prefix2"):
                p += f"+{result['prefix2']}"
            parts.append(f"P:{p}")
        if result["infix"]:  parts.append(f"I:{result['infix']}")
        if result["suffix"]: parts.append(f"S:{result['suffix']}")
        if result["enclitic"]: parts.append(f"E:{result['enclitic']}")   # FIXED: was 'clitic'
        breakdown = " + ".join(parts) if parts else "(direct)"
        print(f"  {word:<22}  {str(result['root']):<18}  {breakdown}")
        shown += 1

    # ── Per-book breakdown ─────────────────────────────────────────────
    if not quick:
        print(f"\n{'=' * 80}")
        print("  PER-BOOK COVERAGE")
        print(f"{'=' * 80}")
        print(f"  {'Book':<10}  {'Type':<10}  {'Lines':>6}  "
              f"{'Tokens':>7}  {'Coverage':>9}")
        print("  " + "-" * 55)

        for i in range(1, 10):
            path = BOOKS_DIR / f"book_{i}.json"
            with open(path, "r", encoding="utf-8") as f:
                book_lines = json.load(f)

            book_total = 0
            book_matched = 0
            for line in book_lines:
                for raw in line.split():
                    c = clean_word(raw)
                    if c and is_likely_rungus(c):
                        book_total += 1
                        r = analyze(c, dictionary)
                        if r["matched"]:
                            book_matched += 1

            cov = book_matched / book_total * 100 if book_total > 0 else 0
            content_type = "folk tales" if i <= 2 else "religious"
            print(f"  book_{i:<5}  {content_type:<10}  {len(book_lines):>6,}  "
                  f"{book_total:>7,}  {cov:>8.1f}%")

    # ── HITL export ────────────────────────────────────────────────────
    if export_review:
        print(f"\n[*] Exporting HITL review queue to {REVIEW_CSV}...")
        with open(REVIEW_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "word", "frequency", "books_found_in", "confidence",
                "prefix_detected", "infix_detected", "suffix_detected",
                "enclitic_detected", "proper_name", "loanword",
                "your_proposed_root", "english_gloss", "notes"
            ])
            writer.writeheader()

            # Export top-500 unknowns for human review
            for word, freq in unknown_counter.most_common(500):
                r = analyze(word, dictionary)
                books = sorted(word_books.get(word, set()))
                writer.writerow({
                    "word":            word,
                    "frequency":       freq,
                    "books_found_in":  str(books),
                    "confidence":      f"{r['confidence']:.2f}",
                    "prefix_detected": r["prefix"] or "",
                    "infix_detected":  r["infix"] or "",
                    "suffix_detected": r["suffix"] or "",
                    "enclitic_detected": r["enclitic"] or "",  # FIXED: was 'clitic'
                    "proper_name":     "Y" if r["proper_name"] else "",
                    "loanword":        "Y" if r["loanword"] else "",
                    "your_proposed_root": "",
                    "english_gloss":   "",
                    "notes":           "",
                })
        print(f"    Exported {min(500, len(unknown_counter))} words to review.")

    print("\n[*] Analysis complete.")


if __name__ == "__main__":
    main()
