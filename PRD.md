# Rungus Morphological Analyzer & Translator — Product Requirements Document

> **Version:** 3.1 · **Date:** 11 July 2026  
> **Author:** Aifven Nelson (Rungus/Momogun descent, Kudat, Sabah)  
> **ISO 639-3:** `drg` · **Status:** Production (96.9% token coverage, 158 tests)
>
> **v3.1:** Implements Christine Dreiheller's expert feedback (6 July 2026): vowel harmony, glide insertion, L/R/D alternation, kA- polysemy, and the Kroeger four-voice system (agent / undergoer / beneficiary / conveyance) now tagged on every parse.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Product Overview](#2-product-overview)
3. [User Personas](#3-user-personas)
4. [Technical Architecture](#4-technical-architecture)
5. [Functional Requirements](#5-functional-requirements)
6. [Data Assets](#6-data-assets)
7. [Linguistic Engine Specification](#7-linguistic-engine-specification)
8. [Web Application Requirements](#8-web-application-requirements)
9. [Knowledge Graph (RungusGraph)](#9-knowledge-graph-rungusgraph)
10. [Automation & Cron Jobs](#10-automation--cron-jobs)
11. [Non-Functional Requirements](#11-non-functional-requirements)
12. [Known Gaps & Open Issues](#12-known-gaps--open-issues)
13. [Roadmap](#13-roadmap)
14. [Relevant Skills & Tooling](#14-relevant-skills--tooling)
15. [Key Personnel](#15-key-personnel)
16. [Appendices](#16-appendices)

---

## 1. Executive Summary

The Rungus Morphological Analyzer is a rule-based computational linguistic tool for the **Rungus language** (ISO 639-3: `drg`), an endangered Austronesian language spoken by the Momogun people of Kudat, Sabah, Malaysia.

**What it does:** Takes any Rungus surface word (e.g. `pinongimotku`) and decomposes it into its morphological constituents — root (`imot`), prefixes (`pinong`), infixes (`-in-`), suffixes, and enclitics (`-ku`) — returning the English gloss for each.

**Current performance:** 96.9% token coverage on a 534,775-token corpus of nine Rungus books — 132x larger lexicon and 2.7x higher coverage than the previous Swarthmore College LING073 transducer. Every parsed verb form is also tagged with its grammatical voice under the four-voice Philippine-type analysis (Kroeger; Dreiheller p.c.).

**Deliverables:** CLI tool, Flask REST API deployed on Vercel, single-page web application (Rungus Computational Workstation), precomputed lexical graph data (RungusGraph), HITL expert review pipeline, and an automatically generated Technical Progress Report PDF.

**Primary collaborator:** Christine Dreiheller (SIL Global) — manages the official Rungus Webonary dictionary, explicitly requested a "hermit crab parser" for root extraction in her prior communication.

---

## 2. Product Overview

### 2.1 Problem Statement

Rungus is a **highly agglutinative** Austronesian language. A single root can produce hundreds of surface forms through combinations of:

- **11+ categories of prefixes** (intransitive, transitive, causative, perfect, realisation, plural, intensifier, stative, imperative, collective, perfective)
- **4 types of suffixes** (verbal, nominal, circumfixal, imperative)
- **3 infixes** (aspectual markers inserted after the root-initial consonant)
- **14 enclitics** (pronominal and aspectual particles appended to the final word)

A dictionary lookup alone fails for **over 80% of words** in running text because the root is hidden under affixation and morphophonological transformations (consonant substitution, vowel contraction, reduplication). Existing computational tools (Swarthmore LING073 FST) cover only 100 stems.

### 2.2 Solution

A heuristic morphological analyzer that:

1. Systematically strips affixes in linguistic order (enclitic → infix → prefix → suffix)
2. Applies reverse morphophonological rules (consonant reverse-substitution, vowel de-contraction, reduplication decomposition)
3. Cross-references the resulting candidate root against a 12,555-entry dictionary
4. Resolves subentries to canonical parent roots
5. Returns a structured breakdown with per-morpheme gloss and confidence score

### 2.3 Core Objectives

| # | Objective | Metric | Current Status |
|---|-----------|--------|----------------|
| 1 | High token coverage on real Rungus text | ≥95% | **96.9%** ✅ |
| 2 | Accurate root identification | Precision ≥90% | ~85% (estimated) |
| 3 | Usable web interface for non-technical linguists | Available at URL | ✅ Vercel deployed |
| 4 | Comprehensive test suite preventing regressions | ≥200 tests | **158 tests** |
| 5 | Dictionary gap identification and patching | Mechanism exists | ✅ STANDALONE_WORDS + VIRTUAL_ROOTS + custom_vocab.json |
| 6 | Human-in-the-loop review workflow | Pipeline exists | ✅ hitl_pipeline.py |

---

## 3. User Personas

### 3.1 Christine (Linguist at SIL Global)

- **Needs:** Enter any Rungus word → get root + affix breakdown + English gloss
- **Expertise:** Native/near-native Rungus, formal linguistics training, familiar with FLEx
- **Pain points:** Dictionary doesn't list derived forms; manual root extraction is tedious
- **Success criteria:** Analyzer saves her team time, produces linguistically sound analyses she can validate

### 3.2 Aifven (Developer & Language Learner)

- **Needs:** Build and maintain the analyzer; demonstrate competence for university admissions
- **Expertise:** Python, web development, limited Rungus proficiency
- **Pain points:** Dictionary gaps, morphophonological edge cases, Cloudflare blocks on Webonary
- **Success criteria:** Working product that Christine uses, strong portfolio piece for Imperial/Stanford

### 3.3 Rungus Community Members (Future)

- **Needs:** Translate Rungus ↔ English, look up word meanings, read analyzed texts
- **Expertise:** Native speakers (varying literacy levels), digital literacy varies
- **Success criteria:** Simple, fast, mobile-friendly translator

### 3.4 AI Agent (Future Maintainers)

- **Needs:** Rapid onboarding — understand project structure, linguistic rules, current state
- **Success criteria:** This PRD + HANDOFF.md + clear file layout enable pickup without reading 30+ sessions of history

---

## 4. Technical Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CORE ENGINE                                 │
│  ┌──────────────────────────────────────┐  ┌──────────────────┐ │
│  │        rungus_analyzer_lib.py        │  │mainDataset_merged│ │
│  │  (1,617 lines — single source of     │  │ .json            │ │
│  │   truth for all linguistic rules)    │  │ 12,555 entries   │ │
│  │                                     │  │                  │ │
│  │  Affix databases (PREFIXES,         │  │ + STANDALONE_    │ │
│  │  SUFFIXES, INFIXES, ENCLITICS)      │  │   WORDS          │ │
│  │  SUBSTITUTION_MAP (6-way C→nasal)   │  │ + VIRTUAL_ROOTS  │ │
│  │  VOWEL_CONTRACTIONS (5 rules)       │  │ + LOANWORDS      │ │
│  │  decontract_vowel()                 │  │ + PROPER_NAMES   │ │
│  │  reverse_substitute()               │  │ + FUNCTION_WORDS │ │
│  │  detect_reduplication()             │  │ + custom_vocab   │ │
│  │  resolve_to_parent()                │  │                  │ │
│  │  analyze() → structured result      │  │                  │ │
│  │  generate() → surface form          │  │                  │ │
│  └──────────────────┬───────────────────┘  └──────────────────┘ │
└─────────────────────┼───────────────────────────────────────────┘
                      │
    ┌─────────────────┼────────────────────┐
    │                 │                    │
    ▼                 ▼                    ▼
┌──────────┐  ┌──────────────┐  ┌──────────────────┐
│ CLI      │  │ Flask API    │  │ precompute_graph_ │
│ analyzer │  │ (api/index   │  │ data.py →         │
│ .py      │  │  .py)        │  │ graph_data.json   │
│          │  │              │  │ (5.7 MB)          │
│ Demo +   │  │ /api/analyze │  └──────────────────┘
│ single-  │  │ /api/batch   │
│ word     │  │ /api/stats   │
│ analysis │  │ /api/health  │
└──────────┘  │ /api/generate │
              └──────┬───────┘
                     │
                     ▼
              ┌──────────────┐
              │ index.html   │
              │ Web Frontend │
              │ (Workstation │
              │  UI)         │
              └──────────────┘
```

### 4.1 File Inventory

| File | Size | Lines | Purpose |
|---|---|---|---|
| `rungus_analyzer_lib.py` | 82 KB | 1,617 | Core library — all linguistic rules, affix DB, dictionary loading, analyze/generate |
| `rungus_analyzer.py` | 7 KB | ~220 | CLI wrapper — interactive demo + single-word analysis |
| `api/index.py` | 27 KB | 758 | Flask REST API — 5 endpoints, Vercel-deployed |
| `index.html` | 49 KB | 1,532 | Single-page web app — Minimalist Dark design |
| `precompute_graph_data.py` | 8.3 KB | ~200 | Builds RungusGraph indices |
| `analyze_books.py` | 12 KB | ~350 | Corpus analysis — token coverage, HITL review queue export |
| `generate_report_pdf.py` | 14 KB | 296 | PDF report generator for Christine |
| `hitl_pipeline.py` | 5 KB | ~150 | Human-in-the-loop review workflow |
| `tests/test_analyzer.py` | — | — | 158 pytest test cases |
| `export_web_dict.py` | 2 KB | — | Exports lightweight dictionary.json for web |
| `convert_allentries.py` | 5 KB | — | allEntries → mainDataset conversion |
| `patch_subentries.py` | 12 KB | — | Subentry linking fixes |
| `requirements.txt` | — | 3 lines | flask, flask-cors, gunicorn |

### 4.2 Scraping Scripts

| File | Purpose | Status |
|---|---|---|
| `scrape_full.py` | Original full Webonary scrape (Playwright) | ✅ Worked initially, Cloudflare blocks |
| `scrape_full_v2.py` | Updated scrape with better bypass attempts | ⚠️ Untested in automated mode |
| `scrape_obscura.py` | Obscura headless browser scrape attempt | ⚠️ Untested |
| `scrape_m_letter.py` | M-letter specific rescrape | ✅ Used |
| `scrape_m_remainder.py` | M-letter remainder rescrape | ✅ Used |
| `scrape_minor_entries.py` | Minor entries rescrape | ✅ Used |

### 4.3 Configuration

```json
// vercel.json (project root)
{
  "builds": [{ "src": "api/index.py", "use": "@vercel/python" }],
  "routes": [
    { "src": "/api/(.*)", "dest": "api/index.py" },
    { "src": "/(.*)",     "dest": "rungus-analyzer-web/$1" }
  ]
}
```

**Live URL:** `https://rungus-analyzer.vercel.app/`

---

## 5. Functional Requirements

### 5.1 F-ANALYZE: Morphological Analysis

**Input:** A Rungus word string (e.g. `"pinongimotku"`, `"nokolohing"`, `"mamamanau"`)

**Output (structured JSON):**

```json
{
  "word": "pinongimotku",
  "matched": true,
  "root": "imot",
  "root_gloss": "see, find",
  "prefix": "pinong",
  "prefix_meaning": "causative past (vowel-initial)",
  "infix": "in",
  "infix_meaning": "past / perfective marker",
  "suffix": null,
  "enclitic": "ku",
  "enclitic_meaning": "my / I (1sg)",
  "confidence": 0.8,
  "proper_name": false,
  "loanword": false,
  "reduplication": null,
  "breakdown": [
    "enclitic: -ku = my / I (1sg)",
    "infix: -in-  = past / perfective marker",
    "prefix: pinong = causative past (vowel-initial)",
    "root candidate: 'imot'"
  ]
}
```

**Analysis order of operations:**
1. Strip enclitics (outermost morphemes — `-ku`, `-nu`, `-no`, etc.)
2. Direct dictionary lookup (skip if matched entry is a subentry)
3. Detect reduplication (full hyphenated `agas-agas` → base `agas`; CV-prefix `mamamanau` → base `mamanau`)
4. Strip infixes (`-in-`, `-um-`, `-inum-`)
5. Strip prefixes with reverse consonant-substitution and vowel de-contraction
6. Strip suffixes
7. Prefix + suffix combination search (e.g. circumfix `ko-...-o`)
8. Fallback: subentry parent resolution via `resolve_to_parent()`
9. Fallback: VIRTUAL_ROOTS lookup
10. Return result

### 5.2 F-GENERATE: Surface Form Generation

**Input:** Root + affix selections

**Output:** Surface form with morphophonological rules applied forward

### 5.3 F-BATCH: Batch Analysis

**Input:** Array of up to 100 words

**Output:** Array of analysis results (parallel, same order)

### 5.4 F-HITL: Human-in-the-Loop Review

- Export top-N unknown words from corpus analysis to CSV
- Each row: word, context snippet, frequency, suggested analysis
- Import validated analyses via `custom_vocab.json`

### 5.5 F-GRAPH: Lexical Network

- Precompute affix→root and root→affix indices
- Store in `graph_data.json` (5.7 MB)
- Enable future interactive visualisation

---

## 6. Data Assets

### 6.1 Dictionary Datasets

| Dataset | Entries | Size | Status |
|---|---|---|---|
| `mainDataset_merged.json` | 12,555 headwords + 5,623 subentries | 5.2 MB | **Active** — used by analyzer |
| `mainDataset.json` | ~12,136 | 5.0 MB | Raw scraped (baseline) |
| `mainDataset_clean.json` | ~12,136 | 5.0 MB | After cleaning/formatting fixes |
| `allEntries.json` | 12,530 | 5.0 MB | Full dataset with subentries |
| `minor_entries.json` | ~1,200 | 3.5 MB | Lower-priority entries |

**Dictionary quality metrics:**
- Senses: 12,023
- Example sentences: 4,126
- Senses missing English gloss: **1,050** (high-priority gap)
- Unique headwords: 12,539

**Sources:** Webonary.org/rungus (SIL), scraped via Playwright/Brave with Cloudflare bypass

### 6.2 Corpus

| Source | Files | Tokens | Genre |
|---|---|---|---|
| Tangon_do_Rungus_A4 | `book_1.json` | ~61 KB text | Folk tales |
| Tangon_I_Kurodong | `book_2.json` | ~33 KB text | Folk tales |
| Panarangan_di_Kitab_Laid I–II | `book_3.json`, `book_4.json` | ~804 KB | Biblical commentary |
| Panarangan_di_Kitab_Vagu I–III | `book_5.json`–`book_7.json` | ~1.8 MB | Biblical commentary |
| Teologia PCS | `book_8.json`, `book_9.json` | ~618 KB | Theology |
| **Total** | **9 files** | **534,775 tokens** | **Religious + folk tales** |

**Domain bias:** 7/9 books are biblical/theological texts from EBFO.de (German mission organisation). Vocabulary skews toward religious/spiritual terms.

### 6.3 External Linguistic Resources

| Resource | Source | Contents |
|---|---|---|
| **Forschner Grammar PDF** | ebfo.de/rungus/Rungus-Grammar_A4.pdf | 87-page grammar (1994) — authoritative reference |
| **Root Registry PDF** | ebfo.de/rungus/Rungus_Roots_A4.pdf | ~1,000+ root words — **not yet cross-referenced** |
| **English-Rungus Dictionary PDF** | ebfo.de — A4.pdf | Bilingual dictionary |
| **Teach Yourself Rungus PDF** | ebfo.de — 2014 | Language learning lessons |
| **Rungus Language Corpus** | github.com/devennn/rungus-language-corpus | 1,927 unique words, parallel sentences, frequency CSVs (MIT) |
| **Swarthmore LING073** | wikis.swarthmore.edu/ling073/Rungus | Student FST — 100 stems, 14 twol rules |
| **Christine's Podcast Transcript** | Local | German interview — Rungus identity, land rights, Christian conversion |

---

## 7. Linguistic Engine Specification

### 7.1 Morphophonological Rules

All rules are implemented in `rungus_analyzer_lib.py` based on **Forschner (1994)** — *Outline of a Momogun Grammar (Rungus Dialect)*.

#### Rule MR1: Consonant Substitution (§1.43)

When actor-focus prefixes attach to voiceless-C or /b/-initial roots, the initial consonant is replaced by a homorganic nasal.

| Surface initial | Possible original roots | Example |
|---|---|---|
| `m` | `m`, `p`, `v`, `b` | `manau` ← `panau` |
| `n` | `n`, `t`, `s` | `napit` ← `tapit` |
| `ng` | `ng`, `k` | `ngama` ← `kama` |

#### Rule MR2: Nasal Addition (§1.43)

For voiced consonants (`d, g, h, r, l, z, j, y, w`), a nasal is prepended — no substitution. E.g.: `mongo-` + `duat` → `mongoduat`.

#### Rule MR3: Vowel Contraction (§1.21–1.22)

| Prefix vowel + stem vowel | Result | Example |
|---|---|---|
| a + i | e | — |
| o + i | e | po + imot → pemot |
| o + u | u | ongo + ulun → ongulun |
| a + a | a | manga + anak → manganak |
| o + o | o | — |

#### Rule MR4: Reverse Vowel De-Contraction

When analysis strips a vowel-ending prefix and the remainder starts with a consonant, try prepending vowels in priority order based on the prefix's terminal vowel.

#### Rule MR5: Reduplication (§2.51–2.52)

- **Full hyphenated:** `agas-agas` → base `agas`
- **CV-prefix reduplication:** `mamamanau` = `ma` + `mamanau` → base `mamanau`
- Guards: 2-char repeats only allowed if in valid CV set; `ma`/`mo` require triple repeat (`mamamanau`) to avoid false positives on normal prefixed forms (`mamanau`)

#### Rule MR6: Vowel Harmony (Dreiheller p.c. 6 July 2026) — NEW in v3.1

When a suffix attaches to a root whose final vowel is high (/u/ or /i/), root /a/ shifts to /o/: `aparu → koporuo, oporuan`; `ganti → gontian`; `janji → jonjizon`. Reversed in `_phonological_variants()`, including two-rule compositions (`jonjizon` → glide strip → harmony reversal → `janji`).

#### Rule MR7: Glide Insertion — NEW in v3.1 (generalised)

Root-final /i/ takes /z/, root-final /u/ takes /v/ before a vowel-initial suffix: `janji + -on → jonjizon`, `ko- + sundu + -o → kosunduvo`.

#### Rule MR8: L/R/D Alternation (Dreiheller p.c.) — NEW in v3.1

L and R interchange root-finally (`sikul → posikuron`, `habal → habaran`); after a nasal both become D (`ralan → endalanan`, `araat → mongindaraat`).

#### Voice System (Kroeger; Dreiheller p.c.) — NEW in v3.1

Every parse is tagged with one of the four Philippine-type voices via `derive_voice()`:
agent (`mAN-`/`pAN-`/`-um-`), undergoer (`-on`, past `-in-`), beneficiary/locative (`-an`, past `-in-…-an`), conveyance/"mobile object" (`i-`, `ni-`). Result fields: `voice`, `voice_meaning`. kA-…-o / kA-…-an nominal circumfixes are excluded from voice tagging, and kA- glosses record the polysemy "can / just now / come to pass".

### 7.2 Affix Database

**Prefixes:** 42 entries across 15 categories (incl. object-focus i-/ni-, potential toro-, past e-variant en-) — intransitive, transitive, perfect/accidental, causative, past causative, realisation/potential, plural, intensifier, stative, intended, imperative, collective, perfective.

**Suffixes:** 7 entries — verbal (-on, -an, -o, -ai) and nominal (-onon, -anon, -inai).

**Infixes:** 4 entries — `-in-` (past), `-um-` (process), `-inum-` (past process), `-ong-` (plural in verb, rare).

**Enclitics:** 14 entries — pronominal (-ku, -nu, -no, -mo, -dau, -ko, -kou, -zou, -oku, -dati, -dino, -diti) and aspectual (-po, -nopo).

**Circumfix:** `ko-...-o` (abstract noun nominalizer) — detected as prefix + suffix combination.

All sorted longest-first to prevent short-string aliasing.

### 7.3 Lexical Patch System

| Patch Map | Entries | Purpose |
|---|---|---|
| `STANDALONE_WORDS` | 30+ | High-frequency roots missing from Webonary entirely |
| `VIRTUAL_ROOTS` | 9 | Linguistic roots that map to a different dictionary entry |
| `PROPER_NAMES` | 60+ | Biblical, geographic, personal names |
| `LOANWORDS` | 60+ | Malay/Indonesian/Arabic loanwords |
| `FUNCTION_WORDS` | 50+ | Grammatical particles not in dictionary |
| `custom_vocab.json` | Dynamic | HITL-imported user additions |

### 7.4 Coverage Metrics

| Category | Unique Words | % of Unique | Tokens |
|---|---|---|---|
| Direct dictionary match | 1,521 | 8.6% | 130,686 |
| Decomposed via affixes | 10,302 | 58.6% | 152,989 |
| Proper names | 124 | 0.7% | 23,242 |
| Loanwords | 204 | 1.2% | 12,040 |
| Grammatical function words | 44 | 0.3% | 199,333 |
| **Failed (unanalyzed)** | **5,391** | **30.7%** | **16,485** |
| **TOTAL** | **17,586** | **100.0%** | **534,775** |

**Total system token coverage: 96.9%** (518,290 of 534,775 tokens)

**v3.0 → v3.1:** failed unique types −15.8% (6,399 → 5,391); token coverage 96.4% → 96.9% — entirely from implementing Christine's four morphophonological rules (no new dictionary entries added).

### 7.5 Comparison: Swarthmore LING073 vs This Analyzer

| Metric | Swarthmore | This project (v3.0) | Delta |
|---|---|---|---|
| Lexicon size | 100 stems | 13,234 entries | **132x** |
| Corpus coverage | 35.8% | 96.9% | **+61.1 pp** |
| Reduplication | No | Yes | **New** |
| Glottal stop normalisation | No | Yes | **New** |
| Proper name detection | No | Yes | **New** |
| Loanword detection | No | Yes | **New** |
| Web REST API | No | Yes (Vercel) | **New** |
| Test suite | No | 158 pytest cases | **New** |
| Voice-system tagging (4 voices) | No | Yes | **New v3.1** |
| Vowel harmony / L-R-D rules | No | Yes | **New v3.1** |

---

## 8. Web Application Requirements

### 8.1 Frontend (`rungus-analyzer-web/index.html`)

**Design system:**
- **Theme:** Minimalist Dark
- **Background:** `#0A0A0F` (deep charcoal)
- **Accent:** `#F59E0B` (amber) with rgba(245, 158, 11, 0.15) muted variant
- **Card style:** Glass-morphism — `rgba(26, 26, 36, 0.6)` with `rgba(255, 255, 255, 0.08)` borders
- **Typography:** Space Grotesk (display), Inter (body), JetBrains Mono (code)

**Morpheme colour coding:**

| Morpheme | Colour | Hex |
|---|---|---|
| Prefix | Cyan | `#00b4d8` |
| Root | Mint | `#00f5d4` |
| Suffix | Amber | `#ff9f1c` |
| Infix | Magenta | `#ff006e` |
| Enclitic | Purple | `#8338ec` |

**Tabs / panels:**
1. **Sentence Tab** — Single-word analysis with visual morpheme breakdown
2. **Batch Tab** — Multi-word batch processing with export-to-CSV
3. **Generator Tab** — Build surface form from root + affix selections
4. **Statistics Tab** — Dictionary size, version, coverage info

### 8.2 Backend API (`api/index.py`)

**Endpoints:**

| Method | Path | Description | Rate Limit |
|---|---|---|---|
| POST | `/api/analyze` | Single-word analysis | 50/min |
| POST | `/api/batch` | Batch analysis (max 100 words) | 10/min |
| GET | `/api/stats` | Dictionary metadata | 100/min |
| GET | `/api/health` | Health check | 100/min |
| POST | `/api/generate` | Surface form generation | 50/min |

### 8.3 Deployment

- **Platform:** Vercel (serverless Python runtime)
- **URL:** `https://rungus-analyzer.vercel.app/`
- **Entry:** `api/index.py` (Flask app)
- **Static:** Serving `rungus-analyzer-web/` at root path
- **Config:** `vercel.json` at project root

---

## 9. Knowledge Graph (RungusGraph)

### 9.1 Current Implementation

`precompute_graph_data.py` generates `rungus-analyzer-web/graph_data.json` (5.7 MB) containing:

| Index | Records | Structure |
|---|---|---|
| `affixes` | ~55 | name, type, category, meaning, sub_type |
| `affix_index` | per-affix | [{ root, gloss, count }] — all roots reachable via each affix |
| `root_index` | per-root | [{ affix, type, category, meaning, count }] — all affixes attachable to each root |
| `collocations` | per-word | [{ collocate, count }] — bigram statistics from corpus |
| `stats` | — | dictionary size, corpus size, version |

### 9.2 Graph Semantics (Proposed)

This is a **lexical derivational network**, not an educational prerequisite graph. Edge types:

| Edge | Source → Target | Semantics |
|---|---|---|
| `derives_from` | Surface form → Root | Morphological derivation |
| `affix_type` | Surface form → Affix | Which affix is attached |
| `phonological_rule` | Surface form → Rule | Which rule transformed the root (substitution, contraction, reduplication) |
| `collocates_with` | Word → Word | Statistical bigram co-occurrence |

### 9.3 Future Visualisation Requirements

- Interactive D3.js / vis.js graph explorer
- Click a root → show all derived forms
- Click an affix → show all roots it attaches to
- Filter by affix category (transitive, causative, etc.)
- Search with autocomplete
- Export subgraph as JSON

---

## 10. Automation & Cron Jobs

### 10.1 Currently Active Cron Jobs

None for the Rungus project. Existing active jobs are for Obsidian math vault, algebra sprint, flow zone diagnostic, and Utski vault management.

### 10.2 Required Cron Jobs

| Job ID | Name | Schedule | Script / Prompt | Deliver | Purpose |
|---|---|---|---|---|---|
| `rungus-coverage` | Coverage Regression Check | Weekly Sun 08:00 | `python3 analyze_books.py` | local | Catch regressions after analyzer changes |
| `rungus-deploy-health` | Deploy Health Check | Daily 09:00 | `curl -f https://rungus-analyzer.vercel.app/api/health` | local | Alert if Vercel deployment is down |
| `rungus-scrape-monitor` | Webonary Scrape Check | Weekly Mon 09:00 | Partial scrape → compare entry count | local | Detect dictionary changes on Webonary |
| `rungus-missing-miner` | Missing Words Mining | Weekly Sat 10:00 | Run corpus → extract top-N unknown → HITL flag | local | Drive coverage upward continuously |

### 10.3 Pipeline Automation

| Step | Tool | Frequency |
|---|---|---|
| New word discovered | Manual / HITL | As needed |
| Add to STANDALONE_WORDS | Edit `rungus_analyzer_lib.py` | Manual |
| Run test suite | `pytest tests/ -v` | After every change |
| Export web dictionary | `python3 export_web_dict.py` | After dictionary changes |
| Precompute graph data | `python3 precompute_graph_data.py` | After analyzer changes |
| Deploy to Vercel | `vercel deploy --prod` | After verified changes |
| Email Christine | Manual | Major milestones |

---

## 11. Non-Functional Requirements

### 11.1 Performance

| Metric | Target | Current |
|---|---|---|
| Single-word analysis latency | <100ms | <50ms ✅ |
| Batch (100 words) | <500ms | ~200ms ✅ |
| Corpus coverage (full 534K corpus) | >95% | 96.4% ✅ |
| Dictionary load time | <2s | <1s ✅ |
| Frontend initial load | <3s | ~1s ✅ |

### 11.2 Reliability

- **Test coverage:** ≥80% of linguistic rules covered by pytest
- **Graceful degradation:** If dictionary fails to load, return meaningful error message
- **Vercel cold starts:** API responds within 2s even after idle period
- **No data loss:** Dictionary JSON is read-only; all user patches go through lexical patch maps or custom_vocab.json

### 11.3 Maintainability

- Single source of truth: `rungus_analyzer_lib.py` contains ALL linguistic rules
- CLI, web API, and graph builder all import the same library
- Lexical patches isolated in named dicts (not inline magic values)
- VIRTUAL_ROOTS pattern enables dictionary gap fixes without modifying the JSON
- Clear separation: data (`mainDataset_merged.json`) vs rules (`rungus_analyzer_lib.py`) vs UI (`index.html`)

### 11.4 Security

- No authentication on the Vercel-deployed API (read-only analysis endpoints)
- Dictionary JSON contains only public Webonary data
- No user accounts, no PII stored
- Cloudflare bypass scripts stored locally, not deployed

---

## 12. Known Gaps & Open Issues

### 12.1 High Priority

| ID | Issue | Area | Impact | Proposed Fix |
|---|---|---|---|---|
| G-001 | 6,399 unique words (36.4%) still unanalyzed | Coverage | 3.6% token volume = 19,013 tokens | Frequency-sort, add top-500 to STANDALONE_WORDS, validate via HITL |
| G-002 | 1,050 senses missing English gloss | Dictionary | Users get empty definitions | Flag for manual annotation; can be community task for Christine's team |
| G-003 | Webonary scrape is fragile (Cloudflare) | Data pipeline | Cannot refresh dictionary | Use Obscura headless (serve --stealth) or visible Chrome + CDP + manual click |
| G-004 | No automated regression testing on corpus | QA | Rule changes can silently break coverage | Cron job: weekly coverage check |

### 12.2 Medium Priority

| ID | Issue | Area | Proposed Fix |
|---|---|---|---|
| G-005 | False positives: analyzer confidently returns wrong root | Accuracy | Add semantic disambiguation (context-aware scoring, bigram priors) |
| G-006 | ko-...-o circumfix detection is heuristic | Accuracy | Formalise as circumfix pair in affix DB with weighted scoring |
| G-007 | Subentry parent resolution unvalidated for all 5,623 subentries | Data quality | Run `resolve_to_parent()` on every subentry, log failures |
| G-008 | Root Registry PDF not cross-referenced | Dictionary | OCR the PDF, diff against dictionary, add missing roots |
| G-009 | CV-prefix reduplication guards hardcoded | Maintainability | Move allowed-CV set to a data structure; source from Forschner |
| G-010 | No interactive graph visualisation | UI | Build D3.js explorer from `graph_data.json` |

### 12.3 Low Priority

| ID | Issue | Area | Proposed Fix |
|---|---|---|---|
| G-011 | No AGENTS.md / Claude.md for AI onboarding | DevX | Create onboarding brief (this PRD partially fulfils) |
| G-012 | Test suite covers 136 cases but no negative testing | QA | Add tests for words that SHOULD fail |
| G-013 | Custom_vocab.json has no schema validation | Data quality | Add JSON schema + validator |
| G-014 | No mobile-responsive optimisation | UI | Audit `index.html` for mobile breakpoints |
| G-015 | Dark theme only — no light mode option | UI | Add CSS `prefers-color-scheme: light` variant |

---

## 13. Roadmap

### Phase A: Stabilise & Maintain (1-2 weeks)

| Task | Effort | Dependencies | Success criteria |
|---|---|---|---|
| A1. Fix Webonary scraper (Obscura or human-assisted) | 2-3h | Obscura installed | Can scrape at least one letter page end-to-end |
| A2. Add cron jobs (coverage check + deploy health) | 1h | — | Jobs created and run successfully |
| A3. Validate all 5,623 subentry parent links | 1h | — | 0 broken parent references |
| A4. Run full test suite, fix any regressions | 1-2h | — | 136 tests passing |

### Phase B: Capacity Expansion (2-4 weeks)

| Task | Effort | Dependencies | Success criteria |
|---|---|---|---|
| B1. OCR Root Registry PDF → cross-reference | 3-4h | — | +50-200 missing roots added to STANDALONE_WORDS |
| B2. Patch 1,050 missing English glosses | 4-6h | B1 | Dictionary offers English for all entries |
| B3. Mine top-500 unanalyzed words from 6,399 | 2-3h | — | 500 new STANDALONE_WORDS → coverage >97% |
| B4. Export web dictionary + redeploy | 1h | B1, B2, B3 | New data live on Vercel |

### Phase C: Web App Maturity (4-6 weeks)

| Task | Effort | Dependencies | Success criteria |
|---|---|---|---|
| C1. Interactive RungusGraph explorer | 8-12h | graph_data.json exists | Click root → see derived forms, click affix → see roots |
| C2. Generator panel in web UI | 4-6h | — | Select root + affixes → see surface form |
| C3. Confidence scoring improvements | 6-8h | — | False positive rate <10% |
| C4. Mobile-responsive audit | 2-3h | — | Passes Lighthouse mobile audit |

### Phase D: Advanced Features (6-12 weeks)

| Task | Effort | Dependencies | Success criteria |
|---|---|---|---|
| D1. Finite-State Transducer (PyFoma) | 20-30h | C3 | Bidirectional analysis/generation via formal FST |
| D2. FLEx export format | 4-6h | D1 | Christine can import analyses into FLEx |
| D3. Local LLM disambiguation | 10-15h | D1 | Ambiguous cases resolved with >80% accuracy |
| D4. Community validation portal | 20-30h | D3 | Rungus speakers can validate/suggest via web UI |

---

## 14. Relevant Skills & Tooling

### 14.1 Hermes Skills

| Skill | Relevance | When to load |
|---|---|---|
| `knowledge-graph` | Graph infrastructure, JSON format, D3.js patterns | When building RungusGraph visualisation |
| `web-scraping-cloudflare` | Cloudflare bypass escalation ladder | When scraping Webonary |
| `human-assisted-browser-auth` | Manual captcha handoff workflow | When automated bypass fails |
| `morphological-analyzer` | Rule-based analyzer design patterns | Any morphological work (same domain) |
| `obsidian-knowledge-graph` | If building Rungus Obsidian vault of linguistic notes | Knowledge management use case |
| `prerequisite-mining` | Concept mining approach — repurposable for derivational relations | Expanding graph |
| `systematic-debugging` | 4-phase root cause analysis | Debugging analyzer failures on specific words |
| `subagent-driven-development` | Parallel dispatch for corpus-wide testing | Large batch analysis runs |
| `spike` | Throwaway experiments | Testing new affix rules or scrape approaches |
| `test-driven-development` | RED-GREEN-REFACTOR | Adding new morphological rules |

### 14.2 Dependencies

| Package | Used by | Purpose |
|---|---|---|
| `flask==3.1.1` | `api/index.py` | REST API |
| `flask-cors==5.0.1` | `api/index.py` | Cross-origin requests |
| `gunicorn==23.0.0` | Vercel | WSGI server |
| `pytest` | Tests | Test framework |
| `fpdf2` | `generate_report_pdf.py` | PDF generation |
| `openai-whisper` / `faster-whisper` | Local | Christine's podcast transcription |
| `playwright` | Scraping scripts | Webonary browser automation |
| `obscura` | Scraping attempts | Cloudflare bypass |

---

## 15. Key Personnel

### 15.1 Aifven Nelson (Developer)

- **Background:** Rungus/Momogun descent, from Kg. Pinorat, Kudat, Sabah
- **Education:** A-Levels at KYUEM (Physics, Economics, Further Math, Math) — starting 19 July
- **Rungus proficiency:** Limited — this limitation motivated the project
- **Design preference:** Minimalist Dark (slate/amber), clean, uncluttered
- **Workstyle:** Decisive, expects full-chain ownership (build → verify → update docs/skills), prefers parallel dispatch for large batch work
- **Privacy-sensitive:** Strips tokens/paths from deliverables
- **Date format:** DD/MM/YYYY (Malaysia context)

### 15.2 Christine Dreiheller (Linguist, SIL Global)

- **Email:** christine_dreiheller@sil.org
- **Role:** Manages the official Rungus dictionary on Webonary.org
- **Expertise:** Rungus language documentation, orthography standardisation, translation
- **Key statement:** *"If you had a solution for the hermit crab parser, my team and I would certainly be interested."*
- **Communication history:** Email drafted and sent (v2 in `email_draft_v2.md`), Technical Progress Report PDF generated and shared, live analyzer URL shared (`https://rungus-analyzer.vercel.app/`)
- **Podcast:** German interview about Rungus identity, oral traditions, land rights, Christian conversion — transcribed locally

---

## 16. Appendices

### A. File Tree

```
C:\backup\!programming\RungusTranslator\
│
├── rungus_analyzer_lib.py              ← CORE (1,617 lines, all linguistic rules)
├── rungus_analyzer.py                  ← CLI interface
├── mainDataset_merged.json             ← Active dictionary (12,555 entries, 5.2 MB)
├── mainDataset.json                    ← Raw scraped baseline
├── mainDataset_clean.json              ← Cleaned version
├── allEntries.json                     ← Full conversion with subentries
├── minor_entries.json                  ← Lower-priority entries
│
├── api/
│   └── index.py                        ← Flask API (Vercel entry point)
│
├── rungus-analyzer-web/
│   ├── index.html                      ← Web frontend (Workstation UI)
│   ├── dictionary.json                 ← Lightweight web dictionary
│   ├── graph_data.json                 ← Precomputed graph indices (5.7 MB)
│   ├── wiki-spy.html                   ← Separate graph visualization attempt
│   ├── vercel.json                     ← Vercel deployment config
│   └── requirements.txt                ← Python deps
│
├── precompute_graph_data.py            ← RungusGraph builder
├── analyze_books.py                    ← Corpus analysis engine
├── generate_report_pdf.py              ← PDF report generation
├── hitl_pipeline.py                    ← Human-in-the-loop workflow
│
├── tests/
│   └── test_analyzer.py                ← 136 pytest cases
│
├── data/books/
│   ├── book_1.json .. book_9.json      ← Corpus (534K tokens)
│
├── resources/
│   ├── Rungus-Grammar_A4.pdf           ← Forschner grammar (87p)
│   ├── Rungus_Roots_A4.pdf            ← Root registry
│   ├── English_Rungus_Dictionary_A4.pdf
│   ├── Teach_Yourself_Rungus.pdf
│   └── Tangon_do_Rungus.pdf
│
├── scrape_full.py / scrape_full_v2.py  ← Webonary scrapers
├── scrape_obscura.py                   ← Obscura-based scrape attempt
├── scrape_m_letter.py / scrape_m_remainder.py / scrape_minor_entries.py
│
├── export_web_dict.py                  ← Web dictionary exporter
├── convert_allentries.py               ← Dataset conversion
├── patch_subentries.py                 ← Subentry fixing
├── clean_dataset.py                    ← Dataset cleaning
├── merge_datasets.py                   ← Dataset merging
│
├── email_draft.txt                     ← First email draft to Christine
├── email_draft_v2.md                   ← Second email draft (richer content)
├── email_to_christine.txt              ← Final email sent
├── Technical_Progress_Report.pdf       ← Generated report
│
├── HANDOFF.md                          ← Agent handoff document
├── README.md                           ← Project readme (v3.0 stats)
├── PRD.md                              ← THIS FILE
│
└── scratch/                            ← Temporary test scripts
```

### B. Glossary

| Term | Definition |
|---|---|
| **Root** | The base morpheme carrying the core meaning (e.g. `imot` = "see") |
| **Prefix** | Morpheme attached before the root (e.g. `po-` = causative) |
| **Suffix** | Morpheme attached after the root (e.g. `-on` = patient focus) |
| **Infix** | Morpheme inserted inside the root (e.g. `-in-` = past, inserted after C₁) |
| **Enclitic** | Morpheme appended after all suffixes, phonologically bound (e.g. `-ku` = my) |
| **Circumfix** | Discontinuous affix — prefix + suffix acting as a single morpheme (e.g. `ko-...-o`) |
| **Consonant substitution** | Root-initial C replaced by nasal under prefix influence |
| **Vowel contraction** | Two adjacent vowels at prefix-root boundary merge into one |
| **Reduplication** | Full or partial repetition of a word/base for grammatical meaning |
| **Agglutinative** | Language where words are formed by stringing morphemes together |
| **Hermit crab parser** | Rule-based system that occupies existing lexicons to extract roots |
| **HITL** | Human-in-the-Loop — review pipeline for low-confidence analyses |
| **FST** | Finite-State Transducer — formal model for bidirectional morphology |
| **Token coverage** | % of words in running text the analyzer can successfully process |
| **Webonary** | SIL's web platform for publishing dictionaries (webonary.org) |

### C. Analysis Example Bank

| Surface | Root | Prefix | Infix | Suffix | Enclitic | Gloss |
|---|---|---|---|---|---|---|
| `nokolohing` | lohing | noko- | — | — | — | accidentally entered |
| `monginsan` | insan | mong- | -on- | — | — | to yawn / gape |
| `sinumambayang` | sumambayang | — | -in- | — | — | prayed (past) |
| `pinongimotku` | imot | pinong- | -in- | — | -ku | my was-seen (I inspected) |
| `mamanau` | panau | mo- | — | — | — | walking |
| `mamamanau` | panau | mo- (redup) | — | — | — | walking (habitual) |
| `kosunduvo` | sundu | ko- | — | -o | — | power/spirit (abstract noun) |
| `pemot` | imot | po- | — | — | — | show (causative of see) |
| `ongulun` | ulun | ongo- | — | — | — | people (plural) |
| `agas-agas` | agas | — (redup) | — | — | — | finely divided |

### D. Christine's Email (Summary)

Sent to `christine_dreiheller@sil.org`. Key points communicated:

1. Analyzer achieves **96.4% coverage** on 534K-word corpus of 9 Rungus books
2. Live prototype at `https://rungus-analyzer.vercel.app/`
3. Two categories of errors identified:
   - **False positives** — spelling collisions (e.g. `mamasa` → `basa` vs `pasa`)
   - **kaka- words** — false reduplication stripping (e.g. `kakal` misparsed as `kal`)
   - **ko-...-o circumfix** — distinguishing nominaliser from imperative `-o`
4. Flagged `kosunduvo` + `konoruvo` as systematic circumfix evidence
5. Asked for:
   - Validation of affix inventory
   - Confirmation of `ko-...-o` circumfix rule
   - Any transcriptions/rule books she can share

---

*Generated: 11 July 2026 · For agent onboarding and project reference.*
*Load `morphological-analyzer` and `hermes-agent` skills before working on this project.*
