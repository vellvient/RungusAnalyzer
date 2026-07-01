"""
Scrape the entire Webonary Rungus Dictionary (~12,000 entries).

Optimized for:
- Reliability: Saves progress incrementally to partial files.
- Politeness: Respects the server to avoid blocks.
- Comprehensive Parsing: Uses the improved multi-span extraction from the POC.

Output: mainDataset.json (when complete)
"""

import json
import re
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

BASE = "https://www.webonary.org/rungus"
BROWSE_URL = f"{BASE}/browse/browse-vernacular-english/"
LETTERS = list("abdeghijklmnoprstuvwyz")  # Rungus alphabet
OUTPUT_FILE = Path(__file__).parent / "mainDataset.json"
STATE_FILE = Path(__file__).parent / "scrape_state.json"
DELAY = 1.0  # seconds between page loads

def parse_entry(entry_div):
    """Refined parser from scrape_100.py ensuring all spans are captured."""
    result = {}
    result["guid"] = entry_div.get("id", "")
    result["url"] = f"{BASE}/{result['guid']}" if result["guid"] else ""

    # Headword (Rungus)
    hw = entry_div.select_one(".mainheadword [lang='drg']")
    result["headword"] = hw.get_text(strip=True) if hw else None

    # Senses
    result["senses"] = []
    for sense in entry_div.select(".senses > .sensecontent > .sense"):
        s = {}
        # Use .select() to catch cases like "abai" where definitions are split
        en_gloss_tags = sense.select(".definitionorgloss [lang='en']")
        ms_gloss_tags = sense.select(".definitionorgloss [lang='zlm']")
        
        s["english"] = "".join(t.get_text() for t in en_gloss_tags).strip() if en_gloss_tags else None
        s["malay"] = "".join(t.get_text() for t in ms_gloss_tags).strip() if ms_gloss_tags else None

        # Example sentences
        s["examples"] = []
        for ex in sense.select(".examplescontent .examplescontent"):
            example_text = ex.select_one(".example [lang='drg']")
            en_trans_tags = ex.select(".translation [lang='en']")
            ms_trans_tags = ex.select(".translation [lang='zlm']")
            
            s["examples"].append({
                "rungus": example_text.get_text(strip=True) if example_text else None,
                "english": "".join(t.get_text() for t in en_trans_tags).strip() if en_trans_tags else None,
                "malay": "".join(t.get_text() for t in ms_trans_tags).strip() if ms_trans_tags else None,
            })

        # Fallback for differently structured examples
        if not s["examples"]:
            for ex_span in sense.select(".example [lang='drg']"):
                parent_content = ex_span.find_parent(class_="examplescontent")
                en_trans_t = []
                ms_trans_t = []
                if parent_content:
                    en_trans_t = parent_content.select(".translation [lang='en']")
                    ms_trans_t = parent_content.select(".translation [lang='zlm']")

                s["examples"].append({
                    "rungus": ex_span.get_text(strip=True),
                    "english": "".join(t.get_text() for t in en_trans_t).strip() if en_trans_t else None,
                    "malay": "".join(t.get_text() for t in ms_trans_t).strip() if ms_trans_t else None,
                })

        result["senses"].append(s)

    # Sub-entries
    result["subentries"] = []
    for sub in entry_div.select(".subentry"):
        sub_hw = sub.select_one("[class^='headword'] [lang='drg']")
        result["subentries"].append({
            "headword": sub_hw.get_text(strip=True) if sub_hw else None,
        })

    return result

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"letter_idx": 0, "page_nr": 1, "collected": []}

def save_state(letter_idx, page_nr, collected):
    with open(STATE_FILE, "w") as f:
        json.dump({"letter_idx": letter_idx, "page_nr": page_nr, "collected": collected}, f)

def scrape_full():
    state = load_state()
    collected = state["collected"]
    start_letter_idx = state["letter_idx"]
    start_page_nr = state["page_nr"]

    print(f"[*] Resuming from letter index {start_letter_idx}, page {start_page_nr}")
    print(f"[*] Total entries currently collected: {len(collected)}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 ... (Chrome/131)")
        page = context.new_page()

        print("[*] Warming up session...")
        page.goto(BASE, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        for l_idx in range(start_letter_idx, len(LETTERS)):
            letter = LETTERS[l_idx]
            page_nr = start_page_nr if l_idx == start_letter_idx else 1
            total_entries = None

            while True:
                url = f"{BROWSE_URL}?key=drg&letter={letter}&pagenr={page_nr}"
                if total_entries:
                    url += f"&totalEntries={total_entries}"

                print(f"[*] {letter.upper()} | Page {page_nr} | Found: {len(collected)}")
                
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(1000)
                except Exception as e:
                    print(f"    [!] Error: {e}. Retrying in 10s...")
                    time.sleep(10)
                    continue

                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                if page_nr == 1 and total_entries is None:
                    pag_link = soup.select_one("a[href*='totalEntries']")
                    if pag_link:
                        m = re.search(r"totalEntries=(\d+)", pag_link["href"])
                        if m:
                            total_entries = int(m.group(1))

                entries = soup.select(".entry")
                if not entries:
                    break

                for entry_div in entries:
                    parsed = parse_entry(entry_div)
                    if parsed["headword"]:
                        # Simple de-duplication log by GUID
                        collected.append(parsed)

                # Save incremental progress
                save_state(l_idx, page_nr, collected)

                next_page = soup.select_one(f"a[href*='pagenr={page_nr + 1}']")
                if not next_page:
                    break
                
                page_nr += 1
                time.sleep(DELAY)

        browser.close()

    # Final Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(collected, f, ensure_ascii=False, indent=2)
    
    print(f"\n[!!!] FINISHED. Total entries: {len(collected)}")
    if STATE_FILE.exists():
        STATE_FILE.unlink()

if __name__ == "__main__":
    scrape_full()
