# OMW pronouns

A multilingual wordnet of pronouns, built the same way as the
[KinDiv kinship wordnet](https://github.com/fcbond/KinDiv): every concept is a
bundle of features with a compositional code, shared by all languages and proposed
to the Collaborative Interlingual Index.

```
uv run ntumc_pronouns.py     # NTUMC pronoun synsets -> data/ntumc-pronouns.tsv
uv run parabank_words.py     # Parabank paradigms   -> data/parabank-lexemes.tsv
uv run tufs_pronouns.py      # TUFS pro-forms       -> data/tufs-pronouns.tsv (curated in data/tufs-curation.tsv)
uv run haspelmath_series.py  # indefinite series    -> data/haspelmath-series.tsv
uv run wordnet_words.py      # words via the ILI    -> data/wordnet-words.tsv
uv run concepts.py           # concept inventory    -> data/concepts.tsv
uv run build.py              # wn collection        -> release/omw-pronoun-0.1(.tar.xz), docs/hierarchy/data.js
uv run --with pytest --with langcodes --with language_data pytest
```

Sources are read from sibling clones: `../NTUMC` (built database), `../tufs`, and
`../parabank-pronouns` (github.com/SimonGreenhill/pronouns, pinned by commit).

## Concepts and codes

`FEATURES.md` lists every feature and gives the algebra that combines them into
codes and orders the codes into the hierarchy. `docs/hierarchy/index.html`
browses the hierarchy, grouped by part of speech and then by head (as in the
release, where each pronoun is also a hyponym of its head's feature synset),
drawing each concept as its features, with one language's
words marked on it; open it from disk, or serve `docs/` with GitHub Pages.
`build.py` writes the data it reads, `docs/hierarchy/data.js`.

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
| direction | `Loc` `Goal` `Src` |
| register (NTUMC) | `Men` `Wom` `Arch` |

- **Unmarked values** stand for their marked ones: `1` is inclusive or exclusive,
  and `Pl` is *non-singular*, as in the paper (English *we* is `1;Pl`). Where a
  dual or trial contrasts, the plural alone is `Gpl`, greater plural. `Dist` is
  *not proximal*, medial or remote: English *that* is `Dist`, Japanese *sore* is
  `Med` and *are* `Rem`, both under it. `Ent` is a person or a thing, so *who*
  (`Pers;Int`) and *what* (`Thng;Int`) are under *which* (`Ent;Int`).
- **Direction** splits place pro-forms where a language does: Czech *kde* "where"
  is `Plc;Loc;Int`, *kam* "where to" `Plc;Goal;Int`, *odkud* "where from"
  `Plc;Src;Int`. English *where* marks none, so it is `Plc;Int`, above all three.
- **Case is inflection, not meaning.** Subjective and objective are not part of
  a concept: *I* and *me* are one entry for `1;Sg`, with the case forms as
  `<Form>` variants tagged `case` (`s`, `a`, `o`, or NTUMC's `obj`).
- **The possessive is meaning.** *My* adds a relation to *I*, and Czech *můj*
  "my" inflects for case itself, so possessives are words of their own, of
  concepts coded `Poss` in the case slot. The determiner and the pronoun are
  separate concepts, as the demonstratives are: *my* is `1;Sg;Poss` (POS `a`),
  *mine* has the head `Ent` (person or thing), `Ent;1;Sg;Poss` (POS `n`), just
  as *this* the determiner is `Sg;Prox` and *this* the pronoun `Ent;Sg;Prox`.
  A possessive is not a kind of its pronoun; the shared lexicon links the two
  by `other` relations typed `possessor` and `possessive`.
- **Bound forms** (affixes) are variants of the free pronoun when their cells are
  the same, tagged `morph=bound`; otherwise they are entries of their own.

The inventory (`data/concepts.tsv`, 210 concepts; 28 possessive determiners and
8 possessive pronouns) comes
from:

- **NTUMC**: its pronoun synsets (`770000xx`), from the current database, with
  subjective and objective case removed. The feature analysis is read from the wordnet itself: the head is
  the hypernym, features are `dmnu` links to feature synsets, and *kind*/*manner*
  are `attr` links. NTUMC also tags 35 synsets outside that inventory as
  pronouns: Princeton's *here*, *there*, *everywhere*, *all*, *each*, and a few
  of its own (Indonesian *aku*, *kami*, Mandarin 其). `data/ntumc-extra.tsv`
  checks each by hand: 24 give concepts, with corrected codes and parts of speech
  (NTUMC reads *there* "a location other than here" as *other*; *everywhere* is a
  place pronoun, not an adverb), and 11 are skipped with a reason (*someone* is the
  synset *person*; *nothing* shares one with *zero*).
- **Parabank**: combinations NTUMC lacks (dual, greater plural, clusivity in the
  dual, number-neutral *you*, and their possessives), admitted by the KinDiv rule: >= 5 language
  families in >= 3 macroareas.
- **`data/extra-concepts.tsv`**: curated additions, so far seven from TUFS Japanese
  (どなた, だれか, ここ, どこか, いつか, どのような, どのぐらい), 20 from the TUFS
  curation, nine for direction (Czech, Polish, German and Russian) and two for
  time deixis, *now* (`Tim;Prox`, also TUFS 今 in 7 languages) and *then*
  (`Tim;Dist`), with curated lemmas in `data/extra-lemmas.tsv`.
- **`data/ntumc-fixes.tsv`** corrects NTUMC codes before they become concepts:
  Japanese あれ, あいつ, あちら are remote, not "distal and remote", and Mandarin
  那样 / Indonesian *begitu* are two-way distal.

**Features are synsets too** (`data/features.tsv`): each concept links to its head by
hypernymy and to its other features by `exemplifies` (NTUMC's usage-domain link).
Of the 54 feature values in use, 29 keep their Princeton ILI (*possessive* is
i69651), 23 are proposed (NTUMC's own and new ones such as *greater plural* and
Haspelmath's functions), and 2 point at doubtful Princeton senses (`check`).
Each records its Universal Dependencies value (`dc:relation="UD:Number=Grpl"`);
36 of 54 have one. Feature synsets form a hierarchy of their own, from the
values that stand for others: *distal* has the hyponyms *medial* and *remote*,
*first person* has *inclusive* and *exclusive*.

**Part of speech and lexicographer file.** Pro-forms cut across parts of speech, as
in UD (PRON/DET/ADV): pronouns are `n` (`noun.pronoun`), determiners `a`
(`adj.pronoun`: *this*, *which*, Japanese *kono*) and pro-adverbs `r`
(`adv.pronoun`: *kō* "in this way"). An entry has one part of speech, so *this* the
determiner and *this* the pronoun are separate entries. Hypernymy stays within a
part of speech: the pronoun *this* is not a kind of the determiner *this*, nor
*mine* of *my*.

**Indefinites** (`haspelmath_series.py`): Haspelmath's (1997) indefinite-pronoun
series (CLDF `cldf-datasets/haspelmathindefpro`, CC BY 4.0, 40 languages) are
function sets over his nine functions (`SK` specific known ... `FC` free choice),
which are also feature synsets. The English-based types are unions of them, from
his English data: `Asrt` (some-) = SK+SU+IRR+Q+COND, `Elec` (any-) =
Q+COND+INEG+DNEG+COMP+FC. `Neg` (no-) is not a function set: *nobody* is used in
direct negation, as *anybody* is, but carries the negation itself, so it is not
a kind of *anybody*. His sample is almost all Eurasian,
so series concepts are admitted on >= 5 families alone (4 concepts); their markers
(German *etwas*, *irgend*) are entries tagged `morph=series`.

The hierarchy is computed from the features: a concept's hypernyms are its closest
generalizations (`1e;Du` is under `1;Du` and `1e;Pl`).

The hierarchy and the feature links live in the shared lexicon `omw-pronoun`; the
language lexicons have none. Join a language synset to its concept on
`dc:identifier`:

```python
base = wn.Wordnet("omw-pronoun")
concept = {s.metadata()["identifier"]: s for s in base.synsets()}
en = wn.Wordnet("omw-pronoun-en")
we = en.synsets("we")[0]
concept[we.metadata()["identifier"]].hypernyms()  # pronoun:1+2;Pl
```

**ILI links** (`data/concept-ili.tsv`): six concepts have an exact counterpart in
CILI and carry its ILI, in the concept lexicon and in every language lexicon:
*here* `Plc;Prox` (i81667), *there* `Plc;Dist` (i81668), *now* `Tim;Prox`
(i116653), *then* `Tim;Dist` (i117639), the determiner *both* `Du;Univ` (i12555)
and *so*, *thus* `Mnr;Prox+Dist` (i18911). Only `exact` rows link; `related`
rows record near misses, such as OEWN's *someone*, which is *person* "a human
being" (the head feature `Pers`), not the indefinite pronoun. Princeton WordNet
has no personal pronouns, so most concepts have nothing to link to.

Wn's `expand="omw-pronoun"` works only for those six: it matches synsets by
ILI, and every other pronoun concept is a proposal (`ili="in"`), which has no
ILI until CILI assigns one.

## Words

- **NTUMC** (English, Mandarin, Japanese, Indonesian, Czech, ...). English case
  forms are paired with their lemma by `data/eng-paradigms.tsv`.
- **`data/extra-lemmas.tsv`**: curated words (Japanese from TUFS).
- **Existing wordnets** (`wordnet_words.py`, `data/wordnet-words.tsv`): the
  words of every Cygnet wordnet, and of the NTU wordnets, for the six concepts
  linked to the ILI, in 20 languages with a lexicon. Words of the Princeton
  synsets in `data/ntumc-extra.tsv` count with them. Nobody has checked these as
  pronouns (Indonesian *waktu* "time" comes in for *then*), so the browser shows
  them only on request, marked as unchecked.
- **Parabank Pronoun** (Greenhill et al., CC BY 4.0): one lexeme per set of
  cells sharing a row of case forms. Caveats:
  - Its gender slots are positional (English *she* is in `3sg_n`, Hindi uses them
    for proximity), so gender is trusted only where the `f` slot is used; elsewhere
    gender-split 3rd-person lexemes are dropped (172 languages).
  - Its `1` is exclusive only where the paradigm also has inclusive (`12`) cells;
    Mandarin has only 1pl *wǒmen*, which is plain `1;Pl`.
  - A genderless cell (`3p-s`) fills only genders the paradigm leaves empty:
    Spanish has both `3pl_f` *ellas* and `3p-s` *ellos*.
  - Its forms are as transcribed in each source (IPA for English, pinyin for
    Mandarin). Languages NTUMC covers use NTUMC's spellings instead; transcribed
    forms carry a `<Pronunciation>`.
- **TUFS** (`tufs_pronouns.py`, then `data/tufs-curation.tsv`): 46 Japanese
  headwords for personal pronouns, demonstratives (これ/この/ここ...),
  interrogatives (何, どこ, いつ, なぜ...) and universals, translated into 22
  languages. Headings are too loose to map by (彼女 "she" also collects *he*,
  *they*), so every form was mapped by its own meaning, with a confidence and a
  `kind`: `pronoun`, `substitute` (a kin term or title used as "I"/"you", e.g.
  Vietnamese *anh*; kept out of the build for now) or `not-proform`. Rows of kind
  `pronoun` with high or medium confidence are built (841 senses). The curation
  added 20 concepts (in `extra-concepts.tsv`), e.g. `Plc;Dist` "there" in two-way
  systems and speaker-sex *I* (Thai *phǒm*, Burmese *kyundaw*).

Every lemma and form records its script (ISO 15924, e.g. `Hani`, `Hira`, `Jpan`).

`docs/pronoun-databases.md` surveys the cross-linguistic pronoun databases.
`docs/open-questions.md` lists design points still to be decided (e.g. whether
how bare Mandarin 我 used as a possessive should be treated).
