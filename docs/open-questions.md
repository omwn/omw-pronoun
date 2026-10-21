# Open questions

Design points that are not settled. Each says what the build does now.

## 1. Possessives

**Decided (October 2026).** Possessives are concepts of their own, not case forms:
*my* adds a relation to *I*, and Czech *můj* inflects for case itself, so it
needs its own lemma. The code keeps `Poss` in the case slot (`1;Sg;Poss`);
subjective and objective are still inflection. Parabank's `p` cells are lexemes
of their own, grouped by shared form (Czech *jeho* is `3;Sg;M+N;Poss`). The
shared lexicon links each possessive to its pronoun with `other` relations
typed `possessor` and `possessive`, and a possessive is never a hyponym of its
pronoun.

The determiner and the independent possessive are separate concepts, since
they differ in meaning and syntax: *my* is `1;Sg;Poss` (POS `a`), *mine* is
`Ent;1;Sg;Poss` (POS `n`, head `Ent`: it stands for a person or thing), as the
demonstrative determiner *this* (`Sg;Prox`) and pronoun (`Ent;Sg;Prox`) are.
Parabank does not tell them apart; its possessives go to the determiners.

Where one word does both jobs (Czech *můj* "my" and "mine"), it is a
determiner only. Standing alone it is the determiner without its noun, by the
general rule that lets adjectives stand for nouns (a pumping rule), not a
second sense. A pronoun concept gets words only where a language has a
distinct form (English *mine* beside *my*).

**Still open.**
- By that rule, NTUMC's pronoun senses of words that are also its determiners
  (English *his*, *its*; Mandarin 你的, 他的 under both) are the determiner
  without a noun. Drop them from the pronoun concepts?
- NTUMC lists bare Mandarin 我, 你, 他 as possessive determiners (*我妈妈*
  "my mother"), so they are lemmas of `1;Sg;Poss` etc. as well as of the
  pronoun. Is that a sense, or the pronoun in a possessive construction?
- Possessives inflect (Czech *můj*, *mého*, *mému*...), but no source gives their
  paradigms yet, so they have no `<Form>`s.

## 2. Pronoun substitutes and address terms

Kin terms and titles used as pronouns (Vietnamese *anh*, *chị*; Burmese
*ɲìlé*) are in `data/tufs-curation.tsv` with kind `substitute` and are not
built. They connect the kinship and pronoun wordnets: *anh* has a kin sense
(`El;Br`) and a pronoun use (`2;Sg`). WN-LMF has no sense relation for "used as";
data: github.com/matbahasa/ProSub (Nomoto et al. 2021; Okano et al. 2022).

## 3. Language tags that do not match Cygnet

Parabank's "Serbian/Croatian" (`hbs`, built as `sh`) and Malay (`zlm`) cover
Cygnet's Croatian (`hr`) and Standard Malay (`zsm`) only approximately. Relabel,
or leave them and note the mapping?

## 4. Doubtful analyses inherited from NTUMC

- Japanese こちら/そちら/あちら and こっち were coded dual (`Ent;Du;Fml;Prox` ...).
  They are not: "this one (polite)" is one thing, not two, and そっち/あっち had no
  dual. Fixed upstream in NTUMC ff224b3, which marks them "of two" (77010009-n). Their
  commonest sense is place or direction ("here, this way": TUFS translates them
  as *here*, *there*, *where* in over 20 languages), now the concepts
  `Plc;Fml;Prox` ... (polite) and `Plc;Infml;Prox` ... (casual), from the TUFS
  headwords; NTUMC has no synset for it. The "one of two" sense is now the domain feature `Two`
  (`Ent;Two;Fml;Prox`, どちら `Ent;Two;Int;Fml`), as for *either*, *neither*
  and *both*.
- NTUMC links あれ, あいつ, あちら (77000059-n, 77000048-n, 77000070-n) to both
  *distal* and *remote*; the a- series is remote. Fixed upstream in NTUMC
  ff224b3; wnja's `data/wn-ntumc-jpn.xml` is still to be re-exported.
- 77000079-a `Sg;Dist` had Mandarin 哪 "which"; removed in NTUMC ff224b3.
- Czech *ten*, *ta*, *to* are three NTUMC lemmas of `Sg;Dist`. Gender on a
  determiner is agreement, so they are forms of one lemma *ten*, as are
  *tento*/*tato*/*toto*; and *ten* is the unmarked demonstrative (*tamten* is
  the distal one).
- どんな is `Mnr;Int` in NTUMC but arguably `Knd;Int` ("what kind of").
- Two feature synsets point at wrong Princeton senses (*thing* as an artifact,
  *archaic* as antediluvian); see bond-lab/NTUMC#8.

## 5. Mandarin 谁 as an indefinite

谁 is also "someone" (*wh*-indefinite); it is mapped only to `Pers;Int`.
The same holds for 什么 "something". Should *wh*-indefinites get the indefinite
concept too, or is that a use rather than a sense?

## 6. Admission of Haspelmath's series

Haspelmath's sample is almost all Eurasian, so indefinite series are admitted on
five families alone, without the macroarea test. Revisit with a wider sample.

## 7. Direction

Place pro-forms split by direction where a language has separate words: Czech
*kde*/*kam*/*odkud*, German *wo*/*wohin*/*woher*, Russian *где*/*куда*/*откуда*
(`Plc;Int;Loc`, `Plc;Int;Goal`, `Plc;Int;Src`). The nine direction concepts are
curated, from four Indo-European languages; neither Parabank nor Haspelmath's
CLDF data records direction.

## Time deixis

*now* (`Tim;Prox`) and *then* (`Tim;Dist`) are curated, like direction: no
source records demonstrative time. *now* has TUFS 今 (concept 8987) in seven
languages (Arabic, Syrian Arabic, French, Japanese, Malay, Burmese, Urdu) and
curated words in seven more; *then* has curated words only, in English, Czech,
German, Polish, Russian and Mandarin. They are pronouns (`n`), like *here* and
*there* (`Plc;Prox`, `Plc;Dist`), though English and UD treat them as adverbs.

- *then* is taken as "at that time" (Czech *tehdy*, German *damals*). Is
  sequential *then* (German *dann*, Czech *pak*) the same concept, or not a
  pro-form at all?
- German *damals* and Czech *tehdy* are past only, English *then* past or
  future. Does distal time split by tense, as place splits by direction?
- Japanese has no single word for *then*: その時, あの時 are phrases. Is that a gap?
- Nothing covers both, as `Plc;Prox+Dist` covers both places, so *now* and *then*
  are tops of the hierarchy.

- Where direction is a semantic case (Turkish *nerede*, *nereye*, *nereden*;
  Japanese どこへ), is it inflection, like subjective and objective, or meaning,
  like the possessive? The TUFS Turkish rows are still plain `Plc;Int` and
  `Plc;Prox`/`Plc;Dist`.
- Czech and Polish *tam* "there, to there" do not split location from goal, so
  they stay `Plc;Dist`; Russian *там* and German *dort* are location only.
- English *whither*, *whence*, *hither*, *thither*, *hence*, *thence* would be
  archaic (`Arch`) members of the same concepts; not added.
