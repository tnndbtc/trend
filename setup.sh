#!/bin/bash

# AI Trend Intelligence Platform - Enhanced Setup Script
# Comprehensive menu-driven interface for development and deployment

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source helper scripts if they exist, otherwise define inline
if [ -f "${SCRIPT_DIR}/scripts/colors.sh" ]; then
    source "${SCRIPT_DIR}/scripts/colors.sh"
    source "${SCRIPT_DIR}/scripts/menu-helpers.sh"
else
    # Inline minimal color support
    COLOR_SUCCESS='\033[1;32m'
    COLOR_ERROR='\033[1;31m'
    COLOR_WARNING='\033[1;33m'
    COLOR_INFO='\033[1;34m'
    COLOR_HIGHLIGHT='\033[1;36m'
    COLOR_RESET='\033[0m'
    SYMBOL_SUCCESS="✅"
    SYMBOL_ERROR="❌"
    SYMBOL_WARNING="⚠️ "
    print_success() { echo -e "${COLOR_SUCCESS}${SYMBOL_SUCCESS} $1${COLOR_RESET}"; }
    print_error() { echo -e "${COLOR_ERROR}${SYMBOL_ERROR} $1${COLOR_RESET}"; }
    print_warning() { echo -e "${COLOR_WARNING}${SYMBOL_WARNING}$1${COLOR_RESET}"; }
    print_info() { echo -e "${COLOR_INFO}$1${COLOR_RESET}"; }
fi

# Determine Docker Compose command
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE="docker compose"
fi

#=============================================================================
# FOLDER STRUCTURE GUIDE - Shows what each folder does
#=============================================================================
show_folder_structure() {
    clear
    echo -e "${COLOR_HIGHLIGHT}"
    cat << 'EOF'
╔══════════════════════════════════════════════════════╗
║     📁 Repository Folder Structure Guide            ║
╚══════════════════════════════════════════════════════╝
EOF
    echo -e "${COLOR_RESET}"

    echo ""
    echo -e "${COLOR_INFO}=== MICROSERVICES (Independently Deployable) ===${COLOR_RESET}"
    echo ""

    echo -e "${COLOR_SUCCESS}📁 services/api/${COLOR_RESET}"
    echo "   Purpose: FastAPI REST API service"
    echo "   Port: 8000"
    echo "   Features: REST endpoints, GraphQL, WebSocket, API authentication"
    echo "   Quick Start: ./setup.sh dev-api"
    echo "   Documentation: services/api/README.md"
    echo ""

    echo -e "${COLOR_SUCCESS}📁 services/web-interface/${COLOR_RESET}"
    echo "   Purpose: Django web UI for browsing trends"
    echo "   Port: 11800"
    echo "   Features: Web dashboard, admin panel, user authentication"
    echo "   Quick Start: ./setup.sh dev-web"
    echo "   Documentation: services/web-interface/README.md"
    echo ""

    echo -e "${COLOR_SUCCESS}📁 services/crawler/${COLOR_RESET}"
    echo "   Purpose: Data collection from multiple sources"
    echo "   Features: Scheduled crawling, Reddit, HackerNews, News RSS"
    echo "   Quick Start: ./setup.sh dev-crawler"
    echo "   Documentation: services/crawler/README.md"
    echo ""

    echo -e "${COLOR_SUCCESS}📁 services/celery-worker/${COLOR_RESET}"
    echo "   Purpose: Background task processing"
    echo "   Features: Async tasks, scheduled jobs, queue management"
    echo "   Quick Start: (Configured in docker-compose.yml)"
    echo ""

    echo -e "${COLOR_SUCCESS}📁 services/translation-service/${COLOR_RESET}"
    echo "   Purpose: Multi-language translation pipeline"
    echo "   Features: Translation providers, caching, cross-language dedup"
    echo "   Status: ⚠️  In development"
    echo ""

    echo -e "${COLOR_INFO}=== SHARED LIBRARIES (Used by All Services) ===${COLOR_RESET}"
    echo ""

    echo -e "${COLOR_SUCCESS}📁 packages/trend-agent-core/${COLOR_RESET}"
    echo "   Purpose: Core shared library"
    echo "   Contains: Storage, LLM, Intelligence, Workflow, Agents, Observability"
    echo "   Install: pip install -e packages/trend-agent-core"
    echo "   Documentation: packages/trend-agent-core/README.md"
    echo ""

    echo -e "${COLOR_SUCCESS}📁 packages/trend-agent-collectors/${COLOR_RESET}"
    echo "   Purpose: Collector plugin library"
    echo "   Contains: Reddit, HackerNews, Google News, RSS collectors"
    echo "   Install: pip install -e packages/trend-agent-collectors"
    echo ""

    echo -e "${COLOR_INFO}=== INFRASTRUCTURE (Deployment & Config) ===${COLOR_RESET}"
    echo ""

    echo -e "${COLOR_SUCCESS}📁 infrastructure/docker/${COLOR_RESET}"
    echo "   Purpose: Docker Compose configurations"
    echo "   Contains: docker-compose.yml, environment configs"
    echo ""

    echo -e "${COLOR_SUCCESS}📁 infrastructure/k8s/${COLOR_RESET}"
    echo "   Purpose: Kubernetes deployment manifests"
    echo "   Contains: Deployments, services, ConfigMaps"
    echo "   Deploy: kubectl apply -k k8s/overlays/production"
    echo ""

    echo -e "${COLOR_SUCCESS}📁 observability/${COLOR_RESET}"
    echo "   Purpose: Monitoring stack configuration"
    echo "   Contains: Grafana dashboards, Prometheus configs, Loki, Jaeger"
    echo "   Access: Grafana at http://localhost:3000"
    echo ""

    echo -e "${COLOR_INFO}=== CONFIGURATION & DATA ===${COLOR_RESET}"
    echo ""

    echo -e "${COLOR_SUCCESS}📁 config/${COLOR_RESET}"
    echo "   Purpose: Application configuration files"
    echo "   Contains: settings.json, alert rules, Grafana dashboards"
    echo ""

    echo -e "${COLOR_SUCCESS}📁 data/${COLOR_RESET}"
    echo "   Purpose: Runtime data storage"
    echo "   Contains: Database files, cache, logs"
    echo "   Note: Git-ignored, created at runtime"
    echo ""

    echo -e "${COLOR_INFO}=== DEVELOPMENT TOOLS ===${COLOR_RESET}"
    echo ""

    echo -e "${COLOR_SUCCESS}📁 scripts/${COLOR_RESET}"
    echo "   Purpose: Utility scripts and helpers"
    echo "   Contains: colors.sh, menu-helpers.sh, deployment scripts"
    echo ""

    echo -e "${COLOR_SUCCESS}📁 docs/${COLOR_RESET}"
    echo "   Purpose: Documentation"
    echo "   Contains: Architecture docs, API docs, development guides"
    echo ""

    echo -e "${COLOR_SUCCESS}📁 tests/${COLOR_RESET}"
    echo "   Purpose: Integration and end-to-end tests"
    echo "   Run: pytest tests/"
    echo ""

    echo -e "${COLOR_INFO}=== KEY FILES ===${COLOR_RESET}"
    echo ""

    echo -e "${COLOR_SUCCESS}📄 Makefile${COLOR_RESET}"
    echo "   Purpose: Convenient development commands"
    echo "   Usage: make dev-api, make build, make test"
    echo ""

    echo -e "${COLOR_SUCCESS}📄 docker-compose.yml${COLOR_RESET}"
    echo "   Purpose: Multi-container orchestration"
    echo "   Usage: docker-compose up -d"
    echo ""

    echo -e "${COLOR_SUCCESS}📄 setup.sh${COLOR_RESET}"
    echo "   Purpose: This script! Interactive developer hub"
    echo "   Usage: ./setup.sh (interactive) or ./setup.sh dev-api (direct)"
    echo ""

    echo -e "${COLOR_HIGHLIGHT}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "💡 PARALLEL DEVELOPMENT WORKFLOW"
    echo ""
    echo "Open multiple terminals or Claude Code instances:"
    echo ""
    echo "Terminal 1 (Infrastructure): ./setup.sh dev-infra"
    echo "Terminal 2 (API Service):    cd services/api && edit code"
    echo "Terminal 3 (Web Interface):  cd services/web-interface && edit code"
    echo "Terminal 4 (Crawler):        cd services/crawler && edit code"
    echo ""
    echo "Each service can be developed, tested, and deployed independently!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${COLOR_RESET}"
    echo ""
    read -p "Press Enter to return to menu..."
}

#=============================================================================
# COMMAND-LINE MODE - Direct command execution
#=============================================================================
if [ $# -gt 0 ]; then
    case "$1" in
        # Development commands
        dev-api)
            print_info "Starting API service..."
            if command -v make &> /dev/null; then
                make dev-api
            else
                cd services/api && uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
            fi
            ;;
        dev-web)
            print_info "Starting web interface..."
            if command -v make &> /dev/null; then
                make dev-web
            else
                cd services/web-interface && python manage.py runserver 11800
            fi
            ;;
        dev-crawler)
            print_info "Starting crawler service..."
            if command -v make &> /dev/null; then
                make dev-crawler
            else
                cd services/crawler && python -m src.main
            fi
            ;;
        dev-infra)
            print_info "Starting infrastructure services..."
            if command -v make &> /dev/null; then
                make dev-infra
            else
                $DOCKER_COMPOSE up -d postgres redis qdrant
            fi
            ;;

        # Build commands
        build|build-all)
            if command -v make &> /dev/null; then
                make build
            else
                $DOCKER_COMPOSE build
            fi
            ;;

        # Docker commands
        up)
            $DOCKER_COMPOSE up -d
            ;;
        down)
            $DOCKER_COMPOSE down
            ;;
        logs)
            shift
            $DOCKER_COMPOSE logs -f "$@"
            ;;
        status)
            $DOCKER_COMPOSE ps
            ;;

        # Info commands
        folders|structure)
            show_folder_structure
            ;;

        help|--help|-h)
            echo "Quick Commands:"
            echo "  ./setup.sh dev-api       - Start API service"
            echo "  ./setup.sh dev-web       - Start web interface"
            echo "  ./setup.sh dev-crawler   - Start crawler"
            echo "  ./setup.sh dev-infra     - Start infrastructure"
            echo "  ./setup.sh build         - Build all Docker images"
            echo "  ./setup.sh up            - Start all services"
            echo "  ./setup.sh down          - Stop all services"
            echo "  ./setup.sh logs [service]- View logs"
            echo "  ./setup.sh status        - Show service status"
            echo "  ./setup.sh folders       - Show folder structure"
            echo ""
            echo "Or run './setup.sh' for interactive menu"
            ;;

        *)
            print_error "Unknown command: $1"
            echo "Run './setup.sh help' for available commands"
            exit 1
            ;;
    esac
    exit 0
fi

#=============================================================================
# PREREQUISITE CHECKS
#=============================================================================
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        echo "Visit: https://docs.docker.com/get-docker/"
        return 1
    fi
    print_success "Docker is installed"
    return 0
}

check_docker_compose() {
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed"
        echo "Visit: https://docs.docker.com/compose/install/"
        return 1
    fi
    print_success "Docker Compose is installed"
    return 0
}

# Run checks
echo -e "${COLOR_HIGHLIGHT}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║   AI Trend Intelligence Platform - Setup Script     ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${COLOR_RESET}"
echo ""

check_docker || exit 1
check_docker_compose || exit 1
echo ""

#=============================================================================
# MAIN MENU
#=============================================================================
show_main_menu() {
    clear
    echo -e "${COLOR_HIGHLIGHT}"
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║   AI Trend Intelligence Platform - Main Menu         ║"
    echo "╚══════════════════════════════════════════════════════╝"
    echo -e "${COLOR_RESET}"
    echo ""

    # Show current status if docker-compose is available
    if $DOCKER_COMPOSE ps > /dev/null 2>&1; then
        local running=$($DOCKER_COMPOSE ps --services --filter "status=running" 2>/dev/null | wc -l)
        echo -e "${COLOR_INFO}Status: ${running} services running${COLOR_RESET}"
        echo ""
    fi

    echo -e "${COLOR_INFO}🚀 Quick Start${COLOR_RESET}"
    echo -e "  ${COLOR_HIGHLIGHT}1)${COLOR_RESET} Full Platform Setup (All Services)"
    echo -e "  ${COLOR_HIGHLIGHT}2)${COLOR_RESET} Basic Setup (Web Interface Only)"
    echo -e "  ${COLOR_HIGHLIGHT}3)${COLOR_RESET} Start/Stop Services"
    echo ""

    echo -e "${COLOR_INFO}📊 Data & Operations${COLOR_RESET}"
    echo -e "  ${COLOR_HIGHLIGHT}4)${COLOR_RESET} Collect Trends"
    echo -e "  ${COLOR_HIGHLIGHT}5)${COLOR_RESET} Manage Categories"
    echo ""

    echo -e "${COLOR_INFO}🔧 System Management${COLOR_RESET}"
    echo -e "  ${COLOR_HIGHLIGHT}6)${COLOR_RESET} Service Status & Health Check"
    echo -e "  ${COLOR_HIGHLIGHT}7)${COLOR_RESET} View Logs"
    echo -e "  ${COLOR_HIGHLIGHT}8)${COLOR_RESET} Database Operations"
    echo -e "  ${COLOR_HIGHLIGHT}9)${COLOR_RESET} Clean Old Data"
    echo ""

    echo -e "${COLOR_INFO}🔐 Configuration${COLOR_RESET}"
    echo -e "  ${COLOR_HIGHLIGHT}10)${COLOR_RESET} Generate API Keys"
    echo -e "  ${COLOR_HIGHLIGHT}11)${COLOR_RESET} Show All Access URLs"
    echo ""

    echo -e "${COLOR_INFO}📚 Documentation & Help${COLOR_RESET}"
    echo -e "  ${COLOR_HIGHLIGHT}12)${COLOR_RESET} 📁 Show Folder Structure (What Each Folder Does)"
    echo -e "  ${COLOR_HIGHLIGHT}13)${COLOR_RESET} CLI Quick Reference"
    echo ""

    echo -e "${COLOR_ERROR}0)${COLOR_RESET} Exit"
    echo ""
    echo -n "Select an option: "
}

#=============================================================================
# EXISTING FUNCTIONS FROM ORIGINAL SETUP.SH
#=============================================================================

# Function to check and create environment
check_environment() {
    if [ ! -f .env.docker ]; then
        if [ -f .env.docker.example ]; then
            print_info "Creating .env.docker from template..."
            cp .env.docker.example .env.docker
            print_success "Created .env.docker"
            echo ""
        else
            print_error "Template file .env.docker.example not found"
            return 1
        fi
    fi

    if [ -z "$OPENAI_API_KEY" ]; then
        print_error "OPENAI_API_KEY environment variable not set"
        echo ""
        print_warning "Set your OpenAI API key:"
        echo "  export OPENAI_API_KEY='sk-proj-xxxxxxxxxxxxx'"
        echo "  ./setup.sh"
        echo ""
        echo "Get key from: https://platform.openai.com/api-keys"
        return 1
    fi

    print_success "Using OPENAI_API_KEY from environment variable"
    return 0
}

# Full platform setup
full_platform_setup() {
    echo ""
    echo -e "${COLOR_HIGHLIGHT}Full Platform Setup${COLOR_RESET}"
    echo ""

    if ! check_environment; then
        return 1
    fi

    print_info "Creating data directories..."
    mkdir -p data/db data/cache
    print_success "Data directories created"

    print_info "Stopping existing containers..."
    $DOCKER_COMPOSE down 2>/dev/null || true
    print_success "Cleanup complete"

    print_info "Building Docker images..."
    if ! $DOCKER_COMPOSE build; then
        print_error "Docker build failed"
        return 1
    fi
    print_success "Docker images built"

    print_info "Starting all services..."
    if ! $DOCKER_COMPOSE --profile api --profile celery --profile observability up -d; then
        print_error "Failed to start services"
        return 1
    fi

    print_info "Waiting for services to start..."
    sleep 10

    print_success "Full Platform Setup Complete!"
    echo ""
    show_all_urls
}

# Basic setup (web only)
build_and_start() {
    echo ""
    echo -e "${COLOR_HIGHLIGHT}Basic Setup (Web Interface Only)${COLOR_RESET}"
    echo ""

    if ! check_environment; then
        return 1
    fi

    print_info "Creating data directories..."
    mkdir -p data/db data/cache

    print_info "Stopping existing containers..."
    docker stop trend-intelligence-agent 2>/dev/null || true
    docker rm -f trend-intelligence-agent 2>/dev/null || true
    $DOCKER_COMPOSE down 2>/dev/null || true

    print_info "Building Docker image..."
    if ! $DOCKER_COMPOSE build; then
        print_error "Docker build failed"
        return 1
    fi
    print_success "Docker image built"

    print_info "Starting containers..."
    if ! $DOCKER_COMPOSE up -d; then
        print_error "Failed to start containers"
        return 1
    fi

    print_info "Waiting for service to start..."
    sleep 5

    if $DOCKER_COMPOSE ps | grep -q "Up"; then
        print_success "Basic Setup Complete!"
        echo ""
        echo "Web Interface: http://localhost:11800"
        echo "Admin Panel: http://localhost:11800/admin"
        echo ""
        print_warning "Default credentials: admin / changeme123"
    else
        print_error "Container failed to start"
        return 1
    fi
}

# Manage services
manage_services() {
    echo ""
    echo -e "${COLOR_HIGHLIGHT}Manage Services${COLOR_RESET}"
    echo ""
    echo "1) Start FastAPI (REST API)"
    echo "2) Stop FastAPI"
    echo "3) Start Celery (Background Tasks)"
    echo "4) Stop Celery"
    echo "5) Start Monitoring (Grafana + Prometheus)"
    echo "6) Stop Monitoring"
    echo "7) Start ALL Optional Services"
    echo "8) Stop ALL Services"
    echo "0) Back to Main Menu"
    echo ""
    echo -n "Select an option: "
    read service_choice

    case $service_choice in
        1)
            print_info "Starting FastAPI..."
            $DOCKER_COMPOSE --profile api up -d api
            print_success "FastAPI started - http://localhost:8000/docs"
            ;;
        2)
            $DOCKER_COMPOSE stop api
            print_success "FastAPI stopped"
            ;;
        3)
            print_info "Starting Celery workers..."
            $DOCKER_COMPOSE --profile celery up -d celery-worker celery-beat
            print_success "Celery started"
            ;;
        4)
            $DOCKER_COMPOSE stop celery-worker celery-beat
            print_success "Celery stopped"
            ;;
        5)
            print_info "Starting Monitoring stack..."
            $DOCKER_COMPOSE --profile observability up -d
            print_success "Monitoring started"
            echo "Grafana: http://localhost:3000 (admin/admin)"
            ;;
        6)
            $DOCKER_COMPOSE stop prometheus grafana postgres-exporter redis-exporter node-exporter
            print_success "Monitoring stopped"
            ;;
        7)
            $DOCKER_COMPOSE --profile api --profile celery --profile observability up -d
            print_success "All services started"
            show_all_urls
            ;;
        8)
            if [ -n "$ZSH_VERSION" ] || [ -n "$BASH_VERSION" ]; then
                read -p "Type 'yes' to stop all services: " confirm
            else
                echo -n "Type 'yes' to stop all services: "
                read confirm
            fi
            if [ "$confirm" = "yes" ]; then
                $DOCKER_COMPOSE down
                print_success "All services stopped"
            else
                print_info "Cancelled"
            fi
            ;;
        0)
            return 0
            ;;
    esac

    echo ""
    read -p "Press Enter to continue..."
}

# Show service status
show_service_status() {
    echo ""
    echo -e "${COLOR_HIGHLIGHT}Service Status & Health Check${COLOR_RESET}"
    echo ""
    echo "Running Services:"
    $DOCKER_COMPOSE ps
    echo ""
    echo "Health Checks:"

    if curl -sf http://localhost:11800 > /dev/null 2>&1; then
        print_success "Django Web - http://localhost:11800"
    else
        print_error "Django Web - not responding"
    fi

    if curl -sf http://localhost:8000 > /dev/null 2>&1; then
        print_success "FastAPI - http://localhost:8000"
    else
        print_warning "FastAPI - not started"
    fi

    if curl -sf http://localhost:3000 > /dev/null 2>&1; then
        print_success "Grafana - http://localhost:3000"
    else
        print_warning "Grafana - not started"
    fi

    echo ""
    read -p "Press Enter to continue..."
}

# View logs
view_logs() {
    echo ""
    echo -e "${COLOR_HIGHLIGHT}View Service Logs${COLOR_RESET}"
    echo ""
    echo "1) Django Web"
    echo "2) FastAPI"
    echo "3) Celery Worker"
    echo "4) PostgreSQL"
    echo "5) Redis"
    echo "6) All Services"
    echo "0) Back"
    echo ""
    echo -n "Select service: "
    read log_choice

    echo ""
    print_info "Viewing logs (Ctrl+C to exit)..."
    echo ""

    case $log_choice in
        1) $DOCKER_COMPOSE logs -f web ;;
        2) $DOCKER_COMPOSE logs -f api ;;
        3) $DOCKER_COMPOSE logs -f celery-worker ;;
        4) $DOCKER_COMPOSE logs -f postgres ;;
        5) $DOCKER_COMPOSE logs -f redis ;;
        6) $DOCKER_COMPOSE logs -f ;;
        0) return 0 ;;
    esac
}

# Show all URLs
show_all_urls() {
    echo ""
    echo -e "${COLOR_HIGHLIGHT}Access URLs & Credentials${COLOR_RESET}"
    echo ""
    echo "Web Interfaces:"
    echo "  Django Web:    http://localhost:11800"
    echo "  Django Admin:  http://localhost:11800/admin"
    echo "  FastAPI Docs:  http://localhost:8000/docs"
    echo "  Grafana:       http://localhost:3000"
    echo "  Prometheus:    http://localhost:9090"
    echo ""
    echo "Databases:"
    echo "  PostgreSQL:    localhost:5433"
    echo "  Qdrant:        localhost:6333"
    echo "  Redis:         localhost:6380"
    echo ""
    echo "Default Credentials:"
    echo "  Django Admin:  admin / changeme123"
    echo "  Grafana:       admin / admin"
    echo "  PostgreSQL:    trend_user / trend_password"
    echo ""
    print_warning "Change default credentials for production!"
    echo ""
    read -p "Press Enter to continue..."
}

# Generate API keys
generate_api_keys() {
    echo ""
    echo -e "${COLOR_HIGHLIGHT}Generate API Keys${COLOR_RESET}"
    echo ""

    if ! command -v openssl &> /dev/null; then
        print_error "openssl not found"
        return 1
    fi

    API_KEY=$(openssl rand -hex 32)
    ADMIN_KEY=$(openssl rand -hex 32)

    print_success "Keys generated!"
    echo ""
    echo "Add these to your .env.docker file:"
    echo ""
    echo "API_KEYS=$API_KEY"
    echo "ADMIN_API_KEYS=$ADMIN_KEY"
    echo ""
    read -p "Press Enter to continue..."
}

# Database operations
database_operations() {
    echo ""
    echo -e "${COLOR_HIGHLIGHT}Database Operations${COLOR_RESET}"
    echo ""
    echo "1) Run Migrations"
    echo "2) Create Backup"
    echo "3) Shell Access (psql)"
    echo "0) Back"
    echo ""
    echo -n "Select: "
    read db_choice

    case $db_choice in
        1)
            print_info "Running migrations..."
            $DOCKER_COMPOSE exec web python manage.py migrate
            ;;
        2)
            BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
            print_info "Creating backup..."
            $DOCKER_COMPOSE exec postgres pg_dump -U trend_user trends > "$BACKUP_FILE"
            print_success "Backup created: $BACKUP_FILE"
            ;;
        3)
            print_info "Opening PostgreSQL shell..."
            $DOCKER_COMPOSE exec postgres psql -U trend_user -d trends
            ;;
    esac

    echo ""
    read -p "Press Enter to continue..."
}

# Collect trends
collect_trends() {
    echo ""
    echo -e "${COLOR_HIGHLIGHT}Collect Trends${COLOR_RESET}"
    echo ""

    if ! $DOCKER_COMPOSE ps | grep -q "Up"; then
        print_error "Container is not running"
        echo "Please start the container first"
        return 1
    fi

    print_success "Container is running"
    echo ""
    echo -n "Max posts per category (default 5): "
    read max_posts_per_category

    if [ -z "$max_posts_per_category" ]; then
        max_posts_per_category=5
    fi

    print_info "Starting trend collection..."
    if $DOCKER_COMPOSE exec web python manage.py collect_trends --max-posts-per-category "$max_posts_per_category"; then
        print_success "Trend collection completed!"
        echo "View at: http://localhost:11800"
    else
        print_error "Trend collection failed"
    fi

    echo ""
    read -p "Press Enter to continue..."
}

# Manage categories
manage_categories() {
    echo ""
    echo -e "${COLOR_HIGHLIGHT}Manage Categories${COLOR_RESET}"
    echo ""
    echo "Feature available in web interface"
    echo "Visit: http://localhost:11800/admin"
    echo ""
    read -p "Press Enter to continue..."
}

# Clean old data
clean_old_data() {
    echo ""
    echo -e "${COLOR_HIGHLIGHT}Clean Old Data${COLOR_RESET}"
    echo ""
    echo "Feature available in web interface"
    echo "Or run: docker-compose exec web python manage.py clean_old_data --days 30"
    echo ""
    read -p "Press Enter to continue..."
}

# CLI Quick Reference
show_cli_reference() {
    echo ""
    echo -e "${COLOR_HIGHLIGHT}CLI Quick Reference${COLOR_RESET}"
    echo ""
    echo "You can run commands directly without menus:"
    echo ""
    echo "Development:"
    echo "  ./setup.sh dev-api      - Start API service"
    echo "  ./setup.sh dev-web      - Start web interface"
    echo "  ./setup.sh dev-crawler  - Start crawler"
    echo "  ./setup.sh dev-infra    - Start infrastructure"
    echo ""
    echo "Docker:"
    echo "  ./setup.sh build        - Build all images"
    echo "  ./setup.sh up           - Start all services"
    echo "  ./setup.sh down         - Stop all services"
    echo "  ./setup.sh logs api     - View API logs"
    echo "  ./setup.sh status       - Show service status"
    echo ""
    echo "Information:"
    echo "  ./setup.sh folders      - Show folder structure"
    echo "  ./setup.sh help         - This help"
    echo ""
    read -p "Press Enter to continue..."
}

#=============================================================================
# MAIN LOOP
#=============================================================================
while true; do
    show_main_menu
    read choice

    case $choice in
        1)
            full_platform_setup
            read -p "Press Enter to continue..."
            ;;
        2)
            build_and_start
            read -p "Press Enter to continue..."
            ;;
        3)
            manage_services
            ;;
        4)
            collect_trends
            ;;
        5)
            manage_categories
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
            clean_old_data
            ;;
        10)
            generate_api_keys
            ;;
        11)
            show_all_urls
            ;;
        12)
            show_folder_structure
            ;;
        13)
            show_cli_reference
            ;;
        0)
            clear
            print_success "Goodbye!"
            exit 0
            ;;
        *)
            print_error "Invalid option"
            sleep 1
            ;;
    esac
done
