# Multi-composition assurance protocol v1

Corpus: `multifixture-assurance-v1`. Preregistration is the first commit adding
this document and `research/configs/multifixture_assurance_v1.json`; its commit ID
and file SHA-256 are stored separately in the evidence. Neither candidate
fixtures nor development or held-out faults were executed before that commit.

## Scope and fixed design

RQ1 is conditional rejection of independently justified faults on generator-produced,
strictly accepted SATB pieces. RQ2 is observational overlap of wire, semantic,
integrity/request and delivery signals. RQ3 is generation yield and certification
cost for the full candidate matrix. No population, musical aesthetics, universal
soundness, origin authentication, equivalence or comparative superiority claim.

The manifest fixes 4 development and 12 evaluation attempts, each exported under
both certified profiles. Base pieces use 1 and 2 bars and major/minor keys;
chromatic/contextual pieces use 2 bars in C/G major. Strata are base, applied
sevenths, secondary leading-tone sevenths, mixture, persistent modulation, and
mixture + secondary harmony + rhythm with required rests/ties. Requests include
all normalized GenerationSpec fields, seed, 30-second solver limit, one worker,
and schema 2.13. These are attempted cells, not asserted feasible cells.

Development/evaluation fixture IDs, request digests, seeds and mutation clusters
are disjoint. The manifest's fault definitions fix eligibility, invalid obligation,
tier and expected outcome without querying the checker. Each eligible artifact
fault changes one value except the explicitly coordinated embedded-seed case.
Repaired-digest faults update only artifact-content SHA-256. Embedded-seed changes
only the serialized seed and coordinates embedded metadata; the independently
supplied manifest request remains fixed. Witnesses are chosen by the first
eligible array index/event, never by observed rejection. MIDI key chooses C
unless already C, then G. Rest/tie cases require an actual rhythm witness and
melody-plus-satb. There are no production certification bypass switches.

## Outcomes and denominators

One generation attempt per slot, no replacements or early stopping. Retain raw
solver status and elapsed cost; UNKNOWN remains distinct from INFEASIBLE.
All planned controls and mutation slots survive failed generation. Failure to
strictly accept a control prevents attacks on it and remains a reported finding.
APPLIED requires a non-no-op witness and independently justified invalidity;
NOT_APPLICABLE, GENERATION_FAILED and HARNESS_ERROR remain explicit. Checker
outcomes are ACCEPT, REJECT, BLOCKED or CRASH. Exceptions are never detections.
Unexpected acceptance stays invalid pending review, never relabeled automatically.

Report counts by split/stratum/family/tier before percentages. Primary uncertainty
uses fixtures with applicable attacks as clusters, scoring a cluster successful
only if every applicable attack is rejected or wire-blocked. Show Wilson 95%
intervals and cluster counts. Their Bernoulli interpretation assumes independent
fixtures; this small purposive fixed matrix does not justify population inference.
Do not treat related mutation rows as independent. Report overlap sets and each
single-channel omission as observational projections, not disabled production runs.

Independent standard-library MIDI oracle compares exact event/context projection
within the SMF domain of certified exports, including rests/ties and modulation.
Independent rhythm oracle compares only CM017–CM019 decisions on eligible arrays.
Existing music21 9.9.2 EH-10 shared-predicate results remain separate and unchanged;
it is not a complete comparator for artifact or delivery assurance.

## Cost, determinism and correction

Use monotonic stage times for generation, serialization, fresh semantics, strict
artifact check, export and delivery-only parse-back; also record full delivery
certification. Linux VmRSS is a process-local sample, not a peak allocation claim.
Report successful-fixture medians/IQR and all-attempt generation time/yield.

Store observational environment/timing records separately from deterministic
outcomes. Normalize solver wall_time_seconds to zero in archived artifact payloads,
retaining the original solver time in observations. Archive accepted candidate
artifacts and MIDI bytes. Deterministic replay rechecks these fixed generator-produced
fixtures and repeats all mutations; a separate fresh-generation command measures
yield/cost and compares regenerated composition identities. A one-worker solver
with a wall-clock limit does not guarantee the same timeout or FEASIBLE incumbent
on different hardware; disclose drift instead of replacing archived fixtures.

No held-out repair or mutation change is permitted silently. Findings, failures
and shortfalls narrow the claim. Changes influenced by held-out faults require a
protocol deviation and a new version with fresh held-out IDs/seeds/clusters. A
production defect is fixed separately; frozen historical evidence stays intact.
