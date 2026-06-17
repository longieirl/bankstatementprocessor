#!/usr/bin/env bash
# Skill registry — maps skill names to their SKILL.md paths.
# Usage: source ./skill.sh <skill-name>

declare -A SKILLS=(
  ["process-bank-statements"]="skills/process-bank-statements/SKILL.md"
)

if [ $# -eq 0 ]; then
  echo "Usage: source ./skill.sh <skill-name>"
  echo ""
  echo "Available skills:"
  for key in "${!SKILLS[@]}"; do
    echo "  - $key  →  ${SKILLS[$key]}"
  done
  exit 0
fi

path="${SKILLS[$1]}"

if [ -z "$path" ]; then
  echo "Unknown skill: $1"
  echo "Run ./skill.sh with no arguments to list available skills."
  exit 1
fi

echo "$path"
