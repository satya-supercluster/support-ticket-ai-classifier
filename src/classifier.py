"""
Ticket Classification System using LangChain and LangGraph
"""
from langchain_openai import AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field
from typing import TypedDict, Annotated
import operator
from datetime import datetime
import logging

from config import settings

logger = logging.getLogger(__name__)


# Data Models
class TicketInput(BaseModel):
    """Input ticket model"""
    ticket_id: str
    subject: str
    description: str
    customer_email: str
    source: str = "email"  # email, chat, portal
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ClassificationOutput(BaseModel):
    """Classification result model"""
    category: str = Field(description="The ticket category")
    priority: str = Field(description="The priority level")
    confidence: float = Field(description="Confidence score between 0 and 1")
    reasoning: str = Field(description="Brief explanation for the classification")
    suggested_team: str = Field(description="Team to handle this ticket")


# LangGraph State
class ClassifierState(TypedDict):
    """State for the classification workflow"""
    ticket: TicketInput
    classification: ClassificationOutput | None
    validation_passed: bool
    retry_count: Annotated[int, operator.add]
    error: str | None


class TicketClassifier:
    """Main classifier using LangChain and LangGraph"""
    
    def __init__(self):
        # Initialize Azure OpenAI LLM
        self.llm = AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            azure_deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )
        
        # Create output parser
        self.parser = PydanticOutputParser(pydantic_object=ClassificationOutput)
        
        # Build the classification workflow
        self.workflow = self._build_workflow()
    
    def _create_classification_prompt(self) -> ChatPromptTemplate:
        """Create the classification prompt template"""
        template = """You are an expert customer support ticket classifier.

Analyze the following support ticket and classify it into the appropriate category and priority level.

TICKET INFORMATION:
Subject: {subject}
Description: {description}
Customer: {customer_email}
Source: {source}

CATEGORIES: {categories}
PRIORITIES: {priorities}

PRIORITY GUIDELINES:
- Critical: System down, data loss, security breach, revenue-impacting
- High: Major functionality broken, affecting multiple users
- Medium: Feature not working as expected, workarounds available
- Low: Questions, minor issues, feature requests

TEAM ASSIGNMENT:
- Billing → Finance Team
- Technical → Engineering Team
- Feature Request → Product Team
- Bug Report → Engineering Team
- Account Management → Customer Success Team

{format_instructions}

Provide your classification with reasoning."""

        return ChatPromptTemplate.from_template(template)
    
    def _classify_node(self, state: ClassifierState) -> ClassifierState:
        """Node: Perform classification"""
        try:
            logger.info(f"Classifying ticket {state['ticket'].ticket_id}")
            
            prompt = self._create_classification_prompt()
            format_instructions = self.parser.get_format_instructions()
            
            chain = prompt | self.llm | self.parser
            
            result = chain.invoke({
                "subject": state["ticket"].subject,
                "description": state["ticket"].description,
                "customer_email": state["ticket"].customer_email,
                "source": state["ticket"].source,
                "categories": ", ".join(settings.categories),
                "priorities": ", ".join(settings.priorities),
                "format_instructions": format_instructions
            })
            
            state["classification"] = result
            state["error"] = None
            logger.info(f"Classification complete: {result.category} - {result.priority}")
            
        except Exception as e:
            logger.error(f"Classification error: {str(e)}")
            state["error"] = str(e)
            state["retry_count"] = 1
        
        return state
    
    def _validate_node(self, state: ClassifierState) -> ClassifierState:
        """Node: Validate classification results"""
        if state["classification"] is None:
            state["validation_passed"] = False
            return state
        
        classification = state["classification"]
        
        # Validate category
        if classification.category not in settings.categories:
            logger.warning(f"Invalid category: {classification.category}")
            state["validation_passed"] = False
            return state
        
        # Validate priority
        if classification.priority not in settings.priorities:
            logger.warning(f"Invalid priority: {classification.priority}")
            state["validation_passed"] = False
            return state
        
        # Validate confidence score
        if not (0 <= classification.confidence <= 1):
            logger.warning(f"Invalid confidence: {classification.confidence}")
            state["validation_passed"] = False
            return state
        
        state["validation_passed"] = True
        logger.info("Validation passed")
        return state
    
    def _should_retry(self, state: ClassifierState) -> str:
        """Conditional edge: Determine if retry is needed"""
        if state["validation_passed"]:
            return "success"
        elif state["retry_count"] >= 3:
            return "failed"
        else:
            return "retry"
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(ClassifierState)
        
        # Add nodes
        workflow.add_node("classify", self._classify_node)
        workflow.add_node("validate", self._validate_node)
        
        # Add edges
        workflow.set_entry_point("classify")
        workflow.add_edge("classify", "validate")
        
        # Conditional edges based on validation
        workflow.add_conditional_edges(
            "validate",
            self._should_retry,
            {
                "success": END,
                "retry": "classify",
                "failed": END
            }
        )
        
        return workflow.compile()
    
    async def classify_ticket(self, ticket: TicketInput) -> ClassificationOutput:
        """Main method to classify a ticket"""
        initial_state: ClassifierState = {
            "ticket": ticket,
            "classification": None,
            "validation_passed": False,
            "retry_count": 0,
            "error": None
        }
        
        # Execute the workflow
        final_state = await self.workflow.ainvoke(initial_state)
        
        if final_state["classification"] is None:
            raise ValueError(f"Classification failed: {final_state['error']}")
        
        return final_state["classification"]


# Singleton instance
classifier = TicketClassifier()