# Migrating to artifact and contract 2.13

Version 2.13 intentionally closes permissive 2.12 certification behavior.

- Regenerate artifacts to serialize all SATB voices and every per-beat form, target,
  source, and key-context array. Inapplicable target/source values are explicit nulls.
- Numeric strings, booleans-as-integers, fractional MIDI pitches, and non-finite numbers
  are rejected by strict input validation.
- `verified_constraint_ids` now lists freshly evaluated rules; the complete 57-row
  ledger separately records `NOT_APPLICABLE` rules. Each row now includes `visited`;
  an applicable predicate that is not reached becomes `BLOCKED`, never `PASS`.
- Validation failures now serialize stable structured diagnostics. Consumers should
  treat `code`, `rule_id`, `feature`, and `location` as machine fields and `message`
  as presentation text.
- Use `verify` for embedded-context inspection and `certify --spec ... --midi ...` for
  strict release acceptance.
- The default generated MIDI is `certified-satb`; request `melody-plus-satb` explicitly
  when the separate rhythmic melody projection is required.
- OR-Tools moved to the `generation` extra. Checker-only installations need only the
  base package.

A complete 2.12 artifact may be inspected with `verify --allow-legacy`, but it is not a
2.13 strict certificate. Incomplete artifacts must be regenerated; missing voices are
never inferred.
