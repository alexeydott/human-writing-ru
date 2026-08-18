# Package contents

Complete installable package for `human-writing-ru`, version **1.9.0-beta.4**.

The ZIP root is the stable Agent Skills directory `human-writing-ru/`; the version belongs to the archive name and metadata, not to the install directory.

## Inventory

- `(root)`: 17 files
- `.github`: 1 files
- `agents`: 1 files
- `benchmark`: 49 files
- `data`: 2 files
- `dist`: 1 files
- `evals`: 19 files
- `profiles`: 4 files
- `quality`: 5 files
- `references`: 19 files
- `research`: 21 files
- `scripts`: 23 files
- `tests`: 17 files

Total files: **179**.

## Integrity

`FILES.sha256` hashes every packaged file except `FILES.sha256` and `PACKAGE_CONTENTS.md` itself to avoid self-reference.

Build with:

```bash
python3 scripts/build_release.py
```

By default the archive and its SHA-256 checksum are written to `dist/`. Use `--output-dir` to write the release inputs to another directory (for example, a temporary directory during tests). The script only prepares local release files; it does not create or publish a GitHub release.
