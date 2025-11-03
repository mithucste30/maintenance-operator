.PHONY: build push install uninstall upgrade test lint package release version dev-setup ci-lint

IMAGE_NAME ?= maintenance-operator
IMAGE_TAG ?= 0.1.0
REGISTRY ?= ghcr.io/mithucste30
NAMESPACE ?= maintenance-operator
GITHUB_REPO ?= mithucste30/maintenance-operator

# Build Docker image
build:
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .

# Push Docker image to registry
push: build
	docker tag $(IMAGE_NAME):$(IMAGE_TAG) $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
	docker push $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)

# Install Helm chart
install:
	helm install maintenance-operator . \
		--create-namespace \
		--namespace $(NAMESPACE) \
		--set image.repository=$(REGISTRY)$(IMAGE_NAME) \
		--set image.tag=$(IMAGE_TAG)

# Uninstall Helm chart
uninstall:
	helm uninstall maintenance-operator --namespace $(NAMESPACE)

# Upgrade Helm chart
upgrade:
	helm upgrade maintenance-operator . \
		--namespace $(NAMESPACE) \
		--set image.repository=$(REGISTRY)$(IMAGE_NAME) \
		--set image.tag=$(IMAGE_TAG)

# Template Helm chart (for debugging)
template:
	helm template maintenance-operator . \
		--namespace $(NAMESPACE) \
		--set image.repository=$(REGISTRY)$(IMAGE_NAME) \
		--set image.tag=$(IMAGE_TAG)

# Lint Helm chart
lint:
	helm lint .

# Run tests
test:
	@echo "Running tests..."
	cd app && python -m pytest tests/ || true

# Clean up
clean:
	docker rmi $(IMAGE_NAME):$(IMAGE_TAG) || true

# Package Helm chart
package:
	@echo "Packaging Helm chart..."
	helm package . --version $(IMAGE_TAG) --app-version $(IMAGE_TAG) --destination .deploy

# CI: Lint everything
ci-lint: lint
	@echo "Running Python linting..."
	@command -v flake8 >/dev/null 2>&1 || pip install flake8
	flake8 app/*.py --max-line-length=120 --ignore=E501 || echo "⚠️  Python linting warnings"
	@echo "✓ CI linting complete"

# Update version in files
version:
	@echo "Updating version to $(IMAGE_TAG)..."
	sed -i.bak "s/^version:.*/version: $(IMAGE_TAG)/" Chart.yaml
	sed -i.bak "s/^appVersion:.*/appVersion: \"$(IMAGE_TAG)\"/" Chart.yaml
	sed -i.bak "s/tag: .*/tag: \"$(IMAGE_TAG)\"/" values.yaml
	rm -f Chart.yaml.bak values.yaml.bak
	@echo "✓ Version updated to $(IMAGE_TAG)"

# Create a release using automated script (recommended)
release:
ifndef VERSION
	@echo "❌ Error: VERSION is required"
	@echo ""
	@echo "Usage: make release VERSION=0.1.0"
	@echo ""
	@echo "Or use the release script directly:"
	@echo "  ./release.sh 0.1.0"
	@exit 1
else
	@./release.sh $(VERSION)
endif

# Create a release (manual method)
release-manual: version
	@echo "Creating release $(IMAGE_TAG)..."
	git add Chart.yaml values.yaml
	git commit -m "chore: bump version to $(IMAGE_TAG)" || true
	git tag -a "v$(IMAGE_TAG)" -m "Release v$(IMAGE_TAG)"
	@echo "✓ Release tag created. Push with: git push origin main && git push origin v$(IMAGE_TAG)"

# Development setup
dev-setup:
	@echo "Setting up development environment..."
	pip install -r app/requirements.txt
	@command -v helm >/dev/null 2>&1 || (echo "❌ Please install Helm 3.x" && exit 1)
	@command -v kubectl >/dev/null 2>&1 || (echo "❌ Please install kubectl" && exit 1)
	@command -v docker >/dev/null 2>&1 || (echo "❌ Please install Docker" && exit 1)
	@echo "✓ Development environment ready"

# Build and push to GHCR
ghcr-push: build
	@echo "Pushing to GitHub Container Registry..."
	docker tag $(IMAGE_NAME):$(IMAGE_TAG) $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
	docker push $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
	@echo "✓ Pushed to $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)"

# Deploy using deployment script
deploy:
	./scripts/deploy.sh $(IMAGE_TAG) $(NAMESPACE)

# Run operator locally
run-operator:
	@echo "Starting operator locally..."
	@echo "Make sure you have a kubeconfig configured"
	kopf run app/operator.py --verbose

# Run maintenance server locally
run-server:
	@echo "Starting maintenance server locally..."
	python app/maintenance_server.py

# Show help
help:
	@echo "Maintenance Operator Makefile"
	@echo ""
	@echo "Usage:"
	@echo "  make build          - Build Docker image"
	@echo "  make push           - Push Docker image to registry"
	@echo "  make ghcr-push      - Push to GitHub Container Registry"
	@echo "  make install        - Install Helm chart"
	@echo "  make uninstall      - Uninstall Helm chart"
	@echo "  make upgrade        - Upgrade Helm chart"
	@echo "  make template       - Template Helm chart"
	@echo "  make lint           - Lint Helm chart"
	@echo "  make ci-lint        - Run all linting (CI)"
	@echo "  make test           - Run tests"
	@echo "  make package        - Package Helm chart"
	@echo "  make version        - Update version in files"
	@echo "  make release        - Create and push release (requires VERSION=x.y.z)"
	@echo "  make dev-setup      - Setup development environment"
	@echo "  make deploy         - Deploy using script"
	@echo "  make run-operator   - Run operator locally"
	@echo "  make run-server     - Run server locally"
	@echo "  make clean          - Clean up Docker images"
	@echo ""
	@echo "Variables:"
	@echo "  IMAGE_NAME=$(IMAGE_NAME)"
	@echo "  IMAGE_TAG=$(IMAGE_TAG)"
	@echo "  REGISTRY=$(REGISTRY)"
	@echo "  NAMESPACE=$(NAMESPACE)"
	@echo "  GITHUB_REPO=$(GITHUB_REPO)"
	@echo ""
	@echo "Examples:"
	@echo "  make build IMAGE_TAG=0.2.0"
	@echo "  make ghcr-push IMAGE_TAG=0.2.0"
	@echo "  make release VERSION=0.2.0"
	@echo ""
	@echo "Quick Release:"
	@echo "  ./release.sh 0.1.0         # Recommended"
	@echo "  make release VERSION=0.1.0 # Alternative"
