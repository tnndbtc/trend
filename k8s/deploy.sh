#!/bin/bash

# ==============================================================================
# Kubernetes Deployment Script for Trend Intelligence Platform
# ==============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}"
echo "========================================================="
echo "  Trend Intelligence Platform - Kubernetes Deployment"
echo "========================================================="
echo -e "${NC}"

# Check prerequisites
check_prerequisites() {
    echo -e "${BLUE}Checking prerequisites...${NC}"
    echo ""

    local all_good=true

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        echo -e "${RED}❌ kubectl not installed${NC}"
        echo "Install: https://kubernetes.io/docs/tasks/tools/"
        all_good=false
    else
        echo -e "${GREEN}✅ kubectl installed${NC}"
    fi

    # Check cluster connection
    if kubectl cluster-info &> /dev/null; then
        echo -e "${GREEN}✅ Connected to cluster: $(kubectl config current-context)${NC}"
    else
        echo -e "${RED}❌ Not connected to a Kubernetes cluster${NC}"
        all_good=false
    fi

    if [ "$all_good" = false ]; then
        echo ""
        echo -e "${RED}Please fix prerequisites before continuing${NC}"
        exit 1
    fi

    echo ""
}

# Show menu
show_menu() {
    echo ""
    echo -e "${BLUE}========================================================="
    echo "  Kubernetes Deployment Menu"
    echo "=========================================================${NC}"
    echo ""
    echo -e "${CYAN}🚀 Deployment${NC}"
    echo -e "${GREEN}1)${NC} Deploy Full Platform"
    echo -e "${GREEN}2)${NC} Deploy Application Only (assumes infrastructure exists)"
    echo -e "${GREEN}3)${NC} Deploy Infrastructure Only (databases, etc.)"
    echo ""
    echo -e "${CYAN}🔐 Secrets Management${NC}"
    echo -e "${GREEN}4)${NC} Create Secrets from Environment Variables"
    echo -e "${GREEN}5)${NC} Setup External Secrets Operator"
    echo -e "${GREEN}6)${NC} Setup Sealed Secrets"
    echo ""
    echo -e "${CYAN}📊 Management${NC}"
    echo -e "${GREEN}7)${NC} Check Deployment Status"
    echo -e "${GREEN}8)${NC} View Pods and Logs"
    echo -e "${GREEN}9)${NC} Scale Deployment"
    echo -e "${GREEN}10)${NC} Update Configuration"
    echo ""
    echo -e "${CYAN}🔧 Maintenance${NC}"
    echo -e "${GREEN}11)${NC} Show Access URLs"
    echo -e "${GREEN}12)${NC} Create Port Forwards"
    echo -e "${GREEN}13)${NC} Cleanup / Delete Deployment"
    echo ""
    echo -e "${RED}0)${NC} Exit"
    echo ""
    echo -n "Select an option: "
}

# Deploy full platform
deploy_full() {
    echo ""
    echo -e "${BLUE}========================================================="
    echo "  Deploy Full Platform"
    echo "=========================================================${NC}"
    echo ""

    # Check for secrets
    if ! kubectl get secret api-keys -n trend-intelligence &> /dev/null; then
        echo -e "${YELLOW}⚠️  Secrets not found${NC}"
        echo ""
        echo "You need to create secrets first. Choose one:"
        echo "  1) Create from environment variables (quick)"
        echo "  2) Use External Secrets Operator (production)"
        echo "  3) Use Sealed Secrets (GitOps)"
        echo ""
        echo -n "Which method? (1/2/3): "
        read -r method
        case $method in
            1) ./secrets/create-from-env.sh ;;
            2) echo "See k8s/secrets/external-secrets/README.md" ; return ;;
            3) echo "See k8s/secrets/sealed-secrets/README.md" ; return ;;
            *) echo "Invalid choice" ; return ;;
        esac
    fi

    echo -e "${BLUE}Deploying namespace...${NC}"
    kubectl apply -f base/namespace.yaml

    echo -e "${BLUE}Deploying infrastructure...${NC}"
    kubectl apply -f base/postgres-statefulset.yaml
    kubectl apply -f base/redis-deployment.yaml
    kubectl apply -f base/qdrant-statefulset.yaml

    echo -e "${BLUE}Waiting for infrastructure to be ready...${NC}"
    kubectl wait --for=condition=ready pod -l app=postgres -n trend-intelligence --timeout=300s
    kubectl wait --for=condition=ready pod -l app=redis -n trend-intelligence --timeout=120s

    echo -e "${BLUE}Deploying application...${NC}"
    kubectl apply -f base/configmap.yaml
    kubectl apply -f base/api-deployment.yaml
    kubectl apply -f base/celery-worker-deployment.yaml

    echo -e "${BLUE}Deploying ingress...${NC}"
    kubectl apply -f base/ingress.yaml

    echo ""
    echo -e "${GREEN}✅ Deployment complete!${NC}"
    echo ""
    check_status
}

# Check deployment status
check_status() {
    echo ""
    echo -e "${BLUE}========================================================="
    echo "  Deployment Status"
    echo "=========================================================${NC}"
    echo ""

    echo -e "${CYAN}Pods:${NC}"
    kubectl get pods -n trend-intelligence

    echo ""
    echo -e "${CYAN}Services:${NC}"
    kubectl get svc -n trend-intelligence

    echo ""
    echo -e "${CYAN}Ingress:${NC}"
    kubectl get ingress -n trend-intelligence

    echo ""
}

# View logs
view_logs() {
    echo ""
    echo -e "${BLUE}========================================================="
    echo "  View Logs"
    echo "=========================================================${NC}"
    echo ""

    echo "Select component:"
    echo "  1) API"
    echo "  2) Celery Worker"
    echo "  3) PostgreSQL"
    echo "  4) All pods"
    echo ""
    echo -n "Choice: "
    read -r choice

    case $choice in
        1) kubectl logs -n trend-intelligence -l app=trend-api --tail=100 -f ;;
        2) kubectl logs -n trend-intelligence -l app=celery-worker --tail=100 -f ;;
        3) kubectl logs -n trend-intelligence postgres-0 --tail=100 -f ;;
        4) kubectl logs -n trend-intelligence --all-containers=true --tail=50 ;;
        *) echo "Invalid choice" ;;
    esac
}

# Scale deployment
scale_deployment() {
    echo ""
    echo -e "${BLUE}========================================================="
    echo "  Scale Deployment"
    echo "=========================================================${NC}"
    echo ""

    echo "Select component to scale:"
    echo "  1) API (current: $(kubectl get deployment trend-api -n trend-intelligence -o jsonpath='{.spec.replicas}'))"
    echo "  2) Celery Worker (current: $(kubectl get deployment celery-worker -n trend-intelligence -o jsonpath='{.spec.replicas}'))"
    echo ""
    echo -n "Choice: "
    read -r choice

    echo -n "New replica count: "
    read -r replicas

    case $choice in
        1) kubectl scale deployment trend-api --replicas=$replicas -n trend-intelligence ;;
        2) kubectl scale deployment celery-worker --replicas=$replicas -n trend-intelligence ;;
        *) echo "Invalid choice" ; return ;;
    esac

    echo -e "${GREEN}✅ Scaled successfully${NC}"
}

# Show access URLs
show_urls() {
    echo ""
    echo -e "${BLUE}========================================================="
    echo "  Access URLs"
    echo "=========================================================${NC}"
    echo ""

    INGRESS_IP=$(kubectl get ingress trend-ingress -n trend-intelligence -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")

    if [ "$INGRESS_IP" = "pending" ]; then
        echo -e "${YELLOW}⚠️  Ingress IP not yet assigned${NC}"
        echo "Use port-forward to access services locally (option 12)"
    else
        echo -e "${GREEN}Ingress IP: $INGRESS_IP${NC}"
        echo ""
        echo "Access via:"
        echo "  • API: http://$INGRESS_IP/api/v1"
        echo "  • Web: http://$INGRESS_IP"
        echo "  • Docs: http://$INGRESS_IP/docs"
    fi

    echo ""
}

# Create port forwards
create_port_forwards() {
    echo ""
    echo -e "${BLUE}========================================================="
    echo "  Create Port Forwards"
    echo "=========================================================${NC}"
    echo ""

    echo "Starting port forwards (press Ctrl+C to stop)..."
    echo ""
    echo "Forwarding:"
    echo "  • API: http://localhost:8000"
    echo "  • PostgreSQL: localhost:5432"
    echo ""

    # Run port forwards in background
    kubectl port-forward -n trend-intelligence svc/trend-api 8000:8000 &
    PF1=$!
    kubectl port-forward -n trend-intelligence svc/postgres 5432:5432 &
    PF2=$!

    # Wait for Ctrl+C
    trap "kill $PF1 $PF2 2>/dev/null" EXIT
    wait
}

# Cleanup
cleanup() {
    echo ""
    echo -e "${BLUE}========================================================="
    echo "  Cleanup Deployment"
    echo "=========================================================${NC}"
    echo ""

    echo -e "${RED}⚠️  WARNING: This will delete all resources!${NC}"
    echo -n "Are you sure? (yes/no): "
    read -r confirm

    if [ "$confirm" = "yes" ]; then
        echo -e "${BLUE}Deleting namespace (this will remove everything)...${NC}"
        kubectl delete namespace trend-intelligence
        echo -e "${GREEN}✅ Cleanup complete${NC}"
    else
        echo "Cancelled"
    fi
}

# Main loop
check_prerequisites

while true; do
    show_menu
    read -r choice

    case $choice in
        1) deploy_full ;;
        2) echo "Deploy app-only: kubectl apply -f base/api-deployment.yaml -f base/celery-worker-deployment.yaml" ;;
        3) echo "Deploy infra: kubectl apply -f base/postgres-statefulset.yaml -f base/redis-deployment.yaml -f base/qdrant-statefulset.yaml" ;;
        4) cd secrets && ./create-from-env.sh && cd .. ;;
        5) echo "See: k8s/secrets/external-secrets/README.md" ;;
        6) echo "See: k8s/secrets/sealed-secrets/README.md" ;;
        7) check_status ;;
        8) view_logs ;;
        9) scale_deployment ;;
        10) echo "Update config: kubectl apply -f base/configmap.yaml && kubectl rollout restart deployment -n trend-intelligence" ;;
        11) show_urls ;;
        12) create_port_forwards ;;
        13) cleanup ;;
        0) echo "Goodbye!" ; exit 0 ;;
        *) echo -e "${RED}Invalid option${NC}" ;;
    esac

    echo ""
    echo -n "Press Enter to continue..."
    read
done
