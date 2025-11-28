# CI/CD Setup Guide

## GitHub Actions vs Azure DevOps

---

## Overview

You now have **TWO complete CI/CD pipelines**:

1. **GitHub Actions** (`.github/workflows/ci-cd.yml`) - For GitHub repositories
2. **Azure DevOps** (`azure-pipelines.yml`) - For Azure DevOps repositories

Both do the same thing but use different platforms. Choose based on where your code is hosted.

---

## Comparison: GitHub Actions vs Azure DevOps

| Feature | GitHub Actions | Azure DevOps |
|---------|---------------|--------------|
| **Best for** | Open source, GitHub-hosted repos | Enterprise, Microsoft ecosystem |
| **Free tier** | 2,000 minutes/month (public repos unlimited) | 1,800 minutes/month |
| **Ease of setup** | ⭐⭐⭐⭐⭐ Very easy | ⭐⭐⭐⭐ Easy |
| **Azure integration** | ⭐⭐⭐⭐ Good | ⭐⭐⭐⭐⭐ Excellent |
| **Marketplace** | Large (GitHub Actions) | Large (Azure DevOps Extensions) |
| **UI/UX** | Modern, clean | Professional, feature-rich |
| **Learning curve** | Lower | Slightly higher |

### When to use GitHub Actions

- ✅ Your code is on GitHub
- ✅ You prefer simpler YAML syntax
- ✅ You want faster setup
- ✅ Open source or small team projects

### When to use Azure DevOps

- ✅ Enterprise environment
- ✅ Already using Azure DevOps for project management
- ✅ Need advanced features (test plans, artifacts)
- ✅ Complex release management requirements

---

## Setting Up GitHub Actions

### Step 1: Required GitHub Secrets

Navigate to: **Repository → Settings → Secrets and variables → Actions → New repository secret**

Add these secrets:

#### Azure Credentials

```
Name: AZURE_CREDENTIALS
Value: 
{
  "clientId": "YOUR_CLIENT_ID",
  "clientSecret": "YOUR_CLIENT_SECRET",
  "subscriptionId": "YOUR_SUBSCRIPTION_ID",
  "tenantId": "YOUR_TENANT_ID"
}
```

**How to get this:**

```bash
az ad sp create-for-rbac \
  --name "github-actions-ticket-classifier" \
  --role contributor \
  --scopes /subscriptions/{subscription-id}/resourceGroups/{resource-group} \
  --sdk-auth
```

#### Azure Container Registry

```
Name: ACR_USERNAME
Value: <your-acr-username>

Name: ACR_PASSWORD
Value: <your-acr-password>
```

**How to get this:**

```bash
az acr credential show --name yourregistry
```

#### Azure OpenAI

```
Name: AZURE_OPENAI_ENDPOINT
Value: https://your-resource.openai.azure.com/

Name: AZURE_OPENAI_API_KEY
Value: <your-api-key>
```

**How to get this:**

```bash
# Endpoint
az cognitiveservices account show \
  --name your-openai-resource \
  --resource-group your-rg \
  --query properties.endpoint

# Key
az cognitiveservices account keys list \
  --name your-openai-resource \
  --resource-group your-rg \
  --query key1
```

#### Cosmos DB

```
Name: COSMOS_ENDPOINT
Value: https://your-cosmos.documents.azure.com:443/

Name: COSMOS_KEY
Value: <your-cosmos-key>
```

**How to get this:**

```bash
# Endpoint
az cosmosdb show \
  --name your-cosmos \
  --resource-group your-rg \
  --query documentEndpoint

# Key
az cosmosdb keys list \
  --name your-cosmos \
  --resource-group your-rg \
  --query primaryMasterKey
```

#### Production URL

```
Name: PROD_URL
Value: https://api.ticket-classifier.example.com
```

#### Slack Notifications (Optional)

```
Name: SLACK_WEBHOOK_URL
Value: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

**How to get this:**

1. Go to Slack → Apps → Incoming Webhooks
2. Create a new webhook
3. Copy the URL

### Step 2: Enable GitHub Actions

1. Go to your repository
2. Click on **Actions** tab
3. GitHub will automatically detect the workflow file
4. Click **"I understand my workflows, go ahead and enable them"**

### Step 3: Protect Main Branch (Recommended)

1. Go to **Settings → Branches**
2. Add branch protection rule for `main`
3. Enable:
   - ✅ Require pull request reviews
   - ✅ Require status checks to pass (select your CI jobs)
   - ✅ Require branches to be up to date

### Step 4: Set Up Environments

1. Go to **Settings → Environments**
2. Create two environments:
   - `development`
   - `production`
3. For production, enable:
   - ✅ Required reviewers (add yourself or team)
   - ✅ Wait timer (optional, e.g., 5 minutes)

---

## Setting Up Azure DevOps

### Step 1: Create Azure DevOps Project

1. Go to <https://dev.azure.com>
2. Create new project: `ticket-classifier`
3. Import your repository or connect to GitHub

### Step 2: Create Service Connections

Navigate to: **Project Settings → Service connections**

#### 1. Azure Resource Manager Connection

- Click **New service connection**
- Select **Azure Resource Manager**
- Choose **Service principal (automatic)**
- Select your subscription and resource group
- Name: `AzureServiceConnection`

#### 2. Azure Container Registry Connection

- Click **New service connection**
- Select **Docker Registry**
- Registry type: **Azure Container Registry**
- Select your ACR
- Name: `AzureContainerRegistry`

#### 3. Kubernetes Connection (for AKS)

- Click **New service connection**
- Select **Kubernetes**
- Choose **Azure Subscription**
- Select your AKS cluster
- Name: `AKSConnection`

### Step 3: Create Variable Groups

Navigate to: **Pipelines → Library → + Variable group**

#### Variable Group: `ticket-classifier-secrets`

Add these variables:

| Variable | Value | Secret? |
|----------|-------|---------|
| azureOpenAIEndpoint | <https://your-resource.openai.azure.com/> | No |
| azureOpenAIKey | <your-api-key> | ✅ Yes |
| azureOpenAIDeployment | gpt-4 | No |
| cosmosEndpoint | <https://your-cosmos.documents.azure.com:443/> | No |
| cosmosKey | <your-cosmos-key> | ✅ Yes |
| acrUsername | <acr-username> | No |
| acrPassword | <acr-password> | ✅ Yes |
| prodUrl | <https://api.ticket-classifier.example.com> | No |

Click the 🔒 icon next to sensitive values to mark them as secret.

### Step 4: Create Pipeline

1. Go to **Pipelines → Pipelines**
2. Click **New pipeline**
3. Select your repository source
4. Choose **Existing Azure Pipelines YAML file**
5. Select `azure-pipelines.yml`
6. Click **Run**

### Step 5: Configure Environments

Navigate to: **Pipelines → Environments**

1. Create environment: `development`
2. Create environment: `production`
   - Add approval check (yourself or team)
   - Add checks and validations as needed

---

## Pipeline Workflow Explained

### What Happens When You Push Code

#### Branch: `develop`

```
1. Code Quality Checks (Linting, Security)
2. Run Tests (Unit, Integration)
3. Build Docker Image
4. Deploy to Development (ACI)
5. Run Smoke Tests
```

#### Branch: `main`

```
1. Code Quality Checks
2. Run Tests
3. Build Docker Image
4. Deploy to Production (AKS) ⚠️ Requires Approval
5. Run Integration Tests
6. Run Performance Tests
7. Notify team (if failure)
```

#### Pull Requests

```
1. Code Quality Checks
2. Run Tests
(No deployment)
```

### Approval Gates

For production deployments:

- **GitHub Actions:** Uses Environment protection rules
- **Azure DevOps:** Uses Environment approvals

This ensures no code goes to production without human review.

---

## Testing Your CI/CD Pipeline

### 1. Test Code Quality Job

Create a test branch with a linting error:

```python
# In src/main.py, add this intentionally bad code:
def   bad_function(  ):
    x=1+2
    return    x
```

Push and watch the pipeline fail on code quality checks.

### 2. Test Build Job

Create a valid branch and push:

```bash
git checkout -b test/ci-cd
git push origin test/ci-cd
```

Watch the pipeline build the Docker image.

### 3. Test Deployment

Merge to `develop` branch:

```bash
git checkout develop
git merge test/ci-cd
git push origin develop
```

Watch it deploy to development environment.

### 4. Test Production Deployment

Create a PR to `main`, get it approved, and merge. Watch the full production deployment flow.

---

## Monitoring Your Pipelines

### GitHub Actions

**View workflow runs:**

- Go to **Actions** tab
- See all runs, their status, and logs

**View specific job:**

- Click on a workflow run
- Expand jobs to see logs
- Download artifacts

**Set up notifications:**

- Go to **Settings → Notifications**
- Enable "Actions" notifications

### Azure DevOps

**View pipeline runs:**

- Go to **Pipelines → Pipelines**
- Click on your pipeline
- See run history

**View detailed logs:**

- Click on a run
- View each stage/job
- Download logs

**Set up notifications:**

- Click on pipeline → ⋯ (more options) → Notifications
- Configure email/Slack alerts

---

## Troubleshooting Common Issues

### Issue 1: "Azure credentials are not valid"

**GitHub Actions:**

```bash
# Recreate service principal
az ad sp create-for-rbac --name "github-actions-ticket-classifier" \
  --role contributor \
  --scopes /subscriptions/{subscription-id} \
  --sdk-auth

# Update AZURE_CREDENTIALS secret with the JSON output
```

**Azure DevOps:**

- Go to Service connections
- Edit the Azure Resource Manager connection
- Verify or recreate

### Issue 2: "Permission denied" for ACR

**Solution:**

```bash
# Give your service principal access to ACR
az role assignment create \
  --assignee <service-principal-id> \
  --role AcrPush \
  --scope /subscriptions/{subscription-id}/resourceGroups/{rg}/providers/Microsoft.ContainerRegistry/registries/{acr-name}
```

### Issue 3: "kubectl: command not found" in pipeline

**GitHub Actions:** Already handled by `azure/setup-kubectl@v3`

**Azure DevOps:** Add this task before kubectl commands:

```yaml
- task: KubectlInstaller@0
  inputs:
    kubectlVersion: 'latest'
```

### Issue 4: Tests fail with "Module not found"

**Solution:** Ensure all dependencies are in `requirements.txt`

```bash
# Generate from your environment
pip freeze > requirements.txt
```

### Issue 5: Health check fails after deployment

**Possible causes:**

1. Container not fully started (increase wait time)
2. Wrong port configuration
3. Health endpoint not accessible

**Solution:**

```yaml
# Increase wait time
- name: Wait for deployment
  run: sleep 60  # Increase from 30 to 60
```

---

## Cost Optimization

### GitHub Actions

**Free tier:** 2,000 minutes/month for private repos

**Optimization tips:**

1. Use caching for dependencies:

   ```yaml
   - uses: actions/setup-python@v4
     with:
       cache: 'pip'  # This caches pip dependencies
   ```

2. Only run on relevant path changes:

   ```yaml
   on:
     push:
       paths:
         - 'src/**'
         - 'tests/**'
   ```

3. Use smaller runners (default is fine)

### Azure DevOps

**Free tier:** 1,800 minutes/month

**Optimization tips:**

1. Use parallel jobs only when necessary
2. Cache NuGet/npm/pip packages
3. Use hosted agents efficiently

---

## Advanced Features

### Matrix Builds (Test Multiple Python Versions)

**GitHub Actions:**

```yaml
jobs:
  test:
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11']
    steps:
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
```

**Azure DevOps:**

```yaml
strategy:
  matrix:
    Python39:
      python.version: '3.9'
    Python310:
      python.version: '3.10'
    Python311:
      python.version: '3.11'
```

### Scheduled Runs (Nightly Builds)

**GitHub Actions:**

```yaml
on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM daily
```

**Azure DevOps:**

```yaml
schedules:
  - cron: "0 2 * * *"
    displayName: Nightly build
    branches:
      include:
        - main
```

### Manual Triggers

**GitHub Actions:**

```yaml
on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy'
        required: true
        default: 'development'
```

**Azure DevOps:**
Already supports manual runs by default via UI.

---

## Best Practices

### 1. Keep Secrets Secure

- ✅ Never commit secrets to code
- ✅ Use secret management (GitHub Secrets, Azure Key Vault)
- ✅ Rotate secrets regularly

### 2. Test Before Deploying

- ✅ Always run tests before deployment
- ✅ Maintain >80% code coverage
- ✅ Include integration tests

### 3. Use Environment Separation

- ✅ Dev → Staging → Production
- ✅ Different configurations per environment
- ✅ Approval gates for production

### 4. Monitor Pipeline Performance

- ✅ Track pipeline duration
- ✅ Optimize slow jobs
- ✅ Use caching effectively

### 5. Document Everything

- ✅ Add comments in YAML
- ✅ Keep this guide updated
- ✅ Document any custom steps

---

## Quick Reference Commands

### GitHub CLI (gh)

```bash
# View workflow runs
gh run list

# View specific run
gh run view <run-id>

# Trigger workflow manually
gh workflow run ci-cd.yml

# Download artifacts
gh run download <run-id>
```

### Azure DevOps CLI

```bash
# Login
az devops login

# List pipelines
az pipelines list --org https://dev.azure.com/yourorg --project ticket-classifier

# Run pipeline
az pipelines run --name "ticket-classifier-ci-cd" --org https://dev.azure.com/yourorg --project ticket-classifier

# Show run details
az pipelines runs show --id <run-id> --org https://dev.azure.com/yourorg --project ticket-classifier
```

---

## Next Steps

1. ✅ Choose your CI/CD platform (GitHub Actions OR Azure DevOps)
2. ✅ Set up required secrets/service connections
3. ✅ Push code and verify the pipeline runs
4. ✅ Test deployment to development
5. ✅ Set up approval gates for production
6. ✅ Configure notifications
7. ✅ Monitor and optimize

---

## Need Help?

### Resources

- **GitHub Actions Docs:** <https://docs.github.com/en/actions>
- **Azure DevOps Docs:** <https://docs.microsoft.com/en-us/azure/devops/>
- **Azure CLI Docs:** <https://docs.microsoft.com/en-us/cli/azure/>

### Common Issues

- Check the troubleshooting section above
- Review pipeline logs
- Verify secrets are set correctly
- Ensure service connections have proper permissions

**You've got a production-ready CI/CD pipeline! 🚀**
