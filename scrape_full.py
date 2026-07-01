"""
Scrape the entire Webonary Rungus Dictionary (~12,000+ entries).
Uses Playwright + Brave browser to bypass Cloudflare challenge.

Cloudflare bypass strategy:
- Uses Brave browser (headless=False) - real browser engine
- Warms up on homepage first (solves CF challenge, gets cookies)
- Each page navigation waits for CF challenge to auto-resolve
- Resumable via scrape_state.json

Output: mainDataset.json
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
OUTPUT_FILE = Path(__file__).parent / "mainDataset.json"
STATE_FILE = Path(__file__).parent / "scrape_state.json"
DELAY = 1.0  # seconds between page loads

# Brave browser path
BRAVE_PATH = "C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"


def get_title_safe(page):
    """Get page title without crashing during navigation."""
    try:
        return page.title()
    except:
        return "(navigating)"


def wait_for_cloudflare(page, max_wait=60):
    """Wait for Cloudflare 'Just a moment...' challenge to resolve. Returns True if resolved."""
    for i in range(max_wait // 2):
        page.wait_for_timeout(2000)
        title = get_title_safe(page)
        if "Just a moment" not in title and title != "(navigating)":
            return True
        if i == 0 or i % 5 == 0:
            print(f"        Waiting for CF ({i*2}s)... {title}")
    return False


def remove_duplicate_suffix(text):
    """Detects and removes duplicated suffixes caused by nested span extraction."""
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
    """Normalize whitespace, commas, semicolons, and remove duplicate suffixes."""
    if not text:
        return None
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r",([^\s])", r", \1", text)
    text = re.sub(r";([^\s])", r"; \1", text)
    text = re.sub(r"^[\s,;]+|[\s,;]+$", "", text)
    text = remove_duplicate_suffix(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text if text else None


def parse_entry(entry_div):
    """Refined parser ensuring all spans are captured and cleaned of artifacts."""
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
        en_gloss_tags = sense.select(".definitionorgloss [lang='en']")
        ms_gloss_tags = sense.select(".definitionorgloss [lang='zlm']")

        raw_en = (
            "".join(t.get_text() for t in en_gloss_tags).strip()
            if en_gloss_tags
            else None
        )
        raw_ms = (
            "".join(t.get_text() for t in ms_gloss_tags).strip()
            if ms_gloss_tags
            else None
        )

        s["english"] = clean_text(raw_en)
        s["malay"] = clean_text(raw_ms)

        # Example sentences
        s["examples"] = []
        for ex in sense.select(".examplescontent .examplescontent"):
            example_text = ex.select_one(".example [lang='drg']")
            en_trans_tags = ex.select(".translation [lang='en']")
            ms_trans_tags = ex.select(".translation [lang='zlm']")

            raw_ex_en = (
                "".join(t.get_text() for t in en_trans_tags).strip()
                if en_trans_tags
                else None
            )
            raw_ex_ms = (
                "".join(t.get_text() for t in ms_trans_tags).strip()
                if ms_trans_tags
                else None
            )

            s["examples"].append(
                {
                    "rungus": example_text.get_text(strip=True) if example_text else None,
                    "english": clean_text(raw_ex_en),
                    "malay": clean_text(raw_ex_ms),
                }
            )

        # Fallback for differently structured examples
        if not s["examples"]:
            for ex_span in sense.select(".example [lang='drg']"):
                parent_content = ex_span.find_parent(class_="examplescontent")
                en_trans_t = []
                ms_trans_t = []
                if parent_content:
                    en_trans_t = parent_content.select(".translation [lang='en']")
                    ms_trans_t = parent_content.select(".translation [lang='zlm']")

                raw_ex_en = (
                    "".join(t.get_text() for t in en_trans_t).strip()
                    if en_trans_t
                    else None
                )
                raw_ex_ms = (
                    "".join(t.get_text() for t in ms_trans_t).strip()
                    if ms_trans_t
                    else None
                )

                s["examples"].append(
                    {
                        "rungus": ex_span.get_text(strip=True),
                        "english": clean_text(raw_ex_en),
                        "malay": clean_text(raw_ex_ms),
                    }
                )

        result["senses"].append(s)

    # Sub-entries
    result["subentries"] = []
    for sub in entry_div.select(".subentry"):
        sub_hw = sub.select_one("[class^='headword'] [lang='drg']")
        result["subentries"].append(
            {"headword": sub_hw.get_text(strip=True) if sub_hw else None}
        )

    return result


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"letter_idx": 0, "page_nr": 1, "collected": []}


def save_state(letter_idx, page_nr, collected):
    with open(STATE_FILE, "w") as f:
        json.dump(
            {"letter_idx": letter_idx, "page_nr": page_nr, "collected": collected}, f
        )


def scrape_full():
    state = load_state()
    collected = state["collected"]
    start_letter_idx = state["letter_idx"]
    start_page_nr = state["page_nr"]

    print(f"[*] Resuming from letter index {start_letter_idx}, page {start_page_nr}")
    print(f"[*] Already collected: {len(collected)} entries")
    print(f"[*] Using Brave browser at: {BRAVE_PATH}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            executable_path=BRAVE_PATH,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context()
        page = context.new_page()

        # ── Phase 1: Warmup (solve Cloudflare on homepage) ──
        print("[*] Phase 1: Warming up (Cloudflare challenge)...")
        page.goto(BASE, wait_until="domcontentloaded", timeout=60000)
        if wait_for_cloudflare(page, max_wait=60):
            print("[+] Cloudflare passed on homepage!")
        else:
            print("[!] Cloudflare did NOT resolve on homepage. Continuing anyway...")

        # ── Phase 2: Scrape all letters ──
        print("[*] Phase 2: Scraping dictionary...")
        for l_idx in range(start_letter_idx, len(LETTERS)):
            letter = LETTERS[l_idx]
            page_nr = start_page_nr if l_idx == start_letter_idx else 1
            total_entries = None

            while True:
                url = f"{BROWSE_URL}?key=drg&letter={letter}&pagenr={page_nr}"
                if total_entries:
                    url += f"&totalEntries={total_entries}"

                print(
                    f"    [{letter.upper()}] p.{page_nr}  |  collected: {len(collected)}"
                )

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                except Exception as e:
                    print(f"        [!] Navigation error: {e}. Retrying in 10s...")
                    time.sleep(10)
                    continue

                # Handle Cloudflare on this page
                if "Just a moment" in get_title_safe(page):
                    print(f"        [!] Cloudflare detected. Waiting...")
                    if not wait_for_cloudflare(page, max_wait=60):
                        print(f"        [!] CF did not resolve. Saving state...")
                        save_state(l_idx, page_nr, collected)
                        browser.close()
                        return

                # Parse
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                # On first page, get total entries count
                if page_nr == 1 and total_entries is None:
                    pag_link = soup.select_one("a[href*='totalEntries']")
                    if pag_link:
                        m = re.search(r"totalEntries=(\d+)", pag_link["href"])
                        if m:
                            total_entries = int(m.group(1))
                            print(f"        [{letter}] total entries: {total_entries}")

                entries = soup.select(".entry")
                if not entries:
                    # Double-check: is it really empty or still blocked?
                    if "Just a moment" in get_title_safe(page):
                        print("        [!] Still blocked. Retrying...")
                        continue
                    print(f"        [i] No more entries on this page.")
                    break

                for entry_div in entries:
                    parsed = parse_entry(entry_div)
                    if parsed["headword"]:
                        collected.append(parsed)

                # Save incremental progress
                save_state(l_idx, page_nr, collected)

                # Check for next page
                next_page = soup.select_one(f"a[href*='pagenr={page_nr + 1}']")
                if not next_page:
                    break

                page_nr += 1
                time.sleep(DELAY)

        browser.close()

    # ── Final save ──
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(collected, f, ensure_ascii=False, indent=2)

    print(f"\n[!!!] SCRAPE COMPLETE. Total entries: {len(collected)}")
    if STATE_FILE.exists():
        STATE_FILE.unlink()


if __name__ == "__main__":
    scrape_full()
