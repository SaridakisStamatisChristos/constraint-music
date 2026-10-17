# Research and Reproducibility

The `research/` tree contains Constraint Music's reproducible assurance, comparator, benchmark, and cross-system study material. It is intentionally separated from the product-facing documentation so measured evidence and historical study lineage are not confused with current feature descriptions.

## Principles

- Preserve raw observations, protocol versions, source/receipt provenance, and negative findings.
- Keep development and held-out data distinct where the protocol requires it.
- Do not rewrite an earlier study after a later implementation change.
- Keep native and adapted comparator endpoints distinct when they answer different questions.
- Treat finite conformance, adversarial, or performance experiments as bounded evidence.
- Retain historical identifiers when they are required to reproduce exact archived evidence.

## Main research areas

### Release and assurance evidence

Top-level research modules implement bounded conformance enumeration, adversarial corruption tests, compiler deletion experiments, assurance ablations, multi-fixture evidence, performance measurement, and the aggregate release-assurance gate.

The canonical aggregate check is:

```bash
python -m research.validate_release_assurance
```

The checked-in evidence inventory is validated by exact SHA-256 values and deterministic replay where applicable.

### Cross-system feasibility and delivery

- [`cross_system_assurance_v1/`](cross_system_assurance_v1/) retains the native-interface feasibility study.
- [`cross_system_delivery_v1/`](cross_system_delivery_v1/) retains the adapted delivery path used to separate native-interface limitations from delivery-conformance questions.

These studies are preserved as bounded precursor evidence and are not pooled into later denominators.

### Paired cross-system studies

- [`paired_cross_system_v1/`](paired_cross_system_v1/) — first prospective paired conformance study.
- [`paired_cross_system_v2/`](paired_cross_system_v2/) — fairer paired grammar with corrected bass-spelling handling and expanded obligations.
- [`paired_cross_system_v3/`](paired_cross_system_v3/) — request-bound harmonization study with fresh held-out collection after the new API was frozen.

V1, v2, and v3 answer different questions. Their protocols, configurations, and denominators remain separate.

For the current v3 archive replay:

```bash
python -m research.check_paired_v3_portable
```

The original frozen checker is also retained. CI runs it on Python versions where its historical floating-point tolerance remains exactly reproducible.

### Raw results and configuration

- [`results/`](results/) stores checked-in evidence artifacts and recorded benchmark outputs.
- [`configs/`](configs/) stores versioned manifests and experiment configurations.
- [`history/`](history/) stores Git bundles used to reconstruct frozen research branches and protocol/source histories during CI replay.

The history bundles are part of provenance, not active product branches.

## Why historical names remain here

Some research modules, manifests, reports, and tests retain identifiers such as `EH-10`, `EH-11`, `EH-12`, study version numbers, source commit IDs, or older PR references. Those labels are preserved only when changing them would obscure a frozen protocol, invalidate exact replay text, alter a claim-boundary fixture, or weaken provenance.

Product-facing files do not rely on those construction labels. Git history remains the source for ordinary implementation chronology.

## Claim boundary

The research tree supports reproducible statements about its declared finite domains. It does not, by itself, establish:

- universal musical correctness;
- aesthetic quality;
- complete historical-style authenticity;
- global solver/verifier equivalence;
- population-level adversarial robustness;
- general superiority over other music systems;
- operational latency or capacity guarantees;
- independent external replication;
- publication acceptance.

See [`../docs/CROSS_SYSTEM_STUDY_STATUS.md`](../docs/CROSS_SYSTEM_STUDY_STATUS.md) for the study-level narrative and [`../docs/ENGINEERING_ASSURANCE_STATUS.md`](../docs/ENGINEERING_ASSURANCE_STATUS.md) for the engineering-assurance boundary.
