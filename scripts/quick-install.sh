#!/bin/bash
#
# Quick install script for Maintenance Operator
# This can be run directly from GitHub:
#   curl -sSL https://raw.githubusercontent.com/mithucste30/maintenance-operator/main/scripts/quick-install.sh | bash
#

set -e

GITHUB_REPO="${GITHUB_REPO:-mithucste30/maintenance-operator}"
VERSION="${VERSION:-latest}"
NAMESPACE="${NAMESPACE:-maintenance-operator}"

echo "🚀 Quick Install: Maintenance Operator"
echo ""
echo "Repository: $GITHUB_REPO"
echo "Version: $VERSION"
echo "Namespace: $NAMESPACE"
echo ""

# Check prerequisites
if ! command -v kubectl &> /dev/null; then
    echo "❌ Error: kubectl is not installed"
    exit 1
fi

if ! command -v helm &> /dev/null; then
    echo "❌ Error: helm is not installed"
    exit 1
fi

# Fetch latest version if needed
if [ "$VERSION" = "latest" ]; then
    echo "🔍 Fetching latest version..."
    VERSION=$(curl -s "https://api.github.com/repos/$GITHUB_REPO/releases/latest" | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/')

    if [ -z "$VERSION" ]; then
        echo "⚠️  Could not fetch latest version, using 0.1.0"
        VERSION="0.1.0"
    fi
fi

echo "📦 Installing version: $VERSION"

# Create namespace
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f - > /dev/null 2>&1

# Install from OCI or GitHub release
if helm pull oci://ghcr.io/${GITHUB_REPO}/charts/maintenance-operator --version "$VERSION" --destination /tmp &> /dev/null; then
    echo "📥 Installing from OCI registry..."
    helm upgrade --install maintenance-operator \
        oci://ghcr.io/${GITHUB_REPO}/charts/maintenance-operator \
        --version "$VERSION" \
        --namespace "$NAMESPACE" \
        --wait \
        --set image.repository=ghcr.io/${GITHUB_REPO} \
        --set image.tag="$VERSION"
else
    echo "📥 Installing from GitHub release..."
    CHART_URL="https://github.com/$GITHUB_REPO/releases/download/v${VERSION}/maintenance-operator-${VERSION}.tgz"

    helm upgrade --install maintenance-operator \
        "$CHART_URL" \
        --namespace "$NAMESPACE" \
        --wait \
        --set image.repository=ghcr.io/${GITHUB_REPO} \
        --set image.tag="$VERSION"
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "To enable maintenance mode:"
echo "  kubectl label ingress <name> under-maintenance=true"
echo ""
echo "To disable maintenance mode:"
echo "  kubectl label ingress <name> under-maintenance-"
echo ""
