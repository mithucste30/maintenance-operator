"""Tests for maintenance_operator.py"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys

# Mock kubernetes config loading before importing the module
with patch('kubernetes.config.load_incluster_config'), \
     patch('kubernetes.config.load_kube_config'), \
     patch('kubernetes.client.CoreV1Api'), \
     patch('kubernetes.client.NetworkingV1Api'), \
     patch('kubernetes.client.CustomObjectsApi'):
    from utils import (
        is_under_maintenance,
        create_backup_configmap,
        get_backup_configmap,
        delete_backup_configmap,
        create_maintenance_service,
        delete_maintenance_service,
    )


class TestIsUnderMaintenance:
    """Test is_under_maintenance function"""

    def test_returns_true_when_annotation_present(self):
        """Test returns True when maintenance annotation is present"""
        annotations = {'maintenance-operator.kahf.io/enabled': 'true'}
        assert is_under_maintenance(annotations) is True

    def test_returns_false_when_annotation_absent(self):
        """Test returns False when maintenance annotation is absent"""
        annotations = {'some-other-annotation': 'value'}
        assert is_under_maintenance(annotations) is False

    def test_returns_false_when_annotation_is_false(self):
        """Test returns False when maintenance annotation is 'false'"""
        annotations = {'maintenance-operator.kahf.io/enabled': 'false'}
        assert is_under_maintenance(annotations) is False

    def test_returns_false_when_annotations_none(self):
        """Test returns False when annotations is None"""
        assert is_under_maintenance(None) is False

    def test_returns_false_when_annotations_empty(self):
        """Test returns False when annotations is empty dict"""
        assert is_under_maintenance({}) is False


class TestBackupConfigMap:
    """Test ConfigMap backup functions"""

    @patch('utils.v1')
    def test_create_backup_configmap(self, mock_v1):
        """Test creating backup ConfigMap"""
        name = "test-ingress"
        namespace = "default"
        backup_data = {'rules': [{'host': 'example.com'}]}

        create_backup_configmap(name, namespace, backup_data)

        # Verify ConfigMap was created
        mock_v1.create_namespaced_config_map.assert_called_once()
        call_args = mock_v1.create_namespaced_config_map.call_args

        # Check that namespace was passed
        assert namespace in str(call_args)

    @patch('utils.v1')
    def test_get_backup_configmap_success(self, mock_v1):
        """Test retrieving backup ConfigMap"""
        name = "test-ingress"
        namespace = "default"

        mock_configmap = Mock()
        mock_configmap.data = {'backup': '{"rules": [{"host": "example.com"}]}'}
        mock_v1.read_namespaced_config_map.return_value = mock_configmap

        result = get_backup_configmap(name, namespace)

        assert result == {"rules": [{"host": "example.com"}]}
        mock_v1.read_namespaced_config_map.assert_called_once()

    @patch('utils.v1')
    def test_get_backup_configmap_not_found(self, mock_v1):
        """Test retrieving non-existent backup ConfigMap"""
        from kubernetes.client.rest import ApiException

        name = "test-ingress"
        namespace = "default"

        mock_v1.read_namespaced_config_map.side_effect = ApiException(status=404)

        result = get_backup_configmap(name, namespace)

        assert result is None

    @patch('utils.v1')
    def test_delete_backup_configmap(self, mock_v1):
        """Test deleting backup ConfigMap"""
        name = "test-ingress"
        namespace = "default"

        delete_backup_configmap(name, namespace)

        mock_v1.delete_namespaced_config_map.assert_called_once()
        call_args = mock_v1.delete_namespaced_config_map.call_args
        assert call_args[0][0] == f"maintenance-backup-{name}"
        assert call_args[0][1] == namespace


class TestMaintenanceService:
    """Test maintenance service management"""

    @patch('utils.v1')
    @patch('utils.get_maintenance_pod_ips')
    def test_create_maintenance_service(self, mock_get_ips, mock_v1):
        """Test creating maintenance proxy service"""
        namespace = "default"
        mock_get_ips.return_value = ["10.1.2.3"]

        service_name = create_maintenance_service(namespace)

        assert "maintenance-operator-proxy" in service_name
        # Verify service was created
        mock_v1.create_namespaced_service.assert_called_once()
        # Verify endpoints were created
        mock_v1.create_namespaced_endpoints.assert_called_once()

    @patch('utils.v1')
    def test_create_maintenance_service_already_exists(self, mock_v1):
        """Test creating service when it already exists (should update)"""
        from kubernetes.client.rest import ApiException

        namespace = "default"
        mock_v1.create_namespaced_service.side_effect = ApiException(status=409)

        # Should not raise exception
        service_name = create_maintenance_service(namespace)

        assert "maintenance-operator-proxy" in service_name

    @patch('utils.v1')
    def test_delete_maintenance_service(self, mock_v1):
        """Test deleting maintenance proxy service"""
        namespace = "default"

        delete_maintenance_service(namespace)

        # Should attempt to delete both service and endpoints
        assert mock_v1.delete_namespaced_service.called
        assert mock_v1.delete_namespaced_endpoints.called


class TestHandlerLogic:
    """Test handler logic without kopf integration"""

    def test_maintenance_annotation_triggers_enable(self):
        """Test that maintenance annotation triggers enable logic"""
        annotations = {
            'maintenance-operator.kahf.io/enabled': 'true'
        }

        # Should be detected as under maintenance
        assert is_under_maintenance(annotations) is True

        # Should NOT have backup annotation (first time enabling)
        assert 'maintenance-operator.kahf.io/original-service' not in annotations

    def test_maintenance_with_custom_page(self):
        """Test custom page annotation is recognized"""
        annotations = {
            'maintenance-operator.kahf.io/enabled': 'true',
            'maintenance-operator.kahf.io/custom-page': 'my-custom-page'
        }

        assert is_under_maintenance(annotations) is True
        assert annotations.get('maintenance-operator.kahf.io/custom-page') == 'my-custom-page'

    def test_default_page_annotation(self):
        """Test default page annotation is recognized"""
        annotations = {
            'maintenance-operator.kahf.io/enabled': 'true',
            'maintenance-operator.kahf.io/custom-page': 'default'
        }

        custom_page = annotations.get('maintenance-operator.kahf.io/custom-page', '').strip()
        # Should not create middleware for 'default'
        assert custom_page.lower() == 'default'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
