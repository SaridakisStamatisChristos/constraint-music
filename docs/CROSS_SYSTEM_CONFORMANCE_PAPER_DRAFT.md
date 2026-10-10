# Separating request, score, and delivered-file conformance in symbolic music generation

Author-review manuscript draft, 10 October 2026. This draft integrates the separately retainedly declared studies; it is not a submission or a claim of externally timestamped preregistration.

## Abstract

A symbolic-music generator can return internally consistent events while missing the requested task, or return a conforming score whose exported file loses information. We evaluate these boundaries separately using a trusted external request, reconstruction of returned score facts, and independent parsing of delivered MIDI. A first bounded Constraint Music study retains 16 fixtures, 32 accepted controls and 456 held-out fault slots. A second, prospectively frozen paired study evaluates Constraint Music, music21 and Diatony on 12 shared SATB requests in six new major keys and two held-out harmonic families, plus four unsupported request cases. All 36 primary attempts returned outputs; delivered end-to-end passes were 12/12, 11/12 and 12/12 respectively, with Diatony's latter endpoint explicitly adapted rather than native. One music21 adapter/native-path output failed the requested triad content while preserving its delivered notes exactly. Among 432 planned injected fault slots, 420 were applicable: 385 were rejected and 35 blocked, with zero accepted faults and 12 retained inapplicable slots. Eight hand-positive and 35 applicable time-division controls passed. These results support the declared finite conformance protocol and demonstrate the value of separate boundaries, without implying population reliability, musical quality, optimization quality or system superiority.

The subsequent controlled replay identifies the music21 discrepancy as an adapter spelling error. A separate freshly frozen study uses 128 feasible requests with inversions, dominant sevenths and soprano anchors. Reproducible common-adapted passes are Constraint Music 45/128, music21 113/128 and Diatony 51/128. Paired inference favors music21 on that declared completion outcome; the Diatony comparison is inconclusive. Constraint Music superiority is not established, and the conformance contribution remains separate from comparative yield.

A subsequent opt-in request-bound harmonizer is developed on the archived cases
and evaluated on 128 fresh, prospectively frozen requests with an unchanged
shared contract. Reproducible native/common-adapted passes are 128/128, compared
with 53/128 for the legacy CM configuration, 111/128 for music21 and 38/128 for
adapted Diatony. Against music21 the new API wins on 17 requests and loses on none:
the corrected exact paired p-value is 0.0000458 and the conservative simultaneous
interval for the completion difference is [+2.34, +23.01] percentage points.
This supports higher completion on the declared grammar and configurations. The
separate prespecified +10-point minimum practical margin is not established
against music21. All earlier observations and verdicts are retained separately.

## 1. Introduction

The controlled spelling experiment and fresh paired Study C are reported in §6.5; the subsequent request-bound engineering improvement and separately frozen Study D are in §6.6. They confirm that the v1 music21 discrepancy is an adapter error and that Constraint Music superiority is not established on the harder measured outcome. Frozen v1 observations remain intact; the new comparison is a separate study.

Users can request a specific key, harmony, duration, voicing and delivery context. Meeting that request is a relation between the user's independently retained specification and the produced score. Agreement among fields inside a result is a weaker relation. Export introduces another boundary: a correct score can be delivered with altered pitch, duration, voice assignment or context. An evaluation that observes only a generator's internal validation flag cannot establish these relations.

We ask where an explicitly requested symbolic-music task fails: generation, request binding, semantic artifact or delivered MIDI. The contribution is an implemented conformance protocol that keeps these boundaries distinct, prospective cross-engine requests, independent semantic/SMF reconstruction and complete evidence accounting. The study is deliberately limited to a common SATB subset; a successful benchmark outcome is not a guarantee for arbitrary music.

The first study tests request-bound assurance within Constraint Music. The second adds two independent external generation engines under a new contract and corpus. They are presented as one paper with separate methods and denominators. Their results are neither pooled nor treated as independent draws from one population.

## 2. Related work and contribution boundary

Reconstruction and checking of tonal exercises already appear in Pisters' 2007 thesis; its full-text comparison is retained in [the contribution preflight](MULTIFIXTURE_CONTRIBUTION_PREFLIGHT.md). Constraint-based SATB modeling, composer control and MIDI export are established by [Diatony](https://www.ijcai.org/proceedings/2024/858). [Harmoniser](https://www.ijcai.org/proceedings/2025/1130) builds broader harmonic planning and modulation on the voicing layer. We use one pinned Diatony implementation, rather than counting project layers as independent engines.

[Dai et al.](https://arxiv.org/html/2607.11334v2) already use independent retained-event checks, serialization consistency and selective release in twelve-tone generation. [MusicConstraintBench/MusicRLVR](https://arxiv.org/html/2609.23665v2) already evaluates jointly requested, programmatically checked musical properties with malformed-score gating, controls, mutations and generalization splits in monophonic ABC. Harmony realization and chorale export are existing [music21](https://music21.org/music21docs/moduleReference/moduleFiguredBassRealizer.html) capabilities.

We therefore do not claim that tonal verification, joint constraint benchmarking, final checking, verifier-guided generation or MIDI export is new. The candidate distinction is the concrete conjunction of a separately fixed request, reconstructed polyphonic score facts, exact independently parsed delivered-SMF relations, and prospective complete-slot evidence across independent engines. The [updated claim matrix](CROSS_SYSTEM_CONTRIBUTION_UPDATE.md) documents overlap and limits. This focused review does not establish global priority, and cross-paper success percentages are not comparable across different musical contracts.

## 3. Assurance model

Let R be the independently fixed request, S the returned native score, A its normalized artifact, and M the actual delivered SMF bytes. Acceptance requires request admission and binding, equality of reconstructed S and A events, integrity admission, fresh semantic evaluation against R, and exact parsed MIDI projection against those events and R's context. A stored hash alone checks integrity; it does not establish harmony or request satisfaction.

Semantic reconstruction derives pitch classes, chord membership, voice order, coverage, harmonic transitions and cadence movement from events. Delivery reconstruction derives actual note pitch, onset and duration plus declared track/channel identity, key, meter and tempo. Parser disagreement or unavailable required evidence prevents acceptance. Unobservable native identity/context is recorded explicitly; it is not presumed correct.

The cumulative transition funnel counts output, request-bound output, semantic artifact and full delivered result from the same fixed attempt denominator. Independent stage outcomes additionally measure faithful delivery of a semantically wrong score. This distinction explains why an exact export can pass its own boundary while the whole request fails.

## 4. Study A: bounded request-bound assurance

The merged PR37 study retains its original frozen protocol, native observations, oracles, hashes and denominators. Its 16 fixtures comprise four development and twelve held-out requests. Its 32 controls passed. Of 456 held-out fault slots, 332 were applicable: 284 rejected and 48 blocked; 124 were inapplicable. These are finite observations under that study's eligibility conditions, not estimates of universal fault detection.

The executable strict API uses an externally supplied expected specification, rather than treating the embedded-spec inspection path as equivalent. Its artifact integrity and fresh semantic checks are paired with exact parsed-back MIDI projection under supported certified profiles. See [the original evaluation](MULTIFIXTURE_ASSURANCE_EVALUATION.md) and [assurance boundary](ASSURANCE_BOUNDARY.md) for its distinct contracts, partitions and claim limits. Study B does not modify or enlarge those counts.

## 5. Study B: prospective paired cross-system evaluation

### 5.1 Systems and common obligations

We pin Constraint Music core to `9de73eae948eac366e7e1a45047a970795ed76bf`, OR-Tools to 9.15.6755, music21 to 9.9.2, Diatony to `2b13446c117c02626659e819ff975fef4b5daec2`, Gecode to 6.2.0 and the secondary MIDI parser mido to 1.3.3. CP-SAT, native figured-bass realization and Gecode are independent generation implementations; two wrappers of one engine are not counted independently.

The shared request names a major key, zero-based degree sequence, 4/4 meter and tempo. Every chord occupies four quarters and must contain all three diatonic triad pitch classes with root bass. Four SATB voices continuously cover the phrase, remain noncrossing and keep stable pitches within harmonic blocks. Quarter or whole durations are allowed. Parallel octave/fifth movement in the same nonzero direction between blocks is forbidden; a leading tone on V must ascend one semitone on I. The contract does not imply every rule of tonal harmony.

Constraint Music's benchmark subclass posts degrees, root inversions, block constancy and cadence obligations before native CP-SAT search; its objective is cleared for first-feasible selection. music21 uses root bass MIDI 48+root pitch class, default native rules plus a benchmark consecutive-possibility cadence hook, and the first viable native movement-DAG path. Diatony uses a benchmark subclass posting complete triad presence and cadence obligations before first-feasible native DFS. Upstream source and core Constraint Music code are unchanged. The profiles retain additional native rules and registers, so shared-obligation conformance is comparable while internal optimization problems are not identical.

Quarter attacks from Constraint Music are retained; the other systems' whole notes are retained. They both satisfy the request's allowed durations but remain distinct delivery projections. music21 outputs native chorale MusicXML/MIDI with explicitly inserted request tempo. Diatony's original MIDI is preserved and separately evaluated; a declared benchmark renderer adds observable SATB identity and exact context to captured native events. Adapted Diatony success must not be attributed to untouched native export.

### 5.2 Split, budgets and development

Development comprises four C/G requests using I-IV-V-I or I-V-I. The primary holdout comprises twelve D/A/E/F/Bb/Eb requests using I-ii-V-I or I-vi-IV-ii-V-I. Both tonic keys and entire harmonic families differ between development and holdout. The two held-out strata have four and six chords. Tempos cycle through 90/108/132. Four additional cases explicitly request minor mode, rests, ties or a given voice; all three adapters declare these unsupported before attempting generation. Native broader capability is not inferred from adapter support.

Each attempt runs in a fresh sequential process group under the same 30-second wall cap; system order rotates by request. CP-SAT and Gecode also have 20-second native limits, while music21 has no equivalent native search clock. CP-SAT uses one worker and seed 7; numerical-library thread environments are capped at one. Costs include startup/import/export. Memory is maximum observed RSS of an individual worker/child process, not concurrent process sums. These measurements are descriptive.

The first development revision exposed native omissions/alternative cadence treatment. All original code and bytes are retained in `development_v0.zip`. Before freezing, explicit native conditioning was added without removing any shared obligation or calling the oracle to select/repair outputs. All twelve revised development attempts passed. Protocol, source, corpus, support, budgets, fault plan and analysis were committed at `167ed84`; the freeze receipt was committed at `ff15f25` before held-out collection. Original history is retained in a Git bundle. This is local prospective declaration, not externally timestamped preregistration. No adapter/oracle/protocol change followed held-out observation.

### 5.3 Oracles and evidence

Native JSON, MusicXML and text captures are independently reconstructed and compared with normalized events. Captured input mappings bind to the trusted request. One semantic implementation uses rational event coverage and scale-degree pitch classes; a separate matrix implementation uses occupancy and chord-quality interval tables. Neither uses a generator's reported validity or imports the other. Hand-positive, negative and metamorphic cases validate agreement. Disagreements block acceptance.

A handwritten SMF parser and mido independently reconstruct delivered bytes and must agree. Tracks 1–4 carry SATB; channels 0–3 apply to Constraint Music/adapted Diatony, and channel 0 on each voice track applies to music21. Key, meter and rounded microseconds-per-quarter tempo are exact at zero. Positive PPQN scaling with proportional ticks is permitted; velocity, program and track names are ignored. Repeated attacks are not coalesced. Malformed SMF is blocked, distinct from semantic rejection.

Every planned attempt retains its trusted request, actual native score/input/MIDI, adapted delivery where applicable, normalized artifact, available metrics and logs with explicit IDs and byte hashes. Unique IDs, exact planned sets, archive coverage, hashes, source reconstruction, both semantic implementations, both parsers, mutations and derived tables are replayed in CI. Unsupported/time-out/no-solution/harness/parse outcomes cannot silently disappear.

### 5.4 Faults, controls and analysis

Twelve predeclared slots per primary attempt give 432 fault slots. The faults change request key/tempo, coordinate a request/score/MIDI transpose, alter score pitch/completeness/crossing/duration with repaired hashes, or alter MIDI pitch/duration/channel/tempo/truncation. Faults are applicable only to untouched fully accepted baselines; a nonconforming baseline retains all its INAPPLICABLE slots. Each mutation must change actual data before observation.

One positive PPQN slot per primary attempt gives 36 planned slots with identical baseline eligibility. Eight hand-positive controls cover two keys, two development families and original/scaled PPQN. Report false rejection only for applicable known-valid controls. False acceptance is a PASS on an applicable injected fault; malformed-MIDI BLOCKED and semantic REJECT are reported separately.

Primary rates use twelve request clusters per system. Pair identical request identities; mutation outcomes do not become independent samples. For descriptive paired uncertainty, enumerate four ordered resamples of the two held-out harmonic-family clusters. Only two purposively selected families are available, so the resulting ranges are illustrative and are not inferential confidence intervals.

## 6. Results

### 6.1 Complete attempt accounting and transitions

All 48 held-out slots are retained: 36 primary OUTPUT and 12 UNSUPPORTED. No primary timeout, no-solution or harness-error outcome occurred in this run. Both semantic implementations agreed on all 36 primary outputs.

| System/profile | Primary planned | Output | Request bound | Semantic artifact | Full delivered | Observable native full |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Constraint Music conditioned/native export | 12 | 12 | 12 | 12 | 12 | 12 |
| music21 conditioned/native export | 12 | 12 | 12 | 11 | 11 | 11 |
| Diatony conditioned/adapted delivery | 12 | 12 | 12 | 12 | 12 | 0 |

All 36 delivered files pass the independent event/context relation. The music21 score failure therefore occurs at the semantic-artifact boundary. Diatony's twelve untouched native files have an observable correct unvoiced event relation but unobservable required voice identity/context; zero observable native full endpoints does not mean twelve demonstrated semantic failures.

### 6.2 Traceable discrepancy

`heldout.extended-submediant.Eb.music21` follows I-vi-IV-ii-V-I. Its third block, at quarter 8, contains SATB MIDI pitches 70/62/58/56, giving pitch classes {10,2,8}. The requested IV in Eb requires {8,0,3}. Both semantic implementations reject triad content/completeness while native reconstruction and delivered MIDI remain exact.

The preserved MusicXML spells the MIDI-56 bass as G-sharp. A subsequent separately retained [controlled replay](../research/paired_cross_system_v2/DEVELOPMENT.md) reproduces the frozen wrong chord with integer-derived spelling. Changing only the spelling to A-flat, while retaining bass MIDI 56, request, native rules, ranges and selection policy, yields the requested IV triad and a fully conforming delivered file. This establishes an adapter error for this case, not a defect in music21. It cannot fairly support a superiority comparison. Study B remains frozen; corrected spelling is used only in a new declared study with fresh heldout requests.

A coordinated request/score/MIDI mutation provides a separate boundary witness: internal consistency remains repaired, yet the result no longer matches the externally retained request. A truncated-MIDI witness demonstrates why admission failures must block acceptance without claiming that a particular harmony rule diagnosed them. All witness bytes and verdicts are linked by baseline IDs.

### 6.3 Faults and known-valid controls

| System | Planned faults | Applicable | REJECT | BLOCKED | INAPPLICABLE | Accepted faults |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Constraint Music | 144 | 144 | 132 | 12 | 0 | 0 |
| music21 | 144 | 132 | 121 | 11 | 12 | 0 |
| Diatony adapted delivery | 144 | 144 | 132 | 12 | 0 | 0 |
| Total | 432 | 420 | 385 | 35 | 12 | 0 |

Truncation accounts for the 35 BLOCKED outcomes; all other applicable injected faults are REJECT. Request faults fail the trusted request boundary, repaired score faults fail semantic artifact checks, and MIDI-only faults fail delivery. The one naturally rejected music21 baseline accounts for twelve inapplicable faults and one inapplicable PPQN control; it is not silently removed from primary request yield.

All eight hand controls and 35 applicable PPQN controls pass: zero observed false rejections among 43 declared valid controls. This finite count does not estimate false rejection for arbitrary valid music.

### 6.4 Pairing and descriptive costs

| Left minus right | Request pairs | Both pass | Left only | Right only | Difference | Illustrative two-family resample range |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Constraint Music minus music21 | 12 | 11 | 1 | 0 | 1/12 | 0 to 1/6 |
| Constraint Music minus adapted Diatony | 12 | 12 | 0 | 0 | 0 | 0 to 0 |
| music21 minus adapted Diatony | 12 | 11 | 0 | 1 | -1/12 | -1/6 to 0 |

The sample is too small and too selected to infer relative generator reliability. Native-rule differences, adapter conditioning and one translation discrepancy further qualify interpretation. A zero resample range is not proof of a zero population difference.

| System | Primary wall min/median/max, seconds | Output max-process RSS min/median/max, KiB |
| --- | --- | --- |
| Constraint Music | 0.467 / 0.546 / 0.632 | 101996 / 104434 / 108988 |
| music21 | 0.355 / 0.395 / 0.456 | 51768 / 52048 / 52244 |
| Diatony | 0.071 / 0.081 / 0.120 | 17536 / 17720 / 18040 |

Each cost distribution has twelve observations from this Linux runner; exact values are in the machine-derived report. Different registers, internal constraints, algorithms, note rhythms and clocks prevent a speed-superiority interpretation.

### 6.5 Study C: corrected adapter and fresh fair comparison

A new version preserves Study B while correcting bass spelling. Its source commit `6ffa3f6` and receipt commit `a1cdd15` precede heldout generation. The [protocol](../research/paired_cross_system_v2/PROTOCOL.md) predefines 128 IID draws from a finite grammar conditioned on independent reference feasibility. Requests contain 8/12 quarter-note chords, fixed bass pitches, inversions, optional dominant sevenths and zero/one/two soprano anchors. Native generators receive the same request and no reference solution. The sample has 128 requests with inversions, 99 with sevenths and 87 with soprano anchors. The grammar rejects 89 infeasible candidates and retains zero exact duplicate draws.

The primary outcome is conforming common-adapted MIDI in both scheduled runs (seeds 7/19), with native export reported separately. Every engine uses the same renderer, ranges, externally checked obligations and 30-second fresh-worker wall cap. CP-SAT/Gecode also have 20-second native caps; no observed attempt times out. Different extra native musical constraints remain explicit. music21 uses ordinary native movement search for complete seventh-chord resolutions; its default special shortcut would force an incomplete tonic. Diatony's unchanged native writer has anonymous four-quarter chords, so adapted delivery explicitly maps chord indices to the requested quarter grid without changing pitches or voices.

| Engine | Primary pass in both runs | Observable native pass in both runs |
| --- | ---: | --- |
| Constraint Music | 45/128 | 45/128 |
| music21 | 113/128 | 113/128 |
| Diatony | 51/128 | Full native contract unobservable |

All 792 slots are retained: 768 primary attempts and 24 unsupported admission slots. Every produced score and adapted MIDI passes both semantic formulations and the byte relation; lower completion rates arise from native no-result outcomes. There are no timeouts, harness errors or inspection blocks. Unsupported minor/rest/tie/third-inversion requests are outside the primary denominator, not musical failures.

CM minus music21 is −53.125 percentage points, with conservative simultaneous interval [−67.03, −35.19] points and exact two-sided McNemar p≈1.497×10⁻¹⁶. CM minus Diatony is −4.6875 points, interval [−21.72, +12.70] points, p≈0.4514. Pairing uses the request, never duplicated run rows. The intervals subtract Clopper–Pearson bounds for the two discordant-cell probabilities using a union-bound construction; 97.5% coverage per comparison gives at least 95% simultaneous coverage for both. Two exact tests use Bonferroni correction. The predefined superiority gate requires both lower bounds above +10 points and both raw p-values below .025; it fails.

music21 completes substantially more requests on this outcome and grammar. The Diatony comparison is inconclusive. Neither result is a general ranking of music systems, listening quality or unconditioned product capability. The templates are shared with development, soprano anchors inherit low-register witness bias, and native extra rules differ. The freeze is local, not external preregistration; repeated workers are not independent replication. Any outcome-informed change to CM or the comparison requires a fresh study version. The [derived report](../research/paired_cross_system_v2/REPORT.md), complete raw archives and request-level paired results preserve this negative superiority finding.

### 6.6 Study D: request-bound harmonization and prospective improvement

The negative Study C result motivated a separate opt-in native API, not a rewrite
of archived outcomes or a relaxation of legacy composition certification.
`constraint_music.harmonization` compiles exactly the common request obligations
with complete pitch-class chord tables, modular pair intervals and motion signs.
Its independent scalar score checker reconstructs the requested chord contents,
inversions, anchors, ranges, order, spacing and resolutions. Atomic native MIDI
export independently parses the exact score/voice/time/context relation before
publishing. No generator imports the finite-path reference or receives a witness.
The legacy API retains root doubling, inner-voice-only sevenths and its melodic
style obligations. Fixed-input diagnosis proves direct conflicts in 23 archived
v2 requests: 21 have forbidden fixed bass tritones and five have given soprano
sevenths (three overlap). Other failures involve coupled additional style rules;
no per-rule causal attribution is asserted for them.

The archived 128 v2 requests became development evidence; the new API delivers
conforming native and adapted MIDI in both runs for all 128. This is explicitly
development replay. A new [prospective v3 protocol](../research/paired_cross_system_v3/PROTOCOL.md)
uses development seed 20261012 and fresh heldout seed 20261013. Source commit
`3686df8` and receipt commit `5322fa9` precede heldout generation. The same conditional
feasible grammar, obligations, 20-second native/30-second worker budgets, first
native solution policy and repeat seeds 7/19 are preserved. A fourth configuration,
unmodified legacy CM, supplies the prespecified paired engineering control.
External adapters and Diatony binary are unchanged from v2. Engine order rotates
across four configurations. Three comparisons use Bonferroni correction and
at least 95% simultaneous coverage overall; the +10-point practical margin is
fixed before collection. This local freeze is not external preregistration.

| Configuration | Common-adapted pass in both runs | Observable native pass |
| --- | ---: | --- |
| CM request-bound API | 128/128 | 128/128 |
| Legacy CM composition API | 53/128 | 53/128 |
| music21 v2 configuration | 111/128 | 111/128 |
| Diatony v2 configuration | 38/128 | Full native contract unobservable |

All 1,056 slots replay: 1,024 primary attempts and 32 unsupported admission slots.
All produced scores and common-adapted files conform; the new API also delivers
128/128 exact native endpoints in both runs. There are zero timeouts, harness
errors or inspection blocks. Requests are the analysis unit, not repeated runs.
New CM has 75 additional passes and no losses versus legacy CM, 17 additional
passes and no losses versus music21, and 90 additional passes and no losses versus
Diatony. Signed differences are +58.59, +13.28 and +70.31 percentage points.
Their conservative simultaneous intervals are [+42.37, +69.94], [+2.34, +23.01]
and [+54.43, +80.38] points. Exact McNemar p-values are approximately 5.294e-23,
1.526e-5 and 1.616e-27; all three remain significant after correction.

The primary comparative finding is a statistically supported completion advantage
for the new API on the declared feasible grammar and configured endpoints. It
achieves 128/128, so further score improvement within this corpus is impossible.
The study also prespecified a stricter +10-point minimum practical margin. That
number was an investigator-chosen threshold, with no independently calibrated
musical or operational justification. The improvement over legacy CM clears it;
the all-comparison gate is **not established** because the music21 interval lower
bound is +2.34 points. We retain this frozen negative gate result rather than
changing the protocol after observing the data. The gate tests the minimum size
of the advantage, whereas the paired inference supports a positive advantage.
Neither finding ranks music systems, aesthetics, algorithms or unconditioned
products. Extra native comparator rules remain a configuration limitation.
No universal completeness or listening-quality claim is made. The new result
schema is `request-bound-satb-v1`, not legacy CM001..CM057 certification. All original
studies and negative verdicts remain unchanged. Full outcomes and bytes are in the
[derived v3 report](../research/paired_cross_system_v3/REPORT.md).

## 7. Threats to validity and release

The shared contract is a narrow major-triad intersection. Minor, rest, tie, fixed-voice and contextual chromatic tasks are unsupported, not covertly weakened or counted as generation failures. Six keys and two longer families broaden the earlier pilot but do not represent all tonal music. Oracle agreement cannot exclude shared conceptual errors, and independent parsers may share format assumptions. Native capture relies on declared pinned adapters; the evidence establishes observed relations, not authenticated origin or resistance to arbitrary malicious provenance fabrication.

Conditioning explicitly changes benchmark models before search; results characterize those profiles, not unrestricted default APIs. Diatony's adapted renderer guarantees observable information by construction, so its score-to-render byte relation is checked independently and native export remains separate. The music21 spelling discrepancy illustrates how an adapter can be part of the evaluated failure path. Natural failures are retained rather than fixed after inspection.

Faults are deterministic and correlated within accepted baselines. A zero accepted-fault count concerns those witnesses; the test set is not an adversarial completeness proof. BLOCKED outcomes prevent release but do not imply semantic fault localization. Positive controls have known constructed truth only within the supported domain. No listening study is needed for machine-checkable conformance, and none supports an aesthetic claim here.

The proprietary Constraint Music license remains unchanged. Public evidence can be inspected, but independent repository execution requires written permission. The [permission route/template](RESEARCH_REPLAY_PERMISSION_TEMPLATE.md) provides a reviewable case-by-case path; it does not issue an automatic public grant. External projects retain their licenses and no upstream code/binary is redistributed. Outside replication has not been conducted. The [replay README](../research/paired_cross_system_v1/README.md) supplies the exact archived-byte checks and a new-version generation procedure.

## 8. Conclusion

The two bounded studies provide concrete evidence for separately checking a trusted request, returned score facts and actual delivered MIDI. The paired extension retains every planned slot, a natural adapter/native-path discrepancy, explicit native unobservability and complete eligible-fault accounting. It supports the declared protocol on the sampled domain and makes its limits inspectable. Future work requires fresh held-out versions for spelling revisions and broader musical domains, explicit evaluator permissions and actual independent replication; it does not retroactively expand these results.

## References and evidence

Primary related-work links are given in section 2 and the claim matrix. Version-specific papers are Dai et al., arXiv:2607.11334v2 (14 July 2026), and Liu and Tang, arXiv:2609.23665v2 (7 October 2026). The retained full-text Pisters comparison and IJCAI papers establish the credited overlaps.

Study A: [MULTIFIXTURE_ASSURANCE_EVALUATION.md](MULTIFIXTURE_ASSURANCE_EVALUATION.md), original frozen corpus and PR37 history. Study B: [PROTOCOL.md](../research/paired_cross_system_v1/PROTOCOL.md), [manifest.json](../research/paired_cross_system_v1/manifest.json), [freeze.json](../research/paired_cross_system_v1/freeze.json), [REPORT.md](../research/paired_cross_system_v1/REPORT.md), [summary.json](../research/paired_cross_system_v1/summary.json), native/normalized byte archives and original-history bundle. The report generator recomputes tables from verified evidence rather than accepting handwritten totals.
