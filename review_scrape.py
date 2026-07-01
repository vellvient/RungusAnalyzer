"""Quick review of scraped data quality."""
import json

data = json.load(open("scraped_words.json", encoding="utf-8"))

print(f"Total entries scraped: {len(data)}")
print()

# Stats
has_english = sum(1 for w in data if any(s.get("english") and s["english"] != "," for s in w.get("senses", [])))
has_malay = sum(1 for w in data if any(s.get("malay") for s in w.get("senses", [])))
has_examples = sum(1 for w in data if any(s.get("examples") for s in w.get("senses", [])))
has_subentries = sum(1 for w in data if w.get("subentries"))
multi_sense = sum(1 for w in data if len(w.get("senses", [])) > 1)

# Some English definitions are just "," which is a parsing artifact
comma_english = sum(1 for w in data if any(s.get("english") == "," for s in w.get("senses", [])))

print(f"  With English definition:  {has_english:3d} / {len(data)}")
print(f"  With Malay definition:    {has_malay:3d} / {len(data)}")
print(f"  With example sentences:   {has_examples:3d} / {len(data)}")
print(f"  With sub-entries:         {has_subentries:3d} / {len(data)}")
print(f"  Multiple senses:          {multi_sense:3d} / {len(data)}")
print(f"  English = ',' (artifact): {comma_english:3d} / {len(data)}")
print()

total_examples = sum(len(ex) for w in data for s in w.get("senses", []) for ex in [s.get("examples", [])])
total_senses = sum(len(w.get("senses", [])) for w in data)
total_subentries = sum(len(w.get("subentries", [])) for w in data)

print(f"  Total senses:      {total_senses}")
print(f"  Total examples:    {total_examples}")
print(f"  Total sub-entries: {total_subentries}")
print()

print("=" * 70)
print("Sample entries:")
print("=" * 70)
for w in data[:15]:
    print(f"\n  {w['headword']}")
    for i, s in enumerate(w.get("senses", [])):
        en = s.get("english", "—")
        ms = s.get("malay", "—")
        print(f"    Sense {i+1}: EN: {en}  |  MS: {ms}")
        for ex in s.get("examples", []):
            print(f"      Ex: {ex.get('rungus', '')[:60]}...")
