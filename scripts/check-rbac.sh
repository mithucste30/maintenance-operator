#!/bin/bash
# RBAC Verification Script for Maintenance Operator
# This script checks if all required RBAC resources are properly configured

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
OPERATOR_NAMESPACE=${OPERATOR_NAMESPACE:-"maintenance-operator"}
RELEASE_NAME=${RELEASE_NAME:-"maintenance-operator"}

echo "======================================"
echo "Maintenance Operator RBAC Verification"
echo "======================================"
echo ""

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        return 1
    fi
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# 1. Check if namespace exists
echo "1. Checking namespace..."
if kubectl get namespace "$OPERATOR_NAMESPACE" &>/dev/null; then
    print_status 0 "Namespace '$OPERATOR_NAMESPACE' exists"
else
    print_status 1 "Namespace '$OPERATOR_NAMESPACE' not found"
    echo "   Create it with: kubectl create namespace $OPERATOR_NAMESPACE"
    exit 1
fi

# 2. Find the operator resources
echo ""
echo "2. Finding operator resources..."

# Try to find ClusterRole by label
CLUSTERROLE=$(kubectl get clusterrole -l "app.kubernetes.io/name=maintenance-operator" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -z "$CLUSTERROLE" ]; then
    # Try finding by name pattern
    CLUSTERROLE=$(kubectl get clusterrole -o name | grep -i "maintenance-operator" | head -1 | cut -d'/' -f2 || echo "")
fi

if [ -z "$CLUSTERROLE" ]; then
    print_status 1 "No ClusterRole found for maintenance-operator"
    echo "   The ClusterRole may not have been created during installation"
else
    print_status 0 "Found ClusterRole: $CLUSTERROLE"
fi

# Find ServiceAccount
SERVICEACCOUNT=$(kubectl get sa -n "$OPERATOR_NAMESPACE" -l "app.kubernetes.io/name=maintenance-operator" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -z "$SERVICEACCOUNT" ]; then
    SERVICEACCOUNT=$(kubectl get sa -n "$OPERATOR_NAMESPACE" -o name | grep -i "maintenance" | head -1 | cut -d'/' -f2 || echo "")
fi

if [ -z "$SERVICEACCOUNT" ]; then
    print_status 1 "No ServiceAccount found in namespace '$OPERATOR_NAMESPACE'"
else
    print_status 0 "Found ServiceAccount: $SERVICEACCOUNT"
fi

# Find ClusterRoleBinding
CLUSTERROLEBINDING=$(kubectl get clusterrolebinding -l "app.kubernetes.io/name=maintenance-operator" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -z "$CLUSTERROLEBINDING" ]; then
    CLUSTERROLEBINDING=$(kubectl get clusterrolebinding -o name | grep -i "maintenance-operator" | head -1 | cut -d'/' -f2 || echo "")
fi

if [ -z "$CLUSTERROLEBINDING" ]; then
    print_status 1 "No ClusterRoleBinding found for maintenance-operator"
else
    print_status 0 "Found ClusterRoleBinding: $CLUSTERROLEBINDING"
fi

# 3. Verify ClusterRoleBinding references
echo ""
echo "3. Verifying ClusterRoleBinding configuration..."

if [ -n "$CLUSTERROLEBINDING" ]; then
    # Check roleRef
    BINDING_ROLE=$(kubectl get clusterrolebinding "$CLUSTERROLEBINDING" -o jsonpath='{.roleRef.name}')
    if [ "$BINDING_ROLE" == "$CLUSTERROLE" ]; then
        print_status 0 "ClusterRoleBinding references correct ClusterRole: $BINDING_ROLE"
    else
        print_status 1 "ClusterRoleBinding references '$BINDING_ROLE' but ClusterRole is '$CLUSTERROLE'"
    fi

    # Check subject
    BINDING_SA=$(kubectl get clusterrolebinding "$CLUSTERROLEBINDING" -o jsonpath='{.subjects[0].name}')
    BINDING_NS=$(kubectl get clusterrolebinding "$CLUSTERROLEBINDING" -o jsonpath='{.subjects[0].namespace}')

    if [ "$BINDING_SA" == "$SERVICEACCOUNT" ] && [ "$BINDING_NS" == "$OPERATOR_NAMESPACE" ]; then
        print_status 0 "ClusterRoleBinding references correct ServiceAccount: $BINDING_NS/$BINDING_SA"
    else
        print_status 1 "ClusterRoleBinding references '$BINDING_NS/$BINDING_SA' but ServiceAccount is '$OPERATOR_NAMESPACE/$SERVICEACCOUNT'"
    fi
fi

# 4. Check ClusterRole permissions
echo ""
echo "4. Checking ClusterRole permissions..."

if [ -n "$CLUSTERROLE" ]; then
    # Check for IngressRoute permissions
    if kubectl get clusterrole "$CLUSTERROLE" -o jsonpath='{.rules}' | grep -q '"traefik.io"' 2>/dev/null; then
        print_status 0 "ClusterRole has permissions for 'traefik.io' API group"
    else
        print_status 1 "ClusterRole missing permissions for 'traefik.io' API group"
    fi

    if kubectl get clusterrole "$CLUSTERROLE" -o jsonpath='{.rules}' | grep -q '"ingressroutes"' 2>/dev/null; then
        print_status 0 "ClusterRole has permissions for 'ingressroutes' resource"
    else
        print_status 1 "ClusterRole missing permissions for 'ingressroutes' resource"
    fi

    # Check for coordination.k8s.io permissions (Kopf)
    if kubectl get clusterrole "$CLUSTERROLE" -o jsonpath='{.rules}' | grep -q '"coordination.k8s.io"' 2>/dev/null; then
        print_status 0 "ClusterRole has permissions for 'coordination.k8s.io' API group (Kopf)"
    else
        print_warning "ClusterRole missing permissions for 'coordination.k8s.io' (may cause issues)"
    fi

    # Check for leases permissions
    if kubectl get clusterrole "$CLUSTERROLE" -o jsonpath='{.rules}' | grep -q '"leases"' 2>/dev/null; then
        print_status 0 "ClusterRole has permissions for 'leases' resource"
    else
        print_warning "ClusterRole missing permissions for 'leases' (Kopf coordination)"
    fi
fi

# 5. Test operator permissions
echo ""
echo "5. Testing operator permissions..."

if [ -n "$SERVICEACCOUNT" ] && [ -n "$OPERATOR_NAMESPACE" ]; then
    # Create a test pod with the service account
    TEST_POD="rbac-test-$(date +%s)"

    echo "   Creating test pod with service account..."
    kubectl run "$TEST_POD" \
        --namespace="$OPERATOR_NAMESPACE" \
        --serviceaccount="$SERVICEACCOUNT" \
        --image=bitnami/kubectl:latest \
        --command=sleep \
        --arg=3600 \
        &>/dev/null || true

    # Wait for pod to be ready
    sleep 3

    if kubectl get pod "$TEST_POD" -n "$OPERATOR_NAMESPACE" &>/dev/null; then
        echo "   Testing permissions via test pod..."

        # Test if can list IngressRoutes
        if kubectl exec -n "$OPERATOR_NAMESPACE" "$TEST_POD" -- kubectl auth can-i list ingressroutes.traefik.io --all-namespaces 2>/dev/null | grep -q "yes"; then
            print_status 0 "ServiceAccount can list IngressRoutes at cluster scope"
        else
            print_status 1 "ServiceAccount cannot list IngressRoutes at cluster scope"
        fi

        # Test if can list namespaces
        if kubectl exec -n "$OPERATOR_NAMESPACE" "$TEST_POD" -- kubectl auth can-i list namespaces 2>/dev/null | grep -q "yes"; then
            print_status 0 "ServiceAccount can list namespaces"
        else
            print_status 1 "ServiceAccount cannot list namespaces"
        fi

        # Test if can create leases
        if kubectl exec -n "$OPERATOR_NAMESPACE" "$TEST_POD" -- kubectl auth can-i create leases.coordination.k8s.io --all-namespaces 2>/dev/null | grep -q "yes"; then
            print_status 0 "ServiceAccount can create leases"
        else
            print_warning "ServiceAccount cannot create leases (may cause Kopf issues)"
        fi

        # Cleanup test pod
        kubectl delete pod "$TEST_POD" -n "$OPERATOR_NAMESPACE" &>/dev/null || true
    else
        print_warning "Could not create test pod to verify permissions"
    fi
fi

# 6. Check operator deployment
echo ""
echo "6. Checking operator deployment..."

DEPLOYMENT=$(kubectl get deployment -l "app.kubernetes.io/name=maintenance-operator" -n "$OPERATOR_NAMESPACE" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -z "$DEPLOYMENT" ]; then
    print_status 1 "No operator deployment found"
else
    print_status 0 "Found deployment: $DEPLOYMENT"

    # Check if deployment is using the correct service account
    DEPLOYMENT_SA=$(kubectl get deployment "$DEPLOYMENT" -n "$OPERATOR_NAMESPACE" -o jsonpath='{.spec.template.spec.serviceAccountName}')
    if [ "$DEPLOYMENT_SA" == "$SERVICEACCOUNT" ]; then
        print_status 0 "Deployment is using correct ServiceAccount: $DEPLOYMENT_SA"
    else
        print_status 1 "Deployment is using ServiceAccount '$DEPLOYMENT_SA' but expected '$SERVICEACCOUNT'"
    fi

    # Check deployment status
    READY_REPLICAS=$(kubectl get deployment "$DEPLOYMENT" -n "$OPERATOR_NAMESPACE" -o jsonpath='{.status.readyReplicas}')
    DESIRED_REPLICAS=$(kubectl get deployment "$DEPLOYMENT" -n "$OPERATOR_NAMESPACE" -o jsonpath='{.spec.replicas}')

    if [ "$READY_REPLICAS" == "$DESIRED_REPLICAS" ] && [ -n "$READY_REPLICAS" ]; then
        print_status 0 "Deployment is ready ($READY_REPLICAS/$DESIRED_REPLICAS replicas)"
    else
        print_warning "Deployment may not be ready ($READY_REPLICAS/$DESIRED_REPLICAS replicas)"
    fi
fi

# Summary
echo ""
echo "======================================"
echo "Verification Complete"
echo "======================================"
echo ""
if [ -n "$CLUSTERROLE" ]; then
    echo "ClusterRole: $CLUSTERROLE"
fi
if [ -n "$SERVICEACCOUNT" ]; then
    echo "ServiceAccount: $OPERATOR_NAMESPACE/$SERVICEACCOUNT"
fi
if [ -n "$CLUSTERROLEBINDING" ]; then
    echo "ClusterRoleBinding: $CLUSTERROLEBINDING"
fi

echo ""
echo "For detailed information, see RBAC_SETUP.md"
