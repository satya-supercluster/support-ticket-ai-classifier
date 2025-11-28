"""
Comprehensive monitoring and metrics collection for observability
"""
import time
import functools
from typing import Callable, Any, Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from threading import Lock
import logging

from prometheus_client import (
    Counter, Histogram, Gauge, Summary, Info,
    CollectorRegistry, generate_latest
)
from opencensus.ext.azure import metrics_exporter
from opencensus.stats import aggregation as aggregation_module
from opencensus.stats import measure as measure_module
from opencensus.stats import stats as stats_module
from opencensus.stats import view as view_module
from opencensus.tags import tag_map as tag_map_module

from config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Prometheus Metrics
# ============================================================================

# Create a custom registry (optional, can use default)
registry = CollectorRegistry()

# Counters - Monotonically increasing values
classification_counter = Counter(
    'ticket_classifications_total',
    'Total number of ticket classifications',
    ['category', 'priority', 'status'],
    registry=registry
)

evaluation_counter = Counter(
    'ticket_evaluations_total',
    'Total number of ticket evaluations',
    ['result'],
    registry=registry
)

error_counter = Counter(
    'errors_total',
    'Total number of errors',
    ['error_type', 'operation'],
    registry=registry
)

api_requests_counter = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status_code'],
    registry=registry
)

# Histograms - Distribution of values with buckets
classification_duration = Histogram(
    'classification_duration_seconds',
    'Time spent classifying tickets',
    ['category'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    registry=registry
)

evaluation_duration = Histogram(
    'evaluation_duration_seconds',
    'Time spent evaluating classifications',
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0],
    registry=registry
)

api_request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
    registry=registry
)

# Gauges - Values that can go up and down
active_classifications = Gauge(
    'active_classifications',
    'Number of classifications currently in progress',
    registry=registry
)

classification_confidence = Gauge(
    'classification_confidence_current',
    'Most recent classification confidence score',
    ['category'],
    registry=registry
)

# Summary - Similar to Histogram but calculates quantiles
classification_size = Summary(
    'classification_input_size_bytes',
    'Size of classification input in bytes',
    registry=registry
)

# Info - Static information
app_info = Info(
    'ticket_classifier_app',
    'Application information',
    registry=registry
)
app_info.info({
    'version': settings.api_version,
    'python_version': '3.11',
    'model': settings.azure_openai_deployment
})


# ============================================================================
# Azure Application Insights Integration
# ============================================================================

class AzureMetricsExporter:
    """Wrapper for Azure Application Insights metrics"""
    
    def __init__(self):
        self.exporter = None
        self.stats = stats_module.stats
        self.view_manager = self.stats.view_manager
        
        if settings.appinsights_connection_string:
            try:
                self.exporter = metrics_exporter.new_metrics_exporter(
                    connection_string=settings.appinsights_connection_string
                )
                self.view_manager.register_exporter(self.exporter)
                logger.info("Azure metrics exporter initialized")
            except Exception as e:
                logger.warning(f"Could not initialize Azure metrics: {e}")
    
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a custom metric to Azure"""
        if not self.exporter:
            return
        
        try:
            measure = measure_module.MeasureFloat(name, name, "units")
            
            mmap = self.stats.stats_recorder.new_measurement_map()
            tmap = tag_map_module.TagMap()
            
            if tags:
                for key, val in tags.items():
                    tmap.insert(key, val)
            
            mmap.measure_float_put(measure, value)
            mmap.record(tmap)
        except Exception as e:
            logger.error(f"Error recording Azure metric: {e}")


azure_metrics = AzureMetricsExporter()


# ============================================================================
# Monitoring Decorators
# ============================================================================

def monitor_classification(func: Callable) -> Callable:
    """
    Decorator to monitor classification operations
    
    Tracks:
    - Duration
    - Success/failure
    - Category distribution
    - Confidence scores
    
    Example:
        @monitor_classification
        async def classify_ticket(ticket: TicketInput):
            ...
    """
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        active_classifications.inc()
        
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            
            # Record metrics
            category = result.category
            priority = result.priority
            confidence = result.confidence
            
            classification_counter.labels(
                category=category,
                priority=priority,
                status='success'
            ).inc()
            
            classification_duration.labels(category=category).observe(duration)
            classification_confidence.labels(category=category).set(confidence)
            
            # Azure metrics
            azure_metrics.record_metric(
                'classification.duration',
                duration * 1000,  # Convert to ms
                tags={'category': category, 'priority': priority}
            )
            
            azure_metrics.record_metric(
                'classification.confidence',
                confidence,
                tags={'category': category}
            )
            
            logger.info(
                f"Classification monitored: {category}/{priority} "
                f"(confidence: {confidence:.2f}, duration: {duration:.2f}s)"
            )
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            
            classification_counter.labels(
                category='unknown',
                priority='unknown',
                status='error'
            ).inc()
            
            error_counter.labels(
                error_type=type(e).__name__,
                operation='classification'
            ).inc()
            
            logger.error(f"Classification error monitored: {str(e)}")
            raise
            
        finally:
            active_classifications.dec()
    
    return wrapper


def monitor_api_request(func: Callable) -> Callable:
    """
    Decorator to monitor API requests
    
    Tracks:
    - Request count
    - Response time
    - Status codes
    - Error rates
    
    Example:
        @app.post("/classify")
        @monitor_api_request
        async def classify_endpoint(data: dict):
            ...
    """
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract request info (this is FastAPI-specific)
        request = kwargs.get('request') or (args[0] if args else None)
        method = request.method if request else 'UNKNOWN'
        path = request.url.path if request else 'UNKNOWN'
        
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            api_requests_counter.labels(
                method=method,
                endpoint=path,
                status_code=status_code
            ).inc()
            
            api_request_duration.labels(
                method=method,
                endpoint=path
            ).observe(duration)
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            
            api_requests_counter.labels(
                method=method,
                endpoint=path,
                status_code=500
            ).inc()
            
            error_counter.labels(
                error_type=type(e).__name__,
                operation='api_request'
            ).inc()
            
            raise
    
    return wrapper


def monitor_performance(operation: str):
    """
    Decorator factory for monitoring arbitrary operations
    
    Example:
        @monitor_performance("database_query")
        def fetch_tickets():
            ...
    """
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                azure_metrics.record_metric(
                    f'{operation}.duration',
                    duration * 1000,
                    tags={'status': 'success'}
                )
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                
                error_counter.labels(
                    error_type=type(e).__name__,
                    operation=operation
                ).inc()
                
                azure_metrics.record_metric(
                    f'{operation}.duration',
                    duration * 1000,
                    tags={'status': 'error'}
                )
                
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                azure_metrics.record_metric(
                    f'{operation}.duration',
                    duration * 1000,
                    tags={'status': 'success'}
                )
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                
                error_counter.labels(
                    error_type=type(e).__name__,
                    operation=operation
                ).inc()
                
                azure_metrics.record_metric(
                    f'{operation}.duration',
                    duration * 1000,
                    tags={'status': 'error'}
                )
                
                raise
        
        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# ============================================================================
# Manual Metrics Recording
# ============================================================================

class MetricsRecorder:
    """Manual metrics recording for complex scenarios"""
    
    @staticmethod
    def record_classification(
        category: str,
        priority: str,
        confidence: float,
        duration_seconds: float,
        success: bool = True
    ):
        """Record classification metrics manually"""
        status = 'success' if success else 'error'
        
        classification_counter.labels(
            category=category,
            priority=priority,
            status=status
        ).inc()
        
        if success:
            classification_duration.labels(category=category).observe(duration_seconds)
            classification_confidence.labels(category=category).set(confidence)
            
            azure_metrics.record_metric(
                'classification.confidence',
                confidence,
                tags={'category': category, 'priority': priority}
            )
    
    @staticmethod
    def record_evaluation(
        evaluation_score: float,
        category_correct: bool,
        priority_correct: bool
    ):
        """Record evaluation metrics manually"""
        result = 'accurate' if category_correct and priority_correct else 'inaccurate'
        
        evaluation_counter.labels(result=result).inc()
        
        azure_metrics.record_metric(
            'evaluation.score',
            evaluation_score,
            tags={'result': result}
        )
    
    @staticmethod
    def record_error(error_type: str, operation: str):
        """Record error manually"""
        error_counter.labels(
            error_type=error_type,
            operation=operation
        ).inc()


# ============================================================================
# Health Checks
# ============================================================================

class HealthChecker:
    """System health monitoring"""
    
    def __init__(self):
        self.checks = {}
        self.lock = Lock()
    
    def register_check(self, name: str, check_func: Callable[[], bool]):
        """Register a health check"""
        with self.lock:
            self.checks[name] = check_func
    
    def check_health(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {}
        }
        
        all_healthy = True
        
        with self.lock:
            for name, check_func in self.checks.items():
                try:
                    is_healthy = check_func()
                    results['checks'][name] = {
                        'status': 'healthy' if is_healthy else 'unhealthy',
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    if not is_healthy:
                        all_healthy = False
                except Exception as e:
                    results['checks'][name] = {
                        'status': 'error',
                        'error': str(e),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    all_healthy = False
        
        results['status'] = 'healthy' if all_healthy else 'unhealthy'
        return results


health_checker = HealthChecker()


# ============================================================================
# Metrics Aggregator
# ============================================================================

class MetricsAggregator:
    """Aggregate metrics over time windows"""
    
    def __init__(self):
        self.data = defaultdict(list)
        self.lock = Lock()
    
    def record(self, metric_name: str, value: float, tags: Optional[Dict] = None):
        """Record a metric value"""
        with self.lock:
            key = f"{metric_name}:{tags}" if tags else metric_name
            self.data[key].append({
                'value': value,
                'timestamp': datetime.utcnow()
            })
    
    def get_stats(self, metric_name: str, window_minutes: int = 5) -> Dict[str, float]:
        """Get aggregated statistics for a metric"""
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        
        with self.lock:
            values = [
                item['value'] 
                for item in self.data.get(metric_name, [])
                if item['timestamp'] > cutoff
            ]
        
        if not values:
            return {}
        
        return {
            'count': len(values),
            'mean': sum(values) / len(values),
            'min': min(values),
            'max': max(values),
            'sum': sum(values)
        }
    
    def cleanup(self, retention_hours: int = 24):
        """Remove old data"""
        cutoff = datetime.utcnow() - timedelta(hours=retention_hours)
        
        with self.lock:
            for key in list(self.data.keys()):
                self.data[key] = [
                    item for item in self.data[key]
                    if item['timestamp'] > cutoff
                ]
                if not self.data[key]:
                    del self.data[key]


metrics_aggregator = MetricsAggregator()


# ============================================================================
# Helper Functions
# ============================================================================

def get_prometheus_metrics() -> bytes:
    """Get Prometheus metrics in text format"""
    return generate_latest(registry)


def get_metrics_summary() -> Dict[str, Any]:
    """Get a summary of current metrics"""
    return {
        'classifications': {
            'total': classification_counter._value.sum(),
            'active': active_classifications._value.get()
        },
        'errors': {
            'total': error_counter._value.sum()
        },
        'api_requests': {
            'total': api_requests_counter._value.sum()
        },
        'timestamp': datetime.utcnow().isoformat()
    }


# Initialize health checks
def check_metrics_available() -> bool:
    """Check if metrics are being collected"""
    return True  # Basic check, can be enhanced


health_checker.register_check('metrics', check_metrics_available)

logger.info("Monitoring module initialized")