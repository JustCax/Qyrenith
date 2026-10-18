# GitHub Setup Guide — Qyrenith 1.0.0

A complete, step-by-step checklist for publishing the Qyrenith repository on
GitHub. Nothing here requires guessing; every step has a concrete command or a
concrete setting. Nothing is pushed, tagged, or published until you run the
command yourself.

## Prerequisites

- The local repository is on `main` with a clean working tree.
- You have a GitHub account and either the `gh` CLI installed, or a browser.
- The release package builds on any platform with Python 3.8+ via
  `python scripts/release.py`. The POSIX alternative `scripts/release.sh`
  additionally requires `bash`, `rsync`, `zip`, `tar`, and `sha256sum`.

Verify the local state before anything else:

```bash
cd /path/to/qyrenith
git status --short          # must be empty
git log --oneline -1        # should be the latest 1.0.0 commit
python qyrenith.py self-test  # must exit 0
```

---

## Phase 1 — Create the public repository

### Option A: GitHub CLI (recommended, fastest)

```bash
gh auth status
gh repo create qyrenith --public --source=. --remote=origin --push
```

This creates the repo, sets the `origin` remote, and pushes the local history in
one step. The repository name `qyrenith` matches the project name; change it if
you prefer a different name.

### Option B: Browser

1. Go to <https://github.com/new>.
2. Repository name: `qyrenith`.
3. Description: `Safety, verification, and orchestration control plane for Non-AI and AI-assisted software development.`
4. Visibility: **Public**.
5. Do **not** initialize with a README, license, or `.gitignore` — the repo
   already has all of these.
6. Click **Create repository**.
7. Then push the local history:

```bash
git remote add origin https://github.com/<YOUR_USERNAME>/qyrenith.git
git push -u origin main
```

---

## Phase 2 — Push everything (the local history)

All commits are already on `main` locally. Push them:

```bash
git push -u origin main
```

Verify:

```bash
git log --oneline origin/main | head -5
git status -sb
```

Expected: `## main...origin/main` (no ahead/behind).

---

## Phase 3 — Repository presentation settings

Set these in **Settings → General** (or with the `gh` CLI).

### Description and topics

```bash
gh repo edit --description "Safety, verification, and orchestration control plane for Non-AI and AI-assisted software development."

gh repo edit --add-topic agents --add-topic agentskills \
  --add-topic artificial-intelligence --add-topic cli --add-topic developer-tools \
  --add-topic mcp --add-topic minecraft --add-topic modding --add-topic neoforge \
  --add-topic orchestration --add-topic python --add-topic verification
```

### Social preview image

1. Go to **Settings → General → Social preview**.
2. Upload `assets/social-preview.png`.
3. GitHub generates the Open Graph preview image used in link shares.

### Default branch

The default branch is `main`. Leave it as-is.

---

## Phase 4 — Community features

### Discussions

1. Go to **Settings → General → Features**.
2. Enable **Discussions**.
3. Create the suggested categories:
   - Announcements (announcements)
   - Q&A / Troubleshooting (rename the default "Q&A")
   - Ideas
   - Show and tell
   - Development
4. Manage categories any time: on the Discussions page, click the pencil
   icon next to "Categories" in the left sidebar.

### Issue templates

Already provided under `.github/ISSUE_TEMPLATE/` (bug report, feature request).
No action needed.

### Code of conduct / contributing / license

Already present: `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `LICENSE` (MIT).
No action needed.

---

## Phase 5 — Security settings

Open the repository **Settings** tab, then the **Security** section in the
left sidebar, and click **Code security and analysis** (on some accounts this
page appears as **Advanced Security**; it is the same place).

What is available depends on the plan and the repository visibility:

| Feature | Private repository | Public repository |
|---|---|---|
| Dependabot alerts and security updates | yes (free) | yes (free) |
| Secret scanning and push protection | paid plan only | yes (free) |
| Code scanning (CodeQL) | paid plan only | yes (free) |
| Private vulnerability reporting | public repositories only | yes (free) |

On a free private repository the page looks almost empty: GitHub hides or
disables the features the current plan does not include, and Dependabot is
the only free option there. That is expected, not a broken page.

This repository already has **Dependabot alerts** and **Dependabot security
updates** enabled. It has no runtime dependencies, so Dependabot will show no
updates — that is correct.

After the repository becomes public, return to this page and enable, all free:

1. **Secret scanning** and **push protection**.
2. **Code scanning**: set up CodeQL with default setup for Python.
3. **Private vulnerability reporting**.

### Security policy

Already present: `SECURITY.md`. No action needed.

---

## Phase 6 — GitHub Actions (CI)

The repository already ships two workflow files:

- `.github/workflows/ci.yml` — syntax check, full self-test, external worker
  protocol, public audit, doc links, schemas, package hygiene, release package
  and checksum, example NeoForge build.
- `.github/workflows/qyrenith-verify.yml` — PR verification gate.

### Install the PR gate

The `qyrenith-verify.yml` file is in the repository. It will run automatically
on pull requests once pushed. No manual installation needed — just push.

### Verify the workflows run

After pushing, check **Actions** tab for the first run. The `verify` job takes
several minutes (full self-test + benchmark + example NeoForge build). The
`example-build` job requires network access to download Gradle dependencies.

### Note on the example-build job

The `example-build` job builds `examples/example-neoforge-mod` with Gradle.
It requires network access and may fail on first run if the NeoForge CDN is
unavailable. This is a known limitation, not a code defect.

---

## Phase 7 — Branch protection

Recommended settings for the `main` branch:

1. Go to **Settings → Branches → Add rule**.
2. Branch name pattern: `main`.
3. Enable:
   - **Require a pull request before merging** (at least 1 approval)
   - **Require status checks to pass before merging**
     - Select: `verify` (from `ci.yml`) and `qyrenith-verify` (from
       `qyrenith-verify.yml`)
   - **Require conversation resolution before merging**
   - **Do not allow bypassing the above settings**
4. Leave "Allow force pushes" and "Allow deletions" disabled.

---

## Phase 8 — Release package

Both scripts produce the same file set; use whichever fits your platform.

### Build

```bash
# Any platform with Python 3.8+ (recommended on Windows)
python scripts/release.py /path/to/output-dir

# POSIX alternative (requires rsync, zip, tar, sha256sum)
bash scripts/release.sh /path/to/output-dir
```

This produces:

- `qyrenith-1.0.0.zip` + `.sha256`
- `qyrenith-1.0.0.tar.gz` + `.sha256`

### Verify

```bash
cd /path/to/output-dir
unzip -t qyrenith-1.0.0.zip
tar -tzf qyrenith-1.0.0.tar.gz >/dev/null
sha256sum -c qyrenith-1.0.0.zip.sha256
sha256sum -c qyrenith-1.0.0.tar.gz.sha256
```

### Package hygiene check

```bash
# Must be empty (no forbidden entries)
! unzip -l /path/to/output-dir/qyrenith-1.0.0.zip | grep -E '(^|/)(\.qyrenith|\.backups|__pycache__|.*\.pyc|.*\.tmp|target|node_modules|Cargo\.lock|\.gradle|build|runs)(/|$)'
```

---

## Phase 9 — Create the first release (v1.0.0)

### Tag

```bash
git tag -a v1.0.0 -m "Qyrenith 1.0.0 — first public release"
git push origin v1.0.0
```

### GitHub Release

1. Go to **Releases → Draft a new release**.
2. Tag: `v1.0.0`.
3. Title: `Qyrenith 1.0.0 — first public release`.
4. Description: paste from `RELEASE_NOTES_1.0.0.md`.
5. Attach:
   - `qyrenith-1.0.0.zip`
   - `qyrenith-1.0.0.zip.sha256`
   - `qyrenith-1.0.0.tar.gz`
   - `qyrenith-1.0.0.tar.gz.sha256`
6. Click **Publish release**.

### Or with the CLI

```bash
gh release create v1.0.0 --title "Qyrenith 1.0.0" --notes-file RELEASE_NOTES_1.0.0.md \
  /path/to/output-dir/qyrenith-1.0.0.zip \
  /path/to/output-dir/qyrenith-1.0.0.zip.sha256 \
  /path/to/output-dir/qyrenith-1.0.0.tar.gz \
  /path/to/output-dir/qyrenith-1.0.0.tar.gz.sha256
```

---

## Phase 10 — Post-release verification

After the release is published:

```bash
# Verify the published archive is installable
python -m venv /tmp/qyrenith-published
/tmp/qyrenith-published/bin/python -m pip install /path/to/qyrenith-1.0.0.tar.gz
/tmp/qyrenith-published/bin/qyrenith --version
/tmp/qyrenith-published/bin/qyrenith self-test
```

On Windows, use `C:\tmp\qyrenith-published\Scripts\python.exe` and
`C:\tmp\qyrenith-published\Scripts\qyrenith.exe`.

---

## Summary checklist

- [ ] `git status` clean, `self-test` exits 0
- [ ] GitHub repository created (public)
- [ ] Local history pushed (`git push -u origin main`)
- [ ] Description and topics set
- [ ] Social preview image uploaded
- [ ] Discussions enabled with categories
- [ ] Secret scanning + push protection + code scanning enabled
- [ ] Branch protection rule on `main`
- [ ] Workflows run green on first push
- [ ] Release package built and verified
- [ ] Tag `v1.0.0` pushed
- [ ] GitHub Release published with archives and checksums
- [ ] Published archive install-verified on a clean venv
