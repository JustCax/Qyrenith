# Changelog

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
