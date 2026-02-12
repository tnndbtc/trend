#!/bin/bash

# ==============================================================================
# Create Sealed Secrets from Environment Variables
# ==============================================================================
#
# This script creates encrypted SealedSecrets from environment variables.
# The encrypted secrets are safe to commit to git.
#
# Usage:
#   export OPENAI_API_KEY='sk-proj-xxxxx'
#   export POSTGRES_PASSWORD='secure-password'
#   ./create-sealed-secrets.sh
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
echo "  Sealed Secrets Creation"
echo "==================================================${NC}"
echo ""

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl is not installed${NC}"
    exit 1
fi

# Check if kubeseal is installed
if ! command -v kubeseal &> /dev/null; then
    echo -e "${RED}❌ kubeseal is not installed${NC}"
    echo ""
    echo "Install with:"
    echo "  wget https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/kubeseal-0.24.0-linux-amd64.tar.gz"
    echo "  tar -xvzf kubeseal-0.24.0-linux-amd64.tar.gz"
    echo "  sudo install -m 755 kubeseal /usr/local/bin/kubeseal"
    exit 1
fi

echo -e "${GREEN}✅ kubectl and kubeseal are installed${NC}"
echo ""

# Check environment variables
NAMESPACE="trend-intelligence"
MISSING_VARS=()

check_var() {
    local var_name="$1"
    if [ -z "${!var_name}" ]; then
        echo -e "${RED}❌ $var_name not set${NC}"
        MISSING_VARS+=("$var_name")
    else
        echo -e "${GREEN}✅ $var_name set${NC}"
    fi
}

echo "Checking environment variables..."
check_var "OPENAI_API_KEY"
check_var "POSTGRES_USER"
check_var "POSTGRES_PASSWORD"

YOUTUBE_API_KEY="${YOUTUBE_API_KEY:-placeholder}"
if [ "$YOUTUBE_API_KEY" != "placeholder" ]; then
    echo -e "${GREEN}✅ YOUTUBE_API_KEY set${NC}"
else
    echo -e "${YELLOW}⚠️  YOUTUBE_API_KEY not set (using placeholder)${NC}"
fi

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo ""
    echo -e "${RED}❌ Missing required environment variables!${NC}"
    echo "Please set: ${MISSING_VARS[*]}"
    exit 1
fi

echo ""
echo -e "${BLUE}Creating temporary secret manifests...${NC}"

# Create temporary directory
TMP_DIR=$(mktemp -d)
trap "rm -rf $TMP_DIR" EXIT

# Create api-keys secret
kubectl create secret generic api-keys \
  --from-literal=openai-api-key="$OPENAI_API_KEY" \
  --from-literal=youtube-api-key="$YOUTUBE_API_KEY" \
  --namespace="$NAMESPACE" \
  --dry-run=client \
  -o yaml > "$TMP_DIR/api-keys.yaml"

# Create postgres-credentials secret
kubectl create secret generic postgres-credentials \
  --from-literal=username="$POSTGRES_USER" \
  --from-literal=password="$POSTGRES_PASSWORD" \
  --namespace="$NAMESPACE" \
  --dry-run=client \
  -o yaml > "$TMP_DIR/postgres-credentials.yaml"

echo -e "${GREEN}✅ Created temporary manifests${NC}"
echo ""

# Encrypt with kubeseal
echo -e "${BLUE}Encrypting secrets with kubeseal...${NC}"

kubeseal -f "$TMP_DIR/api-keys.yaml" \
  -w api-keys-sealed.yaml \
  --namespace="$NAMESPACE"

kubeseal -f "$TMP_DIR/postgres-credentials.yaml" \
  -w postgres-credentials-sealed.yaml \
  --namespace="$NAMESPACE"

echo -e "${GREEN}✅ Created encrypted SealedSecrets${NC}"
echo ""

echo -e "${GREEN}=================================================="
echo "  ✅ Sealed Secrets Created!"
echo "==================================================${NC}"
echo ""

echo "Created files:"
echo "  • api-keys-sealed.yaml"
echo "  • postgres-credentials-sealed.yaml"
echo ""

echo -e "${BLUE}These encrypted files are safe to commit to git!${NC}"
echo ""

echo "Next steps:"
echo ""
echo "  1. Review the encrypted files:"
echo "     cat api-keys-sealed.yaml"
echo ""
echo "  2. Commit to git:"
echo "     git add *-sealed.yaml"
echo "     git commit -m 'Add encrypted secrets'"
echo "     git push"
echo ""
echo "  3. Apply to cluster:"
echo "     kubectl apply -f api-keys-sealed.yaml"
echo "     kubectl apply -f postgres-credentials-sealed.yaml"
echo ""
echo "  4. Verify secrets were created:"
echo "     kubectl get secrets -n $NAMESPACE"
echo ""
echo -e "${YELLOW}💡 Tip:${NC} The controller will automatically decrypt and create k8s secrets"
echo ""
