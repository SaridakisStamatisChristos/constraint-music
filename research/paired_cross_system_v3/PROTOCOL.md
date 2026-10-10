# Request-bound SATB: prospective paired study v3

## Motivation and engineering boundary

The archived v2 corpus is development evidence for this change, never a new
holdout. Its 166 CM nonoutputs were all proven INFEASIBLE under the legacy
composition model. That model also requires root doubling, no outer-voice
sevenths, no melodic/bass tritone leaps and contrary recovery after large melody
leaps. These are stronger obligations than the benchmark request, not CP-SAT
timeouts or evidence that the shared requests are infeasible.

The opt-in `constraint_music.harmonization` API defines a separate request-bound
contract and compiles exactly its obligations. It does not change or relabel
legacy composition certificates. Native score and MIDI checks reconstruct this
new contract independently. No reference witness enters any engine worker.

## Fixed sampling and outcomes

Use the unchanged v2 conditional feasible grammar: four public templates,
optional I-IV-V-I prefix, eight major keys, 8/12 quarter chords, root/first/second
inversions, complete triads/dominant sevenths, fixed bass, 0/1/2 soprano anchors.
The reference sampler certifies feasibility without conditioning on engine
success. Development seed is 20261012 with 8 requests; heldout seed is 20261013
with 128 requests. All rejection counts, duplicate draws and witnesses remain.
The heldout sampling algorithm and seed are committed before heldout generation.
Templates are familiar; requests are fresh, not unseen musical families. Anchor
register bias from the lexicographic reference witness is unchanged and explicit.

The primary endpoint is delivered common-adapted MIDI satisfying every stated
obligation in **both** fresh runs (seeds 7/19). The denominator is 128 requests,
never 256 independent runs. Native export is a separate column. Four unsupported
requests are outside the primary denominator. No result, timeout, rejected score,
blocked inspection or harness error counts as success; unresolved errors block
positive claims. There are four configurations, 1024 primary worker attempts and
32 unsupported admission slots. No outcome-based reruns, exclusions or repair.

## Obligations and engines

Use v2's unchanged independent event oracle and finite-path checker, ranges
S60..84/A55..74/T48..67/B48..59, strict ordering, upper spacing <=12, complete
chords and requested inversion, exact fixed bass/soprano, no same-direction
parallel perfect fifths/octaves in any pair, every V-I leading tone rising one
semitone, every chordal seventh descending one or two semitones. Minor, rests,
ties, third inversions and other seventh qualities remain unsupported here.

1. `constraint-music`: the new native request-bound API, first CP-SAT solution,
   one worker, no objective, no extra musical restrictions; native atomic MIDI
   export independently parses back the exact score, voices, timing and context.
2. `legacy-constraint-music`: unmodified v2 conditioned composition adapter,
   preserving its stronger style rules. This is the prespecified paired control
   for the engineering improvement, not a different upstream product.
3. `music21`: unmodified v2 corrected spelling and native possibility/DAG
   configuration, including complete-chord ordinary seventh handling.
4. `diatony`: the exact v2 pinned native binary and capture configuration.

Every engine receives the same request; the common renderer only serializes
native pitches/voices and declared times/context. No generator imports the
reference solver or uses its witness. Fresh workers have the same 30-second wall
cap; CP-SAT/Gecode also have 20-second search caps; one search thread and numerical
thread caps. Engine order rotates across **four**, not three, configurations.
Timing is descriptive, not a speed superiority endpoint. Extra comparator native
rules remain disclosed: completion differences are configuration-specific and
cannot establish general musical or aesthetic superiority. Native Diatony's
anonymous four-quarter/context-less output remains UNOBSERVABLE; adaptation maps
chord indices to quarters and retains pitches/voices and original native bytes.

## Prespecified paired inference

Three comparisons: new CM versus legacy CM, music21 and Diatony. Use exact
two-sided McNemar tests, Bonferroni p-values multiplied by 3, alpha .05/3 per
comparison. Report four paired cells, signed risk difference and conservative
paired intervals subtracting Clopper-Pearson bounds for discordant probabilities.
At least 98.33% coverage per comparison gives at least 95% simultaneous coverage
across all three. The practical margin is unchanged at +10 percentage points.

Declare practical improvement over legacy CM only if its lower bound exceeds
.10 and p < .05/3, with no unresolved harness/block errors. All-comparison
practical superiority additionally requires these conditions against both
external configurations. Report the gate result even if negative. No general
superiority, listening quality, equivalence, universal completeness, independent
replication, or external preregistration claim follows from this study.

## Evidence and freeze

Commit development-validated source, create and commit the receipt before
heldout generation. Hash every v3 source/protocol/manifest, all recursive native
CM sources, imported v1/v2 adapter/oracle/rendering code, dependency versions and
the pinned binary. Preserve native inputs/scores/MIDI, common-adapted bytes,
events, logs, process status, timing and hashes for every slot. Replay complete
membership, fixed sampling/witnesses, trusted request binding, native score
reconstruction, both independent semantic formulations and separate SMF/mido
parsers. Current working source and source-commit objects must match the receipt.

Permit at most eight floating-point ULPs only at confidence interval bounds for
cross-Python portability; all counts, outcomes, p-values, fields and report text
must replay exactly. Original v1/v2 data, frozen code and verdicts are preserved.
