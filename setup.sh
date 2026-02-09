#!/bin/bash

# AI Trend Intelligence Agent - Docker Setup Script
# This script provides a menu-driven interface for managing the application

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "=================================================="
echo "  AI Trend Intelligence Agent - Docker Setup"
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
    echo -e "${GREEN}1)${NC} Build and start container"
    echo -e "${GREEN}2)${NC} Collect trends (includes category management)"
    echo -e "${GREEN}3)${NC} Run database migrations"
    echo -e "${GREEN}4)${NC} Clean old data"
    echo -e "${RED}0)${NC} Exit"
    echo ""
    echo -n "Select an option: "
}

# Function to build and start container
build_and_start() {
    echo ""
    echo -e "${BLUE}=================================================="
    echo "  Building and Starting Container"
    echo "==================================================${NC}"
    echo ""

    # Check if .env.docker exists and create it if missing
    # This must happen before any docker-compose commands
    if [ ! -f .env.docker ]; then
        echo -e "${YELLOW}⚠️  .env.docker not found. Creating from template...${NC}"

        if [ -f .env.docker.example ]; then
            cp .env.docker.example .env.docker
            echo -e "${GREEN}✅ Created .env.docker from example${NC}"
            echo -e "${YELLOW}⚠️  IMPORTANT: Edit .env.docker and add your OPENAI_API_KEY${NC}"
            echo ""
            read -p "Press Enter to continue after you've added your API key, or Ctrl+C to exit..."
        else
            echo -e "${RED}❌ .env.docker.example not found${NC}"
            return 1
        fi
    fi

    # Check if OPENAI_API_KEY is set in environment or .env.docker
    if [ -n "$OPENAI_API_KEY" ]; then
        echo -e "${GREEN}✅ Using OPENAI_API_KEY from environment variable${NC}"
    else
        # Validate OPENAI_API_KEY is set in .env.docker
        if grep -q "your_api_key_here" .env.docker; then
            echo -e "${RED}❌ OPENAI_API_KEY not set in .env.docker${NC}"
            echo "Please edit .env.docker and add your OpenAI API key"
            return 1
        fi

        echo -e "${GREEN}✅ Environment configuration found in .env.docker${NC}"
    fi

    # Check if ALLOWED_HOSTS is set in environment
    if [ -n "$ALLOWED_HOSTS" ]; then
        echo -e "${GREEN}✅ Using ALLOWED_HOSTS from environment variable: $ALLOWED_HOSTS${NC}"
    else
        echo -e "${BLUE}ℹ️  Using ALLOWED_HOSTS from .env.docker${NC}"
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

    # Start the containers
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
    echo "  🎉 Setup Complete!"
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
        echo "Please start the container first (Option 1)"
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
        echo "Please start the container first (Option 1)"
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
        echo "Please start the container first (Option 1)"
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
            if build_and_start; then
                echo ""
                read -p "Press Enter to return to menu..."
            else
                echo ""
                echo -e "${RED}❌ Build and start failed. Please check the errors above.${NC}"
                read -p "Press Enter to return to menu..."
            fi
            ;;
        2)
            if collect_trends; then
                echo ""
                read -p "Press Enter to return to menu..."
            else
                echo ""
                echo -e "${RED}❌ Trend collection failed. Please check the errors above.${NC}"
                read -p "Press Enter to return to menu..."
            fi
            ;;
        3)
            if run_migrations; then
                echo ""
                read -p "Press Enter to return to menu..."
            else
                echo ""
                echo -e "${RED}❌ Migration failed. Please check the errors above.${NC}"
                read -p "Press Enter to return to menu..."
            fi
            ;;
        4)
            if clean_old_data; then
                echo ""
                read -p "Press Enter to return to menu..."
            else
                echo ""
                echo -e "${RED}❌ Cleanup failed. Please check the errors above.${NC}"
                read -p "Press Enter to return to menu..."
            fi
            ;;
        0)
            echo ""
            echo -e "${GREEN}👋 Goodbye!${NC}"
            echo ""
            exit 0
            ;;
        *)
            echo ""
            echo -e "${RED}❌ Invalid option. Please select 1-4, or 0.${NC}"
            sleep 2
            ;;
    esac
done
