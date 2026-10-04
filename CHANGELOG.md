# Changelog

## 2.11.0a1 — verified secondary leading-tone seventh chords

- Added a separate opt-in `secondary_leading_tone_seventh_enabled` feature and `minimum_secondary_leading_tone_seventh_chords`, preserving the v2.10 triad feature and its feasible set unless the new seventh feature is explicitly enabled.
- Certified only fully diminished secondary leading-tone sevenths (`vii°7/x`, `vii°65/x`, `vii°43/x`) in v2.11; half-diminished quality and third inversion remain outside the contract.
- Derived all four secondary-seventh pitch classes from the exact active local key and declared non-tonic target.
- Reused the deterministic support-degree compatibility bridge rather than forging a chromatic diminished root into a diatonic degree.
- Refined target-bearing seventh classification: applied dominants now count only when active-key support/root identity, exact four-note pitch content, and inversion reconstruct as `V7/x`; fully diminished target-bearing sevenths are independently certified by CM055–CM057.
- Prevented secondary leading-tone sevenths from satisfying `minimum_applied_dominants` accidentally while preserving exact applied-dominant counts when both features coexist.
- Required complete four-tone fully diminished realization with all pitch classes exactly once and root/first/second inversion agreement with the bass.
- Required immediate resolution to the declared untargeted, unborrowed triadic target.
- Added independent tendency rules: local leading tone rises by semitone; diminished fifth and chordal diminished seventh descend by one or two semitones.
- Kept secondary leading-tone sevenths disjoint from modal borrowing and excluded them from certified modulation/cadence anchors.
- Made post-modulation secondary-seventh reconstruction use the persistent destination active key, never stale global-key context.
- Extended the hard contract additively from 54 to 57 rules with CM055 context/quality eligibility, CM056 exact realization/inversion, and CM057 target/tendency resolution.
- Versioned the package to `2.11.0a1` and artifact/contract schema to `2.11`.
- Preserved provenance through existing target, harmonic-form, voicing, modal-source, key-context, and specification data; no opaque secondary-function metadata was added.
- Added hostile tests for unsupported quality, forged/missing/duplicated tones, inversion and third-inversion forgery, wrong target/support identity, all tendency directions, modal overlap, applied-dominant count confusion, provenance tampering, cadence contamination, and stale post-modulation context.
- v2.11 validation baseline: 139 tests passing, 81% branch-aware coverage, strict mypy clean across 26 source files on Python 3.11/3.12/3.13.

## 2.10.0a1 — verified secondary leading-tone chords

- Added opt-in secondary leading-tone triads through `secondary_leading_tone_enabled` and `minimum_secondary_leading_tone_chords`.
- Reused the existing nullable local-target identity instead of introducing an opaque secondary-chord label: target-bearing triads under the v2.10 feature are secondary leading-tone chords.
- Derived each diminished triad from the exact active local key and declared non-tonic target rather than granting unrestricted chromatic pitch permission.
- Added a deterministic active-key support-degree policy so chromatic diminished roots are never forged into fake diatonic degrees while CM005, CM006, and CM007 retain their established meanings.
- Required complete diminished-triad SATB realization with local leading tone and diminished fifth exactly once, stable third doubled, and root/first/second inversion agreement with bass.
- Added immediate resolution to the declared untargeted, unborrowed triadic target.
- Added independent local tendency semantics: local leading tone rises by semitone and diminished fifth falls by one or two semitones.
- Kept secondary leading-tone chords disjoint from modal borrowing and excluded them from certified modulation/cadence anchors.
- Made post-modulation secondary harmony derive from the persistent destination active key, never the original global key.
- Prevented target-bearing triads from satisfying `minimum_applied_dominants`.
- Extended the hard contract additively from 51 to 54 rules with `CM052` context/support eligibility, `CM053` exact diminished realization/inversion, and `CM054` target/tendency resolution.
- Versioned the package to `2.10.0a1` and artifact/contract schema to `2.10`.
- Preserved provenance through existing target, harmonic-form, voicing, modal-source, and key-context data; no synthetic secondary-chord metadata was added.
- Added adversarial tests for forged support degree, doubled tendency tones, inversion mismatch, wrong-direction local resolutions, applied-dominant count forgery, target provenance tampering, and stale global-key interpretation after modulation.

## 2.9.0a1 — source-aware borrowed seventh chords

- Extended opt-in modal mixture to a deliberately filtered subset of source-derived borrowed seventh chords when `harmony_vocabulary: triads+sevenths` is also enabled.
- Kept old borrowed-triad semantics unchanged; v2.9 composes existing harmonic-form, modal-source, and active-local-key identities instead of introducing an opaque chord label.
- Added source-derived seventh pitch reconstruction from active local tonic, canonical parallel source, functional degree, and seventh kind.
- Preserved CM005/CM006 outer-voice semantics by admitting only borrowed sevenths that can be completely realized while keeping soprano and bass in the active-key triadic core.
- Preserved only root, first, and second inversions; third inversion remains outside the certified contract.
- Added complete four-tone realization and inversion/bass verification for borrowed sevenths.
- Added downward borrowed chordal-seventh resolution and explicit parallel-major source-leading-tone resolution.
- Kept borrowing and tonicization mutually exclusive at a beat and excluded borrowed sevenths from certified modulation pivot and destination-cadence anchors.
- Made post-modulation borrowed sevenths derive from the persistent destination active key rather than the original global key.
- Extended the hard contract additively from 48 to 51 rules with `CM049` borrowed-seventh context/eligibility, `CM050` source-derived realization/inversion, and `CM051` tendency resolution.
- Versioned the package to `2.9.0a1` and artifact/contract schema to `2.9`.

## 2.8.0a2 — strict destination-cadence repair

- Repaired the initial v2.8 modulation boundary by fixing the state/domain model instead of weakening terminal voice-leading rules.
- Added context-union storage domains for modulation-enabled pieces so explicitly declared destination-key accidentals can appear in outer voices.
- Added exact per-step active-key admission so the union storage domain cannot leak destination-only pitches into the source region or source-only pitches into the destination region.
- Kept objective tension scoring and independent CM002/CM003 verification active-local-key aware.
- Removed the temporary terminal CM032 exemption completely.
- Strengthened destination confirmation so the certified terminal dominant contains the destination leading tone and every SATB voice carrying it resolves upward by semitone.

## 2.8.0a1 — explicit persistent local key and controlled modulation

- Added true persistent local-key state distinct from one-chord tonicization while keeping the artifact global key immutable.
- Added one explicit same-mode modulation to the dominant key with declared destination identity and modulation boundary.
- Added a fixed common-chord pivot: source tonic is reinterpreted as destination IV.
- Interpreted all post-boundary harmony against the persistent destination key and required destination-key V-I confirmation.
- Added one serialized key context per beat, provenance commitment, and a separate `key_context` no-good distinctness dimension.
- Extended the hard contract from 42 to 48 rules (`CM043`–`CM048`).

## 2.7.0a1 — verified modal mixture

- Added opt-in modal mixture through explicit per-beat parallel-source identity.
- Added canonical source modes: parallel natural minor for global-major pieces and parallel major for global-minor pieces.
- Added source-derived borrowed triads without granting unrestricted chromatic pitch permission or storing harmony as opaque Roman-numeral strings.
- Preserved CM005/CM006 outer-voice semantics and certified cadence/context anchors.
- Made borrowing and tonicization mutually exclusive on a beat while allowing both features elsewhere.
- Extended the hard contract from 40 to 42 rules with `CM041` and `CM042`.
- Versioned package/artifact/contract to `2.7.0a1` / `2.7`.

## 2.6.0a1 — verified applied-dominant tonicization

- Added opt-in applied-dominant tonicization on top of the v2.5 `triads+sevenths` vocabulary.
- Added explicit nullable per-beat tonicization-target metadata, orthogonal to global chord degree, chord kind, inversion, and SATB voicing.
- Added target-derived dominant-seventh construction instead of unrestricted chromatic pitch permission.
- Added complete root/first/second-inversion applied-dominant SATB realization and immediate local-tonic resolution.
- Added downward applied chordal-seventh resolution and upward local-leading-tone resolution.
- Extended the independent hard contract from 36 to 40 rules (`CM037`–`CM040`).
- Versioned artifact/contract to `2.6` and added target provenance.

## 2.5.0a1 — expanded harmonic vocabulary

- Added an opt-in `triads+sevenths` vocabulary while preserving `triads` as the default.
- Added structured `ChordKind` identity and explicit per-beat inversion metadata.
- Added complete diatonic seventh-chord realization with root, first, and second inversion support.
- Added chordal-seventh downward-step resolution and dominant-seventh-to-tonic behavior.
- Extended the independent hard contract from 32 to 36 rules (`CM033`–`CM036`).
- Added `harmonic_form` distinctness and artifact schema 2.5.

## 2.4.0a1 — solver-native SATB harmony

- Added explicit beat-level soprano, alto, tenor, and bass SATB realization inside CP-SAT.
- Added canonical inner-voice ranges, strict voice ordering, upper-voice spacing, complete-triad/root-doubling policy, inner-voice parallel-perfect avoidance, and leading-tone resolution.
- Extended the hard contract from 26 to 32 rules (`CM027`–`CM032`).
- Added `SatbGenerationResult`, SATB provenance, and a separate `voicing` dimension.

## 2.3.0a1 — distinct enumeration and Pareto search

- Replaced seed-only `generate_many()` variation with CP-SAT no-good cuts guaranteeing distinctness over selected musical dimensions.
- Added named objective-vector metadata with independent recomputation.
- Added deterministic scalarization profiles and bounded Pareto-front approximation.
- Versioned JSON artifacts to schema 2.3; the hard contract remained `CM001–CM026`.

## 2.2.0a1 — verified phrase grammar

- Added explicit phrase spans, IDs, roles, exact phrase relations, phrase-local cadences, and a minimal antecedent/consequent period grammar.
- Extended the hard contract from 21 to 26 rules (`CM022`–`CM026`) with independent phrase verification.
- Versioned JSON provenance to schema/contract 2.2.

## 2.1.0a1 — rhythm and motif grammar

- Promoted melody rhythm to an explicit CP-SAT dimension with onset, tie, and rest states.
- Added verified bar density, downbeat articulation, rest/tie limits, and exact repeat/transpose motif grammar.
- Extended the independent contract from 16 to 21 hard rules (`CM017`–`CM021`).
- Added v2.1 JSON provenance committing rhythm.

## 2.0.0a1 — revival baseline

- Rebuilt the recovered v1.1 constraint-programming engine as a clean v2 foundation.
- Added a versioned 16-rule hard-constraint contract with stable rule IDs.
- Closed verifier gaps for melodic tritones, bass tritones, and large-leap recovery.
- Added fail-closed solver/verifier enforcement and independently re-verifiable JSON artifacts.
- Added `constraint-music verify` for offline validation without rerunning CP-SAT.

## 1.1.0 — recovered historical implementation

- CP-SAT melody/bass/harmony generation.
- Configurable functional progression graph.
- Subdivision-level parallel-perfect prevention.
- MIDI and JSON output.
