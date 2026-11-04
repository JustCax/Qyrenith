# Qyrenith 1.1.0 — Engineering Analysis and Release Integrity

## Overview

Qyrenith 1.1.0 adds a modular, standard-library-only engineering analysis package to the existing project verification and orchestration control plane. The new capabilities are supplementary checks; they do not replace existing build, test, security, evidence, or migration gates.

## New capabilities

### Static Python source analysis

- Inventories Python source files without importing or executing project code.
- Computes SHA-256 digests from the same bytes used for parsing.
- Reports syntax state, import references, class/function symbols, and manual-review hints for dynamic `eval` and `exec` calls.
- Enforces file-count, directory-entry, and per-file size limits.
- Treats incomplete scans, symlinked source directories, and unreadable files conservatively.

Command:

```bash
python qyrenith.py source-analysis --project . --max-files 10000 --max-entries 50000
```

### Baseline comparison and change impact

- Compares validated source-analysis snapshots for added, removed, changed, and syntax-regressed files.
- Reports current syntax failures, including failures in newly added files.
- Builds a conservative direct/transitive Python import-impact approximation for explicitly supplied changed paths.
- Rejects absolute and parent-traversal paths and returns UNKNOWN when the input or source inventory is incomplete.

Commands:

```bash
python qyrenith.py impact --project . src/module.py
```

The import graph is intentionally conservative. Relative and dynamic imports, reflection, plugin loading, namespace-package edge cases, and cross-language dependencies may be missed. It is not a complete dependency or semantic graph.

### Filesystem boundary inspection

- Performs read-only inspection of project entries.
- Reports symlink targets that escape the project root and files above the configured size threshold.
- Does not follow symlinked directories.
- Returns BLOCKED when the scan cannot be completed within its bounds or filesystem metadata cannot be inspected.

Command:

```bash
python qyrenith.py boundary-check --project .
```

### Explicit bounded process execution

- Requires an explicit argument vector supplied by the user.
- Executes without a shell, with stdin closed and a small environment-variable allowlist.
- Applies a timeout and a hard in-memory output-capture limit.
- Cleans up the launched POSIX process group on timeout or output overflow.
- Reports ERROR, FAIL, BLOCKED, or PASS without promoting incomplete execution to success.

Command:

```bash
python qyrenith.py bounded-check --project . --timeout 60 --output-limit 32768 --check-command-one "python -m unittest discover -s tests"
```

**Security boundary:** bounded execution is not an operating-system sandbox. Child code retains the invoking user's operating-system permissions and may access files or networks available to that user. Do not use it to execute hostile code. Use a dedicated OS or container sandbox for untrusted workloads. Windows process termination has platform-specific limits and must not be interpreted as equivalent to a security sandbox.

## Architecture and packaging

- Engineering capabilities live in the built-in `qyrenith_engine/` package, keeping the main control plane modular.
- No third-party runtime dependencies are introduced.
- Full source installation requires both `qyrenith.py` and the adjacent `qyrenith_engine/` package, or installation through PyPI/source packaging.
- Public ZIP/TAR release archives and Python source distributions use the explicit `PUBLIC_FILES.txt` allowlist.
- Release-content tests verify archive membership, file bytes, executable modes, source-distribution contents, and wheel module/entry-point contents.
- Internal agent instructions and maintainer-only setup files are excluded from release archives by default.

## Validation

The 1.1.0 validation matrix covers Python 3.11, 3.12, 3.13, and 3.14 on Ubuntu, Windows, and macOS. The full CI workflow additionally runs the repository self-test suite, public audit, documentation-link checks, schema checks, release-manifest tests, archive/checksum validation, and the public NeoForge example build.

A passing CI run demonstrates that the declared checks completed successfully for the tested revision and environments. It does not prove the absence of defects or provide a general security certification.

## Explicit limitations

- Static source analysis is Python AST analysis, not complete semantic or behavioral verification.
- Change-impact analysis is an approximation based on statically resolved Python imports.
- Filesystem boundary inspection is not malware scanning or a complete security audit.
- Bounded process execution is not a sandbox.
- No checker may claim more than its evidence and documented scope support.

## Upgrade

Install or upgrade from PyPI:

```bash
python -m pip install --upgrade qyrenith
```

For source installation, preserve the complete package layout and use Python 3.11 or newer.
