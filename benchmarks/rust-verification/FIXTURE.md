# rust-verification

A redistributable Rust verification fixture for the Qyrenith control plane.

This public fixture is intentionally dependency-free: `cargo check` needs no
network access for a project without dependencies. It proves the
*verification* path — detection, availability semantics, real execution, and
that broken code fails the gate — not a full toolchain build. `cargo check`
performs type checking without linking, so no system linker is required.
