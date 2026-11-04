# Releasing Qyrenith

This document describes the controlled release path for the Python package on PyPI and the deterministic source archives on GitHub Releases.

## Release authority and trigger

A stable GitHub Release publication triggers `.github/workflows/release.yml`. The workflow accepts only a release tag that matches both `VERSION.txt` and `project.version` in `pyproject.toml`, and whose commit is reachable from `main`.

The workflow then:

1. Runs the full Qyrenith self-test and release-specific consistency tests.
2. Builds the Python source distribution and wheel.
3. Builds the deterministic public ZIP/TAR archives and SHA-256 files from `PUBLIC_FILES.txt`.
4. Checks Python distribution metadata and installs the wheel into an isolated target for import/version smoke tests.
5. Publishes the Python distributions to PyPI using Trusted Publishing.
6. Attaches the deterministic archives and checksums to the GitHub Release.

Draft and prerelease releases do not publish.

## One-time PyPI Trusted Publisher setup

A PyPI project owner must register the GitHub Actions publisher once:

1. Open [Qyrenith on PyPI](https://pypi.org/project/qyrenith/), choose **Manage**, then **Publishing**.
2. Add a GitHub Actions publisher with:
   - **Owner:** `JustCax`
   - **Repository:** `Qyrenith`
   - **Workflow filename:** `release.yml`
   - **Environment:** `pypi`
3. Save the publisher configuration.

The publisher must match the repository and workflow identity. No PyPI API token or password is stored in GitHub. The workflow requests a short-lived upload credential through GitHub OIDC.

## GitHub environment protection

In the repository, open **Settings → Environments → pypi**. Create the environment and configure a required reviewer for every production publication. Use a trusted maintainer as reviewer. Do not permit untrusted pull-request code to run in the publishing job.

The publishing job is the only job that receives `id-token: write`. Build and release-asset jobs do not receive PyPI credentials. The publisher runs only after the build job has produced and validated the release bundle.

## Publishing a release

After the workflow and both protection settings are in place:

1. Confirm that the target version is present in `VERSION.txt`, `pyproject.toml`, `qyrenith.py`, and the release notes.
2. Confirm that the version tag points to a commit already on `main`.
3. Create a GitHub Release using the exact tag `vX.Y.Z`.
4. Publish the GitHub Release. This is the explicit release trigger.
5. Review the `Qyrenith Release` workflow. The PyPI job waits for the `pypi` environment approval before publishing.
6. Verify the published files and version on PyPI and the ZIP/TAR/checksum assets on GitHub Releases.

A normal branch push, pull request, or tag push without a published GitHub Release does not publish to PyPI.

## Important limitations

- PyPI releases are immutable by version. Do not attempt to upload different files under an already-published version; prepare a new patch version instead.
- Trusted Publishing authenticates the workflow; it does not prove that the package contents are safe or correct. The workflow therefore builds and validates the package before the publishing job.
- A failed publication must be diagnosed before retrying. Do not create a second artifact with the same version and assume PyPI will replace the first upload.
- The GitHub Release and PyPI project are separate publication destinations. Success in one does not imply success in the other.
