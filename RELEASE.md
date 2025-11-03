# Release Process

This document describes how to create a new release of the Maintenance Operator.

## Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible API changes
- **MINOR** version for new functionality in a backward compatible manner
- **PATCH** version for backward compatible bug fixes

Example: `v0.1.0`, `v1.0.0`, `v1.1.0`, `v1.1.1`

## Automated Release Process

The release process is fully automated via GitHub Actions. Here's how to create a new release:

### 1. Prepare for Release

Ensure all changes are merged to the `main` branch and tested:

```bash
# Make sure you're on main and up to date
git checkout main
git pull origin main

# Run tests locally
helm lint .
helm template maintenance-operator . > /dev/null
```

### 2. Create and Push a Version Tag

Create a Git tag with the version number (including the `v` prefix):

```bash
# Set the version
VERSION="0.1.0"

# Create annotated tag
git tag -a "v${VERSION}" -m "Release v${VERSION}"

# Push the tag to GitHub
git push origin "v${VERSION}"
```

### 3. Automated Actions

Once the tag is pushed, GitHub Actions will automatically:

1. **Build Docker Image** (`.github/workflows/build-and-push.yaml`):
   - Build multi-platform image (amd64, arm64)
   - Push to GitHub Container Registry: `ghcr.io/mithucste30/maintenance-operator:${VERSION}`
   - Tag as `:latest` if it's the latest release
   - Generate attestation

2. **Release Helm Chart** (`.github/workflows/release-chart.yaml`):
   - Update Chart.yaml with version number
   - Package Helm chart
   - Create GitHub Release with:
     - Helm chart tarball
     - Installation instructions
     - Auto-generated release notes
   - Push chart to OCI registry: `oci://ghcr.io/mithucste30/charts/maintenance-operator`

### 4. Verify the Release

After the workflows complete, verify:

```bash
# Check GitHub Release
# Visit: https://github.com/mithucste30/maintenance-operator/releases

# Check Docker image
docker pull ghcr.io/mithucste30/maintenance-operator:${VERSION}

# Check OCI Helm chart
helm pull oci://ghcr.io/mithucste30/charts/maintenance-operator --version ${VERSION}

# Test installation
helm install test-release \
  oci://ghcr.io/mithucste30/charts/maintenance-operator \
  --version ${VERSION} \
  --namespace test \
  --create-namespace \
  --dry-run
```

## Manual Release Process

If you need to create a release manually:

### 1. Update Version Numbers

Update the following files:

```bash
VERSION="0.1.0"

# Update Chart.yaml
sed -i "s/^version:.*/version: ${VERSION}/" Chart.yaml
sed -i "s/^appVersion:.*/appVersion: \"${VERSION}\"/" Chart.yaml

# Update values.yaml
sed -i "s/tag: .*/tag: \"${VERSION}\"/" values.yaml

# Commit changes
git add Chart.yaml values.yaml
git commit -m "chore: bump version to ${VERSION}"
git push origin main
```

### 2. Build and Push Docker Image

```bash
# Build for multiple platforms
docker buildx build --platform linux/amd64,linux/arm64 \
  -t ghcr.io/mithucste30/maintenance-operator:${VERSION} \
  -t ghcr.io/mithucste30/maintenance-operator:latest \
  --push .
```

### 3. Package and Push Helm Chart

```bash
# Package chart
helm package . --version ${VERSION} --app-version ${VERSION}

# Push to OCI registry
helm push maintenance-operator-${VERSION}.tgz oci://ghcr.io/mithucste30/charts
```

### 4. Create GitHub Release

```bash
# Create tag
git tag -a "v${VERSION}" -m "Release v${VERSION}"
git push origin "v${VERSION}"

# Create release using GitHub CLI
gh release create "v${VERSION}" \
  maintenance-operator-${VERSION}.tgz \
  --title "v${VERSION}" \
  --generate-notes
```

## Pre-release / Beta Versions

For pre-release versions, use the appropriate suffix:

```bash
# Alpha release
VERSION="0.2.0-alpha.1"
git tag -a "v${VERSION}" -m "Pre-release v${VERSION}"
git push origin "v${VERSION}"

# Beta release
VERSION="0.2.0-beta.1"
git tag -a "v${VERSION}" -m "Pre-release v${VERSION}"
git push origin "v${VERSION}"

# Release candidate
VERSION="1.0.0-rc.1"
git tag -a "v${VERSION}" -m "Release candidate v${VERSION}"
git push origin "v${VERSION}"
```

Pre-releases will be marked as such in GitHub Releases.

## Hotfix Releases

For urgent bug fixes:

1. Create a hotfix branch from the release tag:
```bash
git checkout -b hotfix/v0.1.1 v0.1.0
```

2. Make the fix and commit:
```bash
git add .
git commit -m "fix: critical bug description"
```

3. Update version to patch release:
```bash
VERSION="0.1.1"
sed -i "s/^version:.*/version: ${VERSION}/" Chart.yaml
sed -i "s/^appVersion:.*/appVersion: \"${VERSION}\"/" Chart.yaml
git add Chart.yaml
git commit -m "chore: bump version to ${VERSION}"
```

4. Merge to main and create tag:
```bash
git checkout main
git merge hotfix/v0.1.1
git tag -a "v${VERSION}" -m "Hotfix release v${VERSION}"
git push origin main
git push origin "v${VERSION}"
```

## Release Checklist

Before creating a release, ensure:

- [ ] All tests pass
- [ ] Helm chart lints successfully
- [ ] Chart templates render correctly
- [ ] Documentation is up to date
- [ ] CHANGELOG.md is updated (if maintained)
- [ ] Breaking changes are clearly documented
- [ ] Migration guide is provided (for major versions)
- [ ] Security vulnerabilities are addressed

## Post-Release Tasks

After a release:

1. Update documentation if needed
2. Announce the release (if applicable)
3. Monitor for issues
4. Update dependent projects

## Rollback

If you need to rollback a release:

```bash
# Delete the tag locally and remotely
git tag -d v0.1.0
git push origin :refs/tags/v0.1.0

# Delete the GitHub release
gh release delete v0.1.0

# Delete container images (if needed)
# This requires proper permissions and should be done carefully
```

## Troubleshooting

### Workflow Fails

1. Check the GitHub Actions logs
2. Ensure all secrets are configured (GITHUB_TOKEN)
3. Verify permissions for GITHUB_TOKEN
4. Check if the tag format is correct (must start with 'v')

### Image Push Fails

1. Verify GitHub Container Registry permissions
2. Ensure the repository has package write permissions
3. Check if the image name is correct

### Helm Chart Push Fails

1. Verify OCI registry authentication
2. Ensure Helm version supports OCI (3.8+)
3. Check chart syntax with `helm lint`

## Support

For issues with the release process, please open an issue on GitHub:
https://github.com/mithucste30/maintenance-operator/issues
