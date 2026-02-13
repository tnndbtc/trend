.PHONY: help install build test clean dev up down logs

# Default target
help:
	@echo "Trend Intelligence Platform - Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  install          - Install all dependencies"
	@echo "  install-api      - Install API service dependencies"
	@echo "  install-web      - Install web interface dependencies"
	@echo "  install-crawler  - Install crawler service dependencies"
	@echo ""
	@echo "  build            - Build all Docker images"
	@echo "  build-api        - Build API service image"
	@echo "  build-web        - Build web interface image"
	@echo "  build-crawler    - Build crawler service image"
	@echo ""
	@echo "  test             - Run all tests"
	@echo "  test-api         - Test API service"
	@echo "  test-web         - Test web interface"
	@echo "  test-crawler     - Test crawler service"
	@echo ""
	@echo "  dev              - Start development environment"
	@echo "  dev-api          - Run API service locally"
	@echo "  dev-web          - Run web interface locally"
	@echo "  dev-crawler      - Run crawler service locally"
	@echo ""
	@echo "  up               - Start all services (Docker Compose)"
	@echo "  down             - Stop all services"
	@echo "  logs             - View logs from all services"
	@echo "  logs-api         - View API service logs"
	@echo "  logs-web         - View web interface logs"
	@echo "  logs-crawler     - View crawler service logs"
	@echo ""
	@echo "  clean            - Clean build artifacts"
	@echo "  format           - Format code with black"
	@echo "  lint             - Lint code with ruff"
	@echo "  migrate          - Run database migrations"
	@echo ""

# Install dependencies
install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	@echo "✅ All dependencies installed"

install-api:
	pip install -r api/requirements.txt

install-web:
	pip install -r web_interface/requirements.txt

install-crawler:
	@echo "Crawler is integrated into web_interface"
	pip install -r web_interface/requirements.txt

# Build Docker images
build:
	@echo "Building all Docker images..."
	docker-compose build
	@echo "✅ All images built"

build-api:
	docker-compose build api

build-web:
	docker-compose build web

build-crawler:
	@echo "Crawler is integrated into web service"
	docker-compose build web

# Testing
test:
	@echo "Running all tests..."
	pytest tests/ -v
	@echo "✅ All tests passed"

test-api:
	pytest api/tests/ -v --cov=api

test-web:
	pytest web_interface/trends_viewer/tests/ -v --cov=trends_viewer

test-crawler:
	@echo "Crawler tests integrated into web_interface"
	pytest web_interface/trends_viewer/tests/ -v

# Development servers
dev: dev-infra
	@echo "Starting development environment..."
	@echo "API: http://localhost:8000"
	@echo "Web: http://localhost:11800"
	@echo "Press Ctrl+C to stop"

dev-infra:
	@echo "Starting infrastructure (PostgreSQL, Redis, Qdrant)..."
	docker-compose up -d postgres redis qdrant

dev-api: dev-infra
	@echo "Starting API service on http://localhost:8000..."
	cd api && uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

dev-web: dev-infra
	@echo "Starting web interface on http://localhost:11800..."
	cd web_interface && python manage.py runserver 11800

dev-crawler: dev-infra
	@echo "Crawler integrated into web_interface - use collect_trends command"
	cd web_interface && python manage.py collect_trends

# Docker Compose operations
up:
	@echo "Starting all services..."
	docker-compose up -d
	@echo "✅ Services started"
	@echo "API: http://localhost:8000"
	@echo "Web: http://localhost:11800"
	@echo "Grafana: http://localhost:3000"
	@echo "Prometheus: http://localhost:9090"

down:
	@echo "Stopping all services..."
	docker-compose down
	@echo "✅ Services stopped"

logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f api

logs-web:
	docker-compose logs -f web

logs-crawler:
	docker-compose logs -f crawler

# Database operations
migrate:
	@echo "Running database migrations..."
	cd web_interface && python manage.py migrate
	@echo "✅ Migrations complete"

migrate-make:
	@echo "Creating new migration..."
	cd web_interface && python manage.py makemigrations

# Code quality
format:
	@echo "Formatting code with black..."
	black trend_agent
	black api
	black web_interface
	@echo "✅ Code formatted"

lint:
	@echo "Linting code with ruff..."
	ruff trend_agent
	ruff api
	ruff web_interface
	@echo "✅ Linting complete"

typecheck:
	@echo "Type checking with mypy..."
	mypy trend_agent
	mypy api
	@echo "✅ Type checking complete"

# Cleanup
clean:
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleaned"

# Deployment helpers
deploy-dev:
	kubectl apply -k k8s/overlays/dev

deploy-staging:
	kubectl apply -k k8s/overlays/staging

deploy-prod:
	kubectl apply -k k8s/overlays/production

# Database backup
backup-db:
	@echo "Backing up database..."
	docker-compose exec postgres pg_dump -U trend_user trends > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Database backed up"

# Quick status check
status:
	@echo "Service Status:"
	@echo ""
	@docker-compose ps

# View configuration
config:
	docker-compose config
