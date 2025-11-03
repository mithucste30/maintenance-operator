#!/usr/bin/env python3
"""
Maintenance Page Server
Serves maintenance pages in different formats (HTML, JSON, XML) based on Accept headers
"""

import os
import logging
from flask import Flask, request, Response
from kubernetes import client, config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Load Kubernetes config
try:
    config.load_incluster_config()
except:
    config.load_kube_config()

v1 = client.CoreV1Api()

# Configuration
NAMESPACE = os.getenv('POD_NAMESPACE', 'default')
HTTP_STATUS_CODE = int(os.getenv('HTTP_STATUS_CODE', '503'))
DEFAULT_HTML = os.getenv('DEFAULT_HTML', '')
DEFAULT_JSON = os.getenv('DEFAULT_JSON', '{"status":"maintenance","message":"Service under maintenance","code":503}')
DEFAULT_XML = os.getenv('DEFAULT_XML', '<?xml version="1.0"?><response><status>maintenance</status></response>')


def get_custom_page(page_name, content_type):
    """
    Retrieve custom maintenance page from ConfigMap
    """
    try:
        # Try to get custom page ConfigMap
        cm_name = f"maintenance-page-{page_name}"
        cm = v1.read_namespaced_config_map(cm_name, NAMESPACE)

        if content_type == 'json':
            return cm.data.get('page.json')
        elif content_type == 'xml':
            return cm.data.get('page.xml')
        else:
            return cm.data.get('page.html')
    except Exception as e:
        logger.debug(f"Custom page not found for {page_name}: {e}")
        return None


def get_best_content_type(accept_header):
    """
    Determine the best content type based on Accept header
    Priority: HTML > JSON > XML (since browsers commonly request HTML)
    """
    if not accept_header:
        return 'html'

    accept_lower = accept_header.lower()

    # Check in priority order - HTML first for browser compatibility
    if 'text/html' in accept_lower:
        return 'html'
    elif 'application/json' in accept_lower:
        return 'json'
    elif 'application/xml' in accept_lower or 'text/xml' in accept_lower:
        return 'xml'
    elif '*/*' in accept_lower:
        return 'html'

    return 'html'


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def maintenance_page(path):
    """
    Serve maintenance page in appropriate format
    """
    # Get custom page name from query parameter or header
    custom_page = request.args.get('page') or request.headers.get('X-Maintenance-Page')

    # Determine content type
    accept_header = request.headers.get('Accept', 'text/html')
    content_type = get_best_content_type(accept_header)

    # Try to get custom page if specified
    content = None
    if custom_page:
        content = get_custom_page(custom_page, content_type)

    # Fall back to default pages
    if not content:
        if content_type == 'json':
            content = DEFAULT_JSON
            mime_type = 'application/json'
        elif content_type == 'xml':
            content = DEFAULT_XML
            mime_type = 'application/xml'
        else:
            content = DEFAULT_HTML
            mime_type = 'text/html'
    else:
        # Set mime type based on content type
        if content_type == 'json':
            mime_type = 'application/json'
        elif content_type == 'xml':
            mime_type = 'application/xml'
        else:
            mime_type = 'text/html'

    logger.info(f"Serving maintenance page: path={path}, content_type={content_type}, custom_page={custom_page}")

    return Response(
        content,
        status=HTTP_STATUS_CODE,
        mimetype=mime_type,
        headers={
            'Retry-After': '3600',  # Suggest retry after 1 hour
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
    )


@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'healthy'}, 200


@app.route('/ready')
def ready():
    """Readiness check endpoint"""
    return {'status': 'ready'}, 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
