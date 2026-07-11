# Draft: Follow-up to Christine — v3.1 (her rules implemented)

**To:** christine_dreiheller@sil.org
**Subject:** Re: RUNGUS MORPHOLOGICAL ANALYSIS SUGGESTION - AIFVEN NELSON

---

Dear Christine,

Thank you again for your detailed feedback — it turned out to be exactly what the parser needed. I have now implemented every rule you described, and I wanted to share the results as the "next instalment" you asked about.

**1. Vowel harmony (A→O after root-final high vowel).** The analyzer now reverses this systematically, including cases where two rules apply at once. All of your examples parse correctly:

- koporuo → paru (kA- + aparu + -o)
- oporuan → paru
- gontian → ganti
- jonjizon → janji (glide /z/ + harmony reversed together)

**2. L/R interchange and D after nasal.** Also implemented, and your examples verify:

- posikuron → sikul
- habaran → habal
- endalanan → ralan (past -in- + -an, r→d after the nasal)
- mongindaraat → ra'at

**3. The four voices.** I read your explanation alongside Dr. Kroeger's Kimaragang work, and the analyzer now tags every parsed verb form with its voice: agent (mAN-/pAN-/-um-), undergoer (-on, past -in-), beneficiary/locative (-an, past -in-…-an), and the mobile object focus (i-, ni-). The web app displays this on every analysis. I also corrected the kA- glosses to record its wider polysemy ("can", "just now", "come to pass") and distinguished kA-…-o from kA-…-an.

**Impact:** with no new dictionary entries — purely from your four rules — the number of word types the parser could not analyze in my 534,000-token corpus fell by 15.8% (6,399 → 5,391), and token coverage rose from 96.4% to 96.9%. Each rule is now also covered by automated tests citing your examples, so future changes cannot silently break them.

The updated analyzer is live at the same address: https://rungus-analyzer.vercel.app/

I have also noted your caution about Forschner's texts and his Eurocentric framework — I've recorded it in the project documentation, and I'm treating the corpus (much of it EBFO material) accordingly.

Two questions, if you have a moment:

1. For the mobile object focus (i-, ni-): are there a few common verbs you'd suggest I test with, so I can verify the parser handles them the way your team would expect?
2. Does the vowel harmony rule ever apply with the prefixes as well (e.g. kA- → kO- before certain roots), or only in the suffix direction?

Thank you again — your two paragraphs improved the parser more than weeks of my own guessing.

Best regards,
Aifven Vellvient Nelson
