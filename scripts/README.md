# Scripts Directory

This directory contains utility scripts for managing the Maintenance Operator.

## Available Scripts

### 🚀 create-release.sh

Creates a new release with automated version bumping and tagging.

**Usage:**
```bash
./scripts/create-release.sh <version>
```

**Example:**
```bash
./scripts/create-release.sh 0.1.0
```

**What it does:**
- Updates version in `Chart.yaml` and `values.yaml`
- Commits the changes
- Creates and pushes git tag `v<version>`
- Triggers GitHub Actions to build and publish Docker image and Helm chart

**See also:** [RELEASING.md](../RELEASING.md)

---

### 🗑️ unrelease.sh

Removes a release, including tags, GitHub releases, and provides cleanup instructions.

**Usage:**
```bash
./scripts/unrelease.sh <version>
```

**Example:**
```bash
./scripts/unrelease.sh 0.1.0
```

**What it does:**
- Deletes local git tag `v<version>`
- Deletes remote git tag from origin
- Deletes GitHub release (if gh CLI available)
- Provides instructions for deleting container images and Helm charts
- Optionally reverts version changes in Chart.yaml and values.yaml

**Requirements:**
- Git
- GitHub CLI (`gh`) - optional but recommended

**See also:** [RELEASING.md](../RELEASING.md#rollback-a-release)

---

### 📦 deploy.sh

Deploys the operator to a Kubernetes cluster using Helm.

**Usage:**
```bash
./scripts/deploy.sh [version] [namespace]
```

**Examples:**
```bash
# Deploy latest version to default namespace
./scripts/deploy.sh

# Deploy specific version to custom namespace
./scripts/deploy.sh 0.1.0 my-namespace
```

**What it does:**
- Installs or upgrades the Helm chart
- Creates namespace if it doesn't exist
- Waits for deployment to be ready

---

### 🧹 uninstall.sh

Safely uninstalls the operator from a Kubernetes cluster.

**Usage:**
```bash
./scripts/uninstall.sh [namespace]
```

**Examples:**
```bash
# Uninstall from default namespace
./scripts/uninstall.sh

# Uninstall from custom namespace
./scripts/uninstall.sh my-namespace
```

**What it does:**
- Checks for active maintenance modes
- Optionally removes maintenance labels from resources
- Uninstalls Helm release
- Cleans up backup ConfigMaps
- Optionally deletes the namespace

---

### ⚡ quick-install.sh

One-liner installation script from GitHub.

**Usage:**
```bash
curl -sSL https://raw.githubusercontent.com/mithucste30/maintenance-operator/main/scripts/quick-install.sh | bash
```

**With custom settings:**
```bash
VERSION=0.1.0 NAMESPACE=maintenance-operator \
  curl -sSL https://raw.githubusercontent.com/mithucste30/maintenance-operator/main/scripts/quick-install.sh | bash
```

**What it does:**
- Detects if Helm is installed
- Installs the operator from OCI registry or GitHub releases
- Creates namespace
- Waits for deployment

---

### 🔐 encode-html.sh

Encodes HTML files to base64 for use in values.yaml.

**Usage:**
```bash
./scripts/encode-html.sh <html-file>
```

**Example:**
```bash
./scripts/encode-html.sh maintenance.html
```

**What it does:**
- Reads HTML file
- Encodes to base64
- Outputs encoded string for copying to values.yaml

**See also:** [README.md - Custom Maintenance Pages](../README.md#custom-maintenance-pages)

---

## Script Dependencies

| Script | Required | Optional |
|--------|----------|----------|
| create-release.sh | git | - |
| unrelease.sh | git | gh (GitHub CLI) |
| deploy.sh | kubectl, helm | - |
| uninstall.sh | kubectl, helm | - |
| quick-install.sh | helm | curl |
| encode-html.sh | base64 | - |

## Installation of Dependencies

### GitHub CLI (gh)

**macOS:**
```bash
brew install gh
gh auth login
```

**Linux:**
```bash
# Debian/Ubuntu
sudo apt install gh

# Fedora/RHEL
sudo dnf install gh

gh auth login
```

**Windows:**
```bash
winget install GitHub.cli
gh auth login
```

### Helm

**macOS:**
```bash
brew install helm
```

**Linux:**
```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

**Windows:**
```bash
winget install Helm.Helm
```

### kubectl

See: https://kubernetes.io/docs/tasks/tools/

## Common Workflows

### Release a New Version

```bash
# 1. Create release
./scripts/create-release.sh 0.2.0

# 2. Monitor build
gh run watch

# 3. Verify release
gh release view v0.2.0

# 4. Test installation
helm install test oci://ghcr.io/mithucste30/charts/maintenance-operator --version 0.2.0 --dry-run
```

### Rollback a Release

```bash
# 1. Un-release
./scripts/unrelease.sh 0.2.0

# 2. Follow manual cleanup instructions for container images/charts
```

### Deploy to Cluster

```bash
# 1. Deploy
./scripts/deploy.sh 0.1.0 production

# 2. Verify
kubectl get pods -n production
kubectl get deployment -n production
```

### Create Custom Maintenance Page

```bash
# 1. Create HTML file
cat > custom-page.html << 'EOF'
<!DOCTYPE html>
<html>
<head><title>Custom Maintenance</title></head>
<body><h1>We'll be back soon!</h1></body>
</html>
EOF

# 2. Encode to base64
./scripts/encode-html.sh custom-page.html

# 3. Add output to values.yaml under maintenance.customPages
```

## Troubleshooting

### "Permission denied"

Make scripts executable:
```bash
chmod +x scripts/*.sh
```

### "gh: command not found"

Install GitHub CLI:
```bash
brew install gh  # macOS
# or follow instructions above for other platforms
```

### "helm: command not found"

Install Helm:
```bash
brew install helm  # macOS
# or follow instructions above for other platforms
```

## Contributing

When adding new scripts:

1. Make them executable: `chmod +x scripts/your-script.sh`
2. Add usage documentation at the top of the script
3. Update this README with script description
4. Add error handling and validation
5. Follow the existing script patterns

## See Also

- [README.md](../README.md) - Main documentation
- [RELEASING.md](../RELEASING.md) - Release process
- [DEPLOYMENT.md](../DEPLOYMENT.md) - Deployment guide
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contributing guidelines
