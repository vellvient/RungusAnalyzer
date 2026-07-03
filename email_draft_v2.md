Subject: Re: Rungus Morphological Workstation Prototype (A Levels & Progress Update!)

Dear Christine,

How are you doing? I hope you are doing well.

I graduated last year and am currently staying in Kg. Pinorat. This coming 19th July, I'll be heading to Selangor to study my A-Levels at KYUEM. I must admit that my personal proficiency in Rungus is still quite limited — and that limitation is exactly what inspired me to try contributing to my native language, and in that process, learn it myself.

Over the past few months, I have been thinking seriously about the questions you raised in your previous email. You mentioned that you and your team would be very interested if someone could build a "hermit crab parser" for Rungus — a tool that extracts roots and affixes from surface word forms. From that, I tried building a prototype of a Rungus morphological analyzer.

Using the 12,530 entries from the Webonary dictionary, Traugott Forschner's Grammar of Rungus, and the morphological rules documented in Swarthmore College's LING073 transducer project, the analyzer currently achieves 96.4% token coverage when tested against a corpus of nine Rungus books containing over 534,000 words (obtained from ebfo.de).

You can try the live deployed prototype here: 🔗 https://rungus-analyzer.vercel.app/

Because of my limited proficiency, the analyzer is not yet fully accurate. I have identified two main categories of errors, and I would really value your expert guidance on them.

1. False Positives — The Analyzer Finds A Root, But The Wrong One

The most common failure mode is a spelling collision: the analyzer successfully strips the affixes, but lands on the wrong root because two valid roots have the same surface form after stripping. The analyzer has no semantic understanding, so it relies entirely on dictionary entries and morphophonological rules to resolve ambiguity.

Example: mamasa — The engine strips the transitive prefix, which nasalizes the stem-initial consonant (a rule documented by Forschner and confirmed by the Swarthmore transducer). The resulting core is masa. Under the nasalization rules, an initial m- can represent an original p-, b-, or v-. Unfortunately, the dictionary contains both basa ("to read") and pasa ("rotten"), both of which are equally short and equally valid candidates. I have since added a priority system that checks the dictionary's own subentry list — if masa appears as a subentry of basa but not pasa, the engine prefers basa. This fixed this particular case, but the approach only works when the dictionary itself hints at the parent root.

Example: kaka- words — Words like kakal ("still/yet"), kakau ("epilepsy"), and kakat ("pull/drag") were initially misparsed because the engine eagerly interpreted ka- as a CV-reduplication prefix, stripping it to produce false bases like kal, kau, or kat, none of which exist. I have since added a guard that checks the full word in the dictionary first before attempting any reduplication stripping.

Example: kosunduvo and the ko-...-o nominalizing circumfix — This is a systematic error I want to raise with you specifically, because I believe I now understand what is happening — but I would like you to confirm it.

Both kosunduvo ("power/spirit" from sundu) and konoruvo ("length" from anaru) are abstract nouns formed by the ko-...-o circumfix, which creates abstract nouns from root stems. The issue was that the analyzer initially treated the trailing -o as the verbal suffix -o ("imperative patient focus") rather than as part of the nominalizing circumfix. The two homophonous suffixes — the verbal -o (imperative) and the nominal -o (abstract noun nominalizer) — are indistinguishable to the engine unless it considers the prefix context.

I have since fixed this: when the prefix ko- is present and the trailing morpheme is -o, the engine now labels it as the nominalizing circumfix, not the imperative. The morphophonological behavior is also consistent with Forschner's grammar. In kosunduvo, the root sundu ends in the high vowel /u/, and Rungus grammar inserts a /v/ glide to bridge the two adjacent vowels before adding -o: ko- + sundu + o → ko-sundu-vo → kosunduvo. I found the same rule applied consistently elsewhere in the dictionary: anaru ("long") → konoruvo ("length"), which follows the exact same pattern (anaru ends in /u/, glide inserted, suffix -o appended). The analyzer now handles both cases correctly.

I am fairly confident this analysis is correct based on the pattern in the data, but I would appreciate your confirmation — particularly on whether the ko-...-o circumfix is fully productive in Rungus, and whether there are other high vowels (like /i/) that trigger the same glide insertion.

2. False Negatives — The Root Is Missing From The Dictionary Entirely

The second failure mode is simpler: a word fails to parse because its root is simply absent from Webonary.

Example: pogibad — Meaning unknown to me, this word appears 85 times across the nine books but fails completely because pogibad is not listed in the dictionary at all, and the analyzer cannot find any root by stripping affixes. I have found dozens of similar cases. To address this, I have been working on a "Human-in-the-Loop" (HITL) workflow where an LLM examines the surrounding sentence context and pre-fills a spreadsheet with educated guesses about the root and meaning, which a human reviewer can then confirm or correct.

As a small test of this workflow, I exported the top 500 unanalyzed words from the corpus. I have attached the pre-filled spreadsheet (reviewed_testv1.csv) along with the raw list (top500before_review.csv) for you to look over. The AI performs surprisingly well on loanwords (like kampong and bandar) but struggles, understandably, with native Rungus vocabulary — which is exactly where your expertise would be invaluable.

To make the review process easy, I have added an "Export Unanalyzed to CSV" button in the Batch Mode section of the web app. If you paste any Rungus text and process it, you can download a spreadsheet of the failed words with their sentence context already filled in, so you do not have to start from scratch.

3. Recent Progress On Morphophonological Rules

Since I started this project, I have also made progress on several morphophonological rules that go beyond simple prefix/suffix stripping. I want to briefly mention these because I would value your input on whether my rule implementations match the actual grammar.

- Glottal Stop Alternations: When a suffix is appended to a root ending in a glottal stop, the glottal stop changes depending on the preceding vowel. The analyzer now reverses these alternations — for example, gilizon ("putting down") is correctly traced to gili' + -on, where the glottal stop became /z/ after the high vowel /i/. Similarly, ontoluhan ("castrated") traces to ontolu' + -an, where the glottal became /h/ after /u/.

- Non-Syllabic Vowel Consonantization: Word-final non-syllabic vowels become consonants when suffixes are appended. For example, pasalahon ("make thicker") is correctly parsed as pa- + asalau + -on, where the non-syllabic /u/ at the end of the root became /h/. Similarly, kavavalazan ("buildings") is parsed as ka-...-an with CV-reduplication on valai, where the non-syllabic /i/ became /z/.

- Stacked Prefixes With Suffixes: Words like nangasavatan ("too high all for me then") combine the past-tense prefix na-, the collective prefix anga-, the root savat, and the suffix -an. The analyzer now strips stacked prefixes (two layers deep) and also tries suffixes on the final remainder.

- Past-Tense Infixation Inside Prefixes: The analyzer handles words like minonudukoku ("I taught"), where the past-tense infix -in- is inserted inside the prefix mo- (after the first consonant m), and the first-person enclitic -oku is attached at the end. It correctly traces this back to tuduk ("to teach") + mo- + -in- + -oku.

I would love the opportunity to meet you in person before I leave for KYUEM, or when I return during a school break. Since you are not far from Tinangol and I am currently in Kg. Pinorat, it would be wonderful to catch up, show you how the analyzer works behind the scenes, and most importantly discuss some of these linguistic questions — particularly the ko-...-vo pattern — that I simply cannot resolve without a native expert.

Please let me know if you might be free sometime soon. I would really enjoy meeting you and hearing your thoughts.

Best regards,

Aifven Vellvient Nelson