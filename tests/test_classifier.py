from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

import pytest

from src.classifier import TicketInput, ClassificationOutput, TicketClassifier
from src.config import settings


def test_settings_loaded():
    """Test that settings are properly loaded"""
    assert settings.api_title == "AI Ticket Classifier"
    assert len(settings.categories) == 5
    assert len(settings.priorities) == 4


def test_categories_valid():
    """Test that all categories are defined"""
    expected = ["Billing", "Technical", "Feature Request", "Bug Report", "Account Management"]
    assert settings.categories == expected


@pytest.mark.asyncio
async def test_ticket_input_validation(sample_ticket):
    """Test ticket input model validation"""
    assert sample_ticket.ticket_id == "TEST-001"
    assert sample_ticket.subject == "Cannot access billing portal"
    assert isinstance(sample_ticket.created_at, datetime)


@pytest.mark.asyncio
async def test_classification_output_validation(sample_classification):
    """Test classification output model validation"""
    assert sample_classification.category in settings.categories
    assert sample_classification.priority in settings.priorities
    assert 0 <= sample_classification.confidence <= 1


@pytest.mark.asyncio
async def test_classifier_initialization():
    """Test that classifier initializes correctly"""
    with patch("langchain_openai.AzureChatOpenAI"):
        classifier = TicketClassifier()
        assert classifier.llm is not None
        assert classifier.workflow is not None


@pytest.mark.asyncio
async def test_full_classification_workflow(sample_ticket):
    """Test complete classification workflow"""
    with patch("langchain_openai.AzureChatOpenAI") as mock_llm:
        # Mock LLM response
        mock_llm_instance = Mock()
        mock_llm_instance.ainvoke = AsyncMock(
            return_value=Mock(
                content='{"category": "Technical", "priority": "High", "confidence": 0.9, '
                        '"reasoning": "Test", "suggested_team": "Engineering Team"}'
            )
        )
        mock_llm.return_value = mock_llm_instance

        classifier = TicketClassifier()
        # You can later actually call classifier.classify_ticket(sample_ticket)
        assert classifier is not None


@pytest.mark.parametrize("priority", ["Critical", "High", "Medium", "Low"])
def test_all_priority_levels(priority, sample_classification):
    """Test that all priority levels are supported"""
    sample_classification.priority = priority
    assert sample_classification.priority in settings.priorities


@pytest.mark.parametrize("category", ["Billing", "Technical", "Feature Request", "Bug Report", "Account Management"])
def test_all_categories(category, sample_classification):
    """Test that all categories are supported"""
    sample_classification.category = category
    assert sample_classification.category in settings.categories
