# Changelog

## 1.1.0 — Engineering analysis and release integrity

Qyrenith 1.1.0 adds a modular, standard-library-only engineering analysis package and strengthens release integrity.

- Added bounded static Python source inventory with SHA-256 evidence, syntax results, import references, symbol inventory, and review hints for dynamic `eval`/`exec` calls. Project code is not imported or executed.
- Added validated source-baseline comparison, including new syntax failures, and conservative direct/transitive Python import-impact hints.
- Added read-only filesystem boundary inspection for symlink escapes, oversized files, and incomplete scans.
- Added explicit bounded process execution with shell-free argv, environment allowlisting, timeout, hard output-capture limits, and POSIX process-group cleanup. This is not an OS sandbox.
- Extracted the new engineering capabilities into the built-in `qyrenith_engine/` package without third-party runtime dependencies.
- Added an explicit `PUBLIC_FILES.txt` release allowlist shared by ZIP/TAR archives and Python source distributions.
- Added release-content tests for archives, source distributions, wheels, executable modes, and CLI entry points.
- Validated the engineering engine across Python 3.11–3.14 on Linux, Windows, and macOS.

Limitations are explicit: source analysis is Python AST analysis, change impact is a static import approximation, filesystem inspection is not a full security audit, and bounded execution is not a sandbox. See [RELEASE_NOTES_1.1.0.md](RELEASE_NOTES_1.1.0.md).

## 1.0.0 — First public release

Qyrenith 1.0.0 is the first public release.

What this release contains:

- Project-neutral verification (`verify`, `inspect`, `policy`, `explain`) for
  Python, Node.js and Rust, each with a real adapter, a reproducible benchmark
  fixture, and a failure-detection test.
- Minecraft L5 control-plane verification: CI gate, policy engine, recovery
  tests, adversarial/failure-quality cases, golden migration benchmark. A real
  Gradle/JAR build remains a mandatory real gate and is never claimed as
  satisfied offline.
- Multi-client AI entrypoints generated from canonical skills, plus a CLI-only
  guide that was followed end-to-end.
- Fail-closed defaults throughout: unknown stays unknown, zero capability is
  never a pass, and `--allow-missing-adapters` is an explicit opt-in.
- A one-file core (`qyrenith.py`), standard library only, no runtime
  dependencies; adapter detection never mistakes the control plane's own file
  for a project capability.
- Build outputs (`target/`, `node_modules/`, `dist/`) stay out of git and the
  release package, so benchmark fixtures remain redistributable.
