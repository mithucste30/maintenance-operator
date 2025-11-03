#!/usr/bin/env python3
"""
Maintenance Operator
Watches Ingress and IngressRoute resources for maintenance label
and redirects traffic to maintenance page when label is present
"""

import logging
import threading
import kopf

from utils import update_all_proxy_endpoints, endpoint_reconciliation_worker
from handlers import handle_ingress, handle_ingressroute

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    """Configure operator settings"""
    settings.persistence.finalizer = 'maintenance-operator.kahf.io/finalizer'
    settings.posting.enabled = True
    logger.info("Maintenance Operator started")

    # Update all existing proxy endpoints on startup
    update_all_proxy_endpoints()

    # Start background thread for periodic reconciliation
    reconciliation_thread = threading.Thread(target=endpoint_reconciliation_worker, daemon=True)
    reconciliation_thread.start()
    logger.info("Started endpoint reconciliation background thread")
