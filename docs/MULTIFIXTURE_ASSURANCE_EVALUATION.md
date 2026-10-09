# Multi-composition assurance evaluation v1

The fixed study generated 16/16 distinct musical artifacts and accepted 32/32 untouched artifact-and-delivery controls. Among 456 held-out mutation slots, 332 were applicable: 284 were rejected and 48 blocked at wire admission. The other 124 were retained as inapplicable. No applicable held-out fault was accepted, crashed, or produced a harness error; no compared independent-oracle predicate disagreed. These are finite-corpus observations under the declared contract, not a population guarantee.

## Frozen identities

| Artifact | Identity |
| --- | --- |
| Corpus | `multifixture-assurance-v1` |
| Repository base | `ef7e8c5a882e07fce5f862fca20fb9e3bb5a3c24` |
| Protocol commit | `9823544b84cd3fe658201780824716805cf77ef2` |
| Generation/evaluation implementation commit | `975b284f9ef3d1a86443e81877fc637be349b803` |
| Evidence commit | `8fef080805302b6aaa549e9a6bd816331d593566` |
| Manifest SHA-256 | `cf5f32fea474e308051eac21d1f0b60ab20dff624a80ab63a13159a5e0b55db9` |
| Implementation SHA-256 | `69cfaa464e1f4e735785e7c7c06a41fc5ea59fbd0d09822eda20a996cd18289e` |
| Deterministic raw canonical SHA-256 | `764d3d0ccacaa6105afede742fb1a5e99972e5647bd65c8fde71770f33f8d39a` |

The protocol was committed before generating either development or evaluation fixtures. Implementation was committed before the corresponding run; the study attests a clean checkout. Source-file hashes cover the production package, independent oracles, and new evaluator/adapter. The existing EH-09/EH-12 sources, denominators and frozen evidence remain byte-for-byte unchanged.

## Candidate yield and full accounting

| Split | Stratum | Planned | Excluded | UNKNOWN | INFEASIBLE | Other failure | Generated | Strict fixtures | Strict profile controls |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| development | applied | 1 | 0 | 0 | 0 | 0 | 1 | 1 | 2 |
| development | base | 1 | 0 | 0 | 0 | 0 | 1 | 1 | 2 |
| development | interaction-rhythm | 1 | 0 | 0 | 0 | 0 | 1 | 1 | 2 |
| development | mixture | 1 | 0 | 0 | 0 | 0 | 1 | 1 | 2 |
| evaluation | applied | 2 | 0 | 0 | 0 | 0 | 2 | 2 | 4 |
| evaluation | base | 2 | 0 | 0 | 0 | 0 | 2 | 2 | 4 |
| evaluation | interaction-rhythm | 2 | 0 | 0 | 0 | 0 | 2 | 2 | 4 |
| evaluation | mixture | 2 | 0 | 0 | 0 | 0 | 2 | 2 | 4 |
| evaluation | modulation | 2 | 0 | 0 | 0 | 0 | 2 | 2 | 4 |
| evaluation | secondary | 2 | 0 | 0 | 0 | 0 | 2 | 2 | 4 |

Every candidate solver status was OPTIMAL, with one worker and a 30-second solver budget. The development artifacts have 4 distinct serialized musical-content digests, the held-out artifacts 12, and the full set 16; this check uses realized music, not seed-bearing request hashes. Keys/modes, lengths, feature minima and both profiles are fixed in the manifest. Base diatonic pieces cover major and minor and 1/2 bars; chromatic/contextual strata here cover C/G major and 2 bars. Do not generalize chromatic findings to minor keys or longer scores.

| Split | Candidate rows | Controls | Planned attacks | Applicable attacks | Inapplicable | Generation-failed attack slots |
| --- | --- | --- | --- | --- | --- | --- |
| development | 4 | 8 | 32 | 32 | 0 | 0 |
| evaluation | 12 | 24 | 456 | 332 | 124 | 0 |
| Total | 16 | 32 | 488 | 364 | 124 | 0 |

The deterministic raw file contains exactly 536 rows: 16 attempts + 32 controls + 488 attack slots. All 32 controls are accepted; there are no hidden exclusions, failed-generation slots, unexpected outcomes or shortfalls. An APPLIED mutation is checked for a changed protected artifact value or MIDI projection before invoking the certifier. Case IDs include fixture, render profile and mutation; cluster IDs retain paired profiles and related mutations together.

## Fault results

| Split | Family | Tier | Planned | Applicable | REJECT | BLOCKED | ACCEPT | CRASH | N/A | Harness errors | Generation failed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| development | delivery | direct | 8 | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| development | integrity-request | repaired-digest | 8 | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| development | realized-music | repaired-digest | 8 | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| development | wire | wire | 8 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 0 |
| evaluation | delivery | direct | 168 | 112 | 112 | 0 | 0 | 0 | 56 | 0 | 0 |
| evaluation | harmonic-claims | repaired-digest | 96 | 48 | 48 | 0 | 0 | 0 | 48 | 0 | 0 |
| evaluation | integrity-request | coordinated | 24 | 24 | 24 | 0 | 0 | 0 | 0 | 0 | 0 |
| evaluation | integrity-request | repaired-digest | 72 | 72 | 72 | 0 | 0 | 0 | 0 | 0 | 0 |
| evaluation | realized-music | repaired-digest | 48 | 28 | 28 | 0 | 0 | 0 | 20 | 0 | 0 |
| evaluation | wire | wire | 48 | 48 | 0 | 48 | 0 | 0 | 0 | 0 | 0 |

The held-out denominator includes wire types/root shape, out-of-range bass, an ineligible initial tie, missing actual tonicization targets, swapped actual modal sources, stale persistent contexts, forged display names, rule/digest/objective claims, a coordinated embedded-seed change, missing/duplicate tracks, wrong key/tick division, and eligible melody onset/rest/tie projection faults. The manifest fixes each obligation and witness predicate. Changing the embedded seed never changes the externally supplied request. Repaired-digest mutations repair only the content digest, so their stale provenance may provide an overlapping integrity signal.

### Held-out results by stratum

| Stratum | Planned | Applicable | REJECT | BLOCKED | N/A | ACCEPT | CRASH | Harness errors |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| applied | 76 | 54 | 46 | 8 | 22 | 0 | 0 | 0 |
| base | 76 | 50 | 42 | 8 | 26 | 0 | 0 | 0 |
| interaction-rhythm | 76 | 66 | 58 | 8 | 10 | 0 | 0 | 0 |
| mixture | 76 | 54 | 46 | 8 | 22 | 0 | 0 | 0 |
| modulation | 76 | 54 | 46 | 8 | 22 | 0 | 0 | 0 |
| secondary | 76 | 54 | 46 | 8 | 22 | 0 | 0 | 0 |

Inapplicability is eligibility-based, not outcome-selected: the corpus has only two rhythm-interaction held-out fixtures, two modulation fixtures, and a subset with realized target-bearing or borrowed harmony. Melody events are certified only under melody-plus-satb; rest/tie mutations also require a real rest/tie witness. Every unavailable slot retains its explicit reason in raw data.

## Assurance signals

| Split | Omitted signal | Applicable attacks | Detected by remaining signals | Lost/undetected | Unique catches |
| --- | --- | --- | --- | --- | --- |
| development | wire_shape | 32 | 24 | 8 | 8 |
| development | semantic_rules | 32 | 32 | 0 | 0 |
| development | integrity_request | 32 | 24 | 8 | 8 |
| development | delivery_parseback | 32 | 24 | 8 | 8 |
| evaluation | wire_shape | 332 | 284 | 48 | 48 |
| evaluation | semantic_rules | 332 | 332 | 0 | 0 |
| evaluation | integrity_request | 332 | 212 | 120 | 120 |
| evaluation | delivery_parseback | 332 | 220 | 112 | 112 |

Per-case signals, issues and detected-by sets are in raw.jsonl. These are projections of one production observation, not runs with disabled certifier channels. Semantic omission loses no signal in this finite set because integrity recomputes fresh validation and other metadata, and some unchanged MIDI disagrees with mutated music. This result does not show that semantic verification is unnecessary: the integrity channel itself invokes it. Wire failure blocks downstream observations; those unobservable checks are not counted as independent detections.

## Independent-oracle agreement

| Split | Shared predicate/domain | Compared | Agreements | Disagreements | Not compared |
| --- | --- | --- | --- | --- | --- |
| development | Exact certified SMF note/context/tick-division projection | 32 | 32 | 0 | 8 |
| development | Rhythm CM017-CM019 only | 8 | 8 | 0 | 32 |
| evaluation | Exact certified SMF note/context/tick-division projection | 308 | 308 | 0 | 172 |
| evaluation | Rhythm CM017-CM019 only | 62 | 62 | 0 | 418 |

The SMF oracle uses its own standard-library parser and independently implemented SATB/melody/context projections. The rhythm oracle checks only enabled rhythm arrays and compares the CM017-CM019 failure set. No oracle above independently verifies the entire tonal contract. Exclusions are 48 wire-blocked + 124 inapplicable held-out slots for delivery; rhythm additionally excludes 246 disabled-rhythm cases. Raw records give reasons, observed values and agreement flags. Existing music21==9.9.2 comparisons remain the separate frozen EH-10 finite shared-predicate study; they are not scores for this complete certifier.

## Cluster-level uncertainty

| Split | Independent-fixture units | All applicable attacks detected | Wilson 95% illustrative interval |
| --- | --- | --- | --- |
| development | 4 | 4 | [0.510109, 1.000000] |
| evaluation | 12 | 12 | [0.757506, 1.000000] |

The primary unit is a fixture, scored successful only when every applicable fault on both profiles is rejected or wire-blocked. There are 12 held-out fixture units, not 332 independent attack samples. The JSON field fixture_family_clusters counts 138 declared fixture-by-mutation-taxonomy clusters on evaluation and 16 on development; these are descriptive nested counts, not additional independent samples. Wilson bounds illustrate finite-sample limits under independent Bernoulli fixture sampling. This purposive small corpus is not a random sample, and shared generator/feature structure further limits that interpretation. No population detection percentage is claimed.

## Cost and recorded environment

Python 3.12.14; OR-Tools 9.15.6755; music21 9.9.2; mido 1.3.3. Linux 6.18.44 x86_64, glibc 2.39, 9 visible logical CPUs; generator uses one worker. The provider exposes a generic processor name, so no physical CPU model is asserted. Monotonic process measurements are observational and have no CI thresholds.

| Stage (16 successful fixtures) | Median ms | Q1 ms | Q3 ms |
| --- | --- | --- | --- |
| generation_seconds | 2754.867 | 1183.056 | 5269.583 |
| fresh_semantic_seconds | 0.298 | 0.289 | 0.559 |
| artifact_certification_seconds | 2.620 | 2.241 | 2.868 |
| serialization_seconds | 1.478 | 1.275 | 1.600 |
| certified-satb.export_seconds | 0.723 | 0.703 | 0.790 |
| certified-satb.delivery_parseback_seconds | 0.522 | 0.500 | 0.601 |
| certified-satb.full_delivery_certification_seconds | 3.413 | 3.151 | 4.410 |
| melody-plus-satb.export_seconds | 0.660 | 0.599 | 0.696 |
| melody-plus-satb.delivery_parseback_seconds | 0.575 | 0.549 | 0.644 |
| melody-plus-satb.full_delivery_certification_seconds | 3.616 | 3.363 | 4.155 |

All-attempt generation time was 49.384 seconds for the 16 frozen slots; successful yield was 16/16. Median per-fixture artifact certification plus delivery-only parse-back divided by generation time was 0.145% for certified-satb and 0.144% for melody-plus-satb. These ratios exclude export and separately timed semantic/serialization work. Full-delivery certification is a separate atomic call that repeats artifact verification; do not add it to artifact certification when estimating one certification path.

| Split | Attempts | Total generation s | Median generation ms |
| --- | --- | --- | --- |
| development | 4 | 11.843 | 2597.627 |
| evaluation | 12 | 37.540 | 2884.052 |

VmRSS samples ranged from 100276 to 223752 KiB. These are cumulative process-local samples following each fixture, not isolated per-fixture or peak memory measurements. Stage samples and original solver wall times survive in observations.json; normalized archived artifacts set only the observational solver wall_time_seconds to zero.

## Recorded counterexamples

1. `eval-base-1.certified-satb.bass-register` changed bass beat 0 from MIDI 47 to 35 while retaining the superficial `validation.valid=true` claim and repairing the artifact-content hash. Fresh reconstruction first rejected CM003 (bass below the fixed range), also found CM013, and produced additional integrity and delivery mismatches. Raw detected-by is semantic_rules + integrity_request + delivery_parseback.

2. `eval-base-1.certified-satb.missing-track` removed the Tenor MIDI track while leaving the accepted artifact digest unchanged. Wire, semantics and integrity passed; delivery parse-back rejected the missing track and four missing tenor note events. Only delivery_parseback detected this case. The independent SMF oracle agreed.

## Development diagnostics and deviations

A development-only diagnostic pilot at implementation commit `9530433` used the same four predeclared development requests, producing 4/4 pieces, 8/8 accepted controls and 32/32 rejected/blocked faults. Its complete candidates, raw data, summary and timings are preserved under development_pilot/. After code review, commit `975b284` separated research-oracle exceptions from production crashes, added replay dependency checks, and strengthened protocol-document pinning. No held-out fault outcome informed those repairs. No mutation definition, witness rule, spec, seed or expected outcome changed.

The fixed final study then ran all 16 planned slots under the final implementation. Thus 20 generation executions occurred operationally (4 diagnostic + 16 final); the extra development pilot is disclosed and is not 4 additional independent fixtures. It contributes neither primary detection nor yield denominators and does not replace a failed candidate. There was no held-out-driven correction, replacement, exclusion or protocol-scope change. To replay the diagnostic implementation, use its attested commit; the final evaluator intentionally rejects its different source hashes.

## Reproduction and validation

Use a full Git checkout: preregistration is checked against its historical commit, so shallow single-commit checkouts are insufficient. Install in an isolated Python 3.11-3.13 environment:

```bash
git fetch --no-tags research/history/multifixture_assurance_v1.bundle refs/heads/research/multifixture-assurance-v1:refs/assurance/multifixture-assurance-v1-original
python -m pip install -e ".[dev]"
python -m pip install mido==1.3.3
python -m research.multifixture_assurance --check
python -m research.validate_release_assurance
```

The first replay rechecks fixed generator-produced candidates and both delivered MIDI profiles, reapplies all predeclared faults, enforces exact IDs/counts/no-op guards, and byte-compares deterministic raw and derived summary output. It requires pinned dependencies and identical production/oracle/evaluator source hashes. It reuses the attested generation environment metadata in deterministic rows; the active Python interpreter may be 3.11, 3.12 or 3.13. CI runs this replay on all three versions after the unchanged release-assurance gate.

For fresh generation and recorded-hardware performance, use a clean committed checkout and a new directory outside the checkout:

```bash
python -m research.multifixture_assurance --generate --directory /tmp/multifixture-assurance-new-run
```

This executes all fixed candidate requests once, then every applicable fault, recording new times, status and composition digests. Compare candidates.json and outcome/summary rows with the archived study; do not expect timing bytes to match. One worker plus a wall-clock limit does not guarantee identical timeout decisions or FEASIBLE incumbents on different hardware. Fresh drift is a result to disclose, not permission to overwrite archived evidence.

The raw summary is directly derived and checked in tests. Candidate slots retain UNKNOWN versus INFEASIBLE, although neither occurred in this run. Tests also inject rejected denominator changes, split leakage, duplicate rows, checker crashes, oracle harness exceptions and unexpected attack acceptance. A finding causes the new replay to fail without deleting the underlying evidence.

## Manuscript-ready bounded results paragraph

We evaluated request-bound artifact and MIDI certification on a preregistered purposive corpus of 16 generator-produced tonal SATB compositions: four development pieces and twelve held-out pieces across six strata. All sixteen predeclared one-worker, 30-second candidate attempts returned OPTIMAL and passed both certified render-profile controls (32/32). Of 456 held-out fault slots, 332 satisfied predeclared witness eligibility; the remaining 124 were retained as inapplicable. Certification rejected 284 applicable faults and blocked 48 malformed wire cases, with no unexpected acceptance, crash or harness error. Separately implemented finite-domain oracles agreed on 308 held-out MIDI-projection comparisons and 62 enabled-rhythm comparisons. Every applicable fault was detected in each of the twelve held-out fixture clusters; the illustrative fixture-level Wilson 95% interval was [0.757506, 1.000000] under an independence assumption that does not establish population representativeness. Leave-one-signal-out projections showed overlap with semantic reconstruction inside integrity checking, so channel results are observational rather than causal. Recorded median generation was 2.755 seconds, artifact certification 2.620 milliseconds, and delivery-only parse-back 0.522/0.575 milliseconds for the two profiles. Results support detection of these specified faults under the versioned finite contract and environment; they establish neither universal musical soundness nor aesthetic quality, comparative superiority, global compiler/checker equivalence or authenticated origin.

See [the contribution preflight](MULTIFIXTURE_CONTRIBUTION_PREFLIGHT.md) for inspected prior work and the unresolved Pisters full-text comparison. Completion of this evaluation is not a manuscript novelty or submission-readiness verdict.

## GitHub transport of original history

The authenticated GitHub connector cannot preserve local commit IDs through its
commit-creation API. The published checkout therefore includes a verified Git
bundle of the original study history and imports its objects before replay. This
preserves the original protocol/evidence references and evaluator source bytes;
no study outcome or mutation definition changed. See
[the history transport record](../research/history/README.md) for the bundle hash
and audit-ref command. The published transport commit is distinct from the
original attested generation/evidence commits and does not establish externally
time-stamped preregistration.
