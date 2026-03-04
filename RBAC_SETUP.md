# RBAC Setup Guide for Maintenance Operator

This guide helps troubleshoot and fix RBAC issues with the maintenance-operator.

## Problem

When applying annotations on a cluster with RBAC enabled, you may see an error like:

```
kopf._cogs.clients.errors.APIForbiddenError: ('ingressroutes.traefik.io is forbidden:
User "system:serviceaccount:maintenance-operator:maintenance-operator" cannot list resource
"ingressroutes" in API group "traefik.io" at the cluster scope:
RBAC: [clusterrole.rbac.authorization.k8s.io "maintenance-operator" not found, ...]
```

## Root Cause

The ClusterRole and/or ClusterRoleBinding are not properly created or the service account doesn't have the necessary permissions.

## Solution

### 1. Verify Current RBAC Resources

Check if the ClusterRole exists:

```bash
# List clusterroles to find your operator's role
kubectl get clusterrole | grep maintenance

# Get detailed info about the ClusterRole (replace with actual name)
kubectl describe clusterrole <maintenance-operator-fullname>
```

Check if the ClusterRoleBinding exists:

```bash
# List clusterrolebindings
kubectl get clusterrolebinding | grep maintenance

# Get detailed info about the ClusterRoleBinding
kubectl describe clusterrolebinding <maintenance-operator-fullname>
```

Check the ServiceAccount:

```bash
# Check service account in operator namespace
kubectl get sa -n <operator-namespace>
kubectl describe sa <maintenance-operator-serviceaccount> -n <operator-namespace>
```

### 2. Reinstall/Upgrade with Proper RBAC

If resources are missing, reinstall the Helm chart with RBAC enabled:

```bash
# Upgrade or install with explicit RBAC creation
helm upgrade --install maintenance-operator ./maintenance-operator \
  --namespace maintenance-operator \
  --create-namespace \
  --set clusterRole.create=true \
  --set serviceAccount.create=true

# Or if using a values file
helm upgrade --install maintenance-operator ./maintenance-operator \
  --namespace maintenance-operator \
  --create-namespace \
  -f custom-values.yaml
```

### 3. Verify Permissions

After installation, verify the ClusterRole has the correct permissions:

```bash
# Check for IngressRoute permissions
kubectl get clusterrole <maintenance-operator-fullname> -o jsonpath='{.rules}' | jq '.[] | select(.resources[]? == "ingressroutes")'

# Expected output should show permissions for both traefik.io and traefik.containo.us API groups
```

### 4. Manual RBAC Creation (Alternative)

If Helm chart issues persist, you can create the RBAC resources manually:

```bash
# Get the rendered template
helm template maintenance-operator ./maintenance-operator \
  --namespace maintenance-operator \
  --set clusterRole.create=true \
  > rendered-manifests.yaml

# Apply only the RBAC resources
kubectl apply -f rendered-manifests.yaml
```

### 5. Check for Common Issues

**Issue 1: Name Mismatch**
```bash
# Verify names match between ClusterRole, ClusterRoleBinding, and ServiceAccount
CLUSTERROLE_NAME=$(kubectl get clusterrole -l app.kubernetes.io/name=maintenance-operator -o jsonpath='{.items[0].metadata.name}')
SA_NAME=$(kubectl get sa -l app.kubernetes.io/name=maintenance-operator -n <operator-namespace> -o jsonpath='{.items[0].metadata.name}')
kubectl get clusterrolebinding -l app.kubernetes.io/name=maintenance-operator -o jsonpath='{.items[0].roleRef.name}')

# All three should output the same name
```

**Issue 2: Namespace mismatch**
```bash
# Ensure ClusterRoleBinding references the correct namespace
kubectl get clusterrolebinding <maintenance-operator-fullname> -o jsonpath='{.subjects[0].namespace}'

# Should match your operator's namespace
```

**Issue 3: Missing cluster-admin (for debugging only)**
```bash
# TEMPORARY: Give cluster-admin to diagnose (NOT for production)
kubectl create clusterrolebinding maintenance-operator-debug \
  --clusterrole=cluster-admin \
  --serviceaccount=maintenance-operator:maintenance-operator

# Remove after debugging
kubectl delete clusterrolebinding maintenance-operator-debug
```

## Required Permissions

The maintenance-operator ClusterRole must include:

1. **IngressRoute permissions** (for Traefik):
   - apiGroups: `["traefik.io", "traefik.containo.us"]`
   - resources: `["ingressroutes"]`
   - verbs: `["get", "list", "watch", "patch", "update"]`

2. **Kopf coordination** (for operator framework):
   - apiGroups: `["coordination.k8s.io"]`
   - resources: `["leases"]`
   - verbs: `["get", "list", "watch", "create", "update", "patch", "delete"]`

3. **Standard resources**:
   - Ingresses (networking.k8s.io)
   - ConfigMaps, Services, Pods, Events, Namespaces

## Verification Test

Create a test IngressRoute to verify permissions:

```bash
cat <<EOF | kubectl apply -f -
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: test-ingressroute
  namespace: default
  annotations:
    maintenance-operator.mithucste30.io/enabled: "true"
spec:
  entryPoints:
    - web
  routes:
    - match: HostPrefix(`test.example.com`)
      kind: Rule
      services:
        - name: test-service
          port: 80
EOF

# Check operator logs for errors
kubectl logs -n maintenance-operator deployment/maintenance-operator -f
```

## Getting Help

If issues persist:
1. Check operator logs: `kubectl logs -n <namespace> deployment/maintenance-operator`
2. Check Kubernetes events: `kubectl get events -n <namespace> --sort-by='.lastTimestamp'`
3. Verify the Helm chart version matches the application version
4. Open an issue at: https://github.com/mithucste30/maintenance-operator/issues
