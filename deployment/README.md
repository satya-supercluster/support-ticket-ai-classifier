# Azure Deployment Guide

## Complete Infrastructure as Code for Ticket Classifier

---

## Overview

You now have **complete Azure infrastructure automation** with:

1. **`azure-deploy.yml`** - ARM/Bicep-style template defining all Azure resources
2. **`deploy-azure.sh`** - Automated deployment script
3. **Helper scripts** - For updates, teardown, and secret management

---

## What Gets Deployed?

### All Environments Get

- ✅ **Azure Container Registry (ACR)** - For Docker images
- ✅ **Azure Cosmos DB** - For ticket/classification storage
- ✅ **Azure OpenAI** - GPT-4 deployment
- ✅ **Application Insights** - Monitoring and telemetry
- ✅ **Log Analytics Workspace** - Centralized logging
- ✅ **Azure Key Vault** - Secret management

### Development Environment

- ✅ **Azure Container Instance (ACI)** - Simple container hosting

### Staging/Production Environments

- ✅ **Azure Kubernetes Service (AKS)** - Scalable container orchestration
- ✅ **Auto-scaling** - 3-10 node configuration
- ✅ **Multi-zone** - High availability across availability zones

---

## Resource Naming Convention

Resources follow Azure best practices:

```
{resource-type}-{application-name}-{environment}

Examples:
- rg-ticket-classifier-dev          (Resource Group)
- acr-ticket-classifier-prod        (Container Registry)
- cosmos-ticket-classifier-staging  (Cosmos DB)
- aks-ticket-classifier-prod        (Kubernetes)
```

---

## Prerequisites

### 1. Install Azure CLI

```bash
# Windows (PowerShell)
Invoke-WebRequest -Uri https://aka.ms/installazurecliwindows -OutFile .\AzureCLI.msi
Start-Process msiexec.exe -Wait -ArgumentList '/I AzureCLI.msi /quiet'

# macOS
brew install azure-cli

# Linux (Ubuntu/Debian)
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

### 2. Login to Azure

```bash
az login

# If you have multiple subscriptions, set the active one
az account list --output table
az account set --subscription "Your Subscription Name"
```

### 3. Register Required Resource Providers

```bash
az provider register --namespace Microsoft.ContainerRegistry
az provider register --namespace Microsoft.DocumentDB
az provider register --namespace Microsoft.CognitiveServices
az provider register --namespace Microsoft.ContainerInstance
az provider register --namespace Microsoft.ContainerService
az provider register --namespace Microsoft.Insights
az provider register --namespace Microsoft.KeyVault

# Check registration status
az provider show --namespace Microsoft.CognitiveServices --query "registrationState"
```

### 4. Request Azure OpenAI Access (if needed)

Azure OpenAI requires approval:

1. Go to: <https://aka.ms/oai/access>
2. Fill out the form
3. Wait for approval (usually 1-2 business days)

---

## Quick Start Deployment

### Deploy Development Environment

```bash
# Make scripts executable
chmod +x deployment/*.sh

# Deploy to dev
./deployment/deploy-azure.sh dev eastus ticket-classifier

# Expected output:
# ✓ Checking prerequisites...
# ✓ Azure CLI found
# ✓ kubectl found
# ✓ Logged in to Azure
# ℹ Deploying to environment: dev
# ℹ Location: eastus
# ...
# ✓ Deployment completed!
```

This creates:

- Resource group: `rg-ticket-classifier-dev`
- All necessary Azure resources
- Container Instance running your app

**Time:** ~10-15 minutes

### Deploy Production Environment

```bash
./deployment/deploy-azure.sh prod eastus ticket-classifier
```

This creates:

- Resource group: `rg-ticket-classifier-prod`
- All resources + AKS cluster (3 nodes, auto-scaling to 10)

**Time:** ~20-30 minutes (AKS takes longer)

---

## Detailed Deployment Steps

### Step 1: Review Configuration

Before deploying, review `deployment/azure-deploy.yml` and customize:

```yaml
parameters:
  - name: containerCpu
    type: int
    default: 2          # Adjust based on load

  - name: containerMemory
    type: int
    default: 4          # GB of memory

  - name: minReplicas
    type: int
    default: 3          # Minimum AKS nodes

  - name: maxReplicas
    type: int
    default: 10         # Maximum AKS nodes
```

### Step 2: Deploy Infrastructure

```bash
# Development
./deployment/deploy-azure.sh dev eastus

# Production
./deployment/deploy-azure.sh prod eastus
```

The script will:

1. ✅ Check prerequisites
2. ✅ Create resource group
3. ✅ Deploy all Azure resources
4. ✅ Configure secrets in Key Vault
5. ✅ Save configuration to `.env.{environment}` file
6. ✅ Display next steps

### Step 3: Build and Push Docker Image

```bash
# Load environment variables
source deployment/.env.dev  # or .env.prod

# Login to ACR
az acr login --name ${ACR_LOGIN_SERVER%%.*}

# Build image
docker build -t $ACR_LOGIN_SERVER/ticket-classifier:latest .

# Push to ACR
docker push $ACR_LOGIN_SERVER/ticket-classifier:latest

# Verify image
az acr repository list --name ${ACR_LOGIN_SERVER%%.*} --output table
```

### Step 4a: Deploy to Development (ACI)

For development, the container is automatically deployed by the ARM template.

**Test the deployment:**

```bash
# Get ACI endpoint
ACI_ENDPOINT=$(az container show \
    --resource-group rg-ticket-classifier-dev \
    --name aci-ticket-classifier-dev \
    --query ipAddress.fqdn -o tsv)

# Health check
curl http://${ACI_ENDPOINT}:8000/health

# Test classification
curl -X POST http://${ACI_ENDPOINT}:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Cannot access account",
    "description": "Getting error when logging in",
    "customer_email": "test@example.com",
    "source": "portal"
  }'
```

### Step 4b: Deploy to Production (AKS)

For production, deploy Kubernetes manifests:

```bash
# Get AKS credentials (already done by deploy script)
az aks get-credentials \
    --resource-group rg-ticket-classifier-prod \
    --name aks-ticket-classifier-prod

# Verify connection
kubectl get nodes

# Create namespace
kubectl create namespace production

# Create secrets from Key Vault
./deployment/get-secrets.sh prod > secrets.env
kubectl create secret generic azure-secrets \
    --from-env-file=secrets.env \
    -n production
rm secrets.env  # Clean up

# Update image in deployment manifest
ACR_SERVER=$(az acr show \
    --name acrticketclassifierprod \
    --resource-group rg-ticket-classifier-prod \
    --query loginServer -o tsv)

sed -i "s|image:.*|image: ${ACR_SERVER}/ticket-classifier:latest|g" \
    deployment/k8s/deployment.yml

# Deploy to Kubernetes
kubectl apply -f deployment/k8s/deployment.yml
kubectl apply -f deployment/k8s/service.yml
kubectl apply -f deployment/k8s/ingress.yml
kubectl apply -f deployment/k8s/hpa.yml

# Wait for rollout
kubectl rollout status deployment/ticket-classifier -n production

# Verify pods
kubectl get pods -n production
```

---

## Post-Deployment Configuration

### 1. Configure DNS (Production)

```bash
# Get LoadBalancer IP
LB_IP=$(kubectl get service ticket-classifier-service \
    -n production \
    -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "Configure your DNS:"
echo "api.ticket-classifier.example.com -> $LB_IP"
```

Add an A record in your DNS provider:

- **Name:** `api.ticket-classifier`
- **Type:** `A`
- **Value:** `{LB_IP}`
- **TTL:** `300`

### 2. Configure SSL Certificate (Production)

Install cert-manager:

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Wait for cert-manager to be ready
kubectl wait --for=condition=Available --timeout=300s \
    deployment/cert-manager -n cert-manager
```

Create ClusterIssuer:

```bash
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

The ingress manifest already references this issuer, so certificates will be automatically issued.

### 3. Configure Monitoring Alerts

```bash
# Create action group for notifications
az monitor action-group create \
    --resource-group rg-ticket-classifier-prod \
    --name ag-ticket-classifier-alerts \
    --short-name tc-alerts \
    --email-receiver email admin your-email@example.com

# Create alert for high error rate
az monitor metrics alert create \
    --resource-group rg-ticket-classifier-prod \
    --name alert-high-error-rate \
    --scopes "/subscriptions/{subscription-id}/resourceGroups/rg-ticket-classifier-prod/providers/Microsoft.Insights/components/appi-ticket-classifier-prod" \
    --condition "count customMetrics/ticket_classification_errors_total > 10" \
    --window-size 5m \
    --evaluation-frequency 1m \
    --action ag-ticket-classifier-alerts
```

---

## Updating Deployments

### Update Application Code

```bash
# Rebuild and push new image
docker build -t $ACR_LOGIN_SERVER/ticket-classifier:v1.0.1 .
docker push $ACR_LOGIN_SERVER/ticket-classifier:v1.0.1

# Update deployment
./deployment/update-deployment.sh prod ticket-classifier v1.0.1
```

### Update Infrastructure

```bash
# Modify azure-deploy.yml as needed

# Re-run deployment (only changed resources will be updated)
./deployment/deploy-azure.sh prod eastus ticket-classifier
```

---

## Monitoring & Troubleshooting

### View Application Logs

**Development (ACI):**

```bash
az container logs \
    --resource-group rg-ticket-classifier-dev \
    --name aci-ticket-classifier-dev \
    --follow
```

**Production (AKS):**

```bash
kubectl logs -f deployment/ticket-classifier -n production
```

### View Application Insights

```bash
# Get App Insights URL
APP_INSIGHTS_URL=$(az monitor app-insights component show \
    --resource-group rg-ticket-classifier-prod \
    --app appi-ticket-classifier-prod \
    --query 'properties.appId' -o tsv)

echo "https://portal.azure.com/#@/resource/subscriptions/{subscription-id}/resourceGroups/rg-ticket-classifier-prod/providers/Microsoft.Insights/components/appi-ticket-classifier-prod/overview"
```

### Check Resource Health

```bash
# Check all resources in resource group
az resource list \
    --resource-group rg-ticket-classifier-prod \
    --output table

# Check specific resource
az container show \
    --resource-group rg-ticket-classifier-dev \
    --name aci-ticket-classifier-dev \
    --query "{Name:name, Status:instanceView.state}" \
    -o table
```

### View Costs

```bash
# View current month costs by resource
az consumption usage list \
    --start-date $(date -u -d "$(date +%Y-%m-01)" '+%Y-%m-%d') \
    --end-date $(date -u '+%Y-%m-%d') \
    --query "[?contains(instanceName, 'ticket-classifier')].{Name:instanceName, Cost:pretaxCost, Currency:currency}" \
    -o table
```

---

## Cost Estimates

### Development Environment (~$150-200/month)

- Azure Container Instance: ~$30/month
- Cosmos DB (Serverless): ~$25/month
- Azure OpenAI (pay-per-use): ~$50-100/month
- Application Insights: ~$25/month
- Other services: ~$20/month

### Production Environment (~$500-800/month)

- AKS (3 D4s_v3 nodes): ~$350/month
- Cosmos DB (Provisioned): ~$50-100/month
- Azure OpenAI (higher volume): ~$100-200/month
- Application Insights: ~$50/month
- Other services: ~$50/month

**Optimization tips:**

- Use Azure Reservations for 30-40% savings on compute
- Scale down dev environment when not in use
- Use serverless Cosmos DB for dev
- Monitor and optimize OpenAI token usage

---

## Cleanup / Teardown

### Delete Everything

```bash
# Development
./deployment/teardown-azure.sh dev ticket-classifier

# Production (⚠️ Be very careful!)
./deployment/teardown-azure.sh prod ticket-classifier
```

This deletes the entire resource group and ALL resources within it.

### Selective Cleanup

```bash
# Delete only ACI (keep other resources)
az container delete \
    --resource-group rg-ticket-classifier-dev \
    --name aci-ticket-classifier-dev \
    --yes

# Delete only AKS (keep other resources)
az aks delete \
    --resource-group rg-ticket-classifier-prod \
    --name aks-ticket-classifier-prod \
    --yes
```

---

## Security Best Practices

### 1. Use Managed Identities

The deployment already uses system-assigned managed identities for:

- AKS cluster accessing ACR
- Key Vault access

### 2. Enable Azure Policy

```bash
az policy assignment create \
    --name 'require-tags' \
    --scope "/subscriptions/{subscription-id}/resourceGroups/rg-ticket-classifier-prod" \
    --policy "require-tag-on-resources"
```

### 3. Enable Network Security

```bash
# Restrict Key Vault access
az keyvault network-rule add \
    --name kv-ticket-classifier-prod \
    --resource-group rg-ticket-classifier-prod \
    --subnet "aks-subnet-id"
```

### 4. Rotate Secrets Regularly

```bash
# Regenerate Cosmos DB key
az cosmosdb keys regenerate \
    --name cosmos-ticket-classifier-prod \
    --resource-group rg-ticket-classifier-prod \
    --key-kind primary

# Update in Key Vault
NEW_KEY=$(az cosmosdb keys list \
    --name cosmos-ticket-classifier-prod \
    --resource-group rg-ticket-classifier-prod \
    --query primaryMasterKey -o tsv)

az keyvault secret set \
    --vault-name kv-ticket-classifier-prod \
    --name cosmos-key \
    --value "$NEW_KEY"

# Restart pods to pick up new secret
kubectl rollout restart deployment/ticket-classifier -n production
```

---

## Troubleshooting Common Issues

### Issue 1: "Location not available for subscription"

**Solution:** Some Azure regions require feature registration

```bash
az feature register --namespace Microsoft.ContainerService --name AKSAzureStandardLoadBalancer
az provider register --namespace Microsoft.ContainerService
```

### Issue 2: "OpenAI resource creation failed"

**Solution:** You need Azure OpenAI access approval

- Apply at: <https://aka.ms/oai/access>
- Wait for approval email
- Retry deployment

### Issue 3: "Insufficient quota"

**Solution:** Request quota increase

```bash
az vm list-usage --location eastus --output table
# Request increase via Azure Portal → Quotas
```

### Issue 4: "ACR login failed"

**Solution:** Ensure admin user is enabled

```bash
az acr update \
    --name acrticketclassifierprod \
    --admin-enabled true
```

---

## Next Steps

1. ✅ Deploy infrastructure: `./deployment/deploy-azure.sh dev eastus`
2. ✅ Build and push Docker image
3. ✅ Test in development environment
4. ✅ Deploy to production with approval gates
5. ✅ Configure monitoring and alerts
6. ✅ Set up CI/CD pipeline (GitHub Actions or Azure DevOps)
7. ✅ Document any custom configurations

---

## Summary

You now have:

- ✅ **Complete Infrastructure as Code** - Automated Azure resource provisioning
- ✅ **Environment Separation** - Dev, Staging, Prod configurations
- ✅ **Secure Secret Management** - Key Vault integration
- ✅ **Scalable Architecture** - ACI for dev, AKS for production
- ✅ **Helper Scripts** - Deploy, update, teardown, secrets
- ✅ **Cost Optimization** - Right-sized resources per environment

This is **production-ready infrastructure** following Azure best practices! 🚀
