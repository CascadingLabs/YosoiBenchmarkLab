# Parser/selector fixture set v1

No large generated fixture is committed in the specification-only revision.

The frozen plan is defined in `specs/parser-selector-v1.json` and
`docs/parser-selector-methodology.md`:

- `cavemanCatalog`: approximately 88 KiB, 128 records, one exact result;
- `hardCatalog`: 12–24 MiB, 25,000 records, at least 250,000 elements, 64
  selected records, and a fixed ordered oracle;
- `scraplingNested`: publisher-exact 5,000-element reproduction;
- `hardRecovery`: bounded malformed/deep/namespace correctness suite.

The next slice must add a deterministic generator, materialize the fixtures,
record their byte sizes and SHA-256 digests in a manifest, and independently
verify the oracle before any benchmark adapter is timed.
