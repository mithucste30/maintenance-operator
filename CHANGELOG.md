# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.5] - 2026-03-05

### Fixed
- **Critical RBAC fix for Traefik IngressRoute support**
  - Added missing `coordination.k8s.io` permissions for `leases` resource
  - Added `pods/status` permissions for proper pod monitoring
  - Fixed permission errors when watching IngressRoutes at cluster scope
  - Error: "User cannot list resource 'ingressroutes' in API group 'traefik.io' at cluster scope"

### Added
- Created `RBAC_SETUP.md` with comprehensive troubleshooting guide
- Created `scripts/check-rbac.sh` for automated RBAC diagnostics
- Added RBAC troubleshooting section to README.md
- Enhanced ClusterRole with Kopf framework coordination permissions

### Changed
- Improved RBAC documentation and error resolution guidance
- Updated troubleshooting section with RBAC-specific solutions

## [2.0.4] - 2025-XX-XX

### Added
- Dockerfile user creation conflict with existing `operator` group
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

[Unreleased]: https://github.com/mithucste30/maintenance-operator/compare/v2.0.4...v2.0.5
[2.0.5]: https://github.com/mithucste30/maintenance-operator/releases/tag/v2.0.5
[2.0.4]: https://github.com/mithucste30/maintenance-operator/releases/tag/v2.0.4
