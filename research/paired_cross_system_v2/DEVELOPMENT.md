# Pre-freeze development and controlled adapter diagnosis

The frozen v1 E♭ counterexample remains unchanged. `diagnostic/evidence.zip`
retains a controlled replay with the original integer-derived bass spelling and
one with explicit diatonic spelling. Only spelling changes in musical input:
MIDI 56 remains MIDI 56, G♯3 becomes A♭3. The legacy event sequence reproduces
v1's native wrong IV chord, pitch classes {8,10,2}; the corrected version has
the requested {8,0,3} and passes all v1 semantic and delivered-byte obligations.
This is an adapter error. It cannot count as evidence against music21.

The first v2 development run is preserved in `development_v0.zip`, including
source and all 72 planned slots. Its seventh-chord music21 workers encountered
an uninitialized native consecutive-rule cache on the special-resolution path.
Inspection also showed that this shortcut forces an incomplete V7–I tonic.
Before freezing, configure ordinary native movement search for dominant sevenths;
the shared complete-chord and resolution rules still apply before search.
The revised development run keeps the same eight sampled requests and budgets.
No heldout request was generated during development.

The engines retain different extra native musical constraints. Feasibility of
every admitted request is independently certified; a native engine can still
return no result under its own additional rules. Such outcomes are measured
completion limits of the specified conditioned configurations. This is not a
universal ranking of musical quality or systems.
