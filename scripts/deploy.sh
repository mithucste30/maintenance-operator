#!/bin/bash
#
# Deployment script for Maintenance Operator
# Installs from GitHub Container Registry and Helm Chart
#
# Usage:
#   ./scripts/deploy.sh [VERSION] [NAMESPACE]
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DEFAULT_VERSION="latest"
DEFAULT_NAMESPACE="maintenance-operator"
GITHUB_REPO="${GITHUB_REPO:-mithucste30/maintenance-operator}"

# Parse arguments
VERSION="${1:-$DEFAULT_VERSION}"
NAMESPACE="${2:-$DEFAULT_NAMESPACE}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Maintenance Operator Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Version:${NC} $VERSION"
echo -e "${GREEN}Namespace:${NC} $NAMESPACE"
echo -e "${GREEN}Repository:${NC} $GITHUB_REPO"
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl is not installed or not in PATH${NC}"
    exit 1
fi

# Check if helm is available
if ! command -v helm &> /dev/null; then
    echo -e "${RED}Error: helm is not installed or not in PATH${NC}"
    exit 1
fi

# Check cluster connectivity
echo -e "${YELLOW}Checking Kubernetes cluster connectivity...${NC}"
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}Error: Cannot connect to Kubernetes cluster${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Connected to cluster${NC}"
echo ""

# Create namespace if it doesn't exist
echo -e "${YELLOW}Creating namespace if needed...${NC}"
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
echo -e "${GREEN}✓ Namespace ready${NC}"
echo ""

# Determine installation method
INSTALL_METHOD="oci"
CHART_URL=""

if [ "$VERSION" = "latest" ]; then
    # For latest, try to get from GitHub releases
    echo -e "${YELLOW}Fetching latest release version...${NC}"
    LATEST_VERSION=$(curl -s "https://api.github.com/repos/$GITHUB_REPO/releases/latest" | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/')

    if [ -z "$LATEST_VERSION" ]; then
        echo -e "${YELLOW}Warning: Could not fetch latest version from GitHub. Using 'latest' tag.${NC}"
        VERSION="latest"
    else
        VERSION="$LATEST_VERSION"
        echo -e "${GREEN}✓ Latest version: $VERSION${NC}"
    fi
fi

# Install using Helm
echo ""
echo -e "${YELLOW}Installing Maintenance Operator...${NC}"

if [ "$INSTALL_METHOD" = "oci" ]; then
    echo -e "${BLUE}Using OCI registry: ghcr.io${NC}"

    # Try OCI registry first
    if helm pull oci://ghcr.io/${GITHUB_REPO}/charts/maintenance-operator --version "$VERSION" &> /dev/null; then
        helm upgrade --install maintenance-operator \
            oci://ghcr.io/${GITHUB_REPO}/charts/maintenance-operator \
            --version "$VERSION" \
            --namespace "$NAMESPACE" \
            --create-namespace \
            --wait \
            --timeout 5m \
            --set image.repository=ghcr.io/${GITHUB_REPO} \
            --set image.tag="$VERSION"
    else
        echo -e "${YELLOW}OCI registry not available, trying GitHub releases...${NC}"
        CHART_URL="https://github.com/$GITHUB_REPO/releases/download/v${VERSION}/maintenance-operator-${VERSION}.tgz"

        helm upgrade --install maintenance-operator \
            "$CHART_URL" \
            --namespace "$NAMESPACE" \
            --create-namespace \
            --wait \
            --timeout 5m \
            --set image.repository=ghcr.io/${GITHUB_REPO} \
            --set image.tag="$VERSION"
    fi
else
    echo -e "${BLUE}Using GitHub release: $CHART_URL${NC}"

    helm upgrade --install maintenance-operator \
        "$CHART_URL" \
        --namespace "$NAMESPACE" \
        --create-namespace \
        --wait \
        --timeout 5m \
        --set image.repository=ghcr.io/${GITHUB_REPO} \
        --set image.tag="$VERSION"
fi

echo ""
echo -e "${GREEN}✓ Maintenance Operator installed successfully!${NC}"
echo ""

# Show deployment status
echo -e "${YELLOW}Checking deployment status...${NC}"
kubectl get deployment -n "$NAMESPACE" -l app.kubernetes.io/name=maintenance-operator
echo ""

echo -e "${YELLOW}Checking pods...${NC}"
kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=maintenance-operator
echo ""

# Show notes
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Next Steps${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "To enable maintenance mode on an Ingress:"
echo -e "  ${GREEN}kubectl label ingress <name> under-maintenance=true${NC}"
echo ""
echo -e "To enable maintenance mode on an IngressRoute:"
echo -e "  ${GREEN}kubectl label ingressroute <name> under-maintenance=true${NC}"
echo ""
echo -e "To disable maintenance mode:"
echo -e "  ${GREEN}kubectl label ingress <name> under-maintenance-${NC}"
echo ""
echo -e "To check operator logs:"
echo -e "  ${GREEN}kubectl logs -n $NAMESPACE -l app.kubernetes.io/name=maintenance-operator -c operator -f${NC}"
echo ""
echo -e "For more information, visit:"
echo -e "  ${BLUE}https://github.com/$GITHUB_REPO${NC}"
echo ""
