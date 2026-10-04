# Architecture

Constraint Music is deliberately split into generation, search, serialization, and independent verification paths.

```text
YAML GenerationSpec
       |
       v
 global key + explicit active-key contexts
       |
       +--> chord degree / support degree
       +--> harmonic form (kind + inversion)
       +--> nullable local target identity
       +--> nullable modal source
       +--> nullable modulation destination/boundary
       |
       v
CP-SAT compiler -----------------------------------------+
       |   \-> SATB + harmonic/context realization       |
       v                                                  |
 feasible + optimized assignment                          |
       |                                                  |
       +--> no-good enumeration / scalarization           |
       |                                                  |
       v                                                  |
ordinary Python musical values                            |
       |                                                  |
       +--> independent objective recomputation           |
       |                                                  |
       v                                                  |
independent verifier <---------------- hard contract -----+
       |
       +--> MIDI
       +--> schema-versioned, tamper-evident JSON
```

## Trust boundary

The CP-SAT model is not accepted as evidence that an output is correct. A generated assignment is converted into ordinary Python values and passed to `verify_result`. The verifier does not inspect OR-Tools variables, constraints, solver state, or internal relation-table membership. If verification fails, generation fails closed with `InternalVerificationError`.

Objective metadata follows the same trust boundary. Solver-side objective components are independently reconstructed from finished musical values; disagreement also fails closed.

## Stable hard-rule contract

`constraint_music.contract` defines stable IDs for every hard musical rule. v2.10 contains `CM001–CM054`.

New feasibility semantics are synchronized across:

1. contract metadata;
2. CP-SAT compilation;
3. independent post-solve verification;
4. hostile regression tests;
5. serialization/provenance whenever semantic state is serialized.

Search mechanisms cannot waive a `CM` rule. No-good cuts constrain which already-valid assignment may be returned next; scalarization ranks feasible assignments; Pareto filtering compares independently reconstructed objective vectors.

## Harmonic identity is decomposed

Constraint Music never collapses harmony into one magic degree or display string. Each beat may carry independent axes:

- immutable artifact/global key;
- explicit active local key;
- functional `chord_degree` or compatibility support degree;
- `ChordKind` (`triad` or `seventh`);
- inversion (`0`, `1`, or `2`);
- nullable local `tonicization_target` / target identity;
- nullable `modal_source`;
- modulation destination/boundary identity;
- concrete SATB notes.

Roman/slash/source notation is derived presentation. A target-bearing seventh is an applied dominant; a target-bearing triad under the v2.10 feature is a secondary leading-tone chord. Borrowed harmony remains source-bearing instead. The serialized primitives are sufficient for independent reconstruction.

## SATB compiler

The SATB harmonic skeleton operates at one sonority per beat. Soprano is anchored to the strong-grid melody, alto and tenor are independent solver variables, and bass reuses the beat-level bass variable.

Pitch-class variables are linked to note variables with modulo constraints. Cached allowed-assignment tables jointly constrain degree/support degree, kind, inversion, local target, modal source, and four SATB pitch classes. Diatonic harmony, applied dominants, borrowed triads, v2.9 borrowed sevenths, and v2.10 secondary leading-tone triads therefore use typed relation data rather than post-processing exceptions.

Ordering/spacing use direct integer constraints. Parallel-perfect and tendency-tone behavior use adjacent-beat transition constraints.

## Outer-voice compatibility contract

`CM005` and `CM006` retain their established meaning: strong melody/soprano and bass are members of the triadic core identified by the stored degree in the exact active local key.

Chromatic context is not unrestricted pitch permission. Tonicization, mixture, modulation, and secondary leading-tone harmony expose only states representable under this invariant.

For v2.10, a chromatic diminished root is never forged into a diatonic degree. The stored degree is a deterministic support degree selected from the active key. It must share at least two pitch classes with the diminished triad and already permit the support-to-target transition under the configured progression graph. The actual chromatic sonority is reconstructed independently from active key + target.

This boundary is a compatibility decision, not a claim that excluded harmonies are invalid music theory.

## v2.6 applied-dominant tonicization model

Applied-dominant tonicization is an opt-in local target event and requires expanded harmony. `NO_TONICIZATION_TARGET` is internal only; artifacts serialize `null` or an integer target degree.

For each supported target, the tonal layer derives the applied dominant root and exact dominant-seventh pitch classes. The SATB layer admits only complete realizations compatible with CM005/CM006. Motion constraints require immediate target resolution, downward applied-seventh resolution, and upward local-leading-tone resolution. The verifier reconstructs those consequences independently.

A target-bearing seventh remains the certified applied-dominant form in v2.10.

## v2.7 modal-mixture model

Modal mixture is an independent context axis. `NO_MODAL_SOURCE` is internal; artifacts serialize `null` or an explicit source identity.

Canonical source policy is deliberately small:

- active major -> parallel natural minor;
- active minor -> parallel major.

Borrowed triads derive source pitch classes from the active tonic, explicit source, and functional degree. Source-bearing harmony cannot carry a local target on the same beat and cannot occupy certified context/cadence anchors.

## v2.8 persistent local-key and modulation model

v2.8 introduced true persistent active-key state while keeping the artifact/global key immutable.

The first certified modulation model is intentionally narrow:

- exactly one event;
- same-mode destination at the dominant key;
- explicit destination identity;
- explicit boundary;
- fixed common-chord pivot: source I -> destination IV;
- persistent destination context after the boundary;
- destination V-I confirmation.

### Context-union storage is not chromatic permission

The strict v2.8.0a2 repair allows modulation-enabled storage domains to contain pitches admitted by any declared persistent local-key region. Every concrete melody/bass step is nevertheless gated against its exact active key. This permits destination accidentals in the destination region without leaking them backward into the source region.

The same active-key sequence drives objective tension scoring, CM002/CM003 verification, target interpretation, and modal-source interpretation.

### No terminal tendency-tone exemption

The rejected early repair skipped a generic terminal tendency check to regain feasibility. v2.8.0a2 removed that exemption. The state/domain model was repaired instead, and destination confirmation independently requires the destination leading tone plus upward semitone resolution in every SATB carrier at the terminal dominant.

## v2.9 borrowed-seventh model

v2.9 composes three mature semantic layers rather than adding another opaque context:

1. v2.5 seventh-form identity;
2. v2.7 explicit modal-source identity;
3. v2.8 explicit active local-key identity.

A source-derived seventh is admitted only if it is genuinely different from the active-key seventh and can preserve existing outer-voice semantics. The current whitelist additionally requires its chordal seventh to coincide with the already-certified active-key seventh pitch class so the established downward-step machinery remains solver/verifier symmetric.

A parallel-major source may introduce a true source leading tone. When such a leading tone occurs in an admitted borrowed seventh and is not the chordal seventh, every SATB carrier resolves upward by semitone.

Borrowed sevenths are excluded from local-target overlap, the modulation pivot, and certified destination-cadence anchors. After modulation, source derivation uses the destination active key; the original global key is never reused as stale borrowing context.

The additive hard rules are CM049–CM051.

## v2.10 secondary leading-tone model

v2.10 introduces target-derived diminished triads without adding a separate opaque chord-name state.

For a supported target degree, the theory layer obtains the target root from the exact active key, places a chromatic leading-tone root one semitone below it, and constructs the diminished triad with minor-third and diminished-fifth intervals.

The form/target pairing is semantic:

- target + `SEVENTH` -> applied dominant;
- target + `TRIAD` -> secondary leading-tone chord.

A deterministic support degree preserves CM005/CM006/CM007. The four SATB voices then realize the actual diminished sonority with the local leading tone and diminished fifth undoubled and the stable third doubled. Root/first/second inversion remain the certified inversion range.

Motion is independently explicit: the local leading tone rises by one semitone, the diminished fifth falls by one or two semitones, and the next beat must be the declared untargeted, unborrowed triadic target.

Secondary leading-tone chords cannot occupy certified modulation/cadence anchors or overlap modal source identity. After modulation, both compiler and verifier derive them from the persistent destination active key.

The additive hard rules are:

- `CM052` — secondary context, supported target, support-degree identity, and protected boundaries;
- `CM053` — target-derived diminished realization, doubling, and inversion;
- `CM054` — immediate target and tendency-tone resolution.

## Serialization and provenance

Artifact schema `2.10` commits semantic music separately from solver metadata. The semantic digest includes, when present:

- melody/rhythm/bass/chord degrees;
- SATB voices;
- chord kinds and inversions;
- local target identities;
- modal sources;
- key contexts.

Because v2.10 composes existing target/form/context fields, no synthetic secondary-chord metadata is required. Changing the target or form changes semantic provenance.

The contract version/digest, composition digest, complete artifact-content digest, verified rule IDs, and independently recomputable objective vector are stored in provenance/search metadata.

## Distinct enumeration

Exact no-good dimensions remain orthogonal:

- `melody`;
- `rhythm`;
- `bass`;
- `harmony` — stored functional/support degree sequence;
- `voicing` — alto/tenor realization;
- `harmonic_form` — kind + inversion;
- `tonicization` — nullable local target sequence;
- `modal_source` — nullable parallel-source sequence;
- `key_context` — persistent active-key sequence.

A feature never redefines an older dimension merely to fit new semantics.

## Extension boundary

Future chromatic expansion should continue to add explicit typed state and independent verification. Current deferred boundaries include secondary leading-tone seventh chords, third-inversion sevenths, richer voice-leading policy revisions, multi-modulation chains, distant-key/enharmonic reinterpretation, augmented-sixth/Neapolitan reinterpretation, and probabilistic key-center inference.
