#!/usr/bin/env python3
"""
Utility functions for Maintenance Operator
Shared functions used by both Ingress and IngressRoute handlers
"""

import os
import json
import logging
import threading
import time
from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)

# Configuration from environment
MAINTENANCE_ANNOTATION = os.getenv('MAINTENANCE_ANNOTATION', 'maintenance-operator.kahf.io/enabled')
MAINTENANCE_ANNOTATION_VALUE = os.getenv('MAINTENANCE_ANNOTATION_VALUE', 'true')
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


def get_maintenance_pod_ips():
    """Get IP addresses of maintenance operator pods"""
    try:
        pods = v1.list_namespaced_pod(
            namespace=OPERATOR_NAMESPACE,
            label_selector=f'app.kubernetes.io/name={MAINTENANCE_SERVICE_NAME}'
        )
        pod_ips = [pod.status.pod_ip for pod in pods.items if pod.status.pod_ip]
        logger.info(f"Found {len(pod_ips)} maintenance operator pod IPs: {pod_ips}")
        return pod_ips
    except ApiException as e:
        logger.error(f"Error getting maintenance pod IPs: {e}")
        return []


def create_maintenance_service(namespace, custom_page=None):
    """Create a ClusterIP service and Endpoints in target namespace pointing to maintenance pods"""
    service_name = f"{MAINTENANCE_SERVICE_NAME}-proxy"

    # Prepare annotations with custom page info
    annotations = {}
    if custom_page and custom_page.lower() != 'default':
        annotations[CUSTOM_PAGE_ANNOTATION] = custom_page

    # Create ClusterIP service (without selector - we'll manually create endpoints)
    service = client.V1Service(
        metadata=client.V1ObjectMeta(
            name=service_name,
            namespace=namespace,
            labels={'app': 'maintenance-operator', 'managed-by': 'maintenance-operator'},
            annotations=annotations if annotations else None
        ),
        spec=client.V1ServiceSpec(
            type='ClusterIP',
            ports=[client.V1ServicePort(
                name='http',
                port=MAINTENANCE_SERVICE_PORT,
                target_port=MAINTENANCE_SERVICE_PORT,
                protocol='TCP'
            )]
        )
    )

    try:
        v1.create_namespaced_service(namespace, service)
        logger.info(f"Created maintenance proxy service {service_name} in namespace {namespace}")
    except ApiException as e:
        if e.status == 409:  # Already exists
            logger.info(f"Maintenance proxy service {service_name} already exists in namespace {namespace}")
        else:
            logger.error(f"Error creating maintenance proxy service: {e}")
            raise

    # Get maintenance pod IPs
    pod_ips = get_maintenance_pod_ips()
    if not pod_ips:
        logger.warning("No maintenance operator pods found, service may not work until pods are available")
        return service_name

    # Create Endpoints object pointing to maintenance pods
    endpoints = client.V1Endpoints(
        metadata=client.V1ObjectMeta(
            name=service_name,
            namespace=namespace,
            labels={'app': 'maintenance-operator', 'managed-by': 'maintenance-operator'}
        ),
        subsets=[client.V1EndpointSubset(
            addresses=[client.V1EndpointAddress(ip=ip) for ip in pod_ips],
            ports=[client.CoreV1EndpointPort(
                name='http',
                port=MAINTENANCE_SERVICE_PORT,
                protocol='TCP'
            )]
        )]
    )

    try:
        v1.create_namespaced_endpoints(namespace, endpoints)
        logger.info(f"Created endpoints for {service_name} in namespace {namespace} pointing to {pod_ips}")
    except ApiException as e:
        if e.status == 409:  # Already exists
            v1.patch_namespaced_endpoints(service_name, namespace, endpoints)
            logger.info(f"Updated endpoints for {service_name} in namespace {namespace}")
        else:
            logger.error(f"Error creating endpoints: {e}")
            raise

    return service_name


def delete_maintenance_service(namespace):
    """Delete the proxy service and endpoints from target namespace"""
    service_name = f"{MAINTENANCE_SERVICE_NAME}-proxy"

    # Delete endpoints
    try:
        v1.delete_namespaced_endpoints(service_name, namespace)
        logger.info(f"Deleted endpoints {service_name} from namespace {namespace}")
    except ApiException as e:
        if e.status != 404:
            logger.error(f"Error deleting endpoints: {e}")

    # Delete service
    try:
        v1.delete_namespaced_service(service_name, namespace)
        logger.info(f"Deleted maintenance proxy service {service_name} from namespace {namespace}")
    except ApiException as e:
        if e.status != 404:
            logger.error(f"Error deleting maintenance proxy service: {e}")


def update_all_proxy_endpoints():
    """Update all proxy service endpoints across all namespaces to point to current operator pods"""
    try:
        # Get current operator pod IPs
        pod_ips = get_maintenance_pod_ips()
        if not pod_ips:
            logger.warning("No maintenance operator pods found, skipping endpoint updates")
            return

        # Find all proxy services across all namespaces
        services = v1.list_service_for_all_namespaces(
            label_selector='app=maintenance-operator,managed-by=maintenance-operator'
        )

        updated_count = 0
        for service in services.items:
            service_name = service.metadata.name
            namespace = service.metadata.namespace

            # Skip if not a proxy service
            if not service_name.startswith(f"{MAINTENANCE_SERVICE_NAME}-proxy"):
                continue

            try:
                # Update the endpoints to point to current pod IPs
                endpoints = client.V1Endpoints(
                    metadata=client.V1ObjectMeta(
                        name=service_name,
                        namespace=namespace,
                        labels={'app': 'maintenance-operator', 'managed-by': 'maintenance-operator'}
                    ),
                    subsets=[client.V1EndpointSubset(
                        addresses=[client.V1EndpointAddress(ip=ip) for ip in pod_ips],
                        ports=[client.CoreV1EndpointPort(
                            name='http',
                            port=MAINTENANCE_SERVICE_PORT,
                            protocol='TCP'
                        )]
                    )]
                )

                v1.patch_namespaced_endpoints(service_name, namespace, endpoints)
                updated_count += 1
                logger.info(f"Updated endpoints for {service_name} in namespace {namespace} to {pod_ips}")
            except ApiException as e:
                logger.error(f"Error updating endpoints for {service_name} in {namespace}: {e}")

        if updated_count > 0:
            logger.info(f"Updated {updated_count} proxy service endpoint(s)")
    except Exception as e:
        logger.error(f"Error in update_all_proxy_endpoints: {e}")


def endpoint_reconciliation_worker():
    """Background worker to periodically reconcile proxy service endpoints"""
    logger.info("Endpoint reconciliation worker started")
    while True:
        try:
            time.sleep(300)  # Wait 5 minutes
            logger.debug("Running periodic endpoint reconciliation")
            update_all_proxy_endpoints()
        except Exception as e:
            logger.error(f"Error in endpoint reconciliation worker: {e}")
