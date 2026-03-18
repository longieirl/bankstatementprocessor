#!/bin/bash
# scripts/setup-dev.sh
# Development environment setup script

set -e  # Exit on any error

echo "🔧 Setting up development environment..."

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  WARNING: Not in a virtual environment!"
    echo "   Consider running: python -m venv venv && source venv/bin/activate"
    echo "   Continuing anyway..."
fi

# Install development dependencies
echo "📦 Installing development dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements/dev.txt
pip install -r requirements/test.txt

# Install pre-commit hooks
echo "🪝 Setting up pre-commit hooks..."
pre-commit install
pre-commit install --hook-type commit-msg

# Run initial pre-commit on all files to catch any existing issues
echo "🔍 Running initial quality checks on all files..."
pre-commit run --all-files || {
    echo "❌ Pre-commit checks found issues. Please fix them before continuing."
    echo "💡 You can run 'pre-commit run --all-files' to see the issues."
    echo "💡 Most formatting issues can be auto-fixed by running:"
    echo "   - black src tests"
    echo "   - isort src tests"
    exit 1
}

# Verify the setup by running a quick test
echo "🧪 Running quick verification test..."
python -m pytest tests/test_models.py -v -q

echo "✅ Development environment setup complete!"
echo ""
echo "🎯 Quality checks configured:"
echo "   - Black (code formatting)"
echo "   - isort (import sorting)"
echo "   - flake8 (linting with 88-char limit)"
echo "   - mypy (type checking)"
echo "   - bandit (security scanning)"
echo "   - pre-commit hooks (runs on every commit)"
echo ""
echo "🚀 Ready for development!"
echo "💡 Run 'make quality-check' to manually run all quality checks"