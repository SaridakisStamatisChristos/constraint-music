# Engineering handoff implementation status

This document records the implementation state against
`Constraint_Music_Engineering_Handoff.md`. It deliberately distinguishes repaired
release behavior from unfinished research evidence. A passing build or CI run is
not a publication-readiness claim.

## Scope and baseline

- Upstream revision: `07c1e312bf40a9564ccc0e13384bcc4653e5eb03`
- Implemented package/schema/contract line: `2.13.0a1` / `2.13` / `2.13`
- Certification profile exercised: `certified-satb`
- Canonicalization profile: `constraint-music-json-v1`

## Work-package status

| Work package | Status | Implemented evidence | Remaining work |
| --- | --- | --- | --- |
| EH-01 | Core repair complete | Strict current-schema shape validation, fail-closed direct and JSON verification, stable `CM001` blocking, malformed-type/length tests, and non-certifying legacy dispatch. | Expand the adversarial matrix across every field and supported legacy fixture. |
| EH-02 | Core repair complete | Canonical SATB event projection, exact S/A/T/B export, independent `mido` parse-back, key-context events, atomic publication, output digest, overlap rejection, a 12-case quality/inversion/register transport corpus, combined tie/rest melody coverage, and verification/replace fault injection. | Continue expanding real solved cross-feature delivery fixtures; the repaired certified profiles and declared failure paths are covered. |
| EH-03 | Core repair complete | Independent request binding, contract/request/composition/artifact/output digests, fresh validation comparison, exact evaluated-ID claims, display-claim checks, and strict write-time verification. | Add authenticated signing only if authenticated origin becomes a product claim. |
| EH-04 | Core instrumentation complete | Versioned 57-rule inventory; typed `PASS`/`FAIL`/`NOT_APPLICABLE`/`BLOCKED` ledger; predicate-level `visited` instrumentation; fail-closed `NOT_VISITED` outcomes; structured diagnostic code/rule/feature/location/voice fields; and measured per-compilation phase registrations with exact CP-SAT constraint spans. The historical compiled-ID alias has been replaced by a real registration catalogue. | Continue refining global runtime diagnostics to narrower beat/transition locations where useful; compiler registrations remain coverage evidence, not an equivalence proof. |
| EH-05 | Core refactor complete | Typed, immutable semantic dispatch is built only from exact local reconstructions for borrowed sevenths, secondary leading-tone triads, and secondary leading-tone sevenths. SATB and modulation verification select mutually exclusive rules by semantic identity rather than diagnostic text; resolution remains independently checked. Adversarial tests cover cosmetic message changes, false target/kind/source/inversion metadata, third-inversion scope, and resolution separation. | Continue expanding the cross-feature interaction corpus, especially combined modulation/modal/secondary fixtures, without weakening the fail-closed dispatch boundary. |
| EH-06 | Operational boundary complete | Checker/certifier imports and executes without OR-Tools; solver loading is lazy; generation dependencies are optional; isolation is tested. | Further split shared result types from mixed runtime modules if a stronger semantic-independence claim is desired. |
| EH-07 | Core oracle complete | Standard-library-only, production-import-guarded oracles cover diatonic triads/sevenths, applied dominants, secondary sevenths, borrowed sevenths, secondary diminished triads, bounded persistent modulation, rhythm, motifs, phrase form, and raw-byte MIDI delivery. Differential fixtures exercise all chromatic tonics, both modes, every diatonic degree, eligible contextual target/degree and certified inversion, all valid modulation boundaries, every four-step rhythm-state sequence, every motif/phrase relation and cadence label, phrase boundaries/roles/period strength, exact delivery projections and output hashes, exact doubling/completeness, and hostile context/tone/inversion/resolution/articulation/density/relation/event/anchor mutations. The versioned reference records source hashes, shared dependencies, adjudication rules, and non-claims. | Continue growing the hand-adjudicated full-piece interaction corpus; changes to oracle sources require new hashes and fresh differential evidence. |
| EH-08 | Core bounded evidence complete | Separately named secondary-seventh partitions persist 27,648 pitch-class cases, 4,824 exact absolute-register cases, 680 context/anchor truth-table cases, 540,000 voice-resolution cases, and a 24-case complete-verifier control/fault matrix. The pinned OR-Tools 9.15.6755 evidence also contains a six-case generator-boundary matrix, one exact named `CM057` compiler-constraint deletion rejected by the oracle/verifier/finalizer, and five valid plus five faulty cross-feature cases spanning tonicization, modal mixture, rhythm, authentic cadence, and modulation. Bounds, pruning, registrations, hashes, category counts, and first disagreements are recorded; every partition currently has zero disagreements or escapes. | Continue breadth expansion across additional named compiler clauses and larger interaction topologies; the handoff's direct-deletion and cross-feature gaps are closed without claiming global equivalence. |
| EH-09 | Core benchmark complete | A frozen 32-case corpus includes 30 attacks and two valid controls across realized music, harmonic claims, malformed structure, integrity/request binding, and certified MIDI delivery. The versioned manifest defines stable IDs, T0–T4 adversary tiers, expected outcomes, and cluster-preserving development/evaluation splits. Checked-in JSONL preserves raw outcomes/issues; the summary reports family/tier/split metrics, 15-cluster Wilson uncertainty, source hashes, 30/30 attack detection, 2/2 control acceptance, and zero crashes. | Expand with independently curated artifacts and additional attack clusters before making population-level robustness claims; the single pinned fixture remains a finite benchmark. |
| EH-10 | Core comparative evidence complete | Research-only leave-one-channel-out signal ablations preserve all 32 EH-09 raw cases and reasons without adding production bypasses. The four overlapping channels retain 24/30, 25/30, 23/30, and 24/30 detections when wire-shape, semantic, integrity/request, and delivery signals are respectively omitted, with zero control flags. Exact-version music21 9.9.2 adapters explicitly normalize shared semantics and show zero disagreements on 9,840 bounded parallel-perfect cases and 126 bounded C-major triad-policy cases. Raw rows, exact denominators, exclusions, dependency identity, and implementation hashes are checked in and replayed in CI. | Expand to independently selected external tools and broader predeclared shared domains before making comparative-performance, general-equivalence, or superiority claims. |
| EH-11 | Core performance evidence complete | The controlled matrix records nine feature profiles at 1, 2, 4, 8, 16, and 32 bars across five fixed seeds and single/throughput worker modes on a pinned Python/OR-Tools environment. Raw rows preserve all 540 single-output attempts plus 18 multi-output throughput cases, including 40 declared scope exclusions, solver outcomes, timing decomposition, peak RSS, certification overhead, and run provenance. The checked-in report records 126 generated, strictly accepted, and released artifacts from 500 runnable single-output cases without converting timeouts into successes. | Re-run on owned, quiescent hardware with longer solve budgets and repeated independent runners before making capacity, latency-SLO, or cross-platform performance claims. |
| EH-12 | Closure defined; execution partial | CI covers supported Python versions, lint, typing, tests, build, checker-only installation, and scheduled bounded enumeration. The versioned [EH-12 closure matrix](EH12_CLOSURE_MATRIX.md) freezes the bounded claim, adjudicates every EH-01–EH-11 residual as satisfied/deferred/blocking, binds every deferral to an explicit non-claim, and fails structural validation on drift. | Publication gate remains HOLD until the PR-34 consolidated assurance corpus, PR-35 one-command release validator, and independent clean-checkout review satisfy `EH12-G02` through `EH12-G04`. |

## Verified release gates

The following commands passed in the implementation workspace:

```text
python -m ruff check src tests research
python -m mypy src
python -m pytest -q
python -m build
python -m constraint_music generate examples/four_bar_arch.yaml \
  --output e2e/piece.mid --json e2e/piece.json
python -m constraint_music certify e2e/piece.json \
  --spec examples/four_bar_arch.yaml --midi e2e/piece.mid \
  --certificate e2e/certificate.json
```

The end-to-end certification returned `PASS (EXTERNAL REQUEST + DELIVERY)` and
independently observed 64 delivery note events. The generated certificate records
all binding digests and the exact evaluated/not-applicable rule sets.

The full local suite contains 606 passing tests and reports 82.66% branch-aware
source coverage. The combined `melody-plus-satb` CLI round trip also passed with 96
independently observed note events. The current bounded evidence records 27,648
pitch-class cases (5,184 accepted and 22,464 rejected), 4,824 exact register cases
(1,233 accepted and 3,591 rejected), 680 context/anchor cases (83 accepted and 597
rejected), 540,000 resolution cases (4,320 accepted and 535,680 rejected), and 24
complete-verifier cases. The pinned generator-boundary matrix rejects all five injected
semantic/objective faults before return; the exact named compiler deletion and all five
cross-feature faults are also rejected with zero escapes. The full corruption benchmark
detects all 30 attacks, accepts both controls, and reports zero crashes across 15
split-isolated attack clusters; its cluster-level 95% Wilson interval is 0.796117–1.0.
The EH-10 signal ablation preserves full 30/30 union coverage and exposes 6, 5, 7, and
6 unique catches for wire-shape, semantic, integrity/request, and delivery channels.
The two scope-normalized music21 9.9.2 adapters agree on all 9,966 bounded shared cases.
The EH-11 performance run records 540 attempts on an AMD EPYC 7763 runner: 40
declared exclusions, 500 runnable cases, and 126 generated artifacts that all passed
strict artifact certification and delivery verification. These are finite observations
from the recorded runner and solve budget, not capacity or latency guarantees.

## Claim boundary

The implementation repairs the demonstrated P0 artifact-shape, delivery, claim,
and external-request-binding defects. It provides substantial assurance
infrastructure, but it does **not** establish global musical soundness,
solver/checker equivalence, superiority to external systems, research novelty, or
publication readiness. Those stronger claims remain gated on the unfinished work
listed above. EH-12 closure status and normative acceptance criteria are tracked in
[`EH12_CLOSURE_MATRIX.md`](EH12_CLOSURE_MATRIX.md).
