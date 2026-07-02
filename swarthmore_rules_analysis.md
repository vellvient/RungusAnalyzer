# Swarthmore Transducer Rules Analysis

## Source
Swarthmore College LING073 (Spring 2025) — Computational Linguistics course
Built a morphological transducer for Rungus using HFST/Apertium framework
Private GitHub: github.swarthmore.edu/Ling073-sp25/ling073-drg

## Key Rules Extracted from Their Grammar Documentation

### 1. Intransitive Prefixes
| Prefix | Function | Example |
|--------|----------|---------|
| m- + stem | Process (impf) | imot → mimot (see) |
| mu- + stem | State of being | valai → muvalai (build house) |
| -um- (infix) | Process after C | rikot → rumikot (come) |

### 2. Transitive Prefixes (most complex)
Depends on stem-initial consonant:

**Stem starts with voiceless C or /b/:** Prefix mo-/ma-, initial C becomes nasal
| Stem initial | Becomes | Example |
|---|---|---|
| p-, b-, v- | m | panau → mamanau, babo → mamabo |
| t-, s- | n | ta'ud → mana'ud, sukung → monukung |
| k- | ng | kama → mangama |

**Stem starts with voiced C (excl /b/):** Prefix mongo-/manga- (no substitution)
| C | Example |
|---|---|
| d- | duat → mongoduat |
| g- | gama → mangagama |
| r- | ramit → mangaramit |
| l- | lobong → mongolobong |

**Stem starts with vowel:** Prefix mong-/mang-
| i- | ido → mongido |
| o- | ovit → mongovit |
| a- | ada → mangada |

### 3. Plural Prefixes
| Prefix | Function | Example |
|---|---|---|
| ongo-/anga- | Plural noun | valai → ongovalai |
| song-/sang- | Collective noun | ulun → songulun |

### 4. Vowel Contraction Rules (from Forschner)
| Combination | Result | Example |
|---|---|---|
| a + i | e | imot + ma- → memot |
| o + i | e | imot + po- → pemot |
| o + u | u | ongo- + ulun → ongulun |
| a + a | a | anga- + anak → anganak |
| o + o | o | ongo- + obpinai → ongobpinai |
| o + i | e | ongo- + idi → ongedi |

### 5. Verbal Flection Table (from Forschner Grammar Section 4.1)

| Tense | Actor transitiv | Actor intrans. | Object | Reference |
|---|---|---|---|---|
| Present (not completed) | mong-, moki-, mi-, mog-, mirim- | m-stem | stem-on | stem-an |
| Past | m-in-ong-, minoki-, mini-, minog-, mrim- | min-stem, -inum- | -stem-in | stem-an |
| Perfect (completed) | nokopong- | noko-stem | no-stem | — |
| Intended action | ti-stem | — | — | — |
| Desirous action | mokipopookot- | — | — | — |
| Imperative immediate | pong-, pi-, pog-stem | stem | stem-o | stem-ai |
| Imperative non-immediate | mong-stem | stem | stem-on | st-an |

### 6. Infixes
| Infix | Function | Example |
|---|---|---|
| -in- | Past tense marker | mapit → minapat |
| -um- | Process after C | rikot → rumikot |
| -inum- | Past of -um- | rumikot → rinumikot |
| -ong- / -anga- | Plural in verb | nokodop → nongokodop |

### 7. Suffixes
| Suffix | Function |
|---|---|
| -on | Nomina gerundiva (the act of X) |
| -an | Nomina collectiva / locative |
| -o | Imperative patient focus |
| -ai | Imperative reference focus |

### 8. Swarthmore Transducer Stats
- 100 stems in lexicon
- 14 twol rewrite rules
- Coverage: 439/1226 corpus words (35.8%)
- Generation test pass rate: 85/94 (90.4%)

## What This Gives Us
The Swarthmore rules + Forschner grammar give us almost everything we need to rebuild the analyzer properly:
1. Exact prefix forms and when to use each variant (mo- vs ma- vs mong- vs mongo-)
2. Consonant substitution rules (p→m, t→n, k→ng, etc.)
3. Vowel contraction rules (a+i=e, o+u=u, etc.)
4. The full verbal tense/aspect system
5. The complete affix inventory with meanings
