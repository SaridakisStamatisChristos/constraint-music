# Constraint Music

**Deterministic symbolic music synthesis with explicit hard constraints, CP-SAT optimization, and independent post-solve verification.**

Constraint Music treats composition as a verifiable constraint problem. A YAML specification is compiled into an OR-Tools CP-SAT model; the solver produces melody, rhythm, bass, harmonic identity, and a solver-native SATB realization; a separate application-level verifier reconstructs the declared musical semantics from ordinary serialized values; only verified results are exported.

> Current release line: **2.12.0a1** — complete verifier-certified secondary leading-tone seventh support within the declared common-practice tonicization domain, including eligible fully diminished and half-diminished qualities and all four inversions.

## Pipeline

```text
YAML GenerationSpec
      |
      v
pitch + rhythm + phrase grammar
      |
      +--> chord degree / deterministic support degree
      +--> harmonic form + inversion
      +--> nullable local target identity
      +--> nullable modal source
      +--> persistent active-key context
      |
      v
OR-Tools CP-SAT compiler
      |
      v
weighted solve / no-good enumeration / Pareto candidate search
      |
      v
ordinary serialized musical values
      |
      +--> independent 57-rule verifier
      +--> independent objective-vector recomputation
      +--> semantic provenance digests
      |
      +----> MIDI with real ties/rests
      +----> JSON + SATB + harmonic/context metadata
```

A solver status of `OPTIMAL` or `FEASIBLE` is never sufficient. Solver/verifier or solver/objective disagreement fails closed.

## Release progression

- **v2.1** — explicit rhythm CSP and motif grammar.
- **v2.2** — phrase grammar and phrase-local cadence semantics.
- **v2.3** — exact distinct enumeration and bounded Pareto search.
- **v2.4** — solver-native SATB harmony.
- **v2.5** — opt-in diatonic seventh vocabulary and structured inversions.
- **v2.6** — verified applied-dominant tonicization.
- **v2.7** — verified modal mixture with explicit parallel-source identity.
- **v2.8** — persistent active local-key regions and one certified dominant-key modulation.
- **v2.8.0a2** — strict modulation repair with context-union domains and no terminal tendency-tone exemption.
- **v2.9** — source-aware borrowed seventh chords.
- **v2.10** — target-derived secondary leading-tone triads.
- **v2.11** — fully diminished secondary leading-tone sevenths with exact functional disambiguation.
- **v2.12** — complete secondary leading-tone seventh certification: eligible `°7`/`ø7` qualities, all four inversions, exact quality-specific tendency behavior, and scoped chromatic outer-voice support.

## Harmonic identity stays decomposed

Constraint Music deliberately avoids a single opaque Roman-numeral field. Each beat may carry independent semantic axes:

- `harmony` — functional/support chord-degree sequence;
- `harmonic_form` — chord kind + inversion;
- `tonicization` — nullable local target identity shared by certified target-bearing chromatic functions;
- `modal_source` — nullable canonical parallel source;
- `key_context` — persistent active local-key sequence / modulation identity;
- `voicing` — SATB realization.

The artifact-global key remains immutable. Persistent modulation changes active-key interpretation without rewriting that global key.

A non-null local target is interpreted together with harmonic form and independently reconstructed pitch identity:

- target + triad under the v2.10 feature => secondary leading-tone triad;
- target + seventh reconstructing exactly as active-key `V7/x` => applied dominant;
- target + seventh reconstructing as an eligible target-derived `vii°7/x` or `viiø7/x` form => secondary leading-tone seventh.

No opaque secondary-function or quality field is required as the artifact source of truth.

## Expanded harmony and applied dominants

Expanded harmony is opt-in:

```yaml
harmony_vocabulary: triads+sevenths
minimum_seventh_chords: 1
```

Applied dominants additionally use:

```yaml
tonicization_enabled: true
minimum_applied_dominants: 1
```

`minimum_applied_dominants` counts only exact active-key `V7/x` realizations. A target-bearing secondary leading-tone seventh cannot satisfy that minimum merely because it is a seventh with a target.

See [Expanded Harmony](docs/EXPANDED_HARMONY.md) and [Applied-Dominant Tonicization](docs/TONICIZATION.md).

## Modal mixture and borrowed sevenths

```yaml
modal_mixture_enabled: true
minimum_borrowed_chords: 1
```

Major active keys use parallel natural minor as their canonical source; minor active keys use parallel major. v2.9 adds a deliberately filtered subset of source-derived borrowed sevenths when expanded harmony is also enabled. Borrowing remains independent from local-target identity and persistent key context.

See [Modal Mixture](docs/MODAL_MIXTURE.md) and [Borrowed Seventh Chords](docs/BORROWED_SEVENTHS.md).

## Persistent local key and controlled modulation

v2.8 distinguishes persistent modulation from one-chord local-target events. Its conservative certified model supports one same-mode modulation to the dominant key with:

- an explicit destination key and boundary;
- source I as a common-chord pivot reinterpreted as destination IV;
- persistent destination-key interpretation after the boundary;
- destination V-I confirmation;
- one serialized active-key context per beat.

The strict v2.8.0a2 repair keeps exact active-key pitch admission and destination leading-tone resolution through the final cadence.

## Secondary leading-tone triads

```yaml
secondary_leading_tone_enabled: true
minimum_secondary_leading_tone_chords: 1
```

v2.10 derives `vii°/x` from the exact active local key and explicit non-tonic target. The chromatic diminished root is not forged into a fake diatonic degree; instead, a deterministic support degree preserves progression semantics while target + voicing reconstruct the actual sonority.

See [Secondary Leading-Tone Triads](docs/SECONDARY_LEADING_TONE.md).

## v2.12: complete secondary leading-tone sevenths

```yaml
harmony_vocabulary: triads+sevenths
secondary_leading_tone_seventh_enabled: true
minimum_secondary_leading_tone_seventh_chords: 1
```

For a **major local target**, the certified family is:

```text
vii°7/x   vii°65/x   vii°43/x   vii°42/x
viiø7/x   viiø65/x   viiø43/x   viiø42/x
```

For a **minor local target**, the certified family is:

```text
vii°7/x   vii°65/x   vii°43/x   vii°42/x
```

Diminished and augmented target triads are not treated as local tonics by this subsystem.

Certification requires:

- exact target-derived four-tone pitch content, each pitch class once;
- independent reconstruction of fully diminished vs. eligible half-diminished quality;
- root, first, second, or third inversion with actual bass/inversion agreement;
- inversion `3` only on a beat independently reconstructed as a secondary leading-tone seventh;
- immediate resolution to the declared untargeted, unborrowed triadic target;
- local leading tone/root `+1` semitone;
- diminished fifth `-1` for a major target and `-2` for a minor target;
- fully diminished chordal seventh `-1` semitone;
- half-diminished chordal seventh `-2` semitones;
- the same rules in every SATB voice, including the bass of a genuine `42`;
- no modal-source overlap and no contamination of certified cadence/modulation anchors;
- post-modulation reconstruction against the persistent destination active key, never the stale global key.

The chromatic outer-voice expansion needed for genuine third inversion is routed only when this feature is enabled. Ordinary harmony retains the earlier domain and inversion contract.

See [Secondary Leading-Tone Seventh Chords](docs/SECONDARY_LEADING_TONE_SEVENTHS.md) and [v2.12 Release Notes](docs/V2_12_RELEASE_NOTES.md).

## Hard-constraint contract

v2.12 exposes **57 stable hard-rule IDs**:

- `CM001–CM021` — tonal, rhythmic, motif, and articulation rules;
- `CM022–CM026` — phrase structure;
- `CM027–CM032` — SATB contract;
- `CM033–CM036` — expanded harmonic form and seventh behavior;
- `CM037–CM040` — exact applied-dominant tonicization;
- `CM041–CM042` — modal-source context and borrowed-triad realization;
- `CM043–CM048` — persistent key context and controlled modulation;
- `CM049–CM051` — borrowed-seventh eligibility, realization, and tendencies;
- `CM052–CM054` — secondary leading-tone triad context, realization, and resolution;
- `CM055–CM057` — complete secondary leading-tone seventh context/quality, four-tone realization/inversion, and exact target/tendency resolution.

Search/ranking semantics cannot waive a hard rule.

See [Verification](docs/VERIFICATION.md).

## Install

Python 3.11+:

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Generate

```bash
constraint-music generate examples/secondary_leading_tone_sevenths.yaml \
  --output build/composition.mid \
  --json build/composition.json \
  --print-grid
```

## Verify without rerunning CP-SAT

```bash
constraint-music verify build/composition.json
```

The verifier rechecks the musical contract plus artifact schema, contract digest, semantic composition digest, full artifact-content digest, and objective-vector metadata. Current package version is `2.12.0a1`; artifact and constraint-contract versions are `2.12`.

Older payloads remain loadable without inventing newer semantic metadata when the corresponding feature is disabled. `--allow-legacy` remains available for intentional inspection of older provenance versions.

## Reproducibility

Use `workers: 1` with a fixed `seed` for deterministic regression work and deterministic enumeration order. Multi-worker CP-SAT search is for performance and should not be assumed to return an identical optimum or enumeration order on every runtime.

## Quality gates

Every supported interpreter runs the same complete gate:

```bash
ruff check src tests
mypy --python-version <3.11|3.12|3.13> src
pytest --cov=constraint_music --cov-report=term-missing
python -m build
```

GitHub Actions runs those gates independently on Python **3.11, 3.12, and 3.13**. The v2.12 pre-merge baseline is **147 tests passing**, **80% branch-aware coverage**, strict mypy clean across **27 source files**, and successful package builds on all three interpreters.

## Scope boundary

Independent verification is an application-level separation of trust, not a formal proof of OR-Tools, Python, or the host machine. Constraint satisfaction demonstrates conformance to the declared executable contract; it does not prove aesthetic quality or complete historical-style authenticity.

v2.12 completes the secondary leading-tone seventh family claimed by this subsystem. Separate future domains include arbitrary modulation chains, distant/enharmonic modulation, broad enharmonic reinterpretation, augmented-sixth/Neapolitan reinterpretation, unrestricted chromatic-harmony inference, free key-center inference, and probabilistic harmony certification.

See [Architecture](docs/ARCHITECTURE.md), [Verification](docs/VERIFICATION.md), [History](docs/HISTORY.md), [Roadmap](docs/ROADMAP.md), and [Changelog](CHANGELOG.md).
