#!/bin/bash
# Pre-commit hook for GitHub Issue Tracker

echo "Running pre-commit checks..."

# Check for Python syntax errors
echo "Checking Python syntax..."
python -m py_compile github_issue_tracker/*.py
if [ $? -ne 0 ]; then
    echo "❌ Python syntax errors found!"
    exit 1
fi

# Check for common issues
echo "Checking for common pitfalls..."

# Check for async refresh() calls (should be sync)
if grep -r "await self\.refresh()" github_issue_tracker/; then
    echo "❌ Found async refresh() calls - these should be synchronous!"
    echo "   Change 'await self.refresh()' to 'self.refresh()'"
    exit 1
fi

# Check for yaml.dump usage (should use safe_dump)
if grep -r "yaml\.dump(" github_issue_tracker/ | grep -v "yaml\.safe_dump"; then
    echo "❌ Found yaml.dump() usage - use yaml.safe_dump() instead!"
    exit 1
fi

# Check for unescaped brackets in error messages
if grep -r "notify.*\[.*\]" github_issue_tracker/ | grep -v "\\\\\\["; then
    echo "⚠️  Warning: Found unescaped brackets in notifications"
    echo "   Consider escaping with \\[ and \\]"
fi

# Validate YAML templates
echo "Validating YAML templates..."
for file in templates/*.yaml; do
    if [ -f "$file" ]; then
        python -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null
        if [ $? -ne 0 ]; then
            echo "❌ Invalid YAML in $file"
            exit 1
        fi
    fi
done

echo "✅ All pre-commit checks passed!"