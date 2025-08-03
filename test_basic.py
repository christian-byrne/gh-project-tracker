#!/usr/bin/env python3
"""Basic test to ensure the package imports work correctly."""

import sys

try:
    from github_issue_tracker import __version__
    from github_issue_tracker.models import Condition, ConditionType, QueryTemplate, Repository
    print(f"✓ All imports successful! Version: {__version__}")
    
    # Test creating a basic template
    template = QueryTemplate(
        name="Test",
        description="Test template",
        repositories=[Repository(owner="test", repo="test")],
        conditions=[Condition(type=ConditionType.LABEL, value="bug")]
    )
    print(f"✓ Created test template: {template.name}")
    
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)