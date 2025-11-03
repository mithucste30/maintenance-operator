#!/bin/bash
#
# Uninstall script for Maintenance Operator
#
# Usage:
#   ./scripts/uninstall.sh [NAMESPACE]
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DEFAULT_NAMESPACE="maintenance-operator"
NAMESPACE="${1:-$DEFAULT_NAMESPACE}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Maintenance Operator Uninstall${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Namespace:${NC} $NAMESPACE"
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

# Check if release exists
if ! helm list -n "$NAMESPACE" | grep -q "maintenance-operator"; then
    echo -e "${YELLOW}Warning: maintenance-operator release not found in namespace $NAMESPACE${NC}"
    echo -e "${YELLOW}Checking other namespaces...${NC}"

    # Try to find in other namespaces
    FOUND_NAMESPACE=$(helm list -A | grep "maintenance-operator" | awk '{print $2}' | head -1)

    if [ -n "$FOUND_NAMESPACE" ]; then
        echo -e "${GREEN}Found in namespace: $FOUND_NAMESPACE${NC}"
        read -p "Do you want to uninstall from $FOUND_NAMESPACE instead? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            NAMESPACE="$FOUND_NAMESPACE"
        else
            echo -e "${RED}Aborting.${NC}"
            exit 1
        fi
    else
        echo -e "${RED}Error: maintenance-operator not found in any namespace${NC}"
        exit 1
    fi
fi

# Show current state
echo -e "${YELLOW}Current deployment:${NC}"
kubectl get all -n "$NAMESPACE" -l app.kubernetes.io/name=maintenance-operator
echo ""

# Confirm uninstallation
read -p "Are you sure you want to uninstall maintenance-operator from namespace $NAMESPACE? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Uninstallation cancelled.${NC}"
    exit 0
fi

# Check for active maintenance modes
echo ""
echo -e "${YELLOW}Checking for active maintenance modes...${NC}"
ACTIVE_INGRESS=$(kubectl get ingress -A -l under-maintenance=true -o jsonpath='{range .items[*]}{.metadata.namespace}/{.metadata.name}{"\n"}{end}')
ACTIVE_INGRESSROUTE=$(kubectl get ingressroute -A -l under-maintenance=true -o jsonpath='{range .items[*]}{.metadata.namespace}/{.metadata.name}{"\n"}{end}' 2>/dev/null || echo "")

if [ -n "$ACTIVE_INGRESS" ] || [ -n "$ACTIVE_INGRESSROUTE" ]; then
    echo -e "${YELLOW}Warning: Found resources in maintenance mode:${NC}"

    if [ -n "$ACTIVE_INGRESS" ]; then
        echo -e "${YELLOW}Ingresses:${NC}"
        echo "$ACTIVE_INGRESS"
    fi

    if [ -n "$ACTIVE_INGRESSROUTE" ]; then
        echo -e "${YELLOW}IngressRoutes:${NC}"
        echo "$ACTIVE_INGRESSROUTE"
    fi

    echo ""
    read -p "Do you want to remove maintenance mode from these resources? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Removing maintenance labels...${NC}"

        if [ -n "$ACTIVE_INGRESS" ]; then
            kubectl get ingress -A -l under-maintenance=true -o json | \
                jq -r '.items[] | "\(.metadata.namespace) \(.metadata.name)"' | \
                while read -r ns name; do
                    echo "  Removing label from ingress $ns/$name"
                    kubectl label ingress -n "$ns" "$name" under-maintenance-
                done
        fi

        if [ -n "$ACTIVE_INGRESSROUTE" ]; then
            kubectl get ingressroute -A -l under-maintenance=true -o json 2>/dev/null | \
                jq -r '.items[] | "\(.metadata.namespace) \(.metadata.name)"' | \
                while read -r ns name; do
                    echo "  Removing label from ingressroute $ns/$name"
                    kubectl label ingressroute -n "$ns" "$name" under-maintenance-
                done || true
        fi

        echo -e "${GREEN}✓ Maintenance labels removed${NC}"
    fi
fi

# Uninstall Helm release
echo ""
echo -e "${YELLOW}Uninstalling Helm release...${NC}"
helm uninstall maintenance-operator -n "$NAMESPACE"
echo -e "${GREEN}✓ Helm release uninstalled${NC}"

# Clean up backup ConfigMaps
echo ""
echo -e "${YELLOW}Cleaning up backup ConfigMaps...${NC}"
kubectl delete configmap -n "$NAMESPACE" -l app=maintenance-operator --ignore-not-found=true
echo -e "${GREEN}✓ Backup ConfigMaps cleaned up${NC}"

# Ask about namespace deletion
echo ""
read -p "Do you want to delete the namespace $NAMESPACE? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Deleting namespace...${NC}"
    kubectl delete namespace "$NAMESPACE" --ignore-not-found=true
    echo -e "${GREEN}✓ Namespace deleted${NC}"
fi

echo ""
echo -e "${GREEN}✓ Maintenance Operator uninstalled successfully!${NC}"
echo ""
