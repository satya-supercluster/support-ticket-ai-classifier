"""
Centralized logging configuration with structured logging and Azure integration
"""
import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict
from pythonjsonlogger import jsonlogger
from opencensus.ext.azure.log_exporter import AzureLogHandler
from config import settings

 
class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional context"""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """Add custom fields to log records"""
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp in ISO format
        log_record['timestamp'] = datetime.utcnow().isoformat()
        
        # Add log level
        log_record['level'] = record.levelname
        
        # Add logger name
        log_record['logger'] = record.name
        
        # Add application info
        log_record['application'] = settings.api_title
        log_record['version'] = settings.api_version
        
        # Add custom fields if present
        if hasattr(record, 'ticket_id'):
            log_record['ticket_id'] = record.ticket_id
        
        if hasattr(record, 'category'):
            log_record['category'] = record.category
        
        if hasattr(record, 'confidence'):
            log_record['confidence'] = record.confidence
        
        if hasattr(record, 'user_email'):
            log_record['user_email'] = record.user_email
        
        if hasattr(record, 'duration_ms'):
            log_record['duration_ms'] = record.duration_ms


def setup_logging() -> None:
    """
    Configure application-wide logging with multiple handlers
    
    Sets up:
    - Console output (JSON for production, readable for dev)
    - File output (JSON format)
    - Azure Application Insights (if configured)
    """
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Use JSON formatter for production, readable for development
    if settings.log_level.upper() == "DEBUG":
        # Development: Human-readable format
        console_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        # Production: JSON format
        console_format = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s'
        )
    
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)
    
    # File Handler (JSON format)
    try:
        file_handler = logging.FileHandler('logs/application.log')
        file_handler.setLevel(logging.INFO)
        file_formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    except (FileNotFoundError, PermissionError) as e:
        # Log to console if file logging fails
        root_logger.warning(f"Could not set up file logging: {e}")
    
    # Azure Application Insights Handler
    if settings.appinsights_connection_string:
        try:
            azure_handler = AzureLogHandler(
                connection_string=settings.appinsights_connection_string
            )
            azure_handler.setLevel(logging.WARNING)  # Only send warnings and errors to Azure
            root_logger.addHandler(azure_handler)
            root_logger.info("Azure Application Insights logging enabled")
        except Exception as e:
            root_logger.warning(f"Could not set up Azure logging: {e}")
    
    # Log startup message
    root_logger.info(
        "Logging configured",
        extra={
            'log_level': settings.log_level,
            'handlers': len(root_logger.handlers)
        }
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module
    
    Args:
        name: Name of the module/component
        
    Returns:
        Configured logger instance
        
    Example:
        logger = get_logger(__name__)
        logger.info("Processing ticket", extra={'ticket_id': 'TKT-001'})
    """
    return logging.getLogger(name)


class LogContext:
    """
    Context manager for adding contextual information to logs
    
    Example:
        with LogContext(ticket_id="TKT-001", user="user@example.com"):
            logger.info("Processing ticket")  # Will include ticket_id and user
    """
    
    def __init__(self, **kwargs):
        self.context = kwargs
        self.logger = logging.getLogger()
        self.old_factory = None
    
    def __enter__(self):
        self.old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)


class PerformanceLogger:
    """
    Context manager for logging operation performance
    
    Example:
        with PerformanceLogger("classification", logger, ticket_id="TKT-001"):
            result = classify_ticket(ticket)
        # Logs: "classification completed in 1234ms"
    """
    
    def __init__(self, operation: str, logger: logging.Logger, **context):
        self.operation = operation
        self.logger = logger
        self.context = context
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.utcnow()
        self.logger.info(
            f"{self.operation} started",
            extra=self.context
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (datetime.utcnow() - self.start_time).total_seconds() * 1000
        
        if exc_type is None:
            self.logger.info(
                f"{self.operation} completed",
                extra={**self.context, 'duration_ms': duration_ms}
            )
        else:
            self.logger.error(
                f"{self.operation} failed",
                extra={
                    **self.context,
                    'duration_ms': duration_ms,
                    'error_type': exc_type.__name__,
                    'error_message': str(exc_val)
                },
                exc_info=True
            )


def log_classification(
    logger: logging.Logger,
    ticket_id: str,
    category: str,
    priority: str,
    confidence: float,
    duration_ms: float
) -> None:
    """
    Helper function to log classification events with consistent structure
    
    Args:
        logger: Logger instance
        ticket_id: Ticket identifier
        category: Classification category
        priority: Classification priority
        confidence: Confidence score
        duration_ms: Processing time in milliseconds
    """
    logger.info(
        "Ticket classified",
        extra={
            'ticket_id': ticket_id,
            'category': category,
            'priority': priority,
            'confidence': confidence,
            'duration_ms': duration_ms,
            'event_type': 'classification'
        }
    )


def log_evaluation(
    logger: logging.Logger,
    ticket_id: str,
    evaluation_score: float,
    category_correct: bool,
    priority_correct: bool
) -> None:
    """
    Helper function to log evaluation events
    
    Args:
        logger: Logger instance
        ticket_id: Ticket identifier
        evaluation_score: Overall evaluation score
        category_correct: Whether category was correct
        priority_correct: Whether priority was correct
    """
    logger.info(
        "Classification evaluated",
        extra={
            'ticket_id': ticket_id,
            'evaluation_score': evaluation_score,
            'category_correct': category_correct,
            'priority_correct': priority_correct,
            'event_type': 'evaluation'
        }
    )


def log_error(
    logger: logging.Logger,
    error: Exception,
    operation: str,
    **context
) -> None:
    """
    Helper function to log errors with consistent structure
    
    Args:
        logger: Logger instance
        error: Exception that occurred
        operation: Operation that failed
        **context: Additional context
    """
    logger.error(
        f"{operation} failed: {str(error)}",
        extra={
            **context,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'operation': operation,
            'event_type': 'error'
        },
        exc_info=True
    )


# Initialize logging when module is imported
setup_logging()


# Example usage functions for documentation
def example_basic_logging():
    """Example: Basic logging"""
    logger = get_logger(__name__)
    
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")


def example_structured_logging():
    """Example: Structured logging with extra fields"""
    logger = get_logger(__name__)
    
    logger.info(
        "Processing ticket",
        extra={
            'ticket_id': 'TKT-001',
            'category': 'Technical',
            'customer_email': 'user@example.com'
        }
    )


def example_context_logging():
    """Example: Using LogContext"""
    logger = get_logger(__name__)
    
    with LogContext(ticket_id="TKT-001", user="user@example.com"):
        logger.info("Starting processing")
        # Do work...
        logger.info("Processing complete")
    # ticket_id and user will be in both log messages


def example_performance_logging():
    """Example: Using PerformanceLogger"""
    logger = get_logger(__name__)
    
    with PerformanceLogger("classification", logger, ticket_id="TKT-001"):
        # Do expensive operation
        import time
        time.sleep(1)
    # Logs duration automatically


def example_helper_functions():
    """Example: Using helper functions"""
    logger = get_logger(__name__)
    
    # Log classification
    log_classification(
        logger=logger,
        ticket_id="TKT-001",
        category="Technical",
        priority="High",
        confidence=0.95,
        duration_ms=1234.5
    )
    
    # Log evaluation
    log_evaluation(
        logger=logger,
        ticket_id="TKT-001",
        evaluation_score=0.92,
        category_correct=True,
        priority_correct=True
    )
    
    # Log error
    try:
        raise ValueError("Something went wrong")
    except ValueError as e:
        log_error(
            logger=logger,
            error=e,
            operation="classification",
            ticket_id="TKT-001"
        )