# Architecture

This document describes the internal architecture of the Maintenance Operator.

## Overview

The Maintenance Operator uses an **on-demand, per-namespace architecture** that creates lightweight maintenance resources only when needed. This design prioritizes simplicity, resource efficiency, and namespace isolation.

## Design Philosophy

### Key Principles

1. **Simplicity**: No centralized service, no cross-namespace routing, no complex endpoint management
2. **On-demand**: Resources created only when maintenance mode is enabled
3. **Resource sharing**: Multiple Ingresses with identical HTML share resources (via content hashing)
4. **Automatic cleanup**: Resources deleted when no longer referenced
5. **Namespace isolation**: Each namespace manages its own maintenance resources

## Components

### 1. Operator Controller

**Language**: Python
**Framework**: Kopf (Kubernetes Operator Framework)
**Location**: `app/maintenance_operator.py`

**Responsibilities**:
- Watch Ingress (networking.k8s.io/v1) resources
- Watch IngressRoute (traefik.io/v1alpha1) resources
- Detect maintenance annotation changes
- Create/delete maintenance resources
- Manage backup ConfigMaps
- Track resource references

**Key Functions**:
- `handle_ingress()` - Process Ingress resources
- `handle_ingressroute()` - Process Traefik IngressRoute resources

### 2. Utility Functions

**Location**: `app/utils.py`

**Key Functions**:

#### Resource Management
- `create_maintenance_resources(namespace, ingress_name, custom_page)`
  - Creates ConfigMap + Pod + Service in target namespace
  - Returns service name based on content hash

- `delete_maintenance_resources(namespace, ingress_name, service_name)`
  - Removes Ingress reference from ConfigMap
  - Deletes resources if no more references exist

#### Content Management
- `get_html_content(custom_page)` - Retrieves HTML from operator namespace ConfigMaps
- `hash_content(content)` - Generates 8-char SHA256 hash for resource naming
- `get_fallback_html()` - Returns basic fallback HTML if ConfigMap missing

#### Backup Management
- `create_backup_configmap()` - Stores original Ingress/IngressRoute config
- `get_backup_configmap()` - Retrieves backup
- `delete_backup_configmap()` - Removes backup

### 3. Maintenance Resources (Per Namespace)

These resources are created **on-demand** in each namespace that enables maintenance mode.

#### ConfigMap: `maintenance-{hash}`

**Purpose**: Store HTML content and track which Ingresses use it

**Structure**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: maintenance-a1b2c3d4  # Hash of HTML content
  namespace: production
  labels:
    app: maintenance-page
    managed-by: maintenance-operator
    content-hash: a1b2c3d4
  annotations:
    maintenance-operator.mithucste30.io/custom-page: "default"
    maintenance-operator.mithucste30.io/used-by: "ingress1,ingress2"
data:
  index.html: |
    <!DOCTYPE html>...
```

#### Pod: `maintenance-{hash}`

**Purpose**: Serve HTML content via nginx

**Structure**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: maintenance-a1b2c3d4
  namespace: production
  labels:
    app: maintenance-page
    managed-by: maintenance-operator
    content-hash: a1b2c3d4
spec:
  containers:
  - name: nginx
    image: nginx:alpine
    ports:
    - containerPort: 80
    volumeMounts:
    - name: html
      mountPath: /usr/share/nginx/html
      readOnly: true
    resources:
      requests:
        cpu: 10m
        memory: 16Mi
      limits:
        cpu: 50m
        memory: 32Mi
  volumes:
  - name: html
    configMap:
      name: maintenance-a1b2c3d4
```

#### Service: `maintenance-{hash}`

**Purpose**: Provide stable endpoint for Ingress/IngressRoute

**Structure**:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: maintenance-a1b2c3d4
  namespace: production
  labels:
    app: maintenance-page
    managed-by: maintenance-operator
    content-hash: a1b2c3d4
spec:
  type: ClusterIP
  ports:
  - name: http
    port: 80
    targetPort: 80
  selector:
    app: maintenance-page
    managed-by: maintenance-operator
    content-hash: a1b2c3d4
```

## Workflow

### Enabling Maintenance Mode

```
User adds annotation
        ↓
Operator detects change
        ↓
Store backup ConfigMap
        ↓
Get HTML content from operator namespace
        ↓
Calculate content hash (e.g., a1b2c3d4)
        ↓
Check if maintenance-a1b2c3d4 exists
        ↓
    ┌──────────┴──────────┐
    │                     │
   YES                   NO
    │                     │
    │              Create ConfigMap
    │              Create Pod
    │              Create Service
    │                     │
    └──────────┬──────────┘
               ↓
    Update ConfigMap's used-by annotation
               ↓
    Update Ingress to point to maintenance-a1b2c3d4
               ↓
         Traffic redirected
```

### Disabling Maintenance Mode

```
User removes annotation
        ↓
Operator detects change
        ↓
Restore original config from backup
        ↓
Remove Ingress name from ConfigMap's used-by
        ↓
Check if any Ingresses still reference resources
        ↓
    ┌───────┴───────┐
    │               │
   YES             NO
    │               │
  Keep          Delete Pod
resources       Delete Service
                Delete ConfigMap
    │               │
    └───────┬───────┘
            ↓
    Delete backup ConfigMap
            ↓
         Complete
```

### Resource Sharing Example

**Scenario**: Three Ingresses in `production` namespace

```
Ingress A: default page  →  maintenance-a1b2c3d4
Ingress B: default page  →  maintenance-a1b2c3d4  (shared!)
Ingress C: custom "app1" →  maintenance-e5f6g7h8
```

**Result**:
- 2 sets of maintenance resources (2 Pods, 2 Services, 2 ConfigMaps)
- ConfigMap `maintenance-a1b2c3d4` has `used-by: "ingressA,ingressB"`
- ConfigMap `maintenance-e5f6g7h8` has `used-by: "ingressC"`

**When disabling Ingress A**:
- Remove "ingressA" from `used-by` annotation
- Resources stay (Ingress B still uses them)

**When disabling Ingress B**:
- Remove "ingressB" from `used-by` annotation
- Delete all `maintenance-a1b2c3d4` resources (no more references)

## Resource Naming

Resources use a content-based naming scheme:

```
maintenance-{hash}
```

Where `{hash}` is the first 8 characters of SHA256(html_content).

**Benefits**:
- Automatic deduplication (same HTML = same hash)
- Predictable naming
- Easy to identify which resources serve which content

**Examples**:
```
Default page:           maintenance-7f9a4bc2
Custom page "app1":     maintenance-3d5e8f1a
Custom page "checkout": maintenance-9b2c7e4d
```

## Configuration Sources

### Operator Namespace ConfigMaps

The operator reads HTML content from ConfigMaps in its own namespace:

**Default page**: `maintenance-operator-default-pages`
```yaml
data:
  page.html: |
    <!DOCTYPE html>...
```

**Custom pages**: `maintenance-page-{name}`
```yaml
metadata:
  name: maintenance-page-my-app
data:
  page.html: |
    <!DOCTYPE html>...
```

These ConfigMaps are created by the Helm chart from `values.yaml`.

## Annotations

### User-facing Annotations

**Enable maintenance mode**:
```yaml
maintenance-operator.mithucste30.io/enabled: "true"
```

**Select custom page**:
```yaml
maintenance-operator.mithucste30.io/custom-page: "my-app"
```

### Operator-managed Annotations

**On Ingress/IngressRoute** (tracks state):
```yaml
maintenance-operator.mithucste30.io/original-service: "true"
maintenance-operator.mithucste30.io/service-name: "maintenance-a1b2c3d4"
```

**On maintenance ConfigMap** (tracks usage):
```yaml
maintenance-operator.mithucste30.io/custom-page: "default"
maintenance-operator.mithucste30.io/used-by: "ingress1,ingress2,ingress3"
```

## RBAC Requirements

The operator requires these permissions:

**Cluster-wide**:
- Ingress: get, list, watch, patch, update
- IngressRoute: get, list, watch, patch, update
- Namespace: get, list, watch (for kopf)

**In all namespaces**:
- ConfigMap: get, list, watch, create, update, patch, delete
- Pod: get, list, create, delete
- Service: get, list, create, delete
- Events: create, patch (for logging)

## Comparison with Previous Architecture

### Old Architecture (Centralized Server)

```
┌─────────────────────────────────────────┐
│        Operator Namespace                │
│  ┌────────────┐  ┌──────────────────┐   │
│  │ Operator   │  │ Maintenance      │   │
│  │ Controller │  │ Server (Flask)   │   │
│  └────────────┘  └──────────────────┘   │
└─────────────────────────────────────────┘
                    ▲
                    │ Cross-namespace
                    │ proxy traffic
                    │
┌─────────────────────────────────────────┐
│    Target Namespaces                     │
│  ┌──────────┐  ┌──────────┐             │
│  │ Service  │  │ Endpoints│             │
│  │ (proxy)  │─▶│ (to ops) │             │
│  └──────────┘  └──────────┘             │
└─────────────────────────────────────────┘
```

**Issues**:
- Complex endpoint management
- Periodic reconciliation needed
- Cross-namespace traffic
- Centralized bottleneck
- High privilege requirements

### New Architecture (Per-Namespace Resources)

```
┌─────────────────────────────────────────┐
│        Operator Namespace                │
│  ┌────────────┐  ┌──────────────────┐   │
│  │ Operator   │  │ Content          │   │
│  │ Controller │  │ ConfigMaps       │   │
│  └────────────┘  └──────────────────┘   │
└─────────────────────────────────────────┘
           │
           │ Creates resources on-demand
           ▼
┌─────────────────────────────────────────┐
│    Target Namespaces                     │
│  ┌────────────────────────────────────┐ │
│  │ maintenance-{hash}                  │ │
│  │ ┌─────────┐  ┌─────┐  ┌─────────┐ │ │
│  │ │ConfigMap│  │ Pod │  │ Service │ │ │
│  │ │(HTML)   │─▶│nginx│─▶│(ClusterIP)│ │
│  │ └─────────┘  └─────┘  └─────────┘ │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

**Benefits**:
- No endpoint management
- No reconciliation loops
- Namespace isolation
- Automatic resource sharing
- Simpler RBAC

## Performance Characteristics

### Resource Overhead

**Per maintenance pod**:
- CPU request: 10m (0.01 core)
- CPU limit: 50m (0.05 core)
- Memory request: 16Mi
- Memory limit: 32Mi
- Image size: ~10MB (nginx:alpine)

**Example cluster with 100 namespaces**:
- If all use default page: 1 pod per namespace = 100 pods
- If some use custom pages: Varies by content diversity
- Shared resources reduce overhead

### Scaling

**Operator**: Single pod, watches all Ingress/IngressRoute across cluster
**Maintenance pods**: Distributed per namespace, minimal footprint
**Typical load**: <1% CPU, <50MB RAM per maintenance pod

### Startup Time

- ConfigMap creation: <100ms
- Pod scheduling: 1-5 seconds (depends on cluster)
- nginx ready: <1 second
- **Total**: 2-6 seconds from annotation to serving traffic

## Future Enhancements

Potential improvements to consider:

1. **Deployment instead of Pod**: Use Deployment for HA and rolling updates
2. **ReplicaSet**: Multiple replicas for high-traffic scenarios
3. **HPA**: Auto-scale maintenance pods based on traffic
4. **JSON/XML support**: Restore content negotiation if needed
5. **Custom status codes**: Per-page HTTP status code configuration
6. **Metrics**: Export prometheus metrics for maintenance state
7. **CRD**: Custom resource for maintenance configuration instead of annotations

## Security Considerations

1. **RBAC**: Operator has wide permissions; restrict access to operator namespace
2. **HTML content**: Validated during Helm install (base64 encoded in values)
3. **Pod security**: Uses nginx:alpine with minimal privileges
4. **Resource limits**: Enforced to prevent resource exhaustion
5. **Namespace isolation**: Each namespace's maintenance resources are isolated

## Debugging

### Check maintenance resources in a namespace

```bash
# List all maintenance resources
kubectl get cm,pod,svc -l app=maintenance-page -n production

# Check specific resource
kubectl describe pod maintenance-a1b2c3d4 -n production

# View HTML content
kubectl get cm maintenance-a1b2c3d4 -n production -o jsonpath='{.data.index\.html}'

# Check used-by annotation
kubectl get cm maintenance-a1b2c3d4 -n production -o jsonpath='{.metadata.annotations}'
```

### Check operator logs

```bash
kubectl logs -n maintenance-operator deployment/maintenance-operator -f
```

### Test maintenance page

```bash
# Port-forward to maintenance service
kubectl port-forward -n production svc/maintenance-a1b2c3d4 8080:80

# View page
curl localhost:8080
```

## References

- Kopf Documentation: https://kopf.readthedocs.io/
- Kubernetes Operator Pattern: https://kubernetes.io/docs/concepts/extend-kubernetes/operator/
- nginx Documentation: https://nginx.org/en/docs/
