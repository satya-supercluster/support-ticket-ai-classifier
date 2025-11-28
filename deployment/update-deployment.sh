# Script to update an existing deployment
cat > deployment/update-deployment.sh <<'UPDATE_EOF'
#!/bin/bash
# deployment/update-deployment.sh
# Script to update application deployment

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

ENVIRONMENT=${1:-dev}
APP_NAME=${2:-ticket-classifier}
IMAGE_TAG=${3:-latest}

RESOURCE_GROUP="rg-${APP_NAME}-${ENVIRONMENT}"

print_info "Updating deployment in: $ENVIRONMENT"
print_info "Image tag: $IMAGE_TAG"

if [[ "$ENVIRONMENT" == "dev" ]]; then
    # Update ACI
    print_info "Updating Azure Container Instance..."
    ACI_NAME="aci-${APP_NAME}-${ENVIRONMENT}"
    ACR_NAME="acr${APP_NAME}${ENVIRONMENT}"
    ACR_SERVER=$(az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query loginServer -o tsv)
    
    az container create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$ACI_NAME" \
        --image "${ACR_SERVER}/${APP_NAME}:${IMAGE_TAG}" \
        --restart-policy Always \
        > /dev/null
    
    print_success "ACI updated"
else
    # Update AKS
    print_info "Updating Kubernetes deployment..."
    kubectl set image deployment/ticket-classifier \
        ticket-classifier="${ACR_SERVER}/${APP_NAME}:${IMAGE_TAG}" \
        -n production
    
    kubectl rollout status deployment/ticket-classifier -n production
    print_success "Kubernetes deployment updated"
fi

print_success "Deployment update completed!"
UPDATE_EOF

chmod +x deployment/update-deployment.sh
