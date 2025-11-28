import pytest
from fastapi.testclient import TestClient
from datetime import datetime

from src.main import app
from src.classifier import TicketInput, ClassificationOutput
from src.config import settings


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def sample_ticket():
    """Sample ticket for testing"""
    return TicketInput(
        ticket_id="TEST-001",
        subject="Cannot access billing portal",
        description="I'm getting a 404 error when trying to access the billing section",
        customer_email="test@example.com",
        source="email",
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_classification():
    """Sample classification result"""
    return ClassificationOutput(
        category="Billing",
        priority="High",
        confidence=0.92,
        reasoning="User cannot access critical billing functionality",
        suggested_team="Finance Team",
    )
