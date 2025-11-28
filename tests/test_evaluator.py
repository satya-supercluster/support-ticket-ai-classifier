import pytest
from unittest.mock import patch

from src.evaluator import ClassificationEvaluator, EvaluationResult


@pytest.mark.asyncio
async def test_evaluation_result_validation():
    """Test evaluation result model"""
    eval_result = EvaluationResult(
        accuracy_score=0.95,
        category_correct=True,
        priority_correct=True,
        reasoning_quality=0.90,
        feedback="Excellent classification",
        overall_score=0.93,
    )

    assert 0 <= eval_result.accuracy_score <= 1
    assert eval_result.category_correct is True
    assert eval_result.overall_score == 0.93


@pytest.mark.asyncio
async def test_evaluator_initialization():
    """Test evaluator initialization"""
    with patch("langchain_openai.AzureChatOpenAI"):
        evaluator = ClassificationEvaluator()
        assert evaluator.llm is not None
