"""
Scrape ALL entries from the 'ng' letter section of the Webonary Rungus Dictionary.

'ng' is a digraph representing a single phoneme in Rungus, but the original
LETTERS list only iterates single characters — so the entire ng- section
was never scraped.

This script collects BOTH:
  - .entry        (main root words, e.g. ngarang, ngawi, ngohogon)
  - .minorentrycomplex  (derived/affixed forms, e.g. mongarang, kingarang)

This avoids the subentry-stub problem: each word gets its full definition
directly rather than just being listed as a headword stub under its parent.

Uses Playwright + Brave (headless=False) — solve Cloudflare manually.

Output: ng_entries.json
Then run: python merge_minor.py   (it handles any JSON in the same format)
Or pass the file directly to a merge step.
"""

import json
import re
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

BASE        = "https://www.webonary.org/rungus"
BROWSE_URL  = f"{BASE}/browse/browse-vernacular-english/"
LETTER      = "ng"                                          # the missing digraph
OUTPUT_FILE = Path(__file__).parent / "ng_entries.json"
STATE_FILE  = Path(__file__).parent / "ng_scrape_state.json"
BRAVE_PATH  = "C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"
DELAY       = 0.8


# ── shared helpers ───────────────────────────────────────────────────────────

def get_title_safe(page):
    try:
        return page.title()
    except:
        return "(navigating)"


def wait_for_cloudflare(page, max_wait=600):
    for i in range(max_wait // 2):
        page.wait_for_timeout(2000)
        title = get_title_safe(page)
        if "Just a moment" not in title and title != "(navigating)":
            print(f"        [+] Cloudflare passed after {i*2}s!")
            page.wait_for_timeout(3000)
            try:
                page.wait_for_load_state("domcontentloaded", timeout=15000)
            except:
                pass
            print(f"        [+] Stabilized. Title: {get_title_safe(page)}")
            return True
        if i == 0 or i % 15 == 0:
            print(f"        Waiting for CF ({i*2}s)... Solve the captcha in Brave")
    return False


def remove_duplicate_suffix(text):
    if not text:
        return text
    def normalize(t):
        return re.sub(r"[^a-zA-Z0-9]", "", t).lower()
    n = len(text)
    for i in range(2, n - 1):
        prefix = text[:i].strip()
        suffix = text[i:].strip()
        if not prefix or not suffix:
            continue
        if normalize(prefix) and normalize(suffix) and normalize(prefix).endswith(normalize(suffix)):
            if len(normalize(suffix)) >= 4:
                return prefix
    return text


def clean_text(text):
    if not text:
        return None
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r",([^\s])", r", \1", text)
    text = re.sub(r";([^\s])", r"; \1", text)
    text = re.sub(r"^[\s,;]+|[\s,;]+$", "", text)
    text = remove_duplicate_suffix(text)
    return re.sub(r"\s+", " ", text).strip() or None


# ── parsers ──────────────────────────────────────────────────────────────────

def parse_main_entry(entry_div):
    """
    Parse a .entry div (main root word).
    Uses .mainheadword and .senses > .sensecontent > .sense
    Subentries are listed by headword only (no full parse — they appear
    separately as .minorentrycomplex on the ng page and will be captured there).
    """
    result = {}
    result["guid"] = entry_div.get("id", "")
    result["url"]  = f"{BASE}/{result['guid']}" if result["guid"] else ""

    hw = entry_div.select_one(".mainheadword [lang='drg']")
    result["headword"] = hw.get_text(strip=True) if hw else None

    result["senses"] = []
    # Use .senses > .sensecontent > .sense  (direct child of .senses only)
    # This avoids picking up sense content from nested .subentry spans.
    for sense in entry_div.select(".senses > .sensecontent > .sense"):
        s = {}
        en_gloss_tags = sense.select(".definitionorgloss [lang='en']")
        ms_gloss_tags = sense.select(".definitionorgloss [lang='zlm']")
        raw_en = "".join(t.get_text() for t in en_gloss_tags).strip() if en_gloss_tags else None
        raw_ms = "".join(t.get_text() for t in ms_gloss_tags).strip() if ms_gloss_tags else None
        s["english"] = clean_text(raw_en)
        s["malay"]   = clean_text(raw_ms)

        s["examples"] = []
        for ex in sense.select(".examplescontents > .examplescontent, .examplescontents-2 > .examplescontent"):
            example_text = ex.select_one(".example [lang='drg'], .example-2 [lang='drg']")
            en_trans_tags = ex.select(".translation [lang='en']")
            ms_trans_tags = ex.select(".translation [lang='zlm']")
            raw_ex_en = "".join(t.get_text() for t in en_trans_tags).strip() if en_trans_tags else None
            raw_ex_ms = "".join(t.get_text() for t in ms_trans_tags).strip() if ms_trans_tags else None
            s["examples"].append({
                "rungus":  example_text.get_text(strip=True) if example_text else None,
                "english": clean_text(raw_ex_en),
                "malay":   clean_text(raw_ex_ms),
            })

        result["senses"].append(s)

    # Subentries: headword names only (stubs).
    # Their full definitions come from .minorentrycomplex parsing below.
    result["subentries"] = []
    for sub in entry_div.select(".subentry"):
        sub_hw = sub.select_one("[class^='headword'] [lang='drg']")
        result["subentries"].append(
            {"headword": sub_hw.get_text(strip=True) if sub_hw else None}
        )

    return result


def parse_minor_entry(entry_div):
    """
    Parse a .minorentrycomplex div (derived/complex form).
    Uses .headword and numbered class variants (.senses-2, .definitionorgloss-2, etc.)
    [class^='X'] selectors match X, X-2, X-3, etc. safely.
    """
    result = {}
    result["guid"] = entry_div.get("id", "")
    result["url"]  = f"{BASE}/{result['guid']}" if result["guid"] else ""

    # Headword: .headword (not .mainheadword) for minor entries
    hw = entry_div.select_one(".headword > [lang='drg']")
    if not hw:
        hw = entry_div.select_one(".headword [lang='drg']")
    result["headword"] = hw.get_text(strip=True) if hw else None

    # Parent root reference
    result["parent"] = None
    parent_node = entry_div.select_one(".nontrivialentryroots [lang='drg']")
    if not parent_node:
        parent_node = entry_div.select_one(".complexformentryrefs .referencedentry [lang='drg']")
    if parent_node:
        result["parent"] = parent_node.get_text(strip=True)

    result["is_minor_entry"] = True

    result["senses"] = []
    # .sensecontent > .sense is safe here because minor entries never nest subentries
    for sense in entry_div.select(".sensecontent > .sense"):
        s = {}
        # [class^='definitionorgloss'] matches .definitionorgloss, .definitionorgloss-2, etc.
        en_gloss_tags = sense.select("[class^='definitionorgloss'] [lang='en']")
        ms_gloss_tags = sense.select("[class^='definitionorgloss'] [lang='zlm']")
        raw_en = "".join(t.get_text() for t in en_gloss_tags).strip() if en_gloss_tags else None
        raw_ms = "".join(t.get_text() for t in ms_gloss_tags).strip() if ms_gloss_tags else None
        s["english"] = clean_text(raw_en)
        s["malay"]   = clean_text(raw_ms)

        s["examples"] = []
        for ex in sense.select(".examplescontent"):
            example_text = None
            for ex_class in ["example", "example-2", "example-3"]:
                example_text = ex.select_one(f".{ex_class} [lang='drg']")
                if example_text:
                    break
            en_trans_tags = ex.select("[class^='translation'] [lang='en']")
            ms_trans_tags = ex.select("[class^='translation'] [lang='zlm']")
            raw_ex_en = "".join(t.get_text() for t in en_trans_tags).strip() if en_trans_tags else None
            raw_ex_ms = "".join(t.get_text() for t in ms_trans_tags).strip() if ms_trans_tags else None
            s["examples"].append({
                "rungus":  example_text.get_text(strip=True) if example_text else None,
                "english": clean_text(raw_ex_en),
                "malay":   clean_text(raw_ex_ms),
            })

        result["senses"].append(s)

    result["subentries"] = []   # minor entries never have subentries
    return result


# ── state helpers ────────────────────────────────────────────────────────────

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"page_nr": 1, "collected": []}


def save_state(page_nr, collected):
    with open(STATE_FILE, "w") as f:
        json.dump({"page_nr": page_nr, "collected": collected}, f)


# ── main ─────────────────────────────────────────────────────────────────────

def scrape_ng():
    state     = load_state()
    collected = state["collected"]
    page_nr   = state["page_nr"]

    print(f"[*] Scraping letter 'ng' (digraph — was missing from original scraper)")
    print(f"[*] Resuming from page {page_nr}  |  already collected: {len(collected)}")
    print(f"[*] Collecting BOTH .entry AND .minorentrycomplex to avoid subentry stubs")
    print(f"[*] Brave: {BRAVE_PATH}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            executable_path=BRAVE_PATH,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context()
        page    = context.new_page()

        # Warm up — solve Cloudflare
        print("[*] Phase 1: Warming up on homepage (solve Cloudflare in the browser)...")
        page.goto(BASE, wait_until="domcontentloaded", timeout=60000)
        if wait_for_cloudflare(page, max_wait=60):
            print("[+] Cloudflare passed!")
        else:
            print("[!] CF did not resolve in warmup. Continuing anyway...")

        print(f"[*] Phase 2: Scraping ng pages...")
        total_entries = None

        while True:
            url = f"{BROWSE_URL}?key=drg&letter={LETTER}&pagenr={page_nr}"
            if total_entries:
                url += f"&totalEntries={total_entries}"

            print(f"    [ng] page {page_nr}  |  collected: {len(collected)}")

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
            except Exception as e:
                print(f"        [!] Navigation error: {e}. Retrying in 10s...")
                time.sleep(10)
                continue

            if "Just a moment" in get_title_safe(page):
                print("        [!] Cloudflare hit. Solve in Brave window...")
                if not wait_for_cloudflare(page):
                    print("        [!] CF timed out. Saving state and stopping.")
                    save_state(page_nr, collected)
                    browser.close()
                    return

            html = page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Get total entries (for URL params on subsequent pages)
            if page_nr == 1 and total_entries is None:
                pag_link = soup.select_one("a[href*='totalEntries']")
                if pag_link:
                    m = re.search(r"totalEntries=(\d+)", pag_link["href"])
                    if m:
                        total_entries = int(m.group(1))
                        print(f"        [ng] total entries reported: {total_entries}")

            main_divs  = soup.select(".entry")
            minor_divs = soup.select(".minorentrycomplex")

            if not main_divs and not minor_divs:
                if "Just a moment" in get_title_safe(page):
                    print("        [!] Still blocked. Retrying...")
                    continue
                print(f"        [i] No entries found — end of ng section.")
                break

            print(f"        found: {len(main_divs)} main + {len(minor_divs)} minor")

            for div in main_divs:
                parsed = parse_main_entry(div)
                if parsed["headword"]:
                    collected.append(parsed)

            for div in minor_divs:
                parsed = parse_minor_entry(div)
                if parsed["headword"]:
                    collected.append(parsed)

            save_state(page_nr, collected)

            # Check if next page exists
            next_link = soup.select_one(f"a[href*='pagenr={page_nr + 1}']")
            if not next_link:
                print(f"        [i] No next page — ng section complete.")
                break

            page_nr += 1
            time.sleep(DELAY)

        browser.close()

    # Write final output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(collected, f, ensure_ascii=False, indent=2)

    main_count  = sum(1 for e in collected if not e.get("is_minor_entry"))
    minor_count = sum(1 for e in collected if e.get("is_minor_entry"))
    print(f"\n[!!!] NG SCRAPE COMPLETE")
    print(f"      Main entries:  {main_count}")
    print(f"      Minor entries: {minor_count}")
    print(f"      Total:         {len(collected)}")
    print(f"      Saved to:      {OUTPUT_FILE}")
    print(f"\n      Next step:  python merge_minor.py  (merge into mainDataset.json)")

    if STATE_FILE.exists():
        STATE_FILE.unlink()


if __name__ == "__main__":
    scrape_ng()
