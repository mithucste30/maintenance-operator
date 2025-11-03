#!/bin/bash
#
# Simple release script for Maintenance Operator
# Usage: ./release.sh <version>
# Example: ./release.sh 0.1.0
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check arguments
if [ -z "$1" ]; then
    echo -e "${RED}Error: Version number required${NC}"
    echo ""
    echo "Usage: ./release.sh <version>"
    echo ""
    echo "Examples:"
    echo "  ./release.sh 0.1.0    # First release"
    echo "  ./release.sh 0.1.1    # Patch release"
    echo "  ./release.sh 0.2.0    # Minor release"
    echo "  ./release.sh 1.0.0    # Major release"
    exit 1
fi

VERSION="$1"

# Validate version format (semver)
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo -e "${RED}Error: Invalid version format${NC}"
    echo "Version must be in format: X.Y.Z (e.g., 0.1.0)"
    exit 1
fi

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Maintenance Operator Release Script  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Version:${NC} ${YELLOW}v${VERSION}${NC}"
echo ""

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}✗ Error: Not in a git repository${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Git repository detected"

# Check if tag already exists
if git rev-parse "v${VERSION}" >/dev/null 2>&1; then
    echo -e "${RED}✗ Error: Tag v${VERSION} already exists${NC}"
    echo ""
    echo "Existing tags:"
    git tag -l | tail -5
    exit 1
fi
echo -e "${GREEN}✓${NC} Tag v${VERSION} is available"

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}⚠ Warning: You have uncommitted changes${NC}"
    git status --short
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Release cancelled${NC}"
        exit 0
    fi
fi

# Get current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo -e "${BLUE}Branch:${NC} $CURRENT_BRANCH"

if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${YELLOW}⚠ Warning: You're on branch '$CURRENT_BRANCH', not 'main'${NC}"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Release cancelled${NC}"
        exit 0
    fi
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}Updating version files...${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"

# Update Chart.yaml
if [ -f Chart.yaml ]; then
    sed -i.bak "s/^version:.*/version: ${VERSION}/" Chart.yaml
    sed -i.bak "s/^appVersion:.*/appVersion: \"${VERSION}\"/" Chart.yaml
    rm -f Chart.yaml.bak
    echo -e "${GREEN}✓${NC} Updated Chart.yaml"
else
    echo -e "${RED}✗ Error: Chart.yaml not found${NC}"
    exit 1
fi

# Update values.yaml
if [ -f values.yaml ]; then
    sed -i.bak "s/tag: \".*\"/tag: \"${VERSION}\"/" values.yaml
    rm -f values.yaml.bak
    echo -e "${GREEN}✓${NC} Updated values.yaml"
else
    echo -e "${RED}✗ Error: values.yaml not found${NC}"
    exit 1
fi

# Show changes
echo ""
echo -e "${BLUE}Changes:${NC}"
git diff Chart.yaml values.yaml

echo ""
read -p "Commit these changes? (Y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo -e "${YELLOW}Changes not committed. Rolling back...${NC}"
    git checkout Chart.yaml values.yaml
    exit 0
fi

# Commit changes
git add Chart.yaml values.yaml
git commit -m "chore: release v${VERSION}" --no-verify

echo -e "${GREEN}✓${NC} Changes committed"

# Create tag
echo ""
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}Creating release tag...${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"

git tag -a "v${VERSION}" -m "Release v${VERSION}"
echo -e "${GREEN}✓${NC} Tag v${VERSION} created"

# Push to remote
echo ""
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}Pushing to remote...${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"

echo ""
read -p "Push to remote now? (Y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo ""
    echo -e "${YELLOW}Not pushed to remote.${NC}"
    echo ""
    echo "To push manually:"
    echo -e "  ${GREEN}git push origin $CURRENT_BRANCH${NC}"
    echo -e "  ${GREEN}git push origin v${VERSION}${NC}"
    exit 0
fi

# Push branch and tag
git push origin "$CURRENT_BRANCH"
echo -e "${GREEN}✓${NC} Pushed branch: $CURRENT_BRANCH"

git push origin "v${VERSION}"
echo -e "${GREEN}✓${NC} Pushed tag: v${VERSION}"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║        Release Created Successfully!   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}What happens next:${NC}"
echo ""
echo -e "  1. ${YELLOW}GitHub Actions will start building...${NC}"
echo -e "     • Docker image (multi-arch)"
echo -e "     • Helm chart package"
echo -e "     • GitHub Release"
echo ""
echo -e "  2. ${YELLOW}Artifacts will be published to:${NC}"
echo -e "     • Docker: ${GREEN}ghcr.io/mithucste30/maintenance-operator:${VERSION}${NC}"
echo -e "     • Helm: ${GREEN}oci://ghcr.io/mithucste30/charts/maintenance-operator:${VERSION}${NC}"
echo -e "     • Release: ${GREEN}https://github.com/mithucste30/maintenance-operator/releases/tag/v${VERSION}${NC}"
echo ""
echo -e "  3. ${YELLOW}Monitor progress:${NC}"
echo -e "     • ${BLUE}https://github.com/mithucste30/maintenance-operator/actions${NC}"
echo ""
echo -e "${BLUE}After completion (3-5 minutes):${NC}"
echo ""
echo -e "  ${GREEN}# Install from OCI registry${NC}"
echo -e "  helm install maintenance-operator \\"
echo -e "    oci://ghcr.io/mithucste30/charts/maintenance-operator \\"
echo -e "    --version ${VERSION} \\"
echo -e "    --namespace maintenance-operator \\"
echo -e "    --create-namespace"
echo ""
echo -e "${YELLOW}Don't forget to make packages public on first release!${NC}"
echo -e "  https://github.com/mithucste30?tab=packages"
echo ""
