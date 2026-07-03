"""
Scrape ONLY the .minorentrycomplex entries from Webonary Rungus Dictionary.
These are derived/complex forms (e.g. kosunduvo, miagung, ahabaran) that
the original scraper missed because it only selected .entry divs.

Uses Playwright + Brave (headless=False) so you can manually solve Cloudflare.

Output: minor_entries.json  (~5,500 new entries)
Then run: python merge_minor.py   to merge into mainDataset.json
"""

import json
import re
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

BASE        = "https://www.webonary.org/rungus"
BROWSE_URL  = f"{BASE}/browse/browse-vernacular-english/"
LETTERS     = list("abdeghijklmnoprstuvwyz")   # Rungus alphabet
OUTPUT_FILE = Path(__file__).parent / "minor_entries.json"
STATE_FILE  = Path(__file__).parent / "minor_scrape_state.json"
BRAVE_PATH  = "C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"
DELAY       = 0.8   # seconds between page loads


# ── helpers (copied from scrape_full.py) ────────────────────────────────────

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
            print(f"        [+] Page stabilized. Title: {get_title_safe(page)}")
            return True
        if i == 0 or i % 15 == 0:
            print(f"        Waiting for CF ({i*2}s)... Solve the captcha in the Brave window")
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
        norm_prefix = normalize(prefix)
        norm_suffix = normalize(suffix)
        if norm_prefix and norm_suffix and norm_prefix.endswith(norm_suffix):
            if len(norm_suffix) >= 4:
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
    text = re.sub(r"\s+", " ", text).strip()
    return text if text else None


# ── parser for .minorentrycomplex divs ──────────────────────────────────────

def parse_minor_entry(entry_div):
    """
    Parse a .minorentrycomplex div into a structured entry dict.
    These use different CSS classes than .entry divs:
      - headword:   .headword [lang='drg']     (not .mainheadword)
      - senses:     .senses-2, .senses-3, etc. (numbered variants)
      - glosses:    .definitionorgloss-2, etc.
      - parent:     .nontrivialentryroots or .complexformentryrefs
    """
    result = {}
    result["guid"] = entry_div.get("id", "")
    result["url"]  = f"{BASE}/{result['guid']}" if result["guid"] else ""

    # ── Headword ─────────────────────────────────────────────────────────────
    # minorentrycomplex uses .headword (no "main" prefix)
    hw = entry_div.select_one(".headword > [lang='drg']")
    if not hw:
        hw = entry_div.select_one(".headword [lang='drg']")
    result["headword"] = hw.get_text(strip=True) if hw else None

    # ── Parent reference ─────────────────────────────────────────────────────
    # .nontrivialentryroots = the true linguistic root of this complex form
    # .complexformentryrefs = all the component words (may include particles)
    result["parent"] = None
    parent_node = entry_div.select_one(".nontrivialentryroots [lang='drg']")
    if not parent_node:
        # Fallback: first referenced entry in complexformentryrefs
        parent_node = entry_div.select_one(".complexformentryrefs .referencedentry [lang='drg']")
    if parent_node:
        result["parent"] = parent_node.get_text(strip=True)

    result["is_minor_entry"] = True

    # ── Senses ───────────────────────────────────────────────────────────────
    # minorentrycomplex has no nested subentries, so .sensecontent > .sense
    # safely targets only this entry's own senses (not sub-sub-entries).
    result["senses"] = []
    for sense in entry_div.select(".sensecontent > .sense"):
        s = {}

        # [class^='definitionorgloss'] matches:
        # .definitionorgloss, .definitionorgloss-2, .definitionorgloss-3, etc.
        en_gloss_tags = sense.select("[class^='definitionorgloss'] [lang='en']")
        ms_gloss_tags = sense.select("[class^='definitionorgloss'] [lang='zlm']")

        raw_en = "".join(t.get_text() for t in en_gloss_tags).strip() if en_gloss_tags else None
        raw_ms = "".join(t.get_text() for t in ms_gloss_tags).strip() if ms_gloss_tags else None

        s["english"] = clean_text(raw_en)
        s["malay"]   = clean_text(raw_ms)

        # ── Examples ─────────────────────────────────────────────────────────
        s["examples"] = []
        for ex in sense.select(".examplescontent"):
            # Try .example, .example-2, .example-3 for the Rungus sentence
            example_text = None
            for ex_class in ["example", "example-2", "example-3"]:
                example_text = ex.select_one(f".{ex_class} [lang='drg']")
                if example_text:
                    break

            # [class^='translation'] matches .translation, .translation-2, etc.
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

    result["subentries"] = []   # minor entries never have sub-entries
    return result


# ── state helpers ────────────────────────────────────────────────────────────

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"letter_idx": 0, "page_nr": 1, "collected": []}


def save_state(letter_idx, page_nr, collected):
    with open(STATE_FILE, "w") as f:
        json.dump({"letter_idx": letter_idx, "page_nr": page_nr, "collected": collected}, f)


# ── main scrape loop ─────────────────────────────────────────────────────────

def scrape_minor():
    state   = load_state()
    collected        = state["collected"]
    start_letter_idx = state["letter_idx"]
    start_page_nr    = state["page_nr"]

    print(f"[*] Resuming from letter index {start_letter_idx}, page {start_page_nr}")
    print(f"[*] Already collected: {len(collected)} minor entries")
    print(f"[*] Using Brave browser at: {BRAVE_PATH}")
    print(f"[!] NOTE: This scraper collects ONLY .minorentrycomplex entries (derived/complex forms).")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            executable_path=BRAVE_PATH,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context()
        page    = context.new_page()

        # Warmup pass (solve Cloudflare on homepage)
        print("[*] Phase 1: Warming up (solve Cloudflare in the browser window)...")
        page.goto(BASE, wait_until="domcontentloaded", timeout=60000)
        if wait_for_cloudflare(page, max_wait=60):
            print("[+] Cloudflare passed!")
        else:
            print("[!] CF did not resolve. Continuing anyway...")

        # Main scrape loop
        print("[*] Phase 2: Scraping minor entries...")
        for l_idx in range(start_letter_idx, len(LETTERS)):
            letter   = LETTERS[l_idx]
            page_nr  = start_page_nr if l_idx == start_letter_idx else 1
            total_entries = None

            while True:
                url = f"{BROWSE_URL}?key=drg&letter={letter}&pagenr={page_nr}"
                if total_entries:
                    url += f"&totalEntries={total_entries}"

                print(f"    [{letter.upper()}] p.{page_nr}  |  collected: {len(collected)}")

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                except Exception as e:
                    print(f"        [!] Navigation error: {e}. Retrying in 10s...")
                    time.sleep(10)
                    continue

                if "Just a moment" in get_title_safe(page):
                    print(f"        [!] Cloudflare detected. Solve in Brave window...")
                    if not wait_for_cloudflare(page):
                        print(f"        [!] CF did not resolve. Saving state...")
                        save_state(l_idx, page_nr, collected)
                        browser.close()
                        return

                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                # Get total entries count on first page (for URL params)
                if page_nr == 1 and total_entries is None:
                    pag_link = soup.select_one("a[href*='totalEntries']")
                    if pag_link:
                        m = re.search(r"totalEntries=(\d+)", pag_link["href"])
                        if m:
                            total_entries = int(m.group(1))
                            print(f"        [{letter}] total entries: {total_entries}")

                # Select ONLY .minorentrycomplex divs (skip .entry — already scraped)
                minor_divs = soup.select(".minorentrycomplex")

                if not minor_divs and not soup.select(".entry"):
                    # No entries at all - check if still blocked
                    if "Just a moment" in get_title_safe(page):
                        print("        [!] Still blocked. Retrying...")
                        continue
                    print(f"        [i] No more entries on this page.")
                    break

                for entry_div in minor_divs:
                    parsed = parse_minor_entry(entry_div)
                    if parsed["headword"]:
                        collected.append(parsed)

                save_state(l_idx, page_nr, collected)

                # Check for next page
                next_page = soup.select_one(f"a[href*='pagenr={page_nr + 1}']")
                if not next_page:
                    break

                page_nr += 1
                time.sleep(DELAY)

        browser.close()

    # Save final output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(collected, f, ensure_ascii=False, indent=2)

    print(f"\n[!!!] SCRAPE COMPLETE. Total minor entries collected: {len(collected)}")
    print(f"[!!!] Saved to: {OUTPUT_FILE}")
    print(f"[!!!] Now run: python merge_minor.py   to merge into mainDataset.json")

    if STATE_FILE.exists():
        STATE_FILE.unlink()


if __name__ == "__main__":
    scrape_minor()
