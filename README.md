# OMW pronouns

A multilingual wordnet of pronouns, built the same way as the
[KinDiv kinship wordnet](https://github.com/fcbond/KinDiv): every concept is a
bundle of features with a compositional code, shared by all languages and proposed
to the Collaborative Interlingual Index.

```
uv run ntumc_pronouns.py     # NTUMC pronoun synsets -> data/ntumc-pronouns.tsv
uv run parabank_words.py     # Parabank paradigms   -> data/parabank-lexemes.tsv
uv run tufs_pronouns.py      # TUFS pronouns        -> data/tufs-pronouns.tsv
uv run concepts.py           # concept inventory    -> data/concepts.tsv
uv run build.py              # wn collection        -> release/omw-pronoun-0.1(.tar.xz)
uv run --with pytest --with langcodes --with language_data pytest
```

Sources are read from sibling clones: `../NTUMC` (built database), `../tufs`, and
`../parabank-pronouns` (github.com/SimonGreenhill/pronouns, pinned by commit).

## Concepts and codes

Concepts follow the componential analysis of Seah & Bond (2014), "Annotation of
Pronouns in a Multilingual Corpus of Mandarin Chinese, English and Japanese"
(ISA-10). A code lists features in the paper's order, separated by `;`, with
alternatives joined by `+`:

| slot | values |
|---|---|
| head (or person) | `Pers` `Thng` `Ent` `Plc` `Tim` `Mnr` `Rsn` `Knd` `Dur` `Qnt`; a personal pronoun has its person instead: `1` `1i` `1e` `2` `3` |
| number | `Sg` `Du` `Tr` `Pl` `Gpl` |
| gender | `M` `F` `N` |
| type | `Asrt` `Elec` `Neg` `Univ` `Int` `Refl` `Recp` `Oth` |
| formality | `Fml` `Infml` |
| politeness | `Pol` `Hon` `NHon` |
| proximity | `Prox` `Med` `Dist` `Rem` |
| register (NTUMC) | `Men` `Wom` `Arch` |

- **Unmarked values** stand for their marked ones: `1` is inclusive or exclusive,
  and `Pl` is *non-singular*, as in the paper (English *we* is `1;Pl`). Where a
  dual or trial contrasts, the plural alone is `Gpl`, greater plural.
- **Case is inflection, not meaning.** The paper's case slot is not part of a
  concept: *I*, *me*, *my* and *mine* are one entry for `1;Sg`, with the case forms
  as `<Form>` variants tagged `case` (`s`, `a`, `o`, `p`, or NTUMC's `obj`,
  `poss`).
- **Bound forms** (affixes) are variants of the free pronoun when their cells are
  the same, tagged `morph=bound`; otherwise they are entries of their own.

The inventory (`data/concepts.tsv`, 124 concepts) comes from:

- **NTUMC**: its pronoun synsets (`770000xx`), from the current database, with
  case removed. The feature analysis is read from the wordnet itself: the head is
  the hypernym, features are `dmnu` links to feature synsets, and *kind*/*manner*
  are `attr` links.
- **Parabank**: combinations NTUMC lacks (dual, greater plural, clusivity in the
  dual, number-neutral *you*), admitted by the KinDiv rule: >= 5 language
  families in >= 3 macroareas.
- **`data/extra-concepts.tsv`**: curated additions, so far seven from TUFS Japanese
  (どなた, だれか, ここ, どこか, いつか, どのような, どのぐらい).

**Features are synsets too** (`data/features.tsv`): each concept links to its head by
hypernymy and to its other features by `exemplifies` (NTUMC's usage-domain link).
25 feature values keep their Princeton ILI, 14 are proposed (NTUMC's own and new
ones such as *greater plural*), and 2 point at doubtful Princeton senses (`check`).
Each records its Universal Dependencies value (`dc:relation="UD:Number=Grpl"`);
28 of 43 have one.

**Part of speech and lexicographer file.** Pro-forms cut across parts of speech, as
in UD (PRON/DET/ADV): pronouns are `n` (`noun.pronoun`), determiners `a`
(`adj.pronoun`: *this*, *which*, Japanese *kono*) and pro-adverbs `r`
(`adv.pronoun`: *kō* "in this way"). An entry has one part of speech, so *this* the
determiner and *this* the pronoun are separate entries.

The hierarchy is computed from the features: a concept's hypernyms are its closest
generalizations (`1e;Du` is under `1;Du` and `1e;Pl`).

## Words

- **NTUMC** (English, Mandarin, Japanese, Indonesian, Czech, ...). English case
  forms are paired with their lemma by `data/eng-paradigms.tsv`.
- **`data/extra-lemmas.tsv`**: curated words (Japanese from TUFS).
- **Parabank Pronoun** (Greenhill et al., CC BY 4.0): one lexeme per set of
  cells sharing a row of case forms. Caveats:
  - Its gender slots are positional (English *she* is in `3sg_n`, Hindi uses them
    for proximity), so gender is trusted only where the `f` slot is used; elsewhere
    gender-split 3rd-person lexemes are dropped (172 languages).
  - It records one form per cell, so Mandarin *wǒmen* comes out exclusive because
    *zánmen* fills the inclusive cell.
  - Its forms are as transcribed in each source (IPA for English, pinyin for
    Mandarin). Languages NTUMC covers use NTUMC's spellings instead; transcribed
    forms carry a `<Pronunciation>`.
- **TUFS** confirms words already found (credited in `dc:source`); its other forms
  are in `data/tufs-candidates.tsv` for curation, since its headings are too loose
  to map by (彼女 "she" also collects *he*, *they*).

Every lemma and form records its script (ISO 15924, e.g. `Hani`, `Hira`, `Jpan`).

`docs/pronoun-databases.md` surveys the cross-linguistic pronoun databases.
