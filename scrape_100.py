"""
Scrape 100 Rungus words from Webonary as a proof-of-concept.

Uses Playwright (headless Chromium) to bypass Cloudflare/403 blocks.
Browses the Rungus–English–Malay browse pages letter by letter,
collecting entries until we have 100.

Output: scraped_words.json  (pretty-printed JSON array of entry dicts)
"""

import json
import re
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

BASE = "https://www.webonary.org/rungus"
BROWSE_URL = f"{BASE}/browse/browse-vernacular-english/"
LETTERS = list("abdeghijklmnoprstuvwyz")  # Rungus alphabet (no c, f, q, x)
TARGET = 100
OUTPUT_FILE = Path(__file__).parent / "scraped_words.json"
DELAY = 1.5  # seconds between page loads — be respectful


def parse_entry(entry_div):
    """Parse a single .entry div into a structured dict."""
    result = {}

    # GUID
    result["guid"] = entry_div.get("id", "")
    result["url"] = f"{BASE}/{result['guid']}" if result["guid"] else ""

    # Headword (Rungus)
    hw = entry_div.select_one(".mainheadword [lang='drg']")
    result["headword"] = hw.get_text(strip=True) if hw else None

    # Senses
    result["senses"] = []
    for sense in entry_div.select(".senses > .sensecontent > .sense"):
        s = {}
        en_gloss_tags = sense.select(".definitionorgloss [lang='en']")
        ms_gloss_tags = sense.select(".definitionorgloss [lang='zlm']")
        s["english"] = "".join(t.get_text() for t in en_gloss_tags).strip() if en_gloss_tags else None
        s["malay"] = "".join(t.get_text() for t in ms_gloss_tags).strip() if ms_gloss_tags else None

        # Example sentences
        s["examples"] = []
        for ex in sense.select(".examplescontent > .examplescontent, .examplescontent > .examplescontent"):
            # Try a more general approach
            pass

        # Simpler example extraction
        for ex in sense.select(".examplescontent .examplescontent"):
            example_text = ex.select_one(".example [lang='drg']")
            en_trans_tags = ex.select(".translation [lang='en']")
            ms_trans_tags = ex.select(".translation [lang='zlm']")
            s["examples"].append({
                "rungus": example_text.get_text(strip=True) if example_text else None,
                "english": "".join(t.get_text() for t in en_trans_tags).strip() if en_trans_tags else None,
                "malay": "".join(t.get_text() for t in ms_trans_tags).strip() if ms_trans_tags else None,
            })

        # If above didn't work, try direct children
        if not s["examples"]:
            for ex in sense.select(".examplescontent .examplescontent"):
                pass  # already tried
            # Fallback: grab all examples directly
            for ex_span in sense.select(".example [lang='drg']"):
                parent_content = ex_span.find_parent(class_="examplescontent") or ex_span.find_parent(class_="examplescontent")
                en_trans_tags = []
                ms_trans_tags = []
                if parent_content:
                    en_trans_tags = parent_content.select(".translation [lang='en']")
                    ms_trans_tags = parent_content.select(".translation [lang='zlm']")

                s["examples"].append({
                    "rungus": ex_span.get_text(strip=True),
                    "english": "".join(t.get_text() for t in en_trans_tags).strip() if en_trans_tags else None,
                    "malay": "".join(t.get_text() for t in ms_trans_tags).strip() if ms_trans_tags else None,
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


def scrape():
    collected = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # headless for environments without display
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        # First, visit the homepage to get cookies / pass Cloudflare
        print("[*] Visiting homepage to warm up session...")
        page.goto(BASE, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)  # let JS/Cloudflare settle

        for letter in LETTERS:
            if len(collected) >= TARGET:
                break

            page_nr = 1
            total_entries = None

            while len(collected) < TARGET:
                url = f"{BROWSE_URL}?key=drg&letter={letter}&pagenr={page_nr}"
                if total_entries:
                    url += f"&totalEntries={total_entries}"

                print(f"[*] Fetching letter='{letter}' page={page_nr}  ({len(collected)}/{TARGET} collected)")
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(2000)  # let entries render
                except Exception as e:
                    print(f"    [!] Navigation error: {e}")
                    break

                time.sleep(DELAY)

                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                # On first page of a letter, grab totalEntries
                if page_nr == 1 and total_entries is None:
                    pag_link = soup.select_one("a[href*='totalEntries']")
                    if pag_link:
                        m = re.search(r"totalEntries=(\d+)", pag_link["href"])
                        if m:
                            total_entries = int(m.group(1))
                            print(f"    totalEntries for '{letter}': {total_entries}")

                entries = soup.select(".entry")
                if not entries:
                    print(f"    No entries found on this page, moving to next letter.")
                    break

                for entry_div in entries:
                    if len(collected) >= TARGET:
                        break
                    parsed = parse_entry(entry_div)
                    if parsed["headword"]:
                        collected.append(parsed)
                        print(f"    [{len(collected):3d}] {parsed['headword']}")

                # Check if there's a next page
                next_page_link = soup.select_one(f"a[href*='pagenr={page_nr + 1}']")
                if not next_page_link:
                    print(f"    No more pages for letter '{letter}'.")
                    break

                page_nr += 1

        browser.close()

    return collected


def main():
    print("=" * 60)
    print(f"  Webonary Rungus Scraper — Target: {TARGET} words")
    print("=" * 60)

    words = scrape()

    # Save to JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"  Done! Scraped {len(words)} entries.")
    print(f"  Saved to: {OUTPUT_FILE}")
    print(f"{'=' * 60}")

    # Print a quick summary
    print("\nFirst 10 entries:")
    for w in words[:10]:
        senses_str = "; ".join(
            f"{s.get('english', '?')} / {s.get('malay', '?')}"
            for s in w.get("senses", [])
        )
        print(f"  • {w['headword']:20s} → {senses_str}")


if __name__ == "__main__":
    main()
