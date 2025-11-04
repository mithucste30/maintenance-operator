# Releasing

Quick guide for creating releases.

## TL;DR

```bash
./release.sh 0.1.0
```

## What the Script Does

The `release.sh` script automates the entire release process:

1. ✅ Validates version format (semantic versioning)
2. ✅ Checks git repository status
3. ✅ Verifies tag doesn't already exist
4. ✅ Updates `Chart.yaml` with new version
5. ✅ Updates `values.yaml` with new image tag
6. ✅ Shows you the changes (git diff)
7. ✅ Commits the changes
8. ✅ Creates git tag `v<version>`
9. ✅ Pushes to GitHub
10. ✅ Triggers automated CI/CD workflows

## Usage

### Basic Release

```bash
# Create release v0.1.0
./release.sh 0.1.0
```

### Patch Release

```bash
# Bug fix release (0.1.0 → 0.1.1)
./release.sh 0.1.1
```

### Minor Release

```bash
# New features (0.1.0 → 0.2.0)
./release.sh 0.2.0
```

### Major Release

```bash
# Breaking changes (0.9.0 → 1.0.0)
./release.sh 1.0.0
```

## What Happens After Push

Once you push the tag, GitHub Actions automatically:

### 1. Build Docker Image (3-5 minutes)
- Multi-platform build (linux/amd64, linux/arm64)
- Push to: `ghcr.io/mithucste30/maintenance-operator:<version>`
- Also tagged as `:latest` (if main branch)

### 2. Package Helm Chart
- Creates: `maintenance-operator-<version>.tgz`
- Pushes to OCI: `oci://ghcr.io/mithucste30/charts/maintenance-operator`

### 3. Create GitHub Release
- URL: `https://github.com/mithucste30/maintenance-operator/releases/tag/v<version>`
- Includes chart tarball
- Auto-generated release notes

## Monitor Progress

```bash
# View in browser
open https://github.com/mithucste30/maintenance-operator/actions

# Or use GitHub CLI
gh run watch
gh run list --limit 5
```

## First Release Only: Make Packages Public

After your first release completes:

1. Go to https://github.com/mithucste30?tab=packages
2. Click on `maintenance-operator` (Docker image)
3. Package Settings → Change visibility → **Public**
4. Repeat for `charts/maintenance-operator` (Helm chart)

## Verify Release

### Check Docker Image

```bash
docker pull ghcr.io/mithucste30/maintenance-operator:0.1.0
docker run --rm ghcr.io/mithucste30/maintenance-operator:0.1.0 id
```

### Check Helm Chart

```bash
helm pull oci://ghcr.io/mithucste30/charts/maintenance-operator --version 0.1.0
tar -tzf maintenance-operator-0.1.0.tgz
```

### Check GitHub Release

```bash
gh release view v0.1.0
```

## Install the Release

### OCI Registry (Recommended)

```bash
helm install maintenance-operator \
  oci://ghcr.io/mithucste30/charts/maintenance-operator \
  --version 0.1.0 \
  --namespace maintenance-operator \
  --create-namespace
```

### GitHub Release Tarball

```bash
helm install maintenance-operator \
  https://github.com/mithucste30/maintenance-operator/releases/download/v0.1.0/maintenance-operator-0.1.0.tgz \
  --namespace maintenance-operator \
  --create-namespace
```

## Rollback a Release

### Using the Unrelease Script (Recommended)

The easiest way to rollback a release is using the automated script:

```bash
# Un-release version 0.1.0
./scripts/unrelease.sh 0.1.0
```

The script will:
- Delete local and remote git tags
- Delete GitHub release
- Provide instructions for deleting container images and Helm charts
- Optionally revert version changes in Chart.yaml and values.yaml

### Manual Rollback

If you prefer to do it manually:

```bash
VERSION="0.1.0"

# Delete the tag locally
git tag -d v${VERSION}

# Delete the tag remotely
git push origin :refs/tags/v${VERSION}

# Delete GitHub release (requires gh CLI)
gh release delete v${VERSION} --yes --cleanup-tag

# Delete container image (manual via GitHub UI)
# Visit: https://github.com/mithucste30/packages/container/maintenance-operator/versions

# Delete Helm chart (manual via GitHub UI)
# Visit: https://github.com/mithucste30/packages/container/charts%2Fmaintenance-operator/versions
```

**Note**: Container images and Helm charts that have been pulled by users cannot be removed from their systems. Deletion only prevents new pulls.

## Troubleshooting

### "Tag already exists"

```bash
# List existing tags
git tag -l

# Delete tag if needed (see Rollback section)
```

### "Uncommitted changes"

```bash
# Commit or stash your changes first
git status
git add .
git commit -m "fix: your changes"

# Or stash temporarily
git stash
./release.sh 0.1.0
git stash pop
```

### "Not on main branch"

The script will warn you but allows proceeding. Best practice is to release from main:

```bash
git checkout main
git pull origin main
./release.sh 0.1.0
```

### Workflow Failed

Check the logs:
```bash
# View in browser
open https://github.com/mithucste30/maintenance-operator/actions

# Or use CLI
gh run list --limit 5
gh run view <run-id>
```

Common issues:
- Chart.yaml syntax error
- Missing permissions
- Network timeout (re-run the workflow)

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0) - Breaking changes
- **MINOR** (0.X.0) - New features (backward compatible)
- **PATCH** (0.0.X) - Bug fixes (backward compatible)

Examples:
- `0.1.0` - First release
- `0.1.1` - Bug fix
- `0.2.0` - New feature
- `1.0.0` - First stable release

## Pre-releases

For alpha/beta versions, use the tag manually:

```bash
VERSION="0.2.0-alpha.1"

# Update files manually
sed -i "s/^version:.*/version: ${VERSION}/" Chart.yaml
sed -i "s/^appVersion:.*/appVersion: \"${VERSION}\"/" Chart.yaml

# Commit and tag
git add Chart.yaml values.yaml
git commit -m "chore: release v${VERSION}"
git tag -a "v${VERSION}" -m "Pre-release v${VERSION}"
git push origin main
git push origin "v${VERSION}"
```

## Release Checklist

Before releasing:

- [ ] All tests pass locally
- [ ] Chart lints successfully: `helm lint .`
- [ ] Documentation is up to date
- [ ] CHANGELOG.md updated (if maintained)
- [ ] Breaking changes documented (for major versions)
- [ ] On main branch (or intentionally on another branch)
- [ ] All commits pushed to GitHub

After releasing:

- [ ] Wait for workflows to complete (~5 minutes)
- [ ] Verify Docker image is available
- [ ] Verify Helm chart is available in OCI registry
- [ ] Verify GitHub Release created
- [ ] Test installation from OCI registry
- [ ] Make packages public (first release only)
- [ ] Announce release (if applicable)

## Quick Commands

```bash
# Create release
./scripts/create-release.sh 0.1.0

# Un-release (rollback)
./scripts/unrelease.sh 0.1.0

# Monitor workflow
gh run watch

# View releases
gh release list

# Test installation
helm install test oci://ghcr.io/mithucste30/charts/maintenance-operator \
  --version 0.1.0 --dry-run

# Clean up test
helm uninstall test
```
