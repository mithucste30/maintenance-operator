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

# Detect if we're in the chart directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHART_DIR="$(dirname "$SCRIPT_DIR")"
LOCAL_CHART_AVAILABLE=false

if [ -f "$CHART_DIR/Chart.yaml" ]; then
    LOCAL_CHART_AVAILABLE=true
fi

# Install using Helm
echo ""
echo -e "${YELLOW}Installing Maintenance Operator...${NC}"

# Check if version looks like a branch name (main, develop, etc.)
if [[ "$VERSION" =~ ^(main|develop|master|dev)$ ]]; then
    # For branch names, try local chart first if available
    if [ "$LOCAL_CHART_AVAILABLE" = true ]; then
        echo -e "${BLUE}Using local chart (branch: $VERSION)${NC}"
        helm upgrade --install maintenance-operator \
            "$CHART_DIR" \
            --namespace "$NAMESPACE" \
            --create-namespace \
            --wait \
            --timeout 5m \
            --set image.repository=ghcr.io/${GITHUB_REPO} \
            --set image.tag="$VERSION"
        INSTALL_SUCCESS=true
    else
        echo -e "${RED}Error: Local chart not found and no release exists for branch name '$VERSION'${NC}"
        echo -e "${YELLOW}Hint: Run this script from the repository directory, or use a version tag like '0.1.0'${NC}"
        exit 1
    fi
else
    # For version tags, try OCI registry first
    INSTALL_SUCCESS=false

    echo -e "${BLUE}Trying OCI registry: ghcr.io${NC}"
    if helm pull oci://ghcr.io/${GITHUB_REPO}/charts/maintenance-operator --version "$VERSION" --destination /tmp &> /dev/null; then
        helm upgrade --install maintenance-operator \
            oci://ghcr.io/${GITHUB_REPO}/charts/maintenance-operator \
            --version "$VERSION" \
            --namespace "$NAMESPACE" \
            --create-namespace \
            --wait \
            --timeout 5m \
            --set image.repository=ghcr.io/${GITHUB_REPO} \
            --set image.tag="$VERSION"
        INSTALL_SUCCESS=true
    else
        echo -e "${YELLOW}OCI registry not available, trying GitHub releases...${NC}"
        CHART_URL="https://github.com/$GITHUB_REPO/releases/download/v${VERSION}/maintenance-operator-${VERSION}.tgz"

        if curl -fsSL -I "$CHART_URL" &> /dev/null; then
            helm upgrade --install maintenance-operator \
                "$CHART_URL" \
                --namespace "$NAMESPACE" \
                --create-namespace \
                --wait \
                --timeout 5m \
                --set image.repository=ghcr.io/${GITHUB_REPO} \
                --set image.tag="$VERSION"
            INSTALL_SUCCESS=true
        else
            echo -e "${YELLOW}GitHub release not found, trying local chart...${NC}"

            if [ "$LOCAL_CHART_AVAILABLE" = true ]; then
                echo -e "${BLUE}Using local chart${NC}"
                helm upgrade --install maintenance-operator \
                    "$CHART_DIR" \
                    --namespace "$NAMESPACE" \
                    --create-namespace \
                    --wait \
                    --timeout 5m \
                    --set image.repository=ghcr.io/${GITHUB_REPO} \
                    --set image.tag="$VERSION"
                INSTALL_SUCCESS=true
            else
                echo -e "${RED}Error: Could not find chart from any source${NC}"
                echo -e "${YELLOW}Tried:${NC}"
                echo -e "  1. OCI registry: oci://ghcr.io/${GITHUB_REPO}/charts/maintenance-operator"
                echo -e "  2. GitHub release: $CHART_URL"
                echo -e "  3. Local chart: Not available"
                echo ""
                echo -e "${YELLOW}Suggestions:${NC}"
                echo -e "  - Create a release: cd <repo> && ./scripts/create-release.sh $VERSION"
                echo -e "  - Run from repo directory to use local chart"
                exit 1
            fi
        fi
    fi
fi

if [ "$INSTALL_SUCCESS" != true ]; then
    echo -e "${RED}Installation failed${NC}"
    exit 1
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
