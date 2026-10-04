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
| EH-02 | Core repair complete | Canonical SATB event projection, exact S/A/T/B export, independent `mido` parse-back, key-context events, atomic publication, output digest, and delivery fault tests. | Broaden fixtures across every quality/inversion and add a larger combined melody-profile corpus. |
| EH-03 | Core repair complete | Independent request binding, contract/request/composition/artifact/output digests, fresh validation comparison, exact evaluated-ID claims, display-claim checks, and strict write-time verification. | Add authenticated signing only if authenticated origin becomes a product claim. |
| EH-04 | Partial | Versioned 57-rule inventory, typed `PASS`/`FAIL`/`NOT_APPLICABLE`/`BLOCKED` ledger, exact ledger cardinality, and applicability tests. | Add predicate-level visit instrumentation, structured diagnostic locations, and real compiler-registration coverage instead of the historical ID alias. |
| EH-05 | Core refactor complete | Typed, immutable semantic dispatch is built only from exact local reconstructions for borrowed sevenths, secondary leading-tone triads, and secondary leading-tone sevenths. SATB and modulation verification select mutually exclusive rules by semantic identity rather than diagnostic text; resolution remains independently checked. Adversarial tests cover cosmetic message changes, false target/kind/source/inversion metadata, third-inversion scope, and resolution separation. | Continue expanding the cross-feature interaction corpus, especially combined modulation/modal/secondary fixtures, without weakening the fail-closed dispatch boundary. |
| EH-06 | Operational boundary complete | Checker/certifier imports and executes without OR-Tools; solver loading is lazy; generation dependencies are optional; isolation is tested. | Further split shared result types from mixed runtime modules if a stronger semantic-independence claim is desired. |
| EH-07 | Partial | Standard-library-only, production-import-guarded oracles cover diatonic triads/sevenths, applied dominants, secondary sevenths, borrowed sevenths, and secondary diminished triads. Differential fixtures exercise all chromatic tonics, both modes, every diatonic degree, every eligible contextual target/degree and certified inversion, exact doubling/completeness, and hostile context/tone/inversion/resolution mutations. | Extend the independently authored oracle and positive/negative fixtures to modulation, rhythm, phrase, and delivery rules. |
| EH-08 | Partial | A bounded secondary-seventh enumerator reports generated cardinalities and persists classifications; current run visited 27,648 cases. | Add absolute-register, resolution, context, complete-verifier, pinned-CP, fault-injection, and cross-feature differential partitions. |
| EH-09 | Partial smoke infrastructure | Deterministic semantic mutations, tiered outcomes, valid controls, and a runnable corruption-benchmark harness exist. | Build and freeze the full adjudicated corpus, manifests, family/tier metrics, clustered uncertainty, and development/evaluation split. |
| EH-10 | Not executed | None claimed. | Implement internal ablations and fairly scoped, pinned external baseline adapters before reporting comparative effects. |
| EH-11 | Not executed | None claimed. | Implement and run the declared multi-size, multi-seed timing/memory/yield matrix on recorded hardware. |
| EH-12 | Partial | CI covers supported Python versions, lint, typing, tests, build, checker-only installation, and scheduled bounded enumeration; assurance and reproducibility docs are present. | Publication gate remains HOLD until the EH-07 through EH-11 evidence program is complete and adjudicated. |

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

The final local suite contains 418 passing tests and reports 80.41% branch-aware
source coverage. The combined `melody-plus-satb` CLI round trip also passed with
96 independently observed note events. The bounded oracle run visited 27,648
cases (5,184 accepted and 22,464 rejected), while the smoke corruption corpus
classified all four initial mutations as `REJECT` or `BLOCKED` without a crash.

## Claim boundary

The implementation repairs the demonstrated P0 artifact-shape, delivery, claim,
and external-request-binding defects. It provides substantial assurance
infrastructure, but it does **not** establish global musical soundness,
solver/checker equivalence, superiority to external systems, research novelty, or
publication readiness. Those stronger claims remain gated on the unfinished work
listed above.
