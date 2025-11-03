#!/usr/bin/env python3
"""
Helper script to encode HTML files to base64 for use in values.yaml

Usage:
    python encode-html.py <html-file>
    python encode-html.py maintenance.html
"""

import base64
import sys
from pathlib import Path


def encode_html_file(file_path: str) -> str:
    """Encode HTML file to base64"""
    path = Path(file_path)

    if not path.exists():
        print(f"Error: File '{file_path}' not found", file=sys.stderr)
        sys.exit(1)

    if not path.is_file():
        print(f"Error: '{file_path}' is not a file", file=sys.stderr)
        sys.exit(1)

    # Read file content
    with open(path, 'rb') as f:
        content = f.read()

    # Encode to base64
    encoded = base64.b64encode(content).decode('utf-8')

    return encoded


def main():
    if len(sys.argv) != 2:
        print("Usage: python encode-html.py <html-file>")
        print("")
        print("Examples:")
        print("  python encode-html.py my-maintenance.html")
        print("  python encode-html.py pages/custom-page.html")
        sys.exit(1)

    html_file = sys.argv[1]

    print(f"Encoding {html_file} to base64...")
    print("")

    encoded = encode_html_file(html_file)

    print("Base64 encoded output:")
    print("---")
    print(encoded)
    print("---")
    print("")
    print("You can now copy this value to your values.yaml file under:")
    print("  maintenance.customPages.<name>.htmlBase64: \"<paste-here>\"")
    print("")
    print("Or for the default page:")
    print("  maintenance.defaultPage.htmlBase64: \"<paste-here>\"")


if __name__ == "__main__":
    main()
