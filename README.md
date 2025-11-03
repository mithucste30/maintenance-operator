# Maintenance Operator

[![Release](https://img.shields.io/github/v/release/mithucste30/maintenance-operator?style=flat-square)](https://github.com/mithucste30/maintenance-operator/releases)
[![Build Status](https://img.shields.io/github/actions/workflow/status/mithucste30/maintenance-operator/build-and-push.yaml?branch=main&style=flat-square)](https://github.com/mithucste30/maintenance-operator/actions)
[![codecov](https://codecov.io/gh/mithucste30/maintenance-operator/branch/main/graph/badge.svg?style=flat-square)](https://codecov.io/gh/mithucste30/maintenance-operator)
[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](LICENSE)
[![Kubernetes](https://img.shields.io/badge/kubernetes-%3E%3D1.19-blue?style=flat-square&logo=kubernetes)](https://kubernetes.io)
[![Helm](https://img.shields.io/badge/helm-v3-blue?style=flat-square&logo=helm)](https://helm.sh)

A Kubernetes operator that manages maintenance mode for Ingress and IngressRoute (Traefik) resources. When you add an annotation to an Ingress or IngressRoute, the operator automatically redirects traffic to a maintenance page.

## Features

- **Automatic maintenance mode**: Simply add an annotation to enable maintenance
- **Works with standard Ingress and Traefik IngressRoute** resources
- **Multiple content types**: Serves HTML, JSON, and XML based on client Accept headers
- **Custom maintenance pages**: Configure different pages for different services (IngressRoute only)
- **Automatic backup and restore**: Original service configuration is stored and restored automatically
- **Proper HTTP status codes**: Returns 503 Service Unavailable by default
- **Zero downtime**: Seamlessly switches between normal and maintenance mode
- **Annotation-based configuration**: All settings managed through annotations

## Feature Compatibility

| Feature | Kubernetes Ingress | Traefik IngressRoute |
|---------|-------------------|---------------------|
| Enable/Disable Maintenance | ✅ Yes | ✅ Yes |
| Default Maintenance Page | ✅ Yes | ✅ Yes |
| Custom Maintenance Pages | ❌ No* | ✅ Yes |
| Content Negotiation | ✅ Yes | ✅ Yes |
| Cross-namespace Support | ✅ Yes | ✅ Yes |

*Custom pages require Traefik Middleware to inject the page selection header. Standard Ingress will always use the default maintenance page.

## How It Works

1. **Enable maintenance mode**: Add the annotation `maintenance-operator.kahf.io/enabled: "true"` to any Ingress or IngressRoute
2. **Operator takes over**: The operator detects the annotation and:
   - Stores the original service configuration in a ConfigMap
   - Redirects traffic to the maintenance page service
   - Tracks the backup state
3. **Disable maintenance mode**: Remove the annotation
4. **Automatic restore**: The operator restores the original service configuration and cleans up backups

## Installation

### Prerequisites

- Kubernetes cluster (1.19+)
- Helm 3.x
- For Traefik IngressRoute support: Traefik CRDs installed

### Quick Install (One-liner)

Install the latest version directly from GitHub:

```bash
curl -sSL https://raw.githubusercontent.com/mithucste30/maintenance-operator/main/scripts/quick-install.sh | bash
```

Or with custom settings:

```bash
VERSION=0.1.0 NAMESPACE=maintenance-operator \
  curl -sSL https://raw.githubusercontent.com/mithucste30/maintenance-operator/main/scripts/quick-install.sh | bash
```

### Install from GitHub Container Registry (Recommended)

Using OCI registry (Helm 3.8+):

```bash
# Install specific version
helm install maintenance-operator \
  oci://ghcr.io/mithucste30/charts/maintenance-operator \
  --version 0.1.0 \
  --namespace maintenance-operator \
  --create-namespace

# Install latest version
helm install maintenance-operator \
  oci://ghcr.io/mithucste30/charts/maintenance-operator \
  --namespace maintenance-operator \
  --create-namespace
```

### Install from GitHub Releases

```bash
# Set version
VERSION=0.1.0

# Install from release tarball
helm install maintenance-operator \
  https://github.com/mithucste30/maintenance-operator/releases/download/v${VERSION}/maintenance-operator-${VERSION}.tgz \
  --namespace maintenance-operator \
  --create-namespace
```

### Install Using Deployment Script

Clone the repository and use the deployment script:

```bash
git clone https://github.com/mithucste30/maintenance-operator.git
cd maintenance-operator

# Deploy with default settings
./scripts/deploy.sh

# Deploy specific version to custom namespace
./scripts/deploy.sh 0.1.0 my-namespace
```

### Install from Source (Development)

For local development or customization:

```bash
# Clone repository
git clone https://github.com/mithucste30/maintenance-operator.git
cd maintenance-operator

# Build Docker image
docker build -t maintenance-operator:dev .

# Push to your registry (optional)
docker tag maintenance-operator:dev <your-registry>/maintenance-operator:dev
docker push <your-registry>/maintenance-operator:dev

# Install from local chart
helm install maintenance-operator . \
  --namespace maintenance-operator \
  --create-namespace \
  --set image.repository=<your-registry>/maintenance-operator \
  --set image.tag=dev
```

## Usage

### Enable Maintenance Mode

For a standard Ingress:

```bash
kubectl annotate ingress my-app maintenance-operator.kahf.io/enabled=true
```

For a Traefik IngressRoute:

```bash
kubectl annotate ingressroute my-app maintenance-operator.kahf.io/enabled=true
```

### Disable Maintenance Mode

```bash
kubectl annotate ingress my-app maintenance-operator.kahf.io/enabled-
# or
kubectl annotate ingressroute my-app maintenance-operator.kahf.io/enabled-
```

### Custom Maintenance Pages

You can configure custom maintenance pages in the `values.yaml`.

**Note:** Custom pages currently work with **Traefik IngressRoute** only. For standard Kubernetes Ingress, the default maintenance page will always be used. This is because custom pages require Traefik Middleware to inject the page selection header.

#### Step 1: Add to values.yaml

```yaml
maintenance:
  customPages:
    my-app:
      html: |
        <!DOCTYPE html>
        <html>
        <head><title>My App - Under Maintenance</title></head>
        <body>
          <h1>My App is Under Maintenance</h1>
          <p>We're upgrading our systems. Back soon!</p>
        </body>
        </html>
      json: |
        {
          "status": "maintenance",
          "message": "My App is currently being upgraded",
          "estimatedDowntime": "2 hours"
        }
      xml: |
        <?xml version="1.0"?>
        <response>
          <status>maintenance</status>
          <message>My App is currently being upgraded</message>
        </response>
```

#### Step 2: Apply and use the custom page

```bash
# Upgrade the Helm release
helm upgrade maintenance-operator . -n maintenance-operator

# Enable maintenance with custom page (IngressRoute only)
kubectl annotate ingressroute my-app \
  maintenance-operator.kahf.io/enabled=true \
  maintenance-operator.kahf.io/custom-page=my-app
```

#### Switch to default page (IngressRoute only)

```bash
# Use "default" value or remove the annotation
kubectl annotate ingressroute my-app \
  maintenance-operator.kahf.io/custom-page=default --overwrite
```

### Content Negotiation

The maintenance server automatically serves the appropriate content type based on the `Accept` header:

- `Accept: text/html` → HTML page
- `Accept: application/json` → JSON response
- `Accept: application/xml` → XML response
- `Accept: */*` → HTML page (default)

## Configuration

### Values

Key configuration options in `values.yaml`:

```yaml
# Operator configuration
operator:
  # Annotation to enable maintenance mode
  maintenanceAnnotation: "maintenance-operator.kahf.io/enabled"
  maintenanceAnnotationValue: "true"

  # Annotation to specify custom maintenance page
  customPageAnnotation: "maintenance-operator.kahf.io/custom-page"

  # Internal annotations (managed by operator)
  backupAnnotation: "maintenance-operator.kahf.io/original-service"
  backupConfigMapPrefix: "maintenance-backup"

# Maintenance page configuration
maintenance:
  httpStatusCode: 503  # HTTP status code returned

  defaultPage:
    html: |
      <!DOCTYPE html>
      <html>...</html>
    json: |
      {"status": "maintenance"}
    xml: |
      <?xml version="1.0"?><response>...</response>

  customPages:
    my-app:
      html: |
        <!DOCTYPE html>
        <html>...</html>
      json: |
        {"status": "maintenance", "app": "my-app"}
      xml: |
        <?xml version="1.0"?><response>...</response>
```

## Architecture

The operator consists of two main components:

1. **Operator Controller** (kopf-based):
   - Watches Ingress and IngressRoute resources
   - Detects maintenance label changes
   - Manages backups and service switching

2. **Maintenance Page Server** (Flask-based):
   - Serves maintenance pages
   - Handles content negotiation
   - Returns proper HTTP status codes

Both run in the same pod with separate containers.

## Development

### Building the Image

```bash
docker build -t maintenance-operator:dev .
```

### Testing Locally

```bash
# Install dependencies
pip install -r app/requirements.txt

# Run the operator (requires kubectl context)
kopf run app/operator.py --verbose

# Run the maintenance server (in another terminal)
python app/maintenance_server.py
```

## Examples

### Example 1: Enable maintenance for an Ingress

```bash
# Enable maintenance mode
kubectl annotate ingress my-app maintenance-operator.kahf.io/enabled=true

# Check the backup was created
kubectl get configmap -n maintenance-operator maintenance-backup-my-app

# Disable maintenance mode to restore
kubectl annotate ingress my-app maintenance-operator.kahf.io/enabled-
```

### Example 2: Use a custom page

1. Add custom page to `values.yaml`:

```yaml
maintenance:
  customPages:
    my-special-app:
      html: |
        <!DOCTYPE html>
        <html>
        <body>
          <h1>Special Maintenance Page</h1>
          <p>We're making things better!</p>
        </body>
        </html>
      json: |
        {"status": "maintenance", "message": "Special maintenance"}
```

2. Upgrade the Helm release:

```bash
helm upgrade maintenance-operator . -n maintenance-operator
```

3. Enable maintenance with custom page:

```bash
kubectl annotate ingress my-app \
  maintenance-operator.kahf.io/enabled=true \
  maintenance-operator.kahf.io/custom-page=my-special-app
```

4. Switch to default page:

```bash
kubectl annotate ingress my-app \
  maintenance-operator.kahf.io/custom-page=default --overwrite
```

## Troubleshooting

### Check operator logs

```bash
kubectl logs -n maintenance-operator \
  deployment/maintenance-operator \
  -c operator -f
```

### Check maintenance server logs

```bash
kubectl logs -n maintenance-operator \
  deployment/maintenance-operator \
  -c server -f
```

### Verify backups

```bash
kubectl get configmap -l app=maintenance-operator
```

### Check if maintenance mode is active

```bash
kubectl get ingress my-app -o yaml | grep maintenance-operator
```

## Uninstall

### Using Uninstall Script (Recommended)

The uninstall script safely removes the operator and cleans up resources:

```bash
# Uninstall from default namespace
./scripts/uninstall.sh

# Uninstall from custom namespace
./scripts/uninstall.sh my-namespace
```

The script will:
- Check for active maintenance modes
- Optionally remove maintenance labels from resources
- Uninstall the Helm release
- Clean up backup ConfigMaps
- Optionally delete the namespace

### Manual Uninstall

```bash
# Remove maintenance annotations from all resources (optional)
kubectl annotate ingress --all maintenance-operator.kahf.io/enabled- --all-namespaces
kubectl annotate ingressroute --all maintenance-operator.kahf.io/enabled- --all-namespaces

# Uninstall Helm release
helm uninstall maintenance-operator -n maintenance-operator

# Clean up backup ConfigMaps
kubectl delete configmap -n maintenance-operator -l app=maintenance-operator

# Delete namespace (optional)
kubectl delete namespace maintenance-operator
```

## License

Copyright (c) 2024 Kahf Infrastructure Team
