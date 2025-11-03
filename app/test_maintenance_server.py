"""Tests for maintenance_server.py"""
import pytest
import json
from unittest.mock import patch

# Mock kubernetes config loading before importing the module
with patch('kubernetes.config.load_incluster_config'), \
     patch('kubernetes.config.load_kube_config'), \
     patch('kubernetes.client.CoreV1Api'):
    from maintenance_server import app


@pytest.fixture
def client():
    """Create a test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestHealthEndpoints:
    """Test health check endpoints"""

    def test_health_endpoint(self, client):
        """Test /health endpoint returns 200"""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'

    def test_ready_endpoint(self, client):
        """Test /ready endpoint returns 200"""
        response = client.get('/ready')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ready'


class TestMaintenancePage:
    """Test maintenance page serving"""

    def test_maintenance_page_html_default(self, client):
        """Test serving HTML maintenance page"""
        response = client.get('/', headers={'Accept': 'text/html'})
        assert response.status_code == 503
        assert b'<!DOCTYPE html>' in response.data
        assert b'maintenance' in response.data.lower() or b'Maintenance' in response.data

    def test_maintenance_page_json_default(self, client):
        """Test serving JSON maintenance response"""
        response = client.get('/', headers={'Accept': 'application/json'})
        assert response.status_code == 503
        assert response.content_type == 'application/json'
        data = json.loads(response.data)
        assert 'status' in data or 'message' in data

    def test_maintenance_page_xml_default(self, client):
        """Test serving XML maintenance response"""
        response = client.get('/', headers={'Accept': 'application/xml'})
        assert response.status_code == 503
        assert 'xml' in response.content_type
        assert b'<?xml' in response.data

    def test_maintenance_page_wildcard_returns_html(self, client):
        """Test wildcard accept header returns HTML"""
        response = client.get('/', headers={'Accept': '*/*'})
        assert response.status_code == 503
        assert 'text/html' in response.content_type

    def test_maintenance_page_no_accept_header(self, client):
        """Test missing accept header returns HTML"""
        response = client.get('/')
        assert response.status_code == 503
        assert 'text/html' in response.content_type


class TestContentNegotiation:
    """Test content type negotiation"""

    def test_multiple_accept_types_prefers_first(self, client):
        """Test that first acceptable type is served"""
        response = client.get('/', headers={'Accept': 'application/json, text/html'})
        assert response.status_code == 503
        # Should prefer JSON as it's first
        assert response.content_type == 'application/json'

    def test_unsupported_accept_type_returns_html(self, client):
        """Test unsupported accept type falls back to HTML"""
        response = client.get('/', headers={'Accept': 'application/pdf'})
        assert response.status_code == 503
        # Should fall back to HTML
        assert 'text/html' in response.content_type


class TestCustomPages:
    """Test custom maintenance pages"""

    def test_custom_page_via_header(self, client):
        """Test custom page selection via X-Maintenance-Page header"""
        # This would require the custom page to exist in ConfigMaps
        # For now, just test that the header is accepted
        response = client.get('/', headers={
            'Accept': 'text/html',
            'X-Maintenance-Page': 'custom-page'
        })
        assert response.status_code == 503

    def test_default_page_when_no_header(self, client):
        """Test default page is served when no custom page header"""
        response = client.get('/', headers={'Accept': 'text/html'})
        assert response.status_code == 503
        assert 'text/html' in response.content_type


class TestErrorHandling:
    """Test error handling"""

    def test_404_on_nonexistent_path(self, client):
        """Test 404 for non-existent paths returns maintenance page"""
        response = client.get('/nonexistent')
        # Should still serve maintenance page
        assert response.status_code in [503, 404]

    def test_post_request_returns_maintenance(self, client):
        """Test POST request returns maintenance page"""
        response = client.post('/')
        assert response.status_code == 503

    def test_put_request_returns_maintenance(self, client):
        """Test PUT request returns maintenance page"""
        response = client.put('/')
        assert response.status_code == 503


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
