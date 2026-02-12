#!/bin/bash

# ==============================================================================
# Create Kubernetes Secrets from Environment Variables
# ==============================================================================
#
# This script creates Kubernetes secrets from environment variables.
# It follows the same security pattern as the Docker Compose setup:
#   - Secrets come from environment variables, never from files
#   - Safe to run on any environment (dev/staging/prod)
#
# Usage:
#   export OPENAI_API_KEY='sk-proj-xxxxx'
#   export POSTGRES_PASSWORD='secure-password'
#   ./create-from-env.sh
#
# ==============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=================================================="
echo "  Kubernetes Secrets Creation"
echo "==================================================${NC}"
echo ""

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl is not installed${NC}"
    echo "Please install kubectl: https://kubernetes.io/docs/tasks/tools/"
    exit 1
fi

echo -e "${GREEN}✅ kubectl is installed${NC}"

# Check if namespace exists
NAMESPACE="trend-intelligence"
if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
    echo -e "${YELLOW}⚠️  Namespace '$NAMESPACE' does not exist${NC}"
    echo -n "Create namespace? (y/n): "
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        kubectl create namespace "$NAMESPACE"
        echo -e "${GREEN}✅ Created namespace '$NAMESPACE'${NC}"
    else
        echo -e "${RED}❌ Namespace required. Exiting.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ Namespace '$NAMESPACE' exists${NC}"
fi

echo ""
echo -e "${BLUE}Checking required environment variables...${NC}"
echo ""

# Track missing variables
MISSING_VARS=()

# Check required variables
check_var() {
    local var_name="$1"
    local var_desc="$2"

    if [ -z "${!var_name}" ]; then
        echo -e "${RED}❌ $var_name not set${NC} - $var_desc"
        MISSING_VARS+=("$var_name")
        return 1
    else
        echo -e "${GREEN}✅ $var_name set${NC}"
        return 0
    fi
}

# Required variables
check_var "OPENAI_API_KEY" "OpenAI API key (required)"
check_var "POSTGRES_USER" "PostgreSQL username (default: trend_user)"
check_var "POSTGRES_PASSWORD" "PostgreSQL password (required)"

# Optional variables
YOUTUBE_API_KEY="${YOUTUBE_API_KEY:-}"
if [ -n "$YOUTUBE_API_KEY" ]; then
    echo -e "${GREEN}✅ YOUTUBE_API_KEY set${NC} (optional)"
else
    echo -e "${YELLOW}⚠️  YOUTUBE_API_KEY not set${NC} (optional - will use placeholder)"
    YOUTUBE_API_KEY="placeholder"
fi

# If any required variables are missing, exit
if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo ""
    echo -e "${RED}❌ Missing required environment variables!${NC}"
    echo ""
    echo "Please set the following variables:"
    echo ""
    for var in "${MISSING_VARS[@]}"; do
        echo "  export $var='your-value-here'"
    done
    echo ""
    echo "Example setup:"
    echo ""
    echo "  export OPENAI_API_KEY='sk-proj-xxxxxxxxxxxxx'"
    echo "  export POSTGRES_USER='trend_user'"
    echo "  export POSTGRES_PASSWORD='secure-random-password'"
    echo "  export YOUTUBE_API_KEY='your-youtube-key'  # optional"
    echo ""
    echo "Then run this script again."
    echo ""
    exit 1
fi

echo ""
echo -e "${BLUE}=================================================="
echo "  Creating Secrets"
echo "==================================================${NC}"
echo ""

# Function to create or update secret
create_secret() {
    local secret_name="$1"
    shift
    local args=("$@")

    if kubectl get secret "$secret_name" -n "$NAMESPACE" &> /dev/null; then
        echo -e "${YELLOW}⚠️  Secret '$secret_name' already exists${NC}"
        echo -n "Replace it? (y/n): "
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            kubectl delete secret "$secret_name" -n "$NAMESPACE"
            echo -e "${BLUE}🔄 Deleted existing secret '$secret_name'${NC}"
        else
            echo -e "${BLUE}⏭️  Skipping '$secret_name'${NC}"
            return 0
        fi
    fi

    kubectl create secret generic "$secret_name" \
        -n "$NAMESPACE" \
        "${args[@]}"

    echo -e "${GREEN}✅ Created secret '$secret_name'${NC}"
}

# Create postgres-credentials secret
echo "Creating 'postgres-credentials' secret..."
create_secret "postgres-credentials" \
    --from-literal=username="$POSTGRES_USER" \
    --from-literal=password="$POSTGRES_PASSWORD"

# Create api-keys secret
echo ""
echo "Creating 'api-keys' secret..."
create_secret "api-keys" \
    --from-literal=openai-api-key="$OPENAI_API_KEY" \
    --from-literal=youtube-api-key="$YOUTUBE_API_KEY"

echo ""
echo -e "${GREEN}=================================================="
echo "  ✅ Secrets Created Successfully!"
echo "==================================================${NC}"
echo ""

# Verify secrets
echo -e "${BLUE}Verifying secrets...${NC}"
echo ""

kubectl get secrets -n "$NAMESPACE" | grep -E "(postgres-credentials|api-keys)"

echo ""
echo -e "${BLUE}Secret details:${NC}"
echo ""
kubectl describe secret postgres-credentials -n "$NAMESPACE" | grep -E "^Name:|^Namespace:|^Data$" -A 5
echo ""
kubectl describe secret api-keys -n "$NAMESPACE" | grep -E "^Name:|^Namespace:|^Data$" -A 5

echo ""
echo -e "${GREEN}✅ Secrets are ready for use!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  1. Deploy the application:"
echo "     kubectl apply -k k8s/base"
echo ""
echo "  2. Verify pods are running:"
echo "     kubectl get pods -n $NAMESPACE"
echo ""
echo "  3. Check logs if needed:"
echo "     kubectl logs -n $NAMESPACE -l app=trend-api"
echo ""
echo -e "${YELLOW}💡 Tip:${NC} To update secrets, just export new values and run this script again."
echo ""
