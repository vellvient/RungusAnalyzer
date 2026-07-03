"""
Generate the technical progress report PDF for Christine Dreiheller.
Uses fpdf2 to create a clean, professional document.
"""
from fpdf import FPDF
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rungus_analyzer_lib import load_dictionary, analyze

d = load_dictionary()


class ReportPDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return  # No header on title page
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, "Rungus Morphological Analyzer - Technical Progress Report", align="R")
        self.ln(8)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")
        self.set_text_color(0, 0, 0)

    def section_title(self, title):
        self.ln(4)
        self.set_font("Helvetica", "B", 13)
        self.set_fill_color(240, 240, 240)
        self.cell(0, 8, title, fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def subsection_title(self, title):
        self.ln(2)
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 6, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5.5, text)
        self.ln(1.5)

    def example_block(self, label, word, analysis_lines):
        """Render a grey-boxed example with word + analysis breakdown."""
        self.ln(1)
        self.set_fill_color(245, 245, 245)
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 6, f"  {label}: {word}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_font("Courier", "", 9)
        for line in analysis_lines:
            self.set_fill_color(250, 250, 250)
            self.cell(0, 5, f"    {line}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_font("Helvetica", "", 10)


def get_breakdown(word):
    """Run the analyzer and return formatted breakdown lines."""
    r = analyze(word, d)
    lines = []
    root = r.get("root") or "(not found)"
    gloss = r.get("root_gloss") or ""
    prefix = r.get("prefix") or ""
    prefix2 = r.get("prefix2") or ""
    infix = r.get("infix") or ""
    suffix = r.get("suffix") or ""
    enclitic = r.get("enclitic") or ""

    lines.append(f"Root: {root}" + (f"  -  \"{gloss}\"" if gloss else ""))
    if prefix:
        pm = r.get("prefix_meaning", "")
        lines.append(f"Prefix: {prefix}  ({pm})")
    if prefix2:
        lines.append(f"Stacked prefix: {prefix2}  ({r.get('prefix2_meaning','')})")
    if infix:
        lines.append(f"Infix: -{infix}-  ({r.get('infix_meaning','')})")
    if suffix:
        lines.append(f"Suffix: -{suffix}  ({r.get('suffix_meaning','')})")
    if enclitic:
        lines.append(f"Enclitic: -{enclitic}  ({r.get('enclitic_meaning','')})")
    return lines


pdf = ReportPDF()
pdf.set_auto_page_break(auto=True, margin=20)
pdf.add_page()

# ── Title ──
pdf.set_font("Helvetica", "B", 18)
pdf.cell(0, 10, "Rungus Morphological Analyzer", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 12)
pdf.set_text_color(80, 80, 80)
pdf.cell(0, 7, "Technical Progress Report for Christine Dreiheller (SIL)", new_x="LMARGIN", new_y="NEXT")
pdf.set_text_color(0, 0, 0)
pdf.ln(3)
pdf.set_draw_color(200, 200, 200)
pdf.line(20, pdf.get_y(), 190, pdf.get_y())
pdf.ln(5)

# ── Overview ──
pdf.section_title("Overview")
pdf.body_text(
    "This report documents the current state of a prototype morphological analyzer for the Rungus "
    "language (ISO 639-3: drg), built as a response to the idea of developing a 'hermit crab parser' "
    "for Rungus. The analyzer decomposes inflected surface words into their base roots, prefixes, "
    "infixes, suffixes, and enclitics, applying morphophonological rewrite rules derived from "
    "Forschner's grammar and the Swarthmore LING073 transducer project."
)
pdf.body_text(
    "Data sources:\n"
    "  -  Webonary Rungus dictionary: 12,530 entries (scraped and normalized)\n"
    "  -  Forschner, T.A. (1994). Outline of a Momogun Grammar (Rungus Dialect)\n"
    "  -  Swarthmore College LING073 Spring 2025 Rungus transducer documentation\n"
    "  -  Corpus: 534,775 tokens across 9 Rungus books (ebfo.de)"
)
pdf.body_text(
    "Current token coverage: 96.4% (515,762 of 534,775 tokens).\n"
    "Live prototype: https://rungus-analyzer.vercel.app/"
)

# ── Section 1: False Positives ──
pdf.section_title("1. False Positives - Wrong Root Selected")

pdf.body_text(
    "The most common failure mode is a spelling collision: the analyzer strips the affixes "
    "correctly, but lands on the wrong root because two valid roots produce the same surface "
    "form after nasal substitution. The analyzer has no semantic understanding, so it relies "
    "entirely on dictionary structure and morphophonological rules to resolve ambiguity."
)

pdf.subsection_title("1.1  Nasal Substitution Collisions")
pdf.body_text(
    "When the transitive prefix mo- (or ma-) attaches to a stem beginning with a voiceless "
    "consonant (/p/, /t/, /k/, /s/) or /b/, the initial consonant is replaced by a nasal at "
    "the same place of articulation (p/b -> m, t/s -> n, k -> ng). During analysis, the engine "
    "must reverse this: an initial m- could come from p-, b-, v-, or an original m-."
)
pdf.example_block("Example", "mamasa", get_breakdown("mamasa"))
pdf.body_text(
    "The engine strips ma- and recovers masa. Under nasal substitution rules, masa could come "
    "from basa (\"to read\"), pasa (\"rotten\"), or vas. The dictionary lists mamasa as a "
    "subentry of basa, so the engine uses this parent-child relationship to prefer basa. "
    "This fix works when the dictionary hints at the correct parent, but does not help when "
    "no subentry entry exists for the surface form."
)

pdf.subsection_title("1.2  The ko-...-o Nominalizing Circumfix")
pdf.body_text(
    "Rungus has two homophonous suffixes written -o: the verbal imperative patient focus (-o) "
    "and the nominal abstract noun suffix that forms a circumfix with ko- (ko-...-o). Without "
    "considering the prefix context, the engine cannot distinguish them. I implemented a rule: "
    "when ko- is the prefix and -o is the suffix, treat it as the nominalizing circumfix."
)
pdf.example_block("Example (fixed)", "kosunduvo", get_breakdown("kosunduvo"))
pdf.example_block("Example (fixed)", "konoruvo", get_breakdown("konoruvo"))
pdf.body_text(
    "In kosunduvo, the root sundu ends in the high vowel /u/. Rungus inserts a /v/ glide to "
    "bridge the adjacent vowels before appending -o: ko- + sundu + o -> kosunduvo. The same "
    "pattern appears in konoruvo (anaru \"long\" -> konoruvo \"length\")."
)
pdf.body_text(
    "Questions for confirmation:\n"
    "  -  Is the ko-...-o circumfix fully productive in Rungus?\n"
    "  -  Does the /v/ glide insertion also occur after /i/, or only after /u/?\n"
    "  -  Are there other circumfixes with similar morphophonological behavior?"
)

pdf.subsection_title("1.3  False Reduplication Stripping")
pdf.body_text(
    "Words like kakal (\"still/yet\"), kakau (\"epilepsy\"), and kakat (\"pull/drag\") were "
    "initially misparsed: the engine saw the repeated ka- syllable and interpreted it as "
    "CV-reduplication, stripping it to produce false bases (kal, kau, kat). I added a guard "
    "that checks the full word in the dictionary before attempting any reduplication stripping."
)

# ── Section 2: False Negatives ──
pdf.section_title("2. False Negatives - Root Missing From Dictionary")

pdf.body_text(
    "The second failure mode is straightforward: a word fails to parse because its root is "
    "simply absent from the Webonary dictionary. No amount of morphological analysis can "
    "recover a root that was never documented."
)
pdf.example_block("Example", "pogibad (85 occurrences, meaning unknown)", get_breakdown("pogibad"))
pdf.body_text(
    "I have been working on a Human-in-the-Loop (HITL) workflow to address this: an AI "
    "examines the surrounding sentence context and pre-fills a spreadsheet with educated "
    "guesses about the root and meaning, which a human reviewer can then confirm or correct. "
    "The top 500 unanalyzed words are included as a separate CSV attachment. The web app also "
    "has an \"Export Unanalyzed to CSV\" button in Batch Mode for generating these lists from "
    "any Rungus text."
)

# ── Section 3: Morphophonological Rules Implemented ──
pdf.section_title("3. Morphophonological Rules Implemented")

pdf.subsection_title("3.1  Nasal Substitution & Vowel Assimilation")
pdf.body_text(
    "The analyzer reverses consonant substitution for all voiceless stops and /b/: p->m, "
    "t/s->n, k->ng. It also handles prenasalization before voiced consonants (liquids, "
    "glides) where a nasal is inserted rather than substituted."
)
pdf.example_block("Example", "mamanau (panau + ma-)", get_breakdown("mamanau"))
pdf.example_block("Example", "monguvo (kuvo + mo-)", get_breakdown("monguvo"))
pdf.example_block("Example", "mangaradu (radu + ma- + prenasalization)", get_breakdown("mangaradu"))

pdf.subsection_title("3.2  Vowel Contractions")
pdf.body_text(
    "When a vowel-ending prefix attaches to a vowel-initial stem, the two vowels contract: "
    "a+i -> e, o+i -> e, o+u -> u. The analyzer reverses these contractions during analysis."
)
pdf.example_block("Example", "elo (ilo + o-, o+i -> e)", get_breakdown("elo"))

pdf.subsection_title("3.3  Glottal Stop Alternations")
pdf.body_text(
    "Root-final glottal stops alternate when a suffix is appended. After the high vowel /i/, "
    "the glottal becomes /z/. After /u/, it becomes /h/. After the low vowel /a/, it is "
    "retained. The analyzer reverses all three alternations."
)
pdf.example_block("Example", "gilizon (gili' + -on, /i/ -> /z/)", get_breakdown("gilizon"))
pdf.example_block("Example", "ontoluhan (ontolu' + -an, /u/ -> /h/)", get_breakdown("ontoluhan"))

pdf.subsection_title("3.4  Non-Syllabic Vowel Consonantization")
pdf.body_text(
    "Word-final non-syllabic vowels become consonants when suffixes are appended: /u/ -> /h/ "
    "and /i/ -> /z/. The analyzer reverses these by trying h->u and z->i (or z-stripping for "
    "glottal stop origins) during root lookup."
)
pdf.example_block("Example", "pasalahon (asalau + pa- + -on, /u/ -> /h/)", get_breakdown("pasalahon"))

pdf.subsection_title("3.5  Infixation")
pdf.body_text(
    "Rungus uses three infixes: -um- (active voice), -in- (past tense), and -inum- (past "
    "intransitive, a contraction of -in- + -um-). Infixes are inserted after the first "
    "consonant of the root, or after the first consonant of the prefix when a prefix is present."
)
pdf.example_block("Example", "riumikot (rikot + -um-)", get_breakdown("riumikot"))
pdf.example_block("Example", "rinumikot (rikot + -inum-)", get_breakdown("rinumikot"))

pdf.subsection_title("3.6  Stacked Prefixes & Extreme Agglutination")
pdf.body_text(
    "The analyzer handles two layers of stacked prefixes and also tries suffixes on the final "
    "remainder. This allows it to parse words combining deep prefix stacking with suffixes."
)
pdf.example_block("Example", "nangasavatan (na- + anga- + savat + -an)", get_breakdown("nangasavatan"))

pdf.subsection_title("3.7  Enclitics & Complete Predicate Words")
pdf.body_text(
    "Rungus attaches pronominal enclitics to the end of verbs, forming complete predicate "
    "sentences within a single word. The analyzer strips these before morphological "
    "decomposition and correctly identifies the subject pronoun."
)
pdf.example_block("Example", "minonudukoku (tuduk + mo- + -in- + -oku \"I\")", get_breakdown("minonudukoku"))
pdf.example_block("Example", "tinumorimaoku (torima + -inum- + -oku \"I\")", get_breakdown("tinumorimaoku"))

# ── Section 4: Open Questions ──
pdf.section_title("4. Open Questions for Expert Review")
pdf.body_text(
    "1. Is the ko-...-o nominalizing circumfix fully productive? Are there restrictions on "
    "   which roots it can attach to?\n\n"
    "2. Does the /v/ glide insertion before -o occur only after /u/, or also after /i/? "
    "   The data shows it after /u/ (sundu -> kosunduvo, anaru -> konoruvo) but I have not "
    "   found a clear /i/ example.\n\n"
    "3. For the nasal substitution collision problem (e.g., mamasa -> basa vs. pasa), is "
    "   there a frequency or semantic preference rule in Rungus that could help disambiguate?\n\n"
    "4. Are there morphophonological rules I have not implemented that would be important for "
    "   accurate analysis? In particular, I would like to verify my treatment of glottal stop "
    "   alternations and non-syllabic vowel consonantization against your knowledge of the "
    "   grammar.\n\n"
    "5. For the missing-root words (Section 2), would you be able to review even a small "
    "   portion of the attached spreadsheet? Even 20-30 entries would significantly improve "
    "   coverage."
)

# ── Closing ──
pdf.ln(3)
pdf.set_draw_color(200, 200, 200)
pdf.line(20, pdf.get_y(), 190, pdf.get_y())
pdf.ln(4)
pdf.body_text(
    "I would greatly appreciate the opportunity to meet in person to discuss these questions. "
    "Please feel free to reach me by email at aifvennelson08@gmail.com."
)
pdf.body_text("Aifven Vellvient Nelson\nKg. Pinorat, Kudat, Sabah")

# ── Save ──
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Technical_Progress_Report.pdf")
pdf.output(output_path)
print(f"PDF saved to: {output_path}")
print(f"Pages: {pdf.page_no()}")
