# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Fixed Dockerfile user creation conflict with existing `operator` group
  - Changed from `operator` user to `appuser` to avoid base image conflicts
  - Added explicit group creation with error handling
- Fixed GitHub Actions build workflow
  - Added missing `id: build` to docker build step
  - Added required permissions: `id-token: write`, `attestations: write`
  - Made attestation step continue-on-error to prevent workflow blocking
- Fixed Helm chart publishing workflow
  - Added `mkdir -p .deploy` to ensure directory exists
  - Improved error handling in OCI push step
  - Added verification step for chart file existence
- Fixed OCI registry paths inconsistency
  - Standardized on `oci://ghcr.io/mithucste30/charts/maintenance-operator`
  - Updated all documentation (README, QUICKSTART, DEPLOYMENT, scripts)
- Fixed deployment script to handle local charts
  - Auto-detects if running from repository directory
  - Falls back to local chart when OCI/GitHub releases unavailable
  - Improved error messages with helpful suggestions

### Added
- Created `DEPLOYMENT.md` with comprehensive deployment guide
- Created `QUICKSTART.md` for first-time users
- Created `scripts/create-release.sh` for automated releases
- Created `CHANGELOG.md` to track changes
- Added support for base64-encoded HTML in values.yaml
- Created helper scripts: `encode-html.sh` and `encode-html.py`
- Added GitHub Actions workflows:
  - `build-and-push.yaml` - Docker image CI/CD
  - `release-chart.yaml` - Helm chart publishing
  - `lint-test.yaml` - Quality checks

### Changed
- HTML in `values.yaml` is now base64-encoded for cleaner configuration
- Deployment script now tries multiple sources in order: OCI → GitHub Release → Local Chart
- Updated Makefile with new targets: `ghcr-push`, `ci-lint`, `release`, `dev-setup`

## [0.1.0] - TBD

### Added
- Initial release
- Kubernetes operator for maintenance mode management
- Support for Ingress and Traefik IngressRoute resources
- Maintenance page server with HTML/JSON/XML support
- Content negotiation based on Accept headers
- Custom maintenance pages per ingress
- Automatic backup and restore of original configurations
- Base64-encoded HTML for clean values.yaml
- Helm chart for deployment
- Complete CI/CD with GitHub Actions
- Docker images for amd64 and arm64
- OCI registry support for Helm charts
- Comprehensive documentation

### Features
- Label-based activation: `under-maintenance: "true"`
- Automatic service backup to ConfigMaps
- Configurable HTTP status codes (default: 503)
- Custom maintenance pages per resource
- Multiple response formats (HTML/JSON/XML)
- Zero-downtime switching
- RBAC-compliant
- Multi-architecture Docker images

[Unreleased]: https://github.com/mithucste30/maintenance-operator/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/mithucste30/maintenance-operator/releases/tag/v0.1.0
