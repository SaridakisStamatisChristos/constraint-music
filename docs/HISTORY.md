# Project history

This repository is a clean revival of a recovered `constraint-music-generator-v1.1.0` package created in 2026. The historical implementation already contained a real OR-Tools CP-SAT model, deterministic seeded generation, major/harmonic-minor theory, configurable progression graphs, MIDI export, JSON output, tests, and CI.

The v2 branch preserves those useful mechanics while tightening the trust boundary. The most important recovered discrepancy was that three solver hard rules were not independently re-checked after solving: melodic tritone avoidance, bass tritone avoidance, and contrary stepwise recovery after large melodic leaps. Those are now first-class contract rules and verifier checks.
