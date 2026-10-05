# Changelog

## 2.13.0a1 — semantic-assurance repair and research infrastructure

- Reject malformed/current artifacts before reconstruction; current SATB artifacts can no longer downgrade to a base result.
- Added strict numeric/null/array validation and safe blocked-rule reporting.
- Added request-bound `certify` with fresh validation, rule-claim reconciliation, and coordinated-forgery regressions.
- Replaced reconstructed harmony delivery with exact four-track SATB export and independent MIDI parse-back.
- Added `PASS`/`FAIL`/`NOT_APPLICABLE`/`BLOCKED` outcomes for all 57 stable rule IDs.
- Made the checker importable without OR-Tools and moved CP-SAT to the optional `generation` extra.
- Replaced message-text diagnostic suppression with typed, exact semantic dispatch for borrowed and secondary leading-tone harmony; invalid labels and third inversions now fail closed while tendency resolution remains independently enforced.
- Added independent diatonic, applied-dominant, secondary-seventh, borrowed-seventh, secondary-triad, persistent-modulation, rhythm, motif, and phrase-form oracles. Coverage includes exhaustive key/mode/boundary policy comparisons, every four-step rhythm-state sequence, every motif/phrase relation and cadence label, phrase-boundary/role/period matrices, and hostile realization, resolution, pivot, context, articulation, density, relation, and terminal-anchor mutations; retained the bounded 27,648-case enumerator, deterministic corruption corpus, and reproducibility documentation.

## 2.12.0a1 — complete secondary leading-tone seventh certification

- Completed the secondary leading-tone seventh family within the declared common-practice tonicization domain instead of leaving half-diminished quality or third inversion as deferred convenience cases.
- Certified both fully diminished and half-diminished `vii7/x` families for major local targets; certified the fully diminished family for minor local targets.
- Added all four inversion figures (`7`, `65`, `43`, `42`) with exact bass/inversion agreement; a third-inversion chord must actually place its chordal seventh in the bass.
- Added a scoped outer-voice compiler path so genuine chromatic `42` realizations are possible without granting unrestricted chromatic melody/bass permission to ordinary harmony.
- Added a second independent inversion-scope guard: inversion `3` is legal only on a beat that independently reconstructs as a secondary leading-tone seventh.
- Kept quality as a solver witness/reconstructed musical property rather than a trusted opaque serialized identity field.
- Added exact target- and quality-dependent tendency semantics in every SATB voice: local leading tone `+1`; diminished fifth `-1` for major targets / `-2` for minor targets; fully diminished chordal seventh `-1`; half-diminished chordal seventh `-2`.
- Preserved immediate resolution to the declared untargeted, unborrowed triadic target, modal-source disjointness, protected cadence/modulation anchors, and persistent destination-key interpretation after modulation.
- Preserved exact applied-dominant classification and minimum counting when applied dominants and secondary leading-tone sevenths coexist.
- Strengthened CM002/CM003/CM005/CM006 only on independently reconstructed secondary-seventh beats; ordinary feature-disabled paths retain their previous domain/verification behavior.
- Removed v2.11's two-tone diatonic-overlap gate from the secondary-seventh support bridge: progression compatibility remains structural, while exact active-key target/quality/pitch reconstruction certifies musical identity. The v2.10 triad path keeps its historical overlap policy.
- Added exhaustive all-key coverage across 12 chromatic tonics × major/minor modes, every progression-reachable eligible target, every certified quality, and all four inversions, including a regression for the formerly excluded `vii°7/iii` in C major.
- Kept the stable hard-rule range `CM001–CM057` while strengthening CM055–CM057 for complete quality/inversion certification.
- Versioned package to `2.12.0a1` and artifact/constraint-contract schema to `2.12`.
- Expanded adversarial coverage across both qualities × all four inversions, inversion-scope leakage, missing/duplicated tones, exact tendency errors, applied-count confusion, modal overlap, cadence contamination, provenance tampering, destination-key reconstruction, and stale-key forgery.
- Validation baseline: 197 tests passing, 80% branch-aware coverage, strict mypy clean across 27 source files, and successful Ruff/mypy/pytest/build gates on Python 3.11, 3.12, and 3.13.

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
- Validation baseline: 139 tests passing with branch coverage enabled, strict mypy clean across 26 source files, and successful builds on Python 3.11, 3.12, and 3.13.

## 2.10.0a1 — verified secondary leading-tone chords

- Added opt-in secondary leading-tone triads through `secondary_leading_tone_enabled` and `minimum_secondary_leading_tone_chords`.
- Reused the existing nullable local-target identity instead of introducing an opaque secondary-chord label: target-bearing sevenths remain applied dominants, while target-bearing triads under the v2.10 feature are secondary leading-tone chords.
- Derived each diminished triad from the exact active local key and declared non-tonic target rather than granting unrestricted chromatic pitch permission.
- Added a deterministic active-key support-degree policy so chromatic diminished roots are never forged into fake diatonic degrees while CM005, CM006, and CM007 retain their established meanings.
- Required complete diminished-triad SATB realization with local leading tone and diminished fifth exactly once, stable third doubled, and root/first/second inversion agreement with bass.
- Added immediate resolution to the declared untargeted, unborrowed triadic target.
- Added independent local tendency semantics: local leading tone rises by semitone and diminished fifth falls by one or two semitones.
- Kept secondary leading-tone chords disjoint from modal borrowing and excluded them from certified modulation/cadence anchors.
- Made post-modulation secondary harmony derive from the persistent destination active key, never the original global key.
- Prevented target-bearing triads from satisfying `minimum_applied_dominants`; applied-dominant counts remain target-bearing seventh counts.
- Extended the hard contract additively from 51 to 54 rules with `CM052` context/support eligibility, `CM053` exact diminished realization/inversion, and `CM054` target/tendency resolution.
- Versioned the package to `2.10.0a1` and artifact/contract schema to `2.10`.
- Preserved provenance through existing target, harmonic-form, voicing, modal-source, and key-context data; no synthetic secondary-chord metadata was added.
- Added adversarial tests for forged support degree, doubled tendency tones, inversion mismatch, wrong-direction local resolutions, applied-dominant count forgery, target provenance tampering, and stale global-key interpretation after modulation.
- Kept secondary leading-tone sevenths, third-inversion sevenths, arbitrary modulation chains, enharmonic reinterpretation, augmented-sixth/Neapolitan reinterpretation, and probabilistic key inference outside v2.10.

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
- Preserved provenance commitment through the existing orthogonal `modal_sources`, `chord_kinds`, `chord_inversions`, and `key_contexts` fields; no synthetic replacement metadata was added.
- Added adversarial tests for forged/missing seventh tones, inversion mismatch, wrong-direction resolution, tonicization overlap, ordinary-vs-borrowed identity forgery, provenance tampering, source-leading-tone behavior, and post-modulation stale-context interpretation.
- Kept secondary leading-tone chords, third-inversion sevenths, arbitrary modulation chains, enharmonic reinterpretation, augmented-sixth/Neapolitan reinterpretation, and probabilistic key inference outside v2.9.

## 2.8.0a2 — strict destination-cadence repair

- Repaired the initial v2.8 modulation boundary by fixing the state/domain model instead of weakening terminal voice-leading rules.
- Added context-union storage domains for modulation-enabled pieces so explicitly declared destination-key accidentals can appear in outer voices.
- Added exact per-step active-key admission so the union storage domain cannot leak destination-only pitches into the source region or source-only pitches into the destination region.
- Kept objective tension scoring and independent CM002/CM003 verification active-local-key aware.
- Removed the temporary terminal CM032 exemption completely.
- Strengthened destination confirmation so the certified terminal dominant contains the destination leading tone and every SATB voice carrying it resolves upward by semitone.
- Preserved strict solver/verifier symmetry through the terminal transition and added hostile wrong-region and terminal-leading-tone tamper tests.

## 2.8.0a1 — explicit persistent local key and controlled modulation

- Added true persistent local-key state distinct from one-chord tonicization while keeping the artifact global key immutable.
- Added one explicit same-mode modulation to the dominant key with declared destination identity and modulation boundary.
- Added a fixed common-chord pivot: source tonic is reinterpreted as destination IV.
- Interpreted all post-boundary harmony against the persistent destination key and required destination-key V-I confirmation.
- Added one serialized key context per beat, provenance commitment, and a separate `key_context` no-good distinctness dimension.
- Made tonicization, modal mixture, and objective tension semantics active-local-key aware after modulation.
- Extended the hard contract from 42 to 48 rules (`CM043`–`CM048`) for key-context shape, boundary/destination, pivot, post-modulation interpretation, destination confirmation, and serialized context consistency.
- Preserved non-modulating pieces on the established global-key path and retained older payload loading behavior when modulation is disabled.

## 2.7.0a1 — verified modal mixture

- Added opt-in modal mixture through explicit per-beat parallel-source identity.
- Added canonical source modes: parallel natural minor for global-major pieces and parallel major for global-minor pieces.
- Added source-derived borrowed triads without granting unrestricted chromatic pitch permission or storing harmony as opaque Roman-numeral strings.
- Preserved CM005/CM006 outer-voice semantics by carrying borrowed chromatic tones in inner voices and structurally filtering unsupported borrowed degrees.
- Preserved the global closure contract by prohibiting borrowing on the final beat and, under authentic cadence, on the penultimate beat.
- Made borrowing and tonicization mutually exclusive on a beat while allowing both features to coexist elsewhere in the same composition.
- Extended the independent hard contract from 40 to 42 rules with `CM041` modal-mixture context and `CM042` borrowed-chord realization.
- Added independent reconstruction of source-mode pitch classes, complete borrowed-triad realization, and inversion/bass agreement from serialized values.
- Added `modal_source` as a separate no-good distinctness dimension without redefining `harmony`, `harmonic_form`, `tonicization`, or `voicing`.
- Versioned package to `2.7.0a1` and artifact/contract schema to 2.7; semantic provenance now commits modal-source metadata.
- Preserved loading and musical verification of older payloads without inventing modal-source metadata when modal mixture is disabled.
- Added deterministic positive generation plus adversarial tests for forged source identity, degree/inversion tampering, provenance tampering, legacy loading, and modal-source distinctness.

## 2.6.0a1 — verified applied-dominant tonicization

- Added opt-in applied-dominant tonicization on top of the v2.5 `triads+sevenths` vocabulary.
- Added explicit nullable per-beat tonicization-target metadata, kept orthogonal to global chord degree, chord kind, inversion, and SATB voicing.
- Added target-derived dominant-seventh construction instead of unrestricted chromatic pitch permission or opaque slash-chord labels.
- Added structural filtering of tonicization targets that cannot preserve the established CM005/CM006 outer-voice semantics.
- Added complete applied-dominant SATB realization with root, first, and second inversions under the preserved outer-voice contract.
- Added solver-native immediate resolution to the declared local tonic, downward applied chordal-seventh resolution, and upward local-leading-tone resolution in every SATB voice.
- Extended the independent hard contract from 36 to 40 rules (`CM001`–`CM040`) with separate tonicization-context, realization, target-resolution, and tendency-resolution IDs.
- Added independent reconstruction of applied-dominant pitch content and resolution from ordinary serialized musical values.
- Added `tonicization` as a separate no-good distinctness dimension without redefining `harmony`, `harmonic_form`, or `voicing`.
- Versioned JSON artifacts and the hard-rule contract to 2.6; semantic provenance now commits tonicization target metadata when present.
- Preserved loading and musical verification of older SATB/harmonic-form payloads without inventing tonicization metadata when the feature is disabled.
- Added positive forced `I -> V7/V -> V -> I -> V -> I` generation coverage and adversarial tests for forged targets, wrong target resolution, unresolved local tendency tones, and provenance tampering.

## 2.5.0a1 — expanded harmonic vocabulary

- Added an opt-in `triads+sevenths` harmonic vocabulary while preserving `triads` as the default for backward-compatible specifications.
- Added structured `ChordKind` identity and explicit per-beat inversion metadata.
- Added complete diatonic seventh-chord realization inside the SATB CP-SAT model.
- Added root, first, and second inversion support while preserving the established CM005/CM006 triadic-core semantics for outer voices.
- Added solver-native downward chordal-seventh resolution and explicit dominant-seventh-to-tonic behavior with leading-tone resolution in every SATB voice.
- Extended the independent hard contract from 32 to 36 rules (`CM001`–`CM036`).
- Added the `harmonic_form` distinctness dimension for chord kind/inversion while preserving `harmony` as chord-degree-sequence distinctness.
- Versioned JSON artifacts to schema 2.5; semantic provenance now commits harmonic kind/inversion metadata when present.
- Preserved loading and musical verification of older SATB artifacts without inventing missing harmonic-form metadata.
- Added positive solver tests plus adversarial tests for inversion mismatch, unresolved sevenths, wrong dominant targets, and harmonic-form provenance tampering.

## 2.4.0a1 — solver-native SATB harmony

- Added explicit beat-level soprano, alto, tenor, and bass SATB realization inside CP-SAT.
- Anchored soprano to the strong-grid melody while solving alto and tenor independently.
- Added canonical inner-voice ranges, strict voice ordering, and octave upper-voice spacing.
- Added complete-triad enforcement with an explicit root-doubling policy.
- Added solver-native parallel-perfect avoidance for every voice pair involving alto or tenor.
- Added solver-native leading-tone resolution for alto and tenor.
- Extended the independently verified hard contract from 26 to 32 rules (`CM001`–`CM032`).
- Added `SatbGenerationResult` serialization and artifact schema 2.4; semantic digests now commit to SATB voices.
- Preserved v2.3 `harmony` distinctness as chord-sequence distinctness and added a separate `voicing` dimension for alto/tenor realizations.
- Added positive SATB generation tests and adversarial verification tests for crossing and chord-completeness tampering.
- Cached immutable SATB chord and parallel-motion tables to avoid rebuilding the same transition relations across repeated solves.

## 2.3.0a1 — distinct enumeration and Pareto search

- Replaced seed-only `generate_many()` variation with CP-SAT no-good cuts that guarantee distinctness over selected musical dimensions.
- Added explicit distinctness dimensions for melody, rhythm, bass, and harmony.
- Split the scalar objective into five named minimized components: tension deviation, melody motion, bass motion, harmonic repetition, and contour mismatch.
- Added independent objective-vector recomputation from serialized musical values; solver-side and independent vectors must agree.
- Added deterministic weighted scalarization profiles and a bounded Pareto-front approximation API.
- Added independent Pareto dominance filtering and deterministic single-worker enumeration tests.
- Versioned JSON artifacts to schema 2.3 with integrity-protected objective-vector metadata.
- Added CLI controls for distinct dimensions, Pareto mode, and Pareto candidate-pool size.
- Kept the hard musical certification contract unchanged at `CM001`–`CM026`; v2.3 changes search/ranking semantics, not feasibility semantics.

## 2.2.0a1 — verified phrase grammar

- Added explicit phrase spans with unique IDs and non-overlap/in-bounds validation.
- Added phrase roles: `statement`, `antecedent`, `consequent`, `transition`, and `cadential`.
- Added exact phrase relations: `independent`, `repeat`, `transpose`, `answer`, and `sequence`.
- Added precise phrase-local cadence labels: `tonic_close`, `dominant_open`, `dominant_to_tonic`, and `leading_tone_to_tonic`.
- Added a minimal answer-linked antecedent/consequent period grammar with open-to-strong closure semantics.
- Extended the hard contract from 21 to 26 rules (`CM001`–`CM026`) with independent phrase verification.
- Versioned JSON provenance to schema/contract 2.2; phrase declarations are committed by the semantic digest through the serialized specification.
- Added Phase 0 stabilization regressions for old all-onset configs, malformed rhythm deserialization, deterministic single-worker generation, and tamper detection.
- Added positive and adversarial phrase tests plus an eight-bar period example.
- Kept the historical `require_authentic_cadence` field backward compatible while documenting it as the legacy whole-piece closure rule.

## 2.1.0a1 — rhythm and motif grammar

- Promoted melody rhythm to an explicit CP-SAT dimension with `onset`, `tie`, and `rest` states.
- Added verified per-bar onset/rest/tie density, downbeat articulation, maximum rest runs, and maximum tie runs.
- Made ties preserve pitch and render as sustained MIDI notes; rests now create real silence in the melody track.
- Added motif grammar with exact repetition and exact semitone transposition between configured phrase locations.
- Extended the independent contract from 16 to 21 hard rules (`CM001`–`CM021`).
- Added v2.1 JSON provenance; semantic hashes now commit to rhythm as well as pitch/harmony/tension.
- Added rhythm/motif adversarial tests, MIDI duration tests, documentation, and an expressive example spec.
- Preserved v2.0 generation behavior by keeping rhythm generation opt-in.

## 2.0.0a1 — revival baseline

- Rebuilt the recovered v1.1 constraint-programming engine as a clean v2 foundation.
- Added a versioned 16-rule hard-constraint contract with stable rule IDs.
- Closed the v1.1 verifier gaps for melodic tritones, bass tritones, and large-leap recovery.
- Added fail-closed solver/verifier contract enforcement.
- Added independently re-verifiable JSON artifacts with SHA-256 composition and contract digests.
- Added `constraint-music verify` for offline validation without rerunning CP-SAT.
- Preserved deterministic seeded generation, MIDI export, custom progression graphs, tension curves, and harmonic-minor support.
- Added adversarial verifier tests and CI quality gates.

## 1.1.0 — recovered historical implementation

- CP-SAT melody/bass/harmony generation.
- Configurable functional progression graph.
- Subdivision-level parallel-perfect prevention.
- MIDI and JSON output.
