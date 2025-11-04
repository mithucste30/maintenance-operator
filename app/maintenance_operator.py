#!/usr/bin/env python3
"""
Maintenance Operator
Watches Ingress and IngressRoute resources for maintenance label
and redirects traffic to maintenance page when label is present
"""

import logging
import kopf

from handlers import handle_ingress, handle_ingressroute

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    """Configure operator settings"""
    settings.persistence.finalizer = 'maintenance-operator.mithucste30.io/finalizer'
    settings.posting.enabled = True
    logger.info("Maintenance Operator started")
