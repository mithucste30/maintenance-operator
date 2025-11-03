# Maintenance Operator

A Kubernetes operator that manages maintenance mode for Ingress and IngressRoute (Traefik) resources. When you add a label to an Ingress or IngressRoute, the operator automatically redirects traffic to a maintenance page.

## Features

- **Automatic maintenance mode**: Simply add a label to enable maintenance
- **Works with standard Ingress and Traefik IngressRoute** resources
- **Multiple content types**: Serves HTML, JSON, and XML based on client Accept headers
- **Custom maintenance pages**: Configure different pages for different services
- **Automatic backup and restore**: Original service configuration is stored and restored automatically
- **Proper HTTP status codes**: Returns 503 Service Unavailable by default
- **Zero downtime**: Seamlessly switches between normal and maintenance mode

## How It Works

1. **Enable maintenance mode**: Add the label `under-maintenance: "true"` to any Ingress or IngressRoute
2. **Operator takes over**: The operator detects the label and:
   - Stores the original service configuration in a ConfigMap
   - Redirects traffic to the maintenance page service
   - Adds an annotation to track the backup
3. **Disable maintenance mode**: Remove the label
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
kubectl label ingress my-app under-maintenance=true
```

For a Traefik IngressRoute:

```bash
kubectl label ingressroute my-app under-maintenance=true
```

### Disable Maintenance Mode

```bash
kubectl label ingress my-app under-maintenance-
# or
kubectl label ingressroute my-app under-maintenance-
```

### Custom Maintenance Pages

You can configure custom maintenance pages in the `values.yaml`. HTML content must be base64 encoded to keep the values file clean.

#### Step 1: Create your HTML file

```bash
cat > my-maintenance.html <<'EOF'
<!DOCTYPE html>
<html>
<head><title>My App - Under Maintenance</title></head>
<body>
  <h1>My App is Under Maintenance</h1>
  <p>We're upgrading our systems. Back soon!</p>
</body>
</html>
EOF
```

#### Step 2: Encode the HTML to base64

```bash
# Using the provided script (recommended)
./scripts/encode-html.sh my-maintenance.html

# Or manually with base64 command
base64 < my-maintenance.html

# Or using Python script
python scripts/encode-html.py my-maintenance.html
```

#### Step 3: Add to values.yaml

```yaml
maintenance:
  customPages:
    my-app:
      # Base64 encoded HTML
      htmlBase64: "PCFET0NUWVBFIGh0bWw+CjxodG1sPgo8aGVhZD48dGl0bGU+TXkgQXBwIC0gVW5kZXIgTWFpbnRlbmFuY2U8L3RpdGxlPjwvaGVhZD4KPGJvZHk+CiAgPGgxPk15IEFwcCBpcyBVbmRlciBNYWludGVuYW5jZTwvaDE+CiAgPHA+V2UncmUgdXBncmFkaW5nIG91ciBzeXN0ZW1zLiBCYWNrIHNvb24hPC9wPgo8L2JvZHk+CjwvaHRtbD4K"
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

#### Step 4: Apply and use the custom page

```bash
# Upgrade the Helm release
helm upgrade maintenance-operator .

# Enable maintenance with custom page
kubectl label ingress my-app under-maintenance=true
kubectl annotate ingress my-app \
  maintenance-operator.kahf.io/custom-page=my-app
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
  maintenanceLabel: "under-maintenance"
  maintenanceLabelValue: "true"
  backupAnnotation: "maintenance-operator.kahf.io/original-service"
  customPageAnnotation: "maintenance-operator.kahf.io/custom-page"

# Maintenance page configuration
maintenance:
  httpStatusCode: 503  # HTTP status code returned
  defaultPage:
    # HTML must be base64 encoded
    htmlBase64: "PCFET0NUWVBFIGh0bWw+Li4u"  # Your base64 encoded HTML
    json: |
      {"status": "maintenance"}
    xml: |
      <?xml version="1.0"?><response>...</response>
```

**Note:** HTML content must be base64 encoded. Use the provided helper scripts:
- `./scripts/encode-html.sh <file.html>`
- `python scripts/encode-html.py <file.html>`

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
# Apply the label
kubectl label ingress my-app under-maintenance=true

# Check the backup was created
kubectl get configmap maintenance-backup-my-app

# Remove the label to restore
kubectl label ingress my-app under-maintenance-
```

### Example 2: Use a custom page

1. Create and encode your custom HTML:

```bash
# Create HTML file
cat > special-page.html <<'EOF'
<html><body><h1>Special Maintenance Page</h1></body></html>
EOF

# Encode to base64
./scripts/encode-html.sh special-page.html
# Copy the output
```

2. Add custom page to `values.yaml`:

```yaml
maintenance:
  customPages:
    my-special-app:
      htmlBase64: "PGh0bWw+PGJvZHk+PGgxPlNwZWNpYWwgTWFpbnRlbmFuY2UgUGFnZTwvaDE+PC9ib2R5PjwvaHRtbD4K"
```

3. Upgrade the Helm release:

```bash
helm upgrade maintenance-operator .
```

4. Apply the label and annotation:

```bash
kubectl label ingress my-app under-maintenance=true
kubectl annotate ingress my-app \
  maintenance-operator.kahf.io/custom-page=my-special-app
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
# Remove maintenance labels from all resources (optional)
kubectl label ingress --all under-maintenance- --all-namespaces
kubectl label ingressroute --all under-maintenance- --all-namespaces

# Uninstall Helm release
helm uninstall maintenance-operator -n maintenance-operator

# Clean up backup ConfigMaps
kubectl delete configmap -n maintenance-operator -l app=maintenance-operator

# Delete namespace (optional)
kubectl delete namespace maintenance-operator
```

## License

Copyright (c) 2024 Kahf Infrastructure Team
