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
    create_maintenance_service,
    delete_maintenance_service,
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

        # Create proxy service with endpoints in target namespace (for Traefik cross-namespace restriction)
        # Pass custom_page to store in service annotations (fallback for when middleware isn't used)
        proxy_service_name = create_maintenance_service(namespace, custom_page)

        # Always try to clean up any existing middleware first (in case we're switching pages)
        potential_middleware_name = f"{name}-maintenance-page"
        try:
            custom_api.delete_namespaced_custom_object(
                group='traefik.io',
                version='v1alpha1',
                namespace=namespace,
                plural='middlewares',
                name=potential_middleware_name
            )
            logger.info(f"Deleted existing middleware {potential_middleware_name}")
        except ApiException as e:
            if e.status != 404:
                logger.warning(f"Error deleting existing middleware: {e}")
            # 404 is fine - middleware doesn't exist

        # Create middleware to inject custom page header if specified
        # Only create if custom_page is set and not "default"
        middleware_name = None
        if custom_page and custom_page.lower() != 'default':
            middleware_name = f"{name}-maintenance-page"
            middleware = {
                'apiVersion': 'traefik.io/v1alpha1',
                'kind': 'Middleware',
                'metadata': {
                    'name': middleware_name,
                    'namespace': namespace,
                    'labels': {'app': 'maintenance-operator', 'managed-by': 'maintenance-operator'}
                },
                'spec': {
                    'headers': {
                        'customRequestHeaders': {
                            'X-Maintenance-Page': custom_page
                        }
                    }
                }
            }
            try:
                custom_api.create_namespaced_custom_object(
                    group='traefik.io',
                    version='v1alpha1',
                    namespace=namespace,
                    plural='middlewares',
                    body=middleware
                )
                logger.info(f"Created middleware {middleware_name} for custom page {custom_page}")
            except ApiException as e:
                if e.status == 409:
                    custom_api.patch_namespaced_custom_object(
                        group='traefik.io',
                        version='v1alpha1',
                        namespace=namespace,
                        plural='middlewares',
                        name=middleware_name,
                        body=middleware
                    )
                    logger.info(f"Updated middleware {middleware_name} for custom page {custom_page}")
                else:
                    raise

        # Update IngressRoute to point to maintenance proxy service (same namespace, no namespace field)
        new_routes = []
        if spec.get('routes'):
            for route in spec['routes']:
                new_route = route.copy()
                # Replace all services with maintenance proxy service (same namespace)
                new_route['services'] = [{
                    'name': proxy_service_name,
                    'port': MAINTENANCE_SERVICE_PORT
                }]
                # Remove our maintenance page middleware if it exists (in case we're switching pages)
                existing_middlewares = new_route.get('middlewares', [])
                filtered_middlewares = [
                    mw for mw in existing_middlewares
                    if mw.get('name') != potential_middleware_name
                ]
                # Add custom page middleware if specified (at the beginning)
                if middleware_name:
                    new_route['middlewares'] = [{'name': middleware_name}] + filtered_middlewares
                else:
                    # No custom page - use filtered middlewares without our maintenance middleware
                    new_route['middlewares'] = filtered_middlewares
                new_routes.append(new_route)

        # Patch the IngressRoute
        patch = {
            'metadata': {
                'annotations': {
                    **annotations,
                    BACKUP_ANNOTATION: 'true'
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

            # Get current routes from spec
            current_routes = spec.get('routes', [])

            # Clean up existing middleware
            potential_middleware_name = f"{name}-maintenance-page"
            try:
                custom_api.delete_namespaced_custom_object(
                    group='traefik.io',
                    version='v1alpha1',
                    namespace=namespace,
                    plural='middlewares',
                    name=potential_middleware_name
                )
                logger.info(f"Deleted existing middleware {potential_middleware_name}")
            except ApiException as e:
                if e.status != 404:
                    logger.warning(f"Error deleting existing middleware: {e}")

            # Create new middleware if needed
            middleware_name = None
            if current_custom_page and current_custom_page.lower() != 'default':
                middleware_name = f"{name}-maintenance-page"
                middleware = {
                    'apiVersion': 'traefik.io/v1alpha1',
                    'kind': 'Middleware',
                    'metadata': {
                        'name': middleware_name,
                        'namespace': namespace,
                        'labels': {'app': 'maintenance-operator', 'managed-by': 'maintenance-operator'}
                    },
                    'spec': {
                        'headers': {
                            'customRequestHeaders': {
                                'X-Maintenance-Page': current_custom_page
                            }
                        }
                    }
                }
                custom_api.create_namespaced_custom_object(
                    group='traefik.io',
                    version='v1alpha1',
                    namespace=namespace,
                    plural='middlewares',
                    body=middleware
                )
                logger.info(f"Created new middleware {middleware_name} for custom page {current_custom_page}")

            # Update routes with new middleware configuration
            new_routes = []
            for route in current_routes:
                new_route = route.copy()
                # Remove our maintenance page middleware if it exists
                existing_middlewares = new_route.get('middlewares', [])
                filtered_middlewares = [
                    mw for mw in existing_middlewares
                    if mw.get('name') != potential_middleware_name
                ]
                # Add custom page middleware if specified (at the beginning)
                if middleware_name:
                    new_route['middlewares'] = [{'name': middleware_name}] + filtered_middlewares
                else:
                    # No custom page - use filtered middlewares without our maintenance middleware
                    new_route['middlewares'] = filtered_middlewares
                new_routes.append(new_route)

            # Patch the IngressRoute with updated routes
            patch = {
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
            # Restore original configuration
            new_annotations = dict(annotations)
            new_annotations.pop(BACKUP_ANNOTATION, None)

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

            # Delete the proxy service
            delete_maintenance_service(namespace)

            # Delete custom page middleware if it exists
            middleware_name = f"{name}-maintenance-page"
            try:
                custom_api.delete_namespaced_custom_object(
                    group='traefik.io',
                    version='v1alpha1',
                    namespace=namespace,
                    plural='middlewares',
                    name=middleware_name
                )
                logger.info(f"Deleted middleware {middleware_name}")
            except ApiException as e:
                if e.status != 404:
                    logger.error(f"Error deleting middleware: {e}")

            logger.info(f"Maintenance mode disabled for IngressRoute {namespace}/{name}")
