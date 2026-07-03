"""
rungus_analyzer_lib.py — Rungus Morphological Analyzer Core Library v3.0
=========================================================================
Shared library imported by both rungus_analyzer.py (CLI) and
rungus-analyzer-web/api/index.py (Flask web API).

Based on:
  - Forschner, T.A. (1994). "Outline of a Momogun Grammar (Rungus Dialect)"
  - Swarthmore LING073 Spring 2025 Rungus transducer documentation
  - SIL Webonary Rungus dictionary (12,000+ entries, scraped 2026)
  - Corpus analysis of 534,775 tokens across 9 book files

Coverage: ~80% of corpus word tokens (baseline before v3 improvements).
Target:   ~89-92% after v3.

Author: Aifven Nelson (Rungus/Momogun descent, Kudat, Sabah)
"""

import json
import re
from pathlib import Path

# Default dictionary path — can be overridden by load_dictionary(path=...)
_DEFAULT_DATA_PATH = Path(__file__).parent / "mainDataset_merged.json"


# ═══════════════════════════════════════════════════════════════════════
# 1. PHONOLOGICAL RULES  (Forschner §1.2–1.4)
# ═══════════════════════════════════════════════════════════════════════

# §1.43 Consonant substitution: when certain prefixes attach, the
# stem-initial consonant is replaced by a nasal at the same place of
# articulation.
# Format: surface_initial → [possible_root_initials]
SUBSTITUTION_MAP = {
    'm':  ['m', 'p', 'v', 'b'],   # m could be original m, or p→m, v→m, b→m
    'n':  ['n', 't', 's'],         # n could be original n, or t→n, s→n
    'ng': ['ng', 'k'],             # ng could be original ng, or k→ng
}

# Nasal addition: voiced consonants (other than /b/) get a nasal prefix
# added in front (for mongo-/manga- type environments) — no substitution.
NASAL_ADDITION = {'d', 'g', 'h', 'r', 'l', 'z', 'j', 'y', 'w'}

# §1.21–1.22 Vowel contraction rules (used in REVERSE for analysis).
# When a vowel-ending prefix merges with a vowel-initial stem, the two
# vowels contract.  Analysis must try to undo these contractions.
VOWEL_CONTRACTIONS = {
    'e': [('a', 'i'), ('o', 'i')],   # e ← a+i or o+i
    'u': [('o', 'u')],               # u ← o+u
    'a': [('a', 'a')],               # a ← a+a
    'o': [('o', 'o')],               # o ← o+o
}


# ═══════════════════════════════════════════════════════════════════════
# 2. AFFIX INVENTORY  (Forschner §2.2–2.4, §4.1; Swarthmore LING073)
# ═══════════════════════════════════════════════════════════════════════
#
# Prefix tuple format:
#   (prefix_string, category, meaning, substitution_type)
#
# substitution_type:
#   'sub'   — stem-initial C is replaced by the nasal at same POA
#             (p/b/v→m, t/s→n, k→ng).  Used by mo-, ma-, mong-, etc.
#   'add'   — a nasal is prepended to the stem (no substitution).
#             Used by miri-, moki-, etc.
#   'none'  — no phonological change to the stem.
#   'vowel' — prefix absorbs stem-initial vowel via contraction.
#             (Handled separately via decontract_vowel().)

PREFIXES = [
    # ── §2.21 Intransitive prefixes ──────────────────────────────────

    # m- before vowel-initial stems: imot → mimot (Swarthmore §1)
    # This is the bare m- prefix, distinct from mi- (reciprocal).
    ("m",              "intransitive",   "intransitive process (vowel-initial stem)",    "none"),

    ("miri",           "intransitive",   "aimless / wandering action",                   "add"),
    ("mirim",          "intransitive",   "intransitive (mirim- variant of miri-)",        "add"),
    ("mi",             "intransitive",   "reciprocal / dual action",                     "none"),
    ("mu",             "intransitive",   "state of being (occupation / habitual)",       "none"),
    ("moki",           "intransitive",   "desirous / wanting to",                        "add"),
    ("mokipopookot",   "intransitive",   "very desirous / improbable wish (long form)",  "add"),
    ("mokipopoko",     "intransitive",   "improbable wish",                              "add"),
    ("mog",            "intransitive",   "intransitive actor focus (mog- variant)",      "none"),

    # ── §2.221 Transitive actor-focus prefixes ────────────────────────

    # mo-/ma- + substitution: used for voiceless-C stems and /b/ stems
    # (Swarthmore §2: panau→mamanau, tapit→napit, kama→ngama)
    ("mo",             "transitive",     "actor focus (voiceless C / b stem)",           "sub"),
    ("ma",             "transitive",     "actor focus (a-vowel voiceless C stem)",       "sub"),

    # mong-/mang- + substitution: vowel-initial stems
    # (Swarthmore §2: imot→mongimot, ada→mangada)
    ("mong",           "transitive",     "actor focus (vowel-initial stem)",             "sub"),
    ("mang",           "transitive",     "actor focus (a-stem vowel-initial)",           "sub"),

    # mongo-/manga-: voiced-C stems (no substitution, nasal added)
    # (Swarthmore §2: duat→mongoduat, gama→mangagama)
    ("mongo",          "transitive",     "actor focus (voiced C stem)",                  "none"),
    ("manga",          "transitive",     "actor focus (a-stem voiced C)",                "none"),

    ("moko",           "transitive",     "actor focus perfective (vowel-initial)",       "sub"),

    # Past actor-focus
    ("minong",         "transitive",     "actor focus PAST (vowel-initial)",             "sub"),
    ("mino",           "transitive",     "actor focus PAST (voiced C stem)",             "none"),
    ("mino",           "transitive",     "actor focus PAST (voiceless C / b stem)",      "sub"),

    # Perfect actor-focus
    ("nokopong",       "transitive",     "actor focus PERFECT (vowel-initial)",          "sub"),

    # ── §2.226–2.227 Perfect / accidental prefixes ────────────────────
    ("noko",           "perfect",        "accidental perfective",                        "sub"),
    ("naka",           "perfect",        "accidental perfective (a-stem)",               "sub"),
    ("nakapa",         "perfect",        "perfect transitive",                           "sub"),
    ("nokopo",         "perfect",        "perfect transitive (voiced C stem)",           "none"),
    ("min",            "perfect",        "actor focus past (m-/n- stems)",               "sub"),
    ("no",             "perfect",        "patient focus perfect",                        "none"),
    ("na",             "perfect",        "patient focus perfect (a-stem)",               "none"),

    # ── §2.223 Causative prefixes ─────────────────────────────────────
    ("po",             "causative",      "causative action",                             "sub"),
    ("pa",             "causative",      "causative action (a-stem)",                    "sub"),
    ("ponga",          "causative",      "causative imperative",                         "sub"),
    ("pongi",          "causative",      "causative imperative (i-stem)",                "sub"),
    ("popi",           "causative",      "reciprocal causative",                         "none"),

    # ── §2.225 Preterit causative prefixes ───────────────────────────
    ("kinopo",         "causative-past", "causative past (voiced C stem)",               "none"),
    ("pinong",         "causative-past", "causative past (vowel-initial)",               "sub"),
    ("kino",           "realisation-past", "realisation past",                           "sub"),
    ("pino",           "causative-past", "causative past",                               "sub"),
    ("in",             "perfective",     "past / perfective (vowel-initial)",            "none"),
    ("um",             "intransitive",   "intransitive process (vowel-initial)",         "none"),
    ("inum",           "intransitive-past","past intransitive (vowel-initial)",           "none"),

    # ── §2.224 Realisation / potential prefixes ───────────────────────
    ("kopio",          "intensive",      "extremely / truly",                            "none"),
    ("ko",             "realisation",    "realisation / potentiality",                   "sub"),
    ("ka",             "realisation",    "realisation / potentiality (a-stem)",          "sub"),
    ("kapa",           "realisation",    "completed action (a-stem)",                    "sub"),
    ("kopo",           "realisation",    "completed action (o-stem)",                    "sub"),
    ("ki",             "have",           "have / possess / use",                         "none"),

    # ── §4.1 Intended / desirous action (verbal flection table) ──────
    ("ti",             "intended",       "intended / about-to-happen action",            "none"),
    ("o",              "stative",        "stative / adjective prefix",                   "none"),
    ("a",              "stative",        "stative / adjective prefix (a-variant)",       "none"),

    # ── §2.461 Plural prefixes ────────────────────────────────────────
    ("ongo",           "plural",         "plural marker",                                "none"),
    ("anga",           "plural",         "plural marker (a-stem)",                       "none"),

    # ── Swarthmore §3 Collective noun prefixes ────────────────────────
    ("song",           "collective",     "collective noun / singulative",                "none"),
    ("sang",           "collective",     "collective noun / singulative (a-variant)",    "none"),

    # ── §4.1 Imperative prefixes ──────────────────────────────────────
    ("pong",           "imperative",     "imperative actor focus (vowel-initial)",       "sub"),
    ("pi",             "imperative",     "imperative (i-variant)",                       "sub"),
    ("pog",            "imperative",     "imperative intransitive",                      "none"),

    # ── §1.31 Intensifier prefixes ────────────────────────────────────
    ("ta",             "intensifier",    "intensifier (extremely)",                      "none"),
    ("to",             "intensifier",    "intensifier (extremely, o-variant)",           "none"),
]

# Sort longest-first so longer prefixes are tried before shorter ones
# (prevents 'mong-' from being short-circuited by 'mo-')
PREFIXES = sorted(PREFIXES, key=lambda x: len(x[0]), reverse=True)


# Suffix tuple format: (suffix_string, category, meaning)
SUFFIXES = [
    # ── §2.34 Verbal suffixes ─────────────────────────────────────────
    ("onon",    "nominal",  "nomina actionis futurae (future action noun)"),
    ("anon",    "nominal",  "nomina actionis futurae (a-variant)"),
    ("inai",    "nominal",  "nomina actionis (action noun)"),
    ("on",      "verbal",   "patient focus / gerundive"),
    ("an",      "verbal",   "reference focus / locative"),
    ("o",       "verbal",   "imperative patient focus"),
    ("ai",      "verbal",   "imperative reference focus"),
]

# Sort longest-first to prefer -onon over -on, -anon over -an, etc.
SUFFIXES = sorted(SUFFIXES, key=lambda x: len(x[0]), reverse=True)


# Infix tuple format: (infix_with_dashes, category, meaning)
INFIXES = [
    ("-inum-",  "aspect",  "past of intransitive process"),
    ("-in-",    "aspect",  "past / perfective marker"),
    ("-um-",    "aspect",  "intransitive process"),
    ("-ong-",   "aspect",  "plural in verb (rare, Swarthmore §6)"),
]

# Sorted longest-first
INFIXES = sorted(INFIXES, key=lambda x: len(x[0]), reverse=True)


# Enclitic tuple format: (enclitic_with_dash, category, meaning)
ENCLITICS = [
    ("-nopo",   "aspect",      "always / continuous"),
    ("-dati",   "pronominal",  "their (3pl)"),
    ("-dino",   "pronominal",  "their then (3pl past)"),
    ("-diti",   "pronominal",  "their here (3pl proximal)"),
    ("-kou",    "pronominal",  "you (2pl)"),
    ("-dau",    "pronominal",  "his/her own (reflexive)"),
    ("-zou",    "pronominal",  "we (exclusive 1pl)"),
    ("-ku",     "pronominal",  "my / I (1sg)"),
    ("-nu",     "pronominal",  "your / you (2sg)"),
    ("-no",     "pronominal",  "his / her (3sg)"),
    ("-mo",     "pronominal",  "his / her (3sg variant)"),
    ("-ko",     "pronominal",  "you (2sg)"),
    ("-po",     "aspect",      "still / yet / more"),
]

# Sorted longest-first
ENCLITICS = sorted(ENCLITICS, key=lambda x: len(x[0]), reverse=True)


# ═══════════════════════════════════════════════════════════════════════
# 3. LEXICAL PATCH MAPS  (for Webonary omissions)
# ═══════════════════════════════════════════════════════════════════════

# VIRTUAL_ROOTS: true linguistic roots that exist in the language but
# are absent from the Webonary dictionary.  Maps root → closest dict entry.
# Use these when the analyzer strips a prefix and lands on a word that
# isn't in the dictionary but IS semantically the root.
VIRTUAL_ROOTS = {
    'ruhang':   'koruhang',    # ruhang (companion) is root of koruhang
    'buatano':  'kobuatano',   # buatano → kobuatano (creation)
    'raatan':   'karaatan',    # raatan → karaatan (evil/sin)
    'ginavon':  'ginavo',      # suffixed form → ginavo (heart)
    'duduk':    'tudukan',     # duduk (sit) → tudukan (seat, place)
    'gulianan': 'nogulianan',  # gulianan (revive/awake) → nogulianan
    'guli':     'nokoguli',    # guli (return/repeat) → nokoguli
    'gulian':   'nogulianan',  # gulian (revive) → nogulianan
    'rungaz':   'rungoi',      # rungaz (destroy/ruin) → rungoi
}

# STANDALONE_WORDS: high-frequency Rungus words completely absent from
# the Webonary dictionary.  Rather than patching through VIRTUAL_ROOTS
# (which requires a dict entry to point to), these words are defined here
# directly.  Corpus source: top-60 unknown words from 534K-token analysis.
#
# Format: { word: (gloss, pos) }
STANDALONE_WORDS = {
    # ── Core pronouns / demonstratives / deixis ───────────────────────
    'ulun':       ('person / people',                         'noun'),
    'oku':        ('I / me (1sg)',                            'pronoun'),
    'dikou':      ('you (2pl)',                               'pronoun'),
    'adau':       ('his / her (3sg possessive)',              'pronoun'),

    # ── High-frequency conjunctions / particles ───────────────────────
    'ioti':       ('then / so / therefore',                   'conjunction'),
    'iosido':     ('also / likewise / too',                   'conjunction'),
    'iadko':      ('but / however',                           'conjunction'),
    'iadino':     ('then / after that',                       'conjunction'),
    'agas':       ('fine / finely divided (reduplicates: agas-agas)',  'adjective'),
    'azak':       ('different / other / separate',            'adjective'),
    'kagi':       ('if / when / whenever',                    'particle'),
    'ontok':      ('for / so that / in order to',             'particle'),
    'elaan':      ('already / now',                           'particle'),
    'ioku':       ('there / that (distal)',                   'demonstrative'),

    # ── Locatives / place words ───────────────────────────────────────
    'laid':       ('there / that place',                      'locative'),
    'sino':       ('where / which place',                     'interrogative'),
    'inot':       ('here / this place',                       'locative'),
    'penlaid':    ('there (distal, specific)',                 'locative'),

    # ── Common nouns missing from Webonary ────────────────────────────
    'ginavo':     ('heart / feeling / mind / inner self',     'noun'),
    'araat':      ('bad / evil / wrong',                      'adjective'),
    'duvo':       ('two',                                     'numeral'),
    'tolu':       ('three',                                   'numeral'),
    'toun':       ('year',                                    'noun'),
    'kurudong':   ('hat / head covering',                     'noun'),
    'koduvo':     ('pair / both / the two',                   'noun'),
    'sumaap':     ('to ask for forgiveness / to greet',       'verb'),
    'oruhai':     ('praise / worship',                        'noun'),
    'fasal':      ('chapter / section (loanword: Arabic→Malay→Rungus)', 'noun'),
    'kavi':       ('all / complete / finished',               'adjective'),
    'momogun':    ('Momogun / Rungus people / indigenous peoples of Kudat', 'noun'),

    # ── Derived forms whose roots are missing ────────────────────────
    'kobuatano':  ('creation / what was made',                'noun'),
    'karaatan':   ('badness / evil / sin (abstract noun)',    'noun'),
    'monuduk':    ('to sit down (actor focus)',               'verb'),
    'mamakai':    ('to use / to wear (actor focus)',          'verb'),
    'makai':      ('to use / to wear (actor focus base)',     'verb'),
    'kiguna':     ('benefit / usefulness',                    'noun'),
    'piniizaan':  ('test / trial / temptation',               'noun'),
    'tudukan':    ('seat / dwelling place',                   'noun'),
    'injil':      ('gospel / good news (loanword: Arabic→Malay→Rungus)', 'noun'),
    'iseso':      ('one / single',                            'numeral'),
    'ikou':       ('you (2pl subject form)',                  'pronoun'),
    'tasantanid': ('various / different types',               'adjective'),
    'za':         ('our / we (exclusive possessive)',         'pronoun'),
    'iokoi':      ('we (exclusive)',                          'pronoun'),
    'podsu':      ('to bathe / wash (body)',                  'verb'),
}


# PROPER_NAMES: biblical, geographic, and personal names found in the
# corpus (primarily book_3–book_9, which are biblical translations).
# Words in this set are flagged as proper names rather than "failed".
PROPER_NAMES = {
    # New Testament figures
    'yesus', 'paulus', 'petrus', 'lukas', 'markus', 'matius', 'yahya',
    'barnabas', 'silas', 'timotius', 'titus', 'yakobus', 'yohanes',
    # Old Testament figures
    'musa', 'daud', 'salomo', 'elia', 'yeremia', 'yesaya', 'daniel',
    'nehemia', 'ezra', 'ester', 'rut', 'amos', 'hosea', 'yunus',
    'habakuk', 'harun', 'ishak', 'yakub', 'yusuf', 'abraham', 'ibrahim',
    'samuel', 'mariam', 'sulaiman', 'adam', 'yosua', 'zakaria', 'yoel',
    'yehezkiel', 'herodis', 'saul', 'abram', 'simun',
    # Places
    'israel', 'yerusalim', 'galilea', 'betlehem', 'nazaret', 'yudea',
    'babilon', 'mesir', 'rom', 'korintus', 'efesus', 'galatia',
    'filipi', 'tesalonika', 'kolosi', 'ibrani', 'yahuda', 'yunani',
    'babil', 'masir', 'samaria', 'sabah', 'yahwe', 'sion',
    # Titles / groups (used as proper nouns in context)
    'kristus', 'nabi', 'yahudi', 'zabur', 'injil', 'parisi', 'taurat', 'pilatus',
    # Book titles / abbreviations / organizations
    'amos', 'rom', 'lukas', 'markus', 'luk', 'mat', 'mikha', 'pcs',
    'gal', 'kor', 'paska', 'tim', 'imamat',
    # Proper names in folk tales
    'sarip', 'bakaka', 'usan',
}


# LOANWORDS: Malay / Indonesian / Arabic words that appear in the corpus
# (particularly book_6, which appears to be in mixed Malay–Rungus).
# These are flagged as loanwords rather than "failed".
LOANWORDS = {
    # Common Malay function words
    'yang', 'dan', 'atau', 'dari', 'oleh', 'dalam', 'dengan', 'untuk',
    'pada', 'akan', 'sudah', 'juga', 'bagi', 'itu', 'ini', 'ada',
    'tetapi', 'bahawa', 'kepada', 'dapat', 'adalah', 'tentang', 'hanya',
    'telah', 'seorang', 'lain', 'sebagai', 'banyak', 'mungkin', 'sesuatu',
    'kerana', 'sebab', 'bukan',
    # Malay content words appearing in corpus
    'orang', 'tidak', 'kami', 'dua', 'dia', 'kita', 'mereka', 'saya',
    'tuhan', 'allah', 'tugas', 'hidup', 'tangan', 'mata', 'hati',
    'kaseh', 'kampong', 'bandar', 'belantara', 'kaisar', 'tampat',
    'rombongan', 'undang', 'hak', 'daerah', 'engat', 'masti', 'teologia',
    'tajuk', 'hari', 'persembaan', 'murid', 'utara', 'sodia', 'kata',
    'gereja', 'sendiri', 'hasil', 'bebas', 'jawab', 'usaha', 'kurang',
    'baik', 'mahu', 'sama', 'lebih', 'lagi', 'lihat', 'selatan', 'alun',
    'kota', 'abad', 'pandita', 'kain', 'parsambaan', 'perlu', 'pesta',
    # Arabic loanwords (via Malay) appearing in religious texts
    'nabi', 'injil', 'zabur', 'fasal', 'iman', 'doa', 'khotbah',
}


# FUNCTION_WORDS: Rungus grammatical particles, pronouns, and discourse
# markers that are genuine Rungus words but so short/grammatical that
# the dictionary doesn't usually list them.
# Words in this set are counted as "known function words" in corpus stats
# (neither matched nor failed — they are correctly excluded).
FUNCTION_WORDS = {
    # Short grammatical particles
    'i', 'di', 'do', 'om', 'dit', 'dot', 'sid', 'ku', 'nu', 'no', 'mo',
    'ko', 'po', 'ka', 'a', 'o', 'nga', 'yo', 'tu', 'ot', 'bo',
    'na', 'da', 'so', 'ro', 'it', 'tgm', 'tm', 'ur', 'sitid',
    'noko', 'ei', 'ma', 'not', 'isot', 'siri', 'pot', 'didino',
    # Demonstratives / locatives (short forms)
    'dino', 'dioti', 'dih', 'iti', 'ino', 'diti', 'nopo', 'kopo',
    'ong', 'song', 'sinod',
    # Discourse particles
    'insan', 'manjadi',
}


# ═══════════════════════════════════════════════════════════════════════
# 4. DICTIONARY LOADING
# ═══════════════════════════════════════════════════════════════════════

def load_dictionary(path=None):
    """Load the merged Webonary dataset into a normalized lookup dict.

    The returned dict maps lowercase headword → entry dict with keys:
      headword   : str  — the canonical headword string
      gloss      : str  — English gloss (joined from all senses)
      is_subentry: bool — True if this word is a subentry of another
      parent     : str  — parent headword (only present if is_subentry)
      subentries : list — list of subentry headword strings

    Also injects STANDALONE_WORDS as first-class entries so they are
    found during direct dictionary lookup.
    """
    data_path = Path(path) if path else _DEFAULT_DATA_PATH

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    lookup = {}

    # Pass 1: load main headwords
    for entry in data:
        hw = entry.get("headword", "").strip().lower()
        if not hw:
            continue
        senses = []
        for s in entry.get("senses", []):
            gloss = s.get("english") or s.get("malay") or ""
            if gloss:
                senses.append(gloss)
        entry_data = {
            "headword":    entry["headword"],
            "gloss":       "; ".join(senses) if senses else "",
            "subentries":  [s.get("headword", "") for s in entry.get("subentries", [])],
            "is_subentry": entry.get("is_subentry", False),
        }
        if "parent" in entry:
            entry_data["parent"] = entry["parent"]
        lookup[hw] = entry_data
        
        # Normalize homonyms by stripping trailing digits (e.g. tumpu1, tumpu2 -> tumpu)
        hw_clean = hw.rstrip("0123456789")
        if hw_clean != hw:
            if hw_clean in lookup:
                if entry_data["gloss"] and lookup[hw_clean]["gloss"]:
                    lookup[hw_clean]["gloss"] += " | " + entry_data["gloss"]
                elif entry_data["gloss"]:
                    lookup[hw_clean]["gloss"] = entry_data["gloss"]
            else:
                lookup[hw_clean] = entry_data.copy()
                lookup[hw_clean]["headword"] = hw_clean.capitalize()

        if "'" in hw:
            lookup[hw.replace("'", "")] = entry_data
        if "'" in hw_clean:
            lookup[hw_clean.replace("'", "")] = lookup.get(hw_clean, entry_data)

    # Pass 2: load subentries (only if not already a headword)
    for entry in data:
        for sub in entry.get("subentries", []):
            shw = sub.get("headword", "").strip().lower()
            if shw:
                entry_data = {
                    "headword":    sub["headword"],
                    "gloss":       f"(sub-entry of {entry['headword']})",
                    "parent":      entry["headword"],
                    "is_subentry": True,
                }
                if shw not in lookup:
                    lookup[shw] = entry_data
                
                # Normalize subentry homonyms (e.g. kosunduvo1 -> kosunduvo)
                shw_clean = shw.rstrip("0123456789")
                if shw_clean != shw:
                    if shw_clean not in lookup:
                        lookup[shw_clean] = entry_data.copy()
                        lookup[shw_clean]["headword"] = shw_clean.capitalize()

                if "'" in shw:
                    shw_clean_glottal = shw.replace("'", "")
                    if shw_clean_glottal not in lookup:
                        lookup[shw_clean_glottal] = entry_data
                if "'" in shw_clean:
                    shw_clean_both = shw_clean.replace("'", "")
                    if shw_clean_both not in lookup:
                        lookup[shw_clean_both] = lookup.get(shw_clean, entry_data)

    # Pass 3: inject STANDALONE_WORDS (they take priority as proper roots)
    for word, (gloss, pos) in STANDALONE_WORDS.items():
        if word not in lookup:
            lookup[word] = {
                "headword":    word,
                "gloss":       gloss,
                "pos":         pos,
                "is_subentry": False,
                "source":      "standalone",
            }

    # Pass 4: inject custom_vocab.json if it exists (allows HITL import)
    custom_path = Path(data_path).parent / "custom_vocab.json"
    if custom_path.exists():
        try:
            with open(custom_path, "r", encoding="utf-8") as f:
                custom_data = json.load(f)
            for word, entry_info in custom_data.items():
                w_lower = word.lower()
                if w_lower not in lookup:
                    lookup[w_lower] = {
                        "headword":    entry_info.get("headword", word),
                        "gloss":       entry_info.get("gloss", ""),
                        "pos":         entry_info.get("pos", "noun"),
                        "is_subentry": False,
                        "source":      "custom",
                    }
        except Exception:
            pass

    # Pass 5: Manual dictionary corrections/patches for Webonary inconsistencies
    if "minakan" in lookup:
        lookup["minakan"]["is_subentry"] = True
        lookup["minakan"]["parent"] = "akan"

    return lookup


# ═══════════════════════════════════════════════════════════════════════
# 5. REVERSE SUBSTITUTION
# ═══════════════════════════════════════════════════════════════════════

def possible_roots_for(word, substitutions=None):
    """Given a word remainder (after prefix stripping), return all possible
    original root forms by reversing the consonant-substitution rule.

    E.g., 'manau' → ['manau', 'panau', 'vanau', 'banau'] because
    'm' could be original m, or p→m, v→m, b→m.
    """
    if substitutions is None:
        substitutions = SUBSTITUTION_MAP
    if not word:
        return []
    # Handle 'ng' digraph at word start
    if word.startswith('ng'):
        candidates = substitutions.get('ng', ['ng'])
        return [c + word[2:] for c in candidates]
    first = word[0]
    candidates = substitutions.get(first, [first])
    return [c + word[1:] for c in candidates]


def reverse_substitute(remainder, prefix_type, substitutions=None):
    """Return a list of possible root forms to try in the dictionary,
    based on the prefix type and consonant-substitution rules."""
    if substitutions is None:
        substitutions = SUBSTITUTION_MAP
    if not remainder:
        return []
    if prefix_type == 'sub':
        return possible_roots_for(remainder, substitutions)
    # 'add' or 'none': no substitution — check remainder as-is
    return [remainder]


# ═══════════════════════════════════════════════════════════════════════
# 6. VOWEL DE-CONTRACTION
# ═══════════════════════════════════════════════════════════════════════

def decontract_vowel(prefix, remainder):
    """Undo vowel contraction at the prefix–stem boundary.

    When a vowel-ending prefix attaches to a vowel-initial stem, the two
    vowels merge (§1.22).  During analysis we must try to restore the
    stem's initial vowel.

    Examples (forward contraction → reverse in analysis):
      ongo- + ulun → ongulun   (o+u=u): strip 'ongo-' → 'lun', try 'ulun'
      po-   + imot → pemot     (o+i=e): strip 'po-'   → 'emot', try 'imot'
      mang- + anak → manganak  (a+a=a): strip 'mang-' → 'anak' (no change)
    """
    if not prefix or not remainder:
        return [remainder]

    prefix_last = prefix[-1]
    if prefix_last not in 'aeiou':
        return [remainder]   # prefix ends in consonant, no contraction

    candidates = [remainder]
    first_char = remainder[0] if remainder else ''

    if first_char and first_char not in 'aeiou':
        # Stem's initial vowel was absorbed into the prefix's terminal vowel.
        # Try all plausible stem-initial vowels in priority order.
        if prefix_last == 'o':
            # o+u=u (most common: ongo+ulun→ongulun)
            # o+i=e (po+imot→pemot handled below via 'e' remainder branch)
            # Try u first (most productive for o-prefix de-contraction)
            for v in ['u', 'i', 'o', 'a', 'e']:
                candidates.append(v + remainder)
        elif prefix_last == 'a':
            # a+a=a (manga+anak→manganak), a+i=e
            for v in ['a', 'i']:
                candidates.append(v + remainder)
        elif prefix_last == 'i':
            candidates.append('i' + remainder)
        elif prefix_last == 'u':
            candidates.append('u' + remainder)
        elif prefix_last == 'e':
            candidates.append('e' + remainder)
    else:
        # Remainder already starts with a vowel.
        # Handle contracted vowel in remainder (e.g., strip po- from pemot → 'emot').
        if first_char == 'e' and prefix_last in ('o', 'a'):
            # o+i=e or a+i=e: stem might start with 'i'
            candidates.append('i' + remainder[1:])
        elif first_char == 'u' and prefix_last == 'o':
            # o+u=u: also try the stem starting with 'o'
            candidates.append('o' + remainder[1:])
        elif first_char == 'a' and prefix_last == 'a':
            # a+a=a: try 'a' again (no-op) or stem with different vowel
            candidates.append('a' + remainder[1:])

    return candidates


# ═══════════════════════════════════════════════════════════════════════
# 7. REDUPLICATION DETECTION  (Forschner §2.51–2.52)
# ═══════════════════════════════════════════════════════════════════════

def detect_reduplication(word):
    """Detect and decompose reduplicated forms.

    Returns (redup_type, base_form) or (None, word) if not reduplicated.

    Three patterns handled:

    1. Hyphenated full reduplication: 'agas-agas' → base='agas'
    2. CV-prefix reduplication (2–4 char repeated prefix):
       'mamamanau' = 'ma' + 'mamanau' → base='mamanau'
       'valaivalai' = 'valai' + 'valai' → base='valai'
    3. Prefix-then-base reduplication (most complex):
       checked as a fallback in the main analyze() loop.
    """
    # Pattern 1: hyphenated reduplication
    if '-' in word:
        parts = word.split('-', 1)
        if len(parts) == 2 and parts[0] == parts[1] and len(parts[0]) >= 2:
            return ('full', parts[0])

    # Pattern 2: CV-prefix reduplication — look for a 2–5 char repeat at start
    for repeat_len in range(5, 1, -1):
        if len(word) > repeat_len * 2:
            candidate_repeat = word[:repeat_len]
            rest = word[repeat_len:]
            if rest.startswith(candidate_repeat):
                # Guard: for 2-character CV syllables, only allow valid prefix syllables
                if repeat_len == 2:
                    allowed_cv = {
                        'ma', 'mo', 'mi', 'pa', 'po', 'pi',
                        'ka', 'ko', 'ki', 'sa', 'so', 'si',
                        'ta', 'to', 'ti', 'mu', 'di'
                    }
                    if candidate_repeat not in allowed_cv:
                        continue
                
                # Guard: for 'ma' and 'mo' prefixes, a double repeat is just the normal
                # prefixed form with consonant substitution (e.g. ma-manau, mo-moros).
                # We require at least a triple repeat (e.g. mamamanau, momomoros) to strip.
                if candidate_repeat in ('ma', 'mo'):
                    if not word.startswith(candidate_repeat * 3):
                        continue
                # e.g., 'mamamanau': repeat='ma', rest='mamanau' ✓
                return ('prefix_redup', rest)
            # Also try: base is itself a reduplication of a shorter form
            # e.g., 'valaivalai': repeat='valai', rest='valai' → already caught by pattern 1

    return (None, word)


# ═══════════════════════════════════════════════════════════════════════
# 8. PARENT RESOLUTION
# ═══════════════════════════════════════════════════════════════════════

def resolve_to_parent(entry_name, dictionary):
    """If the matched entry is a subentry, recursively resolve to the
    canonical grandparent root.  Also passes through VIRTUAL_ROOTS.

    Returns (canonical_headword, canonical_gloss).
    """
    seen = set()
    current = entry_name.strip().lower()

    # Resolve dictionary gaps via VIRTUAL_ROOTS first
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


# ═══════════════════════════════════════════════════════════════════════
# 9. AFFIX-STRIPPING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def strip_enclitic(word):
    """Strip pronominal / aspectual enclitics from the end of a word.

    Returns (enclitic_str, category, meaning, core_word).
    If no enclitic found, returns (None, None, None, word).
    """
    for enclitic, category, meaning in ENCLITICS:
        e = enclitic.lstrip('-')
        if word.endswith(e) and len(word) > len(e) + 2:
            core = word[:-len(e)]
            return e, category, meaning, core
    return None, None, None, word


def strip_infix(word):
    """Strip an infix from a word.

    Per Rungus grammar, infixes are inserted AFTER the first consonant
    cluster of the ROOT (not the whole surface form).  This function
    handles bare roots; when called after prefix-stripping in
    try_strip_prefixes(), it works on the remainder — which is correct.

    Returns (infix_str, category, meaning, root_without_infix).
    If no infix found, returns (None, None, None, word).
    """
    for infix, category, meaning in INFIXES:
        bare = infix.strip("-")
        # Pattern: one or more initial consonants + infix + rest
        pattern = re.compile(
            r"^([^aeiouáéíóú]+)" + re.escape(bare) + r"(.*)",
            re.IGNORECASE
        )
        m = pattern.match(word)
        if m:
            init_c = m.group(1)
            # Prevent 'ong'/'ang' infix collision with 'mong'/'mang'/'song'/'sang' prefixes
            if init_c.lower() == "m" and bare.lower() == "ong" and word.lower().startswith("mong"):
                continue
            if init_c.lower() == "m" and bare.lower() == "ang" and word.lower().startswith("mang"):
                continue
            if init_c.lower() == "s" and bare.lower() == "ong" and word.lower().startswith("song"):
                continue
            if init_c.lower() == "s" and bare.lower() == "ang" and word.lower().startswith("sang"):
                continue
            rest = m.group(2)
            root = init_c + rest
            return bare, category, meaning, root
    return None, None, None, word


def _lookup_root(root_candidate, dictionary):
    """Try to find root_candidate in dictionary, passing through
    VIRTUAL_ROOTS if needed.  Returns (lookup_key, entry) or (None, None).
    """
    key = root_candidate
    if key in VIRTUAL_ROOTS:
        key = VIRTUAL_ROOTS[key]
        
    keys_to_try = [key]
    if key.endswith('v') and len(key) > 2:
        keys_to_try.append(key[:-1])
        
    for k in keys_to_try:
        if k in dictionary:
            return k, dictionary[k]
        # Try proper names and loanwords as fallback roots during parsing
        if k in PROPER_NAMES:
            return k, {"headword": root_candidate, "gloss": "proper name (biblical / geographic)", "is_subentry": False, "proper_name": True}
        if k in LOANWORDS:
            return k, {"headword": root_candidate, "gloss": "loanword (Malay / Arabic)", "is_subentry": False, "loanword": True}
        if k in FUNCTION_WORDS:
            return k, {"headword": root_candidate, "gloss": "grammatical function word / particle", "is_subentry": False}

    # Reversal of vowel harmony (a <-> o)
    # Case 1: Reversing 'o' to 'a' (e.g., gozo -> gazo, tonid -> tanid)
    if 'o' in key:
        alt = key.replace('o', 'a', 1)
        if alt in dictionary:
            return alt, dictionary[alt]
        if key.endswith('o'):
            alt2 = key[:-1].replace('o', 'a') + 'o'
            if alt2 in dictionary:
                return alt2, dictionary[alt2]

    # Case 2: Reversing 'a' to 'o' (e.g., tapat -> topot)
    if 'a' in key:
        alt = key.replace('a', 'o')
        if alt in dictionary:
            return alt, dictionary[alt]
        alt2 = key.replace('a', 'o', 1)
        if alt2 in dictionary:
            return alt2, dictionary[alt2]

    # Case 3: Reversing 'u' to 'o' (e.g., ondus -> ondos, oondus -> oondos)
    if 'u' in key:
        alt = key.replace('u', 'o')
        if alt in dictionary:
            return alt, dictionary[alt]
        alt2 = key.replace('u', 'o', 1)
        if alt2 in dictionary:
            return alt2, dictionary[alt2]

    # Case 4: Reversing trailing 'z' to 'i' (e.g., imbulaz -> imbulai)
    if key.endswith('z'):
        alt = key[:-1] + 'i'
        if alt in dictionary:
            return alt, dictionary[alt]

    # Case 5: Strip acoustic trailing 'h' (e.g., umbasih -> umbasi)
    if key.endswith('h') and len(key) > 3:
        alt = key[:-1]
        if alt in dictionary:
            return alt, dictionary[alt]
            
    return None, None


def try_strip_prefixes(word, dictionary):
    """Try stripping each known prefix and check if the remainder
    (with reverse substitution + vowel de-contraction) exists in the
    dictionary.  Also tries a second-level prefix strip (stacked prefixes).

    Returns list of match dicts, each with keys:
      prefix, category, meaning, root, gloss, matched,
      and optionally: infix, infix_meaning, suffix, suffix_meaning,
                      prefix2, prefix2_meaning (stacked prefix),
                      redup (reduplication type)
    """
    results = []

    # Build a list of (logical_prefix, category, meaning, sub_type, surface_prefix) tuples.
    # 'surface_prefix' is the form of the prefix as it appears in the surface word
    # after vowel contraction.  For most prefixes surface_prefix == prefix_str.
    # But for vowel-ending prefixes (e.g. 'ongo'), the terminal vowel may be
    # absorbed by the stem's initial vowel, giving a contracted surface form
    # (e.g. 'ongo' + 'ulun' → 'ongulun', surface prefix = 'ongu').
    prefix_candidates = []
    for prefix_str, category, meaning, sub_type in PREFIXES:
        # Always try the uncontracted prefix form
        prefix_candidates.append((prefix_str, category, meaning, sub_type, prefix_str))
        # For vowel-ending prefixes, also try contracted forms
        if prefix_str and prefix_str[-1] in 'aeiou':
            pbase = prefix_str[:-1]   # prefix stem without final vowel
            last_v = prefix_str[-1]
            if last_v == 'o':
                allowed_vowels = 'uoe'  # o+u->u, o+o->o, o+i->e
            elif last_v == 'a':
                allowed_vowels = 'ae'   # a+a->a, a+i->e
            else:
                allowed_vowels = last_v  # i/u/e don't contract to other vowels easily
                
            for contracted_v in allowed_vowels:
                cp = pbase + contracted_v
                if cp != prefix_str:
                    prefix_candidates.append(
                        (prefix_str, category, meaning, sub_type, cp)
                    )

    for prefix_str, category, meaning, sub_type, surface_prefix in prefix_candidates:
        if not word.startswith(surface_prefix):
            continue
        # Require a meaningful remainder (at least 2 chars after prefix)
        # Guard: short ambiguous prefixes require a longer remainder
        if prefix_str in ('no', 'mo', 'ma', 'ko', 'ka', 'po', 'pa',
                          'ta', 'to', 'ti', 'mu', 'mi', 'pi', 'm', 'o', 'a'):
            if len(word) - len(surface_prefix) < 3:
                continue

        remainder = word[len(surface_prefix):]

        # Build candidate root forms.
        # Case A: surface_prefix == prefix_str (no contraction occurred).
        #   De-contract then reverse-substitute as normal.
        # Case B: surface_prefix != prefix_str (contraction occurred at boundary).
        #   The contracted vowel in the surface prefix is the result of merging
        #   prefix's terminal vowel with stem's initial vowel.  Restore it by
        #   prepending the contracted vowel to remainder.
        decontracted = decontract_vowel(prefix_str, remainder)
        candidates = []
        
        # High-priority: if the prefix vowel contracted, resolve the exact original vowel:
        # o + i -> e/i (po + imot -> pemot, ongo + inggot -> onginggot) -> resolved = i
        # o + u -> u   (ongo + ulun -> ongulun) -> resolved = u
        # a + i -> e/i (manga + imot -> mengimot/manginggot) -> resolved = i
        contraction_occurred = (surface_prefix != prefix_str and prefix_str and surface_prefix)
        resolved_v = None
        
        if contraction_occurred:
            p_last = prefix_str[-1]
            s_last = surface_prefix[-1]
            if p_last == 'o' and s_last in ('e', 'i'):
                resolved_v = 'i'
            elif p_last == 'o' and s_last == 'u':
                resolved_v = 'u'
            elif p_last == 'a' and s_last in ('e', 'i'):
                resolved_v = 'i'
            
            if resolved_v:
                c_word = resolved_v + remainder
                for rc in reverse_substitute(c_word, sub_type, SUBSTITUTION_MAP):
                    if rc not in candidates:
                        candidates.append(rc)
                if c_word not in candidates:
                    candidates.append(c_word)

        # If no contraction occurred, or the contraction was not resolved, try all decontracted variants
        if not contraction_occurred or not resolved_v:
            for dc in decontracted:
                for rc in reverse_substitute(dc, sub_type, SUBSTITUTION_MAP):
                    if rc not in candidates:
                        candidates.append(rc)
            if remainder not in candidates:
                candidates.append(remainder)

        for root_candidate in candidates:
            # ── Direct root lookup ──────────────────────────────────
            lk, entry = _lookup_root(root_candidate, dictionary)
            if lk:
                results.append({
                    "prefix":   prefix_str,
                    "category": category,
                    "meaning":  meaning,
                    "root":     root_candidate,
                    "gloss":    entry["gloss"],
                    "matched":  True,
                })
                continue

            # ── Infix within remainder (AFTER prefix strip) ─────────
            # This is the correct placement per §2.3: infix goes into root.
            infix_str, infix_cat, infix_meaning, after_infix = strip_infix(root_candidate)
            if infix_str:
                lk2, entry2 = _lookup_root(after_infix, dictionary)
                if lk2:
                    results.append({
                        "prefix":        prefix_str,
                        "category":      category,
                        "meaning":       meaning,
                        "infix":         infix_str,
                        "infix_meaning": infix_meaning,
                        "root":          after_infix,
                        "gloss":         entry2["gloss"],
                        "matched":       True,
                    })
                    continue

            # ── ko-...-o nominalizing circumfix (Forschner grammar) ─────────
            # When prefix is ko-/ka-, the suffix -o forms a nominalizing
            # circumfix producing abstract nouns (not the verbal imperative -o).
            # If the root ends in a high vowel /u/ or /i/, a /v/ glide is
            # inserted before -o:  ko- + sundu + -o → kosunduvo  (length/power)
            #                      ko- + anaru + -o → konoruvo   (length)
            # Strip the glide (-v) + suffix (-o) together to recover the root.
            if prefix_str in ('ko', 'ka') and root_candidate.endswith('vo') and len(root_candidate) > 3:
                glide_core = root_candidate[:-2]   # strip 'vo' → bare vowel-final root
                lk_g, entry_g = _lookup_root(glide_core, dictionary)
                if lk_g:
                    results.append({
                        "prefix":         prefix_str,
                        "category":       "nominal",
                        "meaning":        f"abstract noun nominalizer ({prefix_str}-...-o circumfix)",
                        "suffix":         "o",
                        "suffix_meaning": "abstract noun nominalizer (ko-...-o, /v/ glide before vowel-final root)",
                        "root":           lk_g,
                        "gloss":          entry_g["gloss"],
                        "matched":        True,
                    })

            # ── Suffix within remainder ──────────────────────────────────────
            for suffix_str, suf_cat, suf_meaning in SUFFIXES:
                if root_candidate.endswith(suffix_str) and len(root_candidate) > len(suffix_str) + 1:
                    core = root_candidate[:-len(suffix_str)]
                    lk3, entry3 = _lookup_root(core, dictionary)
                    if lk3:
                        # ko-/ka- + -o is the nominalizing circumfix, not imperative
                        resolved_suf_meaning = suf_meaning
                        resolved_category    = category
                        if prefix_str in ('ko', 'ka') and suffix_str == 'o':
                            resolved_suf_meaning = "abstract noun nominalizer (ko-...-o circumfix)"
                            resolved_category    = "nominal"
                        results.append({
                            "prefix":         prefix_str,
                            "category":       resolved_category,
                            "meaning":        meaning,
                            "suffix":         suffix_str,
                            "suffix_meaning": resolved_suf_meaning,
                            "root":           core,
                            "gloss":          entry3["gloss"],
                            "matched":        True,
                        })


            # ── Stacked prefix: try a SECOND prefix on the remainder ─
            for prefix2_str, cat2, meaning2, sub_type2 in PREFIXES:
                if not root_candidate.startswith(prefix2_str):
                    continue
                if len(root_candidate) <= len(prefix2_str) + 1:
                    continue
                remainder2 = root_candidate[len(prefix2_str):]
                decon2 = decontract_vowel(prefix2_str, remainder2)
                cands2 = set()
                for dc2 in decon2:
                    for rc2 in reverse_substitute(dc2, sub_type2, SUBSTITUTION_MAP):
                        cands2.add(rc2)
                cands2.add(remainder2)
                for root2 in cands2:
                    lk4, entry4 = _lookup_root(root2, dictionary)
                    if lk4:
                        results.append({
                            "prefix":          prefix_str,
                            "category":        category,
                            "meaning":         meaning,
                            "prefix2":         prefix2_str,
                            "prefix2_meaning": f"{meaning2} ({cat2})",
                            "root":            root2,
                            "gloss":           entry4["gloss"],
                            "matched":         True,
                        })
                        break  # one stacked hit is enough

    return results


def try_strip_suffixes(word, dictionary):
    """Try stripping each known suffix and return the first match.

    Returns (suffix_str, category, meaning, dict_entry) or
    (None, None, None, None) if no match.
    """
    for suffix_str, category, meaning in SUFFIXES:
        if word.endswith(suffix_str) and len(word) > len(suffix_str) + 1:
            core = word[:-len(suffix_str)]
            lk, entry = _lookup_root(core, dictionary)
            if lk:
                return suffix_str, category, meaning, entry
            # Also try infix within the core
            infix_str, _, infix_meaning, after_infix = strip_infix(core)
            if infix_str:
                lk2, entry2 = _lookup_root(after_infix, dictionary)
                if lk2:
                    return suffix_str, category, meaning, entry2
    return None, None, None, None


# ═══════════════════════════════════════════════════════════════════════
# 10. MORPHOLOGICAL GENERATION  (surface form from root + affixes)
# ═══════════════════════════════════════════════════════════════════════

# Forward consonant substitution map (root-initial → prefix-adjacent nasal)
_FWD_SUB = {'p': 'm', 'b': 'm', 'v': 'm', 't': 'n', 's': 'n', 'k': 'ng'}

def _apply_substitution(prefix, root):
    """Apply forward consonant substitution: replace root-initial C with
    the nasal at the same place of articulation, when the prefix calls for
    substitution ('sub' type)."""
    if not root:
        return root
    if root[0] in _FWD_SUB:
        return _FWD_SUB[root[0]] + root[1:]
    return root

def _apply_vowel_contraction(prefix, root):
    """Apply vowel contraction at the prefix–root boundary when both end/
    start with vowels (§1.22).

    Rules (prefix_last_vowel + root_initial_vowel → merged_vowel):
      a + i = e    o + i = e    o + u = u    a + a = a    o + o = o
    """
    if not prefix or not root:
        return prefix, root
    pv = prefix[-1]
    rv = root[0] if root else ''
    if pv not in 'aeiou' or rv not in 'aeiou':
        return prefix, root
    contractions = {
        ('a', 'i'): 'e', ('o', 'i'): 'e',
        ('o', 'u'): 'u', ('a', 'a'): 'a',
        ('o', 'o'): 'o',
    }
    merged = contractions.get((pv, rv))
    if merged:
        # Replace prefix-final vowel with merged vowel, drop root-initial vowel
        return prefix[:-1] + merged, root[1:]
    return prefix, root

def generate(root, prefix=None, suffix=None, infix=None, enclitic=None):
    """Generate the surface form of a Rungus word from its morpheme parts.

    Args:
        root    : str — the dictionary root form (e.g., 'panau', 'imot')
        prefix  : str or None — prefix string without dash (e.g., 'mongo')
        suffix  : str or None — suffix string without dash (e.g., 'on')
        infix   : str or None — infix string without dashes (e.g., 'in', 'um')
        enclitic: str or None — enclitic string without dash (e.g., 'ku')

    Returns:
        surface_form: str — the generated surface form

    Examples:
        generate('panau', prefix='mo')     → 'mamanau'
        generate('imot', prefix='po')      → 'pemot'
        generate('rikot', infix='um')      → 'rumikot'
        generate('rikot', infix='inum')    → 'rinumikot'
        generate('ulun', prefix='ongo')    → 'ongulun'
        generate('gama', prefix='manga')   → 'mangagama'
        generate('lobong', prefix='ko', suffix='on')  → 'kolobongon'
    """
    form = root

    # Step 1: apply infix (before prefix, because infix goes into root)
    if infix:
        # Find the first consonant cluster, insert infix after it
        m = re.match(r'^([^aeiou]+)(.*)', form, re.IGNORECASE)
        if m:
            form = m.group(1) + infix + m.group(2)
        else:
            # Root starts with vowel: infix goes right at the start
            form = infix + form

    # Step 2: apply suffix
    if suffix:
        form = form + suffix

    # Step 3: apply prefix (with substitution + vowel contraction)
    if prefix:
        # Find prefix entry to get substitution type
        sub_type = 'none'
        for p_str, _, _, st in PREFIXES:
            if p_str == prefix:
                sub_type = st
                break

        if sub_type == 'sub':
            # Apply consonant substitution (p/b/v→m, t/s→n, k→ng)
            form = _apply_substitution(prefix, form)

        # Apply vowel contraction at prefix–stem boundary.
        # Note: for mo-/ma- prefixes, the prefix vowel also harmonises:
        # mo- before a-vowel substituted stem → 'ma-' (a-harmony).
        # e.g., mo + panau → mo + manau → 'mamanau' (o→a harmony before 'a').
        effective_prefix = prefix
        if prefix in ('mo', 'mong', 'mongo', 'moko', 'mongo') and form and form[0] == 'a':
            # a-vowel harmony: the prefix vowel shifts from 'o' to 'a'
            effective_prefix = prefix.replace('o', 'a', 1)
        elif prefix in ('mo',) and form and form[0] in 'aeiou':
            # mo + vowel-initial (after substitution left a vowel): apply contraction
            pass

        new_prefix, form = _apply_vowel_contraction(effective_prefix, form)
        form = new_prefix + form

    # Step 4: apply enclitic
    if enclitic:
        form = form + enclitic

    return form


# ═══════════════════════════════════════════════════════════════════════
# 11. MAIN ANALYSIS FUNCTION
# ═══════════════════════════════════════════════════════════════════════

def analyze(word, dictionary):
    """Full morphological analysis of a Rungus word.

    Returns a dict with keys:
      input          : str   — original input word
      root           : str   — canonical root headword (or None)
      root_gloss     : str   — English gloss of root (or None)
      prefix         : str   — stripped prefix (or None)
      prefix_meaning : str   — prefix gloss (or None)
      prefix2        : str   — second stacked prefix (or None)
      prefix2_meaning: str   — second prefix gloss (or None)
      infix          : str   — stripped infix (or None)
      infix_meaning  : str   — infix gloss (or None)
      suffix         : str   — stripped suffix (or None)
      suffix_meaning : str   — suffix gloss (or None)
      enclitic       : str   — stripped enclitic (or None)
      enclitic_meaning: str  — enclitic gloss (or None)
      breakdown      : list  — human-readable explanation steps
      matched        : bool  — True if root was found
      confidence     : float — 0.0–1.0
      proper_name    : bool  — True if flagged as a proper name
      loanword       : bool  — True if flagged as a Malay/Arabic loanword
      reduplication  : str   — reduplication type if detected (or None)
    """
    word_lower = word.strip().lower()
    original = word.strip()

    result = {
        "input":           original,
        "root":            None,
        "root_gloss":      None,
        "prefix":          None,
        "prefix_meaning":  None,
        "prefix2":         None,
        "prefix2_meaning": None,
        "infix":           None,
        "infix_meaning":   None,
        "suffix":          None,
        "suffix_meaning":  None,
        "enclitic":        None,
        "enclitic_meaning": None,
        "breakdown":       [],
        "matched":         False,
        "confidence":      0.0,
        "proper_name":     False,
        "loanword":        False,
        "reduplication":   None,
    }

    def _set_match(root_key, confidence, explanation):
        """Resolve root to canonical parent and populate result fields."""
        canonical_hw, canonical_gloss = resolve_to_parent(root_key, dictionary)
        
        # If it was matched as a proper name or loanword, set flags and gloss (only if not a native dictionary word)
        if root_key not in dictionary:
            if root_key in PROPER_NAMES:
                result["proper_name"] = True
                canonical_gloss = "proper name (biblical / geographic)"
            elif root_key in LOANWORDS:
                result["loanword"] = True
                canonical_gloss = "loanword (Malay / Arabic)"

        result["root"] = canonical_hw
        result["root_gloss"] = canonical_gloss
        result["matched"] = True
        result["confidence"] = confidence
        result["breakdown"].extend(explanation)
        
        entry_hw = dictionary.get(root_key, {}).get("headword", root_key) if root_key in dictionary else root_key
        if canonical_hw != entry_hw:
            result["breakdown"].append(
                f"  → resolved sub-entry '{root_key}' to parent '{canonical_hw}'"
            )

    # ── Step 0: Proper name / loanword fast-path ──────────────────────
    if word_lower in PROPER_NAMES:
        result["proper_name"] = True
        result["matched"] = True
        result["confidence"] = 0.85
        result["root"] = original
        result["root_gloss"] = "proper name (biblical / geographic)"
        result["breakdown"].append(f"proper name: '{original}'")
        return result

    if word_lower in LOANWORDS:
        result["loanword"] = True
        result["matched"] = True
        result["confidence"] = 0.75
        result["root"] = original
        result["root_gloss"] = "loanword (Malay / Arabic)"
        result["breakdown"].append(f"loanword: '{original}'")
        return result

    # ── Step 1: Strip enclitics (outermost layer) ─────────────────────
    # Guard: if the full word is already a known entry, don't strip enclitics.
    # This prevents 'iadko' (but/however) from being split into 'iad' + '-ko'.
    _word_is_known = (word_lower in dictionary or word_lower in STANDALONE_WORDS
                      or word_lower in FUNCTION_WORDS)
    if _word_is_known:
        enc_str, enc_cat, enc_meaning, working = None, None, None, word_lower
    else:
        enc_str, enc_cat, enc_meaning, working = strip_enclitic(word_lower)
    if enc_str:
        result["enclitic"] = enc_str
        result["enclitic_meaning"] = f"{enc_meaning} ({enc_cat})"
        result["breakdown"].append(f"enclitic: -{enc_str} = {enc_meaning}")


    # ── Step 1.2: Function word check ───────────────────────────────
    if working in FUNCTION_WORDS:
        result["matched"] = True
        result["confidence"] = 1.0
        result["root"] = working
        result["root_gloss"] = "grammatical function word / particle"
        result["breakdown"].append(f"function word: '{working}'")
        return result

    # ── Step 1.5: Direct dictionary lookup ───────────────────────────
    # If the word is already a known base headword, return it directly.
    # This prevents false reduplication stripping on words like 'kakal' or 'kakau'.
    if working in dictionary and not dictionary[working].get("is_subentry", False) and "-" not in working:
        _set_match(working, 1.0, [f"root: '{working}' = \"{dictionary[working]['gloss']}\""])
        return result

    # ── Step 2: Reduplication detection ──────────────────────────────
    redup_type, redup_base = detect_reduplication(working)
    if redup_type:
        # Recursively analyze the base form to ensure it yields a valid match.
        # This prevents false-positive reduplication stripping from blocking the correct parse.
        sub_r = analyze(redup_base, dictionary)
        if sub_r["matched"]:
            result["reduplication"] = redup_type
            result["root"] = sub_r["root"]
            result["root_gloss"] = sub_r["root_gloss"]
            result["matched"] = True
            result["confidence"] = sub_r["confidence"] * 0.95
            result["prefix"] = sub_r["prefix"]
            result["prefix_meaning"] = sub_r["prefix_meaning"]
            result["prefix2"] = sub_r["prefix2"]
            result["prefix2_meaning"] = sub_r["prefix2_meaning"]
            result["infix"] = sub_r["infix"]
            result["infix_meaning"] = sub_r["infix_meaning"]
            result["suffix"] = sub_r["suffix"]
            result["suffix_meaning"] = sub_r["suffix_meaning"]
            result["enclitic"] = sub_r["enclitic"]
            result["enclitic_meaning"] = sub_r["enclitic_meaning"]
            result["proper_name"] = sub_r["proper_name"]
            result["loanword"] = sub_r["loanword"]
            
            result["breakdown"].append(
                f"reduplication ({redup_type}): '{working}' → base form '{redup_base}'"
            )
            result["breakdown"].extend(sub_r["breakdown"])
            return result

    # ── Step 3: Direct dictionary lookup ─────────────────────────────
    if working in dictionary and not dictionary[working].get("is_subentry", False):
        _set_match(working, 1.0, [f"root: '{working}' = \"{dictionary[working]['gloss']}\""])
        return result

    # Vowel-ending alternation variants (common in Rungus)
    _alt_map = [('o', 'a'), ('a', 'o'), ('u', 'o'), ('i', ''), ('e', 'o')]
    for old_end, new_end in _alt_map:
        if working.endswith(old_end):
            variant = working[:-1] + new_end if new_end else working[:-1]
            if variant and variant in dictionary and not dictionary[variant].get("is_subentry", False):
                _set_match(variant, 0.9,
                           [f"root: '{variant}' = \"{dictionary[variant]['gloss']}\" (vowel variant of '{working}')"])
                return result

    # ── Step 4: Strip infix (bare root before any prefix) ────────────
    # Try infix on the working form first (for bare-root infixed words
    # like rumikot, rinumikot that have no prefix).
    infix_str, infix_cat, infix_meaning, after_infix = strip_infix(working)
    if infix_str:
        result["infix"] = infix_str
        result["infix_meaning"] = infix_meaning
        result["breakdown"].append(f"infix: -{infix_str}- = {infix_meaning}")
        lk, entry = _lookup_root(after_infix, dictionary)
        if lk:
            _set_match(after_infix, 0.85, [f"root: '{after_infix}' = \"{entry['gloss']}\""])
            return result

    # ── Step 5: Strip suffixes ────────────────────────────────────────
    suf_str, suf_cat, suf_meaning, suf_entry = try_strip_suffixes(working, dictionary)
    if suf_str and suf_entry:
        result["suffix"] = suf_str
        result["suffix_meaning"] = f"{suf_meaning} ({suf_cat})"
        _set_match(
            suf_entry["headword"].strip().lower(), 0.75,
            [f"suffix: -{suf_str} = {suf_meaning}",
             f"root candidate: '{suf_entry['headword']}'"]
        )
        return result

    # ── Step 6: Strip prefixes (with substitution + de-contraction) ───
    prefix_results = try_strip_prefixes(working, dictionary)
    if prefix_results:
        # Get parent of working word if it is a subentry, to prioritize
        # matching against its true parent root.
        parent_word = None
        if working in dictionary and dictionary[working].get("is_subentry"):
            parent_word = dictionary[working].get("parent", "").strip().lower()

        # Rank results:
        # 1. Prefer matching the direct parent of the subentry (e.g. mamasa -> basa, not pasa).
        # 2. Prefer single-prefix (no prefix2) over stacked-prefix matches.
        # 3. Prefer longer prefixes (more specific — avoids short-prefix false positives).
        # 4. Among equal-prefix-length, prefer longer root words (more specific).
        # 5. Prefer direct matches (no infix/suffix) over complex parses.
        def _rank(r):
            is_parent   = 0 if parent_word and r.get("root", "").strip().lower() == parent_word else 1
            has_p2      = 1 if r.get("prefix2") else 0
            prefix_len  = -len(r.get("prefix", ""))  # negative = longer prefixes first
            has_infix   = 1 if r.get("infix") else 0
            has_suffix  = 1 if r.get("suffix") else 0
            root_len    = -len(r.get("root", ""))    # negative = longer roots first
            return (is_parent, has_p2, prefix_len, has_infix, has_suffix, root_len)
        prefix_results.sort(key=_rank)

        best = prefix_results[0]
        # If this is a subentry but the best prefix match did not resolve to its true parent,
        # ignore it so we can try to resolve it via suffix stripping (Step 6) or subentry fallback.
        if parent_word and best["root"].strip().lower() != parent_word:
            pass
        else:
            result["prefix"] = best["prefix"]
            result["prefix_meaning"] = f"{best['meaning']} ({best['category']})"
            result["infix"] = best.get("infix")
            result["infix_meaning"] = best.get("infix_meaning")
            result["suffix"] = best.get("suffix")
            result["suffix_meaning"] = best.get("suffix_meaning")
            result["prefix2"] = best.get("prefix2")
            result["prefix2_meaning"] = best.get("prefix2_meaning")

            parts = [f"prefix: {best['prefix']} = {best['meaning']}"]
            if best.get("prefix2"):
                parts.append(f"prefix2: {best['prefix2']} = {best['prefix2_meaning']}")
            if best.get("infix"):
                parts.append(f"infix: -{best['infix']}-  = {best['infix_meaning']}")
            if best.get("suffix"):
                parts.append(f"suffix: -{best['suffix']} = {best['suffix_meaning']}")
            parts.append(f"root candidate: '{best['root']}'")

            _set_match(best["root"].strip().lower(), 0.8, parts)
            return result

    # ── Step 7: Prefix + suffix combination ──────────────────────────
    for prefix_str, cat, meaning, sub_type in PREFIXES:
        if not working.startswith(prefix_str):
            continue
        if len(working) <= len(prefix_str) + 2:
            continue
        after_p = working[len(prefix_str):]
        middles = set(decontract_vowel(prefix_str, after_p))
        for rc in reverse_substitute(after_p, sub_type, SUBSTITUTION_MAP):
            middles.add(rc)
        middles.add(after_p)

        for middle in middles:
            for suffix_str, suf_cat2, suf_meaning2 in SUFFIXES:
                if middle.endswith(suffix_str) and len(middle) > len(suffix_str) + 1:
                    core = middle[:-len(suffix_str)]
                    lk, entry = _lookup_root(core, dictionary)
                    if lk:
                        result["prefix"] = prefix_str
                        result["prefix_meaning"] = f"{meaning} ({cat})"
                        result["suffix"] = suffix_str
                        result["suffix_meaning"] = f"{suf_meaning2} ({suf_cat2})"
                        _set_match(
                            lk, 0.7,
                            [f"prefix: {prefix_str} = {meaning}",
                             f"suffix: -{suffix_str} = {suf_meaning2}",
                             f"root candidate: '{lk}'"]
                        )
                        return result

    # ── Step 8: Subentry fallback ─────────────────────────────────────
    if working in dictionary and dictionary[working].get("is_subentry", False):
        _set_match(working, 0.6,
                   ["morphological parse failed; resolved via sub-entry parent lookup"])
        return result

    # ── Step 9: Standalone words / VIRTUAL_ROOTS fallback ────────────
    if working in STANDALONE_WORDS:
        gloss, pos = STANDALONE_WORDS[working]
        result["root"] = working
        result["root_gloss"] = gloss
        result["matched"] = True
        result["confidence"] = 0.95
        result["breakdown"].append(f"standalone word: '{working}' = \"{gloss}\" ({pos})")
        return result

    # Nothing found
    return result


# ═══════════════════════════════════════════════════════════════════════
# 12. UTILITY: LEVENSHTEIN SUGGESTIONS
# ═══════════════════════════════════════════════════════════════════════

def suggest_similar(word, dictionary, max_dist=2, max_results=5):
    """Return up to max_results dictionary words within edit distance
    max_dist of the given word.  Uses simple Wagner-Fischer DP.
    Only compares against words of similar length to keep it fast.
    """
    word = word.lower()
    n = len(word)
    results = []
    for dict_word in dictionary:
        # Quick length filter before computing full edit distance
        if abs(len(dict_word) - n) > max_dist:
            continue
        # Compute edit distance
        m = len(dict_word)
        dp = list(range(m + 1))
        for i, c1 in enumerate(word):
            dp2 = [i + 1] + [0] * m
            for j, c2 in enumerate(dict_word):
                cost = 0 if c1 == c2 else 1
                dp2[j + 1] = min(dp2[j] + 1, dp[j + 1] + 1, dp[j] + cost)
            dp = dp2
        dist = dp[m]
        if dist <= max_dist:
            results.append((dist, dict_word))
        if len(results) > max_results * 3:
            # Early exit — good enough candidates found
            break
    results.sort()
    return [w for _, w in results[:max_results]]
