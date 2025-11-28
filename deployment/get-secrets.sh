# Script to retrieve secrets from Key Vault
cat > deployment/get-secrets.sh <<'SECRETS_EOF'
#!/bin/bash
# deployment/get-secrets.sh
# Script to retrieve secrets from Azure Key Vault

set -e

ENVIRONMENT=${1:-dev}
APP_NAME=${2:-ticket-classifier}
KEY_VAULT_NAME="kv-${APP_NAME}-${ENVIRONMENT}"

echo "Retrieving secrets from: $KEY_VAULT_NAME"
echo ""

# OpenAI API Key
OPENAI_KEY=$(az keyvault secret show \
    --vault-name "$KEY_VAULT_NAME" \
    --name "openai-api-key" \
    --query value -o tsv)
echo "AZURE_OPENAI_API_KEY=$OPENAI_KEY"

# Cosmos DB Key
COSMOS_KEY=$(az keyvault secret show \
    --vault-name "$KEY_VAULT_NAME" \
    --name "cosmos-key" \
    --query value -o tsv)
echo "COSMOS_KEY=$COSMOS_KEY"

echo ""
echo "Secrets retrieved successfully"
echo "⚠️  Keep these secrets secure!"
SECRETS_EOF

chmod +x deployment/get-secrets.sh

print_success "Helper scripts created in deployment/ directory"