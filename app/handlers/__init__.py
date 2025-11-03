"""
Handlers package for Maintenance Operator
Exports handlers for Ingress and IngressRoute resources
"""

from .ingress import handle_ingress
from .traefik import handle_ingressroute

__all__ = ['handle_ingress', 'handle_ingressroute']
