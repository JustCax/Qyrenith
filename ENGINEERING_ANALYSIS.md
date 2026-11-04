# Static Engineering Analysis

Qyrenith includes an additive Python engineering engine for source inventory, syntax checks, baseline comparison, change-impact hints, and bounded explicit process execution.

These commands are supplementary checks. They do not replace the existing verify, build, test, security, or evidence workflows.

## Source analysis

```bash
python qyrenith.py source-analysis --project . --max-files 10000 --max-entries 50000
```

The command inventories Python source files and reports SHA-256 hashes, syntax status, import references, class/function symbols, and review hints for eval/exec. It does not import or execute project code.

An optional bound is available with --max-files. Syntax errors return FAIL. An incomplete inventory returns BLOCKED. An empty inventory returns UNKNOWN and a non-success CLI exit code. File digests are calculated from the same bytes that are parsed. Both Python-file count and total directory-entry count are bounded; symlinked source directories and filesystem read errors keep the inventory incomplete.

## Change impact

```bash
python qyrenith.py impact --project . src/module.py
```

The engine reports direct and transitive Python importers. It rejects parent-traversal and absolute changed paths, and returns UNKNOWN when the source inventory or changed-path input is incomplete. It is a static approximation: relative/dynamic imports, reflection, plugin loading, namespace-package edge cases, and cross-language dependencies may be missed. Review the affected set before relying on it.

## Filesystem boundary inspection

```bash
python qyrenith.py boundary-check --project .
```

This read-only inspection reports symlinks that resolve outside the project root and files above the configured size threshold. It does not replace a full security audit. Incomplete directory scans return BLOCKED instead of a clean result.

## Explicit bounded process execution

```bash
python qyrenith.py bounded-check --project . --timeout 60 --output-limit 32768 --check-command-one "python -m unittest discover -s tests"
```

This command executes only the explicitly supplied argv, without a shell, with stdin closed, a timeout, bounded captured output, and a small environment allowlist. It may still access the host filesystem and network with the invoking user's permissions. It is not a security sandbox. Do not use it to run untrusted code. Use a dedicated OS/container sandbox for hostile workloads.

## Programmatic API

```python
from qyrenith_engine import (
    analyze_project,
    build_change_impact,
    compare_baselines,
    inspect_project_boundary,
    run_bounded_process,
)
```

All reports use JSON-compatible dictionaries with explicit statuses and limitations. Consumers must not upgrade UNKNOWN, BLOCKED, or review findings into verified success.
