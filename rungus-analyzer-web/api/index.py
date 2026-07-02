"""
Rungus Analyzer — Web API
Flask endpoint for Vercel deployment.
"""
import json
import re
import sys
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ── Load dictionary ──
DICT_PATH = Path(__file__).parent.parent / "dictionary.json"

with open(DICT_PATH, "r", encoding="utf-8") as f:
    DICTIONARY = json.load(f)


# ── Phonological rules ──
SUBSTITUTION_MAP = {
    'm': ['m', 'p', 'v', 'b'],
    'n': ['n', 't', 's'],
    'ng': ['ng', 'k'],
}

PREFIXES = [
    ("miri", "intransitive", "aimless/wandering action", "add"),
    ("mi", "intransitive", "reciprocal/dual action", "none"),
    ("mu", "intransitive", "state of being (occupation)", "none"),
    ("moki", "intransitive", "desirous/wanting to", "add"),
    ("mong", "transitive", "actor focus (vowel-init stem)", "sub"),
    ("moko", "transitive", "actor focus perfect (vowel-init)", "sub"),
    ("mongo", "transitive", "actor focus (voiced C stem)", "none"),
    ("minong", "transitive", "actor focus PAST (vowel-init)", "sub"),
    ("mino", "transitive", "actor focus PAST (voiced C)", "none"),
    ("nokopong", "transitive", "actor focus PERFECT (vowel-init)", "sub"),
    ("noko", "perfect", "accidental perfective", "sub"),
    ("nakapa", "perfect", "perfect transitive", "sub"),
    ("nokopo", "perfect", "perfect transitive (voiced C)", "none"),
    ("po", "causative", "causative action", "sub"),
    ("pa", "causative", "causative action (a-stem)", "sub"),
    ("ponga", "causative", "causative imperative", "sub"),
    ("pongi", "causative", "causative imperative (i-stem)", "sub"),
    ("popi", "causative", "reciprocal causative", "none"),
    ("ko", "realisation", "realisation / potentiality", "sub"),
    ("ka", "realisation", "realisation / potentiality (a-stem)", "sub"),
    ("kapa", "realisation", "completed action (a-stem)", "sub"),
    ("kopo", "realisation", "completed action (o-stem)", "none"),
    ("kinopo", "causative-past", "causative past (voiced C)", "none"),
    ("pinong", "causative-past", "causative past (vowel-init)", "sub"),
    ("onga", "plural", "plural marker (a-stem)", "none"),
    ("ta", "aspect", "state of intensive/completed action", "none"),
    ("to", "aspect", "state of intensive (o-variant)", "none"),
    ("ta", "intensifier", "intensifier (extremely)", "none"),
    ("to", "intensifier", "intensifier (extremely)", "none"),
    ("mang", "transitive", "actor focus (a-stem)", "sub"),
    ("min", "perfect", "actor focus past (m-stems)", "sub"),
    ("no", "perfect", "patient focus perfect", "none"),
]

SUFFIXES = [
    ("on", "verbal", "patient focus / gerundive"),
    ("an", "verbal", "reference focus / locative"),
    ("o", "verbal", "imperative patient focus"),
    ("ai", "verbal", "imperative reference focus"),
    ("onon", "nominal", "nomina actionis futurae"),
    ("anon", "nominal", "nomina actionis futurae"),
    ("inai", "nominal", "nomina actionis"),
]

INFIXES = [
    ("-in-", "aspect", "past / perfective marker"),
    ("-um-", "aspect", "intransitive process"),
    ("-inum-", "aspect", "past of intransitive process"),
]

ENCLITICS = [
    ("-ku", "pronominal", "my (1sg)"),
    ("-nu", "pronominal", "your (2sg)"),
    ("-no", "pronominal", "his/her (3sg)"),
    ("-mo", "pronominal", "his/her (3sg)"),
    ("-dau", "pronominal", "his/her own (reflexive)"),
    ("-ko", "pronominal", "you (2sg)"),
    ("-kou", "pronominal", "you (2pl)"),
    ("-po", "aspect", "still / yet / more"),
    ("-no", "aspect", "already"),
    ("-nopo", "aspect", "always / continuous"),
    ("-zou", "pronominal", "we (excl)"),
]

# Sort by length descending
PREFIXES.sort(key=lambda x: len(x[0]), reverse=True)
SUFFIXES.sort(key=lambda x: len(x[0]), reverse=True)
ENCLITICS.sort(key=lambda x: len(x[0]), reverse=True)


def strip_enclitic(word):
    for enclitic, category, meaning in ENCLITICS:
        e = enclitic.lstrip('-')
        if word.endswith(e) and len(word) > len(e) + 1:
            core = word[:-len(e)]
            return e, meaning, core
    return None, None, word


def strip_infix(word):
    for infix, category, meaning in INFIXES:
        bare = infix.strip("-")
        pattern = re.compile(r"^([^aeiouáéíóú]+)" + re.escape(bare) + r"(.*)", re.IGNORECASE)
        m = pattern.match(word)
        if m:
            root = m.group(1) + m.group(2)
            return bare, meaning, root
    return None, None, word


def decontract_vowel(prefix, remainder):
    if not prefix or not remainder:
        return [remainder]
    prefix_last = prefix[-1]
    if prefix_last not in 'aeiou':
        return [remainder]
    candidates = [remainder]
    first_char = remainder[0] if remainder else ''
    if first_char and first_char not in 'aeiou':
        if prefix_last == 'o':
            for v in ['u', 'i', 'o', 'a', 'e']:
                candidates.append(v + remainder)
        elif prefix_last == 'a':
            candidates.append('a' + remainder)
        elif prefix_last == 'i':
            candidates.append('i' + remainder)
        elif prefix_last == 'u':
            candidates.append('u' + remainder)
        elif prefix_last == 'e':
            candidates.append('e' + remainder)
    return candidates


VIRTUAL_ROOTS = {
    'ruhang': 'koruhang',
}


def resolve_to_parent(entry_name, dictionary):
    seen = set()
    current = entry_name.strip().lower()
    
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
    if current in dictionary:
        return dictionary[current]["headword"], dictionary[current]["gloss"]
    return entry_name, None


def possible_roots_for(word):
    if not word:
        return []
    first = word[0]
    candidates = SUBSTITUTION_MAP.get(first, [first])
    return [c + word[1:] for c in candidates]


def reverse_substitute(remainder, prefix_type):
    if not remainder:
        return []
    if prefix_type == 'sub':
        return possible_roots_for(remainder)
    return [remainder]


# ── Main analysis ──
def analyze_word(word):
    result = {
        "input": word,
        "matched": False,
        "confidence": 0,
        "root": None,
        "root_gloss": None,
        "segments": [],
    }

    word_lower = word.strip().lower()
    working = word_lower

    # Helper function to assign matches and resolve parent coordinates
    def set_canonical_match(root_key, confidence_score, segment_items):
        canonical_hw, canonical_gloss = resolve_to_parent(root_key, DICTIONARY)
        result["root"] = canonical_hw
        result["root_gloss"] = canonical_gloss
        result["matched"] = True
        result["confidence"] = confidence_score
        
        # Add segment items
        for seg in segment_items:
            result["segments"].append(seg)
        
        # If successfully resolved to parent, append virtual segment description
        if canonical_hw != DICTIONARY.get(root_key, {}).get("headword", root_key):
            # Try to show what parent-root it resolved to
            result["segments"].append({
                "type": "root",
                "text": canonical_hw,
                "meaning": f"(Parent root resolved from sub-entry '{root_key}')",
            })
        else:
            # Simple direct root
            result["segments"].append({
                "type": "root",
                "text": canonical_hw,
                "meaning": canonical_gloss,
            })

    # Step 1: Enclitics
    enc_str, enc_meaning, working = strip_enclitic(working)
    if enc_str:
        result["segments"].append({
            "type": "enclitic",
            "text": f"-{enc_str}",
            "meaning": enc_meaning,
        })

    # Step 2: Direct dictionary lookup (ignore if subentry directly)
    if working in DICTIONARY and not DICTIONARY[working].get("is_subentry", False):
        set_canonical_match(working, 1.0, [])
        return result

    # Step 3: Infixes
    infix_str, infix_meaning, after_infix = strip_infix(working)
    if infix_str:
        lookup_infix = after_infix
        if after_infix in VIRTUAL_ROOTS:
            lookup_infix = VIRTUAL_ROOTS[after_infix]
        if lookup_infix in DICTIONARY:
            set_canonical_match(after_infix, 0.85, [{
                "type": "infix",
                "text": f"-{infix_str}-",
                "meaning": infix_meaning,
            }])
            return result

    # Step 4: Prefixes
    for p_str, cat, meaning, sub_type in PREFIXES:
        if not working.startswith(p_str):
            continue
        if len(working) <= len(p_str) + 1:
            continue
        remainder = working[len(p_str):]
        decon = decontract_vowel(p_str, remainder)
        candidates = []
        for dc in decon:
            candidates.extend(reverse_substitute(dc, sub_type))
        candidates.append(remainder)
        for root_candidate in list(set(candidates)):
            lookup_root = root_candidate
            if root_candidate in VIRTUAL_ROOTS:
                lookup_root = VIRTUAL_ROOTS[root_candidate]
            if lookup_root in DICTIONARY:
                set_canonical_match(root_candidate, 0.8, [{
                    "type": "prefix",
                    "text": p_str,
                    "meaning": f"{meaning} ({cat})",
                }])
                return result
            # Try infix within prefix-stripped result
            infix_c, infix_m, after_sub = strip_infix(root_candidate)
            lookup_sub_root = after_sub
            if after_sub in VIRTUAL_ROOTS:
                lookup_sub_root = VIRTUAL_ROOTS[after_sub]
            if infix_c and lookup_sub_root in DICTIONARY:
                set_canonical_match(after_sub, 0.8, [
                    {
                        "type": "prefix",
                        "text": p_str,
                        "meaning": f"{meaning} ({cat})",
                    },
                    {
                        "type": "infix",
                        "text": f"-{infix_c}-",
                        "meaning": infix_m,
                    }
                ])
                return result

    # Step 5: Suffixes
    for s_str, cat, meaning in SUFFIXES:
        if working.endswith(s_str) and len(working) > len(s_str) + 1:
            core = working[:-len(s_str)]
            lookup_core = core
            if core in VIRTUAL_ROOTS:
                lookup_core = VIRTUAL_ROOTS[core]
            if lookup_core in DICTIONARY:
                set_canonical_match(core, 0.75, [{
                    "type": "suffix",
                    "text": f"-{s_str}",
                    "meaning": f"{meaning} ({cat})",
                }])
                return result

    # Step 6: Prefix + suffix combinations
    for p_str, cat, meaning, sub_type in PREFIXES:
        if not working.startswith(p_str):
            continue
        if len(working) <= len(p_str) + 2:
            continue
        after_p = working[len(p_str):]
        for mid in list(set(decontract_vowel(p_str, after_p) + reverse_substitute(after_p, sub_type))):
            for s_str, s_cat, s_meaning in SUFFIXES:
                if mid.endswith(s_str) and len(mid) > len(s_str) + 1:
                    core = mid[:-len(s_str)]
                    lookup_core = core
                    if core in VIRTUAL_ROOTS:
                        lookup_core = VIRTUAL_ROOTS[core]
                    if lookup_core in DICTIONARY:
                        set_canonical_match(core, 0.7, [
                            {
                                "type": "prefix",
                                "text": p_str,
                                "meaning": f"{meaning} ({cat})",
                            },
                            {
                                "type": "suffix",
                                "text": f"-{s_str}",
                                "meaning": f"{s_meaning} ({s_cat})",
                            }
                        ])
                        return result

    # Fallback Step 7: Sub-entry fallback if morphological cracking failed
    if working in DICTIONARY and DICTIONARY[working].get("is_subentry", False):
        set_canonical_match(working, 0.6, [])
        return result

    return result


# ── API routes ──
@app.route("/", methods=["GET"])
def root():
    # Serve the frontend HTML
    html_path = Path(__file__).parent.parent / "index.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    return jsonify({
        "name": "Rungus Morphological Analyzer API",
        "version": "2.0",
        "endpoints": {
            "/api/analyze": "POST - Analyze a Rungus word. Body: {\"word\": \"nokolohing\"}"
        }
    })

@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    if not data or "word" not in data:
        return jsonify({"error": "Missing 'word' field"}), 400
    word = data["word"].strip()
    if not word:
        return jsonify({"error": "Empty word"}), 400
    
    result = analyze_word(word)
    
    # Also suggest similar words if not found
    if not result["matched"]:
        suggestions = []
        for dict_word in DICTIONARY:
            if word[:3] == dict_word[:3] and len(word) > 3:
                suggestions.append(dict_word)
            if len(suggestions) >= 5:
                break
        result["suggestions"] = suggestions
    
    return jsonify(result)
