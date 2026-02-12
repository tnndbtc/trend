#!/bin/bash

# AI Trend Intelligence Agent - Docker Setup Script
# This script provides a menu-driven interface for managing the application

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "=================================================="
echo "  AI Trend Intelligence Platform - Setup"
echo "=================================================="
echo -e "${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

echo -e "${GREEN}✅ Docker is installed${NC}"

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✅ Docker Compose is installed${NC}"

# Determine which Docker Compose command to use
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE="docker compose"
fi

# Function to show menu
show_menu() {
    echo ""
    echo -e "${BLUE}=================================================="
    echo "  Main Menu"
    echo "==================================================${NC}"
    echo ""
    echo -e "${CYAN}🚀 Setup & Startup${NC}"
    echo -e "${GREEN}1)${NC} Full Platform Setup (All Services)"
    echo -e "${GREEN}2)${NC} Basic Setup (Web Interface Only)"
    echo -e "${GREEN}3)${NC} Start/Stop Services (FastAPI, Celery, Monitoring)"
    echo ""
    echo -e "${CYAN}📊 Data Collection${NC}"
    echo -e "${GREEN}4)${NC} Collect Trends"
    echo -e "${GREEN}5)${NC} Manage Categories"
    echo ""
    echo -e "${CYAN}🔧 System Management${NC}"
    echo -e "${GREEN}6)${NC} Service Status & Health Check"
    echo -e "${GREEN}7)${NC} View Logs"
    echo -e "${GREEN}8)${NC} Database Operations"
    echo -e "${GREEN}9)${NC} Clean Old Data"
    echo ""
    echo -e "${CYAN}🔐 Configuration${NC}"
    echo -e "${GREEN}10)${NC} Generate API Keys"
    echo -e "${GREEN}11)${NC} Show All Access URLs"
    echo ""
    echo -e "${RED}0)${NC} Exit"
    echo ""
    echo -n "Select an option: "
}

# Function for full platform setup
full_platform_setup() {
    echo ""
    echo -e "${BLUE}=================================================="
    echo "  Full Platform Setup"
    echo "==================================================${NC}"
    echo ""
    echo -e "${CYAN}This will start all services:${NC}"
    echo "  • Django Web Interface (port 11800)"
    echo "  • FastAPI REST API (port 8080)"
    echo "  • PostgreSQL Database (port 5433)"
    echo "  • Qdrant Vector DB (ports 6333, 6334)"
    echo "  • Redis Cache (port 6380)"
    echo "  • RabbitMQ Message Queue (ports 5672, 15672)"
    echo "  • Celery Workers (background tasks)"
    echo "  • Celery Beat (scheduled tasks)"
    echo "  • Grafana Monitoring (port 3000)"
    echo "  • Prometheus Metrics (port 9090)"
    echo ""

    # Check and create .env.docker
    if ! check_environment; then
        return 1
    fi

    # Create data directories
    echo -e "${BLUE}📁 Creating data directories...${NC}"
    mkdir -p data/db data/cache
    echo -e "${GREEN}✅ Data directories created${NC}"

    # Stop existing containers
    echo -e "${BLUE}🛑 Stopping any existing containers...${NC}"
    ${DOCKER_COMPOSE} down 2>/dev/null || true
    echo -e "${GREEN}✅ Cleanup complete${NC}"

    # Build images
    echo -e "${BLUE}🔨 Building Docker images...${NC}"
    if ! ${DOCKER_COMPOSE} build; then
        echo -e "${RED}❌ Docker build failed${NC}"
        return 1
    fi
    echo -e "${GREEN}✅ Docker images built successfully${NC}"

    # Start all services with profiles
    echo -e "${BLUE}🚀 Starting all services...${NC}"
    if ! ${DOCKER_COMPOSE} --profile api --profile celery --profile observability up -d; then
        echo -e "${RED}❌ Failed to start services${NC}"
        return 1
    fi

    # Wait for services
    echo -e "${BLUE}⏳ Waiting for services to start...${NC}"
    sleep 10

    # Show status
    show_service_status

    echo ""
    echo -e "${GREEN}=================================================="
    echo "  🎉 Full Platform Setup Complete!"
    echo "==================================================${NC}"
    echo ""

    show_all_urls
    return 0
}

# Function for basic setup (web only)
build_and_start() {
    echo ""
    echo -e "${BLUE}=================================================="
    echo "  Basic Setup (Web Interface Only)"
    echo "==================================================${NC}"
    echo ""

    # Check and create .env.docker
    if ! check_environment; then
        return 1
    fi

    # Create data directories
    echo -e "${BLUE}📁 Creating data directories...${NC}"
    mkdir -p data/db data/cache
    echo -e "${GREEN}✅ Data directories created${NC}"

    # Stop and remove any existing containers
    echo -e "${BLUE}🛑 Stopping and removing any existing containers...${NC}"
    docker stop trend-intelligence-agent 2>/dev/null || true
    docker rm -f trend-intelligence-agent 2>/dev/null || true
    ${DOCKER_COMPOSE} down 2>/dev/null || true
    echo -e "${GREEN}✅ Cleanup complete${NC}"

    # Build the Docker image
    echo -e "${BLUE}🔨 Building Docker image...${NC}"
    if ! ${DOCKER_COMPOSE} build; then
        echo -e "${RED}❌ Docker build failed${NC}"
        return 1
    fi

    echo -e "${GREEN}✅ Docker image built successfully${NC}"

    # Start the containers (without profiles = basic services only)
    echo -e "${BLUE}🚀 Starting containers...${NC}"
    if ! ${DOCKER_COMPOSE} up -d; then
        echo -e "${RED}❌ Failed to start containers${NC}"
        return 1
    fi

    # Wait for the service to be ready
    echo -e "${BLUE}⏳ Waiting for service to start...${NC}"
    sleep 5

    # Check if container is running
    if ${DOCKER_COMPOSE} ps | grep -q "Up"; then
        echo -e "${GREEN}✅ Container is running${NC}"
    else
        echo -e "${RED}❌ Container failed to start${NC}"
        echo "Check logs with: ${DOCKER_COMPOSE} logs"
        return 1
    fi

    echo ""
    echo -e "${GREEN}=================================================="
    echo "  🎉 Basic Setup Complete!"
    echo "==================================================${NC}"
    echo ""
    echo -e "${BLUE}📊 Web Interface:${NC} http://localhost:11800"
    echo -e "${BLUE}🔧 Admin Panel:${NC}    http://localhost:11800/admin"
    echo ""
    echo -e "${YELLOW}Default Admin Credentials:${NC}"
    echo "  Username: admin"
    echo "  Password: changeme123"
    echo "  (Change these in .env.docker)"
    echo ""
    echo -e "${CYAN}ℹ️  For full platform with API, Celery, and Monitoring, use Option 1${NC}"
    echo ""
    echo -e "${BLUE}📈 To collect trends, run:${NC}"
    echo "  ${DOCKER_COMPOSE} exec web python manage.py collect_trends --max-posts-per-category 5"
    echo ""
    echo -e "${BLUE}📋 Useful Commands:${NC}"
    echo "  View logs:     ${DOCKER_COMPOSE} logs -f"
    echo "  Stop service:  ${DOCKER_COMPOSE} down"
    echo "  Restart:       ${DOCKER_COMPOSE} restart"
    echo "  Shell access:  ${DOCKER_COMPOSE} exec web bash"
    echo ""
    echo -e "${GREEN}✨ Happy trend hunting!${NC}"
    echo ""
}

# Function to check and create environment
check_environment() {
    # Check if .env.docker exists and create it if missing
    if [ ! -f .env.docker ]; then
        if [ -f .env.docker.example ]; then
            echo -e "${BLUE}📝 Creating .env.docker from template...${NC}"
            cp .env.docker.example .env.docker
            echo -e "${GREEN}✅ Created .env.docker (with placeholders)${NC}"
            echo ""
        else
            echo -e "${RED}❌ Template file .env.docker.example not found${NC}"
            echo "Please ensure .env.docker.example exists in the current directory"
            return 1
        fi
    fi

    # Check if OPENAI_API_KEY is set in environment variable
    if [ -z "$OPENAI_API_KEY" ]; then
        echo -e "${RED}❌ OPENAI_API_KEY environment variable not set${NC}"
        echo ""
        echo -e "${YELLOW}🔐 Security Best Practice: Set API keys as environment variables${NC}"
        echo ""
        echo "Please set your OpenAI API key as an environment variable:"
        echo ""
        echo -e "${CYAN}# Temporary (current session):${NC}"
        echo "  export OPENAI_API_KEY='sk-proj-xxxxxxxxxxxxx'"
        echo "  ./setup.sh"
        echo ""
        echo -e "${CYAN}# Permanent (add to ~/.bashrc or ~/.zshrc):${NC}"
        echo "  echo \"export OPENAI_API_KEY='sk-proj-xxxxxxxxxxxxx'\" >> ~/.bashrc"
        echo "  source ~/.bashrc"
        echo "  ./setup.sh"
        echo ""
        echo -e "${BLUE}Get your API key from:${NC} https://platform.openai.com/api-keys"
        echo ""
        echo -e "${YELLOW}💡 For testing without API costs:${NC}"
        echo "  export MOCK_API=1"
        echo "  export OPENAI_API_KEY='mock-key-for-testing'"
        echo ""
        return 1
    fi

    echo -e "${GREEN}✅ Using OPENAI_API_KEY from environment variable${NC}"

    # Optionally check for other important environment variables
    if [ -n "$MOCK_API" ] && [ "$MOCK_API" = "1" ]; then
        echo -e "${YELLOW}⚠️  Running in MOCK mode (no real API calls)${NC}"
    fi

    return 0
}

# Function to manage individual services
manage_services() {
    echo ""
    echo -e "${BLUE}=================================================="
    echo "  Manage Services"
    echo "==================================================${NC}"
    echo ""
    echo -e "${GREEN}1)${NC} Start FastAPI (REST API)"
    echo -e "${GREEN}2)${NC} Stop FastAPI"
    echo -e "${GREEN}3)${NC} Start Celery (Background Tasks)"
    echo -e "${GREEN}4)${NC} Stop Celery"
    echo -e "${GREEN}5)${NC} Start Monitoring (Grafana + Prometheus)"
    echo -e "${GREEN}6)${NC} Stop Monitoring"
    echo -e "${GREEN}7)${NC} Start ALL Optional Services"
    echo -e "${GREEN}8)${NC} Stop ALL Services"
    echo -e "${RED}0)${NC} Back to Main Menu"
    echo ""
    echo -n "Select an option: "
    read service_choice

    case $service_choice in
        1)
            echo ""
            echo -e "${BLUE}🚀 Starting FastAPI...${NC}"
            ${DOCKER_COMPOSE} --profile api up -d api
            echo -e "${GREEN}✅ FastAPI started${NC}"
            echo -e "${BLUE}📚 API Docs:${NC} http://localhost:8000/docs"
            ;;
        2)
            echo ""
            echo -e "${BLUE}🛑 Stopping FastAPI...${NC}"
            ${DOCKER_COMPOSE} stop api
            echo -e "${GREEN}✅ FastAPI stopped${NC}"
            ;;
        3)
            echo ""
            echo -e "${BLUE}🚀 Starting Celery workers...${NC}"
            ${DOCKER_COMPOSE} --profile celery up -d celery-worker celery-beat
            echo -e "${GREEN}✅ Celery started${NC}"
            echo -e "${CYAN}ℹ️  Background tasks and scheduled collection are now active${NC}"
            ;;
        4)
            echo ""
            echo -e "${BLUE}🛑 Stopping Celery...${NC}"
            ${DOCKER_COMPOSE} stop celery-worker celery-beat
            echo -e "${GREEN}✅ Celery stopped${NC}"
            ;;
        5)
            echo ""
            echo -e "${BLUE}🚀 Starting Monitoring stack...${NC}"
            ${DOCKER_COMPOSE} --profile observability up -d
            echo -e "${GREEN}✅ Monitoring started${NC}"
            echo -e "${BLUE}📊 Grafana:${NC}    http://localhost:3000 (admin/admin)"
            echo -e "${BLUE}📈 Prometheus:${NC} http://localhost:9090"
            ;;
        6)
            echo ""
            echo -e "${BLUE}🛑 Stopping Monitoring...${NC}"
            ${DOCKER_COMPOSE} stop prometheus grafana postgres-exporter redis-exporter node-exporter
            echo -e "${GREEN}✅ Monitoring stopped${NC}"
            ;;
        7)
            echo ""
            echo -e "${BLUE}🚀 Starting ALL optional services...${NC}"
            ${DOCKER_COMPOSE} --profile api --profile celery --profile observability up -d
            echo -e "${GREEN}✅ All services started${NC}"
            show_all_urls
            ;;
        8)
            echo ""
            echo -e "${YELLOW}⚠️  This will stop ALL services. Continue?${NC}"
            echo -n "Type 'yes' to confirm: "
            read confirm
            if [ "$confirm" = "yes" ]; then
                echo -e "${BLUE}🛑 Stopping all services...${NC}"
                ${DOCKER_COMPOSE} down
                echo -e "${GREEN}✅ All services stopped${NC}"
            else
                echo -e "${BLUE}ℹ️  Cancelled${NC}"
            fi
            ;;
        0)
            return 0
            ;;
        *)
            echo -e "${RED}❌ Invalid option${NC}"
            sleep 1
            ;;
    esac

    echo ""
    read -p "Press Enter to continue..."
}

# Function to show service status and health
show_service_status() {
    echo ""
    echo -e "${BLUE}=================================================="
    echo "  Service Status & Health Check"
    echo "==================================================${NC}"
    echo ""
    echo -e "${CYAN}Running Services:${NC}"
    ${DOCKER_COMPOSE} ps
    echo ""
    echo -e "${CYAN}Health Checks:${NC}"

    # Check Web
    if curl -sf http://localhost:11800 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Django Web Interface${NC} - http://localhost:11800"
    else
        echo -e "${RED}❌ Django Web Interface${NC} - http://localhost:11800 (not responding)"
    fi

    # Check API
    if curl -sf http://localhost:8080 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ FastAPI REST API${NC} - http://localhost:8080"
    else
        echo -e "${YELLOW}⚠️  FastAPI REST API${NC} - http://localhost:8080 (not started or not responding)"
    fi

    # Check Grafana
    if curl -sf http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Grafana Monitoring${NC} - http://localhost:3000"
    else
        echo -e "${YELLOW}⚠️  Grafana Monitoring${NC} - http://localhost:3000 (not started)"
    fi

    # Check RabbitMQ
    if curl -sf http://localhost:15672 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ RabbitMQ Management${NC} - http://localhost:15672"
    else
        echo -e "${YELLOW}⚠️  RabbitMQ Management${NC} - http://localhost:15672 (not responding)"
    fi

    # Check Prometheus
    if curl -sf http://localhost:9090 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Prometheus${NC} - http://localhost:9090"
    else
        echo -e "${YELLOW}⚠️  Prometheus${NC} - http://localhost:9090 (not started)"
    fi

    echo ""
    echo -e "${CYAN}Resource Usage:${NC}"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null | head -10

    echo ""
    read -p "Press Enter to continue..."
}

# Function to view logs
view_logs() {
    echo ""
    echo -e "${BLUE}=================================================="
    echo "  View Service Logs"
    echo "==================================================${NC}"
    echo ""
    echo -e "${GREEN}1)${NC} Django Web"
    echo -e "${GREEN}2)${NC} FastAPI"
    echo -e "${GREEN}3)${NC} Celery Worker"
    echo -e "${GREEN}4)${NC} Celery Beat"
    echo -e "${GREEN}5)${NC} PostgreSQL"
    echo -e "${GREEN}6)${NC} Redis"
    echo -e "${GREEN}7)${NC} RabbitMQ"
    echo -e "${GREEN}8)${NC} All Services"
    echo -e "${RED}0)${NC} Back to Main Menu"
    echo ""
    echo -n "Select service: "
    read log_choice

    case $log_choice in
        1)
            echo ""
            echo -e "${CYAN}Showing Django Web logs (Ctrl+C to exit)...${NC}"
            echo ""
            ${DOCKER_COMPOSE} logs -f web
            ;;
        2)
            echo ""
            echo -e "${CYAN}Showing FastAPI logs (Ctrl+C to exit)...${NC}"
            echo ""
            ${DOCKER_COMPOSE} logs -f api
            ;;
        3)
            echo ""
            echo -e "${CYAN}Showing Celery Worker logs (Ctrl+C to exit)...${NC}"
            echo ""
            ${DOCKER_COMPOSE} logs -f celery-worker
            ;;
        4)
            echo ""
            echo -e "${CYAN}Showing Celery Beat logs (Ctrl+C to exit)...${NC}"
            echo ""
            ${DOCKER_COMPOSE} logs -f celery-beat
            ;;
        5)
            echo ""
            echo -e "${CYAN}Showing PostgreSQL logs (Ctrl+C to exit)...${NC}"
            echo ""
            ${DOCKER_COMPOSE} logs -f postgres
            ;;
        6)
            echo ""
            echo -e "${CYAN}Showing Redis logs (Ctrl+C to exit)...${NC}"
            echo ""
            ${DOCKER_COMPOSE} logs -f redis
            ;;
        7)
            echo ""
            echo -e "${CYAN}Showing RabbitMQ logs (Ctrl+C to exit)...${NC}"
            echo ""
            ${DOCKER_COMPOSE} logs -f rabbitmq
            ;;
        8)
            echo ""
            echo -e "${CYAN}Showing all logs (Ctrl+C to exit)...${NC}"
            echo ""
            ${DOCKER_COMPOSE} logs -f
            ;;
        0)
            return 0
            ;;
        *)
            echo -e "${RED}❌ Invalid option${NC}"
            sleep 1
            ;;
    esac
}

# Function to show all access URLs
show_all_urls() {
    echo ""
    echo -e "${CYAN}=================================================="
    echo "  Access URLs & Credentials"
    echo "==================================================${NC}"
    echo ""
    echo -e "${MAGENTA}Web Interfaces:${NC}"
    echo -e "${BLUE}  Django Web:       ${NC}http://localhost:11800"
    echo -e "${BLUE}  Django Admin:     ${NC}http://localhost:11800/admin"
    echo -e "${BLUE}  FastAPI Docs:     ${NC}http://localhost:8000/docs"
    echo -e "${BLUE}  FastAPI ReDoc:    ${NC}http://localhost:8000/redoc"
    echo -e "${BLUE}  Grafana:          ${NC}http://localhost:3000"
    echo -e "${BLUE}  Prometheus:       ${NC}http://localhost:9090"
    echo -e "${BLUE}  RabbitMQ UI:      ${NC}http://localhost:15672"
    echo ""
    echo -e "${MAGENTA}Database Connections:${NC}"
    echo -e "${BLUE}  PostgreSQL:       ${NC}localhost:5433"
    echo -e "${BLUE}  Qdrant:           ${NC}localhost:6333"
    echo -e "${BLUE}  Redis:            ${NC}localhost:6380"
    echo -e "${BLUE}  RabbitMQ:         ${NC}localhost:5672"
    echo ""
    echo -e "${MAGENTA}Default Credentials:${NC}"
    echo -e "${YELLOW}  Django Admin:${NC}"
    echo -e "    Username: admin"
    echo -e "    Password: changeme123"
    echo ""
    echo -e "${YELLOW}  Grafana:${NC}"
    echo -e "    Username: admin"
    echo -e "    Password: admin"
    echo ""
    echo -e "${YELLOW}  RabbitMQ:${NC}"
    echo -e "    Username: trend_user"
    echo -e "    Password: trend_password"
    echo ""
    echo -e "${YELLOW}  PostgreSQL:${NC}"
    echo -e "    Username: trend_user"
    echo -e "    Password: trend_password"
    echo -e "    Database: trends"
    echo ""
    echo -e "${CYAN}ℹ️  Change default credentials in .env.docker for production${NC}"
    echo ""
    read -p "Press Enter to continue..."
}

# Function to generate API keys
generate_api_keys() {
    echo ""
    echo -e "${BLUE}=================================================="
    echo "  Generate API Keys"
    echo "==================================================${NC}"
    echo ""

    # Check if openssl is available
    if ! command -v openssl &> /dev/null; then
        echo -e "${RED}❌ openssl not found. Cannot generate secure keys.${NC}"
        echo ""
        echo "Alternative: Use an online key generator or run:"
        echo "  python3 -c 'import secrets; print(secrets.token_hex(32))'"
        return 1
    fi

    echo -e "${CYAN}Generating secure API keys...${NC}"
    echo ""

    # Generate keys
    API_KEY=$(openssl rand -hex 32)
    ADMIN_KEY=$(openssl rand -hex 32)

    echo -e "${GREEN}✅ Keys generated successfully!${NC}"
    echo ""
    echo -e "${YELLOW}Add these to your .env.docker file:${NC}"
    echo ""
    echo -e "${CYAN}# FastAPI Configuration${NC}"
    echo "API_KEYS=$API_KEY"
    echo "ADMIN_API_KEYS=$ADMIN_KEY"
    echo ""
    echo -e "${YELLOW}Example API usage:${NC}"
    echo ""
    echo "# User API request:"
    echo "curl -H \"X-API-Key: $API_KEY\" http://localhost:8000/api/v1/trends"
    echo ""
    echo "# Admin API request:"
    echo "curl -X POST -H \"X-API-Key: $ADMIN_KEY\" http://localhost:8000/api/v1/admin/collect"
    echo ""
    echo -e "${CYAN}ℹ️  After adding keys to .env.docker, restart the API:${NC}"
    echo "  ${DOCKER_COMPOSE} restart api"
    echo ""
    read -p "Press Enter to continue..."
}

# Function to collect trends
collect_trends() {
    echo ""
    echo -e "${BLUE}=================================================="
    echo "  Collect Trends"
    echo "==================================================${NC}"
    echo ""

    # Check if container is running
    if ! ${DOCKER_COMPOSE} ps | grep -q "Up"; then
        echo -e "${RED}❌ Container is not running${NC}"
        echo "Please start the container first (Option 1 or 2)"
        return 1
    fi

    echo -e "${GREEN}✅ Container is running${NC}"
    echo ""

    # Show current categories
    echo -e "${BLUE}📂 Current Categories:${NC}"
    ${DOCKER_COMPOSE} exec web python -c "
from categories import list_categories
categories = list_categories()
for i, cat in enumerate(categories, 1):
    print(f'  {i}. {cat}')
print(f'\nTotal: {len(categories)} categories')
" 2>/dev/null

    echo ""
    echo -e "${BLUE}ℹ️  The system will create one cluster for each category${NC}"
    echo ""
    echo -e "${YELLOW}Would you like to manage categories before collecting trends?${NC}"
    echo -e "${GREEN}1)${NC} Yes, manage categories first"
    echo -e "${GREEN}2)${NC} No, proceed with current categories"
    echo ""
    echo -n "Select an option (default: 2): "
    read manage_choice

    # Handle category management if requested
    if [ "$manage_choice" = "1" ]; then
        manage_categories_submenu
        if [ $? -ne 0 ]; then
            echo -e "${RED}❌ Returning to main menu${NC}"
            return 1
        fi
        echo ""
        echo -e "${GREEN}✅ Categories configured. Proceeding with trend collection...${NC}"
        echo ""
    fi

    # Prompt for max posts per category
    echo -e "${BLUE}How many posts to keep for EACH category?${NC}"
    echo -e "  ${YELLOW}(The system will cluster all posts, then keep top N per category)${NC}"
    echo -n "Max posts per category (default: 5): "
    read max_posts_per_category

    # Use default if empty
    if [ -z "$max_posts_per_category" ]; then
        max_posts_per_category=5
    fi

    # Validate it's a number
    if ! [[ "$max_posts_per_category" =~ ^[0-9]+$ ]]; then
        echo -e "${RED}❌ Invalid number. Using default: 5${NC}"
        max_posts_per_category=5
    fi

    echo ""
    echo -e "${BLUE}🚀 Starting trend collection...${NC}"
    echo -e "${BLUE}   Max posts per category: $max_posts_per_category${NC}"
    echo -e "${BLUE}   The system will collect from all sources and distribute posts across categories${NC}"
    echo ""

    # Run the collect_trends command
    if ${DOCKER_COMPOSE} exec web python manage.py collect_trends --max-posts-per-category "$max_posts_per_category"; then
        echo ""
        echo -e "${GREEN}✅ Trend collection completed successfully!${NC}"
        echo ""
        echo -e "${BLUE}📊 View results at:${NC} http://localhost:11800"
        echo -e "${BLUE}🔧 Admin panel:${NC}    http://localhost:11800/admin"
        return 0
    else
        echo ""
        echo -e "${RED}❌ Trend collection failed${NC}"
        echo "Check the error messages above or view logs with:"
        echo "  ${DOCKER_COMPOSE} logs -f"
        return 1
    fi
}

# Function to manage categories (submenu)
manage_categories_submenu() {
    echo ""
    echo -e "${BLUE}=================================================="
    echo "  Manage Categories"
    echo "==================================================${NC}"

    while true; do
        echo ""
        echo -e "${BLUE}Current Categories:${NC}"
        # Use Python to show live category list
        ${DOCKER_COMPOSE} exec web python -c "
from categories import list_categories
categories = list_categories()
for i, cat in enumerate(categories, 1):
    print(f'  {i}. {cat}')
print(f'\nTotal: {len(categories)} categories')
" 2>/dev/null

        echo ""
        echo -e "${GREEN}1)${NC} Add category"
        echo -e "${GREEN}2)${NC} Remove category"
        echo -e "${GREEN}3)${NC} Reset to defaults"
        echo -e "${RED}0)${NC} Done managing categories"
        echo ""
        echo -n "Select an option: "
        read cat_choice

        case $cat_choice in
            1)
                echo ""
                echo -n "Enter new category name: "
                read new_category
                if [ -n "$new_category" ]; then
                    echo ""
                    echo -e "${BLUE}Adding category: $new_category${NC}"
                    ${DOCKER_COMPOSE} exec web python -c "
from categories import add_category
success, message = add_category('$new_category')
print(message)
exit(0 if success else 1)
"
                    if [ $? -eq 0 ]; then
                        echo -e "${GREEN}✅ Category added successfully${NC}"
                    else
                        echo -e "${RED}❌ Failed to add category${NC}"
                    fi
                else
                    echo -e "${RED}❌ Category name cannot be empty${NC}"
                fi
                ;;
            2)
                echo ""
                echo -n "Enter category name to remove: "
                read remove_category
                if [ -n "$remove_category" ]; then
                    echo ""
                    echo -e "${YELLOW}⚠️  Are you sure you want to remove '$remove_category'?${NC}"
                    echo -n "Type 'yes' to confirm: "
                    read confirm
                    if [ "$confirm" = "yes" ]; then
                        echo -e "${BLUE}Removing category: $remove_category${NC}"
                        ${DOCKER_COMPOSE} exec web python -c "
from categories import remove_category
success, message = remove_category('$remove_category')
print(message)
exit(0 if success else 1)
"
                        if [ $? -eq 0 ]; then
                            echo -e "${GREEN}✅ Category removed successfully${NC}"
                        else
                            echo -e "${RED}❌ Failed to remove category${NC}"
                        fi
                    else
                        echo -e "${BLUE}ℹ️  Removal cancelled${NC}"
                    fi
                else
                    echo -e "${RED}❌ Category name cannot be empty${NC}"
                fi
                ;;
            3)
                echo ""
                echo -e "${YELLOW}⚠️  This will reset categories to defaults:${NC}"
                echo "  Technology, Politics, Entertainment, Sports, Science, Business, World News"
                echo ""
                echo -n "Type 'yes' to confirm: "
                read confirm
                if [ "$confirm" = "yes" ]; then
                    echo -e "${BLUE}Resetting categories...${NC}"
                    ${DOCKER_COMPOSE} exec web python -c "
from categories import reset_to_defaults
if reset_to_defaults():
    print('✅ Categories reset to defaults')
    exit(0)
else:
    print('❌ Failed to reset categories')
    exit(1)
"
                    if [ $? -eq 0 ]; then
                        echo -e "${GREEN}✅ Reset completed successfully${NC}"
                    else
                        echo -e "${RED}❌ Failed to reset categories${NC}"
                    fi
                else
                    echo -e "${BLUE}ℹ️  Reset cancelled${NC}"
                fi
                ;;
            0)
                return 0
                ;;
            *)
                echo -e "${RED}❌ Invalid option${NC}"
                sleep 1
                ;;
        esac
    done
}

# Function for database operations
database_operations() {
    echo ""
    echo -e "${BLUE}=================================================="
    echo "  Database Operations"
    echo "==================================================${NC}"
    echo ""
    echo -e "${GREEN}1)${NC} Run Migrations"
    echo -e "${GREEN}2)${NC} Create Backup"
    echo -e "${GREEN}3)${NC} Shell Access (psql)"
    echo -e "${RED}0)${NC} Back to Main Menu"
    echo ""
    echo -n "Select an option: "
    read db_choice

    case $db_choice in
        1)
            run_migrations
            ;;
        2)
            echo ""
            echo -e "${BLUE}📦 Creating database backup...${NC}"
            BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
            ${DOCKER_COMPOSE} exec postgres pg_dump -U trend_user trends > "$BACKUP_FILE"
            echo -e "${GREEN}✅ Backup created: $BACKUP_FILE${NC}"
            ;;
        3)
            echo ""
            echo -e "${CYAN}Opening PostgreSQL shell (type \\q to exit)...${NC}"
            echo ""
            ${DOCKER_COMPOSE} exec postgres psql -U trend_user -d trends
            ;;
        0)
            return 0
            ;;
        *)
            echo -e "${RED}❌ Invalid option${NC}"
            ;;
    esac

    echo ""
    read -p "Press Enter to continue..."
}

# Function to run database migrations
run_migrations() {
    echo ""
    echo -e "${BLUE}=================================================="
    echo "  Run Database Migrations"
    echo "==================================================${NC}"
    echo ""

    # Check if container is running
    if ! ${DOCKER_COMPOSE} ps | grep -q "Up"; then
        echo -e "${RED}❌ Container is not running${NC}"
        echo "Please start the container first (Option 1 or 2)"
        return 1
    fi

    echo -e "${GREEN}✅ Container is running${NC}"
    echo ""
    echo -e "${BLUE}📊 Running database migrations...${NC}"
    echo ""

    # Run migrations
    if ${DOCKER_COMPOSE} exec web python manage.py migrate; then
        echo ""
        echo -e "${GREEN}✅ Migrations completed successfully!${NC}"
        return 0
    else
        echo ""
        echo -e "${RED}❌ Migration failed${NC}"
        echo "Check the error messages above or view logs with:"
        echo "  ${DOCKER_COMPOSE} logs -f"
        return 1
    fi
}

# Function to clean old data
clean_old_data() {
    echo ""
    echo -e "${BLUE}=================================================="
    echo "  Clean Old Data"
    echo "==================================================${NC}"
    echo ""

    # Check if container is running
    if ! ${DOCKER_COMPOSE} ps | grep -q "Up"; then
        echo -e "${RED}❌ Container is not running${NC}"
        echo "Please start the container first (Option 1 or 2)"
        return 1
    fi

    echo -e "${GREEN}✅ Container is running${NC}"
    echo ""
    echo -e "${BLUE}Data Retention Policy${NC}"
    echo "This will delete old collection runs to free up disk space."
    echo ""
    echo -e "${YELLOW}How many days of data to keep?${NC}"
    echo "  • Enter 0 to DELETE ALL DATA"
    echo "  • Enter 1 to keep only the last 24 hours"
    echo "  • Enter N to keep only the last N days"
    echo -n "Days to keep (default: 30): "
    read retention_days

    # Use default if empty
    if [ -z "$retention_days" ]; then
        retention_days=30
    fi

    # Validate it's a number
    if ! [[ "$retention_days" =~ ^[0-9]+$ ]]; then
        echo -e "${RED}❌ Invalid number. Using default: 30${NC}"
        retention_days=30
    fi

    echo ""
    echo -e "${BLUE}🔍 Running dry-run to preview...${NC}"
    echo ""

    # First run in dry-run mode to show what would be deleted
    ${DOCKER_COMPOSE} exec web python manage.py clean_old_data --days "$retention_days" --dry-run

    echo ""
    echo -e "${YELLOW}⚠️  Proceed with deletion?${NC}"
    echo -n "Type 'yes' to confirm: "
    read confirmation

    if [ "$confirmation" != "yes" ]; then
        echo -e "${BLUE}ℹ️  Cleanup cancelled${NC}"
        return 0
    fi

    echo ""
    echo -e "${BLUE}🗑️  Deleting old data...${NC}"
    echo ""

    # Run actual cleanup
    if ${DOCKER_COMPOSE} exec web python manage.py clean_old_data --days "$retention_days"; then
        echo ""
        echo -e "${GREEN}✅ Cleanup completed successfully!${NC}"
        return 0
    else
        echo ""
        echo -e "${RED}❌ Cleanup failed${NC}"
        echo "Check the error messages above"
        return 1
    fi
}

# Main menu loop
while true; do
    show_menu
    read choice

    case $choice in
        1)
            if full_platform_setup; then
                echo ""
                read -p "Press Enter to return to menu..."
            else
                echo ""
                echo -e "${RED}❌ Full platform setup failed. Please check the errors above.${NC}"
                read -p "Press Enter to return to menu..."
            fi
            ;;
        2)
            if build_and_start; then
                echo ""
                read -p "Press Enter to return to menu..."
            else
                echo ""
                echo -e "${RED}❌ Basic setup failed. Please check the errors above.${NC}"
                read -p "Press Enter to return to menu..."
            fi
            ;;
        3)
            manage_services
            ;;
        4)
            if collect_trends; then
                echo ""
                read -p "Press Enter to return to menu..."
            else
                echo ""
                echo -e "${RED}❌ Trend collection failed. Please check the errors above.${NC}"
                read -p "Press Enter to return to menu..."
            fi
            ;;
        5)
            manage_categories_submenu
            echo ""
            read -p "Press Enter to return to menu..."
            ;;
        6)
            show_service_status
            ;;
        7)
            view_logs
            ;;
        8)
            database_operations
            ;;
        9)
            if clean_old_data; then
                echo ""
                read -p "Press Enter to return to menu..."
            else
                echo ""
                echo -e "${RED}❌ Cleanup failed. Please check the errors above.${NC}"
                read -p "Press Enter to return to menu..."
            fi
            ;;
        10)
            generate_api_keys
            ;;
        11)
            show_all_urls
            ;;
        0)
            echo ""
            echo -e "${GREEN}👋 Goodbye!${NC}"
            echo ""
            exit 0
            ;;
        *)
            echo ""
            echo -e "${RED}❌ Invalid option. Please select 1-11, or 0.${NC}"
            sleep 2
            ;;
    esac
done
