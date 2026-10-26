# OMW pronouns

A multilingual wordnet of pronouns, built the same way as the
[OMW kinship wordnet](https://github.com/omwn/omw-kinship): every concept is a
bundle of features with a compositional code, shared by all languages and proposed
to the Collaborative Interlingual Index.

```
uv run ntumc_pronouns.py     # NTUMC pronoun synsets -> data/ntumc-pronouns.tsv
uv run parabank_words.py     # Parabank paradigms   -> data/parabank-lexemes.tsv
uv run tufs_pronouns.py      # TUFS pro-forms       -> data/tufs-pronouns.tsv (curated in data/tufs-curation.tsv)
uv run haspelmath_series.py  # indefinite series    -> data/haspelmath-series.tsv
uv run wordnet_words.py      # words via the ILI    -> data/wordnet-words.tsv
uv run concepts.py           # concept inventory    -> data/concepts.tsv
uv run build.py              # wn collection        -> release/omw-pronoun-0.2(.tar.xz), docs/hierarchy/data.js
uv run facts.py              # the paper's figures  -> data/facts.json
uv run --with pytest --with langcodes --with language_data pytest
```

Sources are read from sibling clones: `../NTUMC` (built database), `../tufs`, and
`../parabank-pronouns` (github.com/SimonGreenhill/pronouns, pinned by commit).

## The Cygnet site

`docs/` is also a [Cygnet](https://github.com/omwn/cygnet) site, browsing the
collection with OEWN as its English base (configured in `etc/`):

```
bash cygnet.sh   # release/omw-pronoun-0.2/ -> docs/pronoun-cygnet.db.gz, docs/pronoun-provenance.db.gz
bash run.sh      # serve docs/ locally
```

It needs a clone of Cygnet next to this repository. The databases are
gitignored: attach them to the GitHub release, and the Pages workflow
(`.github/workflows/pages.yml`) downloads them when it deploys. Each concept has
a stable link by its synset id, which is what an ILI proposal's `dc:source`
points to: `https://omwn.org/omw-pronoun/#/search?id=omw-pronoun-1-Pl`.
The six concepts linked to an existing ILI are merged into the CILI concept, so
they are reached by searching for the ILI instead (`#/search?q=i81667`).

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
| domain | `Two`: chosen from two (*either*, *both*, Japanese どちら "which of two") |
| gender | `M` `F` `N` |
| type | `Asrt` `Elec` `Neg` `Univ` `Int` `Refl` `Recp` `Oth` |
| formality | `Fml` `Infml` |
| politeness | `Pol` `Hon` `NHon` |
| proximity | `Prox` `Med` `Dist` `Rem` |
| direction | `Dir` `Loc` `Goal` `Src` |
| register (NTUMC) | `Men` `Wom` `Arch` |

- **Unmarked values** stand for their marked ones: `1` is inclusive or exclusive,
  and `Pl` is *non-singular*, as in the paper (English *we* is `1;Pl`). Where a
  dual or trial contrasts, the plural alone is `Gpl`, plural beyond the dual (not
  the "greater plural" of Corbett and UD, which means "many"). `Dist` is
  *not proximal*, medial or remote: English *that* is `Dist`, Japanese *sore* is
  `Med` and *are* `Rem`, both under it. `Ent` is a person or a thing, so *who*
  (`Pers;Int`) and *what* (`Thng;Int`) are under *which* (`Ent;Int`).
- **Direction** is the relation of an adposition to its place or time, read
  by head: at, to or from a place; at, until or since a time. `Dir` leaves it
  unspecified (the ERG's `loc_nonsp`), and narrower codes are given only where a
  word's coverage is known (`data/word-direction.tsv`): Czech *kde* "where" is
  `Plc;Int;Loc`, *kam* "where to" `Plc;Int;Goal`, *odkud* "where from"
  `Plc;Int;Src`; English *where* covers at and to, so it is `Plc;Int;Loc+Goal`,
  above *kde* and *kam* but not *odkud*, and all are under `Plc;Int;Dir`. A code
  without a direction is a noun, not unspecified for it (FEATURES.md, rules 3
  and 5).
- **Case is inflection, not meaning.** Subjective and objective are not part of
  a concept: *I* and *me* are one entry for `1;Sg`, with the case forms as
  `<Form>` variants tagged `case` (`s`, `a`, `o`, or NTUMC's `obj`).
- **The possessive is meaning.** *My* adds a relation to *I*, and Czech *můj*
  "my" inflects for case itself, so possessives are words of their own, of
  concepts coded `Poss` in the case slot. The determinative and the pronoun are
  separate concepts, as the demonstratives are: *my* is `1;Sg;Poss` (POS `a`),
  *mine* has the head `Ent` (person or thing), `Ent;1;Sg;Poss` (POS `n`), just
  as *this* the determinative is `Sg;Prox` and *this* the pronoun `Ent;Sg;Prox`.
  A possessive is not a kind of its pronoun; the shared lexicon links the two
  by `other` relations typed `possessor` and `possessive`.
- **Bound forms** (affixes) are variants of the free pronoun when their cells are
  the same, tagged `morph=bound`; otherwise they are entries of their own.

The inventory (`data/concepts.tsv`, 241 concepts: 144 pronouns, 53 determinatives,
35 adpositions and 9 adverbs; 28 possessive determinatives and
8 possessive pronouns) comes
from:

- **NTUMC**: its pronoun synsets (`770000xx`), from the current database, with
  subjective and objective case removed. The feature analysis is read from the wordnet itself: the head is
  the hypernym, features are `dmnu` links to feature synsets, and *kind*/*manner*
  are `attr` links. NTUMC also tags 35 synsets outside that inventory as
  pronouns: Princeton's *here*, *there*, *everywhere*, *all*, *each*, and a few
  of its own (Indonesian *aku*, *kami*, Mandarin 其). `data/ntumc-extra.tsv`
  checks each by hand: 24 give concepts, with corrected codes and parts of speech
  (NTUMC reads *there* "a location other than here" as *other*), and 11 are skipped with a reason (*someone* is the
  synset *person*; *nothing* shares one with *zero*).
- **Parabank**: combinations NTUMC lacks (dual, plural beside a dual, clusivity in the
  dual, number-neutral *you*, and their possessives), admitted by the KinDiv rule: >= 5 language
  families in >= 3 macroareas.
- **`data/extra-concepts.tsv`**: curated additions, so far 14 from TUFS Japanese
  (どなた, だれか, ここ, どこか, いつか, どのような, どのぐらい, and the place
  senses of こちら/そちら/あちら/どちら, polite, and こっち/そっち/あっち, casual:
  `Plc;Fml;Prox`, `Plc;Infml;Prox` ...), casual どっち "where" (`Plc;Int;Infml`,
  not in TUFS), 20 from the TUFS curation, one from English (*yours*), nine for direction (Czech, Polish, German
  and Russian; NTUMC now has Czech *kde* and *kam* too) and two for time deixis, *now* (`Tim;Prox`, also TUFS 今 in 7
  languages) and *then* (`Tim;Dist`), with curated lemmas in
  `data/extra-lemmas.tsv`.
- **`data/ntumc-fixes.tsv`** corrects NTUMC codes before they become concepts.
  NTUMC fixed all of them upstream (ff224b3, 0916c58), so it is empty for now.
  Its `drop` column removes a lemma from a synset.

**Features are synsets too** (`data/features.tsv`): each concept links to its head by
hypernymy and to its other features by `exemplifies` (NTUMC's usage-domain link).
Of the 57 feature values in use, 31 keep a Princeton ILI (*possessive* is
i69651), and 26 are proposed (NTUMC's own and new ones such as *plural (beyond
the dual)*, *one of two*, *non-specific locative role*, *archaic* and Haspelmath's
functions). NTUMC linked two features to the wrong Princeton senses: *thing* to
"an artifact" (i60191), now "an entity that is not named specifically" (i60192),
and *archaic* to *antediluvian* "so extremely old…" (i8971), now proposed, since
OEWN has no sense for words no longer in everyday use. The locative of a time code
links to *temporal role* (i69760), of a place code to *locative role* (i69757).
The proposed *non-specific locative role* (`Dir`) is above both, and is placed
under Princeton's *semantic role* (i69752), which is included only for that.
Each records its Universal Dependencies value (`dc:relation="UD:Person=1|Clusivity=In"`)
where there is one. Feature synsets form a hierarchy of their own, from the
values that stand for others: *distal* has the hyponyms *medial* and *remote*,
*first person* has *inclusive* and *exclusive*.

**Part of speech and lexicographer file.** Pro-forms cut across parts of speech:
pronouns are `n` (`noun.pronoun`), determinatives `a` (`adj.pronoun`: *this*,
*which*, Japanese *kono*), adpositions `p` (`adp.pronoun`: *here*, *hither*,
*now*, *everywhere*) and adverbs `r` (`adv.pronoun`: *kō* "in this way",
*how*, *why*, *how long*). An adposition is a place or time pro-form with a
direction: Huddleston and Pullum (2002, ch. 7) treat *here*, *there* and *where*
as intransitive prepositions, and such a word stands for a prepositional phrase
(*here* ≈ *at this place*). Universal Dependencies tags them ADV. An entry has
one part of speech, so *this* the determinative and *this* the pronoun are separate
entries, linked by `derivation` (as are *here* the noun and *here* the
adposition). Hypernymy stays within a part of speech: the pronoun *this* is
not a kind of the determinative *this*, nor *mine* of *my*. In the shared
lexicon, the concepts of such a pair are linked instead by `other` relations
typed `pronoun` and `determinative` (`Sg;Prox` ↔ `Ent;Sg;Prox`), as possessives
are linked to their pronouns (`possessor`, `possessive`) and nouns to their
adpositions (`adposition`, `noun`). The category is called
*determinative* after Huddleston and Pullum (2002); *determiner* is the function.

Place and time pro-forms are nouns or adpositions according to the language
(`data/pro-form-pos.tsv`). *hither*, *whence*, *everywhere* and *sometime* are
only adpositions. *here*, *there*, *where*, *now*, *then* and *when* are
both in English, and OEWN has both senses, but Japanese *doko* is only a noun
(*doko ni* is a phrase). So eight codes have a noun concept (`Plc;Prox`, with
OEWN's noun ILI) and an adposition with no direction specified
(`Plc;Prox;Dir`), linked by `other` relations typed `noun` and
`adposition`; words whose direction is known get a narrower concept
(`Plc;Prox;Loc+Goal` for English *here*). OEWN's adverb ILIs link to the
concept their definition matches: *here* "in or at this place" (i18823) is
`Plc;Prox;Loc`, *now* "at the present moment" (i18426) is `Tim;Prox;Loc`,
*everywhere* "to or in any or all places" (i18291) is `Plc;Univ;Loc+Goal`.
`data/word-pos.tsv` says which a language's word lexicalizes, by lemma or for
the whole language (Japanese, Korean, Chinese, Turkish, Indonesian, Thai: nouns);
a language it does not list is taken as using an adposition. Manner, reason
and duration pro-forms have no direction and are adverbs.

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
(i116653), *then* `Tim;Dist` (i117639), the determinative *both* `Du;Univ` (i12555)
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

## References

Flickinger, Dan, Emily M. Bender and Stephan Oepen (2014). Towards an
Encyclopedia of Compositional Semantics: Documenting the Interface of the English
Resource Grammar. In *Proceedings of LREC'14*, 875–881. Implicit locatives
(`loc_nonsp`): https://github.com/delph-in/docs/wiki/ErgSemantics_ImplicitLocatives

Huddleston, Rodney and Geoffrey K. Pullum (2002). *The Cambridge Grammar of the
English Language*. Cambridge University Press. Chapter 7, Prepositions and
preposition phrases (Pullum and Huddleston).
