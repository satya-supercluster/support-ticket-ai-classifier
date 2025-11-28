"""
FastAPI Application for Ticket Classification API
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest
from prometheus_client.core import CollectorRegistry
from starlette.responses import Response
import logging
from datetime import datetime
import uuid

from config import settings
from classifier import TicketInput, ClassificationOutput, classifier
from evaluator import evaluator, EvaluationResult

# Setup logging
logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
registry = CollectorRegistry()
classification_counter = Counter(
    'ticket_classifications_total',
    'Total number of ticket classifications',
    ['category', 'priority'],
    registry=registry
)
classification_duration = Histogram(
    'ticket_classification_duration_seconds',
    'Time spent classifying tickets',
    registry=registry
)
classification_errors = Counter(
    'ticket_classification_errors_total',
    'Total number of classification errors',
    registry=registry
)

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="AI-Powered Support Ticket Classification System"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.api_title,
        "version": settings.api_version,
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post(
    "/classify",
    response_model=ClassificationOutput,
    status_code=status.HTTP_200_OK
)
async def classify_ticket(ticket_data: dict):
    """
    Classify a support ticket
    
    Request body:
    {
        "subject": "Cannot log into my account",
        "description": "I've been trying to log in for the past hour...",
        "customer_email": "user@example.com",
        "source": "email"
    }
    """
    try:
        # Generate ticket ID if not provided
        if "ticket_id" not in ticket_data:
            ticket_data["ticket_id"] = f"TKT-{uuid.uuid4().hex[:8].upper()}"
        
        # Create ticket input
        ticket = TicketInput(**ticket_data)
        
        logger.info(f"Processing ticket {ticket.ticket_id}")
        
        # Classify ticket (timed)
        with classification_duration.time():
            classification = await classifier.classify_ticket(ticket)
        
        # Update metrics
        classification_counter.labels(
            category=classification.category,
            priority=classification.priority
        ).inc()
        
        logger.info(
            f"Ticket {ticket.ticket_id} classified: "
            f"{classification.category} - {classification.priority}"
        )
        
        return classification
        
    except ValueError as e:
        classification_errors.inc()
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        classification_errors.inc()
        logger.error(f"Classification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during classification"
        )


@app.post(
    "/evaluate",
    response_model=EvaluationResult,
    status_code=status.HTTP_200_OK
)
async def evaluate_classification(evaluation_data: dict):
    """
    Evaluate a classification result
    
    Request body:
    {
        "ticket": {...},
        "classification": {...},
        "ground_truth": {...} (optional)
    }
    """
    try:
        ticket = TicketInput(**evaluation_data["ticket"])
        classification = ClassificationOutput(**evaluation_data["classification"])
        ground_truth = None
        
        if "ground_truth" in evaluation_data:
            ground_truth = ClassificationOutput(**evaluation_data["ground_truth"])
        
        result = await evaluator.evaluate_classification(
            ticket, classification, ground_truth
        )
        
        logger.info(f"Evaluation complete. Score: {result.overall_score}")
        return result
        
    except Exception as e:
        logger.error(f"Evaluation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during evaluation"
        )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(registry),
        media_type="text/plain"
    )


@app.get("/config")
async def get_config():
    """Get current configuration (non-sensitive)"""
    return {
        "categories": settings.categories,
        "priorities": settings.priorities,
        "model_deployment": settings.azure_openai_deployment,
        "temperature": settings.temperature
    }


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower()
    )