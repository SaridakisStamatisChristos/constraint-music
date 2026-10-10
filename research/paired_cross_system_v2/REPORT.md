# Fair paired cross-system study v2

The primary outcome is a fully conforming common-adapted MIDI in both scheduled runs.
The denominator is 128 feasible requests, not 256 run rows. Four unsupported requests
are retained separately. All raw outputs and nonoutputs are replayable.

| Engine | Adapted pass in both runs | Native observed pass in both runs |
|---|---:|---:|
| constraint-music | 45/128 | 45/128 |
| music21 | 113/128 | 113/128 |
| diatony | 51/128 | Full native conformance unobservable |

Native and adapted delivery are separate profiles. Diatony's native anonymous
four-quarter writer cannot establish the requested voiced quarter-grid/context contract.
Its adapted output uses the same renderer as both competitors, with an explicit
native chord-index to quarter mapping and unchanged pitches/voices.

| CM versus | Both pass | CM only | Other only | Neither | Difference | Conservative simultaneous CI | Exact p | Bonferroni p |
|---|---:|---:|---:|---:|---:|---|---:|---:|
| music21 | 40 | 5 | 73 | 10 | -53.12% | [-67.03%, -35.19%] | 1.49665e-16 | 2.99329e-16 |
| diatony | 26 | 19 | 25 | 58 | -4.69% | [-21.72%, +12.70%] | 0.451381 | 0.902762 |

**Overall superiority: NOT ESTABLISHED.** The frozen gate requires both lower
bounds above +10 percentage points and both exact p-values below .025, with no
unresolved harness or inspection errors. Equal rates do not prove equivalence.

The paired intervals subtract simultaneous Clopper-Pearson bounds for the two
discordant-cell probabilities; each comparison has at least 97.5% coverage, giving
at least 95% simultaneous coverage across the two comparisons. They are conservative.

| Engine | Output attempts | No result/native limit | Timeout | Harness error | Blocked | Unsupported slots |
|---|---:|---:|---:|---:|---:|---:|
| constraint-music | 90 | 166 | 0 | 0 | 0 | 8 |
| music21 | 226 | 30 | 0 | 0 | 0 | 8 |
| diatony | 102 | 154 | 0 | 0 | 0 | 8 |

No-result/native-limit includes native exhaustion or a native limit without an
infeasibility certificate. Every primary input nevertheless has a shared-contract
feasibility witness. Extra native musical rules can restrict the compared configuration.

| Engine | Worker wall seconds: min / median / max | Peak process RSS KiB: min / median / max |
|---|---|---|
| constraint-music | 0.3835 / 0.4435 / 0.6301 | 103028 / 109318 / 113608 |
| music21 | 0.6084 / 0.7758 / 1.1170 | 118052 / 119610 / 122972 |
| diatony | 0.3508 / 0.4105 / 10.6916 | 82628 / 84094 / 87812 |

Sample composition: lengths {12: 66, 8: 62}; keys {'D': 17, 'F': 23, 'A': 13, 'Eb': 15, 'Bb': 13, 'G': 19, 'E': 16, 'C': 12}; 128 with inversions;
99 with dominant sevenths; 87 with soprano anchors;
89 infeasible candidates rejected by the reference sampler;
0 exact duplicate IID draws retained.

Population scope: the declared feasible grammar, conditioned pinned engines, common
renderer and budgets. Templates are shared with development; heldout requests use
an independent seed and were generated only after the committed source/receipt freeze.
The repository freeze is not external preregistration. Repeated workers are not
independent replication. Register bias from lexicographic soprano witness anchors
and different extra native rules limit generalization. Timing is descriptive; RSS
covers successful outputs and is not summed process-tree memory. No aesthetics claim.

The controlled v1 Eb replay proves an adapter spelling error, not a music21 musical
failure. V1 stays frozen; its 12/12 versus 11/12 is not superiority evidence.

Every request-level outcome is in `summary.json`; all attempt-level statuses, native
scores, logs and delivered bytes are in `heldout/attempts.json` and `heldout/evidence.zip`.
