# Contributing to Maintenance Operator

Thank you for your interest in contributing to Maintenance Operator! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Docker
- Kubernetes cluster (local or remote)
- kubectl configured
- Helm 3.x
- Python 3.11+
- Git

### Local Development

1. **Clone the repository**

```bash
git clone https://github.com/mithucste30/maintenance-operator.git
cd maintenance-operator
```

2. **Install Python dependencies**

```bash
pip install -r app/requirements.txt
```

3. **Run the operator locally**

```bash
# Terminal 1: Run the operator
kopf run app/operator.py --verbose

# Terminal 2: Run the maintenance server
python app/maintenance_server.py
```

4. **Build Docker image**

```bash
docker build -t maintenance-operator:dev .
```

5. **Test with local Kubernetes**

```bash
# Use kind or minikube
kind create cluster --name maintenance-test

# Load image into kind
kind load docker-image maintenance-operator:dev --name maintenance-test

# Install from local chart
helm install maintenance-operator . \
  --namespace maintenance-operator \
  --create-namespace \
  --set image.repository=maintenance-operator \
  --set image.tag=dev \
  --set image.pullPolicy=Never
```

## Making Changes

### Branch Strategy

- `main` - Production-ready code
- `develop` - Development branch (if used)
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `hotfix/*` - Urgent production fixes

### Workflow

1. **Create a feature branch**

```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes**

3. **Test your changes**

```bash
# Lint Helm chart
helm lint .

# Test template rendering
helm template maintenance-operator . --namespace test

# Run Python linting
flake8 app/*.py --max-line-length=120
```

4. **Commit your changes**

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Format: <type>(<scope>): <description>

git commit -m "feat: add support for custom error pages"
git commit -m "fix: resolve issue with backup restoration"
git commit -m "docs: update installation instructions"
git commit -m "chore: update dependencies"
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

5. **Push and create Pull Request**

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Pull Request Guidelines

### PR Title

Use conventional commit format:
- `feat: add new feature`
- `fix: resolve bug`
- `docs: update documentation`

### PR Description

Include:
- **What**: What changes are being made
- **Why**: Why the changes are needed
- **How**: How the changes are implemented
- **Testing**: How to test the changes
- **Screenshots**: If applicable

Example:
```markdown
## What
Adds support for custom maintenance pages per namespace.

## Why
Users need different maintenance pages for different applications.

## How
- Modified operator to check for namespace-specific ConfigMaps
- Updated values.yaml schema
- Added validation

## Testing
1. Deploy operator
2. Create custom page ConfigMap
3. Apply maintenance label
4. Verify custom page is served

## Checklist
- [x] Tests pass
- [x] Documentation updated
- [x] Helm chart lints
```

### Checklist

- [ ] Code follows project style
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Helm chart lints successfully
- [ ] Commit messages follow conventional format
- [ ] PR description is clear and complete

## CI/CD Pipeline

### Automated Checks

When you create a PR, the following checks run automatically:

1. **Lint and Test** (`.github/workflows/lint-test.yaml`)
   - Helm chart linting
   - Template validation
   - Kubernetes manifest validation
   - Python code linting

2. **Docker Build** (`.github/workflows/build-and-push.yaml`)
   - Multi-platform build test
   - Image is NOT pushed for PRs

### Continuous Integration

On push to `main` or `develop`:
- Docker images are built and pushed to GHCR
- Tagged with branch name

### Release Process

On tag push (`v*`):
1. Docker image built and pushed with version tag
2. Helm chart packaged and released
3. GitHub Release created
4. OCI Helm chart pushed

See [RELEASE.md](RELEASE.md) for detailed release instructions.

## Testing

### Helm Chart Testing

```bash
# Lint chart
helm lint .

# Template test
helm template test . --namespace test > rendered.yaml

# Dry run install
helm install test . --dry-run --debug

# Install in test namespace
helm install test . --namespace test --create-namespace
```

### Operator Testing

```bash
# Run operator locally against test cluster
kopf run app/operator.py --namespace test --verbose

# Create test ingress
kubectl create ingress test --rule="test.example.com/*=test-svc:80"

# Apply maintenance label
kubectl label ingress test under-maintenance=true

# Verify
kubectl get ingress test -o yaml
kubectl get configmap -l app=maintenance-operator

# Remove label
kubectl label ingress test under-maintenance-
```

### Python Testing

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests (when added)
pytest app/tests/

# With coverage
pytest --cov=app app/tests/
```

## Code Style

### Python

- Follow PEP 8
- Maximum line length: 120 characters
- Use type hints where applicable
- Add docstrings to functions

```python
def example_function(param: str) -> dict:
    """
    Brief description.

    Args:
        param: Description of parameter

    Returns:
        Description of return value
    """
    pass
```

### Helm Templates

- Use 2 spaces for indentation
- Add comments for complex logic
- Use helpers for repeated patterns
- Follow [Helm best practices](https://helm.sh/docs/chart_best_practices/)

### YAML Files

- Use 2 spaces for indentation
- Keep lines under 120 characters
- Add comments for clarity

## Documentation

When making changes, update relevant documentation:

- **README.md** - Main documentation
- **values.yaml** - Chart configuration comments
- **RELEASE.md** - Release process changes
- **CONTRIBUTING.md** - This file

### Documentation Style

- Use clear, concise language
- Include code examples
- Add screenshots when helpful
- Keep examples up to date

## Reporting Issues

### Bug Reports

Include:
- Kubernetes version
- Helm version
- Operator version
- Steps to reproduce
- Expected behavior
- Actual behavior
- Logs (operator and server)

### Feature Requests

Include:
- Use case description
- Proposed solution
- Alternative solutions considered
- Additional context

## Community

- Be respectful and inclusive
- Help others learn
- Provide constructive feedback
- Follow the code of conduct (if available)

## Questions?

- Open an issue for questions
- Check existing issues first
- Provide context in your question

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

Thank you for contributing! 🎉
