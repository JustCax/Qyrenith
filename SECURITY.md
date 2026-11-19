# Security

Please do not publish credentials, private source code, proprietary skill files, or `.qyrenith` runtime state in issues or pull requests.

## Security-sensitive behavior

Qyrenith can execute Git and the project's canonical build script. Review the project and skill files before running it on an untrusted repository.

The tool intentionally does not provide a generic arbitrary-shell execution command. Build execution is delegated to the project's declared build skill.

If you find a security issue in Qyrenith, report it privately to the repository maintainers before public disclosure.


## Owner trust store API

The 1.2.0 branch introduces an owner-scoped trust-decision store through `qyrenith_engine.trust_store.OwnerTrustStore`. By default it stores trust state in the current user's Qyrenith configuration directory, outside the managed project. It records append-only TRUST and REVOKE decisions for exact SHA-256 digests of knowledge catalogs, worker manifests, worker qualifications, and execution policies. POSIX storage uses owner-only permissions; Windows storage is constrained to the current user profile and rejects reparse-point paths, but currently relies on inherited profile ACLs rather than independently inspecting the DACL.

The store authenticates its canonical contents with a local HMAC key and detects accidental or repository-local tampering. Use the interactive CLI for owner decisions:

```text
python qyrenith.py trust-store --trust-action init
python qyrenith.py trust-store --trust-action list
python qyrenith.py trust-store --trust-action trust --trust-kind WORKER_MANIFEST --digest sha256:<64-lowercase-hex> --reason "Reviewed exact worker build"
python qyrenith.py trust-store --trust-action revoke --trust-kind WORKER_MANIFEST --digest sha256:<64-lowercase-hex> --reason "Worker withdrawn"
```

Trust/revoke commands require an interactive terminal and an exact one-time challenge. The lower-level Python API remains an administrative primitive and can be called programmatically by code running as the same user; use the CLI only from a trusted local session. This is not a publisher signature, remote attestation, or defense against malicious code already running as the same OS user. Reviewer names are attribution metadata, not authenticated identity. A trust decision must never be inferred from a project file or imported allowlist.

**Important current limitations:** the store is consumed by the opt-in `authorize_migration_with_owner_trust` and `validate_migration_authorization_with_owner_trust` APIs, which recheck exact catalog, manifest, and qualification digests and honor revocation. The `qyrenith_engine.approval` API provides an interactive TTY challenge, HMAC-signed exact-scope host-approval records bound to the owner trust-store ID/generation, expiry revalidation, and replay-resistant one-time nonce consumption. The migration step-boundary APIs `create_migration_step_approval_request()` and `validate_migration_step_approval()` bind the approval to the exact authorization, route/transition, worker grant, workspace, snapshot, command digest, and declared sandbox-profile identity; validation rechecks the relevant trust/authorization state and consumes the nonce before the intended step boundary.

This is a local interactive confirmation mechanism, not independent authentication of a human identity or proof of legal identity. The recorded principal is derived from `getpass.getuser()`, and the local HMAC key is not an independent trust anchor. The lower-level `authorize_migration()` constructor still accepts caller-supplied approver attribution and timestamps; callers must not treat those fields as authenticated approval. The step-boundary API is not an end-to-end worker executor and is not yet proof that every execution/repair path requires this approval. In particular, the legacy `worker-run` command's `--yes` option remains a caller assertion. The declared sandbox-profile ID/digest binds a declaration only: no OS sandbox provider or enforced process/filesystem/network/resource boundary is established by that field. The shared subprocess runner is bounded process execution, not an OS sandbox. Until authenticated host identity, mandatory execution-path integration, independently qualified workers, and OS-enforced isolation are implemented and verified, migration-worker and QDAS repair execution remain propose-only/BLOCKED.



## Security finding review

Secret-like findings are blocking by default. A finding can be explicitly reviewed only with its exact finding ID, a non-empty reason, and `--yes`:

```text
python qyrenith.py security-review --project . --finding-id <id> --reason "Document the false-positive rationale" --yes
```

The review is bound to the finding ID generated from its type, path, line, and redacted value hash. A changed finding therefore requires a new review. Documentation placeholders such as `paste-the-shared-forwarding-secret-here` are classified as placeholders and do not create a secret finding.
