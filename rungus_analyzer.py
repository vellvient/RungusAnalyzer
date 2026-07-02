"""
rungus_analyzer.py — Rungus Morphological Analyzer CLI v3.0
============================================================
Thin wrapper around rungus_analyzer_lib.py.
All linguistic logic lives in the shared library.

Usage:
    python rungus_analyzer.py                      # run demo
    python rungus_analyzer.py "word1" "word2" ...  # analyze specific words

Author: Aifven Nelson
"""

import sys
import os

# Ensure consistent UTF-8 output on all platforms (including Windows CP932)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add project root to path so both 'python rungus_analyzer.py'
# and 'from rungus_analyzer import ...' work correctly.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Re-export everything from the shared library ───────────────────────────
# This keeps backward compatibility: any code that did
#   from rungus_analyzer import load_dictionary, analyze
# will continue to work unchanged.
from rungus_analyzer_lib import (                       # noqa: F401, E402
    load_dictionary,
    analyze,
    generate,
    suggest_similar,
    PREFIXES,
    SUFFIXES,
    INFIXES,
    ENCLITICS,
    SUBSTITUTION_MAP,
    VOWEL_CONTRACTIONS,
    STANDALONE_WORDS,
    PROPER_NAMES,
    LOANWORDS,
    FUNCTION_WORDS,
    VIRTUAL_ROOTS,
    NASAL_ADDITION,
)


# ═══════════════════════════════════════════════════════════════════════
# CLI DEMO
# ═══════════════════════════════════════════════════════════════════════

def demo(words=None):
    """Run an interactive demo of the analyzer.

    Args:
        words: optional list of words to analyze.  If None, a curated
               list of test cases is used.
    """
    dictionary = load_dictionary()

    if words is None:
        words = [
            # Direct dictionary hits
            "panau", "ginavo", "araat", "toun", "ulun",
            # Standalone / high-frequency missing words
            "ioti", "iadko", "elaan", "dikou", "oku",
            # Prefixed forms
            "mamanau", "nokolohing", "ongulun", "mongoduat",
            "mamamanau", "mimot", "songulun",
            # Infixed forms
            "rumikot", "rinumikot",
            # Suffixed forms
            "kiroon", "azakon",
            # Prefix + enclitic
            "pinongimotku", "nokolobongno",
            # Proper names (should be flagged, not failed)
            "yesus", "paulus",
            # Loanwords (should be flagged, not failed)
            "yang", "dengan",
            # Reduplication
            "agas-agas",
            # Tricky / edge cases
            "pemot", "minangagama",
        ]

    # ── Header ──────────────────────────────────────────────────────────
    print("=" * 90)
    print("  Rungus Morphological Analyzer v3.0")
    print("  Based on Forschner (1994) + Swarthmore LING073 + SIL Webonary (12K+ entries)")
    print(f"  Dictionary: {len(dictionary):,} entries | "
          f"Prefixes: {len(PREFIXES)} | Suffixes: {len(SUFFIXES)} | "
          f"Infixes: {len(INFIXES)} | Enclitics: {len(ENCLITICS)}")
    print("=" * 90)

    header = f"  {'Word':<22} {'Root':<18} {'Prefix':<18} {'Infix':<8} {'Suf':<7} {'Enc':<6} {'Conf':<5}  {'Flags'}"
    print(header)
    print("  " + "-" * 85)

    matched_count = 0
    for word in words:
        r = analyze(word, dictionary)

        prefix_str = r["prefix"] or ""
        if r.get("prefix2"):
            prefix_str = f"{prefix_str}+{r['prefix2']}"
        infix_str   = r["infix"] or ""
        suffix_str  = r["suffix"] or ""
        enc_str     = r["enclitic"] or ""
        root_str    = str(r["root"] or "?")[:17]
        conf        = f"{r['confidence']:.2f}" if r["matched"] else "0.00"
        marker      = "[Y]" if r["matched"] else "[N]"

        flags = []
        if r["proper_name"]:    flags.append("NAME")
        if r["loanword"]:       flags.append("LOAN")
        if r["reduplication"]:  flags.append(f"REDUP({r['reduplication']})")

        print(f"  {marker} {word:<20} {root_str:<18} {prefix_str:<18} "
              f"{infix_str:<8} {suffix_str:<7} {enc_str:<6} {conf:<5}  {' '.join(flags)}")

        if r["matched"]:
            matched_count += 1

    print(f"\n  Matched {matched_count}/{len(words)} words "
          f"({matched_count/len(words)*100:.0f}%)")

    # ── Detailed breakdowns ──────────────────────────────────────────────
    detailed = ["nokolohing", "pinongimotku", "mamamanau", "ongulun"]
    for w in detailed:
        if w not in words:
            continue
        print(f"\n  --- Detailed breakdown: '{w}' ---")
        r = analyze(w, dictionary)
        for step in r["breakdown"]:
            print(f"    -> {step}")
        if r["matched"]:
            print(f"    Root: {r['root']} = \"{r['root_gloss']}\"")
        else:
            sug = suggest_similar(w, dictionary, max_dist=2, max_results=3)
            if sug:
                print(f"    Suggestions: {', '.join(sug)}")

    # ── Generation demo ──────────────────────────────────────────────────
    print("\n  --- Morphological generation examples ---")
    gen_examples = [
        ("panau",   "mongo",  None,    None,   None,  "mamanau (actor focus)"),
        ("imot",    "po",     None,    None,   None,  "pemot (causative)"),
        ("rikot",   None,     None,    "um",   None,  "rumikot (intransitive)"),
        ("rikot",   None,     None,    "inum", None,  "rinumikot (past intransitive)"),
        ("ulun",    "ongo",   None,    None,   None,  "ongulun (plural)"),
        ("lobong",  "ko",     "on",    None,   None,  "kolobongon (realisation + patient focus)"),
        ("lobong",  "ko",     "on",    None,   "ku",  "kolobongonku (+ my)"),
        ("gama",    "manga",  None,    None,   None,  "mangagama (actor focus, voiced C)"),
    ]
    for root, pfx, sfx, infx, enc, desc in gen_examples:
        result = generate(root, prefix=pfx, suffix=sfx, infix=infx, enclitic=enc)
        print(f"    generate({root!r}, prefix={pfx!r:<8} suffix={sfx!r:<6} "
              f"infix={infx!r:<6} enc={enc!r:<5}) = {result!r:<18} # {desc}")


if __name__ == "__main__":
    # Allow passing words as CLI args: python rungus_analyzer.py word1 word2 ...
    cli_words = sys.argv[1:] if len(sys.argv) > 1 else None
    demo(words=cli_words)
