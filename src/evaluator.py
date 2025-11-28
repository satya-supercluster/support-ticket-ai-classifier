"""
LLM-Based Evaluation System for Classification Quality
"""
from langchain_openai import AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List
import logging

from config import settings
from classifier import TicketInput, ClassificationOutput

logger = logging.getLogger(__name__)


class EvaluationResult(BaseModel):
    """Evaluation result model"""
    accuracy_score: float = Field(description="Score 0-1 for accuracy")
    category_correct: bool = Field(description="Is the category correct?")
    priority_correct: bool = Field(description="Is the priority correct?")
    reasoning_quality: float = Field(description="Score 0-1 for reasoning quality")
    feedback: str = Field(description="Detailed feedback")
    overall_score: float = Field(description="Overall score 0-1")


class MetricsReport(BaseModel):
    """Aggregated metrics report"""
    total_tickets: int
    avg_confidence: float
    avg_evaluation_score: float
    category_distribution: dict[str, int]
    priority_distribution: dict[str, int]
    accuracy_rate: float


class ClassificationEvaluator:
    """Evaluates classification quality using LLM-as-Judge pattern"""
    
    def __init__(self):
        self.llm = AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            azure_deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version,
            temperature=0.0,
            max_tokens=800,
        )
        self.parser = PydanticOutputParser(pydantic_object=EvaluationResult)
    
    def _create_evaluation_prompt(self) -> ChatPromptTemplate:
        """Create evaluation prompt"""
        template = """You are an expert evaluator for a ticket classification system.

Evaluate the quality of this classification:

ORIGINAL TICKET:
Subject: {subject}
Description: {description}

CLASSIFICATION RESULT:
Category: {category}
Priority: {priority}
Confidence: {confidence}
Reasoning: {reasoning}
Suggested Team: {suggested_team}

EVALUATION CRITERIA:
1. Category Accuracy (0-1): Is the category appropriate for this ticket?
2. Priority Accuracy (0-1): Is the priority level justified?
3. Reasoning Quality (0-1): Is the reasoning clear and logical?
4. Overall Quality (0-1): How good is the classification overall?

Consider:
- Does the category match the ticket content?
- Is the priority appropriate given the issue severity?
- Is the reasoning well-explained?
- Would this classification help route the ticket effectively?

{format_instructions}

Provide detailed evaluation with constructive feedback."""

        return ChatPromptTemplate.from_template(template)
    
    async def evaluate_classification(
        self, 
        ticket: TicketInput,
        classification: ClassificationOutput,
        ground_truth: ClassificationOutput | None = None
    ) -> EvaluationResult:
        """Evaluate a single classification"""
        try:
            prompt = self._create_evaluation_prompt()
            format_instructions = self.parser.get_format_instructions()
            
            chain = prompt | self.llm | self.parser
            
            result = chain.invoke({
                "subject": ticket.subject,
                "description": ticket.description,
                "category": classification.category,
                "priority": classification.priority,
                "confidence": classification.confidence,
                "reasoning": classification.reasoning,
                "suggested_team": classification.suggested_team,
                "format_instructions": format_instructions
            })
            
            # If ground truth is provided, compare
            if ground_truth:
                result.category_correct = (
                    classification.category == ground_truth.category
                )
                result.priority_correct = (
                    classification.priority == ground_truth.priority
                )
            
            logger.info(f"Evaluation complete. Overall score: {result.overall_score}")
            return result
            
        except Exception as e:
            logger.error(f"Evaluation error: {str(e)}")
            raise
    
    def calculate_metrics(
        self,
        evaluations: List[tuple[ClassificationOutput, EvaluationResult]]
    ) -> MetricsReport:
        """Calculate aggregated metrics"""
        if not evaluations:
            raise ValueError("No evaluations provided")
        
        total = len(evaluations)
        
        # Calculate averages
        avg_confidence = sum(
            c.confidence for c, _ in evaluations
        ) / total
        
        avg_eval_score = sum(
            e.overall_score for _, e in evaluations
        ) / total
        
        # Category distribution
        category_dist = {}
        for classification, _ in evaluations:
            cat = classification.category
            category_dist[cat] = category_dist.get(cat, 0) + 1
        
        # Priority distribution
        priority_dist = {}
        for classification, _ in evaluations:
            pri = classification.priority
            priority_dist[pri] = priority_dist.get(pri, 0) + 1
        
        # Accuracy rate (if ground truth was provided)
        accuracy_count = sum(
            1 for _, e in evaluations 
            if e.category_correct and e.priority_correct
        )
        accuracy_rate = accuracy_count / total
        
        return MetricsReport(
            total_tickets=total,
            avg_confidence=round(avg_confidence, 3),
            avg_evaluation_score=round(avg_eval_score, 3),
            category_distribution=category_dist,
            priority_distribution=priority_dist,
            accuracy_rate=round(accuracy_rate, 3)
        )


# Singleton instance
evaluator = ClassificationEvaluator()