#!/bin/bash
#
# Script to un-release a version
# Removes git tags, GitHub releases, container images, and Helm charts
#
# Usage: ./scripts/unrelease.sh <version>
# Example: ./scripts/unrelease.sh 0.1.0
#

set -e

# Show help
show_help() {
    cat << EOF
Unrelease Script - Remove a released version

Usage: $0 <version>

Arguments:
  version    Version to un-release (e.g., 0.1.0 or v0.1.0)

Examples:
  $0 0.1.0      # Un-release version 0.1.0
  $0 v0.2.0     # Un-release version 0.2.0 (v prefix is optional)

What it does:
  - Deletes local git tag
  - Deletes remote git tag
  - Deletes GitHub release (if gh CLI available)
  - Provides instructions for deleting container images and Helm charts
  - Optionally reverts version changes in Chart.yaml and values.yaml

Requirements:
  - Git
  - GitHub CLI (gh) - optional but recommended

Environment Variables:
  GITHUB_REPO    GitHub repository (default: mithucste30/maintenance-operator)

See also:
  RELEASING.md for more information on releases and rollbacks
EOF
}

# Parse arguments
VERSION="${1}"

if [ "$VERSION" = "-h" ] || [ "$VERSION" = "--help" ] || [ "$VERSION" = "help" ]; then
    show_help
    exit 0
fi

GITHUB_REPO="${GITHUB_REPO:-mithucste30/maintenance-operator}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
error() {
    echo -e "${RED}❌ Error: $1${NC}"
    exit 1
}

warning() {
    echo -e "${YELLOW}⚠️  Warning: $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

info() {
    echo "ℹ️  $1"
}

# Validate input
if [ -z "$VERSION" ]; then
    error "Version is required. Usage: $0 <version>"
fi

# Remove 'v' prefix if present
VERSION="${VERSION#v}"
TAG_NAME="v${VERSION}"

echo ""
echo "🗑️  Un-releasing version ${VERSION}"
echo "=================================="
echo ""

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    error "Not in a git repository"
fi

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    warning "GitHub CLI (gh) is not installed. Some operations will be skipped."
    warning "Install with: brew install gh (macOS) or see https://cli.github.com/"
    GH_AVAILABLE=false
else
    GH_AVAILABLE=true

    # Check if authenticated
    if ! gh auth status &> /dev/null; then
        warning "Not authenticated with GitHub CLI. Run: gh auth login"
        GH_AVAILABLE=false
    fi
fi

# Confirm deletion
echo "This will delete:"
echo "  - Local git tag: ${TAG_NAME}"
echo "  - Remote git tag: ${TAG_NAME}"
if [ "$GH_AVAILABLE" = true ]; then
    echo "  - GitHub Release: ${TAG_NAME}"
    echo "  - Container image: ghcr.io/${GITHUB_REPO}:${VERSION}"
    echo "  - Helm chart: oci://ghcr.io/${GITHUB_REPO%/*}/charts/${GITHUB_REPO##*/}:${VERSION}"
fi
echo ""

read -p "Are you sure you want to continue? (yes/no) " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""

# Step 1: Delete local git tag
info "Deleting local git tag..."
if git tag -d "$TAG_NAME" 2>/dev/null; then
    success "Deleted local tag: ${TAG_NAME}"
else
    warning "Local tag ${TAG_NAME} not found (may already be deleted)"
fi

# Step 2: Delete remote git tag
info "Deleting remote git tag..."
if git push --delete origin "$TAG_NAME" 2>/dev/null; then
    success "Deleted remote tag: ${TAG_NAME}"
else
    warning "Remote tag ${TAG_NAME} not found on origin (may already be deleted)"
fi

# Step 3: Delete GitHub Release (if gh CLI is available)
if [ "$GH_AVAILABLE" = true ]; then
    echo ""
    info "Deleting GitHub Release..."

    if gh release delete "$TAG_NAME" --yes --cleanup-tag 2>/dev/null; then
        success "Deleted GitHub Release: ${TAG_NAME}"
    else
        warning "GitHub Release ${TAG_NAME} not found (may already be deleted)"
    fi

    # Step 4: Delete container image from GHCR
    echo ""
    info "Deleting container image from GitHub Container Registry..."
    info "Image: ghcr.io/${GITHUB_REPO}:${VERSION}"

    # Try to delete the package version
    # Note: This requires the gh cli extension or manual deletion via GitHub UI
    warning "Container image deletion requires manual action or GitHub API"
    echo ""
    echo "To delete the container image, visit:"
    echo "  https://github.com/${GITHUB_REPO%/*}/packages/container/${GITHUB_REPO##*/}/versions"
    echo ""
    echo "Or use the GitHub API:"
    echo "  gh api -X DELETE /user/packages/container/${GITHUB_REPO##*/}/versions/VERSION_ID"
    echo ""

    # Step 5: Delete Helm chart from GHCR
    info "Deleting Helm chart from GitHub Container Registry..."
    info "Chart: oci://ghcr.io/${GITHUB_REPO%/*}/charts/${GITHUB_REPO##*/}:${VERSION}"

    warning "Helm chart deletion requires manual action"
    echo ""
    echo "To delete the Helm chart, visit:"
    echo "  https://github.com/${GITHUB_REPO%/*}/packages/container/charts%2F${GITHUB_REPO##*/}/versions"
    echo ""
    echo "Or use the GitHub API:"
    echo "  gh api -X DELETE /user/packages/container/charts%2F${GITHUB_REPO##*/}/versions/VERSION_ID"
    echo ""

else
    echo ""
    warning "GitHub CLI not available. Manual steps required:"
    echo ""
    echo "1. Delete GitHub Release:"
    echo "   Visit: https://github.com/${GITHUB_REPO}/releases/tag/${TAG_NAME}"
    echo "   Click 'Delete' and confirm"
    echo ""
    echo "2. Delete container image:"
    echo "   Visit: https://github.com/${GITHUB_REPO%/*}/packages/container/${GITHUB_REPO##*/}/versions"
    echo "   Find version ${VERSION} and delete it"
    echo ""
    echo "3. Delete Helm chart:"
    echo "   Visit: https://github.com/${GITHUB_REPO%/*}/packages/container/charts%2F${GITHUB_REPO##*/}/versions"
    echo "   Find version ${VERSION} and delete it"
    echo ""
fi

# Step 6: Optionally revert version changes in Chart.yaml and values.yaml
echo ""
read -p "Do you want to revert version changes in Chart.yaml and values.yaml? (y/n) " -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Check if there's a commit with the version bump
    COMMIT_MSG="chore: bump version to ${VERSION}"

    if git log --oneline --all | grep -q "$COMMIT_MSG"; then
        info "Found version bump commit. Attempting to revert..."

        # Find the commit hash
        COMMIT_HASH=$(git log --all --oneline --grep="$COMMIT_MSG" -1 --format="%H")

        if [ -n "$COMMIT_HASH" ]; then
            info "Reverting commit: $COMMIT_HASH"

            # Revert the commit
            git revert "$COMMIT_HASH" --no-edit

            success "Reverted version bump commit"

            read -p "Push the revert to remote? (y/n) " -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
                git push origin "$CURRENT_BRANCH"
                success "Pushed revert to origin/$CURRENT_BRANCH"
            fi
        else
            warning "Could not find commit hash for version bump"
        fi
    else
        warning "Version bump commit not found. You may need to manually update Chart.yaml and values.yaml"
        echo ""
        echo "To manually update versions, edit:"
        echo "  - Chart.yaml (version and appVersion)"
        echo "  - values.yaml (image.tag)"
    fi
fi

echo ""
echo "=================================="
success "Un-release process completed!"
echo ""

# Show summary
echo "Summary:"
echo "  ✓ Local tag ${TAG_NAME} deleted"
echo "  ✓ Remote tag ${TAG_NAME} deleted"

if [ "$GH_AVAILABLE" = true ]; then
    echo "  ⚠ GitHub Release deletion attempted"
    echo "  ⚠ Manual cleanup required for container images and Helm charts"
else
    echo "  ⚠ Manual cleanup required for GitHub Release, images, and charts"
fi

echo ""
echo "Cleanup checklist:"
echo "  [ ] Verify tag is removed: git tag -l | grep ${VERSION}"
echo "  [ ] Check GitHub releases: https://github.com/${GITHUB_REPO}/releases"
echo "  [ ] Check container images: https://github.com/${GITHUB_REPO%/*}/packages"
echo "  [ ] Verify Chart.yaml and values.yaml versions are correct"
echo ""
