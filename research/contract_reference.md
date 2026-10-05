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
| `secondary_seventh.py` | Secondary leading-tone seventh quality, completeness, inversion, bounded context/register and voice resolution | `7e1b22849200a45aa21aa415fe1b1e64d8cc1ce623957c47bbed84014ded94bf` |
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

## Bounded secondary-seventh conformance

`research.enumerate_fragments` keeps the historical pitch-class relation partition
separate from two new finite local partitions and a systematic whole-verifier matrix.
The absolute-register partition enumerates every exact four-role octave placement
inside S 60..81, A 55..74, T 48..67 and B 36..55, with strict ordering and
12-semitone upper-voice spacing. The voice-resolution partition enumerates every
simultaneous -2..+2 semitone motion for all target pitch classes, permitted target
quality policies, inversions and role assignments. Octave normalization is valid
only for that local motion predicate; register and target-triad membership remain
separate obligations.

The context/anchor partition enumerates every beat of 2..8-beat open and
authentic-cadence forms, every valid single-modulation boundary in that range, and the
complete supported-target/modal-overlap truth table. It compares an independent
placement oracle with the exact CM055 production predicate used by full verification.

The complete-verifier matrix embeds all eight permitted quality/inversion forms of
C-major vii7/V -> V, plus one register fault and one resolution fault per form.
Its scope is systematic rather than exhaustive. The checked-in
`research/results/bounded_conformance.json` records exact cardinalities, category
counts, pruning, first disagreements, and hashes for the oracle and production predicates.

## Pinned generator finalization faults

The aggregate evidence pins OR-Tools 9.15.6755, one worker, seed 6131, the canonical
request digest, and hashes for the dependency declaration, fault harness, and production
solver boundary. It runs one valid secondary-seventh control plus four corruptions of
ordinary generated values (melody domain, target metadata, inversion/bass identity, and
tendency resolution) and one corruption of the compiled objective vector. The exact
production finalizer must accept only the control and raise `InternalVerificationError`
for every injected fault.

The direct-deletion partition removes exactly the named
`CM057.root.beat-0.voice-2` CP-SAT constraint, verifies that it belongs to the measured
`secondary_seventh_satb` registration span, and forces a feasible octave-displaced
local-leading-tone resolution. The independent oracle, complete verifier, and
production finalizer all reject the witness. A separate ten-case partition accepts
five generated controls and rejects five targeted faults while secondary sevenths are
coenabled with tonicization, modal mixture, rhythm, authentic cadence, and modulation.

These matrices demonstrate fail-closed behavior at selected generator/compiler and
feature-interaction boundaries. They do not delete every individual CP-SAT constraint,
prove that CP-SAT is correct, or establish global compiler/checker equivalence.

## Known limits

The reference encodes the repository's declared bounded contract. It does not infer
an unlabeled score's harmonic function, prove compiler/checker equivalence, validate
all MIDI software, authenticate an origin, establish aesthetic quality, or turn a
finite fixture corpus into a global correctness theorem.
