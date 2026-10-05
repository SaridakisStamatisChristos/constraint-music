# Independent oracle reference — v1

This document defines the review boundary for the Constraint Music 2.13 research
oracle. The oracle is an independently authored executable reference, not a proof
assistant development and not a claim of universal musical truth.

## Dependency boundary

Every module under `research/oracle/` uses the Python standard library only. The
test guard parses their abstract syntax trees and rejects imports from
`constraint_music`. Tests may import both systems solely to compare decisions.

| Module | Reference domain | SHA-256 |
| --- | --- | --- |
| `contextual_harmony.py` | Diatonic triads/sevenths, applied dominants, borrowed sevenths and tendencies | `f25bff4951e0e634d7d2edc05e0d29a6da2a392b08319f16d25955b67b515259` |
| `secondary_seventh.py` | Secondary leading-tone seventh quality, completeness and inversion | `11b25049467368fb71902636e75d374b42a9826e2eec6774e8c1da8b894ff2d7` |
| `modulation.py` | Dominant destination, persistent context, common pivot and terminal confirmation | `cc547ba54a9bb2e06af061a64a2f007985193bcf4c86f398209509bc9b92a2f4` |
| `rhythm_phrase.py` | CM017–CM026 rhythm, motif, phrase, cadence and period relations | `75eae67d21fb49d3ff66cd9bb057bb464ec8300fd22540480ee1047f4a6e76c9` |
| `delivery.py` | Standard MIDI File parsing, exact event/context projection and byte digest | `3cdc28a711d455e75f4dd1c0dec95756c21b62c57528c2ecd2598ad223601700` |

The hashes identify the exact oracle sources used by the current local evidence.
Any source change requires new hashes and a fresh adjudication run.

## Delivery relation

The delivery oracle reads raw Standard MIDI File bytes without `mido`. It checks:

- format/header/track structural readability and 480 ticks per beat;
- unique required track identity for the selected render profile;
- exact voice, channel, MIDI pitch, onset and duration equality;
- explicit rejection of missing, duplicate, undeclared, unmatched, unterminated,
  or overlapping same-pitch note streams;
- exact tempo, meter, initial-key and declared modulation-key events;
- rhythmic melody onset/tie/rest projection for `melody-plus-satb`;
- SHA-256 of the exact delivered bytes.

`certified-satb` requires Soprano, Alto, Tenor and Bass. `melody-plus-satb`
requires those four tracks plus Melody. `legacy-preview` remains non-certifying.
Velocity, program choice, player behavior, notation spelling and arbitrary MIDI
system messages are not certified semantics.

## Fixture adjudication

Positive fixtures are accepted only when the independently reconstructed relation
and the production checker both accept. Negative fixtures mutate one named
protected value where possible. A disagreement is a defect/adjudication event; the
production checker and oracle do not automatically overrule one another.

The current delivery matrix includes both certifying profiles, tie/rest melody,
twelve representative quality/inversion/register realizations, modulation context,
note identity/timing/channel/track faults, malformed bytes, overlapping note-ons,
output hashing, and publication failures before atomic replacement.

## Known limits

The reference encodes the repository's declared bounded contract. It does not infer
an unlabeled score's harmonic function, prove compiler/checker equivalence, validate
all MIDI software, authenticate an origin, establish aesthetic quality, or turn a
finite fixture corpus into a global correctness theorem.
