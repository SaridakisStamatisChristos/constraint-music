# Executable Contract 2.13

Each rule is emitted exactly once as `PASS`, `FAIL`, `NOT_APPLICABLE`, or `BLOCKED`. `PASS` means the production checker executed the applicable predicate; every outcome carries an explicit `visited` bit. An applicable rule that was not visited is fail-closed as `BLOCKED` with `<RULE>.NOT_VISITED`. `NOT_APPLICABLE` records the condition below; other `BLOCKED` outcomes identify unavailable prerequisites. `checked_rules` is retained only as a compatibility index; certification claims use `rule_outcomes` and `evaluated_rule_ids`.

Failures additionally carry structured diagnostics with a stable code, rule ID,
feature family, location, optional voice, and presentation message. Compiler coverage
is registered independently in `compiler_registry.py`: every invoked phase records its
implementation symbol, applicable rule IDs, and exact half-open CP-SAT constraint span.
The registration catalogue covers `CM001`–`CM057`, but is evidence of implemented
coverage only; it is not a compiler/checker-equivalence theorem.

| Rule | Predicate | Applicability |
|---|---|---|
| CM001 — shape | Melody, rhythm, bass, and harmony lengths match the specification. | `always` |
| CM002 — melody_domain | Every melody pitch is in the active key and inside the configured range, except an exactly reconstructed strong-beat secondary leading-tone seventh may carry one of its certified chromatic chord tones. | `always` |
| CM003 — bass_domain | Every bass pitch is in the active key and inside the configured range, except an exactly reconstructed secondary leading-tone seventh may carry its certified chromatic inversion tone. | `always` |
| CM004 — harmony_domain | Every chord degree is a valid diatonic degree in 0..6. | `always` |
| CM005 — strong_beat_chord_tone | Every strong-beat melody pitch belongs to the active support triad or, for an exact certified secondary leading-tone seventh, to the realized target-derived seventh. | `always` |
| CM006 — bass_chord_member | Every bass pitch belongs to the active support triad or, for an exact certified secondary leading-tone seventh, to the realized target-derived seventh. | `always` |
| CM007 — progression_graph | Every adjacent chord transition is allowed by the configured graph. | `always` |
| CM008 — melody_leap | Adjacent melody motion stays within the configured leap bound. | `always` |
| CM009 — melody_tritone | Adjacent melody motion never forms a tritone. | `always` |
| CM010 — leading_tone_resolution | When enabled, a melodic leading tone resolves upward by semitone. | `resolve_leading_tone` |
| CM011 — melody_repetition | Repeated-note runs do not exceed the configured limit. | `always` |
| CM012 — large_leap_recovery | A melodic leap larger than a perfect fifth is followed by contrary stepwise motion. | `always` |
| CM013 — bass_leap | Adjacent bass motion stays within the configured leap bound. | `always` |
| CM014 — bass_tritone | Adjacent bass motion never forms a tritone. | `always` |
| CM015 — parallel_perfects | When enabled, outer voices avoid parallel perfect fifths and octaves. | `avoid_parallel_perfects` |
| CM016 — legacy_whole_piece_closure | When enabled, the piece opens on tonic and closes dominant-function to tonic with tonic outer voices. | `require_authentic_cadence` |
| CM017 — rhythm_domain | Every melody grid step is explicitly classified as onset, tie, or rest. | `always` |
| CM018 — rhythm_grammar | Ties extend a sounding note, preserve pitch, and tie/rest runs stay within bounds. | `rhythm_enabled` |
| CM019 — rhythm_bar_density | When rhythm generation is enabled, each bar satisfies onset/rest/tie density and downbeat rules. | `rhythm_enabled` |
| CM020 — motif_relation | When configured, a target motif repeats or transposes the source motif exactly, including rhythm. | `motif_relation != none` |
| CM021 — cadential_articulation | The legacy whole-piece closure ends on a newly articulated tonic melody onset. | `require_authentic_cadence` |
| CM022 — phrase_boundary | Declared phrase spans are in bounds, uniquely identified, and pairwise non-overlapping. | `phrases declared` |
| CM023 — phrase_role | Antecedent, consequent, and cadential roles impose explicit opening/closing harmonic semantics. | `phrases declared` |
| CM024 — phrase_relation | Repeat, transpose, answer, and sequence relations reconstruct target melodic/rhythmic material exactly from their declared source. | `phrases declared` |
| CM025 — phrase_cadence | Phrase cadence labels impose their exact tonic-close, dominant-open, dominant-to-tonic, or leading-tone-to-tonic semantics. | `phrases declared` |
| CM026 — antecedent_consequent_structure | An answer-linked antecedent/consequent pair opens stably, leaves the antecedent open, recalls source material, and closes the consequent more strongly. | `phrases declared` |
| CM027 — satb_shape | Solver-native SATB output contains one soprano, alto, and tenor note per beat and anchors soprano to the strong-step melody. | `always` |
| CM028 — satb_ranges_order | SATB voices remain inside their ranges and maintain strict bass-tenor-alto-soprano ordering. | `always` |
| CM029 — satb_spacing | Adjacent upper SATB voices stay within octave spacing. | `always` |
| CM030 — satb_chord_completeness | Every SATB triad contains the complete active-key triad and doubles its root. | `always` |
| CM031 — satb_inner_parallel_perfects | When enabled, voice pairs involving alto or tenor avoid parallel perfect fifths and octaves. | `avoid_parallel_perfects` |
| CM032 — satb_tendency_resolution | When enabled, alto and tenor active-key leading tones resolve upward by semitone. | `resolve_leading_tone` |
| CM033 — harmonic_form_shape | When expanded harmonic-form metadata is present, chord kind and inversion arrays cover every beat and comply with the declared vocabulary/minimum seventh count. | `always` |
| CM034 — expanded_chord_realization | Seventh forms contain all four active-key chord tones exactly once, while every serialized inversion agrees with the realized bass pitch class. | `expanded_harmony_enabled` |
| CM035 — chordal_seventh_resolution | Every diatonic chordal seventh has a following sonority and resolves downward by step. | `expanded_harmony_enabled` |
| CM036 — dominant_seventh_resolution | Every active-key dominant seventh resolves to tonic and each voice carrying its leading tone resolves upward by semitone. | `expanded_harmony_enabled` |
| CM037 — tonicization_context | When applied-dominant tonicization is enabled, only target-bearing sevenths whose active-key pitch content and support identity reconstruct exactly as applied V7/x count toward the declared minimum. Target-bearing triads remain governed by CM052-CM054; v2.12 secondary leading-tone sevenths by CM055-CM057. | `tonicization_enabled` |
| CM038 — applied_dominant_realization | Every seventh certified as an applied dominant has active-key target-derived dominant-seventh pitch classes exactly once, the correct root degree, and an inversion matching the bass. | `tonicization_enabled` |
| CM039 — applied_dominant_target_resolution | Every applied dominant resolves immediately to its declared untargeted diatonic local tonic. | `tonicization_enabled` |
| CM040 — applied_dominant_tendency_resolution | Each applied-dominant chordal seventh resolves downward by step and each voice carrying the local leading tone resolves upward by semitone. | `tonicization_enabled` |
| CM041 — modal_mixture_context | When modal mixture is enabled, every beat carries explicit nullable source-mode metadata; borrowed beats use the active-key canonical parallel source, do not coincide with local-target metadata, stay outside certified cadential/context anchors, and satisfy the declared minimum borrowed-chord count. Borrowed triads are certified by CM042; eligible borrowed sevenths by CM049-CM051. | `modal_mixture_enabled` |
| CM042 — borrowed_chord_realization | Every borrowed triad contains the complete triad derived from its explicit parallel source mode, active key, and degree, with inversion agreeing with realized bass. | `modal_mixture_enabled` |
| CM043 — key_context_shape | Enabled modulation serializes exactly one explicit local-key identity per beat. | `modulation_enabled` |
| CM044 — modulation_boundary_destination | The single modulation boundary targets the declared same-mode dominant key. | `modulation_enabled` |
| CM045 — modulation_pivot | The pre-boundary source-tonic triad is an unaltered common chord reinterpretable as destination IV. | `modulation_enabled` |
| CM046 — post_modulation_interpretation | All post-boundary harmony is independently reconstructed against the persistent destination-key context. | `modulation_enabled` |
| CM047 — destination_confirmation | The destination region closes with an unborrowed, untargeted destination V-I and destination-tonic outer voices. | `modulation_enabled` |
| CM048 — serialized_key_context_consistency | Serialized key contexts equal the exact source-before/destination-after boundary sequence declared by the specification. | `modulation_enabled` |
| CM049 — borrowed_seventh_context_eligibility | A source-bearing seventh requires expanded harmony and modal mixture, uses the active-key canonical parallel source and an explicitly supported degree, carries no local target, and stays outside certified modulation/cadence anchors. | `modal_mixture_enabled and expanded_harmony_enabled` |
| CM050 — borrowed_seventh_realization | Every eligible borrowed seventh contains all four pitch classes derived from its explicit source, active key, and degree exactly once, and its root/first/second inversion agrees with the realized bass. | `modal_mixture_enabled and expanded_harmony_enabled` |
| CM051 — borrowed_seventh_tendency_resolution | Every borrowed chordal seventh resolves downward by step; any admitted parallel-source leading tone carried by a SATB voice resolves upward by semitone. | `modal_mixture_enabled and expanded_harmony_enabled` |
| CM052 — secondary_leading_tone_context | Every target-bearing triad used as a secondary leading-tone chord declares a supported non-tonic active-key target, uses its deterministic CM005/CM006 support degree, does not overlap modal borrowing, and stays outside certified anchors. | `secondary_leading_tone_enabled` |
| CM053 — secondary_leading_tone_realization | Every secondary leading-tone chord is the complete target-derived diminished triad, with local leading tone and diminished fifth undoubled, stable third doubled, and serialized inversion matching the realized bass. | `secondary_leading_tone_enabled` |
| CM054 — secondary_leading_tone_resolution | Every secondary leading-tone chord resolves immediately to its declared unaltered triadic target; each local leading tone rises by semitone and each diminished fifth resolves downward by step. | `secondary_leading_tone_enabled` |
| CM055 — secondary_leading_tone_seventh_context | Every v2.12 target-bearing secondary leading-tone seventh declares a supported non-tonic target in the exact active local key, uses its deterministic progression support degree, does not overlap modal borrowing or applied-dominant identity, and stays outside certified cadence/modulation anchors. Fully diminished quality is eligible for major and minor targets; half-diminished quality only for major targets. | `secondary_leading_tone_seventh_enabled` |
| CM056 — secondary_leading_tone_seventh_realization | Every certified secondary leading-tone seventh contains exactly once the four target-derived pitch classes of its independently reconstructed fully diminished or eligible half-diminished quality. Root, first, second, and third inversions are admitted and the serialized inversion must match the realized bass. | `secondary_leading_tone_seventh_enabled` |
| CM057 — secondary_leading_tone_seventh_resolution | Every certified secondary leading-tone seventh resolves immediately to its declared untargeted, unborrowed triadic target. The local leading tone rises by semitone; the diminished fifth descends by the exact target-quality step; the chordal seventh descends by the exact quality-dependent step, including when carried by the bass in third inversion. | `secondary_leading_tone_seventh_enabled` |

## Trust and scope

The checker validates a declared tonal/SATB contract against an independently supplied request. It does not infer a unique tonal analysis from unlabeled MIDI, prove musical quality, authenticate an author, prove solver optimality, or establish whole-language compiler/checker equivalence. MIDI delivery certification covers ordered note events and declared key-context events for the selected render profile.
