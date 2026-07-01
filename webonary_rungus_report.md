# Webonary Rungus Dictionary — Technical Report
> **Purpose:** A comprehensive reference for AI models and developers writing scripts to scrape, parse, or interact with the Webonary Rungus Dictionary at `https://www.webonary.org/rungus/`

---

## 1. Overview

The **Rungus Dictionary** is a multilingual dictionary website built on **WordPress** using the **Webonary theme** (developed by SIL Global). It contains:

| Language     | Entries  |
|-------------|---------|
| Rungus (drg) | 12,613  |
| English (en) | 10,005  |
| Malay (zlm)  | 9,457   |

- Last upload: February 12, 2026
- Date published: March 8, 2016
- Base URL: `https://www.webonary.org/rungus/`

The site is a **server-rendered WordPress site** — all data is embedded in HTML. There is no public-facing REST API; `wp-json` endpoints require authentication (returns 401). Standard `requests` scraping is **blocked with 403** for most pages — you must use a real browser (Selenium, Playwright, Puppeteer) or spoof headers carefully.

---

## 2. Language Codes

| Language | Code used in URLs/params |
|----------|--------------------------|
| Rungus   | `drg`                    |
| English  | `en`                     |
| Malay    | `zlm`                    |

---

## 3. Site Structure & URL Map

```
https://www.webonary.org/rungus/                          ← Homepage / Search page
https://www.webonary.org/rungus/?lang=en                  ← UI language switcher (en/drg/ms)

── Overview
   /overview/
   /overview/introduction/
   /overview/foreword/
   /overview/copyright/
   /overview/credits-acknowledgements/
   /overview/alphabet/
   /overview/abbreviations/
   /overview/entries-explained/

── Search (same as homepage, POST via GET form)
   /?s={query}&key={lang_code}
   /?s={query}&key={lang_code}&match_whole_words=1
   /?s={query}&key={lang_code}&match_accents=1

── Browse
   /browse/
   /browse/browse-vernacular-english/              ← Browse Rungus→English→Malay
   /browse/browse-vernacular-english/?key=drg&letter={letter}
   /browse/browse-vernacular-english/?key=drg&letter={letter}&totalEntries={n}&pagenr={page}

   /browse/browse-english-vernacular/             ← Index English→Rungus
   /browse/browse-english-vernacular/?key=en&letter={letter}
   /browse/browse-english-vernacular/?key=en&letter={letter}&totalEntries={n}&pagenr={page}

   /browse/index-malay-rungus/                    ← Index Malay→Rungus
   /browse/index-malay-rungus/?key=zlm&letter={letter}
   /browse/index-malay-rungus/?key=zlm&letter={letter}&totalEntries={n}&pagenr={page}

   /browse/categories/                            ← Semantic Domains
   /browse/categories/?lang={lang}

── Individual Entry Pages
   /{guid}                                        ← e.g. /gf1c42e92-b55a-4903-ab9c-e1caa1816951

── Download
   /download/

── Language
   /language/
   /language/map/
   /language/photo-journal/

── Links
   /links/

── Help
   /help/
   /help/searching/
   /help/browsing/
   /help/downloading/
   /help/dictionary-font/
   /help/about-software/
   /help/contact-us/
```

---

## 4. Search Functionality

### 4.1 Search Form

The search is a standard HTML GET form:

```html
<form action="https://www.webonary.org/rungus" id="searchform" method="get" name="searchform">
  <input type="text" id="s" name="s" />
  <input type="submit" id="searchsubmit" name="search" value="Search" />
  <select name="key">
    <option value="drg">Rungus</option>
    <option value="en">English</option>
    <option value="zlm">Malay</option>
  </select>
  <input type="hidden" name="search_options_set" value="1" />
  <input type="checkbox" id="match_whole_words" name="match_whole_words" value="1" />
  <input type="checkbox" id="match_accents" name="match_accents" />
</form>
```

### 4.2 Search URL Parameters

| Parameter           | Values               | Description                          |
|--------------------|----------------------|--------------------------------------|
| `s`                | string               | The search term                      |
| `key`              | `drg`, `en`, `zlm`  | Language to search in                |
| `match_whole_words`| `1` (or absent)      | Whole-word match (default: on)       |
| `match_accents`    | `1` (or absent)      | Accent/tone sensitive match          |
| `search_options_set`| `1`                 | Hidden field, always include         |

### 4.3 Example Search URLs

```
# Search Rungus for "mata" (whole word, default)
https://www.webonary.org/rungus/?s=mata&key=drg&search_options_set=1&match_whole_words=1

# Search English for "eye" 
https://www.webonary.org/rungus/?s=eye&key=en&search_options_set=1&match_whole_words=1

# Partial match (no whole-word constraint)
https://www.webonary.org/rungus/?s=eye&key=en&search_options_set=1
```

### 4.4 Search Results Page

- Page title format: `Rungus Dictionary » Search Results  »  {query}`
- Results are embedded as `.entry` divs directly in the HTML
- Each page returns up to ~15–25 entries; no pagination links were observed for search (all results appear on one page for moderate result sets)
- The matched term is wrapped in `<span class="highlight">` within entries
- JavaScript: `jQuery("#searchresults").highlight('{term}', 1);` applies visual highlighting

---

## 5. Browse Functionality

### 5.1 Browse Rungus–English–Malay (Main Browse)

**URL:** `/browse/browse-vernacular-english/?key=drg&letter={letter}`

**Available letters (Rungus alphabet):**
`a, b, d, e, g, h, i, j, k, l, m, n, o, p, r, s, t, u, v, w, y, z`  
(Note: no c, f, q, x — Rungus uses a subset of the Latin alphabet)

**Pagination:**
```
/browse/browse-vernacular-english/?key=drg&letter=a&totalEntries=570&pagenr=1
/browse/browse-vernacular-english/?key=drg&letter=a&totalEntries=570&pagenr=2
...
```
- `totalEntries` = total number of entries for that letter (provided by the site)
- `pagenr` = page number (1-based)
- Each page returns approximately **17 entries** (observed: 9 on letter `a` page 1 with sub-entries expanding counts)
- The `totalEntries` and page links appear in `<a href="?letter=a&key=drg&totalEntries=570&pagenr=N">N</a>` elements

### 5.2 English Index

**URL:** `/browse/browse-english-vernacular/?key=en&letter={letter}`

- Uses `.reversalindexentry` divs (not `.entry`)
- Standard A–Z English alphabet
- Same pagination params: `totalEntries`, `pagenr`

### 5.3 Malay Index

**URL:** `/browse/index-malay-rungus/?key=zlm&letter={letter}`

- Same structure as English index — uses `.reversalindexentry`
- Example: letter `a` has `totalEntries=318`

### 5.4 Semantic Domains (Categories)

**URL:** `/browse/categories/`  
UI language variant: `/browse/categories/?lang={en|drg|ms}`

The categories page renders the semantic domain tree. No structured entries were observed in scraping — likely JavaScript-rendered or requires interaction.

---

## 6. HTML Structure — CSS Selectors Reference

### 6.1 Main Entry (Rungus headword page / search results)

```html
<div class="entry left" id="{guid}">
  <span class="mainheadword">
    <span lang="drg">
      <a href="https://www.webonary.org/rungus/{guid}">
        HEADWORD_TEXT
      </a>
    </span>
  </span>

  <span class="senses">
    <span class="sensecontent">
      <span class="sense" entryguid="{guid}">

        <span class="definitionorgloss">
          <span class="writingsystemprefix">BM</span>
          <span lang="zlm">MALAY_DEFINITION</span>
          <span class="writingsystemprefix">Eng</span>
          <span lang="en">ENGLISH_DEFINITION</span>
        </span>

        <span class="examplescontents">
          <span class="examplescontent">
            <span class="example">
              <span lang="drg">RUNGUS_EXAMPLE_SENTENCE</span>
            </span>
            <span class="translationcontents">
              <span class="translationcontent">
                <span class="translation">
                  <span class="writingsystemprefix">BM</span>
                  <span lang="zlm">MALAY_TRANSLATION</span>
                </span>
              </span>
            </span>
          </span>
        </span>

        <span class="lexsensereferences">   <!-- cross-references (synonyms, etc.) -->
          <span class="lexsensereference">
            <span class="ownertype_abbreviation"><span lang="en">syn</span></span>
            <span class="configtargets">
              <span class="configtarget">
                <span class="headword-14">
                  <span lang="drg"><a href="...">SYNONYM_WORD</a></span>
                </span>
              </span>
            </span>
          </span>
        </span>

      </span>
    </span>
  </span>

  <span class="subentries">
    <span class="subentry mainentrysubentry">
      <span class="headword-6">
        <span lang="drg"><a href="...">COMPOUND_FORM</a></span>
      </span>
      <!-- senses-3, examplescontents-3, etc. for sub-entries -->
    </span>
  </span>
</div>
```

**Key CSS selectors for main entries:**

| Selector | Description |
|----------|-------------|
| `.entry` | Top-level entry container |
| `.entry[id]` | Entry ID = GUID |
| `.mainheadword [lang="drg"]` | Main headword text (Rungus) |
| `.mainheadword a` | Link to individual entry page |
| `.sense` | Sense block; `entryguid` attr links back to entry |
| `.definitionorgloss [lang="en"]` | English definition/gloss |
| `.definitionorgloss [lang="zlm"]` | Malay definition/gloss |
| `.example [lang="drg"]` | Rungus example sentence |
| `.translation [lang="en"]` | English translation of example |
| `.translation [lang="zlm"]` | Malay translation of example |
| `.subentry` | Sub-entry / compound form |
| `.headword-6 [lang="drg"]` | Sub-entry headword |
| `.highlight` | Matched search term (search pages only) |
| `.writingsystemprefix` | Language label ("BM", "Eng") |

**Numbered variants** (used in sub-entries): `.senses-2`, `.senses-3`, `.definitionorgloss-2`, `.definitionorgloss-3`, `.examplescontents-2`, `.examplescontents-3`, `.translation-2`, `.translation-3`, etc.

### 6.2 Entry ID / GUID

Each entry has a UUID-style GUID:
- Format: `g{8hex}-{4hex}-{4hex}-{4hex}-{12hex}` (prefixed with `g`)
- Example: `gf1c42e92-b55a-4903-ab9c-e1caa1816951`
- Used as: `div#id`, `span[entryguid]`, and the URL path `/rungus/{guid}`

### 6.3 English / Malay Reversal Index Entries

```html
<div class="reversalindexentry" id="{guid}" nodeid="...">
  <span class="reversalform">
    <span lang="en">ENGLISH_WORD</span>
  </span>
  <span class="sensesrs">
    <span class="sensecontent">
      <span class="sensesr" entryguid="{rungus_entry_guid}" nodeid="...">
        <span class="headword">
          <span lang="drg"><a href="...">RUNGUS_HEADWORD</a></span>
        </span>
        <span class="definitionorgloss">
          <span lang="en">ENGLISH_GLOSS</span>
        </span>
        <span class="examplescontents">...</span>
      </span>
    </span>
  </span>
</div>
```

| Selector | Description |
|----------|-------------|
| `.reversalindexentry` | Top-level reversal index entry |
| `.reversalform [lang="en"]` | The English index word |
| `.reversalform [lang="zlm"]` | The Malay index word |
| `.sensesr` | Sense pointing to a Rungus entry |
| `.sensesr .headword [lang="drg"]` | Rungus headword linked |
| `.sensesr[entryguid]` | GUID of the Rungus entry |

### 6.4 Cross-Reference Types

The `ownertype_abbreviation` span contains short labels for relationship types:
- `syn` = synonym
- `ant` = antonym
- `cf` = compare
- `unspec. comp. form` = unspecified compound form

---

## 7. Individual Entry Pages

**URL:** `https://www.webonary.org/rungus/{guid}`

- Returns a full page with the same `.entry` HTML structure as search results
- The entry is the **same HTML structure** — selectors from §6.1 apply
- Sub-entries link to their own individual pages via their GUIDs
- Cross-reference links point to other entry GUIDs

---

## 8. Pagination Details

### Browse Pagination

Pagination links appear as relative URLs within the browse pages:

```html
<a href="?letter=a&key=drg&totalEntries=570&pagenr=1">1</a>
<a href="?letter=a&key=drg&totalEntries=570&pagenr=2">2</a>
...
```

**To iterate all entries for a letter:**
1. Fetch page 1: `?key=drg&letter=a`
2. Parse `totalEntries` from a pagination link's `href`
3. Calculate total pages: `ceil(totalEntries / entries_per_page)` (entries_per_page ≈ 17–25)
4. Loop through `pagenr=1` to `pagenr=N`

**Extracting totalEntries from HTML (Python):**
```python
import re
from bs4 import BeautifulSoup

soup = BeautifulSoup(html, 'html.parser')
pag_link = soup.select_one('a[href*="totalEntries"]')
if pag_link:
    match = re.search(r'totalEntries=(\d+)', pag_link['href'])
    total = int(match.group(1)) if match else None
```

---

## 9. Scraping Strategy & Code Examples

### 9.1 Requirements

- **Direct `requests` calls return 403** for most pages — use a browser automation tool (Playwright, Selenium) or set realistic headers including cookies
- The site uses **Cloudflare/RSSSL** (`data-rsssl="1"` on body)
- **No rate limiting was encountered during browsing**, but be respectful with delays
- The wp-json REST API requires authentication — **not usable for public scraping**

### 9.2 Recommended Scraping Approach (Playwright/Selenium)

```python
# Pseudocode outline for full Rungus dictionary scrape

BASE = "https://www.webonary.org/rungus"
LETTERS = list("abdeghijklmnoprstuvwyz")  # Rungus alphabet

# Step 1: For each letter, get all entries from Browse page
for letter in LETTERS:
    page = 1
    total_entries = None
    while True:
        url = f"{BASE}/browse/browse-vernacular-english/?key=drg&letter={letter}&pagenr={page}"
        if total_entries:
            url += f"&totalEntries={total_entries}"
        
        # navigate with browser automation
        html = get_page(url)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Get total on first page
        if page == 1:
            pag_link = soup.select_one('a[href*="totalEntries"]')
            if pag_link:
                m = re.search(r'totalEntries=(\d+)', pag_link['href'])
                total_entries = int(m.group(1))
        
        entries = soup.select('.entry')
        if not entries:
            break
        
        for entry in entries:
            guid = entry.get('id')
            headword = entry.select_one('.mainheadword [lang="drg"]').get_text(strip=True)
            en_def = entry.select_one('.definitionorgloss [lang="en"]')
            ms_def = entry.select_one('.definitionorgloss [lang="zlm"]')
            # ... collect sub-entries, examples, etc.
        
        page += 1
        if not soup.select_one(f'a[href*="pagenr={page}"]'):
            break
```

### 9.3 Parsing a Single Entry

```python
def parse_entry(entry_div):
    result = {}
    
    # GUID
    result['guid'] = entry_div.get('id')
    result['url'] = f"https://www.webonary.org/rungus/{result['guid']}"
    
    # Headword
    hw = entry_div.select_one('.mainheadword [lang="drg"]')
    result['headword'] = hw.get_text(strip=True) if hw else None
    
    # Senses (main entry)
    result['senses'] = []
    for sense in entry_div.select('.senses > .sensecontent > .sense'):
        s = {}
        en_gloss = sense.select_one('.definitionorgloss [lang="en"]')
        ms_gloss = sense.select_one('.definitionorgloss [lang="zlm"]')
        s['english'] = en_gloss.get_text(strip=True) if en_gloss else None
        s['malay'] = ms_gloss.get_text(strip=True) if ms_gloss else None
        
        # Examples
        s['examples'] = []
        for ex in sense.select('.examplescontent'):
            example_text = ex.select_one('.example [lang="drg"]')
            en_trans = ex.select_one('.translation [lang="en"]')
            ms_trans = ex.select_one('.translation [lang="zlm"]')
            s['examples'].append({
                'rungus': example_text.get_text(strip=True) if example_text else None,
                'english': en_trans.get_text(strip=True) if en_trans else None,
                'malay': ms_trans.get_text(strip=True) if ms_trans else None,
            })
        result['senses'].append(s)
    
    # Sub-entries
    result['subentries'] = []
    for sub in entry_div.select('.subentry'):
        sub_hw = sub.select_one('.headword-6 [lang="drg"]')
        sub_guid_link = sub.select_one('.headword-6 a')
        result['subentries'].append({
            'headword': sub_hw.get_text(strip=True) if sub_hw else None,
            'guid': sub_guid_link['href'].split('/')[-1] if sub_guid_link else None,
        })
    
    return result
```

### 9.4 Search Scraping

```python
# Search for a term in Rungus
def search(term, lang='drg', whole_word=True):
    params = {
        's': term,
        'key': lang,
        'search_options_set': '1',
    }
    if whole_word:
        params['match_whole_words'] = '1'
    
    url = "https://www.webonary.org/rungus/?" + urlencode(params)
    html = get_page(url)  # use browser automation
    soup = BeautifulSoup(html, 'html.parser')
    return [parse_entry(e) for e in soup.select('.entry')]
```

---

## 10. Notable HTML Patterns & Gotchas

1. **`lang` attributes are your friends.** All multilingual content is separated by `lang="drg"`, `lang="en"`, `lang="zlm"` attributes — use these to extract language-specific text.

2. **Numbered class suffixes** (`.senses`, `.senses-2`, `.senses-3`, etc.) are used to distinguish main entries from sub-entries from compound forms. The suffix `-2` and `-3` appear in sub-entries; avoid double-counting by scoping selectors to the right parent.

3. **`nodeid` attributes** appear on reversal index entries alongside `id`. The `nodeid` is an internal FLEx (FieldWorks) node ID (hex string). The `id` is the GUID to use for linking.

4. **Entry page = search result HTML** — individual entry pages (`/{guid}`) render the same `.entry` div as the browse/search pages, so the same parser works everywhere.

5. **`postentry` class** appears on some entries — this is a WordPress post wrapper and can be ignored; the actual dictionary data is in `.entry`.

6. **`hentry` class** is WordPress microformat and appears on page wrappers, not individual dictionary entries.

7. **`<span class="highlight">` is only on search result pages** — wraps the matched portion of the headword/example on search pages.

8. **`complexformentryref`** and **`primaryentryref`** classes mark cross-references to other entries (e.g., "see also", "main entry").

9. **Status classes** (`status-publish`, `post-NNNNNN`) are WordPress metadata on entry wrappers and don't contain linguistic data.

10. **The Rungus language uses `lang="drg"`** (ISO 639-3 code for Rungus). Malay is tagged as both `lang="zlm"` (written as "BM" = Bahasa Melayu in the UI) and sometimes `lang="ms"`.

---

## 11. Site Navigation Summary

```
Top Nav:
  Overview ▼    Search    Browse ▼    Download    Language ▼    Links ▼    Help ▼

Overview submenu: Introduction, Foreword, Copyright, Credits, Alphabet, Abbreviations, Entries Explained
Browse submenu:   Browse Rungus–English–Malay, Index English–Rungus, Index Malay–Rungus, Semantic Domains
Language submenu: Link to Ethnologue, Map, Photo Journal, Bibliography, OLAC Resources
Links submenu:    Webonary, SIL International site
Help submenu:     Searching, Browsing, Downloading, Dictionary Font, About Software, Contact Us

Language switcher (top right): English | Rungus | Malay
  → Changes UI language via ?lang= query param
```

---

## 12. Quick Reference Cheat Sheet

```
Base URL:          https://www.webonary.org/rungus/
Search:            /?s={query}&key={drg|en|zlm}&match_whole_words=1
Browse Rungus:     /browse/browse-vernacular-english/?key=drg&letter={letter}&pagenr={n}
Browse English:    /browse/browse-english-vernacular/?key=en&letter={letter}&pagenr={n}
Browse Malay:      /browse/index-malay-rungus/?key=zlm&letter={letter}&pagenr={n}
Single Entry:      /{guid}
Categories:        /browse/categories/

Entry selector:            .entry
Entry GUID:                .entry[id] → id attribute
Headword (Rungus):         .mainheadword [lang="drg"]
English definition:        .definitionorgloss [lang="en"]
Malay definition:          .definitionorgloss [lang="zlm"]
Example (Rungus):          .example [lang="drg"]
Example translation (EN):  .translation [lang="en"]
Example translation (MS):  .translation [lang="zlm"]
Sub-entries:               .subentry
Reversal entry (EN/MS):    .reversalindexentry
Reversal form:             .reversalform [lang="en"] or [lang="zlm"]
Rungus word (reversal):    .sensesr .headword [lang="drg"]
Pagination link:           a[href*="pagenr"]
Total entries:             re.search(r'totalEntries=(\d+)', href)
Rungus alphabet:           a b d e g h i j k l m n o p r s t u v w y z
Language codes:            drg (Rungus), en (English), zlm (Malay)
```
