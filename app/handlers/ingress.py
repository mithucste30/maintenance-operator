#!/usr/bin/env python3
"""
Ingress Handler for Maintenance Operator
Handles standard Kubernetes Ingress resources
"""

import logging
import kopf
from kubernetes import client
from kubernetes.client.rest import ApiException

from utils import (
    is_under_maintenance,
    create_backup_configmap,
    get_backup_configmap,
    delete_backup_configmap,
    create_maintenance_service,
    delete_maintenance_service,
    BACKUP_ANNOTATION,
    CUSTOM_PAGE_ANNOTATION,
    MAINTENANCE_SERVICE_PORT,
    networking_v1
)

logger = logging.getLogger(__name__)


@kopf.on.create('networking.k8s.io', 'v1', 'ingresses')
@kopf.on.update('networking.k8s.io', 'v1', 'ingresses')
def handle_ingress(spec, name, namespace, annotations, **kwargs):
    """Handle Ingress resources"""
    logger.info(f"Processing Ingress {namespace}/{name}")

    under_maintenance = is_under_maintenance(annotations)
    has_backup = annotations and BACKUP_ANNOTATION in annotations

    if under_maintenance and not has_backup:
        # Enable maintenance mode
        logger.info(f"Enabling maintenance mode for Ingress {namespace}/{name}")

        # Backup original configuration
        backup_data = {
            'rules': spec.get('rules', []),
            'defaultBackend': spec.get('defaultBackend')
        }
        create_backup_configmap(name, namespace, backup_data)

        # Get custom page name if specified
        custom_page = None
        if annotations and CUSTOM_PAGE_ANNOTATION in annotations:
            custom_page = annotations[CUSTOM_PAGE_ANNOTATION]

        # Create proxy service with endpoints in target namespace (for cross-namespace support)
        # Pass custom_page to store in service annotations
        proxy_service_name = create_maintenance_service(namespace, custom_page)

        # Update Ingress to point to maintenance proxy service (same namespace)
        new_backend = client.V1IngressBackend(
            service=client.V1IngressServiceBackend(
                name=proxy_service_name,
                port=client.V1ServiceBackendPort(number=MAINTENANCE_SERVICE_PORT)
            )
        )

        # Update all rules to point to maintenance service
        # For custom pages, we'll use path rewrite to include query parameter
        new_rules = []
        if spec.get('rules'):
            for rule in spec['rules']:
                http = rule.get('http', {})
                paths = http.get('paths', [])
                new_paths = []
                for path in paths:
                    new_path = path.copy()
                    # Point to maintenance service
                    new_path['backend'] = {
                        'service': {
                            'name': proxy_service_name,
                            'port': {'number': MAINTENANCE_SERVICE_PORT}
                        }
                    }
                    # Note: Custom page is stored in service annotations and will be
                    # read by the maintenance server via query param or header
                    # Most ingress controllers preserve query parameters
                    new_paths.append(new_path)

                new_rule = rule.copy()
                new_rule['http'] = {'paths': new_paths}
                new_rules.append(new_rule)

        # Prepare annotations - add rewrite annotation for custom pages
        new_annotations = dict(annotations or {})
        new_annotations[BACKUP_ANNOTATION] = 'true'

        # If custom page is specified, add rewrite annotation for query parameter
        # This works with most ingress controllers (nginx, traefik)
        if custom_page and custom_page.lower() != 'default':
            # Add nginx-style rewrite annotation (most common)
            new_annotations['nginx.ingress.kubernetes.io/configuration-snippet'] = f'rewrite ^(.*)$ $1?page={custom_page} break;'
            # Add traefik-style annotation
            new_annotations['traefik.ingress.kubernetes.io/redirect-regex'] = f'^(.*)$'
            new_annotations['traefik.ingress.kubernetes.io/redirect-replacement'] = f'$1?page={custom_page}'
            logger.info(f"Added rewrite annotations for custom page: {custom_page}")

        # Patch the Ingress
        ingress_patch = {
            'metadata': {
                'annotations': new_annotations
            },
            'spec': {
                'rules': new_rules if new_rules else spec.get('rules'),
                'defaultBackend': new_backend if not new_rules else spec.get('defaultBackend')
            }
        }

        networking_v1.patch_namespaced_ingress(name, namespace, ingress_patch)
        logger.info(f"Maintenance mode enabled for Ingress {namespace}/{name}")

    elif not under_maintenance and has_backup:
        # Disable maintenance mode - restore original configuration
        logger.info(f"Disabling maintenance mode for Ingress {namespace}/{name}")

        backup_data = get_backup_configmap(name, namespace)
        if backup_data:
            # Restore original configuration
            ingress_patch = {
                'spec': {
                    'rules': backup_data.get('rules', []),
                    'defaultBackend': backup_data.get('defaultBackend')
                }
            }

            # Remove backup annotation
            if annotations:
                new_annotations = dict(annotations)
                new_annotations.pop(BACKUP_ANNOTATION, None)
                ingress_patch['metadata'] = {'annotations': new_annotations}

            networking_v1.patch_namespaced_ingress(name, namespace, ingress_patch)

            # Delete backup ConfigMap
            delete_backup_configmap(name, namespace)

            # Delete the proxy service
            delete_maintenance_service(namespace)

            logger.info(f"Maintenance mode disabled for Ingress {namespace}/{name}")
