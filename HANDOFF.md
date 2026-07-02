# Rungus Translator — Session Handoff (1 July 2026)

## Project Overview
Building a **digital translator** for the **Rungus language** (ISO 639-3: drg, endangered indigenous language of Sabah, Malaysia). The user (Aifven) is of Rungus/Momogun descent, from Kudat, Sabah. This serves as both a language preservation project and a university admissions portfolio piece (targeting Stanford, Imperial, etc.).

**Primary collaborator:** Christine Dreiheller (christine_dreiheller@sil.org) — linguist at SIL Global, manages the Rungus Webonary dictionary.

---

## Directory Structure

```
C:\backup\!programming\RungusTranslator\
│
├── rungus_analyzer.py              ← MAIN: v2.0 morphological analyzer (Forschner rules)
├── mainDataset_merged.json         ← 12K dictionary entries (scraped from Webonary)
├── analyze_books.py                ← Script to test analyzer against corpus
├── catchup_summary.md              ← Project brief for human readers
├── swarthmore_rules_analysis.md    ← Extracted grammar rules from Swarthmore LING073
├── email_draft.txt                 ← Draft email to Christine
├── stats_report.txt                ← Dictionary statistics
│
├── data/books/
│   ├── book_1.json .. book_9.json  ← 30K sentences of real Rungus text
│   │                                  (folk tales + biblical translations)
│
├── resources/                       ← Downloaded PDFs
│   ├── Rungus-Grammar_A4.pdf       ← Forschner grammar (87 pages)
│   ├── Rungus_Roots_A4.pdf         ← Root word registry
│   ├── English_Rungus_Dictionary_A4.pdf
│   ├── Teach_Yourself_Rungus.pdf
│   └── Tangon_do_Rungus.pdf
│
├── rungus-analyzer-web/             ← Web app (Vercel-ready)
│   ├── api/index.py                ← Flask API (parallel analyzer)
│   ├── dictionary.json             ← 12K entry lightweight dict (structured)
│   ├── index.html                  ← Dark-themed frontend with visual breakdown
│   ├── vercel.json                 ← Vercel deployment config
│   └── requirements.txt            ← Python deps
│
└── (other files: scrape scripts, backup datasets, etc.)
```

---

## What Was Accomplished Today

### 1. Corpus Analysis
- Scanned all 9 book files (30K sentences, 535K tokens, 17,586 unique words)
- v1 analyzer covered **~65%** of word tokens
- v2 analyzer (after all fixes) covers **~68%** of word tokens
- Top unknowns are mostly proper names (biblical) and function words missing from dictionary

### 2. Key Resources Discovered
| Resource | URL | Contents |
|---|---|---|
| Swarthmore LING073 Rungus | wikis.swarthmore.edu/ling073/Rungus | Grammar docs + transducer stats (14 twol rules, 90% pass rate) |
| Forschner Grammar (PDF) | ebfo.de/rungus/Rungus-Grammar_A4.pdf | 87-page full grammar by T.A. Forschner (1994) |
| Root Registry (PDF) | ebfo.de/rungus/Rungus_Roots_A4.pdf | List of Rungus root words |
| Teach Yourself Rungus (PDF) | ebfo.de/rungus/2014_Teach_Yourself_Rungus.pdf | Language learning lessons |
| Additional Folk Tales (PDF) | ebfo.de/rungus/Tangon_do_Rungus_%20A4.pdf | More Rungus stories |

### 3. Analyzer v2.0 — Rules Implemented (from Forschner)

**Phonological rules encoded:**
- **Consonant substitution** (§1.43): p→m, t→n, k→ng, v→m, s→n, b→m
- **Vowel contraction** (§1.21–1.22): a+i=e, o+i=e, o+u=u, a+a=a, o+o=o, o+i=e
- **Vowel de-contraction** (reverse): when prefix ending in vowel is stripped, try restoring stem's initial vowel

**Prefix inventory** (from §2.21–2.22 and §4.1):
- Intransitive: m-, mu-, mi-, miri-, moki-
- Transitive actor focus: mong-/mang-/moko-, mongo-/manga-, minong-/min-
- Perfect/accidental: noko-, nakapa-, nokopong-
- Causative: po-/pa-, ponga-/pongi-, popi-
- Realisation: ko-/ka-, kapa-/kopo-
- Plural: ongo-/anga-
- Intensifier: ta-/to-
- Past causative: kinopo-, pinong-

**Suffixes:** -on, -an, -o, -ai, -onon, -anon, -inai

**Infixes:** -in- (past), -um- (process), -inum- (past process)

**Enclitics:** -ku, -nu, -no, -mo, -dau, -ko, -kou, -po, -no, -nopo, -zou

### 4. Bug Fixes Applied

#### Bug 1: Subentries matching as roots
- **Problem:** Words like `mamanau` are sub-entries of `panau` in the dictionary. The analyzer found `mamanau` directly in the lookup dict and returned it as a root, never stripping the affixes.
- **Fix:** Tagged dictionary entries with `is_subentry: True/False`. The `analyze()` function now SKIPs direct matches on subentries and lets morphological rules run. If morphological rules fail, it falls back to resolving via `parent` key.

#### Bug 2: Virtual root resolution for dictionary gaps
- **Problem:** True linguistic roots like `ruhang` (companion) aren't in the dictionary at all. So `mongoruhang` stripped `mongo-` to get `ruhang`, then couldn't find `ruhang` in the dict.
- **Fix:** Added `VIRTUAL_ROOTS` mapping (`{'ruhang': 'koruhang'}`) and a `resolve_to_parent()` function that maps missing roots to their nearest dictionary derivative.

### 5. Web App (Vercel-ready)
- **Frontend:** Dark-themed single-page HTML with word breakdown visualization
  - Color-coded segments: prefix (blue), root (green), suffix (orange), infix (red), enclitic (purple)
  - Clickable example words
  - Suggestion chips for failed lookups
- **Backend:** Flask API with `POST /api/analyze` endpoint
- **Dictionary:** Precompiled lightweight `dictionary.json` (12K entries, 365 KB)
- **Live local:** http://127.0.0.1:5000

---

## Current Analyzer Capabilities

| Feature | Status |
|---|---|
| Direct dictionary lookup | ✅ |
| Vowel variation matching (o/a, u/o alternations) | ✅ |
| Subentry avoidance & parent resolution | ✅ |
| Virtual root mapping (ruhang→koruhang) | ✅ |
| Infix detection (-in-, -um-, -inum-) | ✅ |
| Prefix stripping with consonant substitution | ✅ |
| Suffix detection (-on, -an, -o, -ai) | ✅ |
| Prefix+suffix combination detection | ✅ |
| Enclitic stripping (-ku, -nu, -ko, -po, etc.) | ✅ |
| Vowel de-contraction at prefix boundaries | ✅ |
| Intensifier prefix (ta-, to-) | ✅ |
| Affix meaning labeling | ✅ |
| Reduplication (mamamanau) | ❌ Not yet |
| Proper name filtering | ❌ Not yet |
| Root cross-reference with Root Registry PDF | ❌ Not yet |

---

## Known Gaps to Address

1. **Reduplication** — Words like `mamamanau` (reduplication of `mamanau` for collective action) are not handled. Forschner §2.52 describes reduplication rules.

2. **Dictionary coverage** — Common words like `ulun` (person), `araat` (bad), `ginavo` (heart/feeling) are missing from Webonary entirely. Cross-reference with `Rungus_Roots_A4.pdf` (root registry) to fill gaps.

3. **Swarthmore transducer rules** — The LING073 students built 14 twol (phonological rewrite) rules. Their repo is at github.swarthmore.edu (private). Some rules may handle edge cases we're missing.

4. **Coverage improvement** — v2 covers ~68% of tokens. Target is 85%+. Adding missing dictionary entries + reduplication handling would be the biggest wins.

5. **Consonant substitution for mongo-/manga- type prefixes** — For voiced C stems, `mongo-`+`duat`→`mongoduat` works, but there may be cases where the consonant changes in ways we haven't captured.

---

## Architecture Notes for Future Work

### How analyze() works (order of operations):
1. Strip enclitics (outermost)
2. Direct dictionary lookup (skip if subentry)
3. Strip infixes
4. Strip prefixes (with reverse substitution + vowel de-contraction)
5. Strip suffixes
6. Prefix + suffix combination search
7. Fallback: subentry parent resolution
8. Return result

### VIRTUAL_ROOTS pattern:
This is a clean way to patch dictionary gaps without modifying the JSON:
```python
VIRTUAL_ROOTS = {
    'ruhang': 'koruhang',
    # Add more as discovered:
    # 'gavo': 'ginavo',   # hypothetical example
}
```

### resolve_to_parent() pattern:
Recursively traces subentries up to their primary root, also passing through VIRTUAL_ROOTS at each step.

### Vowel de-contraction:
When a vowel-ending prefix is stripped and remainder starts with a consonant, try prepending vowels based on the prefix's final vowel:
- `ongo-` (ends in o) → try u+lun, i+lun, o+lun, a+lun, e+lun → finds `ulun`

---

## How to Continue

1. **Deploy to Vercel:**
   ```bash
   cd C:\backup\!programming\RungusTranslator\rungus-analyzer-web
   vercel deploy
   ```

2. **Send to Christine:**
   - Let her try the web app
   - Ask her to validate the affix meanings
   - Ask about the Swarthmore transducer (she may know the linguists who supervised LING073)

3. **Cross-reference Root Registry:**
   - Extract words from `resources/Rungus_Roots_A4.pdf` (OCR or manual)
   - Cross-reference against dictionary to find missing roots
   - Add to VIRTUAL_ROOTS or directly to dictionary.json

4. **Improve coverage:**
   - Collect more function words (ulun, araat, etc.) from the books corpus
   - Add reduplication rules from Forschner §2.51–2.52

5. **Analyze the Forschner Grammar PDF:**
   - The full text was extracted to a 2,449-line markdown file (cached under AppData)
   - Sections 2.2–2.5 contain the productive affix rules
   - Section 4.1 has the verbal flection table

6. **HITL (Human-in-the-Loop) System:**
   - Build the confidence-scoring filter that presents low-confidence words to Christine
   - Christine explains rules → rules get encoded
   - Re-run analysis to measure improvement

---

## File Reference Quick Links

| File | Size | Purpose |
|---|---|---|
| `rungus_analyzer.py` | ~29 KB | CLI analyzer (source of truth) |
| `rungus-analyzer-web/api/index.py` | ~13 KB | Web API (mirror of rungus_analyzer.py) |
| `rungus-analyzer-web/dictionary.json` | 365 KB | Lightweight structured dictionary |
| `rungus-analyzer-web/index.html` | 17 KB | Frontend UI |
| `swarthmore_rules_analysis.md` | 3.5 KB | Extracted Swarthmore grammar rules |
| `catchup_summary.md` | 3 KB | Project brief for humans |

---

## Running the Analyzer

CLI:
```bash
cd C:\backup\!programming\RungusTranslator
python3 rungus_analyzer.py          # Run demo
python3 analyze_books.py            # Test against corpus
python3 -c "from rungus_analyzer import analyze, load_dictionary; d=load_dictionary(); print(analyze('nokolohing', d))"
```

Web App:
```bash
cd C:\backup\!programming\RungusTranslator\rungus-analyzer-web
python3.14 -c "from api.index import app; app.run(host='127.0.0.1', port=5000, debug=True)"
# Open http://127.0.0.1:5000
```

---

*Handoff prepared 1 July 2026 — Aifven's Rungus Translator Project*
