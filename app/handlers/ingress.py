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
    create_maintenance_resources,
    delete_maintenance_resources,
    BACKUP_ANNOTATION,
    CUSTOM_PAGE_ANNOTATION,
    MAINTENANCE_SERVICE_PORT,
    networking_v1
)

logger = logging.getLogger(__name__)


@kopf.on.create('networking.k8s.io', 'v1', 'ingresses')
@kopf.on.update('networking.k8s.io', 'v1', 'ingresses')
def handle_ingress(spec, name, namespace, annotations, old, new, **kwargs):
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

        # Create maintenance resources (ConfigMap + Pod + Service) in target namespace
        maintenance_service_name = create_maintenance_resources(namespace, name, custom_page)

        # Update Ingress to point to maintenance service (same namespace)
        new_backend = client.V1IngressBackend(
            service=client.V1IngressServiceBackend(
                name=maintenance_service_name,
                port=client.V1ServiceBackendPort(number=MAINTENANCE_SERVICE_PORT)
            )
        )

        # Update all rules to point to maintenance service
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
                            'name': maintenance_service_name,
                            'port': {'number': MAINTENANCE_SERVICE_PORT}
                        }
                    }
                    new_paths.append(new_path)

                new_rule = rule.copy()
                new_rule['http'] = {'paths': new_paths}
                new_rules.append(new_rule)

        # Prepare annotations
        new_annotations = dict(annotations or {})
        new_annotations[BACKUP_ANNOTATION] = 'true'
        # Store the maintenance service name for later cleanup
        new_annotations['maintenance-operator.kahf.io/service-name'] = maintenance_service_name

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

    elif under_maintenance and has_backup:
        # Already in maintenance mode - check if custom page annotation changed
        logger.info(f"Ingress {namespace}/{name} already in maintenance mode, checking for annotation changes")

        # Get the current and old custom page annotations
        current_custom_page = annotations.get(CUSTOM_PAGE_ANNOTATION, '').strip()

        old_annotations = {}
        if old:
            old_annotations = old.get('metadata', {}).get('annotations', {})
        old_custom_page = old_annotations.get(CUSTOM_PAGE_ANNOTATION, '').strip()

        # Check if the custom page annotation changed
        if current_custom_page != old_custom_page:
            logger.info(f"Custom page annotation changed from '{old_custom_page}' to '{current_custom_page}'")

            # Get old service name
            old_service_name = old_annotations.get('maintenance-operator.kahf.io/service-name', '')

            # Remove reference from old maintenance resources
            if old_service_name:
                delete_maintenance_resources(namespace, name, old_service_name)

            # Create new maintenance resources with new custom page
            new_service_name = create_maintenance_resources(namespace, name, current_custom_page)

            # Update Ingress to point to new service
            new_backend = client.V1IngressBackend(
                service=client.V1IngressServiceBackend(
                    name=new_service_name,
                    port=client.V1ServiceBackendPort(number=MAINTENANCE_SERVICE_PORT)
                )
            )

            # Update all rules to point to new maintenance service
            new_rules = []
            if spec.get('rules'):
                for rule in spec['rules']:
                    http = rule.get('http', {})
                    paths = http.get('paths', [])
                    new_paths = []
                    for path in paths:
                        new_path = path.copy()
                        new_path['backend'] = {
                            'service': {
                                'name': new_service_name,
                                'port': {'number': MAINTENANCE_SERVICE_PORT}
                            }
                        }
                        new_paths.append(new_path)

                    new_rule = rule.copy()
                    new_rule['http'] = {'paths': new_paths}
                    new_rules.append(new_rule)

            # Update annotations
            new_annotations = dict(annotations or {})
            new_annotations['maintenance-operator.kahf.io/service-name'] = new_service_name

            # Patch the Ingress
            ingress_patch = {
                'metadata': {
                    'annotations': new_annotations
                },
                'spec': {
                    'rules': new_rules if new_rules else spec.get('rules')
                }
            }

            networking_v1.patch_namespaced_ingress(name, namespace, ingress_patch)
            logger.info(f"Updated Ingress {namespace}/{name} with new custom page configuration")

    elif not under_maintenance and has_backup:
        # Disable maintenance mode - restore original configuration
        logger.info(f"Disabling maintenance mode for Ingress {namespace}/{name}")

        backup_data = get_backup_configmap(name, namespace)
        if backup_data:
            # Get service name for cleanup
            service_name = annotations.get('maintenance-operator.kahf.io/service-name', '')

            # Restore original configuration
            ingress_patch = {
                'spec': {
                    'rules': backup_data.get('rules', []),
                    'defaultBackend': backup_data.get('defaultBackend')
                }
            }

            # Remove backup and service name annotations
            if annotations:
                new_annotations = dict(annotations)
                new_annotations.pop(BACKUP_ANNOTATION, None)
                new_annotations.pop('maintenance-operator.kahf.io/service-name', None)
                ingress_patch['metadata'] = {'annotations': new_annotations}

            networking_v1.patch_namespaced_ingress(name, namespace, ingress_patch)

            # Delete backup ConfigMap
            delete_backup_configmap(name, namespace)

            # Delete or cleanup maintenance resources
            if service_name:
                delete_maintenance_resources(namespace, name, service_name)

            logger.info(f"Maintenance mode disabled for Ingress {namespace}/{name}")
