# How to Create a Release

There are several ways to create a release. Choose the one that fits your workflow.

## 🚀 Quick Start (Recommended)

```bash
./release.sh 0.1.0
```

That's it! The script handles everything automatically.

## 📋 All Methods

### Method 1: Release Script (Easiest)

```bash
# Simple and guided
./release.sh 0.1.0
```

**Features:**
- ✅ Validates version format
- ✅ Checks git status
- ✅ Updates all version files
- ✅ Shows diffs before committing
- ✅ Creates and pushes tag
- ✅ Interactive prompts
- ✅ Helpful error messages
- ✅ Shows next steps

### Method 2: Makefile

```bash
# Using Makefile
make release VERSION=0.1.0
```

**Features:**
- ✅ Calls release.sh internally
- ✅ Consistent with other make commands
- ✅ Good for CI/CD integration

### Method 3: Manual (Advanced)

```bash
# Update versions
sed -i "s/^version:.*/version: 0.1.0/" Chart.yaml
sed -i "s/^appVersion:.*/appVersion: \"0.1.0\"/" Chart.yaml
sed -i "s/tag: \".*\"/tag: \"0.1.0\"/" values.yaml

# Commit and tag
git add Chart.yaml values.yaml
git commit -m "chore: release v0.1.0"
git tag -a v0.1.0 -m "Release v0.1.0"

# Push
git push origin main
git push origin v0.1.0
```

**When to use:**
- You know exactly what you're doing
- You're scripting releases in CI/CD
- You need fine-grained control

## 🎯 What Happens Next

After you push the tag (regardless of method):

### 1. GitHub Actions Starts (automatic)

**Build Workflow** - `build-and-push.yaml`
- Builds Docker image (multi-arch)
- Pushes to `ghcr.io/mithucste30/maintenance-operator:0.1.0`
- Creates build attestation

**Release Workflow** - `release-chart.yaml`
- Packages Helm chart
- Pushes to `oci://ghcr.io/mithucste30/charts/maintenance-operator`
- Creates GitHub Release
- Includes installation instructions

### 2. Monitor Progress

```bash
# Browser
open https://github.com/mithucste30/maintenance-operator/actions

# CLI (requires gh)
gh run watch
```

### 3. Wait 3-5 Minutes

Workflows typically complete in 3-5 minutes.

### 4. Make Packages Public (First Release Only)

1. Visit: https://github.com/mithucste30?tab=packages
2. Click on each package
3. Settings → Visibility → Public

### 5. Install Your Release

```bash
# From OCI registry (recommended)
helm install maintenance-operator \
  oci://ghcr.io/mithucste30/charts/maintenance-operator \
  --version 0.1.0 \
  --namespace maintenance-operator \
  --create-namespace

# Or from GitHub release
helm install maintenance-operator \
  https://github.com/mithucste30/maintenance-operator/releases/download/v0.1.0/maintenance-operator-0.1.0.tgz \
  --namespace maintenance-operator \
  --create-namespace
```

## 📚 Detailed Documentation

For more information, see:

- **RELEASING.md** - Complete release guide with troubleshooting
- **DEPLOYMENT.md** - Deployment and installation details
- **CONTRIBUTING.md** - Developer contribution guide

## 🆘 Common Issues

### Version format error

```bash
# Wrong
./release.sh v0.1.0  # Don't include 'v'
./release.sh 0.1     # Must be X.Y.Z

# Correct
./release.sh 0.1.0
```

### Uncommitted changes

```bash
# Commit or stash first
git add .
git commit -m "your changes"

# Then release
./release.sh 0.1.0
```

### Tag already exists

```bash
# Delete tag if needed
git tag -d v0.1.0
git push origin :refs/tags/v0.1.0

# Then release again
./release.sh 0.1.0
```

## 🎓 Learn More

```bash
# Show help
./release.sh

# Show Makefile help
make help

# View release documentation
cat RELEASING.md
```

## 📝 Quick Reference

| Action | Command |
|--------|---------|
| Create release | `./release.sh 0.1.0` |
| Using Makefile | `make release VERSION=0.1.0` |
| Check status | `gh run watch` |
| View releases | `gh release list` |
| Install release | `helm install ... oci://ghcr.io/mithucste30/charts/maintenance-operator --version 0.1.0` |
| Make public | https://github.com/mithucste30?tab=packages |

---

**Next:** After releasing, see [DEPLOYMENT.md](DEPLOYMENT.md) for installation options.
