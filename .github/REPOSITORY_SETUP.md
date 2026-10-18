# GitHub Repository Setup

This file separates repository-host configuration from the source distribution. It is a checklist for the maintainer after the project is connected to its public GitHub repository.

## Presentation

- Description: `Safety, verification, and orchestration control plane for Non-AI and AI-assisted software development.`
- Suggested topics: `agents`, `agentskills`, `artificial-intelligence`, `cli`, `developer-tools`, `mcp`, `minecraft`, `modding`, `neoforge`, `orchestration`, `python`, `verification`.
- Social preview source asset: `assets/social-preview.png`.
- README architecture diagram: Mermaid section in `README.md`.

## Community

Enable Discussions if the repository uses GitHub Discussions. Suggested categories:

- Announcements
- Q&A / Troubleshooting
- Ideas
- Show and tell
- Development

Issue templates are provided under `.github/ISSUE_TEMPLATE/`.

## Security

Where available on the repository plan, enable and review:

- Security policy (`SECURITY.md`)
- Dependabot
- secret scanning
- push protection
- code scanning
- private vulnerability reporting

Do not claim these are enabled until the repository settings confirm them.

## Releases

Use GitHub Releases with:

- semantic version tag, e.g. `v1.0.0`
- release notes from `RELEASE_NOTES_1.0.0.md`
- verified ZIP
- SHA-256 checksum

## External prerequisite

The local source tree cannot truthfully mark GitHub-host settings as enabled without repository access. This document is therefore a deployment checklist, not evidence that remote settings have already been changed.
