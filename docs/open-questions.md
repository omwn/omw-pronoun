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

The determinative and the independent possessive are separate concepts, since
they differ in meaning and syntax: *my* is `1;Sg;Poss` (POS `a`), *mine* is
`Ent;1;Sg;Poss` (POS `n`, head `Ent`: it stands for a person or thing), as the
demonstrative determinative *this* (`Sg;Prox`) and pronoun (`Ent;Sg;Prox`) are.
Parabank does not tell them apart; its possessives go to the determinatives.

Where one word does both jobs (Czech *můj* "my" and "mine"), it is a
determinative only. Standing alone it is the determinative without its noun, by the
general rule that lets adjectives stand for nouns (a pumping rule), not a
second sense. A pronoun concept gets words only where a language has a
distinct form (English *mine* beside *my*).

**Still open.**
- By that rule, NTUMC's pronoun senses of words that are also its determinatives
  (English *his*, *its*; Mandarin 你的, 他的 under both) are the determinative
  without a noun. Drop them from the pronoun concepts?
- NTUMC lists bare Mandarin 我, 你, 他 as possessive determinatives (*我妈妈*
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
  determinative is agreement, so they are forms of one lemma *ten*, as are
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

- Decided 2026-10-25: every place and time pro-form that is not a noun has a
  direction, and is a pro-adposition (POS `p`). The unmarked direction `Dir`
  (at, to or from; the ERG's `loc_nonsp`) is for words whose coverage has not
  been checked; English and French *here/there/where* (*ici/là/où*) and
  Spanish *aquí/ahí/allí* are `Loc+Goal`, English *now/then/when* `Tim;…;Loc`
  (FEATURES.md, rules 3 to 5). The `:r` adverb twins are gone.
- Future work: time pro-forms mark direction too. Czech *dokdy* "until when"
  (`Tim;Int;Goal`) and *odkdy* "since when" (`Tim;Int;Src`) need feature
  synsets for the temporal goal and source (until, since) before they can be
  added.
- `Goal` links to i82007 "the end (as of a race or journey)" and `Src` to i81759
  "the place where something begins": senses of place, not semantic roles,
  unlike `Loc` (locative role, i69757). OEWN has no goal or source role under
  *semantic role* (i69752). Propose them, as `Dir` is proposed?
- The other European languages' place words are `Dir` until checked
  (Portuguese *aqui/aí/ali*, Italian *qui/qua*, German *da*).

## Time deixis

*now* (`Tim;Prox`) and *then* (`Tim;Dist`) are curated, like direction: no
source records demonstrative time. *now* has TUFS 今 (concept 8987) in seven
languages (Arabic, Syrian Arabic, French, Japanese, Malay, Burmese, Urdu) and
curated words in seven more; *then* has curated words only, in English, Czech,
German, Polish, Russian and Mandarin. Like *here* and *there*, each is a noun
(`Tim;Prox`, OEWN's *now* "the momentary present") and a pro-adposition
(`Tim;Prox;Dir`, English *now* `Tim;Prox;Loc`), which UD tags ADV.

- *then* is taken as "at that time" (Czech *tehdy*, German *damals*). Is
  sequential *then* (German *dann*, Czech *pak*) the same concept, or not a
  pro-form at all?
- German *damals* and Czech *tehdy* are past only, English *then* past or
  future. Does distal time split by tense, as place splits by direction?
- Japanese has no single word for *then*: その時, あの時 are phrases. Is that a gap?
- Nothing covers both, as `Plc;Prox+Dist` covers both places, so *now* and *then*
  are tops of the hierarchy.

- Decided 2026-10-21: direction marked by case is meaning, like the possessive,
  not inflection like subjective and objective. Turkish *nerede*, *nereye*,
  *nereden*, *burada* ... are coded `Plc;Int;Loc` ...; Japanese どこへ is a
  phrase and stays out. Still to check: Mongolian *хаана* "where" against
  *хаашаа* "where to" and *хаанаас* "from where", and Burmese forms with -က
  (ဟိုက "over there, from there"), which TUFS leaves plain.
- Czech and Polish *tam* "there, to there" do not split location from goal, so
  Czech *tam* is `Plc;Dist;Loc+Goal`; Russian *там* and German *dort* are
  location only (`Plc;Dist;Loc`).
- English *whither*, *whence*, *hither*, *thither*, *hence*, *thence* would be
  archaic (`Arch`) members of the same concepts; not added.
