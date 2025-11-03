#!/usr/bin/env python3
"""
Traefik IngressRoute Handler for Maintenance Operator
Handles Traefik IngressRoute custom resources
"""

import logging
import kopf
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
    custom_api
)

logger = logging.getLogger(__name__)


@kopf.on.create('traefik.io', 'v1alpha1', 'ingressroutes')
@kopf.on.update('traefik.io', 'v1alpha1', 'ingressroutes')
def handle_ingressroute(spec, name, namespace, meta, old, new, **kwargs):
    """Handle Traefik IngressRoute resources"""
    logger.info(f"Processing IngressRoute {namespace}/{name}")

    annotations = meta.get('annotations', {})
    under_maintenance = is_under_maintenance(annotations)
    has_backup = BACKUP_ANNOTATION in annotations

    if under_maintenance and not has_backup:
        # Enable maintenance mode
        logger.info(f"Enabling maintenance mode for IngressRoute {namespace}/{name}")

        # Backup original configuration
        backup_data = {
            'routes': spec.get('routes', [])
        }
        create_backup_configmap(name, namespace, backup_data)

        # Get custom page name if specified
        custom_page = annotations.get(CUSTOM_PAGE_ANNOTATION, '').strip()

        # Create maintenance resources (ConfigMap + Pod + Service) in target namespace
        maintenance_service_name = create_maintenance_resources(namespace, name, custom_page)

        # Update IngressRoute to point to maintenance service (same namespace)
        new_routes = []
        if spec.get('routes'):
            for route in spec['routes']:
                new_route = route.copy()
                # Replace all services with maintenance service (same namespace)
                new_route['services'] = [{
                    'name': maintenance_service_name,
                    'port': MAINTENANCE_SERVICE_PORT
                }]
                new_routes.append(new_route)

        # Patch the IngressRoute
        patch = {
            'metadata': {
                'annotations': {
                    **annotations,
                    BACKUP_ANNOTATION: 'true',
                    'maintenance-operator.kahf.io/service-name': maintenance_service_name
                }
            },
            'spec': {
                'routes': new_routes
            }
        }

        custom_api.patch_namespaced_custom_object(
            group='traefik.io',
            version='v1alpha1',
            namespace=namespace,
            plural='ingressroutes',
            name=name,
            body=patch
        )
        logger.info(f"Maintenance mode enabled for IngressRoute {namespace}/{name}")

    elif under_maintenance and has_backup:
        # Already in maintenance mode - check if custom page annotation changed
        logger.info(f"IngressRoute {namespace}/{name} already in maintenance mode, checking for annotation changes")

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

            # Update routes to point to new service
            new_routes = []
            if spec.get('routes'):
                for route in spec['routes']:
                    new_route = route.copy()
                    new_route['services'] = [{
                        'name': new_service_name,
                        'port': MAINTENANCE_SERVICE_PORT
                    }]
                    new_routes.append(new_route)

            # Patch the IngressRoute
            patch = {
                'metadata': {
                    'annotations': {
                        **annotations,
                        'maintenance-operator.kahf.io/service-name': new_service_name
                    }
                },
                'spec': {
                    'routes': new_routes
                }
            }

            custom_api.patch_namespaced_custom_object(
                group='traefik.io',
                version='v1alpha1',
                namespace=namespace,
                plural='ingressroutes',
                name=name,
                body=patch
            )
            logger.info(f"Updated IngressRoute {namespace}/{name} with new custom page configuration")

    elif not under_maintenance and has_backup:
        # Disable maintenance mode - restore original configuration
        logger.info(f"Disabling maintenance mode for IngressRoute {namespace}/{name}")

        backup_data = get_backup_configmap(name, namespace)
        if backup_data:
            # Get service name for cleanup
            service_name = annotations.get('maintenance-operator.kahf.io/service-name', '')

            # Restore original configuration
            new_annotations = dict(annotations)
            new_annotations.pop(BACKUP_ANNOTATION, None)
            new_annotations.pop('maintenance-operator.kahf.io/service-name', None)

            patch = {
                'metadata': {
                    'annotations': new_annotations
                },
                'spec': {
                    'routes': backup_data.get('routes', [])
                }
            }

            custom_api.patch_namespaced_custom_object(
                group='traefik.io',
                version='v1alpha1',
                namespace=namespace,
                plural='ingressroutes',
                name=name,
                body=patch
            )

            # Delete backup ConfigMap
            delete_backup_configmap(name, namespace)

            # Delete or cleanup maintenance resources
            if service_name:
                delete_maintenance_resources(namespace, name, service_name)

            logger.info(f"Maintenance mode disabled for IngressRoute {namespace}/{name}")
