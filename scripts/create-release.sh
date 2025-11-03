#!/bin/bash
#
# Helper script to create a new release
# This will trigger the GitHub Actions workflow to publish everything
#

set -e

VERSION="${1:-0.1.0}"

echo "🚀 Creating release v${VERSION}"
echo ""

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "⚠️  Warning: You have uncommitted changes"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Make sure we're on main branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "⚠️  Warning: You're on branch '$CURRENT_BRANCH', not 'main'"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update version in files
echo "📝 Updating version to ${VERSION}..."
sed -i.bak "s/^version:.*/version: ${VERSION}/" Chart.yaml
sed -i.bak "s/^appVersion:.*/appVersion: \"${VERSION}\"/" Chart.yaml
sed -i.bak "s/tag: .*/tag: \"${VERSION}\"/" values.yaml
rm -f Chart.yaml.bak values.yaml.bak

echo "✓ Version updated"
echo ""

# Show changes
echo "📋 Changes:"
git diff Chart.yaml values.yaml
echo ""

# Commit changes
read -p "Commit these changes? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git add Chart.yaml values.yaml
    git commit -m "chore: bump version to ${VERSION}"
    echo "✓ Changes committed"
    echo ""
fi

# Create and push tag
read -p "Create and push tag v${VERSION}? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git tag -a "v${VERSION}" -m "Release v${VERSION}"
    echo "✓ Tag created"
    echo ""

    echo "🔄 Pushing changes..."
    git push origin $CURRENT_BRANCH
    git push origin "v${VERSION}"

    echo ""
    echo "✅ Release created successfully!"
    echo ""
    echo "GitHub Actions will now:"
    echo "  1. Build and push Docker image to ghcr.io/mithucste30/maintenance-operator:${VERSION}"
    echo "  2. Package and release Helm chart"
    echo "  3. Push Helm chart to oci://ghcr.io/mithucste30/charts/maintenance-operator"
    echo "  4. Create GitHub Release at https://github.com/mithucste30/maintenance-operator/releases"
    echo ""
    echo "Check the workflow status:"
    echo "  https://github.com/mithucste30/maintenance-operator/actions"
    echo ""
    echo "After the workflow completes (3-5 minutes), you can install with:"
    echo "  helm install maintenance-operator \\"
    echo "    oci://ghcr.io/mithucste30/charts/maintenance-operator \\"
    echo "    --version ${VERSION} \\"
    echo "    --namespace maintenance-operator \\"
    echo "    --create-namespace"
else
    echo ""
    echo "❌ Cancelled. To create the tag manually:"
    echo "  git tag -a \"v${VERSION}\" -m \"Release v${VERSION}\""
    echo "  git push origin main"
    echo "  git push origin \"v${VERSION}\""
fi
