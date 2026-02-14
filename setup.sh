#!/bin/bash

# AI Trend Intelligence Platform - Master Setup Script
# Comprehensive menu-driven interface for development and deployment
#
# ⚠️  IMPORTANT: This is the MASTER setup script for the entire project.
#
# SETUP SCRIPT CONVENTIONS:
# ========================
# • DO NOT create new setup_*.sh files (e.g., setup_translation.sh, setup_chinese.sh)
# • ALL installation, configuration, and setup logic MUST be added to THIS file
# • Use functions for modularity (e.g., setup_translation_service(), setup_platform_generation())
# • Update the main menu to expose new setup functions to users
# • Update command-line mode section (lines ~200-285) for direct CLI access
#
# WHY THIS MATTERS:
# • Single source of truth for all setup operations
# • Easier maintenance and debugging
# • Consistent user experience
# • Prevents script fragmentation and confusion
#
# HOW TO ADD NEW SETUP LOGIC:
# 1. Create a new function in this file (e.g., setup_new_feature())
# 2. Add menu option in show_main_menu() function
# 3. Add case handler in main loop (bottom of file)
# 4. Add CLI command in command-line mode section (if needed)
# 5. Test with: ./setup.sh (menu) or ./setup.sh new-command (CLI)
#
# Example:
#   setup_translation_service() {
#       echo "Installing translation dependencies..."
#       pip install jinja2 deep-translator
#       echo "Configuring translation providers..."
#       # ... more setup logic
#   }

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
#
# ⚠️  CRITICAL: KEEP THIS UP TO DATE!
#
# When you add, remove, or rename folders in this repository:
#
# 1. ✅ ADD/UPDATE folder description in the appropriate section below
# 2. ✅ Include: Purpose, Port (if service), Features, Quick Start, Documentation
# 3. ✅ TEST with: ./setup.sh folders
# 4. ✅ If adding service: Update command-line mode section (lines ~200-285)
# 5. ✅ If adding service: Update Makefile with new target
#
# Sections in this function:
#   - MICROSERVICES: services/* folders (independently deployable)
#   - SHARED LIBRARIES: packages/* folders (shared code)
#   - INFRASTRUCTURE: infrastructure/*, observability/
#   - CONFIGURATION & DATA: config/, data/
#   - DEVELOPMENT TOOLS: scripts/, docs/, tests/
#   - KEY FILES: Makefile, docker-compose.yml, setup.sh
#
# Format to follow:
#   echo -e "${COLOR_SUCCESS}📁 path/to/folder/${COLOR_RESET}"
#   echo "   Purpose: What this folder does"
#   echo "   Port: XXXX (if applicable)"
#   echo "   Features: Key features list"
#   echo "   Quick Start: ./setup.sh command"
#   echo "   Documentation: path/to/README.md"
#   echo ""
#
# See .claude/instructions.md for detailed instructions
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
    echo -e "${COLOR_INFO}=== CORE SERVICES (Application Components) ===${COLOR_RESET}"
    echo ""

    echo -e "${COLOR_SUCCESS}📁 api/${COLOR_RESET}"
    echo "   Purpose: FastAPI REST API service"
    echo "   Port: 8000"
    echo "   Features: REST endpoints, GraphQL, WebSocket, API authentication"
    echo "   Quick Start: ./setup.sh dev-api"
    echo "   Documentation: api/README.md"
    echo ""

    echo -e "${COLOR_SUCCESS}📁 web_interface/${COLOR_RESET}"
    echo "   Purpose: Django web UI for browsing trends"
    echo "   Port: 11800"
    echo "   Features: Web dashboard, admin panel, user authentication, user preferences"
    echo "   User Prefs: Session-based + persistent profile filtering (no re-crawling)"
    echo "   Quick Start: ./setup.sh dev-web"
    echo "   Documentation: web_interface/README.md"
    echo "   Preference Docs: docs/USER_PREFERENCES_COMPLETE.md"
    echo ""

    echo -e "${COLOR_SUCCESS}📁 trend_agent/${COLOR_RESET}"
    echo "   Purpose: Core trend intelligence library"
    echo "   Contains: Storage, LLM, Intelligence, Workflow, Collectors, Observability"
    echo "   Features: Reddit, HackerNews, Google News collectors, data processing"
    echo "   Documentation: trend_agent/README.md"
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
    echo "💡 DEVELOPMENT WORKFLOW"
    echo ""
    echo "Open multiple terminals or Claude Code instances:"
    echo ""
    echo "Terminal 1 (Infrastructure): ./setup.sh dev-infra"
    echo "Terminal 2 (API Service):    cd api && edit code"
    echo "Terminal 3 (Web Interface):  cd web_interface && edit code"
    echo "Terminal 4 (Core Library):   cd trend_agent && edit code"
    echo ""
    echo "All components work together in a unified monolithic architecture!"
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
                cd api && uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
            fi
            ;;
        dev-web)
            print_info "Starting web interface..."
            if command -v make &> /dev/null; then
                make dev-web
            else
                cd web_interface && python manage.py runserver 11800
            fi
            ;;
        dev-crawler)
            print_info "Crawler integrated into web_interface..."
            if command -v make &> /dev/null; then
                make dev-crawler
            else
                cd web_interface && python manage.py collect_trends
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

        # User preference commands
        setup-prefs|setup-preferences)
            setup_user_preferences
            ;;
        test-prefs|test-preferences)
            test_user_preferences
            ;;

        help|--help|-h)
            echo "Quick Commands:"
            echo "  ./setup.sh dev-api         - Start API service"
            echo "  ./setup.sh dev-web         - Start web interface"
            echo "  ./setup.sh dev-crawler     - Start crawler"
            echo "  ./setup.sh dev-infra       - Start infrastructure"
            echo "  ./setup.sh build           - Build all Docker images"
            echo "  ./setup.sh up              - Start all services"
            echo "  ./setup.sh down            - Stop all services"
            echo "  ./setup.sh logs [service]  - View logs"
            echo "  ./setup.sh status          - Show service status"
            echo "  ./setup.sh folders         - Show folder structure"
            echo "  ./setup.sh setup-prefs     - Setup user preferences"
            echo "  ./setup.sh test-prefs      - Test user preferences"
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

    echo -e "${COLOR_INFO}👤 User Preferences${COLOR_RESET}"
    echo -e "  ${COLOR_HIGHLIGHT}14)${COLOR_RESET} Setup User Preferences (Phase 1 + Phase 2)"
    echo -e "  ${COLOR_HIGHLIGHT}15)${COLOR_RESET} Test User Preferences"
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
    echo "9) Restart ALL Services (no rebuild)"
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
        9)
            print_info "Restarting all services (no rebuild)..."
            $DOCKER_COMPOSE restart
            print_success "All services restarted"
            echo ""
            print_info "Waiting for services to be healthy..."
            sleep 5
            show_all_urls
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

    # Detect local IP address
    LOCAL_IP=""

    # Method 1: hostname -I (works on most Linux systems)
    if command -v hostname &> /dev/null; then
        LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    fi

    # Method 2: ip route (fallback)
    if [ -z "$LOCAL_IP" ] && command -v ip &> /dev/null; then
        LOCAL_IP=$(ip route get 1 2>/dev/null | awk '{print $7; exit}')
    fi

    # Method 3: ifconfig (older systems)
    if [ -z "$LOCAL_IP" ] && command -v ifconfig &> /dev/null; then
        LOCAL_IP=$(ifconfig 2>/dev/null | grep 'inet ' | grep -v '127.0.0.1' | awk '{print $2}' | head -1)
    fi

    # Format IP display
    if [ -n "$LOCAL_IP" ]; then
        IP_DISPLAY="${COLOR_MUTED} or ${COLOR_RESET}${LOCAL_IP}"
    else
        IP_DISPLAY="${COLOR_MUTED} (local IP not detected)${COLOR_RESET}"
    fi

    echo "Web Interfaces:"
    echo -e "  Django Web:    http://localhost:11800${IP_DISPLAY}:11800"
    echo -e "  Django Admin:  http://localhost:11800/admin${IP_DISPLAY}:11800/admin"
    echo -e "  FastAPI Docs:  http://localhost:8000/docs${IP_DISPLAY}:8000/docs"
    echo -e "  Grafana:       http://localhost:3000${IP_DISPLAY}:3000"
    echo -e "  Prometheus:    http://localhost:9090${IP_DISPLAY}:9090"
    echo ""
    echo "User Preferences (Phase 1 + Phase 2):"
    echo -e "  🔍 My Feed (Filtered Topics): http://localhost:11800/filtered/topics/${IP_DISPLAY}:11800/filtered/topics/"
    echo -e "  📈 My Feed (Filtered Trends): http://localhost:11800/filtered/trends/${IP_DISPLAY}:11800/filtered/trends/"
    echo -e "  👤 User Profile:              http://localhost:11800/profile/${IP_DISPLAY}:11800/profile/"
    echo -e "  🆕 Sign Up:                   http://localhost:11800/register/${IP_DISPLAY}:11800/register/"
    echo -e "  🔑 Login:                     http://localhost:11800/login/${IP_DISPLAY}:11800/login/"
    echo ""
    echo "Databases:"
    if [ -n "$LOCAL_IP" ]; then
        echo -e "  PostgreSQL:    localhost:5433 ${COLOR_MUTED}or${COLOR_RESET} ${LOCAL_IP}:5433"
        echo -e "  Qdrant:        localhost:6333 ${COLOR_MUTED}or${COLOR_RESET} ${LOCAL_IP}:6333"
        echo -e "  Redis:         localhost:6380 ${COLOR_MUTED}or${COLOR_RESET} ${LOCAL_IP}:6380"
    else
        echo "  PostgreSQL:    localhost:5433"
        echo "  Qdrant:        localhost:6333"
        echo "  Redis:         localhost:6380"
    fi
    echo ""
    echo "Default Credentials:"
    echo "  Django Admin:  admin / changeme123"
    echo "  Grafana:       admin / admin"
    echo "  PostgreSQL:    trend_user / trend_password"
    echo ""
    print_warning "Change default credentials for production!"
    if [ -n "$LOCAL_IP" ]; then
        echo ""
        print_info "💡 Use local IP (${LOCAL_IP}) to access from other devices on your network"
    fi
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

    # Check if web container is running
    if ! $DOCKER_COMPOSE ps | grep -q "web.*Up"; then
        print_error "Web container is not running"
        echo "Please start the services first"
        read -p "Press Enter to continue..."
        return
    fi

    # Get current retention setting from SystemSettings
    echo -e "${COLOR_INFO}Current Retention Policy:${COLOR_RESET}"
    CURRENT_RETENTION=$($DOCKER_COMPOSE exec -T web python manage.py shell <<EOF 2>/dev/null
from web_interface.trends_viewer.models_system import SystemSettings
try:
    settings = SystemSettings.load()
    print(f"{settings.data_retention_days}")
except:
    print("7")
EOF
)
    # Extract only numeric data (filter out Django's import message)
    # Look for lines that contain only digits, or default to 7
    CURRENT_RETENTION=$(echo "$CURRENT_RETENTION" | grep -E '^[0-9]+$' | tail -1 | tr -d '[:space:]')
    if [ -z "$CURRENT_RETENTION" ]; then
        CURRENT_RETENTION=7  # Default if query failed
    fi
    echo "  Configured retention: ${CURRENT_RETENTION} days"
    echo ""

    # Get database statistics
    echo -e "${COLOR_INFO}Current Database Status:${COLOR_RESET}"
    DB_STATS=$($DOCKER_COMPOSE exec -T web python manage.py shell <<EOF 2>/dev/null
from web_interface.trends_viewer.models import CollectionRun, CollectedTopic, TrendCluster
import os
runs = CollectionRun.objects.count()
topics = CollectedTopic.objects.count()
clusters = TrendCluster.objects.count()
db_path = '/app/web_interface/db/db.sqlite3'
if os.path.exists(db_path):
    size_mb = os.path.getsize(db_path) / (1024 * 1024)
    print(f"{runs}|{topics}|{clusters}|{size_mb:.1f}")
else:
    print("0|0|0|0.0")
EOF
)
    # Extract only data with pipe separators (filter out Django's import message)
    # Look for lines matching the pattern: number|number|number|number.number
    DB_STATS=$(echo "$DB_STATS" | grep -E '^[0-9]+\|[0-9]+\|[0-9]+\|[0-9.]+$' | tail -1 | tr -d '[:space:]')
    if [ -z "$DB_STATS" ]; then
        DB_STATS="0|0|0|0.0"  # Default if query failed
    fi
    IFS='|' read -r RUNS TOPICS CLUSTERS SIZE_MB <<< "$DB_STATS"
    echo "  📊 Collection Runs: ${RUNS}"
    echo "  📰 Topics: ${TOPICS}"
    echo "  🔗 Clusters: ${CLUSTERS}"
    echo "  💾 Database Size: ${SIZE_MB} MB"
    echo ""

    # Ask user for retention days
    echo -e "${COLOR_WARNING}Cleanup Configuration:${COLOR_RESET}"
    echo "  Data older than N days will be permanently deleted"
    echo "  (Default: ${CURRENT_RETENTION} days, or press Enter to use current setting)"
    echo ""
    read -p "Enter retention days (0-365, 0=delete all) or press Enter for default [${CURRENT_RETENTION}]: " RETENTION_DAYS

    # Use default if empty
    if [ -z "$RETENTION_DAYS" ]; then
        RETENTION_DAYS=$CURRENT_RETENTION
    fi

    # Validate input
    if ! [[ "$RETENTION_DAYS" =~ ^[0-9]+$ ]] || [ "$RETENTION_DAYS" -lt 0 ] || [ "$RETENTION_DAYS" -gt 365 ]; then
        print_error "Invalid retention days. Must be between 0 and 365"
        read -p "Press Enter to continue..."
        return
    fi

    # Special confirmation for nuclear delete (0 days = wipe everything)
    if [ "$RETENTION_DAYS" = "0" ]; then
        echo ""
        echo -e "${COLOR_ERROR}⚠️⚠️⚠️  DANGER ZONE: COMPLETE DATA WIPE  ⚠️⚠️⚠️${COLOR_RESET}"
        echo "You are about to DELETE ALL trend data from the database!"
        echo "This includes all collected topics, trends, and collection history."
        echo ""
        read -p "Type 'DELETE ALL' to confirm (anything else cancels): " NUKE_CONFIRM
        if [ "$NUKE_CONFIRM" != "DELETE ALL" ]; then
            echo ""
            print_info "Operation cancelled - no data was deleted"
            read -p "Press Enter to continue..."
            return
        fi
        echo ""
        print_info "Nuclear delete confirmed. Proceeding..."
    fi

    echo ""
    echo -e "${COLOR_INFO}Dry run: Checking what would be deleted...${COLOR_RESET}"
    echo ""

    # Run dry-run first
    $DOCKER_COMPOSE exec web python manage.py clean_old_data --days "$RETENTION_DAYS" --dry-run

    echo ""
    echo -e "${COLOR_WARNING}⚠️  WARNING: This operation cannot be undone!${COLOR_RESET}"
    echo ""
    read -p "Do you want to proceed with deletion? (yes/no): " CONFIRM

    if [ "$CONFIRM" = "yes" ] || [ "$CONFIRM" = "y" ]; then
        echo ""
        echo -e "${COLOR_INFO}Deleting old data...${COLOR_RESET}"
        echo ""

        # Actually delete
        $DOCKER_COMPOSE exec web python manage.py clean_old_data --days "$RETENTION_DAYS"

        echo ""
        echo -e "${COLOR_SUCCESS}✓ Cleanup complete!${COLOR_RESET}"
        echo ""

        # Show updated statistics
        echo -e "${COLOR_INFO}Updated Database Status:${COLOR_RESET}"
        DB_STATS_AFTER=$($DOCKER_COMPOSE exec -T web python manage.py shell <<EOF 2>/dev/null
from web_interface.trends_viewer.models import CollectionRun, CollectedTopic, TrendCluster
import os
runs = CollectionRun.objects.count()
topics = CollectedTopic.objects.count()
clusters = TrendCluster.objects.count()
db_path = '/app/web_interface/db/db.sqlite3'
if os.path.exists(db_path):
    size_mb = os.path.getsize(db_path) / (1024 * 1024)
    print(f"{runs}|{topics}|{clusters}|{size_mb:.1f}")
else:
    print("0|0|0|0.0")
EOF
)
        # Extract only data with pipe separators (filter out Django's import message)
        # Look for lines matching the pattern: number|number|number|number.number
        DB_STATS_AFTER=$(echo "$DB_STATS_AFTER" | grep -E '^[0-9]+\|[0-9]+\|[0-9]+\|[0-9.]+$' | tail -1 | tr -d '[:space:]')
        if [ -z "$DB_STATS_AFTER" ]; then
            DB_STATS_AFTER="0|0|0|0.0"  # Default if query failed
        fi
        IFS='|' read -r RUNS_AFTER TOPICS_AFTER CLUSTERS_AFTER SIZE_AFTER <<< "$DB_STATS_AFTER"

        RUNS_DELETED=$((RUNS - RUNS_AFTER))
        TOPICS_DELETED=$((TOPICS - TOPICS_AFTER))
        CLUSTERS_DELETED=$((CLUSTERS - CLUSTERS_AFTER))
        SPACE_FREED=$(echo "$SIZE_MB - $SIZE_AFTER" | bc)

        echo "  📊 Collection Runs: ${RUNS_AFTER} (deleted: ${RUNS_DELETED})"
        echo "  📰 Topics: ${TOPICS_AFTER} (deleted: ${TOPICS_DELETED})"
        echo "  🔗 Clusters: ${CLUSTERS_AFTER} (deleted: ${CLUSTERS_DELETED})"
        echo "  💾 Database Size: ${SIZE_AFTER} MB (freed: ${SPACE_FREED} MB)"
        echo ""
    else
        echo ""
        echo -e "${COLOR_INFO}Cleanup cancelled${COLOR_RESET}"
        echo ""
    fi

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
    echo "User Preferences:"
    echo "  ./setup.sh setup-prefs  - Setup user preferences"
    echo "  ./setup.sh test-prefs   - Test user preferences"
    echo ""
    echo "Information:"
    echo "  ./setup.sh folders      - Show folder structure"
    echo "  ./setup.sh help         - This help"
    echo ""
    read -p "Press Enter to continue..."
}

# Setup User Preferences (Phase 1 + Phase 2)
setup_user_preferences() {
    echo ""
    echo -e "${COLOR_HIGHLIGHT}Setup User Preferences (Phase 1 + Phase 2)${COLOR_RESET}"
    echo ""

    print_info "This will setup the complete user preference system:"
    echo "  ✓ Phase 1: Session-based filtering (no login)"
    echo "  ✓ Phase 2: User accounts with persistent profiles"
    echo ""

    if ! $DOCKER_COMPOSE ps | grep -q "web.*Up"; then
        print_error "Web container is not running"
        echo "Please start the web interface first:"
        echo "  Option 2) Basic Setup (Web Interface Only)"
        echo "  or"
        echo "  Option 3) Start/Stop Services"
        echo ""
        read -p "Press Enter to continue..."
        return 1
    fi

    print_success "Web container is running"
    echo ""

    print_info "Step 1: Creating database migrations..."
    if $DOCKER_COMPOSE exec web python manage.py makemigrations trends_viewer; then
        print_success "Migrations created"
    else
        print_error "Failed to create migrations"
        read -p "Press Enter to continue..."
        return 1
    fi

    echo ""
    print_info "Step 2: Applying migrations..."
    if $DOCKER_COMPOSE exec web python manage.py migrate; then
        print_success "Migrations applied"
    else
        print_error "Failed to apply migrations"
        read -p "Press Enter to continue..."
        return 1
    fi

    echo ""
    print_success "User Preference System Setup Complete!"
    echo ""
    echo -e "${COLOR_HIGHLIGHT}What's Now Available:${COLOR_RESET}"
    echo ""
    echo "For Anonymous Users (Phase 1):"
    echo "  • Visit: http://localhost:11800/filtered/topics/"
    echo "  • Set filters (sources, languages, keywords, etc.)"
    echo "  • Click 'Apply Filters'"
    echo "  • Articles queried from database (NO re-crawling!)"
    echo ""
    echo "For Authenticated Users (Phase 2):"
    echo "  • Sign up: http://localhost:11800/register/"
    echo "  • Save multiple preference profiles"
    echo "  • Quick save from filter panel (💾 button)"
    echo "  • Manage profiles: http://localhost:11800/profile/"
    echo "  • Profiles sync across devices"
    echo ""
    echo -e "${COLOR_INFO}Next Steps:${COLOR_RESET}"
    echo "  1. Run option 15) Test User Preferences"
    echo "  2. Or visit: http://localhost:11800/filtered/trends/"
    echo ""
    echo -e "${COLOR_INFO}Documentation:${COLOR_RESET}"
    echo "  • Complete Guide: docs/USER_PREFERENCES_COMPLETE.md"
    echo "  • Quick Start: docs/PHASE1_QUICKSTART.md"
    echo ""
    read -p "Press Enter to continue..."
}

# Test User Preferences
test_user_preferences() {
    echo ""
    echo -e "${COLOR_HIGHLIGHT}Test User Preferences${COLOR_RESET}"
    echo ""

    if ! $DOCKER_COMPOSE ps | grep -q "web.*Up"; then
        print_error "Web container is not running"
        echo "Please start the web interface first"
        echo ""
        read -p "Press Enter to continue..."
        return 1
    fi

    print_success "Web container is running"
    echo ""

    echo -e "${COLOR_HIGHLIGHT}Testing Guide - Phase 1 (No Login Required)${COLOR_RESET}"
    echo ""
    echo "1. Open your browser:"
    echo "   http://localhost:11800/filtered/topics/"
    echo ""
    echo "2. Set Your Filters:"
    echo "   ✓ Select sources (hold Ctrl/Cmd for multiple)"
    echo "   ✓ Select languages"
    echo "   ✓ Choose time range (e.g., Last 7 days)"
    echo "   ✓ Add keywords to include/exclude"
    echo "   ✓ Set minimum upvotes/comments/score"
    echo ""
    echo "3. Click 'Apply Filters'"
    echo "   → See only articles matching your criteria"
    echo "   → All queries from database (NO re-crawling!)"
    echo ""
    echo "4. Try 'Preview Results' button"
    echo "   → Shows count before applying"
    echo ""
    echo "5. Try 'Reset All' button"
    echo "   → Returns to defaults"
    echo ""
    echo ""
    echo -e "${COLOR_HIGHLIGHT}Testing Guide - Phase 2 (With Login)${COLOR_RESET}"
    echo ""
    echo "1. Create Account:"
    echo "   http://localhost:11800/register/"
    echo ""
    echo "2. Login:"
    echo "   http://localhost:11800/login/"
    echo ""
    echo "3. Set filters and click 💾 button"
    echo "   → Enter profile name"
    echo "   → Profile saved instantly"
    echo ""
    echo "4. Load saved profile:"
    echo "   → Use dropdown in filter panel"
    echo "   → Settings apply immediately"
    echo ""
    echo "5. Manage all profiles:"
    echo "   http://localhost:11800/profile/"
    echo "   → View, edit, delete profiles"
    echo "   → Set default profile"
    echo "   → View preference history"
    echo ""
    echo "6. Test Cross-Device Sync:"
    echo "   → Login on another device/browser"
    echo "   → Same profiles available!"
    echo ""
    echo ""
    echo -e "${COLOR_HIGHLIGHT}Test URLs:${COLOR_RESET}"
    echo "  Filtered Topics:  http://localhost:11800/filtered/topics/"
    echo "  Filtered Trends:  http://localhost:11800/filtered/trends/"
    echo "  Register:         http://localhost:11800/register/"
    echo "  Login:            http://localhost:11800/login/"
    echo "  Profile:          http://localhost:11800/profile/"
    echo ""
    echo -e "${COLOR_HIGHLIGHT}Run Automated Tests:${COLOR_RESET}"
    echo "  \$DOCKER_COMPOSE exec web python manage.py test trends_viewer.tests_preferences"
    echo ""
    echo -e "${COLOR_INFO}Documentation:${COLOR_RESET}"
    echo "  Complete Guide: docs/USER_PREFERENCES_COMPLETE.md"
    echo "  Quick Start:    docs/PHASE1_QUICKSTART.md"
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
        14)
            setup_user_preferences
            ;;
        15)
            test_user_preferences
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
