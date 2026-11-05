# Security

Please do not publish credentials, private source code, proprietary skill files, or `.qyrenith` runtime state in issues or pull requests.

## Security-sensitive behavior

Qyrenith can execute Git and the project's canonical build script. Review the project and skill files before running it on an untrusted repository.

The tool intentionally does not provide a generic arbitrary-shell execution command. Build execution is delegated to the project's declared build skill.

If you find a security issue in Qyrenith, report it privately to the repository maintainers before public disclosure.


## Owner trust store API

The 1.2.0 branch introduces an owner-scoped trust-decision store through `qyrenith_engine.trust_store.OwnerTrustStore`. By default it stores trust state in the current user's Qyrenith configuration directory, outside the managed project. It records append-only TRUST and REVOKE decisions for exact SHA-256 digests of knowledge catalogs, worker manifests, worker qualifications, and execution policies. POSIX storage uses owner-only permissions; the Windows default path is constrained to the current user profile and rejects reparse-point paths.

The store authenticates its canonical contents with a local HMAC key and detects accidental or repository-local tampering. This is not a publisher signature, remote attestation, or defense against malicious code already running as the same OS user. Reviewer names are attribution metadata, not authenticated identity. A trust decision must never be inferred from a project file or imported allowlist.

**Important current limitation:** the store is now consumed by the opt-in `authorize_migration_with_owner_trust` and `validate_migration_authorization_with_owner_trust` APIs, which recheck exact catalog, manifest, and qualification digests and honor revocation. The trust store is not yet wired into worker dispatch or the legacy `worker-run` command, and these helpers still do not authenticate the human approver or authorize execution by themselves. The legacy command's `--yes` option is a caller assertion, not authenticated host approval, and the shared subprocess runner is not an OS sandbox. Until the trusted approval channel and OS-enforced sandbox are integrated, migration-worker and QDAS repair execution remain propose-only.



## Security finding review

Secret-like findings are blocking by default. A finding can be explicitly reviewed only with its exact finding ID, a non-empty reason, and `--yes`:

```text
python qyrenith.py security-review --project . --finding-id <id> --reason "Document the false-positive rationale" --yes
```

The review is bound to the finding ID generated from its type, path, line, and redacted value hash. A changed finding therefore requires a new review. Documentation placeholders such as `paste-the-shared-forwarding-secret-here` are classified as placeholders and do not create a secret finding.
