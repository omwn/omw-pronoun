# Pronoun features

Every concept is named by a code that lists its features, after the
componential analysis of Seah & Bond (2014): `1e;Du` is "we two, not you",
`Ent;Sg;Prox` is the pronoun *this*, and `Plc;Int;Goal` is Czech *kam* "where
to". This file gives the meaning of the codes as an algebra over feature values,
then lists every feature.

The code that implements it is `features`, `expand`, `subsumes` and `hypernyms`
in `build.py`. The README's "Concepts and codes" section explains where the
concepts come from.

## The algebra

### Slots and values

A code is a sequence of features separated by `;`. Each feature fills one
**slot**:

| slot | values |
|---|---|
| head | `Pers` `Thng` `Ent` `Plc` `Tim` `Mnr` `Rsn` `Knd` `Dur` `Qnt` |
| person | `1` `1i` `1e` `2` `3` |
| number | `Sg` `Du` `Tr` `Pl` `Gpl` |
| domain | `Two` |
| gender | `M` `F` `N` |
| case | `Poss` |
| type | `Asrt` `Elec` `Neg` `Univ` `Int` `Refl` `Recp` `Oth`, and Haspelmath's functions `SK` `SU` `IRR` `Q` `COND` `INEG` `DNEG` `COMP` `FC` |
| formality | `Fml` `Infml` |
| politeness | `Pol` `Hon` `NHon` |
| proximity | `Prox` `Med` `Dist` `Rem` |
| direction | `Loc` `Goal` `Src` |
| register | `Men` `Wom` `Arch` |

A code fills each slot at most once, and the slot of a value is fixed, so
`3;Sg;M` and `Sg;3;M` would mean the same; codes are written in the order of the
table.

### Atomic values

Some values stand for others. These **unmarked** values are unions of the
**atomic** values below them:

    Ent  = Pers ∪ Thng                  (entity: person or thing)
    1    = 1i ∪ 1e                      (first person, inclusive or exclusive)
    Pl   = Du ∪ Tr ∪ Gpl                (non-singular)
    Dist = Med ∪ Rem                    (not proximal)
    Asrt = SK ∪ SU ∪ IRR ∪ Q ∪ COND      (English some-)
    Elec = Q ∪ COND ∪ INEG ∪ DNEG ∪ COMP ∪ FC   (English any-)

Write expand(v) for the atomic values of v: expand(`Pl`) = {`Du`, `Tr`, `Gpl`},
and expand(`Sg`) = {`Sg`}. `Neg` (no-) is atomic, not a set of functions:
*nobody* is used in direct negation, as *anybody* is, but carries the negation
itself, so it is not a kind of *anybody*.

### Operations

1. **Alternatives** (`+` inside a slot) take the union of the values:
   expand(`Prox+Dist`) = {`Prox`, `Med`, `Rem`}. French *ça* "this, that" is
   `Ent;Sg;Prox+Dist`. `1+2;Pl` is first or second person plural.

2. **Conjunction** (`;` between slots) combines features. A code denotes the set
   of **feature assignments** (one atomic value, or none, for every slot) that
   agree with all its features:

       ⟦c⟧ = { a | for every slot s in c, a(s) ∈ expand(c(s)) }

   A slot the code leaves out is **unspecified**: any value, or none, is
   allowed. `3;Sg` covers *he*, *she* and *it*, and genderless third person
   singulars.

3. **The possessive is the exception.** A code without `Poss` is
   non-possessive, not unspecified for case: *my* (`1;Sg;Poss`) adds a relation
   to *I* (`1;Sg`) and is not a kind of it.

4. **Part of speech** separates concepts with the same features: the pronoun
   *this* (`Ent;Sg;Prox`, POS `n`) and the determiner *this* (`Sg;Prox`, POS
   `a`) are different concepts, and neither is a kind of the other. Pronouns are
   `n`, determiners `a` and pro-adverbs `r`.

### Order and hypernymy

Concepts are ordered by containment: c ⊑ d when ⟦c⟧ ⊆ ⟦d⟧, they have the same
part of speech, and both are possessive or neither is. Slot by slot, c ⊑ d when
every slot d fills, c fills too, with a subset of its values:

    c ⊑ d  ⇔  for every slot s in d:  s is in c  and  expand(c(s)) ⊆ expand(d(s))

A concept's hypernyms are the smallest concepts that strictly contain it
(`hypernyms` in `build.py`). There is no table of relations: the hierarchy is
this order, and no two concepts denote the same set.

The basic ways to get a broader code follow from the definitions:

- **drop a feature**: `3;Sg;M` ⊑ `3;Sg`; `Plc;Int;Goal` ⊑ `Plc;Int`;
- **unmark a value**: `1e;Du` ⊑ `1;Du`, `1e;Du` ⊑ `1e;Pl`, `Ent;Sg;Rem` ⊑
  `Ent;Sg;Dist`; but `Pers;Sg;Neg` (*nobody*) is not ⊑ `Pers;Sg;Elec`
  (*anybody*), since `Neg` is not one of `Elec`'s functions;
- **add an alternative**: `Ent;Sg;Prox` ⊑ `Ent;Sg;Prox+Dist`.

Two codes can have common hyponyms. `1e;Du` lies under both `1;Du` (we two) and
`1e;Pl` (exclusive we), because ⟦1;Du⟧ ∩ ⟦1e;Pl⟧ = ⟦1e;Du⟧. So the hierarchy is a
graph, not a tree: of 210 concepts, 23 have two hypernyms.

The hierarchy has no single root. A concept with no broader concept of its part
of speech is a top: 50 are, among them `1;Sg`, `2`, `3`, `Ent;Int`,
`Ent;Prox` and `Tim;Prox` *now*. Concepts that share a head are not joined
unless some concept states only what they share: *now* and *then* are both
`Tim`, but no concept is `Tim` alone, and `Dur+Tim;Int` (*how long, when*) holds
only interrogatives. In the release they are joined through the head's feature
synset, *time* (see below). There is no concept for a single feature such as `1` or `Sg`, so
nothing joins `1;Sg` and `2`.

### Features are synsets too

Each feature value is also a synset in the shared lexicon (`data/features.tsv`),
with its own hierarchy from the unmarked values: *distal* has the hyponyms
*medial* and *remote*, *first person* has *inclusive* and *exclusive*. A
pronoun links to its head by hypernymy (*who* is a kind of *person*), a
determiner or pro-adverb by `attribute`, and every concept links to its other
features by `exemplifies`.

## Features

Each value has a synset with a label, an ILI or an ILI proposal (except two
whose Princeton match is doubtful, `Thng` and `Arch`), and its Universal
Dependencies feature where there is one. The examples are from the
paper's appendix.

### Head

The kind of thing a pro-form stands for. Personal pronouns have a person instead.

| value | meaning | example | code |
|---|---|---|---|
| `Pers` | person | Czech *kdo* "who" | `Pers;Int` |
| `Thng` | thing | Czech *co* "what" | `Thng;Int` |
| `Ent` | entity: `Pers` or `Thng` | English *which* | `Ent;Int` |
| `Plc` | place | Czech *kde* "where" | `Plc;Int` |
| `Tim` | time | Czech *kdy* "when" | `Tim;Int` |
| `Mnr` | manner | Indonesian *begini* "like this" | `Mnr;Prox` |
| `Rsn` | reason | Czech *proč* "why" | `Rsn;Int` |
| `Qnt` | quantity | French *combien* "how much, how many" | `Qnt;Int` |
| `Knd` | kind | Japanese *kōiu* "this kind of" | `Knd;Prox` |
| `Dur` | duration | Mandarin *duōjiǔ* "how long" | `Dur+Tim;Int` |

### Person

| value | meaning | UD | example | code |
|---|---|---|---|---|
| `1` | first person: `1i` or `1e` | `Person=1` | Czech *já* "I" | `1;Sg` |
| `1i` | first person inclusive | `Clusivity=In` | Indonesian *kita* "we (with you)" | `1i;Pl` |
| `1e` | first person exclusive | `Clusivity=Ex` | Indonesian *kami* "we (not you)" | `1e;Pl` |
| `2` | second person | `Person=2` | Czech *ty* "you (sg.)" | `2;Sg` |
| `3` | third person | `Person=3` | Czech *ona* "she" | `3;Sg;F` |

### Number

| value | meaning | UD | example | code |
|---|---|---|---|---|
| `Sg` | singular | `Number=Sing` | English *I* | `1;Sg` |
| `Du` | dual | `Number=Dual` | Tok Pisin *mitupela* "we two (not you)" | `1e;Du` |
| `Tr` | trial | `Number=Tri` | Tok Pisin *mitripela* "we three (not you)" | (no concept yet) |
| `Pl` | plural: any non-singular, `Du`, `Tr` or `Gpl` | `Number=Plur` | English *we* | `1;Pl` |
| `Gpl` | greater plural: more than a dual or trial | `Number=Grpl` | Tok Pisin *mipela* | `1e;Gpl` |

Number counts the referents. `Du` is *we two*: two people referred to.

### Domain

The size of the set a pro-form chooses from, independent of number and type.
*either* refers to one thing, chosen from two; *both* is the universal over a
set of two, so it refers to both of them. Jeretič et al. (2026) treat *dual* as
a core concept that combines with quantifiers in this way; Indo-European had
interrogatives for "which of two" (Latin *uter*, Greek *póteros*, Old English
*hwæþer*).

| value | meaning | example | code |
|---|---|---|---|
| `Two` | chosen from a set of two | English *either* | `Ent;Sg;Two;Elec` |
| | | English *neither* | `Ent;Sg;Two;Neg` |
| | | English *both* | `Ent;Two;Univ` (pronoun), `Two;Univ` (determiner) |
| | | Japanese *dochira* どちら "which (of two)" | `Ent;Two;Int;Fml` |
| | | Japanese *kochira* こちら "this one (of two)" | `Ent;Two;Fml;Prox` |

### Gender

| value | meaning | UD | example | code |
|---|---|---|---|---|
| `M` | masculine | `Gender=Masc` | Czech *on* "he" | `3;Sg;M` |
| `F` | feminine | `Gender=Fem` | Mandarin *tā* 她 "she" | `3;Sg;F` |
| `N` | neuter | `Gender=Neut` | Czech *ono* "it" | `3;Sg;N` |

### Case

Only the possessive is a feature of meaning; subjective and objective case are
inflection, recorded as form variants (*I*, *me*).

| value | meaning | UD | example | code |
|---|---|---|---|---|
| `Poss` | possessive | `Poss=Yes` | English *my*; *mine* | `1;Sg;Poss` (a); `Ent;1;Sg;Poss` (n) |

### Type

| value | meaning | UD | example | code |
|---|---|---|---|---|
| `Asrt` | assertive existential (some-): `SK` to `COND` | `PronType=Ind` | English *something* | `Thng;Sg;Asrt` |
| `Elec` | elective existential (any-): `Q` to `FC` | `PronType=Ind` | English *anyone* | `Pers;Sg;Elec` |
| `Neg` | negative (no-) | `PronType=Neg` | Czech *nikdo* "nobody" | `Pers;Sg;Neg` |
| `Univ` | universal | `PronType=Tot` | Czech *oba* "both" | `Du;Univ` |
| `Int` | interrogative | `PronType=Int` | Indonesian *siapa* "who" | `Pers;Int` |
| `Refl` | reflexive | `Reflex=Yes` | English *herself* | `3;Sg;F;Refl` |
| `Recp` | reciprocal | `PronType=Rcp` | Mandarin *bǐcǐ* 彼此 "each other" | `3;Pl;Recp` |
| `Oth` | other | | Mandarin *duìfāng* 对方 "the other party" | `3;Sg;Oth` |

### Indefinite functions

Haspelmath's (1997) nine functions of indefinite pronouns, in the type slot. An
indefinite series is coded by the functions it covers (`SK+SU` for a series used
only for specific referents). His test sentences:

| value | function | example |
|---|---|---|
| `SK` | specific known | *I met someone yesterday at the workshop.* |
| `SU` | specific unknown | *Unfortunately, I lost my purse somewhere in the shopping centre.* |
| `IRR` | irrealis non-specific | *I hope that I will meet someone nice at the party.* |
| `Q` | question | *Did you meet someone interesting at the workshop?* |
| `COND` | conditional | *If you meet someone interesting at the workshop, you will be lucky.* |
| `INEG` | indirect negation | *I do not expect that any of our friends will be there.* |
| `DNEG` | direct negation | *I did not meet any of our friends there.* |
| `COMP` | comparative | *Our guest was more interesting than any of our old friends.* |
| `FC` | free choice | *Anyone can come to my birthday party.* |

### Formality and politeness

| value | meaning | UD | example | code |
|---|---|---|---|---|
| `Fml` | formal | `Polite=Form` | Indonesian *Anda* "you" | `2;Sg;Fml;Pol` |
| `Infml` | informal | `Polite=Infm` | Indonesian *kamu* "you" | `2;Sg;Infml` |
| `Pol` | polite | `Polite=Elev` | Mandarin *nín* 您 "you" | `2;Sg;Fml;Pol` |
| `Hon` | honorific | `Polite=Elev` | Japanese *watakushi* わたくし "I" | `1;Sg;Fml;Hon+Pol` |
| `NHon` | non-honorific | | Japanese *yatsu* ヤツ "that guy" | `3;Sg;Infml;NHon` |

### Proximity

| value | meaning | UD | example | code |
|---|---|---|---|---|
| `Prox` | proximal | `Deixis=Prox` | English *this* | `Ent;Sg;Prox` |
| `Med` | medial | `Deixis=Med` | Japanese *sore* それ "that (near you)" | `Ent;Sg;Med` |
| `Dist` | distal: not proximal, `Med` or `Rem` | `Deixis=Remt` | English *that* | `Ent;Sg;Dist` |
| `Rem` | remote | `Deixis=Remt` | Japanese *are* あれ "that (over there)" | `Ent;Sg;Rem` |

### Direction

Only where a language distinguishes them; English *where* marks none, so it is
`Plc;Int`, above all three.

| value | meaning | example | code |
|---|---|---|---|
| `Loc` | locative: at a place | Czech *kde* "where (at)" | `Plc;Int;Loc` |
| `Goal` | goal: to a place | Czech *kam* "where to" | `Plc;Int;Goal` |
| `Src` | source: from a place | Czech *odkud* "where from" | `Plc;Int;Src` |

### Register

Restrictions on the speaker, from the NTU wordnet. Not to be confused with the
anchor sex of kinship terms, which restricts the person a relation is traced
from.

| value | meaning | example | code |
|---|---|---|---|
| `Men` | men's speech | Japanese *ore* おれ "I" | `1;Sg;M;Infml;Men` |
| `Wom` | women's speech | Thai *dichǎn* "I" | `1;Sg;F;Fml;Pol;Wom` |
| `Arch` | archaic | Japanese *washi* わし "I" | `1;Sg;M;Infml;Hon;Arch+Men` |

### Operators

| operator | meaning | example |
|---|---|---|
| `;` | conjunction of features in different slots | `3;Sg;F` "she" |
| `+` | alternatives within a slot | `Ent;Sg;Prox+Dist` French *ça* |

In ids, `;` becomes `-` and `+` becomes `_`: `1;Sg;Fml;Hon+Pol` is the synset
`omw-pronoun-1-Sg-Fml-Hon_Pol`. The `dc:identifier` keeps the code as it is
(`pronoun:1;Sg;Fml;Hon+Pol`).

## References

Jeretič, Paloma, Itai Bassi, Aurore Gonzalez, Marie-Christine Meyer, Kazuko
Yatsushiro and Uli Sauerland (2026). Core concepts and indirect alternatives: on
the anti-duality of quantifiers. *Journal of Semantics* 43(1): 17–54.

Haspelmath, Martin (1997). *Indefinite Pronouns*. Oxford University Press.

Seah, Yu Jie and Francis Bond (2014). Annotation of Pronouns in a Multilingual
Corpus of Mandarin Chinese, English and Japanese. In *Proceedings of the 10th
Joint ACL-ISO Workshop on Interoperable Semantic Annotation*.
