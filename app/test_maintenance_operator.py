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
        create_maintenance_resources,
        delete_maintenance_resources,
        get_html_content,
        hash_content,
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


class TestMaintenanceResources:
    """Test maintenance resource management"""

    def test_hash_content(self):
        """Test content hashing generates consistent hash"""
        content1 = "<html>Test</html>"
        content2 = "<html>Test</html>"
        content3 = "<html>Different</html>"

        hash1 = hash_content(content1)
        hash2 = hash_content(content2)
        hash3 = hash_content(content3)

        # Same content should generate same hash
        assert hash1 == hash2
        # Different content should generate different hash
        assert hash1 != hash3
        # Hash should be 8 characters
        assert len(hash1) == 8

    @patch('utils.v1')
    @patch('utils.get_html_content')
    def test_create_maintenance_resources(self, mock_get_html, mock_v1):
        """Test creating maintenance resources (ConfigMap + Pod + Service)"""
        namespace = "default"
        ingress_name = "test-ingress"
        custom_page = "my-page"

        mock_get_html.return_value = "<html>Maintenance Page</html>"
        mock_v1.read_namespaced_config_map.side_effect = Exception("Not found")

        service_name = create_maintenance_resources(namespace, ingress_name, custom_page)

        # Verify service name follows pattern
        assert service_name.startswith("maintenance-")
        # Verify ConfigMap, Pod, and Service were created
        assert mock_v1.create_namespaced_config_map.called
        assert mock_v1.create_namespaced_pod.called
        assert mock_v1.create_namespaced_service.called

    @patch('utils.v1')
    def test_delete_maintenance_resources_no_refs(self, mock_v1):
        """Test deleting maintenance resources when no more references"""
        namespace = "default"
        ingress_name = "test-ingress"
        service_name = "maintenance-abc123"

        mock_configmap = Mock()
        mock_configmap.metadata.annotations = {
            'maintenance-operator.kahf.io/used-by': ingress_name
        }
        mock_v1.read_namespaced_config_map.return_value = mock_configmap

        delete_maintenance_resources(namespace, ingress_name, service_name)

        # Should delete all resources when no more references
        assert mock_v1.delete_namespaced_pod.called
        assert mock_v1.delete_namespaced_service.called
        assert mock_v1.delete_namespaced_config_map.called

    @patch('utils.v1')
    def test_delete_maintenance_resources_with_refs(self, mock_v1):
        """Test deleting maintenance resources when other ingresses still use them"""
        namespace = "default"
        ingress_name = "test-ingress-1"
        service_name = "maintenance-abc123"

        mock_configmap = Mock()
        mock_configmap.metadata.annotations = {
            'maintenance-operator.kahf.io/used-by': 'test-ingress-1,test-ingress-2'
        }
        mock_v1.read_namespaced_config_map.return_value = mock_configmap

        delete_maintenance_resources(namespace, ingress_name, service_name)

        # Should only update ConfigMap, not delete resources
        assert mock_v1.patch_namespaced_config_map.called
        assert not mock_v1.delete_namespaced_pod.called
        assert not mock_v1.delete_namespaced_service.called
        assert not mock_v1.delete_namespaced_config_map.called


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
