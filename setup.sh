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

    # Check if OPENAI_API_KEY is set in environment
    if [ -n "$OPENAI_API_KEY" ]; then
        echo -e "${GREEN}✅ Using OPENAI_API_KEY from environment variable${NC}"
    else
        # Check if .env.docker exists
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

        # Validate OPENAI_API_KEY is set in .env.docker
        if grep -q "your_api_key_here" .env.docker; then
            echo -e "${RED}❌ OPENAI_API_KEY not set in .env.docker${NC}"
            echo "Please edit .env.docker and add your OpenAI API key"
            return 1
        fi

        echo -e "${GREEN}✅ Environment configuration found in .env.docker${NC}"
    fi

    # Create data directories
    echo -e "${BLUE}📁 Creating data directories...${NC}"
    mkdir -p data/db data/cache
    echo -e "${GREEN}✅ Data directories created${NC}"

    # Stop any existing containers
    echo -e "${BLUE}🛑 Stopping any existing containers...${NC}"
    ${DOCKER_COMPOSE} down 2>/dev/null || true

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
    echo "  ${DOCKER_COMPOSE} exec web python manage.py collect_trends --max-trends 20"
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
        0)
            echo ""
            echo -e "${GREEN}👋 Goodbye!${NC}"
            echo ""
            exit 0
            ;;
        *)
            echo ""
            echo -e "${RED}❌ Invalid option. Please select 1 or 0.${NC}"
            sleep 2
            ;;
    esac
done
