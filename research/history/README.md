# Frozen multifixture history transport

`multifixture_assurance_v1.bundle` preserves the original five local study commits
through `50749ad435690f2f1021e0caeaf9918ad0a12ea3`, based on the already published
`ef7e8c5a882e07fce5f862fca20fb9e3bb5a3c24`. It contains the exact protocol,
implementation and evidence Git objects referenced by the recorded study.

The authenticated GitHub connector uploads repository files through its Git data
API but cannot set the author/committer dates required to recreate identical commit
IDs. Publishing the bundle preserves those original IDs without changing the
frozen evaluator, protocol, raw outcomes or implementation hashes. The published
branch has its own transport commit; this is not an external preregistration claim.

Bundle SHA-256: `d42dbdb6d185c581ab4d9eabd253e777e0a7994efdec5d1ee12cc9ed72ed4dcb`.

From a full checkout, import the original objects into a separate audit ref:

```bash
git bundle verify research/history/multifixture_assurance_v1.bundle
git fetch --no-tags research/history/multifixture_assurance_v1.bundle refs/heads/research/multifixture-assurance-v1:refs/assurance/multifixture-assurance-v1-original
python -m research.multifixture_assurance --check
```

CI performs the fetch before running the release gate and deterministic study
replay on Python 3.11-3.13. Importing these objects does not modify tracked files
or move the checked-out branch. The candidate attestation remains the original
generation checkout, while release-assurance attests the actual current checkout.
