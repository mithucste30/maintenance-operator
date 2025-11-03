# Deployment Guide

## 📦 OCI Registry Configuration

### Helm Chart Location

The Helm chart is published to GitHub Container Registry (GHCR) at:

```
oci://ghcr.io/mithucste30/charts/maintenance-operator
```

### Docker Image Location

The Docker image is published to:

```
ghcr.io/mithucste30/maintenance-operator
```

## 🚀 Publishing a Release

### Automated Release (Recommended)

Use the release script:

```bash
cd maintenance-operator

# Create release v0.1.0
./scripts/create-release.sh 0.1.0
```

This will:
1. Update version in `Chart.yaml` and `values.yaml`
2. Commit changes
3. Create git tag `v0.1.0`
4. Push to GitHub
5. Trigger GitHub Actions workflows

### Manual Release

```bash
# 1. Update versions
sed -i "s/^version:.*/version: 0.1.0/" Chart.yaml
sed -i "s/^appVersion:.*/appVersion: \"0.1.0\"/" Chart.yaml
sed -i "s/tag: .*/tag: \"0.1.0\"/" values.yaml

# 2. Commit
git add Chart.yaml values.yaml
git commit -m "chore: bump version to 0.1.0"

# 3. Create and push tag
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin main
git push origin v0.1.0
```

## ⚙️ GitHub Actions Workflows

### Build and Push Docker Image
**Workflow**: `.github/workflows/build-and-push.yaml`
**Triggers**: Push to main/develop, tags (v*), PRs

**What it does**:
- Builds multi-platform images (amd64, arm64)
- Pushes to `ghcr.io/mithucste30/maintenance-operator`
- Tags: `<version>`, `main`, `latest`, `<branch>-<sha>`
- Creates build attestation

### Release Helm Chart
**Workflow**: `.github/workflows/release-chart.yaml`
**Triggers**: Tag push (v*)

**What it does**:
1. Updates Chart.yaml and values.yaml with tag version
2. Packages Helm chart: `maintenance-operator-<version>.tgz`
3. Creates GitHub Release with chart tarball
4. **Pushes to OCI registry**: `oci://ghcr.io/mithucste30/charts/`
   - Accessible as: `oci://ghcr.io/mithucste30/charts/maintenance-operator`
5. Generates installation README

### Lint and Test
**Workflow**: `.github/workflows/lint-test.yaml`
**Triggers**: PRs, pushes to main/develop

**What it does**:
- Helm chart linting
- Template validation
- Kubernetes manifest validation
- Python code linting

## 📥 Installation Methods

### Method 1: OCI Registry (Production)

```bash
helm install maintenance-operator \
  oci://ghcr.io/mithucste30/charts/maintenance-operator \
  --version 0.1.0 \
  --namespace maintenance-operator \
  --create-namespace
```

### Method 2: GitHub Release

```bash
helm install maintenance-operator \
  https://github.com/mithucste30/maintenance-operator/releases/download/v0.1.0/maintenance-operator-0.1.0.tgz \
  --namespace maintenance-operator \
  --create-namespace
```

### Method 3: Local Chart (Development)

```bash
cd maintenance-operator

helm install maintenance-operator . \
  --namespace maintenance-operator \
  --create-namespace \
  --set image.repository=ghcr.io/mithucste30/maintenance-operator \
  --set image.tag=main
```

### Method 4: Quick Install Script

```bash
curl -sSL https://raw.githubusercontent.com/mithucste30/maintenance-operator/main/scripts/quick-install.sh | bash
```

## 🔐 Package Visibility

After first release, make packages public:

1. Go to https://github.com/mithucste30?tab=packages
2. Click on `maintenance-operator` (Docker image)
3. Settings → Change visibility → **Public**
4. Repeat for `charts/maintenance-operator` (Helm chart)

## 🐛 Troubleshooting

### Chart not found in OCI registry

**Symptoms**:
```
Error: failed to authorize: failed to fetch anonymous token: 403 Forbidden
```

**Solutions**:
1. **Wait for workflow** - Release takes 3-5 minutes
2. **Check workflow status**: https://github.com/mithucste30/maintenance-operator/actions
3. **Make package public** (see above)
4. **Use GitHub Release** method instead
5. **Use local chart** for testing

### Workflow failed

**Check**:
- Workflow logs: https://github.com/mithucste30/maintenance-operator/actions
- Permissions: Ensure `packages: write` is granted
- Secrets: GITHUB_TOKEN is automatically provided

**Common issues**:
- Chart.yaml syntax error
- Missing `.deploy` directory (now fixed with `mkdir -p`)
- OCI login failure (check token permissions)

### Image pull failed

**Cause**: Docker image might be private

**Solution**:
1. Make package public (see above)
2. Or use `imagePullSecrets` in values.yaml

## 📊 Verifying the Release

### Check Docker Image

```bash
# Pull image
docker pull ghcr.io/mithucste30/maintenance-operator:0.1.0

# Verify it works
docker run --rm ghcr.io/mithucste30/maintenance-operator:0.1.0 id
```

### Check Helm Chart

```bash
# Pull chart
helm pull oci://ghcr.io/mithucste30/charts/maintenance-operator --version 0.1.0

# Inspect
tar -tzf maintenance-operator-0.1.0.tgz

# Test template
helm template test oci://ghcr.io/mithucste30/charts/maintenance-operator \
  --version 0.1.0 \
  --namespace test > rendered.yaml
```

### Check GitHub Release

```bash
# List releases
gh release list

# View release
gh release view v0.1.0

# Download assets
gh release download v0.1.0
```

## 🔄 Update Process

### Patch Release (0.1.0 → 0.1.1)

```bash
./scripts/create-release.sh 0.1.1
```

### Minor Release (0.1.0 → 0.2.0)

```bash
./scripts/create-release.sh 0.2.0
```

### Major Release (0.x.x → 1.0.0)

```bash
./scripts/create-release.sh 1.0.0

# Update CHANGELOG.md with breaking changes
# Create migration guide if needed
```

## 📚 References

- **Helm OCI Support**: https://helm.sh/docs/topics/registries/
- **GitHub Packages**: https://docs.github.com/en/packages
- **GitHub Actions**: https://docs.github.com/en/actions
