# Quick Start Guide

## 🚀 Publishing Your First Release

Since the Helm chart isn't in the OCI registry yet, you need to create a release. Here's how:

### Method 1: Using the Release Script (Easiest)

```bash
cd maintenance-operator

# Create release v0.1.0
./scripts/create-release.sh 0.1.0
```

The script will:
1. Update version in `Chart.yaml` and `values.yaml`
2. Commit the changes
3. Create and push a git tag `v0.1.0`
4. Trigger GitHub Actions to build and publish everything

### Method 2: Manual Release

```bash
cd maintenance-operator

# 1. Update version
sed -i "s/^version:.*/version: 0.1.0/" Chart.yaml
sed -i "s/^appVersion:.*/appVersion: \"0.1.0\"/" Chart.yaml
sed -i "s/tag: .*/tag: \"0.1.0\"/" values.yaml

# 2. Commit changes
git add Chart.yaml values.yaml
git commit -m "chore: bump version to 0.1.0"

# 3. Create and push tag
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin main
git push origin v0.1.0
```

### What Happens Next?

GitHub Actions will automatically:

1. **Build Docker Image** (3-5 minutes)
   - Multi-platform: linux/amd64, linux/arm64
   - Push to: `ghcr.io/mithucste30/maintenance-operator:0.1.0`
   - Also tagged as: `:latest`

2. **Package Helm Chart**
   - Create: `maintenance-operator-0.1.0.tgz`
   - Push to OCI: `oci://ghcr.io/mithucste30/charts/maintenance-operator`

3. **Create GitHub Release**
   - URL: `https://github.com/mithucste30/maintenance-operator/releases/tag/v0.1.0`
   - Includes chart tarball
   - Includes installation instructions

### Monitor Progress

```bash
# Check workflow status
open https://github.com/mithucste30/maintenance-operator/actions

# Or use GitHub CLI
gh run list --limit 5
gh run watch
```

## 📦 Installation After Release

### Once the release completes (wait 3-5 minutes), install with:

**Option 1: OCI Registry (Recommended)**
```bash
helm install maintenance-operator \
  oci://ghcr.io/mithucste30/charts/maintenance-operator \
  --version 0.1.0 \
  --namespace maintenance-operator \
  --create-namespace
```

**Option 2: GitHub Release Tarball**
```bash
helm install maintenance-operator \
  https://github.com/mithucste30/maintenance-operator/releases/download/v0.1.0/maintenance-operator-0.1.0.tgz \
  --namespace maintenance-operator \
  --create-namespace
```

**Option 3: Quick Install Script**
```bash
curl -sSL https://raw.githubusercontent.com/mithucste30/maintenance-operator/main/scripts/quick-install.sh | bash
```

## 🔧 Install Right Now (Before Release)

If you want to test it immediately without waiting for the release:

**Using Local Chart**
```bash
cd maintenance-operator

helm install maintenance-operator . \
  --namespace maintenance-operator \
  --create-namespace \
  --set image.repository=ghcr.io/mithucste30/maintenance-operator \
  --set image.tag=main
```

**Using Deployment Script**
```bash
cd maintenance-operator
./scripts/deploy.sh main maintenance-operator
```

**Using Makefile**
```bash
cd maintenance-operator
make install
```

## 🧪 Testing the Operator

Once installed, test it:

```bash
# Create a test ingress
kubectl create namespace test
kubectl create ingress test-ingress \
  --namespace test \
  --rule="test.example.com/*=test-service:80"

# Enable maintenance mode
kubectl label ingress test-ingress under-maintenance=true -n test

# Check it worked
kubectl get ingress test-ingress -n test -o yaml

# You should see:
# - Label: under-maintenance: "true"
# - Annotation: maintenance-operator.kahf.io/original-service: "true"
# - Service points to: maintenance-operator

# Disable maintenance mode
kubectl label ingress test-ingress under-maintenance- -n test
```

## 📊 Checking Package Visibility

After the release, check if packages are public:

1. Go to: `https://github.com/mithucste30?tab=packages`
2. Click on `maintenance-operator` (Docker image)
3. Click "Package Settings" → "Change visibility" → "Public"
4. Repeat for the Helm chart package

## 🔍 Troubleshooting

### "403 Forbidden" when pulling Helm chart
- **Cause**: Chart not published yet or package is private
- **Solution**:
  1. Wait for release workflow to complete
  2. Make package public (see above)
  3. Or use local installation methods

### "Image pull failed"
- **Cause**: Docker image is private
- **Solution**: Make the container package public

### Release workflow failed
- **Check**: https://github.com/mithucste30/maintenance-operator/actions
- **Common issues**:
  - Missing secrets
  - Permissions issues
  - Syntax errors in workflow

## 📚 Next Steps

1. **Create the release**: `./scripts/create-release.sh 0.1.0`
2. **Wait 3-5 minutes**: For GitHub Actions to complete
3. **Install**: Use OCI registry or GitHub releases
4. **Test**: Create a test ingress and enable maintenance mode
5. **Read docs**: Check README.md for full documentation

## 🆘 Need Help?

- **Documentation**: See [README.md](README.md)
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Issues**: https://github.com/mithucste30/maintenance-operator/issues
