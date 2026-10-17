# Documentation

Constraint Music documentation is organized by durable concern rather than implementation chronology.

## Architecture and trust boundary

- [Architecture Overview](ARCHITECTURE_OVERVIEW.md) — visual end-to-end system diagram covering specification, constraint compilation, CP-SAT search, independent certification, delivery, and fail-closed rejection.
- [Architecture](ARCHITECTURE.md) — generator, constraint model, verifier, certification, and delivery flow.
- [Assurance Boundary](ASSURANCE_BOUNDARY.md) — what independent verification does and does not establish.
- [Executable Contract](EXECUTABLE_CONTRACT.md) — rule outcomes and executable hard-constraint contract.
- [Verification](VERIFICATION.md) — independent rule checking and certification behavior.
- [Reproducibility](REPRODUCIBILITY.md) — deterministic settings, evidence replay, and research pins.
- [Engineering Assurance Status](ENGINEERING_ASSURANCE_STATUS.md) — current bounded assurance state and explicit non-claims.

## Musical model

- [SATB Harmony](SATB_HARMONY.md)
- [Expanded Harmony](EXPANDED_HARMONY.md)
- [Applied-Dominant Tonicization](TONICIZATION.md)
- [Modal Mixture](MODAL_MIXTURE.md)
- [Borrowed Seventh Chords](BORROWED_SEVENTHS.md)
- [Secondary Leading-Tone Triads](SECONDARY_LEADING_TONE.md)
- [Secondary Leading-Tone Sevenths](SECONDARY_LEADING_TONE_SEVENTHS.md)
- [Phrase Grammar](PHRASE_GRAMMAR.md)
- [Rhythm and Motifs](RHYTHM_AND_MOTIFS.md)
- [Enumeration and Pareto Search](ENUMERATION_AND_PARETO.md)

## Request-bound harmonization

- [Request-Bound Harmonization](REQUEST_BOUND_HARMONIZATION.md) — the opt-in request-bound SATB API and its independent checks.
- [Cross-System Study Status](CROSS_SYSTEM_STUDY_STATUS.md) — v1/v2/v3 study lineage, retained negative findings, and claim boundaries.
- [Cross-System Conformance Manuscript Draft](CROSS_SYSTEM_CONFORMANCE_PAPER_DRAFT.md) — integrated research manuscript draft.
- [Cross-System Contribution Update](CROSS_SYSTEM_CONTRIBUTION_UPDATE.md) — focused literature/contribution analysis.
- [Research Replay Permission Template](RESEARCH_REPLAY_PERMISSION_TEMPLATE.md) — owner-controlled external replay route under the proprietary license.

## Assurance evidence

The EH-prefixed documents are durable identifiers for bounded assurance evidence, not product-development milestones. They are retained because tests, manifests, raw observations, and claim-boundary validation refer to them directly.

- [EH-10 Assurance Comparison](EH10_ASSURANCE_COMPARISON.md)
- [EH-11 Performance Evaluation](EH11_PERFORMANCE_EVALUATION.md)
- [EH-11 Performance Results](EH11_PERFORMANCE_RESULTS.md)
- [EH-12 Assurance Corpus](EH12_ASSURANCE_CORPUS.md)
- [EH-12 Closure Matrix](EH12_CLOSURE_MATRIX.md)
- [Multi-Fixture Assurance Protocol](MULTIFIXTURE_ASSURANCE_PROTOCOL.md)
- [Multi-Fixture Assurance Evaluation](MULTIFIXTURE_ASSURANCE_EVALUATION.md)
- [Multi-Fixture Contribution Preflight](MULTIFIXTURE_CONTRIBUTION_PREFLIGHT.md)

Raw and replayable evidence lives under [`../research/`](../research/README.md).

## Maintenance and evolution

- [Project History](HISTORY.md) — concise origin and recovery context.
- [Future Work](FUTURE_WORK.md) — unimplemented directions only; not a claim of current capability.
- [2.13 Migration](V2_13_MIGRATION.md) — artifact/contract migration guidance.
- [`../CHANGELOG.md`](../CHANGELOG.md) — release-level change history.

## Documentation policy

Product-facing documents describe the current system. Historical experiment labels and source snapshots are retained only where they carry reproducibility value. Git history remains the source for implementation chronology that no longer belongs in the active documentation tree.
