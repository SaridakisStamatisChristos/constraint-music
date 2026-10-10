# Request-bound harmonization: fresh paired study v3

The primary outcome is a fully conforming common-adapted MIDI in both scheduled runs.
The denominator is 128 feasible requests, not 256 run rows. Four unsupported requests
are retained separately. All raw outputs and nonoutputs are replayable.

| Engine | Adapted pass in both runs | Native observed pass in both runs |
|---|---:|---:|
| constraint-music | 128/128 | 128/128 |
| legacy-constraint-music | 53/128 | 53/128 |
| music21 | 111/128 | 111/128 |
| diatony | 38/128 | Full native conformance unobservable |

Native and adapted delivery are separate profiles. Diatony's native anonymous
four-quarter writer cannot establish the requested voiced quarter-grid/context contract.
Its adapted output uses the same renderer as all competitors, with an explicit
native chord-index to quarter mapping and unchanged pitches/voices.

| CM versus | Both pass | CM only | Other only | Neither | Difference | Conservative simultaneous CI | Exact p | Bonferroni p |
|---|---:|---:|---:|---:|---:|---|---:|---:|
| legacy-constraint-music | 53 | 75 | 0 | 0 | +58.59% | [+42.37%, +69.94%] | 5.29396e-23 | 1.58819e-22 |
| music21 | 111 | 17 | 0 | 0 | +13.28% | [+2.34%, +23.01%] | 1.52588e-05 | 4.57764e-05 |
| diatony | 38 | 90 | 0 | 0 | +70.31% | [+54.43%, +80.38%] | 1.61559e-27 | 4.84676e-27 |

**Practical improvement over legacy CM: True.**


**All-comparison practical superiority: NOT ESTABLISHED.**
The frozen gate requires all three lower
bounds above +10 percentage points and all three exact p-values below .05/3, with no
unresolved harness or inspection errors. Equal rates do not prove equivalence.

The paired intervals subtract simultaneous Clopper-Pearson bounds for the two
discordant-cell probabilities; each comparison has at least 98.33% coverage, giving
at least 95% simultaneous coverage across the three comparisons. They are conservative.

| Engine | Output attempts | No result/native limit | Timeout | Harness error | Blocked | Unsupported slots |
|---|---:|---:|---:|---:|---:|---:|
| constraint-music | 256 | 0 | 0 | 0 | 0 | 8 |
| legacy-constraint-music | 106 | 150 | 0 | 0 | 0 | 8 |
| music21 | 222 | 34 | 0 | 0 | 0 | 8 |
| diatony | 76 | 180 | 0 | 0 | 0 | 8 |

No-result/native-limit includes native exhaustion or a native limit without an
infeasibility certificate. Every primary input nevertheless has a shared-contract
feasibility witness. Extra native musical rules can restrict the compared configuration.

| Engine | Worker wall seconds: min / median / max | Peak process RSS KiB: min / median / max |
|---|---|---|
| constraint-music | 0.4146 / 0.5229 / 0.7712 | 94528 / 97216 / 99312 |
| legacy-constraint-music | 0.3851 / 0.4595 / 0.6170 | 102456 / 105376 / 112808 |
| music21 | 0.6299 / 0.7763 / 1.0220 | 117228 / 119736 / 120664 |
| diatony | 0.3581 / 0.4153 / 4.1165 | 87384 / 90264 / 94424 |

Sample composition: lengths {8: 64, 12: 64}; keys {'F': 23, 'G': 14, 'A': 15, 'C': 15, 'Eb': 17, 'E': 10, 'D': 21, 'Bb': 13}; 128 with inversions;
90 with dominant sevenths; 88 with soprano anchors;
118 infeasible candidates rejected by the reference sampler;
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

This is an opt-in request-bound API, not a change to the legacy style contract.
Its score checker and native MIDI checker are independent of the CP compiler.
Comparators keep their frozen v2 configurations and additional native rules;
completion differences do not establish general musical or aesthetic superiority.
