# node-verification

A redistributable Node.js verification fixture for the Qyrenith control plane.

This public fixture is intentionally dependency-free: it uses only the Node.js
built-in test runner (`node --test`), so no `npm install` and no network access
are required. It proves the *verification* path — detection, availability
semantics, real execution, and that a failing test fails the gate — not a full
toolchain build.
