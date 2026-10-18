# Security

Please do not publish credentials, private source code, proprietary skill files, or `.qyrenith` runtime state in issues or pull requests.

## Security-sensitive behavior

Qyrenith can execute Git and the project's canonical build script. Review the project and skill files before running it on an untrusted repository.

The tool intentionally does not provide a generic arbitrary-shell execution command. Build execution is delegated to the project's declared build skill.

If you find a security issue in Qyrenith, report it privately to the repository maintainers before public disclosure.


## Security finding review

Secret-like findings are blocking by default. A finding can be explicitly reviewed only with its exact finding ID, a non-empty reason, and `--yes`:

```text
python qyrenith.py security-review --project . --finding-id <id> --reason "Document the false-positive rationale" --yes
```

The review is bound to the finding ID generated from its type, path, line, and redacted value hash. A changed finding therefore requires a new review. Documentation placeholders such as `paste-the-shared-forwarding-secret-here` are classified as placeholders and do not create a secret finding.
