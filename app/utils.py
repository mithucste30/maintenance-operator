#!/usr/bin/env python3
"""
Utility functions for Maintenance Operator
Shared functions used by both Ingress and IngressRoute handlers
"""

import os
import json
import logging
import hashlib
import base64
from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)

# Configuration from environment
MAINTENANCE_ANNOTATION = os.getenv('MAINTENANCE_ANNOTATION', 'maintenance-operator.mithucste30.io/enabled')
MAINTENANCE_ANNOTATION_VALUE = os.getenv('MAINTENANCE_ANNOTATION_VALUE', 'true')
BACKUP_ANNOTATION = os.getenv('BACKUP_ANNOTATION', 'maintenance-operator.mithucste30.io/original-service')
CUSTOM_PAGE_ANNOTATION = os.getenv('CUSTOM_PAGE_ANNOTATION', 'maintenance-operator.mithucste30.io/custom-page')
BACKUP_CONFIGMAP_PREFIX = os.getenv('BACKUP_CONFIGMAP_PREFIX', 'maintenance-backup')
MAINTENANCE_SERVICE_PORT = int(os.getenv('MAINTENANCE_SERVICE_PORT', '80'))
OPERATOR_NAMESPACE = os.getenv('POD_NAMESPACE', 'default')
MAINTENANCE_CONFIGMAP_NAME = os.getenv('MAINTENANCE_CONFIGMAP_NAME', 'maintenance-operator-default-pages')

# Load Kubernetes config
try:
    config.load_incluster_config()
except:
    config.load_kube_config()

v1 = client.CoreV1Api()
networking_v1 = client.NetworkingV1Api()
custom_api = client.CustomObjectsApi()


def is_under_maintenance(annotations):
    """Check if resource is in maintenance mode via annotation"""
    if not annotations:
        return False
    return annotations.get(MAINTENANCE_ANNOTATION) == MAINTENANCE_ANNOTATION_VALUE


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


def get_html_content(custom_page=None):
    """
    Get HTML content from operator namespace ConfigMaps.
    Returns the HTML content for the requested page.
    """
    try:
        # Determine which ConfigMap to read from
        if custom_page and custom_page.lower() != 'default':
            # Custom page ConfigMap
            cm_name = f"maintenance-page-{custom_page}"
        else:
            # Default page ConfigMap
            cm_name = MAINTENANCE_CONFIGMAP_NAME

        # Read ConfigMap from operator namespace
        cm = v1.read_namespaced_config_map(cm_name, OPERATOR_NAMESPACE)
        html_content = cm.data.get('page.html', '')

        if not html_content:
            logger.warning(f"No HTML content found in ConfigMap {cm_name}, using fallback")
            html_content = get_fallback_html()

        return html_content
    except ApiException as e:
        if e.status == 404:
            logger.warning(f"ConfigMap {cm_name} not found in namespace {OPERATOR_NAMESPACE}, using fallback HTML")
            return get_fallback_html()
        logger.error(f"Error reading ConfigMap {cm_name}: {e}")
        return get_fallback_html()


def get_fallback_html():
    """Return a basic fallback HTML page"""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Maintenance Mode</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
        h1 { color: #333; }
    </style>
</head>
<body>
    <h1>Site Under Maintenance</h1>
    <p>We'll be back soon. Thank you for your patience.</p>
</body>
</html>"""


def hash_content(content):
    """Generate a short hash of content for resource naming"""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:8]


def create_maintenance_resources(namespace, ingress_name, custom_page=None):
    """
    Create maintenance resources (ConfigMap + Pod + Service) in the target namespace.
    Returns the service name to use in Ingress configuration.
    Multiple Ingresses with the same HTML content will share the same resources.
    """
    # Get HTML content
    html_content = get_html_content(custom_page)
    content_hash = hash_content(html_content)

    # Resource names based on content hash
    resource_name = f"maintenance-{content_hash}"

    # Labels for all resources
    labels = {
        'app': 'maintenance-page',
        'managed-by': 'maintenance-operator',
        'content-hash': content_hash
    }

    # Create ConfigMap with HTML content
    configmap = client.V1ConfigMap(
        metadata=client.V1ObjectMeta(
            name=resource_name,
            namespace=namespace,
            labels=labels,
            annotations={
                'maintenance-operator.mithucste30.io/custom-page': custom_page or 'default',
                'maintenance-operator.mithucste30.io/used-by': ingress_name  # Track usage
            }
        ),
        data={'index.html': html_content}
    )

    try:
        existing_cm = v1.read_namespaced_config_map(resource_name, namespace)
        # Update the used-by annotation to include this ingress
        existing_annotations = existing_cm.metadata.annotations or {}
        used_by = existing_annotations.get('maintenance-operator.mithucste30.io/used-by', '')
        if ingress_name not in used_by.split(','):
            used_by = ','.join(filter(None, [used_by, ingress_name]))
            existing_cm.metadata.annotations['maintenance-operator.mithucste30.io/used-by'] = used_by
            v1.patch_namespaced_config_map(resource_name, namespace, existing_cm)
            logger.info(f"Updated ConfigMap {resource_name} used-by annotation: {used_by}")
    except ApiException as e:
        if e.status == 404:
            v1.create_namespaced_config_map(namespace, configmap)
            logger.info(f"Created ConfigMap {resource_name} in namespace {namespace}")
        else:
            raise

    # Create Pod with nginx serving the HTML
    pod = client.V1Pod(
        metadata=client.V1ObjectMeta(
            name=resource_name,
            namespace=namespace,
            labels=labels
        ),
        spec=client.V1PodSpec(
            containers=[
                client.V1Container(
                    name='nginx',
                    image='nginx:alpine',
                    ports=[client.V1ContainerPort(container_port=80)],
                    volume_mounts=[
                        client.V1VolumeMount(
                            name='html',
                            mount_path='/usr/share/nginx/html',
                            read_only=True
                        )
                    ],
                    resources=client.V1ResourceRequirements(
                        requests={'cpu': '10m', 'memory': '16Mi'},
                        limits={'cpu': '50m', 'memory': '32Mi'}
                    )
                )
            ],
            volumes=[
                client.V1Volume(
                    name='html',
                    config_map=client.V1ConfigMapVolumeSource(name=resource_name)
                )
            ],
            restart_policy='Always'
        )
    )

    try:
        v1.create_namespaced_pod(namespace, pod)
        logger.info(f"Created Pod {resource_name} in namespace {namespace}")
    except ApiException as e:
        if e.status == 409:
            logger.info(f"Pod {resource_name} already exists in namespace {namespace}")
        else:
            logger.error(f"Error creating Pod: {e}")
            raise

    # Create Service pointing to the Pod
    service = client.V1Service(
        metadata=client.V1ObjectMeta(
            name=resource_name,
            namespace=namespace,
            labels=labels
        ),
        spec=client.V1ServiceSpec(
            type='ClusterIP',
            selector=labels,
            ports=[client.V1ServicePort(
                name='http',
                port=MAINTENANCE_SERVICE_PORT,
                target_port=80,
                protocol='TCP'
            )]
        )
    )

    try:
        v1.create_namespaced_service(namespace, service)
        logger.info(f"Created Service {resource_name} in namespace {namespace}")
    except ApiException as e:
        if e.status == 409:
            logger.info(f"Service {resource_name} already exists in namespace {namespace}")
        else:
            logger.error(f"Error creating Service: {e}")
            raise

    return resource_name


def delete_maintenance_resources(namespace, ingress_name, service_name):
    """
    Remove reference to an Ingress from maintenance resources.
    If no Ingresses are using the resources, delete them.
    """
    try:
        # Read ConfigMap to check usage
        cm = v1.read_namespaced_config_map(service_name, namespace)
        annotations = cm.metadata.annotations or {}
        used_by = annotations.get('maintenance-operator.mithucste30.io/used-by', '')

        # Remove this ingress from the used-by list
        ingresses = [i.strip() for i in used_by.split(',') if i.strip() and i.strip() != ingress_name]

        if ingresses:
            # Still in use by other ingresses, just update the annotation
            cm.metadata.annotations['maintenance-operator.mithucste30.io/used-by'] = ','.join(ingresses)
            v1.patch_namespaced_config_map(service_name, namespace, cm)
            logger.info(f"Updated ConfigMap {service_name} used-by annotation: {','.join(ingresses)}")
            return

        # No longer in use, delete all resources
        logger.info(f"No Ingresses using {service_name} in namespace {namespace}, deleting resources")

        # Delete Pod
        try:
            v1.delete_namespaced_pod(service_name, namespace)
            logger.info(f"Deleted Pod {service_name} from namespace {namespace}")
        except ApiException as e:
            if e.status != 404:
                logger.error(f"Error deleting Pod: {e}")

        # Delete Service
        try:
            v1.delete_namespaced_service(service_name, namespace)
            logger.info(f"Deleted Service {service_name} from namespace {namespace}")
        except ApiException as e:
            if e.status != 404:
                logger.error(f"Error deleting Service: {e}")

        # Delete ConfigMap
        try:
            v1.delete_namespaced_config_map(service_name, namespace)
            logger.info(f"Deleted ConfigMap {service_name} from namespace {namespace}")
        except ApiException as e:
            if e.status != 404:
                logger.error(f"Error deleting ConfigMap: {e}")

    except ApiException as e:
        if e.status == 404:
            logger.info(f"ConfigMap {service_name} not found in namespace {namespace}, resources may already be deleted")
        else:
            logger.error(f"Error managing maintenance resources: {e}")
