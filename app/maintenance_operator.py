#!/usr/bin/env python3
"""
Maintenance Operator
Watches Ingress and IngressRoute resources for maintenance label
and redirects traffic to maintenance page when label is present
"""

import os
import json
import logging
import kopf
from kubernetes import client, config
from kubernetes.client.rest import ApiException

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment
MAINTENANCE_LABEL = os.getenv('MAINTENANCE_LABEL', 'under-maintenance')
MAINTENANCE_LABEL_VALUE = os.getenv('MAINTENANCE_LABEL_VALUE', 'true')
BACKUP_ANNOTATION = os.getenv('BACKUP_ANNOTATION', 'maintenance-operator.kahf.io/original-service')
CUSTOM_PAGE_ANNOTATION = os.getenv('CUSTOM_PAGE_ANNOTATION', 'maintenance-operator.kahf.io/custom-page')
BACKUP_CONFIGMAP_PREFIX = os.getenv('BACKUP_CONFIGMAP_PREFIX', 'maintenance-backup')
MAINTENANCE_SERVICE_NAME = os.getenv('MAINTENANCE_SERVICE_NAME', 'maintenance-operator')
MAINTENANCE_SERVICE_PORT = int(os.getenv('MAINTENANCE_SERVICE_PORT', '8080'))
OPERATOR_NAMESPACE = os.getenv('POD_NAMESPACE', 'default')

# Load Kubernetes config
try:
    config.load_incluster_config()
except:
    config.load_kube_config()

v1 = client.CoreV1Api()
networking_v1 = client.NetworkingV1Api()
custom_api = client.CustomObjectsApi()


def is_under_maintenance(labels):
    """Check if resource has maintenance label"""
    if not labels:
        return False
    return labels.get(MAINTENANCE_LABEL) == MAINTENANCE_LABEL_VALUE


def create_backup_configmap(name, namespace, backup_data):
    """Create a ConfigMap to store original service configuration"""
    cm_name = f"{BACKUP_CONFIGMAP_PREFIX}-{name}"

    configmap = client.V1ConfigMap(
        metadata=client.V1ObjectMeta(
            name=cm_name,
            namespace=namespace,
            labels={'app': 'maintenance-operator', 'backup-for': name}
        ),
        data={'backup': json.dumps(backup_data)}
    )

    try:
        v1.create_namespaced_config_map(namespace, configmap)
        logger.info(f"Created backup ConfigMap {cm_name} in namespace {namespace}")
        return cm_name
    except ApiException as e:
        if e.status == 409:  # Already exists
            v1.patch_namespaced_config_map(cm_name, namespace, configmap)
            logger.info(f"Updated backup ConfigMap {cm_name} in namespace {namespace}")
            return cm_name
        else:
            raise


def get_backup_configmap(name, namespace):
    """Retrieve backup data from ConfigMap"""
    cm_name = f"{BACKUP_CONFIGMAP_PREFIX}-{name}"

    try:
        cm = v1.read_namespaced_config_map(cm_name, namespace)
        return json.loads(cm.data.get('backup', '{}'))
    except ApiException as e:
        if e.status == 404:
            logger.warning(f"Backup ConfigMap {cm_name} not found in namespace {namespace}")
            return None
        raise


def delete_backup_configmap(name, namespace):
    """Delete backup ConfigMap"""
    cm_name = f"{BACKUP_CONFIGMAP_PREFIX}-{name}"

    try:
        v1.delete_namespaced_config_map(cm_name, namespace)
        logger.info(f"Deleted backup ConfigMap {cm_name} from namespace {namespace}")
    except ApiException as e:
        if e.status != 404:
            logger.error(f"Error deleting backup ConfigMap: {e}")


def create_maintenance_service(namespace):
    """Create an ExternalName service in target namespace pointing to maintenance service"""
    service_name = f"{MAINTENANCE_SERVICE_NAME}-proxy"

    # ExternalName service to point to maintenance service in operator namespace
    service = client.V1Service(
        metadata=client.V1ObjectMeta(
            name=service_name,
            namespace=namespace,
            labels={'app': 'maintenance-operator', 'managed-by': 'maintenance-operator'}
        ),
        spec=client.V1ServiceSpec(
            type='ExternalName',
            external_name=f"{MAINTENANCE_SERVICE_NAME}.{OPERATOR_NAMESPACE}.svc.cluster.local",
            ports=[client.V1ServicePort(
                name='http',
                port=MAINTENANCE_SERVICE_PORT,
                target_port=MAINTENANCE_SERVICE_PORT
            )]
        )
    )

    try:
        v1.create_namespaced_service(namespace, service)
        logger.info(f"Created maintenance proxy service {service_name} in namespace {namespace}")
        return service_name
    except ApiException as e:
        if e.status == 409:  # Already exists
            logger.info(f"Maintenance proxy service {service_name} already exists in namespace {namespace}")
            return service_name
        else:
            logger.error(f"Error creating maintenance proxy service: {e}")
            raise


def delete_maintenance_service(namespace):
    """Delete the ExternalName service from target namespace"""
    service_name = f"{MAINTENANCE_SERVICE_NAME}-proxy"

    try:
        v1.delete_namespaced_service(service_name, namespace)
        logger.info(f"Deleted maintenance proxy service {service_name} from namespace {namespace}")
    except ApiException as e:
        if e.status != 404:
            logger.error(f"Error deleting maintenance proxy service: {e}")


@kopf.on.create('networking.k8s.io', 'v1', 'ingresses')
@kopf.on.update('networking.k8s.io', 'v1', 'ingresses')
def handle_ingress(spec, name, namespace, labels, annotations, **kwargs):
    """Handle Ingress resources"""
    logger.info(f"Processing Ingress {namespace}/{name}")

    under_maintenance = is_under_maintenance(labels)
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

        # Create ExternalName service in target namespace (for cross-namespace support)
        proxy_service_name = create_maintenance_service(namespace)

        # Get custom page name if specified
        custom_page = None
        if annotations and CUSTOM_PAGE_ANNOTATION in annotations:
            custom_page = annotations[CUSTOM_PAGE_ANNOTATION]

        # Update Ingress to point to maintenance proxy service (same namespace)
        new_backend = client.V1IngressBackend(
            service=client.V1IngressServiceBackend(
                name=proxy_service_name,
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
                    new_path['backend'] = {
                        'service': {
                            'name': proxy_service_name,
                            'port': {'number': MAINTENANCE_SERVICE_PORT}
                        }
                    }
                    new_paths.append(new_path)

                new_rule = rule.copy()
                new_rule['http'] = {'paths': new_paths}
                new_rules.append(new_rule)

        # Patch the Ingress
        ingress_patch = {
            'metadata': {
                'annotations': {
                    BACKUP_ANNOTATION: 'true',
                    **(annotations or {})
                }
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
                new_annotations = annotations.copy()
                new_annotations.pop(BACKUP_ANNOTATION, None)
                ingress_patch['metadata'] = {'annotations': new_annotations}

            networking_v1.patch_namespaced_ingress(name, namespace, ingress_patch)

            # Delete backup ConfigMap
            delete_backup_configmap(name, namespace)

            # Delete the proxy service
            delete_maintenance_service(namespace)

            logger.info(f"Maintenance mode disabled for Ingress {namespace}/{name}")


@kopf.on.create('traefik.io', 'v1alpha1', 'ingressroutes')
@kopf.on.update('traefik.io', 'v1alpha1', 'ingressroutes')
def handle_ingressroute(spec, name, namespace, labels, meta, **kwargs):
    """Handle Traefik IngressRoute resources"""
    logger.info(f"Processing IngressRoute {namespace}/{name}")

    annotations = meta.get('annotations', {})
    under_maintenance = is_under_maintenance(labels)
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
        custom_page = annotations.get(CUSTOM_PAGE_ANNOTATION)

        # Update IngressRoute to point to maintenance service
        new_routes = []
        if spec.get('routes'):
            for route in spec['routes']:
                new_route = route.copy()
                # Replace all services with maintenance service
                new_route['services'] = [{
                    'name': MAINTENANCE_SERVICE_NAME,
                    'port': MAINTENANCE_SERVICE_PORT,
                    'namespace': OPERATOR_NAMESPACE
                }]
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

    elif not under_maintenance and has_backup:
        # Disable maintenance mode - restore original configuration
        logger.info(f"Disabling maintenance mode for IngressRoute {namespace}/{name}")

        backup_data = get_backup_configmap(name, namespace)
        if backup_data:
            # Restore original configuration
            new_annotations = annotations.copy()
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

            logger.info(f"Maintenance mode disabled for IngressRoute {namespace}/{name}")


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    """Configure operator settings"""
    settings.persistence.finalizer = 'maintenance-operator.kahf.io/finalizer'
    settings.posting.enabled = True
    logger.info("Maintenance Operator started")
