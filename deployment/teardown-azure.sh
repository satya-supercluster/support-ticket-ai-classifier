# Script to delete all Azure resources
cat > deployment/teardown-azure.sh <<'TEARDOWN_EOF'
#!/bin/bash
# deployment/teardown-azure.sh
# Script to tear down Azure infrastructure

set -e

RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

ENVIRONMENT=${1:-dev}
APP_NAME=${2:-ticket-classifier}
RESOURCE_GROUP="rg-${APP_NAME}-${ENVIRONMENT}"

print_warning "This will DELETE all resources in: $RESOURCE_GROUP"
print_warning "This action CANNOT be undone!"
echo ""

read -p "Type 'DELETE' to confirm: " CONFIRM
if [[ "$CONFIRM" != "DELETE" ]]; then
    print_error "Teardown cancelled"
    exit 1
fi

echo "Deleting resource group: $RESOURCE_GROUP..."
az group delete --name "$RESOURCE_GROUP" --yes --no-wait

echo "Resource group deletion initiated (running in background)"
echo "Check status with: az group show --name $RESOURCE_GROUP"
TEARDOWN_EOF

chmod +x deployment/teardown-azure.sh
