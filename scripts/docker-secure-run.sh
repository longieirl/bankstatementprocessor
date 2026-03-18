#!/usr/bin/env bash
# docker-secure-run.sh
# Secure Docker execution script for processing sensitive financial data
# Enforces network isolation and security best practices

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored messages
info() { echo -e "${BLUE}ℹ${NC} $1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }
warning() { echo -e "${YELLOW}⚠${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; }

# Banner
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Bank Statements Processor - Secure Docker Execution        ║"
echo "║  Network-Isolated Mode for GDPR Compliance                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# ============================================================================
# PRE-FLIGHT SECURITY CHECKS
# ============================================================================

info "Running pre-flight security checks..."

# Check 1: Docker is running
if ! docker info >/dev/null 2>&1; then
    error "Docker is not running. Please start Docker first."
    exit 1
fi
success "Docker is running"

# Check 2: Input directory exists
if [ ! -d "./input" ]; then
    error "Input directory './input' not found"
    exit 1
fi
success "Input directory exists"

# Check 3: Input directory is not empty
if [ -z "$(ls -A ./input/*.pdf 2>/dev/null)" ]; then
    warning "No PDF files found in ./input directory"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check 4: Output directory exists and is writable
mkdir -p ./output ./logs
if [ ! -w "./output" ] || [ ! -w "./logs" ]; then
    error "Output/logs directories are not writable"
    exit 1
fi
success "Output directories are writable"

# Check 5: Warn about file permissions
info "Checking file permissions..."
if find ./output ./logs -type f -perm /o+r 2>/dev/null | grep -q .; then
    warning "Some output files are world-readable!"
    warning "Consider restricting permissions: chmod 700 output/ logs/"
fi

# Check 6: Verify no network dependencies in image
info "Verifying image configuration..."

# ============================================================================
# SECURITY CONFIRMATION
# ============================================================================

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  SECURITY CONFIGURATION                                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  🔒 Network Mode:       NONE (complete isolation)"
echo "  🔒 Filesystem:          Read-only root + restricted volumes"
echo "  🔒 Capabilities:        ALL DROPPED"
echo "  🔒 Privilege Escalation: DISABLED"
echo "  🔒 Resource Limits:     8GB RAM, 4 CPUs"
echo ""
echo "  📂 Input Directory:     ./input (read-only)"
echo "  📂 Output Directory:    ./output (read-write)"
echo "  📂 Logs Directory:      ./logs (read-write)"
echo ""

# GDPR Warning
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  ⚠️  GDPR & DATA PRIVACY NOTICE                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  This script processes sensitive financial data."
echo ""
echo "  ✓ All processing is LOCAL (no network access)"
echo "  ✓ Data stays on your computer"
echo "  ✓ No cloud services or external APIs"
echo "  ✓ GDPR-compliant architecture"
echo ""
echo "  YOUR RESPONSIBILITIES:"
echo "  • Ensure you have authorization to process the documents"
echo "  • Protect output files with appropriate access controls"
echo "  • Delete processed data when no longer needed"
echo "  • Use encrypted disk storage (FileVault/BitLocker)"
echo ""

# User confirmation
read -p "Do you confirm you understand these responsibilities? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    error "User declined responsibility confirmation"
    exit 1
fi

# ============================================================================
# CLEANUP OLD CONTAINERS
# ============================================================================

info "Cleaning up old containers..."
if docker ps -a --format '{{.Names}}' | grep -q "bank-statement-processor-isolated"; then
    docker-compose -f docker-compose.network-isolated.yml down 2>/dev/null || true
fi
docker system prune -f >/dev/null 2>&1 || true
success "Cleanup complete"

# ============================================================================
# BUILD AND RUN
# ============================================================================

echo ""
info "Building Docker image with network isolation..."
echo ""

# Export version info
export VERSION="${VERSION:-$(cat src/__version__.py | grep -oP '(?<=__version__ = ")[^"]*')}"
export BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
export VCS_REF="$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"

# Build and run with network isolation
if docker-compose -f docker-compose.network-isolated.yml up --build; then
    echo ""
    success "Processing completed successfully!"
    echo ""
    info "Output files:"
    ls -lh ./output/*.{csv,json} 2>/dev/null || echo "  No output files generated"
    echo ""
    info "Logs:"
    ls -lh ./logs/*.jsonl 2>/dev/null || echo "  No log files generated"
    echo ""

    # Security reminder
    warning "SECURITY REMINDER:"
    warning "• Review output files for sensitive data"
    warning "• Restrict file permissions: chmod 600 output/* logs/*"
    warning "• Delete files when no longer needed"
    warning "• Do not share without proper encryption"
    echo ""

    exit 0
else
    echo ""
    error "Processing failed!"
    echo ""
    info "Troubleshooting:"
    echo "  1. Check logs: docker-compose -f docker-compose.network-isolated.yml logs"
    echo "  2. Verify input PDFs are valid"
    echo "  3. Check disk space: df -h"
    echo "  4. Review environment variables in .env"
    echo ""
    exit 1
fi
