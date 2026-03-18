#!/bin/bash
#
# Script to install git hooks for this repository
# Run this after cloning the repository: ./scripts/install-git-hooks.sh
#

set -e

HOOKS_DIR=".git/hooks"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Installing git hooks..."
echo ""

# Check if we're in a git repository
if [ ! -d "$PROJECT_ROOT/.git" ]; then
    echo "❌ Error: Not in a git repository root"
    echo "Please run this script from the project root directory"
    exit 1
fi

# Create hooks directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/$HOOKS_DIR"

# Install pre-commit hook
cat > "$PROJECT_ROOT/$HOOKS_DIR/pre-commit" << 'EOF'
#!/bin/bash
#
# Git hook to prevent direct commits to main branch
# This enforces the PR workflow
#

# Get the current branch name
branch="$(git symbolic-ref HEAD 2>/dev/null | sed 's/refs\/heads\///')"

# Define protected branches
protected_branches="main master"

# Check if current branch is protected
for protected in $protected_branches; do
    if [ "$branch" = "$protected" ]; then
        echo ""
        echo "❌ COMMIT REJECTED!"
        echo ""
        echo "You are trying to commit directly to the '$branch' branch."
        echo "Direct commits to '$branch' are not allowed."
        echo ""
        echo "Please follow this workflow:"
        echo "  1. Create a feature branch:"
        echo "     git checkout -b feature/your-feature-name"
        echo ""
        echo "  2. Make your changes and commit:"
        echo "     git add ."
        echo "     git commit -m 'your message'"
        echo ""
        echo "  3. Push your branch:"
        echo "     git push -u origin feature/your-feature-name"
        echo ""
        echo "  4. Create a Pull Request on GitHub"
        echo ""
        echo "To bypass this hook (NOT recommended):"
        echo "  git commit --no-verify"
        echo ""
        exit 1
    fi
done

exit 0
EOF

chmod +x "$PROJECT_ROOT/$HOOKS_DIR/pre-commit"
echo "✅ Installed pre-commit hook"

# Install pre-push hook
cat > "$PROJECT_ROOT/$HOOKS_DIR/pre-push" << 'EOF'
#!/bin/bash
#
# Git hook to prevent direct pushes to main branch
# This is a safety net in case pre-commit is bypassed
#

# Read stdin to get the list of refs being pushed
while read local_ref local_sha remote_ref remote_sha
do
    # Extract branch name from ref
    if [[ $remote_ref =~ refs/heads/(.*) ]]; then
        branch="${BASH_REMATCH[1]}"

        # Check if pushing to protected branch
        if [ "$branch" = "main" ] || [ "$branch" = "master" ]; then
            echo ""
            echo "❌ PUSH REJECTED!"
            echo ""
            echo "You are trying to push directly to the '$branch' branch."
            echo "Direct pushes to '$branch' are not allowed."
            echo ""
            echo "Please follow this workflow:"
            echo "  1. Push to a feature branch:"
            echo "     git push origin your-feature-branch"
            echo ""
            echo "  2. Create a Pull Request on GitHub"
            echo ""
            echo "  3. After CI/CD checks pass and review, merge via GitHub"
            echo ""
            echo "If you need to update main (e.g., after merge):"
            echo "  git checkout main"
            echo "  git pull origin main"
            echo ""
            echo "To bypass this hook (NOT recommended):"
            echo "  git push --no-verify"
            echo ""
            exit 1
        fi
    fi
done

exit 0
EOF

chmod +x "$PROJECT_ROOT/$HOOKS_DIR/pre-push"
echo "✅ Installed pre-push hook"

echo ""
echo "🎉 Git hooks installed successfully!"
echo ""
echo "These hooks will:"
echo "  • Prevent direct commits to main/master branches"
echo "  • Prevent direct pushes to main/master branches"
echo "  • Enforce the Pull Request workflow"
echo ""
echo "To bypass hooks (NOT recommended):"
echo "  git commit --no-verify"
echo "  git push --no-verify"
echo ""
