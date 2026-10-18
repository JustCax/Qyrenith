# Contributing

## Rules

- Keep the core project-neutral.
- Do not add an author's private mod names or proprietary feature names to core logic.
- Keep Minecraft API knowledge in specialist skills/references.
- Preserve the responsibility boundary.
- Every safety invariant needs a regression test.
- Do not weaken backup, audit, validation, or commit gates for convenience.
- Prefer standard library dependencies for the core.
- Keep CLI exit codes stable once released.
- Add documentation for new user-visible behavior.

## Pull requests

Include:

- motivation
- behavior change
- tests
- safety impact
- compatibility impact
- documentation updates

Run:

```bash
python qyrenith.py self-test
python -m unittest discover -s tests -v
```
