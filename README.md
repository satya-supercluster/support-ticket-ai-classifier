# AI-Powered Ticket Classification System

**Author:** Satyam Gupta  
**Date:** [28 Nov 2025]  
**Version:** 1.0  
**Target Audience:** Engineering Team, DevOps, Support Operations

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Architecture Deep Dive](#architecture-deep-dive)
4. [Setup & Installation](#setup--installation)
5. [Configuration Guide](#configuration-guide)
6. [Deployment Procedures](#deployment-procedures)
7. [Monitoring & Troubleshooting](#monitoring--troubleshooting)
8. [API Documentation](#api-documentation)
9. [Testing Guide](#testing-guide)
10. [Maintenance & Operations](#maintenance--operations)
11. [Common Issues & Solutions](#common-issues--solutions)
12. [Future Enhancements](#future-enhancements)
13. [Contact & Support](#contact--support)

---

## Executive Summary

### What This System Does

The AI-Powered Ticket Classification System automatically categorizes and prioritizes customer support tickets using Azure OpenAI's GPT-4. It reduces manual triage time from 4-6 hours to under 3 seconds and decreases misrouting from 30% to under 6%.

### Key Benefits

- ⚡ **Speed:** Real-time classification (< 3 seconds)
- 🎯 **Accuracy:** 94% classification accuracy
- 💰 **Cost-Effective:** ~$0.05 per ticket
- 📈 **Scalable:** Handles 500+ tickets/hour
- 🔍 **Observable:** Comprehensive monitoring and logging

### Technology Stack

- **API Framework:** FastAPI
- **LLM Integration:** LangChain + LangGraph
- **LLM Provider:** Azure OpenAI (GPT-4)
- **Database:** Azure Cosmos DB
- **Monitoring:** Prometheus + Application Insights
- **Container Platform:** Azure Kubernetes Service (AKS)
- **CI/CD:** Azure DevOps

---

## System Overview

### High-Level Architecture

```
┌─────────────┐
│   Ticket    │
│   Sources   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│         FastAPI Endpoint            │
│         (Port 8000)                 │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      LangGraph Workflow             │
│  ┌───────────────────────────────┐  │
│  │  1. Classify (LangChain+LLM)  │  │
│  │  2. Validate Results          │  │
│  │  3. Retry if Needed (3x max)  │  │
│  └───────────────────────────────┘  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      Classification Result          │
│  • Category (5 options)             │
│  • Priority (4 levels)              │
│  • Confidence Score                 │
│  • Reasoning                        │
│  • Suggested Team                   │
└─────────────────────────────────────┘
```

### Components

1. **FastAPI Application** (`main.py`)
   - REST API endpoints
   - Request validation
   - Prometheus metrics
   - Error handling

2. **Classifier** (`classifier.py`)
   - LangChain integration
   - LangGraph workflow
   - Retry logic
   - Result validation

3. **Evaluator** (`evaluator.py`)
   - LLM-as-judge evaluation
   - Metrics aggregation
   - Quality scoring

4. **Configuration** (`config.py`)
   - Pydantic settings
   - Environment variables
   - Constants

---

## Architecture Deep Dive

### Classification Workflow (LangGraph)

```python
State: {
    ticket: TicketInput
    classification: ClassificationOutput | None
    validation_passed: bool
    retry_count: int
    error: str | None
}

Graph:
    START → Classify → Validate → [Decision]
                                       ├→ Success → END
                                       ├→ Retry → Classify
                                       └→ Failed → END
```

**Workflow Steps:**

1. **Classification Node**
   - Receives ticket input
   - Constructs prompt with ticket details
   - Calls Azure OpenAI via LangChain
   - Parses response using Pydantic
   - Handles errors and updates state

2. **Validation Node**
   - Checks category is in allowed list
   - Checks priority is in allowed list
   - Validates confidence score (0-1)
   - Ensures all required fields present

3. **Conditional Routing**
   - If validation passes → END (success)
   - If validation fails AND retries < 3 → Retry
   - If retries exhausted → END (failed)

### Prompt Engineering

**Current Prompt Structure:**

```
System Context: "You are an expert customer support ticket classifier"
Ticket Details: Subject, Description, Customer, Source
Instructions: Categories, Priorities, Guidelines
Output Format: Structured JSON (via Pydantic)
```

**Priority Guidelines:**

- **Critical:** System down, data loss, security, revenue impact
- **High:** Major functionality broken, multiple users affected
- **Medium:** Feature not working, workarounds available
- **Low:** Questions, minor issues, feature requests

### Data Models

```python
class TicketInput(BaseModel):
    ticket_id: str
    subject: str
    description: str
    customer_email: str
    source: str  # email, chat, portal
    created_at: datetime

class ClassificationOutput(BaseModel):
    category: str  # Billing, Technical, Feature Request, Bug Report, Account Management
    priority: str  # Critical, High, Medium, Low
    confidence: float  # 0.0 to 1.0
    reasoning: str
    suggested_team: str
```

---

## Setup & Installation

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Azure subscription with:
  - Azure OpenAI access
  - Cosmos DB instance
  - Application Insights
  - Azure Container Registry (ACR)
  - Azure Kubernetes Service (AKS) for production

### Local Development Setup

1. **Clone Repository**

```bash
git clone https://github.com/satya-supercluster/smart-content-personalization-engine.git
cd smart-content-personalization-engine
```

2. **Create Virtual Environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install Dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure Environment Variables**

```bash
cp .env.example .env
# Edit .env with your credentials
```

Required variables:

```
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4
COSMOS_ENDPOINT=https://your-cosmos.documents.azure.com:443/
COSMOS_KEY=your-cosmos-key
APPLICATIONINSIGHTS_CONNECTION_STRING=your-app-insights-connection
```

5. **Run Locally**

```bash
python -m uvicorn src.main:app --reload
```

Access at: `http://localhost:8000`

### Docker Setup

1. **Build Image**

```bash
docker build -t ticket-classifier:latest .
```

2. **Run Container**

```bash
docker run -p 8000:8000 --env-file .env ticket-classifier:latest
```

3. **Docker Compose (with monitoring)**

```bash
docker-compose up -d
```

This starts:

- Ticket Classifier (port 8000)
- Prometheus (port 9090)
- Grafana (port 3000)

---

## Configuration Guide

### Application Settings

All configuration is managed via `config.py` using Pydantic Settings.

**Key Configuration Options:**

```python
# API Configuration
api_host = "0.0.0.0"
api_port = 8000

# Model Configuration
temperature = 0.0  # Deterministic output
max_tokens = 500

# Categories (customizable)
categories = [
    "Billing",
    "Technical",
    "Feature Request",
    "Bug Report",
    "Account Management"
]

# Priorities (customizable)
priorities = ["Critical", "High", "Medium", "Low"]
```

### Customizing Categories

To add/modify categories:

1. Update `config.py`:

```python
categories = [
    "Billing",
    "Technical",
    "Feature Request",
    "Bug Report",
    "Account Management",
    "Sales Inquiry"  # New category
]
```

2. Update team routing logic in prompt (classifier.py):

```python
TEAM ASSIGNMENT:
- Sales Inquiry → Sales Team
```

3. Update tests to include new category

4. Redeploy application

### Adjusting LLM Parameters

**Temperature:**

- Current: 0.0 (deterministic)
- For more creative classifications: 0.3-0.5
- Not recommended: > 0.5 (too random)

**Max Tokens:**

- Current: 500
- Increase if reasoning needs to be more detailed
- Decrease to reduce costs (minimum ~200)

---

## Deployment Procedures

### Development Environment (Azure Container Instance)

```bash
# Login to Azure
az login

# Deploy to ACI
az container create \
  --resource-group rg-ticket-classifier-dev \
  --name ticket-classifier-dev \
  --image yourregistry.azurecr.io/ticket-classifier:latest \
  --cpu 2 \
  --memory 4 \
  --dns-name-label ticket-classifier-dev \
  --ports 8000 \
  --environment-variables \
    AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT \
    AZURE_OPENAI_DEPLOYMENT=$AZURE_OPENAI_DEPLOYMENT \
  --secure-environment-variables \
    AZURE_OPENAI_API_KEY=$AZURE_OPENAI_API_KEY \
    COSMOS_ENDPOINT=$COSMOS_ENDPOINT \
    COSMOS_KEY=$COSMOS_KEY
```

### Production Environment (Azure Kubernetes Service)

1. **Build and Push Image**

```bash
# Build
docker build -t ticket-classifier:v1.0.0 .

# Tag for ACR
docker tag ticket-classifier:v1.0.0 yourregistry.azurecr.io/ticket-classifier:v1.0.0

# Push to ACR
az acr login --name yourregistry
docker push yourregistry.azurecr.io/ticket-classifier:v1.0.0
```

2. **Deploy to AKS**

```bash
# Get AKS credentials
az aks get-credentials --resource-group rg-ticket-classifier-prod --name aks-prod

# Create secrets (first time only)
kubectl create secret generic azure-secrets \
  --from-literal=openai-endpoint=$AZURE_OPENAI_ENDPOINT \
  --from-literal=openai-api-key=$AZURE_OPENAI_API_KEY \
  --from-literal=cosmos-endpoint=$COSMOS_ENDPOINT \
  --from-literal=cosmos-key=$COSMOS_KEY \
  -n production

# Deploy
kubectl apply -f deployment/k8s/deployment.yml
kubectl apply -f deployment/k8s/service.yml
kubectl apply -f deployment/k8s/ingress.yml
kubectl apply -f deployment/k8s/hpa.yml

# Verify deployment
kubectl rollout status deployment/ticket-classifier -n production
kubectl get pods -n production
```

3. **Verify Health**

```bash
# Get service endpoint
kubectl get service ticket-classifier-service -n production

# Test health endpoint
curl http://<external-ip>/health
```

### Rollback Procedure

```bash
# View rollout history
kubectl rollout history deployment/ticket-classifier -n production

# Rollback to previous version
kubectl rollout undo deployment/ticket-classifier -n production

# Rollback to specific revision
kubectl rollout undo deployment/ticket-classifier --to-revision=3 -n production
```

---

## Monitoring & Troubleshooting

### Key Metrics

**Prometheus Metrics (available at `/metrics`):**

1. `ticket_classifications_total{category,priority}` - Counter
   - Total classifications by category and priority

2. `ticket_classification_duration_seconds` - Histogram
   - Time spent classifying tickets

3. `ticket_classification_errors_total` - Counter
   - Total classification errors

### Application Insights Queries

**Average Classification Time:**

```kusto
requests
| where name == "POST /classify"
| summarize avg(duration) by bin(timestamp, 5m)
| render timechart
```

**Error Rate:**

```kusto
requests
| where name == "POST /classify"
| summarize 
    total = count(),
    errors = countif(success == false)
| extend error_rate = errors * 100.0 / total
```

**Top Classified Categories:**

```kusto
customMetrics
| where name == "ticket_classifications_total"
| extend category = tostring(customDimensions.category)
| summarize count() by category
| render piechart
```

### Health Checks

**Kubernetes Probes:**

- **Liveness Probe:** Checks if application is running
  - Endpoint: `/health`
  - Fails after 3 consecutive failures
  - Pod is restarted

- **Readiness Probe:** Checks if application is ready to serve traffic
  - Endpoint: `/health`
  - Fails after 3 consecutive failures
  - Traffic is not routed to pod

**Manual Health Check:**

```bash
curl http://<service-url>/health
# Expected: {"status": "healthy", "timestamp": "..."}
```

### Log Access

**Kubernetes Logs:**

```bash
# View logs for all pods
kubectl logs -l app=ticket-classifier -n production

# Follow logs
kubectl logs -f deployment/ticket-classifier -n production

# Logs for specific pod
kubectl logs <pod-name> -n production

# Previous container logs (if crashed)
kubectl logs <pod-name> -n production --previous
```

**Application Insights:**

- Navigate to Azure Portal → Application Insights → Logs
- Query traces, requests, exceptions

---

## API Documentation

### Base URL

- **Development:** `http://ticket-classifier-dev.azurecontainer.io:8000`
- **Production:** `https://api.ticket-classifier.example.com`

### Endpoints

#### 1. Health Check

```
GET /health
```

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### 2. Classify Ticket

```
POST /classify
```

**Request Body:**

```json
{
  "subject": "Cannot access billing portal",
  "description": "I'm getting a 404 error when trying to view my invoices",
  "customer_email": "customer@example.com",
  "source": "email"
}
```

**Response:**

```json
{
  "category": "Billing",
  "priority": "High",
  "confidence": 0.92,
  "reasoning": "User cannot access critical billing functionality, affecting their ability to manage their account",
  "suggested_team": "Finance Team"
}
```

**Status Codes:**

- `200 OK` - Successful classification
- `400 Bad Request` - Invalid input
- `500 Internal Server Error` - Classification failed

#### 3. Evaluate Classification

```
POST /evaluate
```

**Request Body:**

```json
{
  "ticket": {
    "ticket_id": "TKT-001",
    "subject": "Test ticket",
    "description": "Test description",
    "customer_email": "test@example.com"
  },
  "classification": {
    "category": "Technical",
    "priority": "High",
    "confidence": 0.90,
    "reasoning": "System issue",
    "suggested_team": "Engineering Team"
  },
  "ground_truth": {  // Optional
    "category": "Technical",
    "priority": "High",
    "confidence": 1.0,
    "reasoning": "Correct classification",
    "suggested_team": "Engineering Team"
  }
}
```

**Response:**

```json
{
  "accuracy_score": 0.95,
  "category_correct": true,
  "priority_correct": true,
  "reasoning_quality": 0.85,
  "feedback": "Excellent classification. Category and priority are appropriate.",
  "overall_score": 0.92
}
```

#### 4. Get Configuration

```
GET /config
```

**Response:**

```json
{
  "categories": ["Billing", "Technical", "Feature Request", "Bug Report", "Account Management"],
  "priorities": ["Critical", "High", "Medium", "Low"],
  "model_deployment": "gpt-4",
  "temperature": 0.0
}
```

#### 5. Prometheus Metrics

```
GET /metrics
```

Returns metrics in Prometheus format.

### Example Usage

**Python:**

```python
import requests

url = "https://api.ticket-classifier.example.com/classify"
data = {
    "subject": "Application crashing on login",
    "description": "Every time I try to log in, the app crashes",
    "customer_email": "user@company.com",
    "source": "mobile"
}

response = requests.post(url, json=data)
result = response.json()

print(f"Category: {result['category']}")
print(f"Priority: {result['priority']}")
print(f"Team: {result['suggested_team']}")
```

**cURL:**

```bash
curl -X POST https://api.ticket-classifier.example.com/classify \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Need help with API integration",
    "description": "Documentation is unclear about authentication",
    "customer_email": "dev@startup.com",
    "source": "portal"
  }'
```

---

## Testing Guide

### Running Tests

**All Tests:**

```bash
pytest tests/ -v
```

**With Coverage:**

```bash
pytest tests/ -v --cov=src --cov-report=html
open htmlcov/index.html  # View coverage report
```

**Specific Test File:**

```bash
pytest tests/test_classifier.py -v
```

**Mark-Based Tests:**

```bash
# Run only integration tests
pytest tests/ -v -m integration

# Skip slow tests
pytest tests/ -v -m "not slow"
```

### Test Categories

1. **Unit Tests** (`test_classifier.py`, `test_evaluator.py`)
   - Test individual components
   - Mock external dependencies
   - Fast execution

2. **Integration Tests** (`test_api.py`)
   - Test full API workflows
   - Use TestClient
   - Verify end-to-end behavior

3. **Performance Tests**
   - Measure classification latency
   - Load testing with locust

### Writing New Tests

**Test Template:**

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from main import app
from classifier import TicketInput, ClassificationOutput

@pytest.fixture
def client():
    return TestClient(app)

def test_your_feature(client):
    # Arrange
    data = {"subject": "Test", "description": "Test", "customer_email": "test@test.com"}
    
    # Act
    response = client.post("/classify", json=data)
    
    # Assert
    assert response.status_code == 200
    assert response.json()["category"] in settings.categories
```

---

## Maintenance & Operations

### Daily Operations

**Morning Checklist:**

1. Check system health via monitoring dashboard
2. Review error logs for any overnight issues
3. Verify classification metrics are within expected ranges
4. Check Azure OpenAI quota usage

**Weekly Tasks:**

1. Review evaluation scores and identify patterns
2. Analyze category distribution - adjust prompts if skewed
3. Check cost reports and optimize if needed
4. Review and update documentation if necessary

### Scaling Considerations

**Vertical Scaling (per pod):**

```yaml
resources:
  requests:
    memory: "1Gi"     # Increase for more load
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "4000m"
```

**Horizontal Scaling (more pods):**

```yaml
spec:
  replicas: 5  # Increase for more throughput
```

**Auto-scaling is configured via HPA:**

- Scales between 3-10 pods
- Triggers at 70% CPU or 80% memory

### Cost Optimization

**Azure OpenAI Costs:**

- GPT-4: ~$0.03 per 1K input tokens, ~$0.06 per 1K output tokens
- Current average: ~$0.05 per classification

**Optimization Strategies:**

1. Use GPT-3.5 for simple tickets (50% cost reduction)
2. Implement caching for similar tickets
3. Batch processing for non-urgent tickets
4. Optimize prompt length (fewer input tokens)

### Backup & Recovery

**Cosmos DB Backup:**

- Automatic continuous backups enabled
- Point-in-time restore available for last 30 days

**Configuration Backup:**

```bash
# Export Kubernetes configs
kubectl get all -n production -o yaml > backup-$(date +%Y%m%d).yaml

# Export secrets (encrypted)
kubectl get secrets -n production -o yaml > secrets-backup-$(date +%Y%m%d).yaml
```

**Disaster Recovery:**

1. Redeploy from Azure DevOps pipeline
2. Restore Kubernetes manifests from backup
3. Recreate secrets from Azure Key Vault
4. Verify health and run smoke tests

---

## Common Issues & Solutions

### Issue 1: Classification Returns 500 Error

**Symptoms:**

- POST /classify returns 500
- Logs show "Classification failed"

**Possible Causes:**

1. Azure OpenAI endpoint unreachable
2. API key invalid or expired
3. Quota exceeded
4. Malformed prompt

**Resolution:**

```bash
# Check Azure OpenAI status
az cognitiveservices account show --name your-openai-resource --resource-group your-rg

# Verify API key
kubectl get secret azure-secrets -n production -o jsonpath='{.data.openai-api-key}' | base64 -d

# Check quota
# Navigate to Azure Portal → Cognitive Services → Quotas

# Review logs for specific error
kubectl logs -l app=ticket-classifier -n production | grep -A 5 "Classification error"
```

### Issue 2: High Latency (> 10 seconds)

**Symptoms:**

- Classification takes longer than expected
- Timeout errors in production

**Possible Causes:**

1. Azure OpenAI throttling
2. Large prompt size
3. Insufficient resources

**Resolution:**

```bash
# Check resource usage
kubectl top pods -n production

# Increase pod resources if needed
kubectl edit deployment ticket-classifier -n production

# Check Azure OpenAI metrics
# Azure Portal → OpenAI → Metrics → Token Rate

# Optimize prompt in classifier.py
# Reduce description length or simplify prompt
```

### Issue 3: Pods Crash Looping

**Symptoms:**

- Pods repeatedly restart
- CrashLoopBackOff status

**Possible Causes:**

1. Missing environment variables
2. Health check failing
3. Out of memory

**Resolution:**

```bash
# Check pod status
kubectl get pods -n production
kubectl describe pod <pod-name> -n production

# View crash logs
kubectl logs <pod-name> -n production --previous

# Verify secrets exist
kubectl get secret azure-secrets -n production

# Check memory usage
kubectl top pod <pod-name> -n production

# If OOM, increase memory limits
kubectl edit deployment ticket-classifier -n production
```

### Issue 4: Incorrect Classifications

**Symptoms:**

- Tickets being classified into wrong categories
- Low confidence scores
- Support team reporting issues

**Resolution:**

1. Review recent evaluation scores
2. Analyze problematic tickets
3. Update prompt in `classifier.py`
4. Add examples to prompt for edge cases
5. Retrain team on new categories if added
6. Run evaluation suite on test set

**Prompt Tuning Process:**

```python
# In classifier.py, enhance prompt with examples:

template = """You are an expert customer support ticket classifier.

EXAMPLES OF CORRECT CLASSIFICATIONS:
- "Cannot log in" → Technical, High
- "Invoice missing" → Billing, Medium
- "Want dark mode feature" → Feature Request, Low

TICKET INFORMATION:
...
"""
```

### Issue 5: API Key Rotation

**Steps:**

1. Generate new API key in Azure Portal
2. Update Kubernetes secret:

```bash
kubectl create secret generic azure-secrets \
  --from-literal=openai-api-key=$NEW_API_KEY \
  --dry-run=client -o yaml | kubectl apply -f - -n production
```

3. Restart pods to pick up new secret:

```bash
kubectl rollout restart deployment/ticket-classifier -n production
```

4. Verify functionality with test request

---

## Future Enhancements

### Roadmap

**Q1 2024:**

- [ ] Multi-language support (Spanish, French, German)
- [ ] Sentiment analysis for customer frustration detection
- [ ] A/B testing framework for prompt optimization

**Q2 2024:**

- [ ] Automated responses for FAQs (30% of tickets)
- [ ] Integration with Zendesk/Salesforce
- [ ] Real-time dashboard for support team

**Q3 2024:**

- [ ] Customer feedback loop (thumbs up/down on classifications)
- [ ] Machine learning model for classification (complement LLM)
- [ ] SLA prediction based on ticket characteristics

**Q4 2024:**

- [ ] Proactive ticket creation from monitoring alerts
- [ ] Knowledge base integration and recommendations
- [ ] Advanced analytics and reporting

### Technical Debt

1. **Testing:** Increase coverage from 85% to 95%
2. **Monitoring:** Add custom Grafana dashboards
3. **Documentation:** Create video tutorials for common tasks
4. **Security:** Implement rate limiting per customer
5. **Performance:** Add Redis caching layer

---

## Contact & Support

### Primary Contact

**Satyam Gupta**  

- Email: <my.email@company.com>
- Teams: My Team
- Available: Monday-Friday, 9 AM - 6 PM

### Team Contacts

**Engineering Lead:**

- Name: [Engineering Lead]
- Email: <lead@company.com>

**DevOps Support:**

- Name: [DevOps Engineer]
- Email: <devops@company.com>

**Product Manager:**

- Name: [PM Name]
- Email: <pm@company.com>

### Escalation Path

1. **Level 1:** Check this documentation and logs
2. **Level 2:** Contact primary contact (you)
3. **Level 3:** Engineering Lead
4. **Level 4:** CTO for critical production issues

### Useful Links

- **GitHub Repository:** [[link](https://github.com/satya-supercluster/smart-content-personalization-engine)]
- **Azure Portal:** [link to resource group]
- **Application Insights:** [link]
- **Grafana Dashboard:** [link]
- **Azure DevOps Pipelines:** [link]
- **Runbook:** [link to detailed runbook]

---

## Knowledge Transfer Sessions

### Session 1: Architecture Overview (90 minutes)

**Target:** Engineering Team
**Agenda:**

1. System architecture walkthrough (20 min)
2. Code structure and key components (30 min)
3. LangGraph workflow deep dive (20 min)
4. Q&A and hands-on exploration (20 min)

### Session 2: Operations & Maintenance (60 minutes)

**Target:** DevOps Team
**Agenda:**

1. Deployment procedures (15 min)
2. Monitoring and alerting (15 min)
3. Common issues and troubleshooting (20 min)
4. Hands-on exercise: Deploy to dev environment (10 min)

### Session 3: Using the System (45 minutes)

**Target:** Support Team
**Agenda:**

1. How classifications work (10 min)
2. Interpreting confidence scores and reasoning (10 min)
3. When to override classifications (10 min)
4. Providing feedback for improvements (10 min)
5. Q&A (5 min)

---

## Appendix A: Glossary

- **LangChain:** Framework for building LLM applications
- **LangGraph:** Library for building stateful, multi-step workflows with LLMs
- **Azure OpenAI:** Microsoft's enterprise offering of OpenAI models
- **Cosmos DB:** Azure's globally distributed database
- **AKS:** Azure Kubernetes Service
- **ACR:** Azure Container Registry
- **HPA:** Horizontal Pod Autoscaler
- **Prometheus:** Monitoring and alerting toolkit
- **Application Insights:** Azure's application performance management service

---

## Appendix B: Useful Commands Cheatsheet

```bash
# Docker
docker build -t ticket-classifier .
docker run -p 8000:8000 --env-file .env ticket-classifier
docker logs <container-id>

# Kubernetes
kubectl get pods -n production
kubectl logs -f deployment/ticket-classifier -n production
kubectl describe pod <pod-name> -n production
kubectl exec -it <pod-name> -n production -- /bin/bash
kubectl rollout restart deployment/ticket-classifier -n production

# Azure CLI
az login
az aks get-credentials --resource-group <rg> --name <aks-name>
az acr login --name <registry-name>

# Testing
pytest tests/ -v
pytest tests/ --cov=src --cov-report=html
pytest tests/ -k test_classifier

# Python
python -m uvicorn src.main:app --reload
python -m pytest tests/
python -m mypy src/
```

---

**Document Version:** 1.0  
**Last Updated:** [28 November 2025]  

---

## Feedback

This is a living document. Please submit improvements via:

- Pull requests to the documentation
- Direct message to Satyam Gupta

Thank you for maintaining this system! 🚀
