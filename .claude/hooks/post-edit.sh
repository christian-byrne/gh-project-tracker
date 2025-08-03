#!/bin/bash
# Post-edit hook - runs after Claude makes changes

# Check if models.py was modified
if git diff --name-only | grep -q "models.py"; then
    echo "📝 models.py was modified - checking for enum handling..."
    
    # Remind about enum serialization
    echo "⚠️  Reminder: When storing enums in YAML:"
    echo "   - Use enum.value, not the enum object"
    echo "   - Check _auto_save() in tui.py converts enums properly"
fi

# Check if github_client.py was modified  
if git diff --name-only | grep -q "github_client.py"; then
    echo "🌐 github_client.py was modified - checking API patterns..."
    
    # Check for parallel processing
    if git diff github_client.py | grep -q "asyncio.gather"; then
        echo "⚠️  Warning: Found asyncio.gather() - consider sequential processing"
        echo "   Parallel requests can silently drop results"
    fi
fi

# Check if any templates were modified
if git diff --name-only | grep -q "templates/.*\.yaml"; then
    echo "📄 Template files modified - validating..."
    
    for file in $(git diff --name-only | grep "templates/.*\.yaml"); do
        python -c "import yaml; data = yaml.safe_load(open('$file')); print(f'✅ {file} is valid YAML')" 2>/dev/null
        if [ $? -ne 0 ]; then
            echo "❌ $file has invalid YAML!"
        fi
    done
fi

# Run quick smoke test if tui.py changed
if git diff --name-only | grep -q "tui.py"; then
    echo "🖥️  TUI modified - running import test..."
    python -c "from github_issue_tracker.tui import GitHubIssueTracker" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✅ TUI imports successfully"
    else
        echo "❌ TUI import failed - check for syntax errors"
    fi
fi