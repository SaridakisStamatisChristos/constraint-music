# EH-12 closure matrix and claim freeze

## Decision

**Publication gate: HOLD.** EH-01 through EH-11 are core-complete, but the bounded
publication package still requires the consolidated assurance corpus, the one-command
release validator, and an independent clean-checkout review.

The machine-readable source of truth is
[`research/configs/eh12_closure_matrix.json`](../research/configs/eh12_closure_matrix.json).
`python -m research.validate_eh12_closure` rejects missing work packages, unknown
non-claims, unreferenced deferrals, missing evidence, duplicate IDs, documentation
drift, or a decision inconsistent with the remaining blockers.

## Frozen claim

`bounded-assurance-v1`:

> Constraint Music implements a versioned, fail-closed generation and certification
> pipeline whose current-schema validation, request binding, declared rule outcomes,
> bounded oracle comparisons, corruption benchmark, scope-normalized comparator
> adapters, and recorded performance matrix are reproducible within their explicitly
> declared finite domains.

This covers schema/contract 2.13, the `certified-satb` and `melody-plus-satb`
delivery profiles, the finite domains recorded in the repository, and the pinned
dependencies/environment declarations attached to each evidence family.

## Closure rule

Every inherited residual has exactly one classification:

- **satisfied** — implemented with repository evidence checkable from a clean checkout;
- **deferred by non-claim** — unnecessary for the frozen claim and bound to an explicit
  non-claim;
- **blocker** — required by the frozen claim or release process and assigned to a
  concrete closure slice.

EH-12 may become complete only when no blocker remains, all satisfied evidence exists,
all deferrals remain bound to explicit non-claims, and the independent review gate is
satisfied.

## Inherited residuals

| ID | Source | Classification | Disposition |
| --- | --- | --- | --- |
| `EH12-R01` | EH-01 | Blocker → PR-34 | Complete current-schema field-family mutations and prove every supported legacy fixture non-certifying. |
| `EH12-R02` | EH-02 | Blocker → PR-34 | Add solved cross-feature controls with exact certified MIDI parse-back and output digests. |
| `EH12-R03` | EH-03 | Deferred → `NC-01` | Signing is unnecessary without an authenticated-origin claim. |
| `EH12-R04` | EH-04 | Deferred → `NC-09` | Existing typed outcomes and phase spans suffice; universally minimal locations are not claimed. |
| `EH12-R05` | EH-05 | Blocker → PR-34 | Add pairwise modulation/modal/secondary controls and targeted faults on disjoint beats. |
| `EH12-R06` | EH-06 | Deferred → `NC-04` | Checker-only isolation is proven; absolute codebase independence is not claimed. |
| `EH12-R07` | EH-07 | Blocker → PR-34 | Add frozen, hand-adjudicated full-piece control/fault pairs for each consolidated interaction family. |
| `EH12-R08` | EH-08 | Blocker → PR-34 | Delete at least two more named clauses from distinct compiler phases and persist witnesses, spans, hashes, and escape counts. |
| `EH12-R09` | EH-09 | Blocker → PR-34 | Add at least three independently curated valid fixtures with stable identities and exact denominators. |
| `EH12-R10` | EH-10 | Deferred → `NC-06` | Existing music21 adapters stay bounded; no superiority or general-equivalence claim is made. |
| `EH12-R11` | EH-11 | Deferred → `NC-07` | Recorded timings remain finite observations, not SLO, capacity, or cross-platform guarantees. |

Detailed acceptance criteria live in the machine-readable matrix and are normative.

## Explicit non-claims

| ID | Excluded claim |
| --- | --- |
| `NC-01` | Authenticated authorship, origin, or non-repudiation. |
| `NC-02` | Universal musical soundness, aesthetics, or unique tonal interpretation. |
| `NC-03` | Global solver/compiler/checker equivalence outside declared finite partitions. |
| `NC-04` | Absolute implementation independence from every shared data type/helper. |
| `NC-05` | Population-level robustness inferred from the finite corruption corpus. |
| `NC-06` | Comparative superiority, general external equivalence, or SOTA performance. |
| `NC-07` | Capacity, latency-SLO, cross-platform, or production-performance guarantees. |
| `NC-08` | Research novelty, venue acceptance, or publication readiness established by CI alone. |
| `NC-09` | Beat- or transition-local diagnostics for every global validation failure. |

## EH-12 gates

| Gate | Status | Acceptance boundary |
| --- | --- | --- |
| `EH12-G01` | Satisfied by PR-33 | Claim frozen; EH-01–EH-11 residuals classified; matrix and documentation structurally validated. |
| `EH12-G02` | Blocker → PR-34 | One versioned consolidated corpus satisfies all PR-34 residual criteria and preserves raw controls, faults, exclusions, and crashes. |
| `EH12-G03` | Blocker → PR-35 | One documented command validates dependencies, tests, builds, checker isolation, evidence replay/hashes, and claim drift in CI. |
| `EH12-G04` | Blocker → INDEPENDENT-REVIEW | Fresh-clone execution and claim/evidence audit by a reviewer who did not author the closure changes. |

Research novelty and venue suitability remain a separate, live-literature research
gate. Completing EH-12 makes the repository reproducible for its bounded engineering
claim; it cannot by itself establish novelty or guarantee publication.
