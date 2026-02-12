#!/bin/bash
#
# Menu helper functions for interactive setup.sh
# Source this file to use menu functions
#

# Source colors
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/colors.sh"

# Show a menu and get user selection
# Usage: show_menu "Title" "option1:description1" "option2:description2" ...
show_menu() {
    local title="$1"
    shift
    local options=("$@")

    print_section "$title"
    echo ""

    local i=1
    for option in "${options[@]}"; do
        local key="${option%%:*}"
        local desc="${option#*:}"
        echo -e "  ${COLOR_HIGHLIGHT}${key}.${COLOR_RESET} ${desc}"
        ((i++))
    done

    echo -e "\n  ${COLOR_MUTED}0.${COLOR_RESET} ${COLOR_MUTED}← Back / Exit${COLOR_RESET}"
    echo ""
}

# Get user input with prompt
# Usage: value=$(get_input "Prompt message" "default_value")
get_input() {
    local prompt="$1"
    local default="$2"
    local value

    if [ -n "$default" ]; then
        read -p "$(echo -e ${COLOR_INFO}${prompt}${COLOR_RESET} [${default}]: )" value
        echo "${value:-$default}"
    else
        read -p "$(echo -e ${COLOR_INFO}${prompt}${COLOR_RESET}: )" value
        echo "$value"
    fi
}

# Confirm action
# Usage: if confirm "Are you sure?"; then ...
confirm() {
    local prompt="$1"
    local response

    read -p "$(echo -e ${COLOR_WARNING}${prompt}${COLOR_RESET} [y/N]: )" response
    case "$response" in
        [yY][eE][sS]|[yY])
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Show progress bar
# Usage: show_progress 50 100 "Processing..."
show_progress() {
    local current=$1
    local total=$2
    local message=$3
    local percent=$((current * 100 / total))
    local filled=$((percent / 2))
    local empty=$((50 - filled))

    printf "\r${COLOR_INFO}${message}${COLOR_RESET} ["
    printf "%${filled}s" | tr ' ' '='
    printf "%${empty}s" | tr ' ' ' '
    printf "] ${percent}%%"

    if [ "$current" -eq "$total" ]; then
        echo ""
    fi
}

# Spinner for long-running tasks
# Usage: run_with_spinner "make build" "Building images..."
run_with_spinner() {
    local command="$1"
    local message="$2"
    local pid
    local spin='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    local i=0

    # Run command in background
    eval "$command" > /tmp/spinner_output_$$ 2>&1 &
    pid=$!

    # Show spinner while command runs
    while kill -0 $pid 2>/dev/null; do
        i=$(( (i+1) % 10 ))
        printf "\r${COLOR_INFO}${spin:$i:1}${COLOR_RESET} ${message}"
        sleep 0.1
    done

    # Check if command succeeded
    wait $pid
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        printf "\r${COLOR_SUCCESS}${SYMBOL_SUCCESS}${COLOR_RESET} ${message}\n"
    else
        printf "\r${COLOR_ERROR}${SYMBOL_ERROR}${COLOR_RESET} ${message} (failed)\n"
        if [ -f "/tmp/spinner_output_$$" ]; then
            cat "/tmp/spinner_output_$$"
        fi
    fi

    rm -f "/tmp/spinner_output_$$"
    return $exit_code
}

# Check if a service is running (Docker)
# Usage: if is_service_running "api"; then ...
is_service_running() {
    local service_name="$1"
    docker-compose ps -q "$service_name" 2>/dev/null | grep -q .
}

# Get service status symbol
# Usage: status=$(get_service_status "api")
get_service_status() {
    local service_name="$1"

    if docker-compose ps "$service_name" 2>/dev/null | grep -q "Up"; then
        echo "${COLOR_SUCCESS}${SYMBOL_SUCCESS} running${COLOR_RESET}"
    else
        echo "${COLOR_MUTED}${SYMBOL_STOPPED} stopped${COLOR_RESET}"
    fi
}

# Get service URL if running
# Usage: url=$(get_service_url "api" "8000")
get_service_url() {
    local service_name="$1"
    local port="$2"

    if is_service_running "$service_name"; then
        echo "http://localhost:${port}"
    else
        echo "${COLOR_MUTED}not running${COLOR_RESET}"
    fi
}

# Wait for user to press any key
pause() {
    local message="${1:-Press any key to continue...}"
    read -n 1 -s -r -p "$(echo -e ${COLOR_MUTED}${message}${COLOR_RESET})"
    echo ""
}

# Clear screen and show banner
show_banner() {
    clear
    echo -e "${COLOR_BOLD_CYAN}"
    cat << "EOF"
╔══════════════════════════════════════════════════════╗
║  🌟  Trend Intelligence Platform - Dev Hub  🌟      ║
╚══════════════════════════════════════════════════════╝
EOF
    echo -e "${COLOR_RESET}"
}

# Show current system status
show_status() {
    echo -e "${COLOR_INFO}Current Status:${COLOR_RESET}"

    # Git branch
    local branch=$(git branch 2>/dev/null | grep '^\*' | cut -d' ' -f2-)
    local git_status=$(git status --porcelain 2>/dev/null | wc -l)
    if [ "$git_status" -eq 0 ]; then
        echo -e "  ${SYMBOL_SUCCESS} Branch: ${COLOR_HIGHLIGHT}${branch}${COLOR_RESET} (clean)"
    else
        echo -e "  ${SYMBOL_WARNING}Branch: ${COLOR_HIGHLIGHT}${branch}${COLOR_RESET} ($git_status changes)"
    fi

    # Running services
    local running_count=0
    local stopped_count=0
    for service in api web postgres redis qdrant; do
        if is_service_running "$service"; then
            ((running_count++))
        else
            ((stopped_count++))
        fi
    done
    echo -e "  ${SYMBOL_RUNNING} Services: ${COLOR_SUCCESS}${running_count} running${COLOR_RESET}, ${COLOR_MUTED}${stopped_count} stopped${COLOR_RESET}"

    # Last update
    local last_commit=$(git log -1 --format="%ar" 2>/dev/null || echo "unknown")
    echo -e "  ${SYMBOL_INFO} Last update: ${last_commit}"

    echo ""
}

# Execute a make target with visual feedback
# Usage: execute_make_target "build" "Building Docker images..."
execute_make_target() {
    local target="$1"
    local message="$2"

    echo -e "\n${COLOR_INFO}${SYMBOL_RUNNING}${COLOR_RESET} ${message}\n"

    if make "$target"; then
        echo ""
        print_success "${message} completed!"
        return 0
    else
        echo ""
        print_error "${message} failed!"
        return 1
    fi
}

# Show what's next suggestions
show_next_steps() {
    echo -e "\n${COLOR_INFO}What would you like to do next?${COLOR_RESET}"
    echo -e "  ${COLOR_HIGHLIGHT}1.${COLOR_RESET} Return to main menu"
    echo -e "  ${COLOR_HIGHLIGHT}2.${COLOR_RESET} Exit"
    echo -e "  ${COLOR_MUTED}Or press any other key to continue...${COLOR_RESET}\n"

    read -n 1 -s -r choice
    case "$choice" in
        1)
            return 0  # Return to menu
            ;;
        2)
            exit 0
            ;;
        *)
            return 1  # Continue
            ;;
    esac
}

# Check prerequisites
check_prerequisites() {
    local missing=0

    print_info "Checking prerequisites..."

    # Check Docker
    if command -v docker &> /dev/null; then
        print_success "Docker installed"
    else
        print_error "Docker not found"
        ((missing++))
    fi

    # Check Docker Compose
    if command -v docker-compose &> /dev/null; then
        print_success "Docker Compose installed"
    else
        print_error "Docker Compose not found"
        ((missing++))
    fi

    # Check Python
    if command -v python3 &> /dev/null; then
        local python_version=$(python3 --version | cut -d' ' -f2)
        print_success "Python ${python_version} installed"
    else
        print_error "Python 3 not found"
        ((missing++))
    fi

    # Check Make
    if command -v make &> /dev/null; then
        print_success "Make installed"
    else
        print_warning "Make not found (optional)"
    fi

    if [ $missing -gt 0 ]; then
        echo ""
        print_error "$missing required prerequisites missing!"
        return 1
    else
        echo ""
        print_success "All prerequisites met!"
        return 0
    fi
}
