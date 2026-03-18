# Bank Statements Processor - Development Makefile
# Provides convenient commands for common development tasks

# Extract version from __version__.py (macOS/BSD compatible)
VERSION ?= $(shell grep '__version__ = ' src/__version__.py 2>/dev/null | cut -d'"' -f2 || echo "dev")
BUILD_DATE := $(shell date -u +"%Y-%m-%dT%H:%M:%SZ")
VCS_REF := $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")

.PHONY: help install install-dev test test-unit test-integration coverage lint format security clean build build-free-tier build-free-tier-dry-run docker-build docker-run docker-up setup pre-commit-install pre-commit-run type-check version-bump-major version-bump-minor version-bump-patch release

# Default target
help:	## Show this help message
	@echo "Bank Statements Processor - Development Commands"
	@echo "================================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation and setup
install:	## Install production dependencies
	pip install --upgrade pip
	pip install -r requirements.txt

install-dev:	## Install development dependencies
	pip install --upgrade pip
	pip install -r requirements.txt
	pip install -r requirements/test.txt
	pip install -r requirements/dev.txt

setup:	## Full development environment setup
	@echo "🔧 Setting up development environment..."
	$(MAKE) install-dev
	$(MAKE) pre-commit-install
	chmod +x setup-git-hooks.sh
	./setup-git-hooks.sh
	@echo "✅ Setup complete!"

# Testing
test:	## Run all tests with coverage
	python3 -m pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=xml --cov-report=html --cov-fail-under=90

test-unit:	## Run only unit tests
	python3 -m pytest tests/ -v -m "unit" --cov=src --cov-report=term-missing

test-integration:	## Run only integration tests
	python3 -m pytest tests/ -v -m "integration" --cov=src --cov-report=term-missing

test-fast:	## Run tests in parallel (faster)
	python3 -m pytest tests/ -v -n auto --cov=src --cov-report=term-missing

test-watch:	## Run tests in watch mode (re-run on file changes)
	python3 -m ptw -- tests/ -v --cov=src

coverage:	## Generate and open coverage report
	python3 -m pytest tests/ --cov=src --cov-report=html --cov-fail-under=90
	@echo "Opening coverage report in browser..."
	@python3 -c "import webbrowser; webbrowser.open('htmlcov/index.html')"

# Code quality
format:	## Format code with Black and isort
	@echo "🎨 Formatting code..."
	black src tests
	isort src tests
	@echo "✅ Code formatted"

lint:	## Run linting checks
	@echo "🔍 Running linting checks..."
	flake8 src tests --max-line-length=88 --extend-ignore=E203,W503,E501,W504,D,C420
	@echo "✅ Linting passed"

type-check:	## Run type checking with MyPy
	@echo "🔎 Running type checks..."
	mypy src --ignore-missing-imports
	@echo "✅ Type checking passed"

security:	## Run security scans
	@echo "🔐 Running security scans..."
	bandit -r src -f json -o bandit-report.json || echo "⚠️  Bandit found issues - check bandit-report.json"
	echo "" | safety scan --json > safety-report.json 2>/dev/null || echo "⚠️  Safety requires authentication - skipping vulnerability scan"
	@echo "📊 Security reports generated: bandit-report.json, safety-report.json"

check:	## Run all quality checks (format, lint, type-check, security)
	@echo "🔍 Running all quality checks..."
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) type-check
	$(MAKE) security
	@echo "✅ All quality checks completed"

# Pre-commit hooks
pre-commit-install:	## Install pre-commit hooks
	pre-commit install
	pre-commit install --hook-type commit-msg
	pre-commit install --hook-type pre-push

pre-commit-run:	## Run pre-commit on all files
	pre-commit run --all-files

pre-commit-update:	## Update pre-commit hook versions
	pre-commit autoupdate

validate-config:	## Validate quality tool configuration
	@echo "🔧 Validating quality configuration..."
	@python3 scripts/validate-quality-config.py

# Docker operations
docker-build:	## Build Docker image with version tags
	@echo "🐳 Building Docker image v$(VERSION)..."
	docker build \
		--target production \
		--build-arg VERSION=$(VERSION) \
		--build-arg BUILD_DATE=$(BUILD_DATE) \
		--build-arg VCS_REF=$(VCS_REF) \
		-t bankstatementsprocessor:$(VERSION) \
		-t bankstatementsprocessor:latest \
		.
	@echo "✅ Docker image built: v$(VERSION)"

docker-run:	## Run application in Docker container
	@echo "🐳 Running application in Docker..."
	VERSION=$(VERSION) BUILD_DATE=$(BUILD_DATE) VCS_REF=$(VCS_REF) docker-compose up --build

docker-up:	## Start application with docker-compose (with build metadata)
	@echo "🐳 Starting application with docker-compose..."
	VERSION=$(VERSION) BUILD_DATE=$(BUILD_DATE) VCS_REF=$(VCS_REF) docker-compose up --build

docker-push:	## Push Docker images to GHCR
	@echo "🐳 Pushing Docker images to GHCR..."
	docker push ghcr.io/longieirl/bankstatements:$(VERSION)
	docker push ghcr.io/longieirl/bankstatements:latest
	@echo "✅ Docker images pushed"

docker-test:	## Test Docker image functionality
	@echo "🐳 Testing Docker image..."
	docker run --rm bankstatementsprocessor:latest python3 -m src.app --version

docker-clean:	## Clean up Docker images and containers
	@echo "🐳 Cleaning Docker resources..."
	docker-compose down --volumes --remove-orphans
	docker system prune -f
	@echo "✅ Docker cleanup completed"

docker-scan-trivy:	## Scan Docker image for vulnerabilities with Trivy (HIGH,CRITICAL)
	@echo "🔍 Scanning Docker image for vulnerabilities..."
	@docker images bankstatementsprocessor:latest -q > /dev/null 2>&1 || { echo "❌ Image not found. Run 'make docker-build' first."; exit 1; }
	trivy image --severity HIGH,CRITICAL bankstatementsprocessor:latest
	@echo "✅ Vulnerability scan completed"

docker-scan-trivy-full:	## Full Trivy scan with all severities
	@echo "🔍 Running comprehensive Trivy scan..."
	@docker images bankstatementsprocessor:latest -q > /dev/null 2>&1 || { echo "❌ Image not found. Run 'make docker-build' first."; exit 1; }
	trivy image bankstatementsprocessor:latest
	@echo "✅ Full scan completed"

docker-scan-secrets:	## Scan for secrets accidentally baked into image
	@echo "🔐 Scanning for secrets in Docker image..."
	@docker images bankstatementsprocessor:latest -q > /dev/null 2>&1 || { echo "❌ Image not found. Run 'make docker-build' first."; exit 1; }
	trivy image --scanners secret bankstatementsprocessor:latest
	@echo "✅ Secret scan completed"

docker-scan-config:	## Scan for misconfigurations
	@echo "🔧 Scanning for misconfigurations..."
	@docker images bankstatementsprocessor:latest -q > /dev/null 2>&1 || { echo "❌ Image not found. Run 'make docker-build' first."; exit 1; }
	trivy image --scanners config bankstatementsprocessor:latest
	@echo "✅ Configuration scan completed"

docker-scan-scout:	## Scan Docker image with Docker Scout
	@echo "🔍 Scanning Docker image with Docker Scout..."
	@docker images bankstatementsprocessor:latest -q > /dev/null 2>&1 || { echo "❌ Image not found. Run 'make docker-build' first."; exit 1; }
	docker scout cves bankstatementsprocessor:latest --only-severity critical,high
	@echo "✅ Docker Scout scan completed"

docker-scan-scout-recommendations:	## Get base image recommendations from Docker Scout
	@echo "💡 Getting base image recommendations..."
	@docker images bankstatementsprocessor:latest -q > /dev/null 2>&1 || { echo "❌ Image not found. Run 'make docker-build' first."; exit 1; }
	docker scout recommendations bankstatementsprocessor:latest
	@echo "✅ Recommendations displayed"

docker-scan-all:	## Run all security scans (comprehensive)
	@echo "🔍 Running all security scans..."
	@$(MAKE) docker-scan-trivy
	@echo ""
	@$(MAKE) docker-scan-secrets
	@echo ""
	@$(MAKE) docker-scan-config
	@echo ""
	@$(MAKE) docker-scan-scout
	@echo ""
	@echo "✅ All security scans completed"

docker-update-base:	## Update base image and rebuild (intentional update)
	@echo "🔄 Pulling latest base image..."
	docker pull python:3.11-slim
	@echo "🐳 Rebuilding with updated base image..."
	$(MAKE) docker-build
	@echo "🔍 Scanning updated image..."
	@$(MAKE) docker-scan-trivy
	@echo "✅ Base image updated, rebuilt, and scanned"

docker-secure-run:	## Run with network isolation for sensitive data (GDPR-compliant)
	@echo "🔒 Running with network isolation (GDPR-compliant mode)..."
	@./scripts/docker-secure-run.sh

docker-secure-test:	## Test network isolation is working correctly
	@echo "🧪 Testing network isolation..."
	@echo "Building with network isolation..."
	@docker-compose -f docker-compose.network-isolated.yml up -d 2>/dev/null || true
	@sleep 2
	@echo "Verifying network mode..."
	@docker inspect bank-statement-processor-isolated --format='Network Mode: {{.HostConfig.NetworkMode}}' 2>/dev/null || echo "Container not running"
	@echo "Testing network access (should fail)..."
	@docker exec bank-statement-processor-isolated ping -c 1 8.8.8.8 2>&1 | grep -q "Network is unreachable" && echo "✅ Network isolation verified: ping failed (expected)" || echo "❌ WARNING: Network isolation may not be working!"
	@docker-compose -f docker-compose.network-isolated.yml down 2>/dev/null
	@echo "✅ Network isolation test completed"

# Build and packaging
build-free-tier:	## Build FREE tier (bankpdfprocessor) distribution — strips PAID_ONLY code
	@echo "📦 Building FREE tier distribution..."
	python3 scripts/build_free_tier.py
	@echo "✅ FREE tier build complete: dist/bankpdfprocessor"

build-free-tier-dry-run:	## Show what build-free-tier would do without making changes
	python3 scripts/build_free_tier.py --dry-run

build:	## Build the application
	@echo "🔨 Building application..."
	python3 -m pip install --upgrade build
	python3 -m build
	@echo "✅ Build completed"

clean:	## Clean up generated files
	@echo "🧹 Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf dist/
	rm -rf build/
	rm -f bandit-report.json
	rm -f safety-report.json
	@echo "✅ Cleanup completed"

# Development workflow helpers
new-feature:	## Start a new feature branch (usage: make new-feature NAME=my-feature)
	@if [ -z "$(NAME)" ]; then \
		echo "❌ Please provide feature name: make new-feature NAME=my-feature"; \
		exit 1; \
	fi
	git checkout main
	git pull origin main
	git checkout -b feature/$(NAME)
	@echo "✅ Created feature branch: feature/$(NAME)"

new-fix:	## Start a new fix branch (usage: make new-fix NAME=my-fix)
	@if [ -z "$(NAME)" ]; then \
		echo "❌ Please provide fix name: make new-fix NAME=my-fix"; \
		exit 1; \
	fi
	git checkout main
	git pull origin main
	git checkout -b fix/$(NAME)
	@echo "✅ Created fix branch: fix/$(NAME)"

pr-ready:	## Check if code is ready for PR
	@echo "🔍 Checking if code is ready for PR..."
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) type-check
	$(MAKE) security
	$(MAKE) test
	@echo "✅ Code is ready for PR!"

# CI/CD simulation
ci-lint:	## Simulate CI linting job locally
	@echo "🤖 Simulating CI linting job..."
	python3 -m pip install --upgrade pip
	pip install -r requirements.txt
	pip install -r requirements/dev.txt
	black --check --diff src tests
	flake8 src tests --max-line-length=88 --extend-ignore=E203,W503,E501,W504,D,C420
	mypy src --ignore-missing-imports
	bandit -r src -f json -o bandit-report.json || true
	echo "" | safety scan --json > safety-report.json 2>/dev/null || echo "⚠️  Safety requires authentication - skipping vulnerability scan"
	@echo "✅ CI linting simulation completed"

ci-test:	## Simulate CI test job locally
	@echo "🤖 Simulating CI test job..."
	python3 -m pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=xml --cov-report=html -n auto --tb=short
	@echo "✅ CI test simulation completed"

ci-docker:	## Simulate CI Docker job locally
	@echo "🤖 Simulating CI Docker job..."
	docker build -t bankstatementsprocessor:test .
	docker run --rm bankstatementsprocessor:test python3 -c "import sys; print('Python:', sys.version); import src.app; print('App module loaded successfully')"
	@echo "✅ CI Docker simulation completed"

ci-all:	## Run all CI jobs locally
	@echo "🤖 Running full CI simulation..."
	$(MAKE) ci-lint
	$(MAKE) ci-test
	$(MAKE) ci-docker
	@echo "✅ Full CI simulation completed"

# Version management
version-bump-major:	## Bump major version (X.0.0)
	@echo "📦 Bumping major version..."
	python3 scripts/bump_version.py major

version-bump-minor:	## Bump minor version (0.X.0)
	@echo "📦 Bumping minor version..."
	python3 scripts/bump_version.py minor

version-bump-patch:	## Bump patch version (0.0.X)
	@echo "📦 Bumping patch version..."
	python3 scripts/bump_version.py patch

release:	## Create a release (bump patch, tag, and push)
	@echo "🚀 Creating release..."
	$(MAKE) version-bump-patch
	git push origin main --tags
	@echo "✅ Release created and pushed"

# Environment info
info:	## Show development environment information
	@echo "Bank Statements Processor - Environment Info"
	@echo "==========================================="
	@echo "Current version: $(VERSION)"
	@echo "Python version: $(shell python3 --version)"
	@echo "Pip version: $(shell pip --version)"
	@echo "Git branch: $(shell git branch --show-current 2>/dev/null || echo 'Not a git repository')"
	@echo "Git status: $(shell git status --porcelain 2>/dev/null | wc -l | tr -d ' ') files modified"
	@echo "Pre-commit installed: $(shell pre-commit --version 2>/dev/null && echo 'Yes' || echo 'No')"
	@echo "Docker available: $(shell docker --version 2>/dev/null && echo 'Yes' || echo 'No')"
	@echo "Virtual environment: $(shell echo $${VIRTUAL_ENV:-'None'})"

# Data management and GDPR compliance
delete-data:	## Delete all output files (requires confirmation)
	@echo "⚠️  WARNING: This will delete ALL output files"
	@echo "Files to be deleted:"
	@ls -lh output/*.csv output/*.json output/*.xlsx 2>/dev/null || echo "  (no files found)"
	@read -p "Are you sure? Type 'yes' to confirm: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		python3 scripts/delete_data.py --all --force; \
		echo "✅ Data deleted successfully"; \
	else \
		echo "❌ Deletion cancelled"; \
	fi

cleanup-old-data:	## Clean up files older than retention period
	@echo "🧹 Cleaning up expired files..."
	@python3 scripts/delete_data.py --older-than $${DATA_RETENTION_DAYS:-90}
	@echo "✅ Cleanup completed"

show-retention-status:	## Show data retention status
	@echo "📊 Data Retention Status"
	@echo "======================="
	@python3 -c "from src.services.data_retention import DataRetentionService; from src.app import AppConfig; config = AppConfig.from_env(); service = DataRetentionService(config.data_retention_days, config.output_dir); files = service.find_expired_files(); print(f'Retention period: {config.data_retention_days} days'); print(f'Expired files: {len(files)}')"

# Docker build modes
.PHONY: docker-local docker-remote docker-build docker-pull

docker-local: ## Build and run from local code
	@echo "🔨 Building from local code..."
	@cp .env.local .env
	docker-compose down
	docker-compose up --build

docker-remote: ## Pull and run from GitHub registry
	@echo "⬇️  Pulling from GitHub Container Registry..."
	@cp .env.remote .env
	docker-compose down
	docker-compose pull
	docker-compose up

docker-build: ## Build local image without running
	@cp .env.local .env
	docker-compose build

docker-pull: ## Pull remote image without running
	@cp .env.remote .env
	docker-compose pull
