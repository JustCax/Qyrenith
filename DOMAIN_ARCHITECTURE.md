# Qyrenith Domain Architecture

Qyrenith is a project-neutral verification and orchestration control plane. Minecraft is the first flagship domain, not a hard architectural boundary.

## Core vs domain

The core owns:

- preflight and safety
- backups and Git boundaries
- Reality Map and Reality Diff
- evidence/provenance
- worker/agent contracts
- build and artifact trust
- validation
- recovery
- policy and reporting

A domain owns specialist knowledge through skills, providers, workers, and adapters.

Initial domain registry:

- Minecraft
- Roblox
- Skyrim
- GTA/FiveM
- Unity
- Godot
- Unreal
- Python
- JavaScript/TypeScript
- Rust
- Java
- C/C++

These registrations do not claim full domain support. They establish safe routing boundaries and extension points. A domain becomes fully supported only when it has real providers, workers, validators, and benchmarks.

## Maturity levels

Levels follow the L0–L5 model. A level is claimed only where the evidence
actually runs; the table in `README.md` states each domain's level with its
evidence. Current claims: Minecraft L5, Python L2, JavaScript/TypeScript/Node
L2, Rust L2. All other registered domains are L0 (routing names only).

## Skill routing rule

A generic task must not activate a specialist skill merely because the repository contains that specialist domain. Explicit task-domain signals take precedence over project-domain signals.

Example: `Minecraft repository + review this Python utility` routes to generic/Python expertise and does not activate Minecraft migration skills. A Minecraft migration task routes to Minecraft specialists. Discovery is advisory and never grants execution authority.
