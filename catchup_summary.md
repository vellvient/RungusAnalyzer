# Rungus Translator — Catch-Up Summary (1 July 2026)

## Project Goal
Build a digital translator for the Rungus language (endangered language of Sabah). You're from Kudat, of Rungus/Momogun descent. This doubles as a university admissions project.

## What's Been Done So Far
| Phase | What | Status |
|---|---|---|
| Web scraping | Scraped ~12,000 entries from Webonary.org Rungus dictionary | ✅ |
| Data cleaning | Merged datasets, cleaned parsing bugs (the "abai" bug) | ✅ |
| Stats report | Analyzed dictionary coverage, missing English entries | ✅ |
| Morphological analyzer | Built `rungus_analyzer.py` — strips affixes to find roots | ✅ Prototype |

## The Analyzer (What Christine Asked About)
Takes any Rungus word → strips known prefixes/suffixes/infixes/clitics → checks if the remainder is in the dictionary → returns root + affix breakdown.

### Book Analysis Results (NEW)
Ran analyzer against all 9 Rungus book files in data/books/:

- **534,775 word tokens** across 30,000+ sentences
- **17,586 unique words**
- **~35% unique words** found in dictionary (matched + decomposed via analyzer)
- **~65% per-word coverage** in the books (most unknown words are proper names and vocabulary gaps)
- Analyzer successfully decomposes words like `minonurat → monurat` (infix -in-), `kogunaan → guna` (prefix ko- + suffix -an + infix -og-), `nokolohing → lohing` (prefix noko-)

### Critical Resources Discovered (NEW)

1. **Swarthmore College LING073 (Spring 2025)** — A computational linguistics class at Swarthmore actually built a **morphological transducer** (exactly the "hermit crab parser" Christine mentioned!) for Rungus using HFST/Apertium. They have:
   - 14 phonological rewrite rules (the transformation rules we're missing!)
   - Grammar documentation with detailed rules for prefixes, suffixes, infixes
   - A working analyzer/generator (90% test pass rate on generation)
   - **This is the single most valuable resource for the project**

2. **Forschner's "Outline of a Momogun Grammar" (1994)** — 87-page PDF grammar available free at ebfo.de. Contains:
   - Complete phonology with vowel contraction rules (e.g. o + u = u, a + a = a, o + i = e)
   - Verbal flection table (which affix combinations produce which tenses)
   - Noun affixation patterns
   - Pronunciation guide and alphabet

3. **"Register of roots in the Rungus dialect"** — A root registry PDF on ebfo.de. Contains a list of Rungus root words.

4. **"Teach yourself Rungus"** — Learning lessons available on ebfo.de

5. **Webonary Introduction** — Basic language overview with alphabet guide

## The System You Envisioned
The HITL (Human-in-the-Loop) pipeline:
```
Books (30K sentences) → Analyzer → Finds low-confidence words
  ↓
Human (Christine + you) reviews, explains rules
  ↓
Rules encoded into analyzer code
  ↓
Re-run analysis → fewer low-confidence words
  ↓
Repeat until coverage hits 95%+
```

## Your Rungus Speaker Skill
You can judge if a word "sounds right or wrong" — this is valuable for:
- Validating analyzer output
- Spotting obviously wrong decompositions
- Telling us if a word is real vs. nonsense
