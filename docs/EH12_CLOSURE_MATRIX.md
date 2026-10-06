# EH-12 closure matrix and claim freeze

## Decision

**Publication gate: HOLD.** EH-01 through EH-11 are core-complete and the consolidated
assurance corpus and repository-authored release validator are satisfied. The bounded
publication package still requires an independent clean-checkout review.

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
| `EH12-R01` | EH-01 | Satisfied by PR-34 | Twenty-six fail-closed cases cover every declared current-schema field family and schema 2.12, with no crashes. |
| `EH12-R02` | EH-02 | Satisfied by PR-34 | Four certified deliveries record exact parse-back counts and output digests; the articulated control covers `melody-plus-satb`. |
| `EH12-R03` | EH-03 | Deferred → `NC-01` | Signing is unnecessary without an authenticated-origin claim. |
| `EH12-R04` | EH-04 | Deferred → `NC-09` | Existing typed outcomes and phase spans suffice; universally minimal locations are not claimed. |
| `EH12-R05` | EH-05 | Satisfied by PR-34 | Three pairwise modulation/modal/secondary controls use disjoint witness beats and reject reconstructed-semantic faults. |
| `EH12-R06` | EH-06 | Deferred → `NC-04` | Checker-only isolation is proven; absolute codebase independence is not claimed. |
| `EH12-R07` | EH-07 | Satisfied by PR-34 | Every interaction has a frozen full-piece control/fault pair, adjudication note, and pinned oracle hashes. |
| `EH12-R08` | EH-08 | Satisfied by PR-34 | Named `CM057`, `CM016`, and `CM018` deletions span three compiler phases and record zero escapes. |
| `EH12-R09` | EH-09 | Satisfied by PR-34 | Three distinct specifications/seeds retain fixture identity, clusters, outcomes, raw issues, crashes, and exclusions. |
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
| `EH12-G02` | Satisfied by PR-34 | The versioned 39-case corpus, raw JSONL, and derived summary satisfy all PR-34 residual criteria deterministically. |
| `EH12-G03` | Satisfied by PR-35 | `python -m research.validate_release_assurance` validates exact research pins, lint, types, tests, coverage, builds, a solver-free wheel install, four deterministic evidence replays, all 12 evidence hashes, and the frozen claim/closure state; CI runs the same command. |
| `EH12-G04` | Blocker → INDEPENDENT-REVIEW | Fresh-clone execution and claim/evidence audit by a reviewer who did not author the closure changes. |

Research novelty and venue suitability remain a separate, live-literature research
gate. Completing EH-12 makes the repository reproducible for its bounded engineering
claim; it cannot by itself establish novelty or guarantee publication.
