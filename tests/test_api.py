from unittest.mock import patch
import time

from src.config import settings


def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_config_endpoint(client):
    """Test configuration endpoint"""
    response = client.get("/config")
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    assert "priorities" in data
    assert len(data["categories"]) == 5


def test_metrics_endpoint(client):
    """Test Prometheus metrics endpoint"""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"


@patch("src.classifier.TicketClassifier.classify_ticket")
def test_classify_endpoint_success(mock_classify, client, sample_classification):
    """Test successful classification"""
    mock_classify.return_value = sample_classification

    ticket_data = {
        "subject": "Cannot log in",
        "description": "Getting error 500",
        "customer_email": "user@test.com",
        "source": "portal",
    }

    response = client.post("/classify", json=ticket_data)
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "Billing"
    assert data["priority"] == "High"
    assert "confidence" in data


def test_classify_endpoint_missing_fields(client):
    """Test classification with missing required fields"""
    ticket_data = {
        "subject": "Test"
        # Missing description
    }

    response = client.post("/classify", json=ticket_data)
    assert response.status_code == 422  # Validation error


def test_classify_endpoint_generates_ticket_id(client, sample_classification):
    """Test that ticket ID is auto-generated if not provided"""
    with patch("src.classifier.TicketClassifier.classify_ticket", return_value=sample_classification):
        ticket_data = {
            "subject": "Test ticket",
            "description": "Test description",
            "customer_email": "test@test.com",
        }

        response = client.post("/classify", json=ticket_data)
        assert response.status_code == 200


def test_classify_endpoint_internal_error(client):
    """Test handling of internal errors"""
    with patch("src.classifier.TicketClassifier.classify_ticket", side_effect=Exception("Test error")):
        ticket_data = {
            "subject": "Test",
            "description": "Test description",
            "customer_email": "test@test.com",
        }

        response = client.post("/classify", json=ticket_data)
        assert response.status_code == 500
        assert "error" in response.json()


def test_prometheus_metrics_updated(client, sample_classification):
    """Test that metrics are updated on classification"""
    from src.config import settings  # just to ensure config import works

    with patch("src.classifier.TicketClassifier.classify_ticket", return_value=sample_classification):
        ticket_data = {
            "subject": "Test",
            "description": "Test",
            "customer_email": "test@test.com",
        }

        # Make classification request
        client.post("/classify", json=ticket_data)

        # Check metrics endpoint
        response = client.get("/metrics")
        assert response.status_code == 200
        content = response.text
        assert "ticket_classifications_total" in content


def test_classification_performance(client, sample_classification):
    """Test classification response time"""
    with patch("src.classifier.TicketClassifier.classify_ticket", return_value=sample_classification):
        ticket_data = {
            "subject": "Test",
            "description": "Test description",
            "customer_email": "test@test.com",
        }

        start = time.time()
        response = client.post("/classify", json=ticket_data)
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 5.0  # Should respond within 5 seconds
