#!/bin/bash
#
# Helper script to encode HTML files to base64 for use in values.yaml
#
# Usage:
#   ./scripts/encode-html.sh <html-file>
#   ./scripts/encode-html.sh maintenance.html
#

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <html-file>"
    echo ""
    echo "Examples:"
    echo "  $0 my-maintenance.html"
    echo "  $0 pages/custom-page.html"
    exit 1
fi

HTML_FILE="$1"

if [ ! -f "$HTML_FILE" ]; then
    echo "Error: File '$HTML_FILE' not found"
    exit 1
fi

echo "Encoding $HTML_FILE to base64..."
echo ""
echo "Base64 encoded output:"
echo "---"
base64 < "$HTML_FILE"
echo "---"
echo ""
echo "You can now copy this value to your values.yaml file under:"
echo "  maintenance.customPages.<name>.htmlBase64: \"<paste-here>\""
echo ""
echo "Or for the default page:"
echo "  maintenance.defaultPage.htmlBase64: \"<paste-here>\""
