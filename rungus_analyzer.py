"""
Rungus Morphological Analyzer v2.0
Based on Forschner's "Outline of a Momogun Grammar (Rungus Dialect)" 1994
and Swarthmore LING073 Spring 2025 Rungus transducer research.

Analyzes Rungus words into root + affixes with semantic meanings.
"""

import json
import re
from pathlib import Path

DATA_PATH = Path(__file__).parent / "mainDataset_merged.json"

# ═══════════════════════════════════════════════════════════════
# 1. PHONOLOGICAL RULES (from Forschner §1.2–1.4)
# ═══════════════════════════════════════════════════════════════

# Consonant substitution: when certain prefixes attach,
# the stem-initial consonant is replaced by a nasal at the same POA
# Format: surface_initial → [possible_root_initials]
SUBSTITUTION_MAP = {
    'm': ['m', 'p', 'v', 'b'],   # m could be original m, or p→m, v→m, b→m
    'n': ['n', 't', 's'],        # n could be original n, or t→n, s→n
    'ng': ['ng', 'k'],           # ng could be original ng, or k→ng
}

# Nasal addition: voiced consonants get a nasal prefix added
# (for mongo-/manga- type prefixes)
NASAL_ADDITION = {'d', 'g', 'h', 'r', 'l', 'z', 'j', 'y', 'w'}

# Vowel contraction rules (Forschner §1.21–1.22)
# Used in reverse for analysis
VOWEL_CONTRACTIONS = {
    'e': [('a', 'i'), ('o', 'i')],  # e could be a+i or o+i
    'u': [('o', 'u')],              # u could be o+u
    'a': [('a', 'a')],              # a could be a+a
    'o': [('o', 'o')],              # o could be o+o
}

# ═══════════════════════════════════════════════════════════════
# 2. AFFIX INVENTORY (from Forschner §2.2–2.4 + §4.1)
# ═══════════════════════════════════════════════════════════════

# Prefixes: (prefix_string, category, meaning, substitution_type)
# substitution_type: 'sub' = replaces initial C with nasal
#                    'add' = adds nasal before initial C
#                    'none' = no change
#                    'vowel' = vowel-assimilating (o-varies with a-)
PREFIXES = [
    # ── Intransitive prefixes (§2.21) ──
    ("miri",          "intransitive",  "aimless/wandering action",           "add"),
    ("mi",            "intransitive",  "reciprocal/dual action",            "none"),
    ("mu",            "intransitive",  "state of being (occupation)",       "none"),
    ("moki",          "intransitive",  "desirous/wanting to",               "add"),
    ("mokipopoko",    "intransitive",  "improbable wish",                   "add"),

    # ── Transitive actor focus prefixes (§2.221) ──
    ("mong",          "transitive",    "actor focus (vowel-init stem)",     "sub"),
    ("moko",          "transitive",    "actor focus (vowel-init,perfect)",  "sub"),
    ("mongo",         "transitive",    "actor focus (voiced C stem)",       "none"),
    ("minong",        "transitive",    "actor focus PAST (vowel-init)",     "sub"),
    ("mino",          "transitive",    "actor focus PAST (voiced C)",       "none"),
    ("nokopong",      "transitive",    "actor focus PERFECT (vowel-init)",  "sub"),

    # ── Perfect / accidental prefixes (§2.226–2.227) ──
    ("noko",          "perfect",       "accidental perfective",             "sub"),
    ("nakapa",        "perfect",       "perfect transitive",                "sub"),
    ("nokopo",        "perfect",       "perfect transitive (voiced C)",     "none"),

    # ── Causative prefixes (§2.223) ──
    ("po",            "causative",     "causative action",                  "sub"),
    ("pa",            "causative",     "causative action (a-stem)",         "sub"),
    ("ponga",         "causative",     "causative imperative",              "sub"),
    ("pongi",         "causative",     "causative imperative (i-stem)",     "sub"),
    ("popi",          "causative",     "reciprocal causative",              "none"),

    # ── Realisation / potential prefixes (§2.224) ──
    ("ko",            "realisation",   "realisation/potentiality",          "sub"),
    ("ka",            "realisation",   "realisation/potentiality (a-stem)", "sub"),
    ("kapa",          "realisation",   "completed action (a-stem)",         "sub"),
    ("kopo",          "realisation",   "completed action (o-stem)",         "none"),

    # ── Preterit causative prefixes (§2.225) ──
    ("kinopo",        "causative-past","causative past (voiced C)",         "none"),
    ("pinong",        "causative-past","causative past (vowel-init)",       "sub"),

    # ── Plural prefixes (§2.461) ──
    ("ongo",          "plural",        "plural marker",                     "none"),
    ("anga",          "plural",        "plural marker (a-stem)",            "none"),
    
    # ── Intensifier prefixes (§1.31) ──
    ("ta",            "intensifier",   "intensifier (extremely)",           "none"),
    ("to",            "intensifier",   "intensifier (extremely)",           "none"),

    # ── Other prefixes ──
    ("mang",          "transitive",    "actor focus (a-stem)",              "sub"),
    ("min",           "perfect",       "actor focus past (m-stems)",        "sub"),
    ("no",            "perfect",       "patient focus perfect",             "none"),
]

# Suffixes: (suffix_string, category, meaning)
SUFFIXES = [
    # ── Verbal suffixes (§2.34) ──
    ("on",            "verbal",        "patient focus / gerundive"),
    ("an",            "verbal",        "reference focus / locative"),
    ("o",             "verbal",        "imperative patient focus"),
    ("ai",            "verbal",        "imperative reference focus"),

    # ── Nominalizing suffixes (§2.411–2.412) ──
    ("onon",          "nominal",       "nomina actionis futurae"),
    ("anon",          "nominal",       "nomina actionis futurae"),
    ("inai",          "nominal",       "nomina actionis"),
]

# Infixes: (infix, category, meaning)
INFIXES = [
    ("-in-", "aspect", "past/perfective marker"),
    ("-um-", "aspect", "intransitive process"),
    ("-inum-", "aspect", "past of intransitive process"),
    ("-on-", "aspect", "plural in verb (rare)"),
]

# Enclitics: (enclitic, category, meaning)
ENCLITICS = [
    ("-ku", "pronominal", "my / I (1sg)"),
    ("-nu", "pronominal", "your / you (2sg)"),
    ("-no", "pronominal", "his/her (3sg)"),
    ("-mo", "pronominal", "his/her (3sg variant)"),
    ("-dau", "pronominal", "his/her own (reflexive)"),
    ("-dati", "pronominal", "their (3pl)"),
    ("-dino", "pronominal", "their then (3pl past)"),
    ("-diti", "pronominal", "their here (3pl prox)"),
    ("-ko", "pronominal", "you (2sg)"),
    ("-kou", "pronominal", "you (2pl)"),
    ("-zou", "pronominal", "we (excl)"),

    # Aspectual enclitics (§2.6)
    ("-po", "aspect", "still / yet / more"),
    ("-no", "aspect", "already"),
    ("-nopo", "aspect", "always / continuous"),
]

# Sort all by length (longest first) to prefer longer matches
PREFIXES = sorted(PREFIXES, key=lambda x: len(x[0]), reverse=True)
SUFFIXES = sorted(SUFFIXES, key=lambda x: len(x[0]), reverse=True)
ENCLITICS = sorted(ENCLITICS, key=lambda x: len(x[0]), reverse=True)
INFIXES_LIST = sorted(INFIXES, key=lambda x: len(x[1]), reverse=True)


# ═══════════════════════════════════════════════════════════════
# 3. DICTIONARY LOADING
# ═══════════════════════════════════════════════════════════════

# Known unlisted/missing roots mapped to their closet dictionary derivatives
# This acts as an active lexical-patch for Webonary omissions
VIRTUAL_ROOTS = {
    'ruhang': 'koruhang',   # ruhang is the true root of companion, koruhang
}

def resolve_to_parent(entry_name, dictionary):
    """If the matched entry is tagged as a subentry, recursively
    resolve it to its primary grandparent parent-root."""
    seen = set()
    current = entry_name.strip().lower()
    
    # Resolve physical gaps/dictionary omissions first
    if current in VIRTUAL_ROOTS:
        current = VIRTUAL_ROOTS[current]
        
    while current in dictionary:
        if current in seen:
            break
        seen.add(current)
        entry = dictionary[current]
        if entry.get("is_subentry", False) and entry.get("parent"):
            current = entry["parent"].strip().lower()
            if current in VIRTUAL_ROOTS:
                current = VIRTUAL_ROOTS[current]
        else:
            break
    # Return the final canonical heading
    if current in dictionary:
        return dictionary[current]["headword"], dictionary[current]["gloss"]
    return entry_name, None
def load_dictionary():
    """Load the merged dictionary dataset into a lookup."""
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    lookup = {}
    for entry in data:
        hw = entry.get("headword", "").strip().lower()
        if hw:
            senses = []
            for s in entry.get("senses", []):
                gloss = s.get("english") or s.get("malay") or ""
                senses.append(gloss)
            lookup[hw] = {
                "headword": entry["headword"],
                "gloss": "; ".join(senses),
                "subentries": [s.get("headword", "") for s in entry.get("subentries", [])],
                "is_subentry": False,
            }
    for entry in data:
        for sub in entry.get("subentries", []):
            shw = sub.get("headword", "").strip().lower()
            if shw and shw not in lookup:
                lookup[shw] = {
                    "headword": sub["headword"],
                    "gloss": f"(sub-entry of {entry['headword']})",
                    "parent": entry["headword"],
                    "is_subentry": True,
                }
    return lookup


# ═══════════════════════════════════════════════════════════════
# 4. REVERSE SUBSTITUTION RULES
# ═══════════════════════════════════════════════════════════════

def possible_roots_for(word, substitutions):
    """Given a word after stripping a prefix, try all possible
    reverse substitutions on the initial segment to find dictionary roots."""
    if not word:
        return []
    first = word[0]
    candidates = substitutions.get(first, [first])
    return [c + word[1:] for c in candidates]


def reverse_substitute(remainder, prefix_type, substitutions):
    """Apply reverse substitution rules after stripping a prefix.
    Returns list of possible root forms to check against dictionary."""
    if not remainder:
        return []
    
    if prefix_type == 'sub':
        # Substituting prefix: stem-initial C was replaced by nasal
        return possible_roots_for(remainder, substitutions)
    elif prefix_type == 'add':
        # Adding prefix: initial consonant + nasal prefix stays intact
        # For analysis, we just check the remainder as-is
        return [remainder]
    else:
        # No substitution
        return [remainder]


# ═══════════════════════════════════════════════════════════════
# 5. AFFIX STRIPPING FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def strip_enclitic(word):
    """Strip pronominal and aspectual enclitics from the end of a word."""
    for enclitic, category, meaning in ENCLITICS:
        e = enclitic.lstrip('-')
        if word.endswith(e) and len(word) > len(e) + 1:
            core = word[:-len(e)]
            return e, category, meaning, core
    return None, None, None, word


def strip_infix(word):
    """Strip infixes (-in-, -um-, -inum-, etc.) from a word.
    Infixes appear after the first consonant."""
    for infix, category, meaning in INFIXES:
        bare = infix.strip("-")
        # Pattern: first C + infix + rest
        pattern = re.compile(r"^([^aeiouáéíóú]+)" + re.escape(bare) + r"(.*)", re.IGNORECASE)
        m = pattern.match(word)
        if m:
            prefix_c = m.group(1)
            rest = m.group(2)
            root = prefix_c + rest
            return bare, category, meaning, root
    return None, None, None, word


def decontract_vowel(prefix, remainder):
    """Handle vowel de-contraction at prefix-stem boundary.
    When a vowel-ending prefix attaches to a vowel-initial stem,
    the two vowels merge. In analysis, after stripping the prefix,
    we may need to restore the stem's initial vowel.
    
    E.g., ongo- + ulun → ongulun. After stripping 'ongo-', we get
    'lun', but the root is 'ulun' (o+u contracted to u).
    """
    if not prefix or not remainder:
        return [remainder]
    
    prefix_last = prefix[-1]
    if prefix_last not in 'aeiou':
        return [remainder]  # Prefix doesn't end in vowel, no contraction
    
    candidates = [remainder]
    first_char = remainder[0] if remainder else ''
    
    # The vowel contraction rules (§1.22):
    # o + u = u,  a + a = a,  o + o = o,  o + i = e
    #
    # For analysis, if the remainder starts with a single consonant
    # (no vowel), the stem's initial vowel may have been absorbed
    if first_char and first_char not in 'aeiou':
        # The stem's initial vowel was absorbed into the prefix's final vowel
        # Try all possible stem-initial vowels
        if prefix_last == 'o':
            # o + ? → ? means stem could start with almost anything
            # But most commonly: ulun, iti, ino, etc.
            for v in ['u', 'i', 'o', 'a', 'e']:
                candidates.append(v + remainder)
        elif prefix_last == 'a':
            # a + a = a, so the stem started with 'a'
            candidates.append('a' + remainder)
        elif prefix_last == 'i':
            candidates.append('i' + remainder)
        elif prefix_last == 'u':
            candidates.append('u' + remainder)
        elif prefix_last == 'e':
            candidates.append('e' + remainder)
    else:
        # Remainder starts with a vowel — check if it's a merged result
        # E.g., ongo- + ilo → ongelo (o+i=e). Strip 'ongo-' → 'lo'? 
        # Actually remainder would be 'lo' in some cases
        pass
    
    return candidates


def try_strip_prefixes(word, dictionary):
    """Try stripping each known prefix and checking if the remainder 
    (with reverse substitutions) exists in the dictionary."""
    results = []
    for prefix_str, category, meaning, sub_type in PREFIXES:
        if not word.startswith(prefix_str):
            continue
        if len(word) <= len(prefix_str) + 1:
            continue
        
        remainder = word[len(prefix_str):]
        
        # Try vowel de-contraction (prefix ended in vowel, stem started with vowel)
        decontracted = decontract_vowel(prefix_str, remainder)
        
        # Try reverse substitution to find possible roots
        possible_candidates = []
        for dc in decontracted:
            possible_candidates.extend(reverse_substitute(dc, sub_type, SUBSTITUTION_MAP))
        # Also try the plain remainder
        possible_candidates.append(remainder)
        # Remove duplicates
        possible_roots = list(set(possible_candidates))
        
        for possible_root in possible_roots:
            # Map through VIRTUAL_ROOTS if applicable
            lookup_root = possible_root
            if possible_root in VIRTUAL_ROOTS:
                lookup_root = VIRTUAL_ROOTS[possible_root]
                
            if lookup_root in dictionary:
                results.append({
                    "prefix": prefix_str,
                    "category": category,
                    "meaning": meaning,
                    "root": possible_root,  # Preserve the semantic root form
                    "gloss": dictionary[lookup_root]["gloss"],
                    "matched": True,
                })
            # Try with infix analysis too
            infix_char, infix_cat, infix_meaning, after_infix = strip_infix(possible_root)
            lookup_infix_root = after_infix
            if after_infix in VIRTUAL_ROOTS:
                lookup_infix_root = VIRTUAL_ROOTS[after_infix]
                
            if infix_char and lookup_infix_root in dictionary:
                results.append({
                    "prefix": prefix_str,
                    "category": category,
                    "meaning": meaning,
                    "infix": infix_char,
                    "infix_meaning": infix_meaning,
                    "root": after_infix,
                    "gloss": dictionary[lookup_infix_root]["gloss"],
                    "matched": True,
                })
            # Try with suffix stripping too
            for suffix_str, suf_cat, suf_meaning in SUFFIXES:
                if possible_root.endswith(suffix_str) and len(possible_root) > len(suffix_str) + 1:
                    core = possible_root[:-len(suffix_str)]
                    lookup_core = core
                    if core in VIRTUAL_ROOTS:
                        lookup_core = VIRTUAL_ROOTS[core]
                    if lookup_core in dictionary:
                        results.append({
                            "prefix": prefix_str,
                            "category": category,
                            "meaning": meaning,
                            "suffix": suffix_str,
                            "suffix_meaning": suf_meaning,
                            "root": core,
                            "gloss": dictionary[lookup_core]["gloss"],
                            "matched": True,
                        })
    return results


def try_strip_suffixes(word, dictionary):
    """Try stripping each known suffix."""
    for suffix_str, category, meaning in SUFFIXES:
        if word.endswith(suffix_str) and len(word) > len(suffix_str) + 1:
            core = word[:-len(suffix_str)]
            if core in dictionary:
                return suffix_str, category, meaning, dictionary[core]
            # Also check if core has an infix
            infix_char, infix_cat, infix_meaning, after_infix = strip_infix(core)
            if infix_char and after_infix in dictionary:
                return suffix_str, category, meaning, dictionary[after_infix]
    return None, None, None, None


# ═══════════════════════════════════════════════════════════════
# 6. MAIN ANALYSIS FUNCTION
# ═══════════════════════════════════════════════════════════════

def analyze(word, dictionary):
    """Full morphological analysis of a Rungus word."""
    word_lower = word.strip().lower()
    original = word.strip()

    result = {
        "input": original,
        "root": None,
        "root_gloss": None,
        "prefix": None,
        "prefix_meaning": None,
        "infix": None,
        "infix_meaning": None,
        "suffix": None,
        "suffix_meaning": None,
        "enclitic": None,
        "enclitic_meaning": None,
        "breakdown": [],
        "matched": False,
        "confidence": 0,
    }

    # Helper function to assign matched outcomes canonical grandparent root resolving
    def set_canonical_match(root_key, confidence_score, explanation_list):
        canonical_hw, canonical_gloss = resolve_to_parent(root_key, dictionary)
        result["root"] = canonical_hw
        result["root_gloss"] = canonical_gloss
        result["matched"] = True
        result["confidence"] = confidence_score
        for exp in explanation_list:
            result["breakdown"].append(exp)
        if canonical_hw != dictionary.get(root_key, {}).get("headword", root_key):
            result["breakdown"].append(f"  → (resolved sub-entry '{root_key}' to parent root '{canonical_hw}')")

    # Step 1: Strip enclitics (outermost layer)
    enc_str, enc_cat, enc_meaning, working = strip_enclitic(word_lower)
    if enc_str:
        result["enclitic"] = enc_str
        result["enclitic_meaning"] = f"{enc_meaning} ({enc_cat})"
        result["breakdown"].append(f"enclitic: -{enc_str} = {enc_meaning}")

    # Step 2: Check if core word exists directly in dictionary
    if working in dictionary and not dictionary[working].get("is_subentry", False):
        set_canonical_match(working, 1.0, [f"✓ root: '{working}' = \"{dictionary[working]['gloss']}\""])
        return result
    
    # Also check with vowel ending variations (common in Rungus)
    variations = [working]
    if working.endswith('o'):
        variations.append(working[:-1] + 'a')
    if working.endswith('a'):
        variations.append(working[:-1] + 'o')
    if working.endswith('u'):
        variations.append(working[:-1] + 'o')
    if working.endswith('i'):
        variations.append(working[:-1])
    if working.endswith('e'):
        variations.append(working[:-1] + 'o')
    
    for var in variations:
        if var != working and var in dictionary and not dictionary[var].get("is_subentry", False):
            set_canonical_match(var, 0.9, [f"✓ root: '{var}' = \"{dictionary[var]['gloss']}\" (vowel variant)"])
            return result

    # Step 3: Try stripping infix (infixes are close to the root)
    infix_str, infix_cat, infix_meaning, after_infix = strip_infix(working)
    if infix_str:
        result["infix"] = infix_str
        result["infix_meaning"] = infix_meaning
        result["breakdown"].append(f"infix: -{infix_str}- = {infix_meaning}")
        
        if after_infix in dictionary:
            set_canonical_match(after_infix, 0.85, [f"✓ root: '{after_infix}' = \"{dictionary[after_infix]['gloss']}\""])
            return result

    # Step 4: Try stripping prefixes (with reverse substitution)
    prefix_results = try_strip_prefixes(working, dictionary)
    if prefix_results:
        best = prefix_results[0]  # First match (longest prefix)
        result["prefix"] = best["prefix"]
        result["prefix_meaning"] = f"{best['meaning']} ({best['category']})"
        result["infix"] = best.get("infix")
        result["infix_meaning"] = best.get("infix_meaning")
        result["suffix"] = best.get("suffix")
        result["suffix_meaning"] = best.get("suffix_meaning")
        
        parts = [f"prefix: {best['prefix']} = {best['meaning']}"]
        if best.get("infix"):
            parts.append(f"infix: -{best['infix']}-")
        if best.get("suffix"):
            parts.append(f"suffix: -{best['suffix']} = {best['suffix_meaning']}")
        parts.append(f"✓ root candidate: '{best['root']}'")
        
        set_canonical_match(best["root"].strip().lower(), 0.8, parts)
        return result

    # Step 5: Try stripping suffixes
    suf_str, suf_cat, suf_meaning, dict_entry = try_strip_suffixes(working, dictionary)
    if suf_str and dict_entry:
        result["suffix"] = suf_str
        result["suffix_meaning"] = f"{suf_meaning} ({suf_cat})"
        parts = [f"suffix: -{suf_str} = {suf_meaning}", f"✓ root candidate: '{dict_entry['headword']}'"]
        set_canonical_match(dict_entry["headword"].strip().lower(), 0.75, parts)
        return result

    # Step 6: Prefix + suffix combinations (most complex forms)
    for prefix_str, cat, meaning, sub_type in PREFIXES:
        if not working.startswith(prefix_str):
            continue
        if len(working) <= len(prefix_str) + 2:
            continue
        
        after_prefix = working[len(prefix_str):]
        possible_middles = reverse_substitute(after_prefix, sub_type, SUBSTITUTION_MAP)
        
        for middle in possible_middles:
            for suffix_str, suf_cat, suf_meaning in SUFFIXES:
                if middle.endswith(suffix_str) and len(middle) > len(suffix_str) + 1:
                    core = middle[:-len(suffix_str)]
                    if core in dictionary:
                        result["prefix"] = prefix_str
                        result["prefix_meaning"] = f"{meaning} ({cat})"
                        result["suffix"] = suffix_str
                        result["suffix_meaning"] = f"{suf_meaning} ({suf_cat})"
                        
                        parts = [
                            f"prefix: {prefix_str} = {meaning}",
                            f"suffix: -{suffix_str} = {suf_meaning}",
                            f"✓ root candidate: '{core}'"
                        ]
                        set_canonical_match(core, 0.7, parts)
                        return result

    # Fallback Step 7: Word was checked as a subentry but morphological cracking
    # couldn't decompose it cleanly. Let's resolve the root using the "parent" tag.
    if working in dictionary and dictionary[working].get("is_subentry", False):
        parent = dictionary[working].get("parent")
        if parent in dictionary:
            set_canonical_match(working, 0.6, [f"(morphological parse failed; resolved via lookup of parent root)"])
            return result

    return result


# ═══════════════════════════════════════════════════════════════
# 7. DEMO / TESTING
# ═══════════════════════════════════════════════════════════════

def demo():
    """Run the analyzer on example words and show detailed output."""
    print("[*] Loading dictionary...")
    dictionary = load_dictionary()
    print(f"[*] Loaded {len(dictionary)} words\n")

    test_words = [
        # Actor focus (transitive)
        "mamanau",       # mo- + panau → mamanau "goes"
        "mongovit",      # mong- + ovit → mongovit "brings"
        "mangagama",     # manga- + gama → mangagama "works"
        "mongoduat",     # mongo- + duat → mongoduat "asks"
        "monulung",      # mo- + tulung → monulung "helps"
        "mangaramit",    # manga- + ramit → mangaramit "holds"
        
        # Perfect / past
        "nokolohing",    # noko- + lohing → nokolohing (accidentally entered)
        "minangagama",   # min- + manga- + gama → minangagama "made (past)"
        "minongovit",    # minong- + ovit → minongovit "brought (past)"
        
        # Infixed forms
        "rumikot",       # -um- + rikot → rumikot "comes"
        "rinumikot",     # -inum- + rikot → rinumikot "came (past)"
        "sinumambayang", # -in- + sumambayang → sinumambayang "prayed"
        
        # Causative
        "pemot",         # po- + imot → pemot "shows"
        "pamanau",       # pa- + panau → pamanau "makes go"
        
        # With enclitics
        "pinongimotku",  # pinong- + imot + -ku "my being seen"
        
        # Reduplicated
        "mamamanau",     # redup. of mamanau "they all go"
        
        # Suffixed forms
        "kiroon",        # kiro + -on "calculation"
        "koposizan",     # ko- + posi + -an "life"
        "kogunaan",      # ko- + guna + -an "usefulness"
        
        # Plural
        "ongovalai",     # ongo- + valai "houses"
        "onganak",       # anga- + anak "children"
        "ongulun",       # ongo- + ulun "people"
        
        # From original test set
        "mongimot",      # mong- + imot "sees"
        "nokolohing",    # noko- + lohing (already above)
        "monginsan",     # mong- + insan
        "monguasa",      # mong- + uasa
        "monginggirit",  # mong- + inggirit
        "kavasa",        # ka- + vasa
    ]

    print(f"{'Input':<25} {'Root':<18} {'Prefix':<20} {'Infix':<10} {'Suffix':<10} {'Enclitic':<10} {'Conf'}")
    print("=" * 110)
    
    for word in test_words:
        r = analyze(word, dictionary)
        
        p = r["prefix"] or ""
        i = r["infix"] or ""
        s = r["suffix"] or ""
        e = r["enclitic"] or ""
        root = str(r["root"] or "?")
        conf = f"{r['confidence']:.1f}" if r["matched"] else "0.0"
        marker = "✓" if r["matched"] else "✗"
        
        print(f"{marker} {word:<23} {root:<18} {p:<20} {i:<10} {s:<10} {e:<10} {conf}")
    
    print(f"\n--- Detailed breakdown: 'nokolohing' ---")
    r = analyze("nokolohing", dictionary)
    for step in r["breakdown"]:
        print(f"  → {step}")
    if r["matched"]:
        print(f"  Root: {r['root']} = \"{r['root_gloss']}\"")
    
    print(f"\n--- Detailed breakdown: 'pinongimotku' ---")
    r = analyze("pinongimotku", dictionary)
    for step in r["breakdown"]:
        print(f"  → {step}")
    if r["matched"]:
        print(f"  Root: {r['root']} = \"{r['root_gloss']}\"")


if __name__ == "__main__":
    demo()
