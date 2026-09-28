# Pronoun databases: is there a "Kinbank for pronouns"?

Research date: 2026-09-28. Everything below was checked directly (repo clone, file download, or page fetch) unless marked *unverified*.

## Short answer

Yes. The **Parabank Pronoun Dataset** (Simon Greenhill et al., ANU; `github.com/SimonGreenhill/pronouns`) is the pronoun sibling of Kinbank. Both come from the same Parabank project (Evans, Greenhill, Quinn). It is a **CLDF Wordlist, CC BY 4.0, 733 varieties / 681 Glottocodes, 46,915 forms**, with **one form per paradigm cell**. Cells are person × number × gender × role (A/S/O/Possessive). This is the same design as Kinbank: to get a form's meaning, collect every cell where that form appears. No other resource we found records pronoun forms per cell at this scale under an open licence.

---

## Ranked resources

### 1. Parabank Pronoun Dataset (CLDF): best fit

- **URL:** https://github.com/SimonGreenhill/pronouns (CLDF in `cldf/`); web front end https://pdb.simon.net.nz ("Pronoun Paradigms Database", 658 paradigms listed on the site)
- **Licence:** CC BY 4.0 (LICENSE file, GitHub licence field, site footer)
- **Authors:** Simon J. Greenhill, Wolfgang Barth, Kyla Quinn, Nick Evans, and 15 other coders (CONTRIBUTORS.md)
- **Format:** CLDF Wordlist built with pylexibank (`forms.csv`, `parameters.csv`, `languages.csv`, `sources.bib`). Raw per-language CSVs are in `raw/<Family>/<Language> <glottocode>.csv`.
- **Coverage (my count from the clone):** 735 language rows, 681 Glottocodes. By area: Papunesia 258, Africa 138, Eurasia 123, Australia 96, South America 82, North America 35. Analect: 722 Free (independent pronouns) and 13 Bound. 603 sources, 100% Glottolog-linked, 0% Concepticon-linked.
- **Release status:** no GitHub releases and no Zenodo DOI yet (there is a `.zenodo.json`, but no release has been cut). Last commit "rebuild", updated 2026-08-03. Cite the commit hash.
- **Records:** forms per cell. Each row has `Language_ID, Parameter_ID, Value, Form, Comment, Source, Paradigm_ID`. The parameters table decomposes each cell into `Person` (1, 12, 2, 3), `GrammaticalNumber` (sg, du, tr, pl), `Gender` (M, F, N) and `Alignment` (A, S, O, P).
- **Cell notation (IDs):** `1sg_a`, `1du_s`, `1pl_o`, `12du_p`, `12pl_a`, `2sg_s`, `3sg_m_a`, `3sg_f_o`, `3sg_n_p`, `3du_m_s`, `3pl_f_a`, `1tr_s` … plus legacy `3d-a`, `3p-s` (3rd dual/plural without gender). Person `1` means 1st exclusive ("1st (excl) Person …") and `12` means inclusive. P means **Possessive**, not Patient: the website column is "Poss." and Tok Pisin P = *biloŋ mi*.
- **Paradigm per language:** 1/12/2/3 × sg/du/pl (+tr) × A/S/O/P, with 3rd person optionally split by gender. The full grid is filled even where a language has no such category. Czech and English put the plural form into the dual cells, and English puts *we* into both 12pl and 1pl. So the set-of-cells method works as it does for Kinbank: English *wi:* = {1du,1pl,12du,12pl}_{A,S} = "1 non-singular, nominative", Tok Pisin *yumi* = {12pl}, Tagalog *kata* = {12du_s}.
- **Numbers:** inclusive differs from exclusive (12pl_s ≠ 1pl_s) in 307 varieties. 1du_s = 1pl_s (no dual) in 493 of 733. 4,154 cells hold more than one form (variants separated by `;/,`). ∅ is used for zero forms.
- **Caveats (checked):**
  - **Gender slots are really "gender 1 / gender 2".** The site shows "3rd Person Singular Gender 1/Gender 2", and these are mapped to `m`/`n`. English *she* (ši:) sits in `3sg_n_*`. In 157 varieties the m and n cells differ but f is empty. Do not read `n` as neuter without checking.
  - Trial is filled for only 2 languages. There are **no cells for paucal, politeness/honorifics, speaker sex, emphatic or clitic series, or case beyond A/S/O/Poss**. These show up only in free-text comments: "formal" 50 times, "polite" 34, "clitic" 32, "emphatic" 15, "honorific" 4.
  - Data-quality spot check: the variety named "Indonesian" (`indonesian_standard`) contains colloquial Jakartan forms (*elu*, *gua*). Expect some noise, as in Kinbank.
- **Usefulness:** very high. It works like Kinbank, uses the same Parabank/Glottobank team and pipeline, is CLDF and CC BY, and has forms per cell. It can be dropped into the KinDiv code path almost unchanged (parameters → feature bundles; a form's cell set → concept).

### 2. Ivani (2026), "The semantic space of independent personal pronouns: a typological dataset"

- **URL:** https://zenodo.org/records/22557543 (DOI 10.5281/zenodo.22557543), v1.0, 2026-09-07
- **Licence:** CC BY-SA 4.0 (ShareAlike, so derived data must stay SA)
- **Coverage:** 385 languages (Glottocodes)
- **Format:** plain CSV + PDF documentation + .bib. **Not CLDF.**
- **Records:** **partitions only, no forms.** For each language, a "signature" groups the 11 meanings that share an identical form, e.g. Abun `(1),(1+,12),(1++,12+),(2),(2+),(2++),(3),(3+),(3++)`. Gender, case and animacy are deliberately left out.
- **Notation (worth adopting or mapping to):** Cysouw/Harbour referential notation. `1` speaker alone; `1+` speaker + one other; `1++` speaker + more than one other; `12` speaker + addressee; `12+` speaker + addressee + ≥1 other; `2`, `2+`, `2++`; `3`, `3+`, `3++`. (The documentation lists 11 meanings, but the Abun signature shows no `12++`; the space is 1, 1+, 1++, 12, 12+, 2, 2+, 2++, 3, 3+, 3++.)
- **Source:** derived from *tymber* (Ivani & Zakharko 2019, https://github.com/jkivani/tymber, CC BY 4.0). The public tymber CSVs contain only number-category flags and reference types, **not pronoun forms**.
- **Usefulness:** medium. It gives no words, but it provides a clean language-independent concept inventory, and it can validate the syncretism patterns we compute from Parabank.

### 3. Lexibank wordlists with pronoun concepts (forms, few cells)

- **ASJP** (https://github.com/lexibank/asjp, CC BY 4.0, CLDF, ~11,500 doculects): concepts `*I` → Concepticon 1209 I, `*you` → 1215 THOU, `*we` → 1212 WE. That covers 3 cells, in ASJPcode transcription.
- **IDS** (https://github.com/lexibank/ids, CC BY 4.0, CLDF, ~320 languages): I (1209), you sg (THOU 1215), he/she/it (262), we (1212), we incl (1131), we excl (1130), you pl (YOU 1213), they (817).
- **Usefulness:** low to medium. There are many languages, but only nominative sg/pl (plus clusivity in IDS). A Concepticon gloss such as WE does not tell you whether the form also covers the dual. Good for coverage-filling, poor for exact meaning.

### 4. Concepticon pronoun concept sets (concepts, no forms)

- **URL:** https://github.com/concepticon/concepticon-data (v3.4.0), CC BY 4.0
- There are about **33 personal-pronoun concept sets**. Nominative: I 1209, THOU 1215, WE 1212, YOU 1213, HE 1211, SHE 1834, IT 169, THEY 817, HE OR SHE 2642, HE OR SHE OR IT 262. Clusivity/number: WE (INCLUSIVE) 1131, WE (EXCLUSIVE) 1130, WE TWO 2634, WE TWO (INCLUSIVE) 2637, WE TWO (EXCLUSIVE) 2636, YOU TWO 2111, THEY TWO 2635. Politeness: YOU (FORMAL ADDRESS) 2844, THOU (HONORIFIC) 3292, YOU (HONORIFIC) 3293. Oblique: ME 2301, THEE 2304, US 2310, YOU (OBLIQUE) 2312. Possessive: MY 2090, YOUR 2091, YOUR (SINGULAR) 732, YOUR (PLURAL) 2274, OUR 780, HIS OR HER 2092, HIS 2473, HER 2474, THEIR 2400.
- The granularity is uneven and English-centred: no trial or paucal, and no 3rd-person gender beyond HE/SHE. Demonstratives and interrogatives: THIS 1214, THAT 78, HERE 136, THERE 1937, WHO 1235, WHAT 1236, WHO OR WHAT 2147.
- **Usefulness:** useful as a **linking layer** (map our feature-bundle concepts to Concepticon IDs where one exists), not as a data source. Parabank's pronoun dataset is currently 0% Concepticon-mapped, so we would be adding value there.

### 5. Typological feature databases (feature values only, no forms)

All are CLDF StructureDatasets under CC BY 4.0. They are useful for validating which distinctions a language makes, and useless for forms.
- **WALS** (https://github.com/cldf-datasets/wals):
  - 39A Inclusive/Exclusive in independent pronouns (Cysouw, 200 languages)
  - 40A the same in verbal inflection (Cysouw)
  - 41A, 42A demonstratives (Diessel)
  - 43A Third-person pronouns and demonstratives (Bhat, 225)
  - 44A Gender in independent personal pronouns (Siewierska, 378)
  - 45A Politeness distinctions in pronouns (Helmbrecht, 207)
  - 136A/137A M-T and N-M pronouns (Nichols & Peterson, 230 each)
  - 46A Indefinite pronouns (Haspelmath), 47A Intensifiers and reflexives
- **Grambank** (https://github.com/grambank/grambank, ~2,400 languages):
  - GB028 inclusive/exclusive; GB030 gender in 3rd-person independent pronouns; GB031 dual for all persons in pronouns
  - GB196 m/f in 2nd person; GB197 m/f in 1st person (which covers speaker/addressee sex)
  - GB415 politeness in 2nd person; GB167 logophoric pronoun; GB073 oblique case on pronouns; GB313 special possessive pronouns
- **AUTOTYP** (https://github.com/autotyp/autotyp-data, CC BY 4.0, CSV/YAML, not CLDF): Clusivity module (`HasClusivityAsPerson`), PersonNumberCategories in GrammaticalRelations, and verb-agreement summaries. No pronoun forms.
- **Usefulness:** low for extracting words. Grambank GB196/GB197/GB415 and WALS 45A are the only open sources that flag **politeness and speaker/addressee sex**, which Parabank lacks.

### 6. Haspelmath (1997) Indefinite Pronouns, if we extend beyond personal pronouns

- https://github.com/cldf-datasets/haspelmathindefpro, CC BY 4.0, CLDF StructureDataset, 40 languages
- Records indefinite-pronoun **series and constructions (with forms)** against the 9 functions of the implicational map: specific-known, specific-unknown, irrealis non-specific, question, conditional, indirect negation, direct negation, comparative, free choice. Here a series covers a set of functions, so the same "meaning = set of cells" logic applies. It is small but well structured.

### Checked and not usable, or not found

- **Cysouw (2003), *The Paradigmatic Structure of Person Marking*** (OUP): about 400 languages of paradigms in the book and thesis (PDF at http://cysouw.de/home/books_files/cysouwTHESIS.pdf). **No machine-readable or CLDF release found.** Its content survives as WALS 39A/40A, and its notation (1, 1+2, 1+3, 2+3 …) underlies the Ivani and Harbour notation.
- **Calgary Pronoun Database** (Bliss & Ritter 2001, "Developing a database of personal and demonstrative pronoun paradigms", 123 languages): described only in the paper. **No public download found.**
- **Parabank (glottobank.org):** the umbrella project covering free pronouns, verb agreement and kin terms, with demonstratives and interrogatives planned. `kinbank/parabank` holds only the kinship part, and `parabank/parabank-kinship-code` is kinship code. The pronoun part **is** resource #1.
- Searches for "PronounBank", "World Pronoun", "PeLiCo", a Surrey person database, or a Siewierska/Bhat forms database turned up nothing verifiable. Siewierska, Bhat, Helmbrecht and Diessel exist as WALS chapters (features only). I found **no open demonstrative-forms-per-cell database**.
- **Wordnets / OMW:** PWN and OEWN have no personal-pronoun synsets. GWA documentation (https://globalwordnet.github.io/gwadoc/) has `restricts`/`restricted_by` relations meant for pronoun features ("'medial' or 'proximal' in pronouns … 'male' for male personal pronouns"). It uses the NTU closed-class synset range as an example (`this-n 77000061-n`), which came from NTU-MC pronoun annotation (Seah & Bond 2014, componential analysis for English/Chinese/Japanese). No multilingual pronoun synset inventory is linked to CILI.

---

## Notation options for our concept IDs

| Scheme | Example cells | Pros | Cons |
|---|---|---|---|
| Parabank | `1sg_s`, `12du_a`, `3sg_f_o`, `2pl_p` | matches the data source directly; role and gender built in | "1" = exclusive; `n` really means "gender 2"; tied to sg/du/pl labels |
| Ivani / Cysouw–Harbour | `1`, `1+`, `1++`, `12`, `12+`, `2+`, `3++` | label-free referential composition; handles minimal/augmented systems | no gender, role or politeness; `+`/`++` is awkward in IDs |
| Leipzig-style | `1SG`, `1PL.EXCL`, `1+2DU`, `3SG.F.ACC` | familiar to linguists | label-based (assumes sg/du/pl) |

**Suggestion:** keep a feature-bundle ID in Parabank style, since it maps 1:1 to the data, extended with optional features (e.g. `2sg.pol`, `1sg.fsp` for female speaker). Store the Cysouw/Harbour referential composition (`1+`, `12`, …) as a property of each concept, so that non-singular forms can be matched as unions of cells. This parallels how KinDiv uses Murdock kin-type strings.

## Recommendation

Use the **Parabank Pronoun Dataset** (CLDF, CC BY 4.0, 681 languages, forms per cell) as the Kinbank analogue.
- Build concepts from its parameter grid, collapsing A/S/O/P into case/role features.
- Compute each form's cell set per language and match it to the most specific concept that covers exactly those cells. This is the same algorithm as for kin terms.
- Treat the `m`/`n` gender slots as "gender 1/2" until checked.
- Link concepts to Concepticon IDs (about 33 pronoun sets) where they exist.
- Cross-check the syncretism patterns against Ivani (2026).
- Add politeness and speaker-sex concepts later from language-specific comments plus Grambank GB196/GB197/GB415. No open forms database covers those.
- The dataset has no DOI yet, so pin a commit, and consider asking Simon Greenhill to cut a Zenodo release.
